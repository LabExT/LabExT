#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from tkinter import Tk, Frame, Label, Button, messagebox, StringVar, OptionMenu, Checkbutton, IntVar


class ChooseStageWindow(Frame):
    """Frame that lets the user choose which stage corresponds to
    which USB id (address).

    Attributes
    ----------
    left_choice : StringVar
        User choice for the left stage.
    right_choice : StringVar
        User choice for the right stage.
    """

    def __init__(self, parent: Tk, experiment_manager, label, stages):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent window
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        label : string
            Label displayed to user for more guidance
        stages : list
            List of possible stages
        """
        super(ChooseStageWindow, self).__init__(parent)

        self.logger = logging.getLogger()
        self.logger.debug('Initialise ChooseStageWindow with parent:%s experiment_manager:%s label:%s stages:%s',
                          parent, experiment_manager, label, stages)

        self._root = parent
        self._experiment_manager = experiment_manager
        self._root.title = 'Stage Overview'

        parent.protocol("WM_DELETE_WINDOW", self.__on_close__)
        self._text_label = label
        self._stages = stages
        self.grid(row=0, column=0)  # place window in root element

        # setup "output" variables, accessed by Mover
        self.aborted = False
        self.num_stages = None
        self.left_choice = None
        self.right_choice = None

        # setup the window content
        self.__setup__()

    def __on_close__(self):
        """Called when user presses 'x'. Aborts the selection.
        """
        self._root.destroy()
        self.aborted = True

    def __setup__(self):
        """Set up the frame with dropdowns for each stage.
        """
        self._single_stage_choice = IntVar(self._root, value=0)

        self._single_stage_checkbox = Checkbutton(self._root,
                                                  text="Use only a single stage.",
                                                  variable=self._single_stage_choice,
                                                  command=self._single_stage_changed)
        self._single_stage_checkbox.grid(row=0, column=0, columnspan=2)

        self._left_label = Label(self._root, text='Left Stage:')
        self._left_label.grid(row=1, column=0)
        self._right_label = Label(self._root, text='Right Stage:')
        self._right_label.grid(row=2, column=0)

        self._left_choice = StringVar(self._root)
        self._left_choice.set(self._stages[0])
        self._right_choice = StringVar(self._root)
        self._right_choice.set(self._stages[0])

        self._left_selector = OptionMenu(self._root, self._left_choice, *self._stages)
        self._left_selector.grid(row=1, column=1)
        self._right_selector = OptionMenu(self._root, self._right_choice, *self._stages)
        self._right_selector.grid(row=2, column=1)

        self._continue_button = Button(self._root, text="Continue", command=self._continue)
        self._continue_button.grid(row=3, column=1, sticky='e')

    def _single_stage_changed(self):
        """
        Callback on state change of single stage select box.
        """
        if self._single_stage_choice.get() == 1:
            self._right_selector.configure(state="disabled")
            self._right_label.configure(state="disabled")
            self._left_label.config(text="Stage:")
        else:
            self._right_selector.configure(state="normal")
            self._right_label.configure(state="normal")
            self._left_label.config(text="Left Stage:")

    def _continue(self):
        """Called upon button press. Checks if user selection is valid
        and closes the window.
        """
        # in case of two stages, we must make sure that the selected IDs are not the same
        if self._single_stage_choice.get() == 0:
            # we don't do anything if the user selects the same stages
            if self._left_choice.get() == self._right_choice.get():
                messagebox.showinfo('Warning', 'You selected the same stages!')
                return

        # save outputs
        self.left_choice = self._left_choice.get()
        self.right_choice = None if self._single_stage_choice.get() == 1 else self._right_choice.get()
        self.num_stages = 1 if self._single_stage_choice.get() == 1 else 2

        self.logger.info('Num stages:%d Left choice:%s Right choice:%s',
                         self.num_stages, self.left_choice, self.right_choice)
        self._root.destroy()
