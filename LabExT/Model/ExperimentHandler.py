#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from LabExT.Experiments.StandardExperiment import StandardExperiment
from LabExT.Model.Extensions.KillableThread import KillableThread


class ExperimentHandler(object):
    """Handles experiments."""

    @property
    def current_experiment(self):
        """Gets the current experiment."""
        return self._current_experiment

    @current_experiment.setter
    def current_experiment(self, experiment: StandardExperiment):
        """Sets the current experiment."""
        self.stop_experiment()  # stop old experiment if it is still running
        self._current_experiment = experiment  # replace experiment
        self._experiment_thread = None  # remove experiment thread

    def __init__(self):
        self._experiment_thread = None
        self._current_experiment = None
        self.experiment_finished = list()  # initialize structure for callbacks

    def __run__(self):
        """Worker function for the experiment thread."""
        self._current_experiment.run()  # run experiment

        # execute callback functions
        for callback in self.experiment_finished:
            callback()

    def run_experiment(self, experiment: StandardExperiment = None):
        """Run experiment. Either runs current experiment or sets the
        current experiment according to the parameters."""
        if experiment is None:
            experiment = self.current_experiment

        if experiment is not None:
            self._experiment_thread = KillableThread(
                target=self.__run__,
                name="Experiment Runner"
            )  # create a killable thread for the experiment
            self._experiment_thread.start()  # start experiment thread

    def stop_experiment(self):
        """Stop current experiment."""
        if self._experiment_thread is not None and self._current_experiment is not None:
            self._experiment_thread.terminate()
