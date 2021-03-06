#!/usr/bin/env python

r"""
This module provides many valuable print functions such as sprint_var,
sprint_time, sprint_error, sprint_call_stack.
"""

import sys
import os
import time
import inspect
import re
import grp
import socket
import argparse
import __builtin__
import logging
import collections

try:
    robot_env = 1
    from robot.utils import DotDict
    from robot.utils import NormalizedDict
    from robot.libraries.BuiltIn import BuiltIn
    # Having access to the robot libraries alone does not indicate that we
    # are in a robot environment.  The following try block should confirm that.
    try:
        var_value = BuiltIn().get_variable_value("${SUITE_NAME}", "")
    except:
        robot_env = 0
except ImportError:
    robot_env = 0

import gen_arg as ga

# Setting these variables for use both inside this module and by programs
# importing this module.
pgm_dir_path = sys.argv[0]
pgm_name = os.path.basename(pgm_dir_path)
pgm_dir_name = re.sub("/" + pgm_name, "", pgm_dir_path) + "/"


# Some functions (e.g. sprint_pgm_header) have need of a program name value
# that looks more like a valid variable name.  Therefore, we'll swap odd
# characters like "." out for underscores.
pgm_name_var_name = pgm_name.replace(".", "_")

# Initialize global values used as defaults by print_time, print_var, etc.
col1_indent = 0

# Calculate default column width for print_var functions based on environment
# variable settings.  The objective is to make the variable values line up
# nicely with the time stamps.
col1_width = 29

NANOSECONDS = os.environ.get('NANOSECONDS', '1')


if NANOSECONDS == "1":
    col1_width = col1_width + 7

SHOW_ELAPSED_TIME = os.environ.get('SHOW_ELAPSED_TIME', '1')

if SHOW_ELAPSED_TIME == "1":
    if NANOSECONDS == "1":
        col1_width = col1_width + 14
    else:
        col1_width = col1_width + 7

# Initialize some time variables used in module functions.
start_time = time.time()
sprint_time_last_seconds = start_time

# The user can set environment variable "GEN_PRINT_DEBUG" to get debug output
# from this module.
gen_print_debug = int(os.environ.get('GEN_PRINT_DEBUG', 0))


###############################################################################
def sprint_func_name(stack_frame_ix=None):

    r"""
    Return the function name associated with the indicated stack frame.

    Description of arguments:
    stack_frame_ix                  The index of the stack frame whose
                                    function name should be returned.  If the
                                    caller does not specify a value, this
                                    function will set the value to 1 which is
                                    the index of the caller's stack frame.  If
                                    the caller is the wrapper function
                                    "print_func_name", this function will bump
                                    it up by 1.
    """

    # If user specified no stack_frame_ix, we'll set it to a proper default
    # value.
    if stack_frame_ix is None:
        func_name = sys._getframe().f_code.co_name
        caller_func_name = sys._getframe(1).f_code.co_name
        if func_name[1:] == caller_func_name:
            stack_frame_ix = 2
        else:
            stack_frame_ix = 1

    func_name = sys._getframe(stack_frame_ix).f_code.co_name

    return func_name

###############################################################################


