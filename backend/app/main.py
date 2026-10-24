
from fastapi import FastAPI, UploadFile, File, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from sqlalchemy import select, delete
import pandas as pd
import io
from pydantic import BaseModel, Field
from pathlib import Path


from app.ingestion.csv_reader import read_csv_file
from app.profiling.profiler import generate_profile
from app.quality.quality_engine import calculate_quality
from app.database.connection import SessionLocal, engine, Base
from app.database.models import DatasetRecord, AnomalyRecord
from app.anomaly.anomaly_engine import detect_anomalies
from app.database import models
from app.database.models import LineageNode, LineageEdge
from app.lineage.lineage_service import (
    create_dataset_lineage,
    get_dataset_lineage,
)
from app.graph.neo4j_client import (
    driver as neo4j_driver,
    close_neo4j_connection,
    verify_neo4j_connection,
)
from app.graph.lineage_graph_service import (
    sync_lineage_to_neo4j,
    get_lineage_from_neo4j,
)
from app.database.models import AnomalyRecord
from app.rca.rca_engine import analyze_root_cause
from app.graph.impact_service import get_downstream_impact
from app.database import models
from app.database.models import AnomalyRecord, PipelineExecutionRecord



app = FastAPI(
    title="DataTrace API",
    description="Data profiling, data quality analysis and storage",
    version="2.0.0",
)
UPLOAD_DIR = Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try: 
        yield db
    finally:
        db.close()
        

@app.on_event("shutdown")
def shutdown():
    close_neo4j_connection()
    
    

class PipelineExecutionPayload(BaseModel):
    dataset_id: int
    dag_id: str
    dag_run_id: str
    state: str
    task_states: dict = Field(default_factory=dict)
    started_at: str | None = None
    finished_at: str | None = None
    error_summary: str | None = None


@app.get("/")
def home():
    return {
        "project": "DataTrace",
        "status": "running",
    }


@app.post("/api/datasets/analyze")
async def analyze_dataset(file: UploadFile = File(...), db: Session = Depends(get_db)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )
    
    file_bytes = await file.read()

    try:
        df = read_csv_file(file_bytes)
        
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=400,
            detail="Could not read the CSV file.",
        ) from exc
        
    profile = generate_profile(df)
    quality = calculate_quality(df)
    
    record = DatasetRecord(
        filename=file.filename,
        row_count=len(df),
        column_count=len(df.columns),
        profile=profile,
        quality=quality,
        quality_score=quality["quality_score"],
        quality_status=quality["status"],
    )
    
    saved_path = None

    try:
        db.add(record)
        db.flush()  # Assign the dataset ID before committing.

        saved_path = UPLOAD_DIR / f"dataset_{record.id}.csv"
        saved_path.write_bytes(file_bytes)

        db.commit()
        db.refresh(record)

    except Exception as exc:
        db.rollback()

        if saved_path is not None and saved_path.exists():
            saved_path.unlink()

        raise HTTPException(
            status_code=500,
            detail="Could not save the dataset and its original CSV file.",
        ) from exc 
    return {
        "id": record.id,
        "dataset_id": record.id,
        "filename": record.filename,
        "row_count": record.row_count,
        "column_count": record.column_count,
        "profile": record.profile,
        "quality": record.quality,
        "quality_score": record.quality_score,
        "quality_status": record.quality_status,
        "created_at": record.created_at,
    }   

@app.get("/api/datasets")
def list_datasets(db: Session = Depends(get_db)):
    try:
        records = db.scalars(
            select(DatasetRecord).order_by(DatasetRecord.id.desc())
        ).all()

        result = []

        for record in records:
            result.append({
                "id": record.id,
                "filename": record.filename,
                "row_count": record.row_count,
                "column_count": record.column_count,
                "quality_score": record.quality_score,
                "quality_status": record.quality_status,
                "created_at": record.created_at,
            })

        return result

    except Exception as exc:
        print(f"Error listing datasets: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve datasets."
        ) from exc

    


@app.get("/api/datasets/{dataset_id}")
def get_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    record = db.get(DatasetRecord, dataset_id)

    if record is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    return {
        "id": record.id,
        "dataset": record.filename,
        "profile": record.profile,
        "quality": record.quality,
        "created_at": record.created_at,
    }



@app.post("/api/datasets/{dataset_id}/lineage")
def create_lineage_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    try:
        lineage = create_dataset_lineage(db, dataset)
        db.commit()
        return lineage

    except Exception as exc:
        db.rollback()
        print(f"Error creating lineage: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not create dataset lineage.",
        ) from exc


