
from fastapi import FastAPI, UploadFile, File, HTTPException
import pandas as pd

from app.ingestion.csv_reader import read_csv_file
from app.profiling.profiler import generate_profile
from app.quality.quality_engine import calculate_quality


app = FastAPI(
    title="DataTrace API",
    description="Data profiling and data quality analysis",
    version="1.0.0",
)


@app.get("/")
def home():
    return {
        "project": "DataTrace",
        "status": "running",
    }


@app.post("/api/datasets/analyze")
async def analyze_dataset(file: UploadFile = File(...)):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Please upload a CSV file.",
        )

    try:
        file_bytes = await file.read()

        if not file_bytes:
            raise HTTPException(
                status_code=400,
                detail="The uploaded file is empty.",
            )

        df = read_csv_file(file_bytes)

        if len(df.columns) == 0:
            raise HTTPException(
                status_code=400,
                detail="The CSV contains no columns.",
            )

        profile = generate_profile(df)
        quality = calculate_quality(df)

        return {
            "dataset": file.filename,
            "profile": profile,
            "quality": quality,
        }

    except HTTPException:
        raise
    except (
        pd.errors.ParserError,
        UnicodeDecodeError,
        ValueError,
    ) as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to process CSV: {exc}",
        ) from exc
    finally:
        await file.close()