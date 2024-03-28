"""USG Regulation Retriever

Open's the U.S. Government's documentation site, and downloads the list 
of regulations to the hard drive for parsing
"""

# Imports - Python Builtin
import os
from configparser import ConfigParser
from configparser import Error as ConfigParserError
import logging
from urllib.request import urlretrieve
from urllib.parse import urljoin
import re
import csv

# Imports - Third Party
from bs4 import BeautifulSoup

# Imports - Local


# Setup
logging.basicConfig(level=logging.DEBUG) # REMOVE ME LATER
logger = logging.getLogger(__name__)

def get_environment_config() -> dict[str, str]:
    """Reads the ini file

    returns the following values, as a dictionary:
    'regulation_storage_path'
    'regulation_base_url'
    'temp_dir'
    """

    # Open up the configuration
    parser = ConfigParser()
    parser.read('config.ini')

    retval = {}
    try:
        retval['regulation_storage_path'] = parser.get('Local', 'Regulation_Local_Location')
    except ConfigParserError:
        # Catch all configparser errors
        logger.error("Missing Configuration Item For "
                     "Regulation Storage Path:  Local -> "
                     "Regulation_Local_Location")
        retval['regulation_storage_path'] = "raw_regulations"  # Default Value
    logger.debug("Regulation Storage Path: %s", os.path.abspath(retval['regulation_storage_path']))

    try:
        retval['regulation_base_url'] = parser.get("Acquisition_Regulations", "Base_URL")
    except ConfigParserError:
        # Catch all configparser errors
        logger.error("Missing Configuration Item for Acquisition.gov URL: "
                     " Acquisition_Regulations -> Base_URL")
        retval['regulation_base_url'] = "https://www.acquisition.gov/content/regulations"
    logger.debug("Pulling Regulations from <%s>", retval['regulation_base_url'])

    try:
        retval['temp_dir'] = parser.get("Local", "Temp_Dir")
    except ConfigParserError:
        # Catch all configparser errors:
        logger.error("Missing Configuration Item for Temp Directory:  Local -> Temp_Dir")
        retval['temp_dir'] = "temp"
    logger.debug("Temp file path: %s", os.path.abspath(retval['temp_dir']))

    return retval

def download_documents_index(regulation_storage_path, regulation_base_url, temp_dir) -> None:
    """US Gov. Doc Retriever

    Goes to the Acquisition website, and downloads the latest copies
    of the acquisition regulations.  Parses them according to each 
    regulation.
    """

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
    # print(regulation_links)
    # print(len(regulation_links))

    regulation_dict = {}

    # have a list of a hrefs...
    for regulation_link in links:
        regulation_dict_entry = {
            'href': urljoin(regulation_base_url, regulation_link['href']),
            'title': regulation_link['title'].strip(),
            'directory': os.path.join(
                os.path.abspath(regulation_storage_path), 
                regulation_link['href'][1:]
            ),
            'abbreviation': regulation_link.text
        }
        regulation_dict[regulation_link.text] = regulation_dict_entry
        os.makedirs(regulation_dict_entry['directory'], exist_ok=True)

    # Write out an index file, or update it
    regulation_index_csv_flname = os.path.join(
        regulation_storage_path, "metadata.csv"
    )
    if os.path.exists(regulation_index_csv_flname):
        # The file exists, so we have to do line comparisons
        disk_dict = {}
        with open(regulation_index_csv_flname, mode="r", encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                disk_dict[row['abbreviation']] = row
        for reg_abbrev, reg_definition in regulation_dict.items():
            if reg_abbrev not in disk_dict:
                disk_dict[reg_abbrev] = reg_definition
        with open(regulation_index_csv_flname, mode='w', encoding='utf-8') as csvfile:
            fieldnames = ['abbreviation', 'title', 'href', 'directory',
                          'regulation_effective_date', 'last_download_date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval='')
            writer.writeheader()
            for reg_abbrev, reg_definition in disk_dict.items():
                writer.writerow(reg_definition)
    else:
        # The file does not exist, so we can just write out the csv.
        with open(regulation_index_csv_flname, mode="w", encoding='utf-8') as csvfile:
            fieldnames = ['abbreviation', 'title', 'href', 'directory',
                          'regulation_effective_date', 'last_download_date']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval='')
            writer.writeheader()
            for reg_abbrev, reg_definition in regulation_dict.items():
                writer.writerow(reg_definition)

    # print(regulation_dict)
                
def update_documents(regulation_storage_path, regulation_base_url, temp_dir) -> None:
    regulation_index_csv_filename = os.path.join(
        regulation_storage_path, "metadata.csv"
    )
    

def main() -> None:
    """Runs tests for the doc retriever"""
    logger.setLevel(logging.DEBUG)
    envconf = get_environment_config()
    download_documents_index(**envconf)
    update_documents(**envconf)


if __name__ == "__main__":
    main()
