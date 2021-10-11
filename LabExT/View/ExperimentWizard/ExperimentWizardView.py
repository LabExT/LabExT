#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Toplevel, Label, Button


class ExperimentWizardHelperFrame (Frame):
    def __init__(self, model, view, controller, parent):
        Frame.__init__(self, parent)

        self.model = model
        self.view = view
        self.controller = controller

        self.grid(row=0, column=0)

        label_title = Label(self, text='Welcome to the ExperimentWizard.')
        label_title.configure(font='Helvetica 12 bold')
        label_title.grid(row=0, column=0)

        label_description = Label(self, text=("We will guide you through the different steps to start a new experiment."
                                              " Press F1 for help."))
        label_description.configure(font='Helvetica 10')
        label_description.grid(row=1, column=0)

        path = controller.experiment_manager.chip._path if controller.experiment_manager.chip else 'None'
        choose_chip_label = Label(self, text='0. Choose a Chip. (loaded file: ' + path + ')')
        choose_chip_label.configure(font='Helvetica 10', bg='yellow')
        choose_chip_label.grid(row=2, column=0, sticky='w')

        self.view.labels.append(choose_chip_label)

        choose_devices_label = Label(self, text='1. Choose devices you want to perform measurements on.')
        choose_devices_label.configure(font='Helvetica 10')
        choose_devices_label.grid(row=3, column=0, sticky='w')

        self.view.labels.append(choose_devices_label)

        choose_measurements_label = Label(self, text='2. Choose measurements to perform.')
        choose_measurements_label.configure(font='Helvetica 10')
        choose_measurements_label.grid(row=4, column=0, sticky='w')

        self.view.labels.append(choose_measurements_label)

        choose_instruments_label = Label(self, text="3. Choose the instruments for the measurements.")
        choose_instruments_label.configure(font='Helvetica 10')
        choose_instruments_label.grid(row=5, column=0, sticky='w')

        self.view.labels.append(choose_instruments_label)

        choose_settings_label = Label(self, text='4. Choose measurement specific settings.')
        choose_settings_label.configure(font='Helvetica 10')
        choose_settings_label.grid(row=6, column=0, sticky='w')

        self.view.labels.append(choose_settings_label)

        ready_label = Label(self,
                            text='You are all set! Please click on \'Continue\' to close ' +
                                 'the ExperimentWizard and start your measurements ' +
                                 'by clicking on the \'Run\' button.'
                            )
        ready_label.configure(font='Helvetica 10')
        ready_label.grid(row=7, column=0)

        self.view.labels.append(ready_label)

        self.continue_button = Button(self,
                                      text='Continue',
                                      state='disabled',
                                      command=self.controller.finish_wizard)
        self.continue_button.grid(row=8, column=0, sticky='e')


class ExperimentWizardMainWindow (Toplevel):
    def __init__(self, model, view, controller, parent):
        Toplevel.__init__(self, parent)
        self.geometry('+%d+%d' % (0, 0))
        self.attributes('-topmost', 'true')
        self.protocol('WM_DELETE_WINDOW', controller.close_wizard)
        self.bind('<F1>', controller.experiment_manager.show_documentation)

        self.helper_window = ExperimentWizardHelperFrame(model, view, controller, self)


class ExperimentWizardView:
    def __init__(self, model, controller, parent):
        self.model = model
        self.controller = controller

        self.parent = parent

        # list of all the labels, used to track user steps and coloring
        self.labels = []

        # set up and run the main window
        self.main_window = ExperimentWizardMainWindow(self.model, self, self.controller, self.parent)

    def new_toplevel(self, frame_class, exp_manager, callback):
        new_w = Toplevel(self.main_window)
        new_w.geometry('+%d+%d' % (self.parent.winfo_screenwidth() / 2,
                                   self.parent.winfo_screenheight() / 2))
        new_w.lift()
        new_w.bind('<F1>', exp_manager.show_documentation)
        frame_class(new_w, exp_manager, callback=callback)
