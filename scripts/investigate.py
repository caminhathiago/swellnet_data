import os
from datetime import datetime, timedelta

import pytz
import boto3
from dotenv import load_dotenv

from swellnet.config.config import IMAGE_KEY_PATTERN


load_dotenv()

# -----------------------------
# CONFIG
# -----------------------------
ACCESS_KEY = os.getenv('ACCESS_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
BUCKET_NAME = os.getenv('BUCKET_NAME')
PREFIX = os.getenv('PREFIX')

AWST = pytz.timezone("Australia/Perth")
# Optional: set region if needed
# REGION = "us-east-1"

# -----------------------------
# SESSION
# -----------------------------
session = boto3.Session(
    aws_access_key_id=ACCESS_KEY,
    aws_secret_access_key=SECRET_KEY,
    # region_name=REGION
)

s3 = session.client("s3")


# -----------------------------
# LIST ROOT CONTENTS
# -----------------------------
def list_root(
    bucket,
    start_datetime=None,
    end_datetime=None,
    prefix="",
    enable_print=False
):
    paginator = s3.get_paginator("list_objects_v2")

    print(f"\n📦 Listing: s3://{bucket}/{prefix}\n")

    contents = []

    try:
        for page in paginator.paginate(Bucket=bucket, Prefix=prefix):

            if "Contents" not in page:
                continue

            for obj in page["Contents"]:
                key = obj["Key"]
                size = obj["Size"]
                last_modified = obj["LastModified"]

                # -----------------------------
                # TIME FILTERING
                # -----------------------------
                if start_datetime and last_modified < start_datetime:
                    continue

                if end_datetime and last_modified > end_datetime:
                    continue

                if enable_print:
                    print(f"FILE  | {key} | {size} bytes | {last_modified}")

                contents.append({
                    "key": key,
                    "size": size,
                    "last_modified": last_modified
                })

        return contents

    except s3.exceptions.ClientError as e:
        print("❌ Access error:", e.response["Error"]["Message"])
        return []


# -----------------------------
# RECURSIVE CRAWL (LIGHTWEIGHT TREE)
# -----------------------------
def crawl(bucket, prefix="", depth=0, max_depth=10):
    indent = "  " * depth
    if depth > max_depth:
        return

    try:
        response = s3.list_objects_v2(
            Bucket=bucket,
            Prefix=prefix,
            Delimiter="/"
        )
    except s3.exceptions.ClientError as e:
        print(indent + f"❌ Access denied at {prefix}")
        return

    # files
    for obj in response.get("Contents", []):
        print(indent + f"FILE: {obj['Key']}")

    # folders
    for cp in response.get("CommonPrefixes", []):
        print(indent + f"DIR : {cp['Prefix']}")
        crawl(bucket, cp["Prefix"], depth + 1, max_depth)

def list_folders(bucket, prefix):
    paginator = s3.get_paginator("list_objects_v2")

    print(f"\n📁 Folders inside s3://{bucket}/{prefix}\n")

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=prefix,
        Delimiter="/"
    ):
        for cp in page.get("CommonPrefixes", []):
            print(cp["Prefix"])



def generate_s3_keys(
    prefix,
    station,
    start_datetime,
    end_datetime,
    timezone="AWST",
    step_minutes=1,
    check_exists=False,
    s3_client=None,
    bucket=None
):
    keys = []

    current = start_datetime

    while current <= end_datetime:

        key = IMAGE_KEY_PATTERN.format(
            prefix=prefix,
            station=station,
            site_name=station,
            year=f"{current:%Y}",
            month=f"{current:%m}",
            day=f"{current:%d}",
            hour=f"{current:%H}",
            minute=f"{current:%M}",
            second=f"{current:%S}",
            timezone=timezone
        )

        if check_exists:
            try:
                s3_client.head_object(Bucket=bucket, Key=key)
                keys.append(key)
            except Exception:
                pass
        else:
            keys.append(key)

        current += timedelta(minutes=step_minutes)

    return keys



if __name__ == "__main__":

    list_folders(BUCKET_NAME, PREFIX)

    # contents = list_root(BUCKET_NAME, PREFIX + 'scarborough')

    # end = datetime.now(AWST)
    # start = end - timedelta(days=1)

    # files = list_root(
    #     bucket=BUCKET_NAME,
    #     prefix= PREFIX + 'scarborough',
    #     start_datetime=start,
    #     end_datetime=end,
    #     enable_print=True
    # )

    # from datetime import datetime
    # from zoneinfo import ZoneInfo

    # AWST = ZoneInfo("Australia/Perth")

    # start = datetime(2026, 1, 1, 0, 0, tzinfo=AWST)
    # end   = datetime(2026, 1, 1, 2, 0, tzinfo=AWST)

    # keys = generate_s3_keys(
    #     prefix="city-stirling",
    #     station="scarborough",
    #     start_datetime=start,
    #     end_datetime=end,
    #     step_minutes=1
    # )

    print("script sucessfully finished")
    # Optional: tree crawl
    # crawl(BUCKET_NAME)
