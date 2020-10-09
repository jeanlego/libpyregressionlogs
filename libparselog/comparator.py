#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict
from libparselog.utils import sanitize_value
import sys


class Comparator:

    fn_tbl = dict()

    def __init__(self, fn_table=None):
        self.fn_tbl = fn_table

    def _compare_values(self, comparator_name, conf, expected, got):
        # convert to a number if possible
        expected = sanitize_value(expected)
        got = sanitize_value(got)

        if comparator_name in self.fn_tbl:
            return self.fn_tbl[comparator_name](conf, expected, got)
        else:
            print("ERROR: unable to find " + comparator_name)
            sys.exit(255)

        return False

    def compare(self, comparator_name, conf, expected, got):
        if got is None and expected is None:
            return True

        if got is None or expected is None:
            return False

        if isinstance(got, list) and isinstance(expected, list):
            # make sure we have the same number of items
            if len(got) != len(expected):
                return False

            for (got_item, expected_item) in zip(got, expected):
                if not self._compare_values(comparator_name, conf, got_item, expected_item):
                    return False

            return True

        if isinstance(got, list) or isinstance(expected, list):
            return False

        return self._compare_values(comparator_name, conf, got, expected)
