from datetime import datetime, timezone
from pathlib import Path
import os

import pandas as pd

from cryptography.fernet import Fernet, InvalidToken
from dotenv import load_dotenv
from fastapi import HTTPException, Depends
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import create_engine, inspect, text, select, delete
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.database.connection import SessionLocal
from app.database.models import DatabaseSource

from app.database.models import DatasetRecord, AnomalyRecord
from app.profiling.profiler import generate_profile
from app.quality.quality_engine import calculate_quality
from app.anomaly.anomaly_engine import detect_anomalies


load_dotenv()

router = APIRouter(prefix="/api/sources", tags=["Database Sources"])


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_fernet():
    key = os.getenv("DATATRACE_CREDENTIAL_KEY")
    if not key:
        raise HTTPException(
            status_code=500,
            detail="Database credential encryption is not configured.",
        )
    try:
        return Fernet(key.encode())
    except (ValueError, TypeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Database credential encryption key is invalid.",
        ) from exc


class ConnectionDetails(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    db_type: str
    host: str = Field(min_length=1, max_length=255)
    port: int = Field(ge=1, le=65535)
    database_name: str = Field(min_length=1, max_length=255)
    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=1024)


class SelectTableRequest(BaseModel):
    schema_name: str | None = Field(default=None, max_length=255)
    table_name: str = Field(min_length=1, max_length=255)


def normalize_type(db_type: str) -> str:
    value = db_type.strip().lower()
    if value not in {"postgresql", "mysql"}:
        raise HTTPException(
            status_code=422,
            detail="db_type must be postgresql or mysql.",
        )
    return value


def build_engine(details: ConnectionDetails, password: str):
    db_type = normalize_type(details.db_type)

    if db_type == "postgresql":
        driver = "postgresql+psycopg"
        connect_args = {"connect_timeout": 5}
    else:
        driver = "mysql+pymysql"
        connect_args = {"connect_timeout": 5}

    url = URL.create(
        drivername=driver,
        username=details.username,
        password=password,
        host=details.host,
        port=details.port,
        database=details.database_name,
    )

    return create_engine(
        url,
        connect_args=connect_args,
        pool_pre_ping=True,
    )


def source_details(source: DatabaseSource):
    # Deliberately never return the encrypted or plaintext password.
    return {
        "id": source.id,
        "name": source.name,
        "db_type": source.db_type,
        "host": source.host,
        "port": source.port,
        "database_name": source.database_name,
        "username": source.username,
        "selected_schema": source.selected_schema,
        "selected_table": source.selected_table,
        "is_active": source.is_active,
        "created_at": source.created_at,
    }


def source_engine(source: DatabaseSource):
    try:
        password = get_fernet().decrypt(
            source.encrypted_password.encode()
        ).decode()
    except (InvalidToken, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=500,
            detail="Saved credentials could not be decrypted.",
        ) from exc

    details = ConnectionDetails(
        name=source.name,
        db_type=source.db_type,
        host=source.host,
        port=source.port,
        database_name=source.database_name,
        username=source.username,
        password=password,
    )
    return build_engine(details, password)


@router.post("/test-connection")
def test_connection(details: ConnectionDetails):
    engine = build_engine(details, details.password)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        return {
            "success": True,
            "message": "Database connection successful.",
        }
    except SQLAlchemyError as exc:
        # Avoid returning connection URLs, passwords, or driver internals.
        raise HTTPException(
            status_code=400,
            detail="Connection failed. Check the host, port, database, "
                   "username, password, network access, and database permissions.",
        ) from exc
    finally:
        engine.dispose()


@router.post("")
def create_source(
    details: ConnectionDetails,
    db: Session = Depends(get_db),
):
    db_type = normalize_type(details.db_type)

    # Test first, so an unreachable source is not saved as a valid connection.
    engine = build_engine(details, details.password)
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=400,
            detail="Connection failed. Test the credentials and network access.",
        ) from exc
    finally:
        engine.dispose()

    encrypted_password = get_fernet().encrypt(
        details.password.encode()
    ).decode()

    source = DatabaseSource(
        name=details.name.strip(),
        db_type=db_type,
        host=details.host.strip(),
        port=details.port,
        database_name=details.database_name.strip(),
        username=details.username.strip(),
        encrypted_password=encrypted_password,
    )

    db.add(source)
    db.commit()
    db.refresh(source)
    return source_details(source)


@router.get("")
def list_sources(db: Session = Depends(get_db)):
    sources = (
        db.query(DatabaseSource)
        .order_by(DatabaseSource.id.desc())
        .all()
    )
    return [source_details(source) for source in sources]


@router.get("/{source_id}/tables")
def list_source_tables(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DatabaseSource, source_id)
    if source is None or not source.is_active:
        raise HTTPException(status_code=404, detail="Database source not found.")

    engine = source_engine(source)
    try:
        inspector = inspect(engine)
        schemas = inspector.get_schema_names()

        # Hide internal PostgreSQL schemas from the table browser.
        if source.db_type == "postgresql":
            schemas = [
                schema for schema in schemas
                if schema not in {"information_schema"}
                and not schema.startswith("pg_")
            ]
        else:
            schemas = [source.database_name]

        tables = []
        for schema in schemas:
            try:
                for table_name in inspector.get_table_names(schema=schema):
                    tables.append({
                        "schema": schema,
                        "table_name": table_name,
                    })
            except SQLAlchemyError:
                # A schema may be visible but not readable to this user.
                continue

        return {
            "source_id": source.id,
            "tables": tables,
        }
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not browse tables. Check database permissions.",
        ) from exc
    finally:
        engine.dispose()


@router.post("/{source_id}/select-table")
def select_source_table(
    source_id: int,
    selection: SelectTableRequest,
    db: Session = Depends(get_db),
):
    source = db.get(DatabaseSource, source_id)
    if source is None or not source.is_active:
        raise HTTPException(status_code=404, detail="Database source not found.")

    engine = source_engine(source)
    try:
        inspector = inspect(engine)
        schema = selection.schema_name

        if source.db_type == "mysql":
            schema = source.database_name

        if schema not in inspector.get_schema_names():
            raise HTTPException(status_code=400, detail="Schema not found.")

        tables = inspector.get_table_names(schema=schema)
        if selection.table_name not in tables:
            raise HTTPException(status_code=400, detail="Table not found.")

        source.selected_schema = schema
        source.selected_table = selection.table_name
        db.commit()
        db.refresh(source)

        return {
            "message": "Table selected successfully.",
            "source": source_details(source),
        }
    except HTTPException:
        raise
    except SQLAlchemyError as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not verify the selected table.",
        ) from exc
    finally:
        engine.dispose()


@router.post("/{source_id}/ingest")
def ingest_source(source_id: int):
    # Incremental ingestion logic will go here.
    pass

