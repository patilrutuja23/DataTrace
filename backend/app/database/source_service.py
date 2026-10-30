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
def ingest_source(
    source_id: int,
    db: Session = Depends(get_db),
):
    source = db.get(DatabaseSource, source_id)

    if source is None or not source.is_active:
        raise HTTPException(
            status_code=404,
            detail="Database source not found.",
        )

    if not source.selected_table or not source.selected_schema:
        raise HTTPException(
            status_code=400,
            detail="Select a database table before ingesting.",
        )

    engine = source_engine(source)

    try:
        schema = source.selected_schema
        table = source.selected_table

        inspector = inspect(engine)

        if schema not in inspector.get_schema_names():
            raise HTTPException(
                status_code=400,
                detail="Selected schema does not exist.",
            )

        if table not in inspector.get_table_names(schema=schema):
            raise HTTPException(
                status_code=400,
                detail="Selected table does not exist.",
            )

        preparer = engine.dialect.identifier_preparer

        qualified_table = (
            f"{preparer.quote_schema(schema)}."
            f"{preparer.quote(table)}"
        )

        # Read the latest complete table snapshot.
        with engine.connect() as connection:
            df = pd.read_sql_query(
                text(f"SELECT * FROM {qualified_table}"),
                connection,
            )

        if df.empty:
            raise HTTPException(
                status_code=400,
                detail="The selected table contains no records.",
            )

        # Recalculate the complete dataset profile and quality.
        profile = generate_profile(df)
        quality = calculate_quality(df)
        anomalies = detect_anomalies(df)

        # Reuse the existing database-backed dataset.
        record = None

        if source.dataset_id is not None:
            record = db.get(DatasetRecord, source.dataset_id)

        is_new_dataset = record is None

        if is_new_dataset:
            record = DatasetRecord(
                filename=f"{source.name}.{schema}.{table}",
                row_count=len(df),
                column_count=len(df.columns),
                profile=profile,
                quality=quality,
                quality_score=quality["quality_score"],
                quality_status=quality["status"],
            )
            db.add(record)
            db.flush()

        else:
            record.filename = f"{source.name}.{schema}.{table}"
            record.row_count = len(df)
            record.column_count = len(df.columns)
            record.profile = profile
            record.quality = quality
            record.quality_score = quality["quality_score"]
            record.quality_status = quality["status"]

        # Replace previous anomaly results for this dataset.
        db.execute(
            delete(AnomalyRecord).where(
                AnomalyRecord.dataset_id == record.id
            )
        )

        for anomaly in anomalies:
            db.add(
                AnomalyRecord(
                    dataset_id=record.id,
                    column_name=anomaly["column_name"],
                    row_index=anomaly["row_index"],
                    observed_value=anomaly["observed_value"],
                    lower_bound=anomaly["lower_bound"],
                    upper_bound=anomaly["upper_bound"],
                    direction=anomaly["direction"],
                    severity=anomaly["severity"],
                    method=anomaly["method"],
                )
            )

        source.dataset_id = record.id
        source.last_sync_at = datetime.now(timezone.utc)
        source.ingestion_status = "success"

        # This is a snapshot row count, not yet an incremental checkpoint.
        source.last_checkpoint = str(len(df))

        db.commit()
        db.refresh(record)

        return {
            "success": True,
            "message": (
                "Database dataset updated successfully."
                if not is_new_dataset
                else "Database dataset created successfully."
            ),
            "source_id": source.id,
            "dataset_id": record.id,
            "updated_existing": not is_new_dataset,
            "filename": record.filename,
            "row_count": record.row_count,
            "column_count": record.column_count,
            "profile": record.profile,
            "quality": record.quality,
            "quality_score": record.quality_score,
            "quality_status": record.quality_status,
            "anomaly_count": len(anomalies),
            "created_at": record.created_at,
            "last_sync_at": source.last_sync_at,
        }

    except HTTPException:
        db.rollback()
        raise

    except Exception as exc:
        db.rollback()

        print(f"Database ingestion failed: {exc}")

        failed_source = db.get(DatabaseSource, source_id)

        if failed_source is not None:
            failed_source.ingestion_status = "failed"
            db.commit()

        raise HTTPException(
            status_code=500,
            detail="Database ingestion failed. Check backend logs.",
        ) from exc

    finally:
        engine.dispose()

