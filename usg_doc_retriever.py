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
from datetime import datetime

# Imports - Third Party
from bs4 import BeautifulSoup

# Imports - Local


# Setup
logging.basicConfig(level=logging.DEBUG, filename='logs.txt', filemode='w') # REMOVE ME LATER
logger = logging.getLogger(__name__)

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

    try:
        retval['regulation_csv_file_path'] = os.path.abspath(parser.get("Local", "Regulation_CSV_File"))
    except ConfigParserError:
        # Catch all configparser errors:
        logger.error("Missing Configuration Item for CSV File path: Local -> Regulation_CSV_File")
        retval['regulation_csv_file_path'] = os.path.abspath('regulations.csv') # default value
    logger.debug("CSV file: %s", retval['regulation_csv_file_path'])
    return retval

def write_regulation_dict(regulation_csv_file_path, regulation_dict) -> None:
    with open(regulation_csv_file_path, mode="w", encoding='utf-8') as csvfile:
        fieldnames = ['abbreviation', 'title', 'href', 'directory',
                        'regulation_effective_date', 'last_download_date']
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames, restval='')
        writer.writeheader()
        for reg_abbrev, reg_definition in regulation_dict.items():
            # don't want to mess up the original
            reg_definition_copy = reg_definition.copy()
            if 'regulation_effective_date' in reg_definition_copy:
                if isinstance(reg_definition_copy['regulation_effective_date'],datetime):
                    reg_definition_copy['regulation_effective_date'] = datetime.strftime(
                        reg_definition_copy['regulation_effective_date'],"%Y-%m-%d"
                    )
            if 'last_download_date' in reg_definition_copy:
                if isinstance(reg_definition_copy['last_download_date'],datetime):
                    reg_definition_copy['last_download_date'] = datetime.strftime(
                        reg_definition_copy['last_download_date'],"%Y-%m-%d"
                    )
            writer.writerow(reg_definition_copy)

def read_regulation_dict(regulation_csv_file_path) -> dict[str,dict]:
    disk_dict = {}
    with open(regulation_csv_file_path, mode='r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            disk_dict[row['abbreviation']] = row
            if disk_dict[row['abbreviation']]['regulation_effective_date'] != '':
                disk_dict[row['abbreviation']]['regulation_effective_date'] = \
                    datetime.strptime(
                        disk_dict[row['abbreviation']]['regulation_effective_date'],"%Y-%m-%d"
                    )
            if disk_dict[row['abbreviation']]['last_download_date'] != '':
                disk_dict[row['abbreviation']]['last_download_date'] = \
                    datetime.strptime(
                        disk_dict[row['abbreviation']]['last_download_date'],"%Y-%m-%d"
                    )
    return disk_dict

def download_documents_index(regulation_storage_path, regulation_base_url, 
                             temp_dir, regulation_csv_file_path, **kwargs) -> None:
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
            # Sanitize the abbreviations...
            'abbreviation': ''.join(char for char in regulation_link.text if char.isalnum())
        }
        regulation_dict[regulation_dict_entry['abbreviation']] = regulation_dict_entry
        os.makedirs(regulation_dict_entry['directory'], exist_ok=True)

    # Write out an index file, or update it
    if os.path.exists(regulation_csv_file_path):
        # The file exists, so we have to do line comparisons
        disk_dict = read_regulation_dict(regulation_csv_file_path=regulation_csv_file_path)
        for reg_abbrev, reg_definition in regulation_dict.items():
            if reg_abbrev not in disk_dict:
                disk_dict[reg_abbrev] = reg_definition
        write_regulation_dict(regulation_csv_file_path=regulation_csv_file_path,
                              regulation_dict=disk_dict)
    else:
        # The file does not exist, so we can just write out the csv.
        write_regulation_dict(regulation_csv_file_path=regulation_csv_file_path,
                              regulation_dict=regulation_dict)

    # print(regulation_dict)

