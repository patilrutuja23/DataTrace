
import pandas as pd


def calculate_quality(df: pd.DataFrame) -> dict:
    total_cells = df.shape[0] * df.shape[1]

    missing_cells = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    score = 100.0

    if total_cells > 0:
        missing_percentage = (
            missing_cells / total_cells
        ) * 100
        score -= missing_percentage

    if len(df) > 0:
        duplicate_percentage = (
            duplicate_rows / len(df)
        ) * 100
        score -= duplicate_percentage

    score = max(0, min(100, score))

    if score >= 90:
        status = "GOOD"
    elif score >= 70:
        status = "WARNING"
    else:
        status = "POOR"

    return {
        "quality_score": round(score, 2),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "status": status,
    }