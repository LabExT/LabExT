#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
import logging
import os.path
import re
import threading

import importlib_metadata
from os import makedirs
from os.path import join, dirname, abspath, exists, basename
from pathlib import Path
from tkinter import TclError, Toplevel, ttk, Label

import unicodedata

def get_labext_version() -> tuple[str, str]:
    """
    Finds the release version and the current Git commit the file is on.

    :return: a tuple of two strings: the first string is the version as defined in the setup.py file, the second is the
    short-ref of the last Git commit of the LabExT sourcecode
    """

    # read version from python builtin methods
    try:
        version_str = importlib_metadata.distribution("LabExT_pkg").version
    except importlib_metadata.PackageNotFoundError:
        # pkg_resources cannot find LabExT, lets manually try to parse from setup.py as stored in the Git repo
        version_str = None

    if version_str is None:
        # read version from setup.py
        try:
            setup_py_path = join(dirname(dirname(__file__)), 'setup.py')
            with open(setup_py_path, 'r') as fp:
                content = fp.read()
        except FileNotFoundError:
            # if package is not installed, and we cannot find the setup.py file, we
            # effectively cannot find out our package version :/
            content = ''

        m = re.search(r"version=['\"][0-9]+\.[0-9]+\.[0-9]+['\"]", content)
        if m is not None:
            version_str = m[0].split('=')[1][1:-1]  # get the version numbers alone
        else:
            version_str = '-'

    # access git folder relative to this file
    git_folder_path = join(dirname(dirname(__file__)), '.git')
    if exists(git_folder_path):

        with open(join(git_folder_path, 'HEAD'), 'r') as fp_head:
            head_ref = fp_head.read()
        try:
            head_ref = head_ref.split(":", 1)[1].strip()
        except IndexError:
            # in case there is no :, the HEAD file just includes the hash for the checked-out commit
            long_ref = head_ref
            head_ref = None

        if head_ref is not None:
            # in case we have to follow a reference path to get the commit hash
            with open(join(git_folder_path, str(head_ref))) as fp_ref:
                long_ref = fp_ref.read().strip()

        git_short_ref = long_ref[0:8]
    else:
        git_short_ref = '-'

    # LabExT does not seem to be a clone from Git, version is undefined
    return version_str, git_short_ref


def get_author_list() -> list[str]:
    """
    Returns a list of all authors as listed in the AUTHORS.md file.
    The format of each string should be:
    Firstname Lastname <email@email.com>
    """
    # utf-8 decoding is needed because of umlauts in German names
    with open(join(dirname(dirname(__file__)), 'AUTHORS.md'), encoding='utf-8') as authors_file:
        authors_lines = authors_file.readlines()
    authors = [line[1:].strip() for line in authors_lines if line[0] == '*']
    return authors


def get_visa_lib_string() -> str:
    """
    Gets the visa library string specified in the LabExT settings. See
    https://pyvisa.readthedocs.io/en/latest/introduction/configuring.html

    Returns
    -------
    A pyvisa-compatible settings string. If the settings file is not found, it returns "@py" to use the pyvisa-py
    implementation.
    """
    cfg_path = get_configuration_file_path('instruments.config', ignore_missing=True)
    if not os.path.isfile(cfg_path):
        return '@py'
    else:
        with open(cfg_path, 'r') as fp:
            cfg_content = json.load(fp)
        return cfg_content['Visa Library Path']


def get_visa_address(name: str) -> list[dict]:
    """Gets the VISA addresses of all wanted instruments, as
    specified in instruments.config file.

    Parameters
    ----------
    name : string
        Name of the type of instrument wanted (Laser, PowerMeter, etc.)
        Any enumeration at the end of the instrument name gets ignored: "SMU 2" <-> "SMU"

    Returns
    -------
    List of dictionary with all available instruments for that type.

    Raises
    ------
    RuntimeError
        If no instrument addresses found for specified type,
        raises RuntimeError.
    """
    instr_config_path_in_module = 'instruments.config'
    file_path = get_configuration_file_path(instr_config_path_in_module, ignore_missing=False)
    logging.getLogger().debug("Using instruments.config at: " + str(file_path))
    with open(file_path) as f:
        instrument_dict = json.load(f)['Instruments']

    # Remove Enumeration "SMU 2" -> "SMU"
    # This is needed to allow multiple instruments with the same name
    name_no_enum = re.sub(r" [0-9]+$", "", name)

    # we have a dict of instrument types,
    # key is instrument type (HAS TO BE UNIQUE!)
    # each instrument type contains a list (value)
    # of instruments belonging to that type
    # see wiki for more information
    available_instruments = instrument_dict.get(name_no_enum)

    if available_instruments is None:
        raise RuntimeError("Fatal Error, no instrument type " + str(name) + " found!")
    else:
        return available_instruments


