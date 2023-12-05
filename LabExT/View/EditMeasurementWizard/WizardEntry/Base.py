"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging

from abc import ABC, abstractmethod

from tkinter import Frame, Button

from typing import TYPE_CHECKING, Union, Tuple, Any

from LabExT.View.Controls.CustomFrame import CustomFrame
from LabExT.View.Controls.KeyboardShortcutButtonPress import callback_if_btn_enabled

if TYPE_CHECKING:
    from LabExT.View.EditMeasurementWizard.EditMeasurementWizardController import EditMeasurementWizardController
else:
    EditMeasurementWizardController = None

####################
# Controller
####################


class WizardEntryController(ABC):
    """A base-class defining the method interface for the wizard entries.

    When createing a ``WizardEntryController`` the ``_define_view()``
    method is called to get the ``WizardEntryView`` used with this
    controller.

    The intended way to use this controller is to call the 
    ``deserialize`` method after creation to populate the
    entries of the view from a ``dict``.

    After the entry is finished the results can be polled
    with the ``results`` method.

    The ``serialize`` method receives a dict where the entries 
    of the view can be written to. This dict should be passed
    to the ``deserialize`` method later.
    """

    @abstractmethod
    def results(self) -> Any:
        """Returns the result of this WizardEntry.

        The type of the result is defined by the subclass that
        inherits this base-class and may vary.
        """
        self._logger.warning("Using default implementation of abstract method")

    @abstractmethod
    def deserialize(self, settings: dict) -> None:
        """Takes a dict and uses it to populate the view.

        Args:
            settings: A dict that contains the data used to 
                populate the view of this WizardEntry.
        """
        self._logger.warning("Using default implementation of abstract method")

    @abstractmethod
    def serialize(self, settings: dict) -> None:
        """Writes the entries from the view to a dict for later reuse.

        Args:
            settings: A dict whose entries will be used to store the
                data used in the view of this WizardEntry.
        """
        self._logger.warning("Using default implementation of abstract method")

    @abstractmethod
    def _define_view(self, parent: Frame) -> "WizardEntryView":
        """This method defines and returns the `WizardEntryView` used by this controller.
        """
        self._logger.warning("Using default implementation of abstract method")
        return None

    def allow_interaction(self, allowed: bool) -> None:
        """This method makes the continue button clickable based on `allowed`.

        Args:
            allowed: Makes the button clickable if True and greyed-out otherwise.
        """
        self._view.continue_button['state'] = 'normal' if allowed else 'disabled'

    def disable(self) -> None:
        """Makes the view non-interactable and changes the button to 'Back'.
        """
        self._view.disable()

    def remove(self) -> None:
        """Removes the view from the parent widget.
        """
        self._view.remove()

    def __init__(self, stage: int, controller: EditMeasurementWizardController, parent: Frame) -> None:
        """Initializes this controller.

        Args:
            stage: The index of this controller in the list of entries.
            controller: This controller is used by subclasses to 
                access the underlying data-model and other attributes.
            parent: The tk Frame into which the view will be placed.
        """
        super().__init__()

        self._logger = logging.getLogger()
        self._main_controller = controller

        self._stage = stage
        self._view = self._define_view(parent=parent)

    def __str__(self) -> str:
        return f"WizardEntryController (stage = {self._stage}, view = {self._view})"


####################
# View
####################


class WizardEntryView(ABC):
    """The base class for entries in a wizard window.

    To create custom entries for a wizard inherit from this class
    and override the abstract methods::

        WizardEntryView.results()
        WizardEntryView._content()
        WizardEntryView._main_title()

    This method interface allows for easy creation of wizard
    entries with equal style.

    Usage:
        When initialized this abstract base-class automatically
        calls the ``_content()`` and ``_main_title()`` methods
        to retrieve the components that should be visualized in
        the parent component.

        The content itself has to be added to the ``CustomFrame``
        containing it. This should be done in the ``_content()``
        method using the following code::

            self._content_frame.add_widget(<content>, row=0, column=0, padx=5, pady=5, sticky='we')

        Here ``<content>`` needs to be replaced with the widget
        that is defined and returned at the end of the method.
        There can also be multiple such calls (see ``DeviceSelect.py#WizardEntryChipDeviceSelect).
        ``self._content_frame`` can also be passed to the 
        initializers of custom widgets if needed.

    """

    @abstractmethod
    def results(self) -> Any:
        """Returns the result of the user interaction with this entry if there is one.
        """
        self._logger.warning(
            "Using default implementation of abstract method.")
        return None

    @abstractmethod
    def _content(self) -> Union[CustomFrame, Tuple]:
        """Create and return the content displayed in this entry.

        This function is responsible for calling the 
        ``self._stage_frame.add_widget(...)`` method to place the 
        content inside the tk parent.

        The content will usually be a CustomFrame, however in theory
        any tk widget can be used.
        """
        self._logger.warning(
            "Using default implementation of abstract method.")
        return None

    @abstractmethod
    def _main_title(self) -> str:
        """Returns the title of the box this entry is placed in.
        """
        self._logger.warning(
            "Using default implementation of abstract method.")
        return "Undefined title"

    def __init__(
        self,
        stage: int,
        parent: Frame,
        controller: EditMeasurementWizardController
    ) -> None:
        super().__init__()

        self._logger = logging.getLogger()

        self.stage = stage
        self.parent = parent
        self.controller = controller
        """The main controller used for callbacks.
        
        This cross-dependency could be removed by using an event-
        based system, however creating an event system just for 
        this wizard would be out of scope. 
        
        Todo:
            In the future create an event system and overhaul
            all wizards in the codebase.
        """

        self._content_frame = CustomFrame(parent=parent)
        self._content_frame.title = self._main_title()
        self._content_frame.grid(
            row=stage, column=0, padx=5, pady=5, sticky="we")

        def on_continue(*args): return controller.stage_completed(stage)

        self._content_frame.continue_button = Button(
            self._content_frame, text="Continue", command=on_continue, width=10
        )

        self.content = self._content()
        """Stores the content displayed in this Entry.
        
        The type may vary based on the implementation of the
        inheriting subclass but is typically a `CustomFrame` 
        or a tuple of tk widgets.
        """

        controller.register_keyboard_shortcut(
            "<Escape>", lambda event: controller.escape_event(stage))
        controller.register_keyboard_shortcut(
            "<Return>",
            callback_if_btn_enabled(
                on_continue, self._content_frame.continue_button))

        # this is needed because some implementations may have
        # multiple elements in content
        try:
            column = len(self.content)
        except TypeError:
            column = 1
        self._content_frame.continue_button.grid(
            row=0, column=column, padx=5, pady=5, sticky="e"
        )

        self._content_frame.columnconfigure(0, weight=1)

    def __str__(self) -> str:
        return f"WizardEntryView with stage {self.stage}"

    @property
    def continue_button(self) -> Button:
        """Returns the button to the right of this Entry

        The button's default text when active is 'Continue'.
        This changes to back, once this entry is deactivated.
        """
        return self._content_frame.continue_button

    def remove(self):
        """Removes this Entry from its parent component.
        """
        self._content_frame.grid_remove()

    def disable(self):
        """Stops interaction with this Entry and changes button's content to 'Back'.
        """
        self._content_frame.enabled = False
        self.continue_button.config(
            text='Back', command=lambda: self.controller.stage_start(self.stage))
