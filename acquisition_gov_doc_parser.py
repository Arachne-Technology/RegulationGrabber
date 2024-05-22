"""USG Regulation Parser - Acquisition.gov requirements

Opens a set of regulations that have been downloaded to the hard drive, and 
parses them for putting into a vectorstore for later RAG use.
"""

# Imports - Python Builtin
import os
import logging
from urllib.request import urlretrieve
from urllib.parse import urljoin
import re
import csv
from datetime import datetime
import glob
import json
import jsonlines

# Imports - Third Party
from bs4 import BeautifulSoup

# Imports - Local
from utils import (
    get_environment_config,
    write_regulation_dict,
    read_regulation_dict,
    safepath,
    safestring,
)

# Setup
logging.basicConfig(
    level=logging.DEBUG, filename="logs.txt", filemode="w"
)  # REMOVE ME LATER
logger = logging.getLogger(__name__)


def simplify_documents(Regulation_CSV_File):
    all_regulation_dict = read_regulation_dict(Regulation_CSV_File)
    for reg_abbreviation, reg_dictionary in all_regulation_dict.items():
        reg_folder = os.path.join(reg_dictionary["directory"], "pages")
        valid_extensions = ".html"  # for now, might change later.
        files = [
            os.path.abspath(os.path.join(reg_folder, fn))
            for fn in os.listdir(reg_folder)
            if any(fn.endswith(ext) for ext in valid_extensions)
        ]
        for file in files:
            logger.debug("Dealing with %s", file)
            with open(file, mode="r", encoding="utf-8") as reghtmlfile:
                soup = BeautifulSoup(reghtmlfile.read(), "lxml")
            print(f"#############   Working {file}   ############")
            parse_folder = os.path.join(reg_dictionary["directory"], "pages2")
            if not os.path.isdir(parse_folder):
                os.mkdir(parse_folder)
            parseflname = os.path.join(
                parse_folder, os.path.splitext(os.path.basename(file))[0] + ".json"
            )
            linesflname = os.path.join(
                parse_folder, os.path.splitext(os.path.basename(file))[0] + ".jsonl"
            )
            lineslist = []
            with open(
                parseflname,
                mode="w",
                encoding="utf-8",
            ) as outfile:
                logger.debug("writing %s", parseflname)
                # for string in soup.strings:
                #     string = string.strip()
                #     if len(string) > 0:
                #         outfile.write(string + os.linesep)
                title_headings = ["title"]
                section_headings = [f"h{n}" for n in range(1, 7)]
                paragraph_containters = ["p"]
                # content_containers = [
                #     "a",
                #     "em",
                #     "ol",
                #     "ul",
                #     "li",
                #     "td",
                #     "tr",
                #     "table",
                #     "span",
                #     "strong",
                # ]
                # list_of_dicts = []
                heading_contents_dict = {}
                if soup.title:
                    current_title = (
                        reg_abbreviation + " " + safestring(str(soup.title.string))
                    )
                heading_contents_dict["doctitle"] = current_title
                heading_contents_dict["regulation_abbreviation"] = reg_abbreviation
                heading_contents_dict["regulation_name"] = reg_dictionary["title"]
                current_heading = ""
                current_paragraph = ""
                for tag in soup.find_all():
                    if tag.name in section_headings:
                        # keep track of our current heading
                        current_heading = safestring(soup_text_helper(tag))
                    elif tag.name in paragraph_containters:
                        # if we are a paragraph container, see if we have sub-paragraph containers
                        # - we do not want to parse sub paragraph containers twice
                        current_paragraph = safestring(soup_text_helper(tag))
                        if len(current_paragraph) > 10:  # don't keep trivial sentances
                            # list_of_dicts.append(
                            #     {
                            #         "title": current_title,
                            #         "heading": current_heading,
                            #         "paragraph": current_paragraph,
                            #     }
                            # )
                            if current_heading in heading_contents_dict:
                                # add to existing content
                                heading_contents_dict[current_heading] += (
                                    os.linesep + current_paragraph
                                )
                                lineslist[-1]["content"] = (
                                    lineslist[-1]["content"]
                                    + os.linesep
                                    + current_paragraph
                                )
                            else:
                                heading_contents_dict[current_heading] = (
                                    current_paragraph
                                )
                                lineslist.append(
                                    {
                                        "reg_abbreviation": heading_contents_dict[
                                            "regulation_abbreviation"
                                        ],
                                        "reg_name": heading_contents_dict[
                                            "regulation_name"
                                        ],
                                        "doctitle": heading_contents_dict["doctitle"],
                                        "title": current_title,
                                        "heading": current_heading,
                                        "content": current_paragraph,
                                    }
                                )

                json.dump(heading_contents_dict, outfile)
            with jsonlines.open(linesflname, mode="w") as outfile:
                outfile.write_all(lineslist)

            htmlflname = os.path.join(
                parse_folder, os.path.splitext(os.path.basename(file))[0] + ".html"
            )
            with open(
                htmlflname,
                mode="wb",
            ) as htmloutfile:
                logger.debug("writing %s", htmlflname)
                htmloutfile.write(soup.prettify("utf-8"))
            print("done")


def soup_text_helper(soup):
    retstring = "".join(soup.strings)
    return retstring.strip()


def simplify_documents_helper(soup, child):
    NotImplemented


def main():
    env_config = get_environment_config()
    simplify_documents(Regulation_CSV_File=env_config["regulation_csv_file_path"])


if __name__ == "__main__":
    main()
