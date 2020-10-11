# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict, deque

import sys
import os

from typing import Union, Tuple, Any
from configparser import ConfigParser, ExtendedInterpolation
from json import loads as jsonLoads

from libparselog.utils import ( 
    sanitize_value,
    strip_str,
    assertion
)


class Toml:
    """[summary]
    Toml namespace, the basic loads and load are offered to read extended toml format str and from a file
    Some parameters are ofered at initilization time
    """
    default_str: str = "DEFAULT"
    commment_prefixes: str = "#"
    include_cmd: str = "#include"
    search_path: str = ""

    def __init__(
        self,
        default="DEFAULT",
        comment="#",
        include="#include",
        path=""
    ):
        """[summary]

        Args:
            default (str, optional): [description]. Defaults to "DEFAULT".
            comment (str, optional): [description]. Defaults to "#".
            include (str, optional): [description]. Defaults to "#include".
            path (str, optional): [description]. Defaults to "".
        """
        self.default_str = default
        self.commment_prefixes = comment
        self.include_cmd = include
        self.search_path = path

    def _flatten_toml_string(self, content: str, local_search_path: str) -> str:
        """Read a toml string, but extends it by parsing $include to include other Toml files
        The next Toml file is inserted in place.

        Args:
            content (str): the Toml string
            local_search_path (str, optional): The path to look in for file_path. Defaults to self.search_path.

        Returns:
            str: the flattend toml file
        """
        output_str = ""
        for line in content:
            if line.startswith(self.include_cmd + " "):
                # import the next file in line
                next_file = line.strip(self.include_cmd).strip()
                output_str += self._flatten_toml_file(next_file, local_search_path)

        return output_str

    def _flatten_toml_file(self, file_path: str, local_search_path: str) -> str:
        """preprocess a toml str, this flatens the toml str an does the necessary imports
        unlike the basic Toml standard, this is extended to allow to #include other toml files
        the inclusion search uses a stack, every include pushes its working directory on the stack
        and if the file isnt found there, look up the stack

        Args:
            file_path (str): the file to open for parsing
            local_search_path (str, optional): The path to look in for file_path. Defaults to self.search_path.

        Returns:
            str: the flattened toml file
        """
        # stash the current working directory at the front of the search list
        local_search_path = os.getcwd() + ":" + local_search_path

        # initialize the return value
        content: str = ""

        # start the lookup for the file from the top of the stack
        for paths in local_search_path.split(':'):
            if os.path.exists(paths + file_path):
                # extract the directory
                directory = os.path.dirname(file_path)
                if directory != "":
                    os.chdir(directory)

                # read it as a string and flatten it
                with open(file_path) as current_file:
                    content = self._flatten_toml_string(current_file, local_search_path)

                # get back to the previous path and pop it
                previous_dir, local_search_path = local_search_path.split(':', 1)
                os.chdir(previous_dir)

                # we stop at the first find
                break

        return content

    def _load_flatened_toml(self, flattened_toml: str, dest: OrderedDict = None) -> OrderedDict:
        """[summary]

        Args:
            flattened_toml (str): [description]
            dest (OrderedDict, optional): [description]. Defaults to None.

        Returns:
            OrderedDict: [description]
        """
        # initialize our return value
        if dest is None:
            dest = OrderedDict()

        # raw configparse
        parser = ConfigParser(
            dict_type=OrderedDict,
            allow_no_value=False,
            delimiters=("="),
            comment_prefixes=(self.commment_prefixes),
            strict=False,
            empty_lines_in_values=True,
            interpolation=ExtendedInterpolation(),
            default_section=self.default_str,
        )

        # read as a simple INI file
        parser.read_string(flattened_toml)

        # we are gonna build a json string out of it since it
        # is a relatively simple file to translate Toml onto and our values are
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
        new_dict = jsonLoads(json_entry, object_pairs_hook=OrderedDict)
        new_dict = sanitize_value(new_dict)
        for section in new_dict:
            # we override sections by section, overloading is done differently
            dest[section] = new_dict[section]

        return dest

    def loads(self, file_as_str: str, dest: OrderedDict = None):
        """[summary]

        Args:
            file_as_str (str): [description]
            dest (OrderedDict, optional): [description]. Defaults to None.
        """
        flattened_toml = self._flatten_toml_string(file_as_str, self.search_path)
        dest = self._load_flatened_toml(flattened_toml, dest=dest)
        return dest

    def load(self, file_list, dest: OrderedDict = None) -> OrderedDict:
        """[summary]

        Args:
            file_list ([type]): [description]
            dest (OrderedDict, optional): [description]. Defaults to None.

        Returns:
            OrderedDict: [description]
        """
        if isinstance(file_list, str):
            flattened_toml = self._flatten_toml_file(file_list, self.search_path)
            dest = self._load_flatened_toml(flattened_toml, dest=dest)
        else:
            for files in file_list:
                dest = self.load(files, dest=dest)
        return dest

    def finalize(self, dest: OrderedDict = None):
        """if a toml entry is prefixed with '.', it is a generic entry, not used after finalization.
        a toml entry can inherit from another one using '::'
        the last entry is the name, it inherits from all the '::' before

        Args:
            dest (OrderedDict, optional): [description]. Defaults to None.
        """
    def assert_type(
        self,
        conf: OrderedDict,
        entry: str,
        key: str,
        type_list: Union[type, Tuple[Union[type, Tuple[Any, ...]], ...]],
    ):
        """[summary]

        Args:
            conf (OrderedDict): [description]
            entry (str): [description]
            key (str): [description]
            type_list (Union[type, Tuple[Union[type, Tuple[Any, ...]], ...]]): [description]
        """
        msg = "Invalid entry in  " + key + ' in ["' + entry + '"]' + "is not of type ("
        try:
            msg += ", ".join([types.__name__ for types in type_list])
        except TypeError:
            msg += type_list.__name__
        msg += ")"

        assertion(isinstance(conf[entry][key], type_list), msg)

    def unload_entry(self, conf: OrderedDict, entry: str) -> OrderedDict:
        """[summary]

        Args:
            entry (str): [description]

        Returns:
            OrderedDict: [description]
        """
        entry_dict = OrderedDict()
        # load the processing lib
        if entry in conf:
            entry_dict = conf[entry]
            del conf[entry]

        return entry_dict
