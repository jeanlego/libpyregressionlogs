#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

import sys
import argparse

from libparselog.utils import (
    colored,
    dump_csv,
    dump_json,
    load_json,
    load_csv,
)

from libparselog.parsedriver import ParseDriver

_LEN = 38


def satus_line(status, color, colorize):
    output = (
        colored("  " + status + " ", color, colorize)
        + ". . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . . ."
    )
    return output[:_LEN] + " "


def mismatch_str(colorize, header, expected=None, got=None):
    header = "{0:<{1}}".format("- " + header, _LEN)
    if expected is None:
        expected = ""
    else:
        expected = colored("[-" + str(expected) + "-]", "red", colorize)

    if got is None:
        got = ""
    else:
        got = colored("{+" + str(got) + "+}", "green", colorize)

    return "    " + header + expected + got


def compress_tbl(driver, tbl):
    # hide the one matching the condition
    for entry in tbl:
        tbl[entry] = driver.auto_hide_values(tbl[entry])

    # make sure that the defaults are printed as a separate table
    tbl["DEFAULT"] = driver.generate_hidden_tbl()
    return tbl


def decompress_tbl(tbl):
    # json are compressed using default table
    if "DEFAULT" in tbl:
        # once we have loaded the file, we go through and fill back the default
        # we will delete the default, then this way we could merge two files with different defaults
        # without issue
        for entry in tbl:
            if entry != "DEFAULT":
                for header in tbl["DEFAULT"]:
                    if entry not in tbl or header not in tbl[entry] or tbl[entry][header] is None:
                        tbl[entry][header] = tbl["DEFAULT"][header]

        del tbl["DEFAULT"]
    return tbl


def dump_tbl(driver, output_dict, as_csv, file=sys.stdout):
    if as_csv:
        dump_csv(driver, output_dict, file=file)
    else:
        output_dict = compress_tbl(driver, output_dict)
        dump_json(output_dict, file=file)


def load_log(driver, log_file_name) -> list:
    # load log file and parse
    log_file_name = driver.hooks.do_preprocess(log_file_name)

    # setup our output dict
    input_values = OrderedDict()

    with open(log_file_name) as log:
        for line in log:
            line = driver.hooks.do_process(line)
            for header in driver.get_header_list():
                value = driver.regex_line(header, line)
                if value is not None and value != "":
                    input_values = driver.insert_value(input_values, header, value)

    # load the defaults bfore post processing
    input_values = driver.set_default(input_values)
    input_values = driver.hooks.do_postprocess(input_values)

    # reload the default to fill the table
    input_values = driver.set_default(input_values)

    # expects a list, but we only have one here
    return [input_values]


def load_into_tbl(driver, file_name):
    tbl = OrderedDict()

    if file_name.endswith(".json"):
        tbl = load_json(file_name)
        tbl = decompress_tbl(tbl)
    else:
        data_list = []
        if file_name.endswith(".csv"):
            data_list = load_csv(file_name)
        else:
            # we assume this is a log file
            data_list = load_log(driver, file_name)

        for data in data_list:
            # make a key from the user desired key items
            key = driver.generate_key(data)
            tbl[key] = data

    return tbl


def parse(driver, file_list, as_csv=False):
    # load toml
    parsed_files = OrderedDict()
    if isinstance(file_list, str):
        parsed_files.update(load_into_tbl(driver, file_list))
    elif isinstance(file_list, (set, list)):
        for files in file_list:
            parsed_files.update(load_into_tbl(driver, files))

    dump_tbl(driver, parsed_files, as_csv)


