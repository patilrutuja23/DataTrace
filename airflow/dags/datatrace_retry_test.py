from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator


def fail_once_for_testing(**context):
    """Fail the first attempt and succeed on the retry."""
    ti = context["ti"]
    attempt = ti.try_number

    print(f"Test attempt number: {attempt}")

    if attempt == 1:
        raise RuntimeError("Intentional test failure on first attempt")

    print("Retry succeeded. Test completed.")


def record_test_failure(context):
    """Log failure details for the test only."""
    ti = context["ti"]
    error = context.get("exception")

    print(f"TEST TASK FAILED: {ti.task_id}")
    print(f"TEST ERROR: {error}")


with DAG(
    dag_id="datatrace_retry_test",
    description="Isolated test for Airflow retries",
    start_date=datetime(2026, 1, 1),
    schedule=None,
    catchup=False,
    default_args={
        "retries": 1,
        "retry_delay": timedelta(seconds=10),
    },
    tags=["datatrace", "test"],
) as dag:

    retry_test = PythonOperator(
        task_id="fail_once_then_succeed",
        python_callable=fail_once_for_testing,
        on_failure_callback=record_test_failure,
    )