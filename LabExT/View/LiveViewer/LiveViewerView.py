#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from typing import TYPE_CHECKING
from tkinter import Frame, Toplevel, OptionMenu, Button, StringVar, Scrollbar, Canvas
from tkinter.messagebox import askyesno

from LabExT.View.LiveViewer.LiveViewerPlot import LiveViewerPlot
from LabExT.View.Controls.ParameterTable import ParameterTable

if TYPE_CHECKING:
    from tkinter import Tk
    from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
    from LabExT.View.LiveViewer.LiveViewerModel import LiveViewerModel
    from LabExT.ExperimentManager import ExperimentManager
else:
    Tk = None
    LiveViewerController = None
    LiveViewerModel = None
    ExperimentManager = None

if TYPE_CHECKING:
    from LabExT.View.LiveViewer.LiveViewerController import LiveViewerController
else:
    LiveViewerController = None


class LiveViewerView:
    """
    Viewer class for the live viewer. Contains all functionality related to widgets.
    """

    def __init__(self, root: Tk, controller: LiveViewerController, model: LiveViewerModel, experiment_manager: ExperimentManager):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        experiment_manager : ExperimentManager
            Current instance of ExperimentManager
        """
        self.root: Tk = root
        self.controller: LiveViewerController = controller
        self.model: LiveViewerModel = model
        self.experiment_manager: ExperimentManager = experiment_manager

        self.main_window = LiveViewerMainWindow(self.root, controller, model)


class LiveViewerMainWindow(Toplevel):
    """
    The main window itself. Inherits from TopLevel and acts as a standalone window.
    """

    def __init__(self, root: Tk, controller: LiveViewerController, model: LiveViewerModel):
        """Constructor.

        Parameters
        ----------
        root : Tk
            Tkinter root window
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        """
        Toplevel.__init__(self, root)
        self.controller: LiveViewerController = controller
        ws, hs = root.winfo_screenwidth(), root.winfo_screenheight()
        # limit window size - otherwise performance suffers heavily on large-screen systems
        w = min(ws, 1600)
        h = min(hs, 1000)
        self.geometry(f"{w:d}x{h:d}+{int((ws-w)/2)}+{int((hs-h)/2)}")
        self.lift()
        # self.attributes('-topmost', 'true')
        # self.protocol('WM_DELETE_WINDOW', self.controller.close_wizard)
        self.bind("<F1>", self.controller.experiment_manager.show_documentation)

        self.main_frame = MainFrame(self, controller, model)
        self.main_frame.grid(row=0, column=0, padx=2, pady=2, sticky="NESW")
        self.grid_rowconfigure(0, weight=1)  # this needed to be added
        self.grid_columnconfigure(0, weight=1)

        self.lift()

    def destroy(self):
        """
        Overloading of the destroy operator. Makes sure, that all parameters are saved and the instruments closed.
        """
        self.main_frame.plot_wrapper.stop_animation()
        self.controller.close_all_instruments()
        self.controller.save_parameters()
        Toplevel.destroy(self)


class MainFrame(Frame):
    """
    The main Frame. Contains all other smaller frames.
    """

    def __init__(self, parent: Tk, controller: LiveViewerController, model: LiveViewerModel):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        """
        Frame.__init__(self, parent)

        # add the selector bar
        self.control_wrapper = ControlFrame(self, controller, model)
        self.control_wrapper.grid(row=0, column=1, padx=2, pady=2, sticky="NESW")

        # add the plot window
        self.plot_wrapper = LiveViewerPlot(self, model=model)
        self.plot_wrapper.grid(row=0, column=0, padx=2, pady=2, sticky="NESW")
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)