def compare(
    driver,
    golden_result_file_name,
    result_file_name,
    diff_file_name,
    as_csv=False,
    subset=False,
    colorize=True,
):
    # load toml
    failure_count = 0
    expected = load_into_tbl(driver, golden_result_file_name)
    got = load_into_tbl(driver, result_file_name)
    diff = driver.do_diff(expected, got)
    diff_tbl = OrderedDict()
    for entry in diff:
        diff_tbl[entry] = OrderedDict()

        # subset are expected to have missing entries
        if diff[entry]["__STATUS__"] == "Missing" and subset:
            diff_tbl[entry][header] = diff[entry]["__ENTRIES__"][header]["__EXPECTED__"]
        else:
            print_color = ""
            if diff[entry]["__STATUS__"] == "Ok":
                print_color = "green"
            else:
                if diff[entry]["__STATUS__"] == "Failure":
                    print_color = "red"
                else:
                    print_color = "yellow"

                # print to std error the failed test name
                print(entry, file=sys.stderr)
                failure_count += 1

            print(satus_line(diff[entry]["__STATUS__"], print_color, colorize) + entry)

            if diff[entry]["__STATUS__"] == "Ok":
                for header in diff[entry]["__ENTRIES__"]:
                    diff_tbl[entry][header] = diff[entry]["__ENTRIES__"][header]["__EXPECTED__"]

            elif diff[entry]["__STATUS__"] == "Missing":
                for header in diff[entry]["__ENTRIES__"]:
                    print(
                        mismatch_str(
                            colorize,
                            header,
                            expected=diff[entry]["__ENTRIES__"][header]["__EXPECTED__"],
                        )
                    )
                    # dont add it in the diff

            elif diff[entry]["__STATUS__"] == "New":
                for header in diff[entry]["__ENTRIES__"]:
                    print(
                        mismatch_str(
                            colorize, header, got=diff[entry]["__ENTRIES__"][header]["__GOT__"]
                        )
                    )
                    diff_tbl[entry][header] = diff[entry]["__ENTRIES__"][header]["__GOT__"]

            elif diff[entry]["__STATUS__"] == "Failed":
                for header in diff[entry]["__ENTRIES__"]:
                    if diff[entry]["__ENTRIES__"][header]["__STATUS__"] == "Ok":
                        diff_tbl[entry][header] = diff[entry]["__ENTRIES__"][header]["__EXPECTED__"]
                    else:
                        print(
                            mismatch_str(
                                colorize,
                                header,
                                expected=diff[entry]["__ENTRIES__"][header]["__EXPECTED__"],
                                got=diff[entry]["__ENTRIES__"][header]["__GOT__"],
                            )
                        )
                        diff_tbl[entry][header] = diff[entry]["__ENTRIES__"][header]["__GOT__"]

    with open(diff_file_name, "w+") as diff_file:
        dump_tbl(driver, diff_tbl, as_csv, file=diff_file)

    return failure_count


def main():

    parser = argparse.ArgumentParser(description="Process some integers.")
    parser.add_argument("action", choices=["display", "parse", "join", "compare"])
    parser.add_argument(
        "--csv", default=False, action="store_true", help="output as a csv rather than JSON"
    )
    parser.add_argument(
        "--no_color",
        dest="colorize",
        default=True,
        action="store_false",
        help="Disable colorized output",
    )
    parser.add_argument(
        "--subset",
        dest="subset",
        action="store_true",
        default=False,
        help="disable errors on missing test since we are only running a part of it",
    )

    parser.add_argument(
        "-C",
        "--conf",
        dest="conf",
        default=[],
        type=str,
        action="append",
        metavar=("TOML config file"),
        help="adds a TOML config file to drive the parser",
    )

    parser.add_argument(
        "--preprocess",
        dest="preprocess_fn",
        default=[],
        type=str,
        action="append",
        metavar=("python file"),
        help="add preprocess hook to drive the log parser",
    )

    parser.add_argument(
        "--process",
        dest="process_fn",
        default=[],
        type=str,
        action="append",
        metavar=("python file"),
        help="add process hook to drive the log parser",
    )

    parser.add_argument(
        "--postprocess",
        dest="postprocess_fn",
        default=[],
        type=str,
        action="append",
        metavar=("python file"),
        help="add postprocess hook to drive the log parser",
    )

    parser.add_argument(
        "--import",
        dest="import_file",
        default=[],
        type=str,
        action="append",
        metavar=("python_file"),
        help="import python file",
    )

    parser.add_argument("file_list", nargs="+", metavar=("input_file"), help="list of input files")

    args = parser.parse_args()

    if len(args.conf) < 1:
        print("Expected at least one configuration file to drive the parser", file=sys.stderr)
        print(parser.print_help(), file=sys.stderr)
        return -1

    driver = ParseDriver(
        args.conf, args.import_file, args.preprocess_fn, args.process_fn, args.postprocess_fn
    )

    if args.action == "compare":
        if len(args.file_list) != 3:
            print("Expected 3 files to do the comparison <golden> <result> <diff>", file=sys.stderr)
            print(parser.print_help(), file=sys.stderr)
            return -1

        return compare(
            driver,
            args.file_list[0],
            args.file_list[1],
            args.file_list[2],
            args.csv,
            args.subset,
            args.colorize,
        )

    else:
        return parse(driver, args.file_list, args.csv)


if __name__ == "__main__":
    sys.exit(main())
