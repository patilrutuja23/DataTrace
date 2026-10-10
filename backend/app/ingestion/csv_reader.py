
import io
import pandas as pd


def read_csv_file(file_bytes: bytes) -> pd.DataFrame:
    """
    Read uploaded CSV file bytes and convert them
    into a Pandas DataFrame.
    """
    df = pd.read_csv(io.BytesIO(file_bytes))
    return df