def update_document_dates(regulation_base_url, regulation_csv_file_path,
                      **kwargs) -> None:
    regulation_dict = read_regulation_dict(regulation_csv_file_path=regulation_csv_file_path)
    for reg_abbrev, reg_definition in regulation_dict.items():
        # grab the index page, to see if the effective date is newer
        reg_index_flname = os.path.join(
            reg_definition['directory'],
            reg_abbrev + "_index.html"
        )
        urlretrieve(reg_definition['href'], filename=reg_index_flname)
        with open(reg_index_flname, mode='r', encoding='utf-8') as htmlfile:
            contents = htmlfile.read()
        soup = BeautifulSoup(contents, 'lxml')
        
        tabularformat = [
            'FAR','DFARS','DFARSPGI','AFARS','DAFFARS','DAFFARSMP',
            'DARS','DLAD','NMCARS','SOFARS','TRANSFARS', 'GSAMR'
        ]
        h4format = [
            'AGAR', 'AIDAR', 'CAR', 'DEAR', 'DIAR', 'DOLAR', 'DOSAR',
            'DTAR', 'EDAR', 'EPAAR', 'FEHBAR', 'HHSAR', "HSAR", 'HUDAR',
            'IAAR', 'JAR', 'LIFAR', 'NFS', 'NRCAR', 'TAR', 'VAAR'
        ]
        if  reg_abbrev in tabularformat:
            rightrow = False
            for tr in soup.find_all('tr'):
                all_th = tr.find_all('th')
                if all_th:
                    try:
                        all_heads = [th.text for th in all_th]
                        date_idx = all_heads.index('Effective Date')
                        dita_idx = all_heads.index('DITA')
                        rightrow = True
                        continue
                    except Exception:
                        # wrong row
                        continue
                if rightrow:
                    all_td = tr.find_all('td')
                    effdate = datetime.strptime(
                        all_td[date_idx].text,
                        "%m/%d/%Y"
                    )
                    dita_link = urljoin(
                        regulation_base_url, 
                        all_td[dita_idx].find_all('a')[0]['href']
                    )
                    # logger.debug("%s - %s - %s",reg_abbrev, effdate, dita_link)
                    rightrow = False
        elif reg_abbrev == 'Chapter99CAS':
            ps = soup.find_all('p')
            for p in ps:
                match = re.search(r'Last Update: (\d{2}.+\d{4})', p.text)
                if match:
                    effdate = datetime.strptime(match.group(1), "%d %B %Y")
        elif reg_abbrev in h4format:
            date_candidates = soup.select('#effective-date')
            for candidate in date_candidates:
                matches = re.search(r'\d{2}/\d{2}/\d{4}', candidate.text)
                if matches:
                    effdate = datetime.strptime(
                        matches.group(0),
                        "%m/%d/%Y"
                    )
        else:
            logger.error("Unrecognized regulation format: %s",reg_abbrev)
        # print(reg_abbrev, effdate)
        # regulation_dict[reg_abbrev]['regulation_effective_date'] = effdate
        reg_definition['regulation_effective_date'] = effdate
        write_regulation_dict(regulation_csv_file_path=regulation_csv_file_path, 
                              regulation_dict=regulation_dict)

def safepath(s: str) -> str:
    s = s.strip()
    # remove Non-word characters
    s = re.sub(r'[\N{EM DASH}\N{EN DASH}\N{HYPHEN}]','-',s) # replace all the dash lookalikes
    s = re.sub(r' - ', '-', s) # space dash space replacement
    s = re.sub(r'[^\w\s\.-]', '', s) # strip anything else
    # remove runs of whitespace
    s = re.sub(r'\s+','-',s)
    # remove runs of double dashes
    s = re.sub(r'\-\-+','-',s)
    return s.upper()
    
