
import pandas as pd


def detect_anomalies(df: pd.DataFrame) -> list[dict]:
    anomalies = []

    numeric_columns = df.select_dtypes(
        include="number"
    ).columns

    for column in numeric_columns:
        values = df[column].dropna()

        if len(values) < 4:
            continue

        q1 = float(values.quantile(0.25))
        q3 = float(values.quantile(0.75))
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr

        extreme_lower = q1 - 3 * iqr
        extreme_upper = q3 + 3 * iqr

        for row_index, value in df[column].items():
            if pd.isna(value):
                continue

            value = float(value)

            if value < lower_bound:
                direction = "LOW"
                severity = (
                    "HIGH" if value < extreme_lower
                    else "MEDIUM"
                )
            elif value > upper_bound:
                direction = "HIGH"
                severity = (
                    "HIGH" if value > extreme_upper
                    else "MEDIUM"
                )
            else:
                continue

            anomalies.append({
                "column_name": str(column),
                "row_index": int(row_index),
                "observed_value": value,
                "lower_bound": round(lower_bound, 4),
                "upper_bound": round(upper_bound, 4),
                "direction": direction,
                "severity": severity,
                "method": "IQR",
            })

    return anomalies
