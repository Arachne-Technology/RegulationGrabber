"""USG Regulation Retriever

Open's the U.S. Government's documentation site, and downloads the list 
of regulations to the hard drive for parsing
"""

# Imports - Python Builtin
import os
from configparser import ConfigParser
from configparser import Error as ConfigParserError
import logging
from urllib.request import Request, urlretrieve, urlopen
import re

# Imports - Third Party
from bs4 import BeautifulSoup

# Imports - Local


# Setup
logging.basicConfig(level=logging.DEBUG) # REMOVE ME LATER
logger = logging.getLogger(__name__)


def download_documents() -> None:
    """US Gov. Doc Retriever

    Goes to the Acquisition website, and downloads the latest copies
    of the acquisition regulations.  Parses them according to each 
    regulation.
    """

    # Open up the configuration
    parser = ConfigParser()
    parser.read('config.ini')

    try:
        regulation_storage_path = parser.get('Local', 'Regulation_Local_Location')
    except ConfigParserError:
        # Catch all configparser errors
        logger.error("Missing Configuration Item For "
                     "Regulation Storage Path:  Local -> "
                     "Regulation_Local_Location")
        regulation_storage_path = "raw_regulations"  # Default Value
    logger.info("Regulation Storage Path: %s", os.path.abspath(regulation_storage_path))

    try:
        regulation_base_url = parser.get("Acquisition_Regulations", "Base_URL")
    except ConfigParserError:
        # Catch all configparser errors
        logger.error("Missing Configuration Item for Acquisition.gov URL: "
                     " Acquisition_Regulations -> Base_URL")
        regulation_base_url = "https://www.acquisition.gov/content/regulations"
    logger.info("Pulling Regulations from <%s>", regulation_base_url)

    try:
        temp_dir = parser.get("Local", "Temp_Dir")
    except ConfigParserError:
        # Catch all configparser errors:
        logger.error("Missing Configuration Item for Temp Directory:  Local -> Temp_Dir")
        temp_dir = "temp"
    logger.debug("Temp file path: %s", os.path.abspath(temp_dir))

    # Make temp dir if needed
    if not os.path.isdir(temp_dir):
        os.makedirs(temp_dir)

    # download the acquisition.gov page
    # req = Request(regulation_base_url, headers={'User-Agent': 'Mozilla/5.0'})
    acq_index_flname = 'acq_index.html'
    acq_index_flpath = os.path.join(temp_dir, acq_index_flname)
    urlretrieve(regulation_base_url, acq_index_flpath)
    with open(acq_index_flpath, encoding='utf-8') as page:
        contents = page.read()
        # print(contents)

    # import the index into beautiful soup
    soup = BeautifulSoup(contents, "lxml")
    # print(soup.prettify())
    regulation_links = []
    reg_sections = soup.find_all("div", {"class":"supreg"})
    for reg_section in reg_sections:
        # logger.debug(reg_section)
        links = reg_section.find_all("a", {'title':True})
        regulation_links += links
    print(regulation_links)
    print(len(regulation_links))


def main() -> None:
    """Runs tests for the doc retriever"""
    logger.setLevel(logging.DEBUG)
    download_documents()


if __name__ == "__main__":
    main()
