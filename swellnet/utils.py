import os
import sys
from datetime import datetime, timezone
import logging
import re
import argparse

import pickle
# from netCDF4 import Dataset
import pandas as pd
import numpy as np
from dotenv import load_dotenv, parser


GENERAL_LOGGER = logging.getLogger("general_logger")
SITE_LOGGER = logging.getLogger("site_logger")

load_dotenv()

def args_auswaves_processing():
    """
    Returns the script arguments

        Parameters:

        Returns:
            vargs (obj): input arguments
    """
    parser = argparse.ArgumentParser(description='Creates NetCDF files.\n '
                                     'Prints out the path of the new locally generated NetCDF file.')
    
    # parser.add_argument('-o', '--output-path', dest='output_path', type=str, default=None,
    #                     help="output directory of netcdf file",
    #                     required=True)
    
    # parser.add_argument('-i', '--incoming-path', dest='incoming_path', type=str, default=None,
    #                     help="directory to store netcdf file to be pushed to AODN",
    #                     required=True)

    parser.add_argument('-w', '--window', dest='window', type=str, default=5,
                        help="desired window from present backwards to be processed and qualified. Default to 24, please check argument --window-unit for the right desired unit.",
                        required=False)


    def parse_site_list(value):
        return [site.strip() for site in value.split(',') if site.strip()]

    parser.add_argument(
        '-sp', '--site-to-process',
        dest='site_to_process',
        type=parse_site_list,
        default=None,
        help="Comma-separated list of sites to be processed (e.g., site1,site2,site3). A single site is also valid.",
        required=False
    )
    
    parser.add_argument('-e', '--email-alert', dest='email_alert', action="store_true",
                        help="toggle email alert.",
                        required=False)
    
    parser.add_argument('-ow', '--overwrite', dest='overwrite', action="store_true",
                        help="store everythin fetched, disregarding previously downloaded images",
                        required=False)
    
    # parser.add_argument('-b', '--backfill', dest='backfill', action="store_true",
    #                     help="backfill all paginated data",
    #                     required=False)
    
    parser.add_argument('-b', '--backfill', dest='backfill', type=str, default=None,
                        help="backfill images. 'all' to download all images from source, 'backfill' to download all images after latest downloaded",
                        required=False)


    vargs = parser.parse_args()

    if vargs.backfill:
        if vargs.backfill not in ('all', 'backfill'):
            raise ValueError(f"Invalid value for --backfill|-b: {('all', 'backfill')} available. Please see argument help.")
        vargs.backfill = str(vargs.backfill)
    else:
        vargs.backfill = 'disabled'
    
    if vargs.window:
        try:
            vargs.window = int(vargs.window)
        except ValueError:
            raise ValueError(
                f"Invalid value for --window: '{vargs.window}'. Must be an integer."
            )

    if vargs.email_alert:
        vargs.email_alert = True
    else:
        vargs.email_alert = False

    if vargs.overwrite:
        vargs.overwrite = True
    else:
        vargs.overwrite = False    

    return vargs


class IMOSLogging:
    unexpected_error_message = "An unexpected error occurred when processing {site_name}\n Please check the site log for details"

    def __init__(self):
        pass

    @staticmethod
    def generate_general_logger(incomming_path, script_name):

        general_log_file = os.path.join(
                incomming_path,
                "logs",
                f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_general_{script_name}.log"
            )
    
        return IMOSLogging().logging_start(logger_name="general_logger", logging_filepath=general_log_file)

    @staticmethod
    def generate_site_logger(incomming_path, site_name, script_name):
     
        site_log_file = os.path.join(
            incomming_path,
            site_name, 
            "logs", 
            f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{site_name.upper()}_{script_name}.log")
        
        return IMOSLogging().logging_start(logger_name="site_logger", logging_filepath=site_log_file)

    @staticmethod
    def preview_list(items, head=3, tail=3):
        if len(items) <= head + tail:
            return items
        return items[:head] + ["..."] + items[-tail:]


    def logging_start(self, logging_filepath, logger_name="general_logger", level=logging.INFO):
        """
        Start logging using the Python logging library.
        Parameters:
            logger_name (str): Name of the logger to create or retrieve.
            level (int): Logging level (default: logging.INFO).
        Returns:
            logger (logging.Logger): Configured logger instance.
        """
        self.logging_filepath = logging_filepath

        if not os.path.exists(os.path.dirname(self.logging_filepath)):
            os.makedirs(os.path.dirname(self.logging_filepath))

        self.logger = logging.getLogger(logger_name)

        if not self.logger.hasHandlers():
            # self.logger.setLevel(level)

            # handler = logging.FileHandler(self.logging_filepath, mode="w")
            # handler.setLevel(level)

            # formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            # handler.setFormatter(formatter)

            # self.logger.addHandler(handler)

            self.logger.setLevel(level)

            # File handler (writes to file)
            file_handler = logging.FileHandler(self.logging_filepath, mode="w")
            file_handler.setLevel(level)

            # Stream handler (prints to CLI)
            stream_handler = logging.StreamHandler(sys.stdout)
            stream_handler.setLevel(level)

            # Formatter
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            file_handler.setFormatter(formatter)
            stream_handler.setFormatter(formatter)

            # Add both handlers
            self.logger.addHandler(file_handler)
            self.logger.addHandler(stream_handler)

        return self.logger

    def logging_stop(self, logger):
        """Close logging handlers for the current logger."""
        handlers = list(logger.handlers)
        for handler in handlers:
            logger.removeHandler(handler)
            handler.flush()
            handler.close()

    def get_log_file_path(self, logger):
        return logger.handlers[0].baseFilename
    
    def rename_log_file_if_error(self, site_name: str, file_path, script_name: str, add_runtime: bool = True):
        site_name = site_name.upper()
        runtime = datetime.now().strftime("%Y%m%dT%H%M%S")
        pattern = f"{site_name}_{script_name}"
        new_name = "ERROR_" + f"{site_name}_{script_name}"
        if add_runtime:
            new_name += f"_{runtime}"

        new_file_name = re.sub(pattern, new_name, file_path)
        if os.path.exists(new_file_name):
            os.replace(file_path, new_file_name)
        else:
            os.rename(file_path, new_file_name)
        GENERAL_LOGGER.info(f"{site_name} log file renamed as {new_file_name}")

        return os.path.join(file_path, new_file_name)

    def rename_push_log_if_error(self, file_path: str, add_runtime: bool = True):
        runtime = datetime.now().strftime("%Y%m%dT%H%M%S")
        pattern = "aodn_ftp_push"
        new_name = f"ERROR_aodn_ftp_push"
        if add_runtime:
            new_name += f"_{runtime}"

        new_file_name = re.sub(pattern, new_name, file_path)
        if os.path.exists(new_file_name):
            os.replace(file_path, new_file_name)
        else:
            os.rename(file_path, new_file_name)

        return os.path.join(file_path, new_file_name)

