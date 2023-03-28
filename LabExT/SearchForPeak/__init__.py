
import logging
import json

from typing import Type
from os.path import dirname, exists

from LabExT.PluginLoader import PluginAPI
from LabExT.Movement.MoverNew import MoverNew

from LabExT.SearchForPeak.PeakSearcher import PeakSearcher
from LabExT.SearchForPeak.GaussianFit2D import GaussianFit2D
from LabExT.Utils import get_configuration_file_path


class SearchForPeakError(RuntimeError):
    pass


class SearchForPeak:
    """

    """
    search_for_peak_settings_file = get_configuration_file_path(
        "search_for_peak_settings.json")

    DEFAULT_PEAK_SEARCHER = GaussianFit2D

    LAST_PEAK_SEARCHER_KEY = "most_recently_used_peak_searcher"
    PEAK_SEARCHER_SETTINGS_KEY = "peak_searcher_settings"
    INSTRUMENTS_KEY = "instruments"
    STAGES_KEY = "stages"
    PARAMETERS_KEY = "parameters"

    def __init__(
        self,
        mover,
        experiment_manager,
    ) -> None:
        self.mover: Type[MoverNew] = mover
        self.experiment_manager = experiment_manager

        self.logger = logging.getLogger()

        self._peak_searcher: Type[PeakSearcher] = self.DEFAULT_PEAK_SEARCHER(
            self.mover)
        self.peak_searcher_api = PluginAPI(
            base_class=PeakSearcher,
            core_search_path=dirname(__file__))

        self.__running: bool = False

        self._peak_searcher_settings = {}

    @property
    def is_running(self) -> bool:
        """
        Returns True if a peak searcher is executing.
        """
        return self.__running

    @property
    def initialized(self) -> bool:
        """
        Returns True if search for peak is initialized.
        """
        return False

    @property
    def peak_searcher(self) -> Type[PeakSearcher]:
        """
        Returns the current peak searcher instance.
        """
        return self._peak_searcher

    @peak_searcher.setter
    def peak_searcher(self, new_peak_searcher: Type[PeakSearcher]) -> None:
        """
        Sets new peak searcher instance.
        """
        self._raise_if_updates_are_locked()

        if not issubclass(new_peak_searcher.__class__, PeakSearcher):
            raise ValueError(
                f"Cannot set peak searcher {new_peak_searcher}. Instance is not a sub class of PeakSearcher.")

        self._peak_searcher = new_peak_searcher

    def set_peak_searcher_by_name(self, peak_searcher_name: str) -> None:
        """
        Sets new peak searcher by name.
        """
        peak_searcher = self.peak_searcher_api.get_class(peak_searcher_name)
        if not peak_searcher:
            raise ValueError(
                f"Cannot set peak searcher with name {peak_searcher_name}. No peak searcher found by this name.")

        self.peak_searcher = peak_searcher(self.mover)

    def initialize_selected_instruments(self, selected_instruments) -> None:
        """

        """
        self._raise_if_updates_are_locked()

        for instr_class in self.peak_searcher.get_wanted_instruments():
            self.experiment_manager.instrument_api.create_instrument_obj(
                instr_class, selected_instruments, self.peak_searcher.instruments)
        # check that all instruments were correctly initialized, if this is not
        # the case, we raise an Exception
        if not all(
                inst is not None for inst in self.peak_searcher.instruments.values()):
            raise RuntimeError('Instruments were not initialized correctly.')

        self.store_peak_searcher_settings(
            self.peak_searcher, self.INSTRUMENTS_KEY, selected_instruments)
        self.dump_settings()

    def set_selected_stages(self, selected_stages) -> None:
        """

        """
        self._raise_if_updates_are_locked()

        for stage_role in self.peak_searcher.get_wanted_stages():
            calibration = selected_stages[stage_role]
            if calibration not in self.mover.calibrations:
                raise ValueError(
                    f"Selected Stage {calibration} is not registered in mover")

            self.peak_searcher.stages[stage_role] = calibration

        self.store_peak_searcher_settings(
            self.peak_searcher, self.STAGES_KEY, {r: {
                "class": c.stage.__class__.__name__,
                "identifier": c.stage.identifier
            } for r, c in selected_stages.items()})
        self.dump_settings()

    def set_selected_parameters(self, selected_parameters) -> None:
        """

        """
        self._raise_if_updates_are_locked()
        self.peak_searcher.parameters = selected_parameters

        self.store_peak_searcher_settings(
            self.peak_searcher, self.PARAMETERS_KEY, {
                k: v.value for k, v in selected_parameters.items()})
        self.dump_settings()

    def run(self) -> None:
        """

        """
        if self.is_running:
            raise SearchForPeak(
                f"Cannot update search for peak: Peak Searcher {self.peak_searcher} is running.")

        data = {}
        instr_dict_no_cls = {
            k: v for (
                k,
                _),
            v in self.peak_searcher.instruments.items()}

        self.__running = True
        try:
            peak_coordinate = self.peak_searcher.algortihm(
                data,
                instr_dict_no_cls,
                self.peak_searcher.stages,
                self.peak_searcher.parameters)
        finally:
            self.__running = False

        return data

    def get_peak_searcher_settings(
        self,
        peak_searcher: Type[PeakSearcher],
        data_key: str
    ) -> dict:
        """

        """
        peak_searcher_settings = self._peak_searcher_settings.setdefault(
            peak_searcher.__class__.__name__, {})
        return peak_searcher_settings.get(data_key, {})

    def store_peak_searcher_settings(
        self,
        peak_searcher: Type[PeakSearcher],
        data_key: str,
        data: dict
    ) -> None:
        """

        """
        peak_searcher_settings = self._peak_searcher_settings.setdefault(
            peak_searcher.__class__.__name__, {})
        peak_searcher_settings[data_key] = data

    def load_settings(self) -> None:
        """

        """
        if not exists(self.search_for_peak_settings_file):
            self.logger.debug(
                f"SfP settings file {self.search_for_peak_settings_file} not found. Skipping loading settings.")
            return

        with open(self.search_for_peak_settings_file, "r") as fp:
            try:
                settings = json.load(fp)
            except json.decoder.JSONDecodeError as err:
                self.logger.error(
                    f"Failed to decode sfp settings file: {err}")
                return

        if self.LAST_PEAK_SEARCHER_KEY in settings:
            self.peak_searcher = self.peak_searcher_api.get_class(
                settings[self.LAST_PEAK_SEARCHER_KEY], self.DEFAULT_PEAK_SEARCHER)(self.mover)

        self._peak_searcher_settings = settings.get(
            self.PEAK_SEARCHER_SETTINGS_KEY, {})

    def dump_settings(self) -> None:
        """

        """
        with open(self.search_for_peak_settings_file, "w") as fp:
            json.dump({
                self.LAST_PEAK_SEARCHER_KEY: self.peak_searcher.__class__.__name__,
                self.PEAK_SEARCHER_SETTINGS_KEY: self._peak_searcher_settings
            }, fp, indent=2)

    def _raise_if_updates_are_locked(self):
        """
        Raises SearchForPeakError if instance updates are not possible.
        """
        if self.is_running:
            raise SearchForPeakError(
                f"Cannot update search for peak: Peak Searcher {self.peak_searcher} is running.")
