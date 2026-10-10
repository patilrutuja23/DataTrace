
import pandas as pd


def generate_profile(df: pd.DataFrame) -> dict:
    profile = {
        "row_count": int(len(df)),
        "column_count": int(len(df.columns)),
        "columns": df.columns.tolist(),
        "data_types": {
            column: str(dtype)
            for column, dtype in df.dtypes.items()
        },
        "missing_values": {
            column: int(count)
            for column, count in df.isnull().sum().items()
        },
        "duplicate_rows": int(df.duplicated().sum()),
        "numeric_statistics": {},
    }

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    for column in numeric_columns:
        profile["numeric_statistics"][column] = {
            "min": float(df[column].min()),
            "max": float(df[column].max()),
            "mean": float(df[column].mean()),
            "median": float(df[column].median()),
        }

    return profile