# get_arg_name is not a print function per se.  I have included it in this
# module because it is used by sprint_var which is found in this module.
###############################################################################
def get_arg_name(var,
                 arg_num=1,
                 stack_frame_ix=1):

    r"""
    Return the "name" of an argument passed to a function.  This could be a
    literal or a variable name.

    Description of arguments:
    var                             The variable whose name you want returned.
    arg_num                         The arg number (1 through n) whose name
                                    you wish to have returned.  This value
                                    should not exceed the number of arguments
                                    allowed by the target function.
    stack_frame_ix                  The stack frame index of the target
                                    function.  This value must be 1 or
                                    greater.  1 would indicate get_arg_name's
                                    stack frame.  2 would be the caller of
                                    get_arg_name's stack frame, etc.

    Example 1:

    my_var = "mike"
    var_name = get_arg_name(my_var)

    In this example, var_name will receive the value "my_var".

    Example 2:

    def test1(var):
        # Getting the var name of the first arg to this function, test1.
        # Note, in this case, it doesn't matter what you pass as the first arg
        # to get_arg_name since it is the caller's variable name that matters.
        dummy = 1
        arg_num = 1
        stack_frame = 2
        var_name = get_arg_name(dummy, arg_num, stack_frame)

    # Mainline...

    another_var = "whatever"
    test1(another_var)

    In this example, var_name will be set to "another_var".

    """

    # Note: I wish to avoid recursion so I refrain from calling any function
    # that calls this function (i.e. sprint_var, valid_value, etc.).

    # The user can set environment variable "GET_ARG_NAME_DEBUG" to get debug
    # output from this function.
    local_debug = int(os.environ.get('GET_ARG_NAME_DEBUG', 0))
    # In addition to GET_ARG_NAME_DEBUG, the user can set environment
    # variable "GET_ARG_NAME_SHOW_SOURCE" to have this function include source
    # code in the debug output.
    local_debug_show_source = int(
        os.environ.get('GET_ARG_NAME_SHOW_SOURCE', 0))

    if arg_num < 1:
        print_error("Programmer error - Variable \"arg_num\" has an invalid" +
                    " value of \"" + str(arg_num) + "\".  The value must be" +
                    " an integer that is greater than 0.\n")
        # What is the best way to handle errors?  Raise exception?  I'll
        # revisit later.
        return
    if stack_frame_ix < 1:
        print_error("Programmer error - Variable \"stack_frame_ix\" has an" +
                    " invalid value of \"" + str(stack_frame_ix) + "\".  The" +
                    " value must be an integer that is greater than or equal" +
                    " to 1.\n")
        return

    if local_debug:
        debug_indent = 2
        print("")
        print_dashes(0, 120)
        print(sprint_func_name() + "() parms:")
        print_varx("var", var, 0, debug_indent)
        print_varx("arg_num", arg_num, 0, debug_indent)
        print_varx("stack_frame_ix", stack_frame_ix, 0, debug_indent)
        print("")
        print_call_stack(debug_indent, 2)

    for count in range(0, 2):
        try:
            frame, filename, cur_line_no, function_name, lines, index = \
                inspect.stack()[stack_frame_ix]
        except IndexError:
            print_error("Programmer error - The caller has asked for" +
                        " information about the stack frame at index \"" +
                        str(stack_frame_ix) + "\".  However, the stack" +
                        " only contains " + str(len(inspect.stack())) +
                        " entries.  Therefore the stack frame index is out" +
                        " of range.\n")
            return
        if filename != "<string>":
            break
        # filename of "<string>" may mean that the function in question was
        # defined dynamically and therefore its code stack is inaccessible.
        # This may happen with functions like "rqprint_var".  In this case,
        # we'll increment the stack_frame_ix and try again.
        stack_frame_ix += 1
        if local_debug:
            print("Adjusted stack_frame_ix...")
            print_varx("stack_frame_ix", stack_frame_ix, 0, debug_indent)

    called_func_name = sprint_func_name(stack_frame_ix)

    module = inspect.getmodule(frame)

    # Though I would expect inspect.getsourcelines(frame) to get all module
    # source lines if the frame is "<module>", it doesn't do that.  Therefore,
    # for this special case, I will do inspect.getsourcelines(module).
    if function_name == "<module>":
        source_lines, source_line_num =\
            inspect.getsourcelines(module)
        line_ix = cur_line_no - source_line_num - 1
    else:
        source_lines, source_line_num =\
            inspect.getsourcelines(frame)
        line_ix = cur_line_no - source_line_num

    if local_debug:
        print("\n  Variables retrieved from inspect.stack() function:")
        print_varx("frame", frame, 0, debug_indent + 2)
        print_varx("filename", filename, 0, debug_indent + 2)
        print_varx("cur_line_no", cur_line_no, 0, debug_indent + 2)
        print_varx("function_name", function_name, 0, debug_indent + 2)
        print_varx("lines", lines, 0, debug_indent + 2)
        print_varx("index", index, 0, debug_indent + 2)
        print_varx("source_line_num", source_line_num, 0, debug_indent)
        print_varx("line_ix", line_ix, 0, debug_indent)
        if local_debug_show_source:
            print_varx("source_lines", source_lines, 0, debug_indent)
        print_varx("called_func_name", called_func_name, 0, debug_indent)

    # Get a list of all functions defined for the module.  Note that this
    # doesn't work consistently when _run_exitfuncs is at the top of the stack
    # (i.e. if we're running an exit function).  I've coded a work-around
    # below for this deficiency.
    all_functions = inspect.getmembers(module, inspect.isfunction)

    # Get called_func_id by searching for our function in the list of all
    # functions.
    called_func_id = None
    for func_name, function in all_functions:
        if func_name == called_func_name:
            called_func_id = id(function)
            break
    # NOTE: The only time I've found that called_func_id can't be found is
    # when we're running from an exit function.

    # Look for other functions in module with matching id.
    aliases = set([called_func_name])
    for func_name, function in all_functions:
        if func_name == called_func_name:
            continue
        func_id = id(function)
        if func_id == called_func_id:
            aliases.add(func_name)

    # In most cases, my general purpose code above will find all aliases.
    # However, for the odd case (i.e. running from exit function), I've added
    # code to handle pvar, qpvar, dpvar, etc. aliases explicitly since they
    # are defined in this module and used frequently.
    # pvar is an alias for print_var.
    aliases.add(re.sub("print_var", "pvar", called_func_name))

    func_regex = ".*(" + '|'.join(aliases) + ")[ ]*\("

    # Search backward through source lines looking for the calling function
    # name.
    found = False
    for start_line_ix in range(line_ix, 0, -1):
        # Skip comment lines.
        if re.match(r"[ ]*#", source_lines[start_line_ix]):
            continue
        if re.match(func_regex, source_lines[start_line_ix]):
            found = True
            break
    if not found:
        print_error("Programmer error - Could not find the source line with" +
                    " a reference to function \"" + called_func_name + "\".\n")
        return

    # Search forward through the source lines looking for a line whose
    # indentation is the same or less than the start line.  The end of our
    # composite line should be the line preceding that line.
    start_indent = len(source_lines[start_line_ix]) -\
        len(source_lines[start_line_ix].lstrip(' '))
    end_line_ix = line_ix
    for end_line_ix in range(line_ix + 1, len(source_lines)):
        if source_lines[end_line_ix].strip() == "":
            continue
        line_indent = len(source_lines[end_line_ix]) -\
            len(source_lines[end_line_ix].lstrip(' '))
        if line_indent <= start_indent:
            end_line_ix -= 1
            break

    # Join the start line through the end line into a composite line.
    composite_line = ''.join(map(str.strip,
                             source_lines[start_line_ix:end_line_ix + 1]))

    # arg_list_etc = re.sub(".*" + called_func_name, "", composite_line)
    arg_list_etc = "(" + re.sub(func_regex, "", composite_line)
    if local_debug:
        print_varx("aliases", aliases, 0, debug_indent)
        print_varx("func_regex", func_regex, 0, debug_indent)
        print_varx("start_line_ix", start_line_ix, 0, debug_indent)
        print_varx("end_line_ix", end_line_ix, 0, debug_indent)
        print_varx("composite_line", composite_line, 0, debug_indent)
        print_varx("arg_list_etc", arg_list_etc, 0, debug_indent)

    # Parse arg list...
    # Initialize...
    nest_level = -1
    arg_ix = 0
    args_list = [""]
    for ix in range(0, len(arg_list_etc)):
        char = arg_list_etc[ix]
        # Set the nest_level based on whether we've encounted a parenthesis.
        if char == "(":
            nest_level += 1
            if nest_level == 0:
                continue
        elif char == ")":
            nest_level -= 1
            if nest_level < 0:
                break

        # If we reach a comma at base nest level, we are done processing an
        # argument so we increment arg_ix and initialize a new args_list entry.
        if char == "," and nest_level == 0:
            arg_ix += 1
            args_list.append("")
            continue

        # For any other character, we append it it to the current arg list
        # entry.
        args_list[arg_ix] += char

    # Trim whitespace from each list entry.
    args_list = [arg.strip() for arg in args_list]

    if arg_num > len(args_list):
        print_error("Programmer error - The caller has asked for the name of" +
                    " argument number \"" + str(arg_num) + "\" but there " +
                    "were only \"" + str(len(args_list)) + "\" args used:\n" +
                    sprint_varx("args_list", args_list))
        return

    argument = args_list[arg_num - 1]

    if local_debug:
        print_varx("args_list", args_list, 0, debug_indent)
        print_varx("argument", argument, 0, debug_indent)
        print_dashes(0, 120)

    return argument

