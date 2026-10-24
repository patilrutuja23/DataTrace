
import pandas as pd


def detect_anomalies(
    df: pd.DataFrame,
    method: str = "IQR",
) -> list[dict]:
    anomalies = []

    method = method.upper()
    if method not in {"IQR", "LOG_IQR"}:
        raise ValueError("method must be 'IQR' or 'LOG_IQR'")

    numeric_columns = df.select_dtypes(include="number").columns

    for column in numeric_columns:
        values = df[column].dropna()

        if len(values) < 4:
            continue

        # Log-IQR is only valid for non-negative values.
        if method == "LOG_IQR":
            if (values < 0).any():
                continue
            transformed = values.map(lambda value: __import__("math").log1p(float(value)))
        else:
            transformed = values.astype(float)

        q1 = float(transformed.quantile(0.25))
        q3 = float(transformed.quantile(0.75))
        iqr = q3 - q1

        if iqr == 0:
            continue

        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        extreme_lower = q1 - 3 * iqr
        extreme_upper = q3 + 3 * iqr

        # Return bounds in the original data scale.
        if method == "LOG_IQR":
            import math
            lower_bound = math.expm1(lower)
            upper_bound = math.expm1(upper)
            extreme_lower_original = math.expm1(extreme_lower)
            extreme_upper_original = math.expm1(extreme_upper)
        else:
            lower_bound = lower
            upper_bound = upper
            extreme_lower_original = extreme_lower
            extreme_upper_original = extreme_upper

        for row_index, value in values.items():
            value = float(value)

            if method == "LOG_IQR":
                transformed_value = __import__("math").log1p(value)
            else:
                transformed_value = value

            if transformed_value < lower:
                direction = "LOW"
                severity = (
                    "HIGH"
                    if transformed_value < extreme_lower
                    else "MEDIUM"
                )
            elif transformed_value > upper:
                direction = "HIGH"
                severity = (
                    "HIGH"
                    if transformed_value > extreme_upper
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
                "method": method,
            })

    return anomalies
