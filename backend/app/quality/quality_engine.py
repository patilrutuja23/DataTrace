
import pandas as pd


def calculate_quality(df: pd.DataFrame) -> dict:
    # Basic dataset statistics
    total_rows, total_columns = df.shape
    total_cells = total_rows * total_columns

    missing_cells = int(df.isnull().sum().sum())
    duplicate_rows = int(df.duplicated().sum())

    # Preserve the existing quality score calculation
    score = 100.0

    if total_cells > 0:
        missing_percentage = (missing_cells / total_cells) * 100
        score -= missing_percentage

    if total_rows > 0:
        duplicate_percentage = (duplicate_rows / total_rows) * 100
        score -= duplicate_percentage

    score = max(0.0, min(100.0, score))

    if score >= 90:
        status = "GOOD"
    elif score >= 70:
        status = "WARNING"
    else:
        status = "POOR"

    # Column-level profiling
    column_profiles = []

    for column in df.columns:
        series = df[column]

        missing_count = int(series.isnull().sum())
        unique_count = int(series.nunique(dropna=True))

        column_profiles.append({
            "column": str(column),
            "data_type": str(series.dtype),
            "missing_count": missing_count,
            "missing_percentage": round(
                (missing_count / total_rows) * 100, 2
            ) if total_rows > 0 else 0.0,
            "unique_count": unique_count,
            "constant_column": (
                total_rows > 0 and unique_count <= 1
            ),
        })

    # Detect text values with leading or trailing whitespace
    whitespace_issues = {}

    for column in df.select_dtypes(include=["object", "string"]).columns:
        values = df[column].dropna().astype(str)
        count = int(
            values.ne(values.str.strip()).sum()
        )

        if count > 0:
            whitespace_issues[str(column)] = count

    # Detect duplicate column names
    duplicate_column_names = [
        str(column)
        for column in df.columns[df.columns.duplicated()].tolist()
    ]

    

    return {
        # Existing fields retained for compatibility
        "quality_score": round(score, 2),
        "missing_cells": missing_cells,
        "duplicate_rows": duplicate_rows,
        "status": status,

        # Additional dataset statistics
        "total_rows": int(total_rows),
        "total_columns": int(total_columns),

        # Additional quality checks
        "column_profiles": column_profiles,
        "duplicate_column_names": duplicate_column_names,
        "whitespace_issues": whitespace_issues,
    }
