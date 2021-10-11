#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.

Contains a two functions to clean markdown code. One simply cleans the markdown, while the other strips all but
the first paragraph after cleaning.
"""


def remove_indentation_from_docstring(docstring: str) -> str:
    """
    This function sanitizes a docstring. This is necessary, e.g. for following markdown compilation as
    docstrings might have an unknown amount of whitespace infront of every line of text due to the necessity to
    indent in Python.

    Parameters
    ----------
    docstring : string
    The docstring of a class containing indented, markdown formatted text.

    Returns
    -------
    The sanitized string: every line has common indentation removed.
    """

    if docstring is None:
        docstring = ''

    lines = docstring.split('\n')

    # if we have a line with only whitespace, add newline to previous line s.t. whitespace cleaning works afterwards
    for lidx in range(1, len(lines)):
        if len(lines[lidx].strip()) == 0:
            lines[lidx-1] += '\n'
            lines[lidx] = ''

    # remove all now empty lines
    while '' in lines:
        lines.remove('')

    # Goal: remove all leading whitespace if ALL lines have it in common
    while len(lines) > 0:

        # check if all lines have 1 whitespace infront
        if len("".join([l[0] for l in lines]).strip()) > 0:
            break

        # cut away said whitespace
        for lidx in range(len(lines)):
            lines[lidx] = lines[lidx][1:]

        # remove all now empty lines
        while '' in lines:
            lines.remove('')

    sanitized = "\n".join(lines)
    return sanitized


def get_short_docstring(docstring: str) -> str:
    """
    This function sanitizes a docstring and shortens it to be only a paragraph long. Furthermore, the title gets
    removed.

    Parameters
    ----------
    docstring : string
    The docstring of a class containing indented, markdown formatted text.

    Returns
    -------
    The sanitized string: every line has common indentation removed, its only one paragraph long and
    the title has been removed.
    """
    cleaned = remove_indentation_from_docstring(docstring)
    lines = cleaned.split('\n')
    starts_with_pound = [i for i in range(len(lines)) if lines[i].startswith('#')]
    if len(starts_with_pound) < 2:
        return cleaned
    first_chapter_lines = [lines[i] for i in range(starts_with_pound[0] + 1, starts_with_pound[1])]
    return '\n'.join(first_chapter_lines)