def update_local_documents(regulation_csv_file_path, regulation_base_url, **kwargs) -> None:
    regulation_dict = read_regulation_dict(regulation_csv_file_path=regulation_csv_file_path)
    for reg_abbrev, reg_dictionary in regulation_dict.items():
        if( reg_dictionary['last_download_date'] == '' or reg_dictionary['last_download_date'] < reg_dictionary['regulation_effective_date']):
            # our local copy has either not been made, or is out of date.
            logger.debug("Have to update %s", reg_abbrev)
            
            # open the file with soup
            reg_index_flname = os.path.join(
                reg_dictionary['directory'],
                reg_abbrev + "_index.html"
            )
            with open(reg_index_flname, mode='r', encoding='utf-8') as htmlfile:
                contents = htmlfile.read()
            soup = BeautifulSoup(contents, 'lxml')
            tablerows = soup.find_all('tr')

            tablular1 = [
                'FAR', 'DFARS', 'AFARS', 'DAFFARS', 'NMCARS', 'SOFARS', 'TRANSFARS',
                'GSAMR', 'DARS', 'DLAD'
            ]
            nodeformat = [
                'Chapter99CAS', 'AGAR', 'AIDAR', 'CAR', 'DEAR', 'DIAR', 'DOLAR', 'DOSAR', 'DTAR', 'EDAR', 'EPAAR', 'FEHBAR', 'HHSAR', 'HSAR', 'HUDAR', 'IAAR', 'JAR', 'LIFAR', 'NFS', 'NRCAR', 'TAR', 'VAAR'
            ]
            if reg_abbrev in tablular1:
                for tablerow in tablerows:
                    tabledata = tablerow.find_all('td')
                    if len(tabledata) > 0:
                        for tableelement in tabledata:
                            for link in tableelement.find_all('a'):
                                if 'title' in link.attrs:
                                    match = re.match(r'print part (.+)', link['title'].lower())
                                    if match:
                                        flname = os.path.join(reg_dictionary['directory'], 'pages', reg_abbrev + '-' + safepath(match.group(1)) + '.html')
                                        if(not os.path.exists(os.path.dirname(flname))):
                                            os.mkdir(os.path.dirname(flname))
                                        dlurl = urljoin(regulation_base_url, link['href'])
                                        logger.debug('Found section - %s-%s : %s', reg_abbrev, flname, dlurl)
                                        urlretrieve(dlurl, flname)
                reg_dictionary['last_download_date'] = datetime.now()

            elif reg_abbrev in nodeformat:
                for tablerow in tablerows:
                    tabledata = tablerow.find_all('td')
                    if len(tabledata) > 0:
                        partid = ''
                        for tableelement in tabledata:
                            if tableelement.text.strip() != '':
                                match = re.match(r'part[s]* (\d+[\-]*.+)', tableelement.text.strip().lower())
                                if match:
                                    partid = match.group(1)
                                else:
                                    match = re.match(r'append[\S]*\s+(.+)',tableelement.text.strip().lower())
                                    if match:
                                        partid = match.group(0)
                            for link in tableelement.find_all('a'):
                                if 'title' in link.attrs:
                                    match = re.match(r'print node .+', link['title'].lower())
                                    if match:
                                        flname = os.path.join(reg_dictionary['directory'], 'pages', reg_abbrev + '-' + safepath(partid) + '.html')
                                        if(not os.path.exists(os.path.dirname(flname))):
                                            os.mkdir(os.path.dirname(flname))
                                        dlurl = urljoin(regulation_base_url, link['href'])
                                        logger.debug('Found section - %s-%s : %s', reg_abbrev, flname, dlurl)
                reg_dictionary['last_download_date'] = datetime.now()
            elif reg_abbrev == 'DFARSPGI':
                for tablerow in tablerows:
                    tabledata = tablerow.find_all('td')
                    if len(tabledata) > 0:
                        for tableelement in tabledata:
                            for link in tableelement.find_all('a'):
                                if 'title' in link.attrs:
                                    match = re.match(r'Print PGI Part (.+)', link['title'])
                                    if match:
                                        flname = os.path.join(reg_dictionary['directory'], 'pages', reg_abbrev + '-' + safepath(match.group(1)) + '.html')
                                        if(not os.path.exists(os.path.dirname(flname))):
                                            os.mkdir(os.path.dirname(flname))
                                        dlurl = urljoin(regulation_base_url, link['href'])
                                        logger.debug('Found section - %s-%s : %s', reg_abbrev, flname, dlurl)
                reg_dictionary['last_download_date'] = datetime.now()
            elif reg_abbrev == 'DAFFARSMP':
                for tablerow in tablerows:
                    tabledata = tablerow.find_all('td')
                    if len(tabledata) > 0:
                        for tableelement in tabledata:
                            for link in tableelement.find_all('a'):
                                if 'title' in link.attrs:
                                    match = re.match(r'Print (.+)', link['title'])
                                    if match:
                                        flname =  os.path.join(reg_dictionary['directory'], 'pages', reg_abbrev + '-' + safepath(match.group(1)) + '.html')
                                        if(not os.path.exists(os.path.dirname(flname))):
                                            os.mkdir(os.path.dirname(flname))
                                        dlurl = urljoin(regulation_base_url, link['href'])
                                        logger.debug('Found section - %s-%s : %s', reg_abbrev, flname, dlurl)
                reg_dictionary['last_download_date'] = datetime.now()
        else:
            logger.debug("Regulation %s is already at latest version - no updates to do", reg_abbrev)
    write_regulation_dict(regulation_csv_file_path=regulation_csv_file_path, regulation_dict=regulation_dict)

def main() -> None:
    """Runs tests for the doc retriever"""
    logger.setLevel(logging.DEBUG)
    envconf = get_environment_config()
    download_documents_index(**envconf)
    update_document_dates(**envconf)
    update_local_documents(**envconf)


if __name__ == "__main__":
    main()