###############################################################################


###############################################################################
def sprint_time(buffer=""):

    r"""
    Return the time in the following format.

    Example:

    The following python code...

    sys.stdout.write(sprint_time())
    sys.stdout.write("Hi.\n")

    Will result in the following type of output:

    #(CDT) 2016/07/08 15:25:35 - Hi.

    Example:

    The following python code...

    sys.stdout.write(sprint_time("Hi.\n"))

    Will result in the following type of output:

    #(CDT) 2016/08/03 17:12:05 - Hi.

    The following environment variables will affect the formatting as
    described:
    NANOSECONDS                     This will cause the time stamps to be
                                    precise to the microsecond (Yes, it
                                    probably should have been named
                                    MICROSECONDS but the convention was set
                                    long ago so we're sticking with it).
                                    Example of the output when environment
                                    variable NANOSECONDS=1.

    #(CDT) 2016/08/03 17:16:25.510469 - Hi.

    SHOW_ELAPSED_TIME               This will cause the elapsed time to be
                                    included in the output.  This is the
                                    amount of time that has elapsed since the
                                    last time this function was called.  The
                                    precision of the elapsed time field is
                                    also affected by the value of the
                                    NANOSECONDS environment variable.  Example
                                    of the output when environment variable
                                    NANOSECONDS=0 and SHOW_ELAPSED_TIME=1.

    #(CDT) 2016/08/03 17:17:40 -    0 - Hi.

    Example of the output when environment variable NANOSECONDS=1 and
    SHOW_ELAPSED_TIME=1.

    #(CDT) 2016/08/03 17:18:47.317339 -    0.000046 - Hi.

    Description of arguments.
    buffer                          This will be appended to the formatted
                                    time string.
    """

    global NANOSECONDS
    global SHOW_ELAPSED_TIME
    global sprint_time_last_seconds

    seconds = time.time()
    loc_time = time.localtime(seconds)
    nanoseconds = "%0.6f" % seconds
    pos = nanoseconds.find(".")
    nanoseconds = nanoseconds[pos:]

    time_string = time.strftime("#(%Z) %Y/%m/%d %H:%M:%S", loc_time)
    if NANOSECONDS == "1":
        time_string = time_string + nanoseconds

    if SHOW_ELAPSED_TIME == "1":
        cur_time_seconds = seconds
        math_string = "%9.9f" % cur_time_seconds + " - " + "%9.9f" % \
            sprint_time_last_seconds
        elapsed_seconds = eval(math_string)
        if NANOSECONDS == "1":
            elapsed_seconds = "%11.6f" % elapsed_seconds
        else:
            elapsed_seconds = "%4i" % elapsed_seconds
        sprint_time_last_seconds = cur_time_seconds
        time_string = time_string + " - " + elapsed_seconds

    return time_string + " - " + buffer

###############################################################################


###############################################################################
def sprint_timen(buffer=""):

    r"""
    Append a line feed to the buffer, pass it to sprint_time and return the
    result.
    """

    return sprint_time(buffer + "\n")

###############################################################################


###############################################################################
def sprint_error(buffer=""):

    r"""
    Return a standardized error string.  This includes:
      - A time stamp
      - The "**ERROR**" string
      - The caller's buffer string.

    Example:

    The following python code...

    print(sprint_error("Oops.\n"))

    Will result in the following type of output:

    #(CDT) 2016/08/03 17:12:05 - **ERROR** Oops.

    Description of arguments.
    buffer                          This will be appended to the formatted
                                    error string.
    """

    return sprint_time() + "**ERROR** " + buffer

###############################################################################


