#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.

This engine is the main driver behind the documentation. It uses Jinja2 to generate a html file from a templated file.

It first reads all measurements, cleans the docstrings and genereates html. This is then passed to jinja, which
uses the template to generate the final index.html file.
"""

import tempfile
from os import makedirs
from os.path import dirname, join
from shutil import rmtree, copytree

try:
    import mkdocs.commands.build
    import mkdocs.config

    MKDOCS_PRESENT = True
except ImportError:
    MKDOCS_PRESENT = False

from LabExT.DocumentationEngine.MarkdownCleaner import remove_indentation_from_docstring
from LabExT.Utils import make_filename_compliant


class DocumentationEngine:
    """
    This class stores all metadata for the documentation. It contains member function
    for parsing and generating the html.
    """

    def __init__(self, experiment_manager):
        """
        Constructor for DocumentationEngine. Initializes all needed variables.
        """
        self.docu_available = MKDOCS_PRESENT

        self._experiment_manager = experiment_manager
        self.meas_class_dict = None
        self.instr_class_dict = None

        self.temp_dir = None
        self.temp_file = None

    def cleanup(self):
        """
        To be called on LabExT exit. Removes the temporary directory, as windows does not do this automatically.
        """
        if self.temp_dir is not None:
            rmtree(self.temp_dir)

    def generate_index_html(self):
        """
        This function generates the Addon Documentation. It is called after the dynamic loading of measurements and
        instruments from the Experiment Manager. It does about this:
        - generate a new temporary directory (where depends on OS)
        - gather the docstrings of all loaded measurements (docstrings are markdown formatted)
        - gather the docstrings of all loaded instruments (docstrings are markdown formatted)
        - save all the docstrings to the temp. directory
        - run the build stage of mkdocs to generate the HTML webpage
        """
        if not MKDOCS_PRESENT:
            self._experiment_manager.logger.warning('MKDocs is not installed. Not compiling Addon documentation.')
            return

        # generate temporary directory
        temp_dir_root = tempfile.mkdtemp()
        self.temp_dir = join(temp_dir_root, 'mkdocs')
        doc_root_dir = join(dirname(dirname(__file__)), 'DocumentationEngine', 'mkdocs_files')
        copytree(doc_root_dir, self.temp_dir)

        # get markdown docstring of all loaded measurements
        self.meas_class_dict = self._experiment_manager.exp.measurements_classes
        all_meas_file_names = []
        meas_md_file_dir = join(self.temp_dir, 'docs', 'Measurements')
        makedirs(meas_md_file_dir, exist_ok=True)
        for meas_name, meas_class in self.meas_class_dict.items():
            sanitized_md = remove_indentation_from_docstring(meas_class.__doc__)
            this_fn = make_filename_compliant(meas_name) + '.md'
            with open(join(meas_md_file_dir, this_fn), 'w') as fp:
                fp.write(sanitized_md)
            all_meas_file_names.append(this_fn)

        # get markdown docstring of all loaded instruments
        self.instr_class_dict = self._experiment_manager.instrument_api.instruments
        all_instr_file_names = []
        instr_md_file_dir = join(self.temp_dir, 'docs', 'Instruments')
        makedirs(instr_md_file_dir, exist_ok=True)
        for instr_name, instr_class in self.instr_class_dict.items():
            sanitized_md = remove_indentation_from_docstring(instr_class.__doc__)
            this_fn = make_filename_compliant(instr_name) + '.md'
            with open(join(instr_md_file_dir, this_fn), 'w') as fp:
                fp.write(sanitized_md)
            all_instr_file_names.append(this_fn)

        # add the navigation to the mkdocs config file:
        with open(join(self.temp_dir, 'mkdocs.yml'), 'a') as fp:
            fp.write('nav:\n')
            fp.write("  - index.md\n")
            fp.write("  - 'Measurements':\n")
            for mfn in sorted(all_meas_file_names, key=lambda v: v.upper()):
                fp.write(f'    - Measurements/{mfn:s}\n')
            fp.write("  - 'Instruments':\n")
            for mfn in sorted(all_instr_file_names, key=lambda v: v.upper()):
                fp.write(f'    - Instruments/{mfn:s}\n')

        # run mkdocs build process
        mkd_config = {
            'docs_dir': join(self.temp_dir, 'docs'),
            'site_dir': join(self.temp_dir, 'site'),
            'config_file': join(self.temp_dir, 'mkdocs.yml')
        }
        mkdocs.commands.build.build(config=mkdocs.config.load_config(**mkd_config))

        # adapt this to mkdocs output
        self.temp_file = join(self.temp_dir, 'site', 'index.html')
