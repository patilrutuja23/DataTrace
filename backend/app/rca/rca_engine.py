
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
