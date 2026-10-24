
def analyze_root_cause(
    dataset: dict,
    anomalies: list[dict],
) -> dict:
    """
    Generate evidence-based, rule-driven RCA findings.
    This function does not use an LLM.
    """

    profile = dataset.get("profile") or {}
    quality = dataset.get("quality") or {}

    findings = []
    missing_values = profile.get("missing_values") or {}

    # Rule 1: Missing values in the dataset
    columns_with_missing = {
        column: count
        for column, count in missing_values.items()
        if isinstance(count, (int, float)) and count > 0
    }

    if columns_with_missing:
        findings.append({
            "cause": "Missing data detected",
            "category": "DATA_QUALITY",
            "confidence": 0.90,
            "evidence": {
                "columns_with_missing_values": columns_with_missing,
                "missing_cells": quality.get("missing_cells"),
            },
            "recommendation": (
                "Inspect missing records and determine whether "
                "they result from ingestion, source data, or "
                "an intentional business rule."
            ),
        })

    # Rule 2: Duplicate rows
    duplicate_rows = profile.get("duplicate_rows", 0)

    if isinstance(duplicate_rows, (int, float)) and duplicate_rows > 0:
        findings.append({
            "cause": "Duplicate rows detected",
            "category": "DATA_QUALITY",
            "confidence": 0.90,
            "evidence": {
                "duplicate_rows": int(duplicate_rows),
            },
            "recommendation": (
                "Check whether duplicate records are valid "
                "transactions or unintended duplicate ingestion."
            ),
        })
    
    # Rule 2b: Leading or trailing whitespace
    whitespace_issues = quality.get("whitespace_issues") or {}

    if whitespace_issues:
        findings.append({
            "cause": "Leading or trailing whitespace detected",
            "category": "DATA_QUALITY",
            "confidence": 0.95,
            "evidence": {
                "columns_with_whitespace": whitespace_issues,
                "affected_value_count": sum(
                    count for count in whitespace_issues.values()
                    if isinstance(count, (int, float))
                ),
            },
            "recommendation": (
                "Inspect affected text columns and trim whitespace "
                "where appropriate. Check whether whitespace changes "
                "identifiers, category matching, or joins."
            ),
        })

    # Rule 2c: Duplicate column names
    duplicate_column_names = quality.get("duplicate_column_names") or []

    if duplicate_column_names:
        findings.append({
            "cause": "Duplicate column names detected",
            "category": "DATA_QUALITY",
            "confidence": 0.99,
            "evidence": {
                "duplicate_column_names": duplicate_column_names,
            },
            "recommendation": (
                "Rename duplicate columns uniquely and verify that "
                "each column maps to the intended source field."
            ),
        })

    # Rule 2d: Constant columns
    column_profiles = quality.get("column_profiles") or []

    constant_columns = [
        item.get("column")
        for item in column_profiles
        if item.get("constant_column") is True
        and item.get("column") is not None
    ]

    if constant_columns:
        findings.append({
            "cause": "Constant columns detected",
            "category": "DATA_QUALITY",
            "confidence": 0.75,
            "evidence": {
                "constant_columns": constant_columns,
            },
            "recommendation": (
                "Check whether these columns are expected to contain "
                "only one distinct value. If not, investigate source "
                "mapping, ingestion, and transformation logic."
            ),
        })


    # Rule 3: Numeric anomalies
    if anomalies:
        affected_columns = sorted({
            anomaly["column_name"]
            for anomaly in anomalies
        })

        findings.append({
            "cause": "Unusual numeric values detected",
            "category": "ANOMALY",
            "confidence": 0.80,
            "evidence": {
                "anomaly_count": len(anomalies),
                "affected_columns": affected_columns,
                "methods": sorted({
                    anomaly.get("method", "UNKNOWN")
                    for anomaly in anomalies
                }),
                "severity_counts": {
                    severity: sum(
                        1 for anomaly in anomalies
                        if anomaly.get("severity") == severity
                    )
                    for severity in ("HIGH", "MEDIUM")
                    if any(
                        anomaly.get("severity") == severity
                        for anomaly in anomalies
                    )
                },
            },
            "recommendation": (
                "Compare the flagged values with source records, "
                "business events, and historical patterns before "
                "deciding whether the values are erroneous."
            ),
        })

    # Rule 4: Poor quality score
    quality_score = quality.get("quality_score")

    if isinstance(quality_score, (int, float)) and quality_score < 70:
        findings.append({
            "cause": "Low overall data quality score",
            "category": "DATA_QUALITY",
            "confidence": 0.85,
            "evidence": {
                "quality_score": quality_score,
                "quality_status": quality.get("status"),
            },
            "recommendation": (
                "Investigate missing values, duplicates, and "
                "the individual quality checks that reduced "
                "the score."
            ),
        })

    if not findings:
        findings.append({
            "cause": "No root cause identified from available evidence",
            "category": "UNKNOWN",
            "confidence": 0.0,
            "evidence": {
                "anomaly_count": len(anomalies),
                "quality_score": quality.get("quality_score"),
            },
            "recommendation": (
                "Collect additional evidence such as historical "
                "metrics, ingestion logs, and pipeline execution "
                "status."
            ),
        })

    return {
        "dataset_id": dataset.get("id"),
        "dataset": dataset.get("filename"),
        "finding_count": len(findings),
        "findings": findings,
        "limitations": [
            "Findings are rule-based hypotheses, not proof of causation.",
            "Pipeline logs and execution status are not currently "
            "available to this engine.",
        ],
    }
