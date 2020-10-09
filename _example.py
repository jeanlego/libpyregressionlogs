#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

# your function name must be loaded as a string in PRE_HOOKS= [] within your file
def _preprocessor_function(input_file, output_file) -> None:
    """This is a minimaly working example of a working log parser preprocessing hook

    Args:
        input (File_obj):
            the input file that is open as read only,
        output (File_obj):
            the temporary file opened to write back the processed input
    """

    for line in input_file:
        print(line, file=output_file)


# your function name must be loaded as a string in INLINE_HOOKS= [] within your file
def _processor_function(line_in: str) -> str:
    """This is a minimaly working example of a working log parser inline processing hook

    Args:
        line_in (str): the current line being read by the log processor

    Returns:
        str: the line to pass back to the log parser
    """
    return line_in


# your function name must be loaded as a string in POST_HOOKS= [] within your file
def postprocessor_function(dataset: OrderedDict) -> OrderedDict:
    """This is a minimaly working example of a working log parser postprocessing hook

    Args:
        dataset (OrderedDict): the input dataset to reorganize

    Returns:
        OrderedDict: the reodered dataset
    """
    return dataset

def compare_equals(_conf: OrderedDict, expected, got) -> bool:
    """Will verify the equality between two values

    Args:
        _conf (OrderedDict): is the TOML configuration
        dataset (OrderedDict): the input dataset to reorganize

    Returns:
        bool: if the values are equivalen
    """

    # short circuit
    if got == expected:
        return True

    # first make sure we can compare them,
    # the parser might eagerly convert numbers to floats then to int,
    # this will downcast if it one of them didn't succeed.
    if isinstance(got, str) or isinstance(expected, str):
        got = str(got)
        expected = str(expected)
    elif isinstance(got, float) or isinstance(expected, float):
        got = float(got)
        expected = float(expected)
    elif isinstance(got, int) or isinstance(expected, int):
        got = int(got)
        expected = int(expected)

    # short circuit
    if got == expected:
        return True

    if isinstance(got, str):
        # case unsensitive match
        return got.lower() == expected.lower()

    # if neither are infinite, then maybe theres a rouding error
    if (
        isinstance(got, float)
        and not math.isinf(got)
        and not math.isinf(expected)
        and not math.isnan(got)
        and not math.isinf(expected)
    ):
        tolerance = 1e-09
        got = math.fabs(got)
        expected = math.fabs(expected)
        diff = math.fabs(expected - got)
        return diff <= tolerance * max(got, expected)

    return False