###############################################################################
def sprint_varx(var_name,
                var_value,
                hex=0,
                loc_col1_indent=col1_indent,
                loc_col1_width=col1_width,
                trailing_char="\n"):

    r"""
    Print the var name/value passed to it.  If the caller lets loc_col1_width
    default, the printing lines up nicely with output generated by the
    print_time functions.

    Note that the sprint_var function (defined below) can be used to call this
    function so that the programmer does not need to pass the var_name.
    sprint_var will figure out the var_name.  The sprint_var function is the
    one that would normally be used by the general user.

    For example, the following python code:

    first_name = "Mike"
    print_time("Doing this...\n")
    print_varx("first_name", first_name)
    print_time("Doing that...\n")

    Will generate output like this:

    #(CDT) 2016/08/10 17:34:42.847374 -    0.001285 - Doing this...
    first_name:                                       Mike
    #(CDT) 2016/08/10 17:34:42.847510 -    0.000136 - Doing that...

    This function recognizes several complex types of data such as dict, list
    or tuple.

    For example, the following python code:

    my_dict = dict(one=1, two=2, three=3)
    print_var(my_dict)

    Will generate the following output:

    my_dict:
      my_dict[three]:                                 3
      my_dict[two]:                                   2
      my_dict[one]:                                   1

    Description of arguments.
    var_name                        The name of the variable to be printed.
    var_value                       The value of the variable to be printed.
    hex                             This indicates that the value should be
                                    printed in hex format.  It is the user's
                                    responsibility to ensure that a var_value
                                    contains a valid hex number.  For string
                                    var_values, this will be interpreted as
                                    show_blanks which means that blank values
                                    will be printed as "<blank>".  For dict
                                    var_values, this will be interpreted as
                                    terse format where keys are not repeated
                                    in the output.
    loc_col1_indent                 The number of spaces to indent the output.
    loc_col1_width                  The width of the output column containing
                                    the variable name.  The default value of
                                    this is adjusted so that the var_value
                                    lines up with text printed via the
                                    print_time function.
    trailing_char                   The character to be used at the end of the
                                    returned string.  The default value is a
                                    line feed.
    """

    # Determine the type
    if type(var_value) in (int, float, bool, str, unicode) \
       or var_value is None:
        # The data type is simple in the sense that it has no subordinate
        # parts.
        # Adjust loc_col1_width.
        loc_col1_width = loc_col1_width - loc_col1_indent
        # See if the user wants the output in hex format.
        if hex:
            if type(var_value) not in (int, long):
                value_format = "%s"
                if var_value == "":
                    var_value = "<blank>"
            else:
                value_format = "0x%08x"
        else:
            value_format = "%s"
        format_string = "%" + str(loc_col1_indent) + "s%-" \
            + str(loc_col1_width) + "s" + value_format + trailing_char
        return format_string % ("", str(var_name) + ":", var_value)
    elif type(var_value) is type:
        return sprint_varx(var_name, str(var_value).split("'")[1], hex,
                           loc_col1_indent, loc_col1_width, trailing_char)
    else:
        # The data type is complex in the sense that it has subordinate parts.
        format_string = "%" + str(loc_col1_indent) + "s%s\n"
        buffer = format_string % ("", var_name + ":")
        loc_col1_indent += 2
        try:
            length = len(var_value)
        except TypeError:
            length = 0
        ix = 0
        loc_trailing_char = "\n"
        type_is_dict = 0
        if type(var_value) is dict:
            type_is_dict = 1
        try:
            if type(var_value) is collections.OrderedDict:
                type_is_dict = 1
        except AttributeError:
            pass
        try:
            if type(var_value) is DotDict:
                type_is_dict = 1
        except NameError:
            pass
        try:
            if type(var_value) is NormalizedDict:
                type_is_dict = 1
        except NameError:
            pass
        if type_is_dict:
            for key, value in var_value.iteritems():
                ix += 1
                if ix == length:
                    loc_trailing_char = trailing_char
                if hex:
                    # Since hex is being used as a format type, we want it
                    # turned off when processing integer dictionary values so
                    # it is not interpreted as a hex indicator.
                    loc_hex = not (type(value) is int)
                    buffer += sprint_varx(key, value,
                                          loc_hex, loc_col1_indent,
                                          loc_col1_width,
                                          loc_trailing_char)
                else:
                    buffer += sprint_varx(var_name + "[" + key + "]", value,
                                          hex, loc_col1_indent, loc_col1_width,
                                          loc_trailing_char)
        elif type(var_value) in (list, tuple, set):
            for key, value in enumerate(var_value):
                ix += 1
                if ix == length:
                    loc_trailing_char = trailing_char
                buffer += sprint_varx(var_name + "[" + str(key) + "]", value,
                                      hex, loc_col1_indent, loc_col1_width,
                                      loc_trailing_char)
        elif type(var_value) is argparse.Namespace:
            for key in var_value.__dict__:
                ix += 1
                if ix == length:
                    loc_trailing_char = trailing_char
                cmd_buf = "buffer += sprint_varx(var_name + \".\" + str(key)" \
                          + ", var_value." + key + ", hex, loc_col1_indent," \
                          + " loc_col1_width, loc_trailing_char)"
                exec(cmd_buf)
        else:
            var_type = type(var_value).__name__
            func_name = sys._getframe().f_code.co_name
            var_value = "<" + var_type + " type not supported by " + \
                        func_name + "()>"
            value_format = "%s"
            loc_col1_indent -= 2
            # Adjust loc_col1_width.
            loc_col1_width = loc_col1_width - loc_col1_indent
            format_string = "%" + str(loc_col1_indent) + "s%-" \
                + str(loc_col1_width) + "s" + value_format + trailing_char
            return format_string % ("", str(var_name) + ":", var_value)

        return buffer

    return ""

###############################################################################


###############################################################################
def sprint_var(*args):

    r"""
    Figure out the name of the first argument for you and then call
    sprint_varx with it.  Therefore, the following 2 calls are equivalent:
    sprint_varx("var1", var1)
    sprint_var(var1)
    """

    # Get the name of the first variable passed to this function.
    stack_frame = 2
    caller_func_name = sprint_func_name(2)
    if caller_func_name.endswith("print_var"):
        stack_frame += 1
    var_name = get_arg_name(None, 1, stack_frame)
    return sprint_varx(var_name, *args)

