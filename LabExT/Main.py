#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import sys
import traceback
from argparse import ArgumentParser
from logging.handlers import RotatingFileHandler
from os.path import abspath, dirname, join
from tkinter import Tk
from PIL import ImageTk

if __name__ == '__main__':
    # if we are running this file directly, i.e. without installing LabExT as a module,
    # we need to extend the python path with the directory above the LabExT module folder
    # so we are temporarily "installing" the module for this Python instance
    sys.path.append(dirname(dirname(abspath(__file__))))


# import LabExT submodules
from LabExT.ExperimentManager import ExperimentManager
from LabExT.Logs.CustomLogFormatter import CustomLogFormatter
from LabExT.Logs.MaxLevelFilter import MaxLevelFilter
from LabExT.Utils import get_configuration_file_path, setup_user_settings_directory


# launch
def main():

    #
    # create Tk root element
    #

    tk_root = Tk()

    #
    # parse arguments
    #

    argparser = ArgumentParser(
        description="""LabExT - Laboratory Experiment Tool is an automated Laboratory measurement software.
                           It allows to execute arbitrary measurements using SCPI compatible instruments on devices
                           under test. This can be used for electro-optic characterization of nano-photonic devices on
                           silicon wafers. To facilitate the work, automatic movement of piezo-actuated precision
                           stages is included for multi-DUT experiments."""
    )
    argparser.add_argument('-l', '--log-file-level', type=str,
                           help='Logging level of the log file, i.e. all messages of the level at least chosen here are'
                                ' printed to the log file, any lower levels are omitted. The lowest level "debug" '
                                'prints all SCPI communication to the log file, too! By default set to "info".',
                           choices=["debug", "info", "warning", "error", "critical"],
                           default="info")
    argparser.add_argument("-v", "--verbose",
                           help="Makes the console output verbose. This flag is ignored if -q or -V are set.",
                           action="store_true",
                           dest='verbose',
                           default=False)
    argparser.add_argument("-V", "--Verbose",
                           help="Makes the console output very verbose. This flag is ignored if -q is set.",
                           action="store_true",
                           dest="Verbose",
                           default=False)
    argparser.add_argument("-q", "--quiet",
                           help="Hides warnings from console output.",
                           action="store_true",
                           dest="quiet",
                           default=False)
    args = argparser.parse_args()

    #
    # setup logging
    #

    # create users settings folder
    setup_user_settings_directory(makedir_if_needed=True)

    # get root logger instance
    logger = logging.getLogger()
    logger.setLevel("DEBUG")  # root logger needs to capture all messages

    # create custom formatter which truncates line lengths
    clf = CustomLogFormatter()

    # create console output for warnings
    sh = logging.StreamHandler(sys.stderr)
    sh.setLevel(logging.ERROR if args.quiet else logging.WARNING)
    sh.setFormatter(clf)
    logger.addHandler(sh)

    # create console output for infos and debugs
    if not args.quiet and (args.verbose or args.Verbose):
        cons = logging.StreamHandler(sys.stdout)
        cons.setLevel(logging.DEBUG if args.Verbose else logging.INFO)
        cons.addFilter(MaxLevelFilter(logging.INFO))
        cons.setFormatter(clf)
        logger.addHandler(cons)

    # create log file rotating handler for debugs and above
    log_file_path = get_configuration_file_path('debug.log')
    rfh = RotatingFileHandler(log_file_path, mode='a', maxBytes=100e6, backupCount=5)
    rfh.setLevel(str.upper(args.log_file_level))  # defaults to DEBUG
    rfh.setFormatter(clf)
    logger.addHandler(rfh)

    # make sure all uncaught exceptions are written to the log
    def log_except_hook(*exc_info):
        text = "".join(traceback.format_exception(*exc_info))
        logging.error("Unhandled exception: %s", text)

    # write all uncaught exceptions in the log
    tk_root.report_callback_exception = log_except_hook

    # load icon
    tk_root.iconphoto(True, ImageTk.PhotoImage(file=join(dirname(__file__), 'icon.png')))

    # greet user and start logging
    logger.info('==============================================================================')
    logger.info('==============================================================================')
    logger.info('LabExT started with arguments ' + str(sys.argv))

    #
    # create Experiment Manager master instance
    #

    ExperimentManager(tk_root, log_file_path)

    #
    # start the GUI (blocking call)
    #

    logger.debug('Starting mainloop now.')
    tk_root.mainloop()

    #
    # LabExT shutdown
    #

    logger.info('Stopped.')
    logger.info('==============================================================================')
    logger.info('==============================================================================')


if __name__ == '__main__':
    main()
