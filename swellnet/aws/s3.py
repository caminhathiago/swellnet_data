import os
from datetime import datetime, timedelta, UTC

from swellnet.aws.checkpoint import load_checkpoint, save_checkpoint, create_new_station
# from swellnet.config.config import CHECKPOINT_FILE

from pathlib import Path
PACKAGE_ROOT = Path(__file__).resolve().parents[1]
CHECKPOINT_FILE = PACKAGE_ROOT / "aws" / "s3_checkpoint.pkl"


def get_latest_subdir(paths, key_func):
    return max(paths, key=key_func)

def list_dirs(path, ignore_logs=True):
    if ignore_logs:
        return [p for p in path.iterdir() if p.is_dir() and p.name.lower() != "logs"]
    return [p for p in path.iterdir() if p.is_dir()]


def check_years_folders(station_path: Path) -> bool:

    if not station_path.exists():
        return False

    children = [p for p in station_path.iterdir() if p.is_dir()]

    if not children:
        return False

    non_logs = [p for p in children if p.name.lower() != "logs"]

    return len(non_logs) != 0

def get_latest_image_by_hierarchy(base_path: str, station: str, prefix:str) -> str | None:
    base = Path(base_path) / station
    if not base.exists():
        return None

    if not check_years_folders(base):
        raise NotADirectoryError(f"{station} doesnt have any data downloaded to be used as reference for backfilling. Either run script with --backfill set to 'all' or with no backfill.")

    year = get_latest_subdir(list_dirs(base), lambda p: int(p.name))
    month = get_latest_subdir(list_dirs(year), lambda p: int(p.name))
    day = get_latest_subdir(list_dirs(month), lambda p: int(p.name))
    hour = get_latest_subdir(list_dirs(day), lambda p: int(p.name))

    files = list(hour.glob("*.jpg"))
    
    if not files:
        raise FileNotFoundError(f"Latest file not found. Check for inconsistencies.")
    
    latest_file = max(files, key=lambda f: f.name)

    return (Path(prefix) / station / os.path.basename(latest_file)).as_posix()

def process_backfilling(incoming_path, backfill_arg, station, prefix):
    
    if backfill_arg == "all":
        checkpoint = None
        cutoff_enabled = False
    
    elif backfill_arg == "backfill":
        checkpoint = get_latest_image_by_hierarchy(incoming_path, station, prefix)
        cutoff_enabled = False

    elif backfill_arg == "disabled":
        contents = load_checkpoint(CHECKPOINT_FILE)
        contents = create_new_station(station, contents, CHECKPOINT_FILE)
        checkpoint = contents[station]["key"]
        cutoff_enabled = True
    
    else:
        raise ValueError("Backfill must be 'all', 'backfill' or 'disabled'.")

    return checkpoint, cutoff_enabled

def list_incremental(
        bucket, 
        prefix, 
        station, 
        s3,
        # start_datetime=None,
        end_datetime=datetime.now(UTC),
        lookback=timedelta(minutes=10),
        backfill=False,
        incoming_path=None):

    lookback += timedelta(minutes=+1)
    cutoff = end_datetime - lookback    

    checkpoint, cutoff_enabled = process_backfilling(incoming_path, backfill, station, prefix)

    paginator = s3.get_paginator("list_objects_v2")

    results = []
    first_key_in_window = None

    for page in paginator.paginate(
        Bucket=bucket,
        Prefix=prefix + station,
        StartAfter=checkpoint or ""
    ):

        for obj in page.get("Contents", []):

            key = obj["Key"]
            last_modified = obj["LastModified"]
            print(os.path.basename(key))
            if cutoff_enabled and last_modified < cutoff:
                continue

            results.append(obj)

            if not backfill and first_key_in_window is None:
                first_key_in_window = key
                first_key_last_mofied = last_modified

    if first_key_in_window:
        save_checkpoint(station, first_key_in_window, first_key_last_mofied, CHECKPOINT_FILE)

    return results

def filter_new_results(results, station, incoming_path):
    
    new_results = []

    for obj in results:
        key = obj.get("Key") or obj.get("key")

        local_path = process_local_path(key, station, incoming_path)

        # local_path = os.path.join(incoming_path, station, os.path.basename(key))

        if not os.path.exists(local_path):
            new_results.append(obj)

    return new_results

def process_local_path(key, station, incoming_path):

    import re
    match = re.search(r"_(\d{4})-(\d{2})-(\d{2})_(\d{2})", key)

    year = match.group(1)
    month = match.group(2)
    day = match.group(3)
    hour = match.group(4)

    local_path = os.path.join(
        incoming_path,
        station,
        year,
        month,
        day,
        hour,
        os.path.basename(key),
    )

    # os.makedirs(output_dir, exist_ok=True)

    return local_path

def download_s3_results(results, bucket, s3, station, incoming_path):
    
    os.makedirs(incoming_path, exist_ok=True)

    downloaded = []

    for obj in results:
        key = obj["Key"] if "Key" in obj else obj["key"]

        local_path = process_local_path(key, station, incoming_path)#os.path.join(output_dir, station, os.path.basename(key))
       
        os.makedirs(os.path.dirname(local_path), exist_ok=True)

        try:
            s3.download_file(bucket, key, local_path)
            downloaded.append(local_path)

        except Exception as e:
            print(f"❌ Failed to download {key}: {e}")

    return downloaded
    
    