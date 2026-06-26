import os
from datetime import datetime, timedelta

import pytz
import boto3
import pandas as pd
from dotenv import load_dotenv

from swellnet.config.config import IMAGE_KEY_PATTERN


def build_minute_index(start_datetime, end_datetime, freq="1min"):
    """
    Vectorized generation of minute timestamps.
    """
    return pd.date_range(start=start_datetime, end=end_datetime, freq=freq)


def build_minute_prefix(row, prefix, station, timezone):
    """
    Build S3 prefix up to minute resolution (ignore seconds).
    """
    return (
        f"{prefix}/{station}/"
        f"{station}_"
        f"{row.year}-{row.month:02d}-{row.day:02d}_"
        f"{row.hour:02d}-{row.minute:02d}-"
    )


def list_available_files(
    s3_client,
    bucket,
    prefix,
    station,
    start_datetime,
    end_datetime,
    timezone="AWST"
):
    results = []

    # -----------------------------
    # 1. VECTORISED TIME GRID
    # -----------------------------
    times = build_minute_index(start_datetime, end_datetime)

    df = pd.DataFrame({"time": times})

    # -----------------------------
    # 2. BUILD PREFIXES (vectorised)
    # -----------------------------
    df["s3_prefix"] = df["time"].apply(
        lambda t: build_minute_prefix(t, prefix, station, timezone)
    )

    unique_prefixes = df["s3_prefix"].unique()

    # -----------------------------
    # 3. QUERY S3 PER MINUTE PREFIX
    # -----------------------------
    # for p in unique_prefixes:

    response = s3_client.list_objects_v2(
        Bucket=bucket,
        Prefix=prefix + station
    )

    for obj in response.get("Contents", []):
        key = obj["Key"]
        print(key)
        # optional filtering safety (in case prefix is broad)
        if key.startswith(f"{prefix}{station}/{station}_"):
            results.append({
                "key": key,
                "last_modified": obj["LastModified"],
                "size": obj["Size"]
            })

    return pd.DataFrame(results)


if __name__ == "__main__":


    load_dotenv()
    ACCESS_KEY = os.getenv('ACCESS_KEY')
    SECRET_KEY = os.getenv('SECRET_KEY')
    BUCKET_NAME = os.getenv('BUCKET_NAME')
    PREFIX = os.getenv('PREFIX')

    session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
)

    s3 = session.client("s3")
    
    from datetime import datetime

    AWST = pytz.timezone("Australia/Perth")
    
    # start_datetime = datetime(2026, 1, 1, 0, 0, tzinfo=AWST)
    # end_datetime   = datetime(2026, 1, 1, 2, 0, tzinfo=AWST)

    end_datetime = datetime.now(AWST)
    start_datetime = end_datetime - timedelta(hours=24)

    results = list_available_files(
        s3,
        BUCKET_NAME,
        PREFIX,
        'scarborough',
        start_datetime,
        end_datetime,
        timezone="AWST"
    )

    print("scrip run successful")