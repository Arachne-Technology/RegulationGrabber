import os
from configparser import ConfigParser
from configparser import Error as ConfigParserError
import logging
import csv
from datetime import datetime
import re
from unidecode import unidecode

logger = logging.getLogger(__name__)


def safestring(s: str) -> str:
    s = unidecode(s)
    s = s.strip()

    # remove Non-word characters
    s = re.sub(
        r"[\N{EM DASH}\N{EN DASH}\N{HYPHEN}]", "-", s
    )  # replace all the dash lookalikes
    s = re.sub(r" - ", "-", s)  # space dash space replacement
    # s = re.sub(r"[^\w\s\.-]", "", s)  # strip anything else

    # remove runs of whitespace
    s = re.sub(r"\s+", " ", s)

    # remove runs of double dashes
    s = re.sub(r"\-\-+", "-", s)
    return s


def safepath(s: str) -> str:
    s = s.strip()
    # remove Non-word characters
    s = re.sub(
        r"[\N{EM DASH}\N{EN DASH}\N{HYPHEN}]", "-", s
    )  # replace all the dash lookalikes
    s = re.sub(r" - ", "-", s)  # space dash space replacement
    s = re.sub(r"[^\w\s\.-]", "", s)  # strip anything else
    # remove runs of whitespace
    s = re.sub(r"\s+", "-", s)
    # remove runs of double dashes
    s = re.sub(r"\-\-+", "-", s)
    return s.upper()


def get_environment_config() -> dict[str, str]:
    """Reads the ini file

    returns the following values, as a dictionary:
    'regulation_storage_path'
    'regulation_base_url'
    'temp_dir'
    'regulation_csv_file_path'
    """

    # Open up the configuration
    parser = ConfigParser()
    parser.read("config.ini")

    retval = {}
    try:
        retval["regulation_storage_path"] = parser.get(
            "Local", "Regulation_Local_Location"
        )
    except ConfigParserError:
        # Catch all configparser errors
        logger.error(
            "Missing Configuration Item For "
            "Regulation Storage Path:  Local -> "
            "Regulation_Local_Location"
        )
        retval["regulation_storage_path"] = "raw_regulations"  # Default Value
    logger.debug(
        "Regulation Storage Path: %s",
        os.path.abspath(retval["regulation_storage_path"]),
    )

    try:
        retval["regulation_base_url"] = parser.get(
            "Acquisition_Regulations", "Base_URL"
        )
    except ConfigParserError:
        # Catch all configparser errors
        logger.error(
            "Missing Configuration Item for Acquisition.gov URL: "
            " Acquisition_Regulations -> Base_URL"
        )
        retval["regulation_base_url"] = (
            "https://www.acquisition.gov/content/regulations"
        )
    logger.debug("Pulling Regulations from <%s>", retval["regulation_base_url"])

    try:
        retval["temp_dir"] = parser.get("Local", "Temp_Dir")
    except ConfigParserError:
        # Catch all configparser errors:
        logger.error(
            "Missing Configuration Item for Temp Directory:  Local -> Temp_Dir"
        )
        retval["temp_dir"] = "temp"
    logger.debug("Temp file path: %s", os.path.abspath(retval["temp_dir"]))

    try:
        retval["regulation_csv_file_path"] = os.path.abspath(
            parser.get("Local", "Regulation_CSV_File")
        )
    except ConfigParserError:
        # Catch all configparser errors:
        logger.error(
            "Missing Configuration Item for CSV File path: Local -> Regulation_CSV_File"
        )
        retval["regulation_csv_file_path"] = os.path.abspath(
            "regulations.csv"
        )  # default value
    logger.debug("CSV file: %s", retval["regulation_csv_file_path"])
    return retval


def write_regulation_dict(regulation_csv_file_path, regulation_dict) -> None:
    with open(regulation_csv_file_path, mode="w", encoding="utf-8") as csvfile:
        fieldnames = [
            "abbreviation",
            "title",
            "href",
            "directory",
            "regulation_effective_date",
            "last_download_date",
        ]
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval="")
        writer.writeheader()
        for reg_abbrev, reg_definition in regulation_dict.items():
            # don't want to mess up the original
            reg_definition_copy = reg_definition.copy()
            if "regulation_effective_date" in reg_definition_copy:
                if isinstance(
                    reg_definition_copy["regulation_effective_date"], datetime
                ):
                    reg_definition_copy["regulation_effective_date"] = (
                        datetime.strftime(
                            reg_definition_copy["regulation_effective_date"], "%Y-%m-%d"
                        )
                    )
            if "last_download_date" in reg_definition_copy:
                if isinstance(reg_definition_copy["last_download_date"], datetime):
                    reg_definition_copy["last_download_date"] = datetime.strftime(
                        reg_definition_copy["last_download_date"], "%Y-%m-%d"
                    )
            writer.writerow(reg_definition_copy)


def read_regulation_dict(regulation_csv_file_path) -> dict[str, dict]:
    disk_dict = {}
    with open(regulation_csv_file_path, mode="r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            disk_dict[row["abbreviation"]] = row
            if disk_dict[row["abbreviation"]]["regulation_effective_date"] != "":
                disk_dict[row["abbreviation"]]["regulation_effective_date"] = (
                    datetime.strptime(
                        disk_dict[row["abbreviation"]]["regulation_effective_date"],
                        "%Y-%m-%d",
                    )
                )
            if disk_dict[row["abbreviation"]]["last_download_date"] != "":
                disk_dict[row["abbreviation"]]["last_download_date"] = (
                    datetime.strptime(
                        disk_dict[row["abbreviation"]]["last_download_date"], "%Y-%m-%d"
                    )
                )
    return disk_dict