###############################################################################


###############################################################################
def sprint_vars(*args):

    r"""
    Sprint the values of one or more variables.

    Description of args:
    args:
        If the first argument is an integer, it will be interpreted to be the
        "indent" value.
        If the second argument is an integer, it will be interpreted to be the
        "col1_width" value.
        If the third argument is an integer, it will be interpreted to be the
        "hex" value.
        All remaining parms are considered variable names which are to be
        sprinted.
    """

    if len(args) == 0:
        return

    # Get the name of the first variable passed to this function.
    stack_frame = 2
    caller_func_name = sprint_func_name(2)
    if caller_func_name.endswith("print_vars"):
        stack_frame += 1

    parm_num = 1

    # Create list from args (which is a tuple) so that it can be modified.
    args_list = list(args)

    var_name = get_arg_name(None, parm_num, stack_frame)
    # See if parm 1 is to be interpreted as "indent".
    try:
        if type(int(var_name)) is int:
            indent = int(var_name)
            args_list.pop(0)
            parm_num += 1
    except ValueError:
        indent = 0

    var_name = get_arg_name(None, parm_num, stack_frame)
    # See if parm 1 is to be interpreted as "col1_width".
    try:
        if type(int(var_name)) is int:
            loc_col1_width = int(var_name)
            args_list.pop(0)
            parm_num += 1
    except ValueError:
        loc_col1_width = col1_width

    var_name = get_arg_name(None, parm_num, stack_frame)
    # See if parm 1 is to be interpreted as "hex".
    try:
        if type(int(var_name)) is int:
            hex = int(var_name)
            args_list.pop(0)
            parm_num += 1
    except ValueError:
        hex = 0

    buffer = ""
    for var_value in args_list:
        var_name = get_arg_name(None, parm_num, stack_frame)
        buffer += sprint_varx(var_name, var_value, hex, indent, loc_col1_width)
        parm_num += 1

    return buffer

###############################################################################


###############################################################################
def lprint_varx(var_name,
                var_value,
                hex=0,
                loc_col1_indent=col1_indent,
                loc_col1_width=col1_width,
                log_level=getattr(logging, 'INFO')):

    r"""
    Send sprint_varx output to logging.
    """

    logging.log(log_level, sprint_varx(var_name, var_value, hex,
                loc_col1_indent, loc_col1_width, ""))

###############################################################################


###############################################################################
def lprint_var(*args):

    r"""
    Figure out the name of the first argument for you and then call
    lprint_varx with it.  Therefore, the following 2 calls are equivalent:
    lprint_varx("var1", var1)
    lprint_var(var1)
    """

    # Get the name of the first variable passed to this function.
    stack_frame = 2
    caller_func_name = sprint_func_name(2)
    if caller_func_name.endswith("print_var"):
        stack_frame += 1
    var_name = get_arg_name(None, 1, stack_frame)
    lprint_varx(var_name, *args)

###############################################################################


###############################################################################
def sprint_dashes(indent=col1_indent,
                  width=80,
                  line_feed=1,
                  char="-"):

    r"""
    Return a string of dashes to the caller.

    Description of arguments:
    indent                          The number of characters to indent the
                                    output.
    width                           The width of the string of dashes.
    line_feed                       Indicates whether the output should end
                                    with a line feed.
    char                            The character to be repeated in the output
                                    string.
    """

    width = int(width)
    buffer = " " * int(indent) + char * width
    if line_feed:
        buffer += "\n"

    return buffer

###############################################################################


###############################################################################
def sindent(text="",
            indent=0):

    r"""
    Pre-pend the specified number of characters to the text string (i.e.
    indent it) and return it.

    Description of arguments:
    text                            The string to be indented.
    indent                          The number of characters to indent the
                                    string.
    """

    format_string = "%" + str(indent) + "s%s"
    buffer = format_string % ("", text)

    return buffer

###############################################################################


###############################################################################
def sprint_call_stack(indent=0,
                      stack_frame_ix=0):

    r"""
    Return a call stack report for the given point in the program with line
    numbers, function names and function parameters and arguments.

    Sample output:

    -------------------------------------------------------------------------
    Python function call stack

    Line # Function name and arguments
    ------ ------------------------------------------------------------------
       424 sprint_call_stack ()
         4 print_call_stack ()
        31 func1 (last_name = 'walsh', first_name = 'mikey')
        59 /tmp/scr5.py
    -------------------------------------------------------------------------

    Description of arguments:
    indent                          The number of characters to indent each
                                    line of output.
    stack_frame_ix                  The index of the first stack frame which
                                    is to be returned.
    """

    buffer = ""
    buffer += sprint_dashes(indent)
    buffer += sindent("Python function call stack\n\n", indent)
    buffer += sindent("Line # Function name and arguments\n", indent)
    buffer += sprint_dashes(indent, 6, 0) + " " + sprint_dashes(0, 73)

    # Grab the current program stack.
    current_stack = inspect.stack()

    # Process each frame in turn.
    format_string = "%6s %s\n"
    ix = 0
    for stack_frame in current_stack:
        if ix < stack_frame_ix:
            ix += 1
            continue
        # I want the line number shown to be the line where you find the line
        # shown.
        try:
            line_num = str(current_stack[ix + 1][2])
        except IndexError:
            line_num = ""
        func_name = str(stack_frame[3])
        if func_name == "?":
            # "?" is the name used when code is not in a function.
            func_name = "(none)"

        if func_name == "<module>":
            # If the func_name is the "main" program, we simply get the
            # command line call string.
            func_and_args = ' '.join(sys.argv)
        else:
            # Get the program arguments.
            arg_vals = inspect.getargvalues(stack_frame[0])
            function_parms = arg_vals[0]
            frame_locals = arg_vals[3]

            args_list = []
            for arg_name in function_parms:
                # Get the arg value from frame locals.
                arg_value = frame_locals[arg_name]
                args_list.append(arg_name + " = " + repr(arg_value))
            args_str = "(" + ', '.join(map(str, args_list)) + ")"

            # Now we need to print this in a nicely-wrapped way.
            func_and_args = func_name + " " + args_str

        buffer += sindent(format_string % (line_num, func_and_args), indent)
        ix += 1

    buffer += sprint_dashes(indent)

    return buffer