class ControlFrame(Frame):
    """
    The control Frame. Contains all cards.

    ToDo: this control frame currently bugs when turning MouseWheel, we might need to disable
    see https://gist.github.com/JackTheEngineer/81df334f3dcff09fd19e4169dd560c59
    """

    def __init__(self, parent: Tk, controller: LiveViewerController, model: LiveViewerModel):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        """
        self.model: LiveViewerModel = model
        self.controller: LiveViewerController = controller
        self.parent: MainFrame = parent
        Frame.__init__(self, parent)

        # add the CardManager
        self.cardM = CardManager(self, controller, model)
        self.cardM.grid(row=0, column=0, columnspan=3, sticky="NESW", pady=12)

        self.ref_set_button = Button(self, text="Set Reference", command=self.confirm_set_new_references)
        self.ref_set_button.grid(row=3, column=0, sticky="NESW", pady=1)

        self.ref_clear_button = Button(self, text="Clear Reference", command=self.controller.reference_clear)
        self.ref_clear_button.grid(row=3, column=1, sticky="NESW", pady=1)

        self.ref_recall_button = Button(self, text="Recall Reference", command=self.controller.reference_recall)
        self.ref_recall_button.grid(row=3, column=2, sticky="NESW", pady=1)

        self.pause_button = Button(self, text="Pause Plotting", command=self.controller.toggle_plotting_active)
        self.pause_button.grid(row=4, column=0, columnspan=3, sticky="NESW", pady=1)

        self.save_button = Button(self, text="Save current Data", command=self.controller.create_snapshot)
        self.save_button.grid(row=5, column=0, columnspan=3, sticky="NESW", pady=1)

        self.card_full_container = Frame(self)
        self.card_full_container.grid(row=1, column=0, columnspan=3, sticky="NESW")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        self.rowconfigure(1, weight=1)

        vscrollbar = Scrollbar(self.card_full_container, orient="vertical")
        vscrollbar.pack(side="right", fill="y")

        self.canvas = Canvas(self.card_full_container, yscrollcommand=vscrollbar.set)
        self.canvas.pack(side="left", fill="y")

        vscrollbar.config(command=self.canvas.yview)

        # Make the canvas expandable
        self.card_full_container.grid_rowconfigure(0, weight=1)
        self.card_full_container.grid_columnconfigure(0, weight=1)

        # Create the canvas contents
        self.content_carrier = Frame(self.canvas)

        # add the content frame to the canvas
        self.canvas.create_window(0, 0, window=self.content_carrier, anchor="nw")

        self.set_cards()

    def confirm_set_new_references(self):
        if askyesno(title='Set References of all Live Viewer Traces',
                    message='This references all plotted traces to the last measured value. ' + \
                    'This overrides previously set references. Proceed?',
                    parent=self.parent):
            self.controller.reference_set()

    def set_cards(self):
        """
        Function to render all cards from the correlating model
        """
        for i, (card_title, card) in enumerate(self.model.cards):
            if card is not None:
                continue
            # set up new card
            new_card = self.model.lvcards_classes[card_title](self.content_carrier, self.controller, self.model)
            self.model.cards[i] = (card_title, new_card)
            new_card.pack(side="top", anchor="nw", fill="x", pady=(0, 20))

            # when a card is newly created, we enable the GUI elements s.t. the user can set the parameters
            # this can only happen after the card has been rendered in the "pack" call above
            new_card.enable_settings_interaction()

        self.canvas.update()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.configure(width=self.canvas.bbox("all")[2])


class CardManager(Frame):
    """
    Card manager frame, containing buttons and menus to add more cards.
    """

    def __init__(self, parent: Tk, controller: LiveViewerController, model: LiveViewerModel):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        controller :
            The Live viewer controller
        model :
            The Live viewer model
        """
        self._root: Tk = parent
        self.model: LiveViewerModel = model
        self.parent: Tk = parent
        self.controller: LiveViewerController = controller
        Frame.__init__(self, parent, relief="groove", borderwidth=2)

        self.add_card_button = Button(self, text="Add Instrument", command=self.add_card)

        self.add_card_button.grid(row=0, column=0, sticky="EW")

        options = model.lvcards_classes

        self.selected_value = StringVar()
        self.selected_value.set([*options][0])

        self.card_selector = OptionMenu(self, self.selected_value, *[*options])

        self.card_selector.grid(row=1, column=0, sticky="EW")
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.ptable = ParameterTable(self)
        self.ptable.title = "General Parameters"
        self.ptable.parameter_source = self.model.general_settings
        self.ptable.grid(row=0, column=1, sticky="NESW", padx=(12, 0))

        _update_settings_button = Button(
            self, text="Apply General Parameters", command=lambda: self.controller.update_settings(self.ptable.to_meas_param())
        )
        _update_settings_button.grid(row=1, column=1, sticky="EW", padx=(12, 0))

    def add_card(self):
        """
        Wrapper function to add a new card.
        """
        self.model.cards.append((self.selected_value.get(), None))
        self.parent.set_cards()