def find_dict_with_ignore(target, search_list, ignore_keys):
    """
    Search for the dictionary target within the list of dictionaries search_list.
    Any keys in ignore_keys are completely ignored in the search.
    The index of the first dictionary where keys and values match in search_list is returned.
    :param target: the dictionary to be found
    :param search_list: the list of dictionaries of which one is to be found.
    :param ignore_keys:
    :return: The index of the first dictionary matching target. None if no match was found.
    """

    target_clean = {k: v for k, v in target.items() if k not in ignore_keys}

    for cidx, candidate in enumerate(search_list):
        cand_clean = {k: v for k, v in candidate.items() if k not in ignore_keys}
        if target_clean == cand_clean:
            return cidx
    return None
    

def make_filename_compliant(value: str, force_lower: bool = False) -> str:
    """
    Makes a string filename compliant.
    From: https://github.com/django/django/blob/master/django/utils/text.py

    Convert to ASCII. Convert spaces to hyphens.
    Remove characters that aren't alphanumerics, underscores, or hyphens.
    Convert to lowercase. Also strip leading and trailing whitespace.
    """
    value = str(value)
    value = unicodedata.normalize('NFKD', value).encode('ascii', 'ignore').decode('ascii')
    value = re.sub(r'[^\w\s-]', '', value).strip()
    if force_lower:
        value = value.lower()
    return re.sub(r'[-\s]+', '-', value)


def setup_user_settings_directory(makedir_if_needed: bool = False) -> str:
    """
    Setups the LabExT settings directory in the users home folder.

    Parameters
    ----------
    makedir_if_needed
        (optional) boolean flag default false, set to True if you want to create the settings directory in case it
        doesn't exist

    Returns
    -------
        str, the path to the LabExT settings directory
    """
    settings_directory = abspath(join(str(Path.home()), ".labext"))
    if makedir_if_needed:
        makedirs(settings_directory, exist_ok=True)
    return settings_directory


def get_configuration_file_path(config_file_path_in_settings_dir: str, ignore_missing: bool = True) -> str:
    """ Searches for a given configuration file in the users labext configuration directory at: ~/.labext/

    Should be used in two cases:
        ignore_missing=False - if you want to find a configuration file to load it within LabExT
        ignore_missing=True - if you want to find the path where you should write a non-existing configuration file

    Parameters
    ----------
    config_file_path_in_settings_dir:
        path to the file within the settings directory
    ignore_missing
        (optional) boolean flag by default True, set to False if you want to raise an error if the file does not exist

    Returns
    -------
        the path to the found configuration file
    """
    config_fn = basename(config_file_path_in_settings_dir)
    settings_directory = setup_user_settings_directory(makedir_if_needed=False)
    path_in_settings_dir = abspath(join(settings_directory, config_fn))
    if exists(path_in_settings_dir):
        config_path = path_in_settings_dir
    else:
        if ignore_missing:
            config_path = path_in_settings_dir
        else:
            raise FileNotFoundError(config_file_path_in_settings_dir)
    return config_path


def run_with_wait_window(tk_root, description: str, function):
    """
    Use this as decorator to run the given function in a second thread and display a wait window.
    You must supply a description string.
    This function does not provide a return value.
    """
    new_window = Toplevel(tk_root)
    new_window.attributes('-topmost', 'true')
    prog = ttk.Progressbar(new_window, mode='indeterminate')
    prog.grid(row=1, column=0)
    prog.start(50)
    lbl = Label(new_window, text=description)
    lbl.grid(row=0, column=0)

    def async_exec_func():
        try:
            function()
        finally:
            new_window.destroy()

    threading.Thread(target=async_exec_func, name="wait window: " + str(description)).start()
    tk_root.wait_window(new_window)


def try_to_lift_window(window):
    if window is None:
        return False
    
    try:
        window.deiconify()
        window.lift()
        window.focus_set()
        return True
    except TclError:
        return False