###############################################################################


###############################################################################
def sprint_executing(stack_frame_ix=None):

    r"""
    Print a line indicating what function is executing and with what parameter
    values.  This is useful for debugging.

    Sample output:

    #(CDT) 2016/08/25 17:54:27 - Executing: func1 (x = 1)

    Description of arguments:
    stack_frame_ix                  The index of the stack frame whose
                                    function info should be returned.  If the
                                    caller does not specify a value, this
                                    function will set the value to 1 which is
                                    the index of the caller's stack frame.  If
                                    the caller is the wrapper function
                                    "print_executing", this function will bump
                                    it up by 1.
    """

    # If user wants default stack_frame_ix.
    if stack_frame_ix is None:
        func_name = sys._getframe().f_code.co_name
        caller_func_name = sys._getframe(1).f_code.co_name
        if caller_func_name.endswith(func_name[1:]):
            stack_frame_ix = 2
        else:
            stack_frame_ix = 1

    stack_frame = inspect.stack()[stack_frame_ix]

    func_name = str(stack_frame[3])
    if func_name == "?":
        # "?" is the name used when code is not in a function.
        func_name = "(none)"

    if func_name == "<module>":
        # If the func_name is the "main" program, we simply get the command
        # line call string.
        func_and_args = ' '.join(sys.argv)
    else:
        # Get the program arguments.
        arg_vals = inspect.getargvalues(stack_frame[0])
        function_parms = arg_vals[0]
        frame_locals = arg_vals[3]

        args_list = []
        for arg_name in function_parms:
            # Get the arg value from frame locals.
            arg_value = frame_locals[arg_name]
            args_list.append(arg_name + " = " + repr(arg_value))
        args_str = "(" + ', '.join(map(str, args_list)) + ")"

        # Now we need to print this in a nicely-wrapped way.
        func_and_args = func_name + " " + args_str

    return sprint_time() + "Executing: " + func_and_args + "\n"

###############################################################################


###############################################################################
def sprint_pgm_header(indent=0,
                      linefeed=1):

    r"""
    Return a standardized header that programs should print at the beginning
    of the run.  It includes useful information like command line, pid,
    userid, program parameters, etc.

    Description of arguments:
    indent                          The number of characters to indent each
                                    line of output.
    linefeed                        Indicates whether a line feed be included
                                    at the beginning and end of the report.
    """

    loc_col1_width = col1_width + indent

    buffer = ""
    if linefeed:
        buffer = "\n"

    if robot_env:
        suite_name = BuiltIn().get_variable_value("${suite_name}")
        buffer += sindent(sprint_time("Running test suite \"" + suite_name +
                          "\".\n"), indent)

    buffer += sindent(sprint_time() + "Running " + pgm_name + ".\n", indent)
    buffer += sindent(sprint_time() + "Program parameter values, etc.:\n\n",
                      indent)
    buffer += sprint_varx("command_line", ' '.join(sys.argv), 0, indent,
                          loc_col1_width)
    # We want the output to show a customized name for the pid and pgid but
    # we want it to look like a valid variable name.  Therefore, we'll use
    # pgm_name_var_name which was set when this module was imported.
    buffer += sprint_varx(pgm_name_var_name + "_pid", os.getpid(), 0, indent,
                          loc_col1_width)
    buffer += sprint_varx(pgm_name_var_name + "_pgid", os.getpgrp(), 0, indent,
                          loc_col1_width)
    userid_num = str(os.geteuid())
    try:
        username = os.getlogin()
    except OSError:
        if userid_num == "0":
            username = "root"
        else:
            username = "?"
    buffer += sprint_varx("uid", userid_num + " (" + username +
                          ")", 0, indent, loc_col1_width)
    buffer += sprint_varx("gid", str(os.getgid()) + " (" +
                          str(grp.getgrgid(os.getgid()).gr_name) + ")", 0,
                          indent, loc_col1_width)
    buffer += sprint_varx("host_name", socket.gethostname(), 0, indent,
                          loc_col1_width)
    try:
        DISPLAY = os.environ['DISPLAY']
    except KeyError:
        DISPLAY = ""
    buffer += sprint_varx("DISPLAY", DISPLAY, 0, indent,
                          loc_col1_width)
    # I want to add code to print caller's parms.

    # __builtin__.arg_obj is created by the get_arg module function,
    # gen_get_options.
    try:
        buffer += ga.sprint_args(__builtin__.arg_obj, indent)
    except AttributeError:
        pass

    if robot_env:
        # Get value of global parm_list.
        parm_list = BuiltIn().get_variable_value("${parm_list}")

        for parm in parm_list:
            parm_value = BuiltIn().get_variable_value("${" + parm + "}")
            buffer += sprint_varx(parm, parm_value, 0, indent, loc_col1_width)

        # Setting global program_pid.
        BuiltIn().set_global_variable("${program_pid}", os.getpid())

    if linefeed:
        buffer += "\n"

    return buffer

