#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

import sys
import re

from libparselog.toml import Toml
from libparselog.hooks import Hooks
from libparselog.comparator import Comparator
from libparselog.utils import sanitize_value, load_fn_table, unload_list, assertion


class ParseDriver:
    """loads a toml or a list of toml files to
    drive the log parser using the provided configurations
    """

    _K_DFLT = "default"
    _K_KEY = "key"
    _K_REGEX = "regex"
    _K_HIDE_IF = "hide-if"
    _K_AUTO_HIDE = "auto-hide"
    _K_LIST = "listing"
    _K_COMPARE = "compare"

    _KEYS = [
        _K_DFLT,
        _K_KEY,
        _K_REGEX,
        _K_HIDE_IF,
        _K_AUTO_HIDE,
        _K_LIST,
        _K_COMPARE,
    ]

    hooks = Hooks()
    comparator = Comparator()
    conf = OrderedDict()

    def __init__(
        self, toml_file_list, import_list, preprocess_list, process_list, postprocess_list
    ):

        # generate the conf
        toml_loader = Toml(toml_file_list)
        
        self.conf = toml_loader.load(toml_file_list)

        # unload the DRIVER entry
        driver_entries = toml_loader.unload_entry(self.conf, "DRIVER")

        # load the args from the TOML and append them to the cmd line args
        import_list += unload_list(driver_entries, "import")
        preprocess_list += unload_list(driver_entries, "preprocess")
        process_list += unload_list(driver_entries, "process")
        postprocess_list += unload_list(driver_entries, "postprocess")

        # load the functions from the imports into a table
        function_table = load_fn_table(import_list)

        # initialize our hooks and comparators using the function table
        self.hooks = Hooks(function_table, preprocess_list, process_list, postprocess_list)
        self.comparator = Comparator(function_table)

        # finalize the toml now that we stripped entries that are for the driver
        self._init_entries()
        self._sanitize()

    def _init_entries(self):
        for entry in self.conf:
            for key in self.conf[entry]:
                if key not in self._KEYS:
                    print(
                        "invalid option: "
                        + key
                        + " passed into the entry ["
                        + entry
                        + "], removing"
                    )
                    del self.conf[entry][key]

            for key in self._KEYS:
                if key not in self.conf[entry]:
                    self.conf[entry][key] = None

            # some types have built in defaults
            if self.conf[entry][self._Kself._KEY] is None:
                self.conf[entry][self._Kself._KEY] = False

            if self.conf[entry][self._K_LIST] is None:
                self.conf[entry][self._K_LIST] = False

            # if the type is a key, remove the defaults
            if self.conf[entry][self._Kself._KEY]:
                self.conf[entry][self._K_DFLT] = None
                self.conf[entry][self._K_AUTO_HIDE] = False
                self.conf[entry][self._K_HIDE_IF] = None

            # disable auto hide as a sane default if we have no entry
            if self.conf[entry][self._K_AUTO_HIDE] is None or self.conf[entry][self._K_HIDE_IF] is None:
                self.conf[entry][self._K_AUTO_HIDE] = False

            if self.conf[entry][self._K_LIST] is None:
                self.conf[entry][self._K_LIST] = False

    def _sanitize(self):
        # this will be used to make sure we have a key for the table
        keyed = False

        for entry in self:

            assertion(
                self._K_REGEX in self.conf[entry],
                self._K_REGEX + " in toml[" + entry + "] is required for the configuration to work",
            )
            self.Toml.assert_type(self, entry, self._K_REGEX, (str, list))

            if isinstance(self.conf[entry][self._K_REGEX], str):
                # regexes are always arrays, so we just fix that here
                self.conf[entry][self._K_REGEX] = [self.conf[entry][self._K_REGEX]]
            elif isinstance(self.conf[entry][self._K_REGEX], list):
                for regexes in self.conf[entry][self._K_REGEX]:
                    assertion(
                        isinstance(regexes, str),
                        self._K_REGEX + " in toml[" + entry + "] is expected to be a list of string",
                    )

            Toml.assert_type(self, entry, self._K_AUTO_HIDE, (bool))
            Toml.assert_type(self, entry, self._K_LIST, (bool))
            Toml.assert_type(self, entry, self._Kself._KEY, (bool))

            if self.conf[entry][self._K_DFLT] is not None and isinstance(
                self.conf[entry][self._K_DFLT], list
            ):
                self.conf[entry][self._K_LIST] = True

            if self.conf[entry][self._K_LIST]:
                if self.conf[entry][self._K_DFLT] is None:
                    self.conf[entry][self._K_DFLT] = []
                elif not isinstance(self.conf[entry][self._K_DFLT], list):
                    self.conf[entry][self._K_DFLT] = [self.conf[entry][self._K_DFLT]]

                # make sure the hide-if is changed back too
                if self.conf[entry][self._K_HIDE_IF] is not None and not isinstance(
                    self.conf[entry][self._K_HIDE_IF], list
                ):
                    self.conf[entry][self._K_HIDE_IF] = [self.conf[entry][self._K_HIDE_IF]]

            # if we have a comparison, make sur it contains a struct we can hand off
            if self.conf[entry][self._K_COMPARE] is not None:
                Toml.assert_type(self, entry, self._K_COMPARE, (dict))
                assertion(
                    len(self.conf[entry][self._K_COMPARE].self._KEYS()) == 1,
                    self._K_COMPARE + " in toml[" + entry + "] must be of format 'function: struct', with only one function",
                )

            if self.conf[entry][self._Kself._KEY]:
                keyed = True

        if not keyed:
            print(
                "Your toml has no KEYS\n"
                " please add a key = ? to allow this tool to sort the items"
            )
            sys.exit(255)

    def insert_value(self, tbl, header, value):
        if header not in tbl and self.conf[header][self._K_LIST]:
            tbl[header] = []

        # append all the finds to the list
        if self.conf[header][self._K_LIST]:
            tbl[header].append(value)
        # keep overriding
        else:
            tbl[header] = value

        return tbl

    def set_default(self, tbl):
        for header in self.get_header_list():
            if header not in tbl:
                tbl[header] = self.conf[header][self._K_DFLT]

        return tbl

    def is_multivalued(self, header):
        return self.conf[header][self._K_LIST]

    def generate_tbl(self, key: str) -> OrderedDict:
        """will generate an empty table for the key, with the default value

        Args:
            key (str): the key used to generate the table

        Returns:
            OrderedDict: the generated table
        """
        # set the grab the values for that key
        input_values = OrderedDict()
        for header in self.conf:
            if not self.conf[header][self._Kself._KEY]:
                input_values[header] = self.conf[header][key]

        return input_values

    def generate_hidden_tbl(self) -> OrderedDict:
        """will generate an empty table with the value from the hidden condition key"""
        return self.generate_tbl(self._K_HIDE_IF)

    def regex_line(self, header, line):
        # compile the regex entries
        entry_list = []

        for regexes in self.conf[header][self._K_REGEX]:
            matched_re = re.match(regexes, line)
            if matched_re is not None:
                for entry in matched_re.groups():
                    if entry is not None:
                        entry_list.append(entry)

        entry_str = ""
        if len(entry_list) > 0:
            # collapse list into a single string
            entry_str = " ".join(entry_list)

        # sanitize whitespace
        return sanitize_value(entry_str)

    def get_header_list(self):
        return self.conf.keys()

    def generate_key(self, dataset):
        keyed = []
        for header in self.conf:
            if self.conf[header][self._Kself._KEY]:
                value = None
                if header in dataset and dataset[header] is not None:
                    value = dataset[header]

                if value is not None:
                    if isinstance(value, list):
                        keyed += value
                    else:
                        keyed.append(value)

        if len(keyed) == 0:
            print("FATAL_ERROR == Unable to key the file")
            sys.exit(255)

        return " ".join(keyed)

    def auto_hide_values(self, dataset):
        for header in self.conf:
            if self.conf[header][self._K_AUTO_HIDE] is True and header in dataset:
                if (
                    dataset[header] is self.conf[header][self._K_HIDE_IF]
                    or dataset[header] == self.conf[header][self._K_HIDE_IF]
                ):
                    del dataset[header]

        return dataset

    def do_diff(
        self,
        expected,
        got,
    ):
        diff = OrderedDict()

        # generate the diff table
        for entry in set(list(expected.keys()) + list(got.keys())):
            diff[entry] = OrderedDict()
            diff[entry]["__STATUS__"] = "Ok"
            diff[entry]["__ENTRIES__"] = OrderedDict()

            for header in self.get_header_list():
                diff[entry]["__ENTRIES__"][header] = OrderedDict()
                diff[entry]["__ENTRIES__"][header]["__GOT__"] = None
                diff[entry]["__ENTRIES__"][header]["__EXPECTED__"] = None
                diff[entry]["__ENTRIES__"][header]["__STATUS__"] = "Ok"

                if entry not in expected:
                    diff[entry]["__STATUS__"] = "New"
                    diff[entry]["__ENTRIES__"][header]["__STATUS__"] = "New"
                elif header in expected[entry]:
                    diff[entry]["__ENTRIES__"][header]["__EXPECTED__"] = expected[entry][header]

                if entry not in got:
                    diff[entry]["__STATUS__"] = "Missing"
                    diff[entry]["__ENTRIES__"][header]["__STATUS__"] = "Missing"
                elif entry in got and header in got[entry]:
                    diff[entry]["__ENTRIES__"][header]["__GOT__"] = got[entry][header]

                if not self.compare(
                    header,
                    diff[entry]["__ENTRIES__"][header]["__EXPECTED__"],
                    diff[entry]["__ENTRIES__"][header]["__GOT__"],
                ):
                    diff[entry]["__STATUS__"] = "Failed"
                    diff[entry]["__ENTRIES__"][header]["__STATUS__"] = "Failed"

        return diff

    def compare(self, header, expected, got):
        if self.conf[header][self._K_COMPARE] is None:
            return True

        return self.comparator.compare(
            list(self.conf[header][self._K_COMPARE].keys())[0],
            list(self.conf[header][self._K_COMPARE].values())[0],
            expected,
            got,
        )