@app.get("/api/datasets/{dataset_id}/lineage")
def get_lineage_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    return get_dataset_lineage(db, dataset_id)




@app.post("/api/datasets/{dataset_id}/lineage/sync")
def sync_lineage_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    try:
        verify_neo4j_connection()

        result = sync_lineage_to_neo4j(
            db=db,
            driver=neo4j_driver,
            dataset_id=dataset_id,
        )

        if result["nodes_synced"] == 0:
            raise HTTPException(
                status_code=409,
                detail="Create PostgreSQL lineage before syncing to Neo4j.",
            )

        return result

    except HTTPException:
        raise
    except Exception as exc:
        print(f"Neo4j sync error: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Could not synchronize lineage to Neo4j.",
        ) from exc


@app.get("/api/datasets/{dataset_id}/lineage/graph")
def get_neo4j_lineage_endpoint(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    try:
        verify_neo4j_connection()

        return get_lineage_from_neo4j(
            driver=neo4j_driver,
            dataset_id=dataset_id,
        )

    except Exception as exc:
        print(f"Neo4j query error: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve lineage from Neo4j.",
        ) from exc



@app.post("/api/datasets/{dataset_id}/anomalies")
async def analyze_anomalies(
    dataset_id: int,
    file: UploadFile | None = File(default=None),
    method: str = "IQR",
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    method = method.upper()
    if method not in {"IQR", "LOG_IQR"}:
        raise HTTPException(
            status_code=400,
            detail="method must be IQR or LOG_IQR.",
        )

    try:
        if file is not None:
            if not file.filename or not file.filename.lower().endswith(".csv"):
                raise HTTPException(
                    status_code=400,
                    detail="Only CSV files are supported.",
                )
            file_bytes = await file.read()
        else:
            stored_path = UPLOAD_DIR / f"dataset_{dataset_id}.csv"

            if not stored_path.is_file():
                raise HTTPException(
                    status_code=404,
                    detail=(
                        "Original CSV file not found for this dataset. "
                        "Re-upload the CSV to enable dataset-specific "
                        "anomaly detection."
                    ),
                )

            file_bytes = stored_path.read_bytes()

        df = read_csv_file(file_bytes)
        anomalies = detect_anomalies(df, method=method)

        db.execute(
            delete(AnomalyRecord).where(
                AnomalyRecord.dataset_id == dataset_id
            )
        )

        records = [
            AnomalyRecord(
                dataset_id=dataset_id,
                **anomaly,
            )
            for anomaly in anomalies
        ]

        db.add_all(records)
        db.commit()

        return {
            "dataset_id": dataset_id,
            "filename": dataset.filename,
            "method": method,
            "anomaly_count": len(anomalies),
            "anomalies": anomalies,
        }

    except HTTPException:
        raise
    except (
        pd.errors.ParserError,
        pd.errors.EmptyDataError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail="Could not read or analyze the CSV file.",
        ) from exc
    except Exception as exc:
        db.rollback()
        print(f"Anomaly detection error: {exc}")
        raise HTTPException(
            status_code=500,
            detail="Could not save anomaly results.",
        ) from exc



@app.get("/api/datasets/{dataset_id}/anomalies")
def get_anomalies(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    records = db.scalars(
        select(AnomalyRecord)
        .where(AnomalyRecord.dataset_id == dataset_id)
        .order_by(AnomalyRecord.id)
    ).all()

    return {
        "dataset_id": dataset_id,
        "anomaly_count": len(records),
        "anomalies": [
            {
                "id": record.id,
                "column_name": record.column_name,
                "row_index": record.row_index,
                "observed_value": record.observed_value,
                "lower_bound": record.lower_bound,
                "upper_bound": record.upper_bound,
                "direction": record.direction,
                "severity": record.severity,
                "method": record.method,
                "detected_at": record.detected_at,
            }
            for record in records
        ],
    }




@app.get("/api/datasets/{dataset_id}/rca")
def get_root_cause(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    records = db.scalars(
        select(AnomalyRecord).where(
            AnomalyRecord.dataset_id == dataset_id
        )
    ).all()

    anomalies = [
        {
            "column_name": record.column_name,
            "row_index": record.row_index,
            "observed_value": record.observed_value,
            "lower_bound": record.lower_bound,
            "upper_bound": record.upper_bound,
            "direction": record.direction,
            "severity": record.severity,
            "method": record.method,
        }
        for record in records
    ]

    dataset_data = {
        "id": dataset.id,
        "filename": dataset.filename,
        "profile": dataset.profile,
        "quality": dataset.quality,
    }

    return analyze_root_cause(dataset_data, anomalies)



@app.get("/api/datasets/{dataset_id}/impact")
def get_dataset_impact(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    try:
        verify_neo4j_connection()

        return get_downstream_impact(
            driver=neo4j_driver,
            dataset_id=dataset_id,
        )

    except Exception as exc:
        print(f"Impact analysis error: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve downstream impact from Neo4j.",
        ) from exc



@app.get("/api/datasets/{dataset_id}/investigate")
def investigate_dataset(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    records = db.scalars(
        select(AnomalyRecord).where(
            AnomalyRecord.dataset_id == dataset_id
        )
    ).all()

    anomalies = [
        {
            "column_name": record.column_name,
            "row_index": record.row_index,
            "observed_value": record.observed_value,
            "lower_bound": record.lower_bound,
            "upper_bound": record.upper_bound,
            "direction": record.direction,
            "severity": record.severity,
            "method": record.method,
        }
        for record in records
    ]

    dataset_data = {
        "id": dataset.id,
        "filename": dataset.filename,
        "profile": dataset.profile,
        "quality": dataset.quality,
    }

    rca = analyze_root_cause(dataset_data, anomalies)

    try:
        verify_neo4j_connection()

        impact = get_downstream_impact(
            driver=neo4j_driver,
            dataset_id=dataset_id,
        )

    except Exception as exc:
        print(f"Investigation impact query failed: {exc}")
        raise HTTPException(
            status_code=503,
            detail="Could not retrieve impact data from Neo4j.",
        ) from exc

    return {
        "dataset_id": dataset_id,
        "dataset": dataset.filename,
        "anomaly_count": len(anomalies),
        "root_cause_analysis": rca,
        "impact_analysis": impact,
    }



@app.post("/api/datasets/{dataset_id}/pipeline-executions")
def save_pipeline_execution(
    dataset_id: int,
    payload: PipelineExecutionPayload,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    if payload.dataset_id != dataset_id:
        raise HTTPException(
            status_code=400,
            detail="Dataset ID in the URL and payload must match.",
        )

    if not payload.dag_id.strip() or not payload.dag_run_id.strip():
        raise HTTPException(
            status_code=400,
            detail="dag_id and dag_run_id must not be empty.",
        )

    allowed_states = {"success", "failed", "running", "queued"}
    if payload.state.lower() not in allowed_states:
        raise HTTPException(
            status_code=400,
            detail=f"state must be one of {sorted(allowed_states)}.",
        )

    record = db.query(PipelineExecutionRecord).filter_by(
        dag_run_id=payload.dag_run_id
    ).first()

    values = payload.model_dump(exclude={"dataset_id"})

    if record is None:
        record = PipelineExecutionRecord(
            dataset_id=dataset_id,
            **values,
        )
        db.add(record)
    else:
        if record.dataset_id != dataset_id:
            raise HTTPException(
                status_code=409,
                detail="This DAG run ID is already associated with another dataset.",
            )
        for key, value in values.items():
            setattr(record, key, value)

    try:
        db.commit()
        db.refresh(record)
    except Exception:
        db.rollback()
        raise

    return {
        "message": "Pipeline execution evidence saved.",
        "id": record.id,
        "dataset_id": record.dataset_id,
        "dag_id": record.dag_id,
        "dag_run_id": record.dag_run_id,
        "state": record.state,
        "task_states": record.task_states,
        "started_at": record.started_at,
        "finished_at": record.finished_at,
        "error_summary": record.error_summary,
    }



@app.get("/api/datasets/{dataset_id}/pipeline-executions")
def get_pipeline_executions(
    dataset_id: int,
    db: Session = Depends(get_db),
):
    dataset = db.get(DatasetRecord, dataset_id)

    if dataset is None:
        raise HTTPException(
            status_code=404,
            detail="Dataset analysis not found.",
        )

    records = (
        db.query(PipelineExecutionRecord)
        .filter(PipelineExecutionRecord.dataset_id == dataset_id)
        .order_by(PipelineExecutionRecord.id.desc())
        .all()
    )

    return [
        {
            "id": record.id,
            "dataset_id": record.dataset_id,
            "dag_id": record.dag_id,
            "dag_run_id": record.dag_run_id,
            "state": record.state,
            "task_states": record.task_states,
            "started_at": record.started_at,
            "finished_at": record.finished_at,
            "error_summary": record.error_summary,
        }
        for record in records
    ]