###############################################################################


###############################################################################
def sprint_error_report(error_text="\n",
                        indent=2,
                        format=None):

    r"""
    Return a string with a standardized report which includes the caller's
    error text, the call stack and the program header.

    Description of args:
    error_text                      The error text to be included in the
                                    report.  The caller should include any
                                    needed linefeeds.
    indent                          The number of characters to indent each
                                    line of output.
    format                          Long or short format.  Long includes
                                    extras like lines of dashes, call stack,
                                    etc.
    """

    # Process input.
    indent = int(indent)
    if format is None:
        if robot_env:
            format = 'short'
        else:
            format = 'long'
    error_text = error_text.rstrip('\n') + '\n'

    if format == 'short':
        return sprint_error(error_text)

    buffer = ""
    buffer += sprint_dashes(width=120, char="=")
    buffer += sprint_error(error_text)
    buffer += "\n"
    # Calling sprint_call_stack with stack_frame_ix of 0 causes it to show
    # itself and this function in the call stack.  This is not helpful to a
    # debugger and is therefore clutter.  We will adjust the stack_frame_ix to
    # hide that information.
    stack_frame_ix = 2
    caller_func_name = sprint_func_name(2)
    if caller_func_name.endswith("print_error_report"):
        stack_frame_ix += 1
    if not robot_env:
        buffer += sprint_call_stack(indent, stack_frame_ix)
    buffer += sprint_pgm_header(indent)
    buffer += sprint_dashes(width=120, char="=")

    return buffer

###############################################################################


###############################################################################
def sprint_issuing(cmd_buf,
                   test_mode=0):

    r"""
    Return a line indicating a command that the program is about to execute.

    Sample output for a cmd_buf of "ls"

    #(CDT) 2016/08/25 17:57:36 - Issuing: ls

    Description of args:
    cmd_buf                         The command to be executed by caller.
    test_mode                       With test_mode set, your output will look
                                    like this:

    #(CDT) 2016/08/25 17:57:36 - (test_mode) Issuing: ls

    """

    buffer = sprint_time()
    if test_mode:
        buffer += "(test_mode) "
    buffer += "Issuing: " + cmd_buf + "\n"

    return buffer

###############################################################################


###############################################################################
def sprint_pgm_footer():

    r"""
    Return a standardized footer that programs should print at the end of the
    program run.  It includes useful information like total run time, etc.
    """

    buffer = "\n" + sprint_time() + "Finished running " + pgm_name + ".\n\n"

    total_time = time.time() - start_time
    total_time_string = "%0.6f" % total_time

    buffer += sprint_varx(pgm_name_var_name + "_runtime", total_time_string)
    buffer += "\n"

    return buffer

###############################################################################


###############################################################################
def sprint(buffer=""):

    r"""
    Simply return the user's buffer.  This function is used by the qprint and
    dprint functions defined dynamically below, i.e. it would not normally be
    called for general use.

    Description of arguments.
    buffer                          This will be returned to the caller.
    """

    return str(buffer)

###############################################################################


###############################################################################
def sprintn(buffer=""):

    r"""
    Simply return the user's buffer with a line feed.  This function is used
    by the qprint and dprint functions defined dynamically below, i.e. it
    would not normally be called for general use.

    Description of arguments.
    buffer                          This will be returned to the caller.
    """

    buffer = str(buffer) + "\n"

    return buffer

###############################################################################


###############################################################################
def gp_debug_print(buffer):

    r"""
    Print buffer to stdout only if gen_print_debug is set.

    This function is intended for use only by other functions in this module.

    Description of arguments:
    buffer                          The string to be printed.
    """

    if not gen_print_debug:
        return

    if robot_env:
        BuiltIn().log_to_console(buffer)
    else:
        print(buffer)

###############################################################################


###############################################################################
def get_var_value(var_value=None,
                  default=1,
                  var_name=None):

    r"""
    Return either var_value, the corresponding global value or default.

    If var_value is not None, it will simply be returned.

    If var_value is None, this function will return the corresponding global
    value of the variable in question.

    Note: For global values, if we are in a robot environment,
    get_variable_value will be used.  Otherwise, the __builtin__ version of
    the variable is returned (which are set by gen_arg.py functions).

    If there is no global value associated with the variable, default is
    returned.

    This function is useful for other functions in setting default values for
    parameters.

    Example use:

    def my_func(quiet=None):

      quiet = int(get_var_value(quiet, 0))

    Example calls to my_func():

    In the following example, the caller is explicitly asking to have quiet be
    set to 1.

    my_func(quiet=1)

    In the following example, quiet will be set to the global value of quiet,
    if defined, or to 0 (the default).

    my_func()

    Description of arguments:
    var_value                       The value to be returned (if not equal to
                                    None).
    default                         The value that is returned if var_value is
                                    None and there is no corresponding global
                                    value defined.
    var_name                        The name of the variable whose value is to
                                    be returned.  Under most circumstances,
                                    this value need not be provided.  This
                                    function can figure out the name of the
                                    variable passed as var_value.  One
                                    exception to this would be if this
                                    function is called directly from a .robot
                                    file.
    """

    if var_value is not None:
        return var_value

    if var_name is None:
        var_name = get_arg_name(None, 1, 2)

    if robot_env:
        var_value = BuiltIn().get_variable_value("${" + var_name + "}",
                                                 default)
    else:
        var_value = getattr(__builtin__, var_name, default)

    return var_value

###############################################################################


# hidden_text is a list of passwords which are to be replaced with asterisks
# by print functions defined in this module.
hidden_text = []
# password_regex is created based on the contents of hidden_text.
password_regex = ""


