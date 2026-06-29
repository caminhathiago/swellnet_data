import os
from datetime import datetime, timedelta, UTC

import pytz
import boto3
import pandas as pd
from dotenv import load_dotenv

from swellnet.aws.s3 import *
from swellnet.utils import SITE_LOGGER, IMOSLogging, args_auswaves_processing
from swellnet.alerts.email import Email

if __name__ == "__main__":

    load_dotenv()
    
    ACCESS_KEY = os.getenv('ACCESS_KEY')
    SECRET_KEY = os.getenv('SECRET_KEY')
    BUCKET_NAME = os.getenv('BUCKET_NAME')
    PREFIX = os.getenv('PREFIX')

    INCOMING_PATH = os.getenv('INCOMING_PATH')

    vargs = args_auswaves_processing()

    imos_logging = IMOSLogging()
    GENERAL_LOGGER = imos_logging.generate_general_logger(INCOMING_PATH, os.path.basename(__file__).removesuffix(".py"))

    sites = [
        'brighton',
        'contacio',
        'north-floreat',
        'north-scarborough',
        'scarborough',
        'south-trigg',
    ]

    for STATION in sites:
        
        sites_error_logs = []

        try:
            
            SITE_LOGGER = imos_logging.generate_site_logger(INCOMING_PATH, STATION, os.path.basename(__file__).removesuffix(".py"))
            
            GENERAL_LOGGER.info(f"{STATION.upper()} processing"+"="*60)

            SITE_LOGGER.info("Connecting with AWSs3")
            session = boto3.Session(
                aws_access_key_id=ACCESS_KEY,
                aws_secret_access_key=SECRET_KEY,
            )

            s3 = session.client("s3")

            SITE_LOGGER.info(f"Backfill is set to {vargs.backfill}. Fetching images from last {vargs.window} minutes if backfill is set to 'disabled'.")
            results = list_incremental(
                BUCKET_NAME, 
                PREFIX, 
                STATION, 
                s3,
                end_datetime=datetime.now(UTC),
                lookback=timedelta(minutes=vargs.window),
                backfill=vargs.backfill,
                incoming_path=INCOMING_PATH
            )

            if not vargs.overwrite:
                SITE_LOGGER.info(f"Filtering new images only")
                results= filter_new_results(results, STATION, INCOMING_PATH)

            if not results:
                SITE_LOGGER.info("No new data since last execution")
                imos_logging.logging_stop(logger=SITE_LOGGER)
                continue            

            keys = [r["Key"] for r in results]
            SITE_LOGGER.info(
                f"Downloading {len(keys)} images (preview):\n%s",
                "\n".join(imos_logging.preview_list(keys)),
            )

            download_s3_results(
                results,
                BUCKET_NAME,
                s3,
                STATION,
                INCOMING_PATH
            )

            SITE_LOGGER.info(f"{STATION} images fetching successfully finished")
            imos_logging.logging_stop(logger=SITE_LOGGER)

        except Exception as e:
            
            error_message = IMOSLogging().unexpected_error_message.format(site_name=STATION)
            GENERAL_LOGGER.error(str(e), exc_info=True)
            SITE_LOGGER.error(str(e), exc_info=True)

            site_logger_file_path = imos_logging.get_log_file_path(SITE_LOGGER)
            imos_logging.logging_stop(logger=SITE_LOGGER)
            error_logger_file_path = imos_logging.rename_log_file_if_error(
                site_name=STATION,
                file_path=site_logger_file_path,
                script_name=os.path.basename(__file__).removesuffix(".py"),
                add_runtime=False)
            
            sites_error_logs.append(error_logger_file_path)

        if sites_error_logs:
            if vargs.email_alert:
                e = Email(script_name=os.path.basename(__file__),
                        email=os.getenv("EMAIL_TO"),
                        log_file_path=sites_error_logs)
                e.send()

    GENERAL_LOGGER.info("script successfully finished")
    imos_logging.logging_stop(logger=GENERAL_LOGGER)
    