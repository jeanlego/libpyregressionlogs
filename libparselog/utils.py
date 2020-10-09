#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

import sys
import os

from json import load as jsonLoad
from json import dumps as jsonDumps
from csv import reader as csvReader

from types import FunctionType


def colored(input_str, color, colorize):
    if colorize:
        if color == "red":
            return "\033[31m" + input_str + "\033[0m"
        if color == "green":
            return "\033[32m" + input_str + "\033[0m"
        if color == "orange":
            return "\033[33m" + input_str + "\033[0m"

    return input_str


def unload_list(tbl: OrderedDict, entry: str) -> list:
    entries = []
    # load the processing lib
    if entry in tbl:
        if isinstance(tbl[entry], str):
            entries.append(tbl[entry])
        elif isinstance(tbl[entry], (list, set)):
            for items in tbl[entry]:
                entries.append(items)
        # unload the entry from the table
        del tbl[entry]
    return entries

def strip_str(value_str):
    value_str.strip()
    while (value_str.startswith("'") and value_str.endswith("'")) or (
        value_str.startswith('"') and value_str.endswith('"')
    ):
        value_str = value_str[1:-1]
        value_str.strip()

    return value_str


def sanitize_value(value):
    # convert to a number if possible
    if isinstance(value, (int, bool)):
        return value

    if isinstance(value, (float)):
        if value % 1.0 == 0.0:
            value = int(value)
        return value

    if isinstance(value, str):
        # tidy the input
        value = " ".join(value.split())

        if value in ("False", "false"):
            return False

        if value in ("True", "true"):
            return True

        if value in ("NaN", "nan", "NAN"):
            return float("NaN")

        if value in ("inf", "INF"):
            return float("inf")

        if value in ("-inf", "-INF"):
            return float("-inf")

        try:
            # try to convert but gracefully fail otherwise
            value = float(value)
            return sanitize_value(value)
        except ValueError:
            return str(value)

    if isinstance(value, (list, set)):
        for i in range(len(value)):
            value[i] = sanitize_value(value[i])
        return value

    if isinstance(value, dict):
        for key in value:
            value[key] = sanitize_value(value[key])
        return value

    print("Invalid data type for comparison")
    sys.exit(255)

def dump_csv(driver, output_dict, file=sys.stdout):
    # dump csv to stdout
    header_line = []
    result_lines = []
    for keys in output_dict:
        result_lines.append(list())

    for header in driver.get_header_list():
        if driver.is_multivalued(header):
            continue

        # figure out the pad
        pad = len(str(header).strip())
        for keys in output_dict:
            if header in output_dict[keys]:
                pad = max(pad, len(str(output_dict[keys][header]).strip()))

        header_line.append("{0:<{1}}".format(str(header).strip(), pad))
        index = 0
        for keys in output_dict:
            if header in output_dict[keys]:
                result_lines[index].append(
                    "{0:<{1}}".format(str(output_dict[keys][header]).strip(), pad)
                )
                index += 1

    # now write everything to the file:
    print(", ".join(header_line), file=file)
    for row in result_lines:
        print(", ".join(row), file=file)


def dump_json(output_dict, file=sys.stdout):
    print(jsonDumps(output_dict, indent=4), file=file)


def load_json(file_name):
    file_dict = OrderedDict()
    with open(file_name, newline="") as json_file:
        file_dict = jsonLoad(json_file, object_pairs_hook=OrderedDict)

    return file_dict


def load_csv(csv_file_name):
    header = []
    file_dict = []
    with open(csv_file_name, newline="") as csvfile:
        is_header = True
        csv_reader = csvReader(csvfile)
        for row in csv_reader:
            if row is not None and len(row) > 0:
                input_row = OrderedDict()
                file_dict.append(input_row)
                index = 0
                for element in row:
                    element = " ".join(element.split())
                    if is_header:
                        header.append(element)
                    else:
                        input_row[header[index]] = sanitize_value(element)
                    index += 1

                is_header = False

    return file_dict


def load_fn_table(file_list):
    current_dir = os.getcwd()
    function_table = {}

    if file_list is not None:
        if isinstance(file_list, str):
            directory = os.path.dirname(file_list)
            file_name = os.path.basename(file_list)

            # strip the extension
            ext_split = file_name.rsplit(".",1)
            if len(ext_split[0]) > 0:
                file_name = ext_split[0]

            # add this path here to find other include
            sys.path.append(directory)
            if directory != "":
                os.chdir(directory)
            module = __import__(file_name).__dict__
            os.chdir(current_dir)

            for items in module:
                if isinstance(module[items], FunctionType):
                    function_table[items] = module[items]

        elif isinstance(file_list, (list, set)):
            for files in file_list:
                function_table.update(load_fn_table(files))
    return function_table