###############################################################################
def register_passwords(*args):

    r"""
    Register one or more passwords which are to be hidden in output produced
    by the print functions in this module.

    Note:  Blank password values are NOT registered.  They are simply ignored.

    Description of argument(s):
    args                            One or more password values.  If a given
                                    password value is already registered, this
                                    function will simply do nothing.
    """

    global hidden_text
    global password_regex

    for password in args:
        if password == "":
            break
        if password in hidden_text:
            break

        # Place the password into the hidden_text list.
        hidden_text.append(password)
        # Create a corresponding password regular expression.  Escape regex
        # special characters too.
        password_regex = '(' +\
            '|'.join([re.escape(x) for x in hidden_text]) + ')'

###############################################################################


###############################################################################
def replace_passwords(buffer):

    r"""
    Return the buffer but with all registered passwords replaced by a string
    of asterisks.


    Description of argument(s):
    buffer                          The string to be returned but with
                                    passwords replaced.
    """

    global password_regex

    if int(os.environ.get("DEBUG_SHOW_PASSWORDS", "0")):
        return buffer

    if password_regex == "":
        # No passwords to replace.
        return buffer

    return re.sub(password_regex, "********", buffer)

###############################################################################


###############################################################################
# In the following section of code, we will dynamically create print versions
# for each of the sprint functions defined above.  So, for example, where we
# have an sprint_time() function defined above that returns the time to the
# caller in a string, we will create a corresponding print_time() function
# that will print that string directly to stdout.

# It can be complicated to follow what's being created by the exec statements
# below.  Here is an example of the print_time() function that will be created:

# def print_time(*args):
#     s_func = getattr(sys.modules[__name__], "sprint_time")
#     sys.stdout.write(s_func(*args))
#     sys.stdout.flush()

# Here are comments describing the 3 lines in the body of the created function.
# Create a reference to the "s" version of the given function in s_func (e.g.
# if this function name is print_time, we want s_funcname to be "sprint_time").
# Call the "s" version of this function passing it all of our arguments.
# Write the result to stdout.

# func_names contains a list of all print functions which should be created
# from their sprint counterparts.
func_names = ['print_time', 'print_timen', 'print_error', 'print_varx',
              'print_var', 'print_vars', 'print_dashes', 'indent',
              'print_call_stack', 'print_func_name', 'print_executing',
              'print_pgm_header', 'print_issuing', 'print_pgm_footer',
              'print_error_report', 'print', 'printn']

# stderr_func_names is a list of functions whose output should go to stderr
# rather than stdout.
stderr_func_names = ['print_error', 'print_error_report']

gp_debug_print("robot_env: " + str(robot_env))
for func_name in func_names:
    gp_debug_print("func_name: " + func_name)
    if func_name in stderr_func_names:
        output_stream = "stderr"
    else:
        output_stream = "stdout"

    func_def_line = "def " + func_name + "(*args):"
    s_func_line = "    s_func = getattr(sys.modules[__name__], \"s" +\
        func_name + "\")"
    # Generate the code to do the printing.
    if robot_env:
        func_print_lines = \
            [
                "    BuiltIn().log_to_console(replace_passwords" +
                "(s_func(*args)),"
                " stream='" + output_stream + "',"
                " no_newline=True)"
            ]
    else:
        func_print_lines = \
            [
                "    sys." + output_stream +
                ".write(replace_passwords(s_func(*args)))",
                "    sys." + output_stream + ".flush()"
            ]

    # Create an array containing the lines of the function we wish to create.
    func_def = [func_def_line, s_func_line] + func_print_lines
    # We don't want to try to redefine the "print" function, thus the if
    # statement.
    if func_name != "print":
        pgm_definition_string = '\n'.join(func_def)
        gp_debug_print(pgm_definition_string)
        exec(pgm_definition_string)

    # Insert a blank line which will be overwritten by the next several
    # definitions.
    func_def.insert(1, "")

    # Define the "q" (i.e. quiet) version of the given print function.
    func_def[0] = "def q" + func_name + "(*args):"
    func_def[1] = "    if int(get_var_value(None, 0, \"quiet\")): return"
    pgm_definition_string = '\n'.join(func_def)
    gp_debug_print(pgm_definition_string)
    exec(pgm_definition_string)

    # Define the "d" (i.e. debug) version of the given print function.
    func_def[0] = "def d" + func_name + "(*args):"
    func_def[1] = "    if not int(get_var_value(None, 0, \"debug\")): return"
    pgm_definition_string = '\n'.join(func_def)
    gp_debug_print(pgm_definition_string)
    exec(pgm_definition_string)

    # Define the "l" (i.e. log) version of the given print function.
    func_def_line = "def l" + func_name + "(*args):"
    func_print_lines = \
        [
            "    logging.log(getattr(logging, 'INFO'), s_func(*args))"
        ]

    func_def = [func_def_line, s_func_line] + func_print_lines
    if func_name != "print_varx" and func_name != "print_var":
        pgm_definition_string = '\n'.join(func_def)
        gp_debug_print(pgm_definition_string)
        exec(pgm_definition_string)

    if func_name == "print" or func_name == "printn":
        gp_debug_print("")
        continue

    # Create abbreviated aliases (e.g. spvar is an alias for sprint_var).
    alias = re.sub("print_", "p", func_name)
    prefixes = ["", "s", "q", "d", "l"]
    for prefix in prefixes:
        pgm_definition_string = prefix + alias + " = " + prefix + func_name
        gp_debug_print(pgm_definition_string)
        exec(pgm_definition_string)

    gp_debug_print("")

###############################################################################
