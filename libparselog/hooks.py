#!/usr/bin/env python3

"""[summary]
"""

# We use OrderedDict in place of dict to
# keep the ordering from the toml
from collections import OrderedDict

# your function name must be loaded as a string in PRE_HOOKS= [] within your file
def _preprocess_fn(input_file, output_file) -> None:
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
def _process_fn(line_in: str) -> str:
    """This is a minimaly working example of a working log parser inline processing hook

    Args:
        line_in (str): the current line being read by the log processor

    Returns:
        str: the line to pass back to the log parser
    """
    return line_in


# your function name must be loaded as a string in POST_HOOKS= [] within your file
def postprocess_fn(dataset: OrderedDict) -> OrderedDict:
    """This is a minimaly working example of a working log parser postprocessing hook

    Args:
        dataset (OrderedDict): the input dataset to reorganize

    Returns:
        OrderedDict: the reodered dataset
    """
    return dataset


class Hooks:
    """[summary]

    Returns:
        [type]: [description]
    """

    preprocess = [
        # no functions registered
    ]

    process = [
        # no functions registered
    ]

    postprocess = [
        # no functions registered
    ]

    def __init__(
        self, function_table=None, preprocess_list=None, process_list=None, postprocess_list=None
    ):
        if preprocess_list is not None:
            for fn_name in preprocess_list:
                if fn_name in function_table:
                    self.preprocess.append(function_table[fn_name])

        if process_list is not None:
            for fn_name in process_list:
                if fn_name in function_table:
                    self.process.append(function_table[fn_name])

        if postprocess_list is not None:
            for fn_name in postprocess_list:
                if fn_name in function_table:
                    self.postprocess.append(function_table[fn_name])

    def do_preprocess(self, file_name: str) -> str:
        """will do each preprocessor functions

        Args:
            file_name (str): the input file name

        Returns:
            str: the final file once all the preprocessing as been done
        """
        file_to_return = file_name
        file_input = open(file_to_return, "r")
        preproc_count = 0
        for hook_fn in self.preprocess:
            preproc_count += 1
            file_input.seek(0, 0)
            file_to_return = file_name + ".preproc_" + str(preproc_count)
            file_output = open(file_to_return, "w+")
            hook_fn(file_input, file_output)
            file_input.close()
            file_input = file_output

        file_input.close()
        return file_to_return

    def do_process(self, line: str) -> str:
        """will do each inline processor functions

        Args:
            line (str): the current line being parsed

        Returns:
            str: the line once all the processing as been done
        """
        for hook_fn in self.process:
            line = hook_fn(line)

        return line

    def do_postprocess(self, dataset: OrderedDict) -> OrderedDict:
        """will do each post processor functions

        Args:
            dataset (OrderedDict): the input dataset to reorganize

        Returns:
            OrderedDict: the reodered dataset
        """
        for hook_fn in self.postprocess:
            dataset = hook_fn(dataset)

        return dataset
