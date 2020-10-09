
# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

import sys
import os

from typing import Union, Tuple, Any
from configparser import ConfigParser, ExtendedInterpolation
from json import loads as jsonLoads

from libparselog.utils import (
    sanitize_value,
    strip_str
)

class Toml(OrderedDict):

    def _preproc(self, file_path: str) -> str:
        current_dir = os.getcwd()
        directory = os.path.dirname(file_path)
        # add this path here to find other include
        sys.path.append(directory)
        if directory != "":
            os.chdir(directory)
        str = ""

        with open(file_path) as current_file:
            for line in current_file:
                if line.startswith("#include "):
                    # import the next file in line
                    next_file = line.strip("#include").strip()
                    str += self._preproc(next_file)
                else:
                    # strip comments
                    clean_line = line.split("#")[0]
                    str += clean_line + "\n"

        os.chdir(current_dir)
        return str


    def _parse(self, file: str) -> OrderedDict:
        str = self._preproc(os.path.abspath(file))

        # raw configparse
        parser = ConfigParser(
            dict_type=OrderedDict,
            allow_no_value=False,
            delimiters=("="),
            comment_prefixes=("#"),
            strict=False,
            empty_lines_in_values=True,
            interpolation=ExtendedInterpolation(),
            default_section="DEFAULT",
        )

        # read as a simple INI file
        parser.read_string(str)

        # we are gonna build a json string out of it since it
        # is a relatively simple file, and our values are
        # always json strings
        json_entries = []
        for _section in parser.sections():
            # make it a json string
            section = '"' + strip_str(_section) + '"'
            key_entries = []
            for _option in parser.options(_section):
                # make it a json string
                option = '"' + strip_str(_option) + '"'
                value = parser.get(_section, _option, fallback=None)
                if value is None:
                    key_entries.append(option + ": null")
                else:
                    key_entries.append(option + ": " + value)
            json_entries.append(section + ": {\n\t\t" + ",\n\t\t".join(key_entries) + "\n\t}")
        json_entry = "{\n" + ", ".join(json_entries) + "\n}"

        # escape the escape character for json
        json_entry = json_entry.replace("\\", "\\\\")
        json_dict = jsonLoads(json_entry, object_pairs_hook=OrderedDict)

        json_dict = sanitize_value(json_dict)

        return json_dict

    def __init__(self, file_list: list) -> OrderedDict:
        super()
        for files in file_list:
            new_dict = self._parse_files)
            for section in new_dict:
                # we simply override with the new arrivals
                self[section] = new_dict[section]

    def assertion(self, condition: bool, entry: str, key: str, message: str):

        if not condition:
            print("Invalid entry in  " + key + ' in ["' + entry + '"]' + message)
            sys.exit(255)

    def assert_type(
        self,
        conf: OrderedDict,
        entry: str,
        key: str,
        type_list: Union[type, Tuple[Union[type, Tuple[Any, ...]], ...]],
    ):
        msg = "is not of type ("
        try:
            msg += ", ".join([types.__name__ for types in type_list])
        except TypeError:
            msg += type_list.__name__
        msg += ")"

        self._assertion(isinstance(conf[entry][key], type_list), entry, key, msg)

    def unload_entry(self, entry: str) -> OrderedDict:
        entry_dict = OrderedDict()
        # load the processing lib
        if entry in self:
            entry_dict = self[entry]
            del self[entry]

        return entry_dict

        
