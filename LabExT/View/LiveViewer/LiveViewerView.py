#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

from tkinter import Frame, Toplevel, OptionMenu, Button, StringVar, Scrollbar, Canvas

from LabExT.View.Controls.ParameterTable import ParameterTable
from LabExT.View.Controls.PlotControl import PlotControl


class LiveViewerView:
    """
    Viewer class for the live viewer. Contains all functionality related to widgets.
    """
    def __init__(self, root, controller, model, experiment_manager):
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
        self.root = root
        self.controller = controller
        self.model = model
        self.experiment_manager = experiment_manager

        self.main_window = LiveViewerMainWindow(self.root, controller, model)


class LiveViewerMainWindow(Toplevel):
    """
    The main window itself. Inherits from TopLevel and acts as a standalone window.
    """
    def __init__(self, root, controller, model):
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
        self.controller = controller
        w, h = root.winfo_screenwidth() - 20, root.winfo_screenheight() - 100
        self.geometry("%dx%d+0+0" % (w, h))
        self.lift()
        # self.attributes('-topmost', 'true')
        # self.protocol('WM_DELETE_WINDOW', self.controller.close_wizard)
        self.bind('<F1>', self.controller.experiment_manager.show_documentation)

        self.main_frame = MainFrame(self, controller, model)
        self.main_frame.grid(row=0, column=0, padx=2, pady=2, sticky='NESW')
        self.grid_rowconfigure(0, weight=1)  # this needed to be added
        self.grid_columnconfigure(0, weight=1)

        self.lift()

    def destroy(self):
        """
        Overloading of the destroy operator. Makes sure, that all parameters are saved and the instruments closed.
        """
        self.controller.save_parameters()
        self.controller.close_all_instruments()
        Toplevel.destroy(self)


class MainFrame(Frame):
    """
    The main Frame. Contains all other smaller frames.
    """
    def __init__(self, parent, controller, model):
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
        self.control_wrapper.grid(row=0, column=1, padx=2, pady=2, sticky='NESW')

        # add the plot window
        self.plot_wrapper = PlotFrame(self, controller, model)
        self.plot_wrapper.grid(row=0, column=0, padx=2, pady=2, sticky='NESW')
        self.grid_rowconfigure(0, weight=1)  # this needed to be added
        self.grid_columnconfigure(0, weight=1)


class ControlFrame(Frame):
    """
    The control Frame. Contains all cards.
    """
    def __init__(self, parent, controller, model):
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
        self.model = model
        self.controller = controller
        Frame.__init__(self, parent)

        # add the CardManager
        self.cardM = CardManager(self, controller, model)
        self.cardM.grid(row=0, column=0, sticky='NEW', pady=(12, 20))

        self.save_button = Button(self, text="Save current Data", command=self.controller.create_snapshot)
        self.save_button.grid(row=2, column=0, sticky='SEW', pady=(12, 20))

        self.card_full_container = Frame(self)
        self.card_full_container.grid(row=1, column=0, sticky='NESW')
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        vscrollbar = Scrollbar(self.card_full_container, orient='vertical')
        vscrollbar.pack(side='right', fill='y')

        self.canvas = Canvas(self.card_full_container, yscrollcommand=vscrollbar.set)
        self.canvas.pack(side='left', fill='y')

        vscrollbar.config(command=self.canvas.yview)

        # Make the canvas expandable
        self.card_full_container.grid_rowconfigure(0, weight=1)
        self.card_full_container.grid_columnconfigure(0, weight=1)

        # Create the canvas contents
        self.content_carrier = Frame(self.canvas)

        # add the content frame to the canvas
        self.canvas_frame = self.canvas.create_window(0, 0, window=self.content_carrier, anchor='nw')

        self.set_cards()

    def set_cards(self):
        """
        Function to render all cards from the corellating model
        """
        for i, (card_type, card) in enumerate(self.model.cards):
            if card is not None:
                continue
            # set up new card
            new_card = self.model.options[card_type](self.content_carrier, self.controller, self.model, i)
            self.model.cards[i] = (card_type, new_card)
            new_card.pack(side='top', anchor='nw', fill='x', pady=(0, 20))

            # when a card is newly created, we enable the GUI elements s.t. the user can set the parameters
            # this can only happen after the card has been rendered in the "pack" call above
            new_card.enable_settings_interaction()

        self.canvas.update()
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        self.canvas.configure(width=self.canvas.bbox("all")[2])


class PlotFrame(Frame):
    """
    Plot Frame, containing the live plot.
    """
    def __init__(self, parent, controller, model):
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
        self.model = model
        self.controller = controller
        Frame.__init__(self, parent)
        self.plot_widget = PlotWidget(self, self.model)

        self.plot_widget.grid(row=0, column=0, rowspan=2, padx=10, pady=10, sticky='nswe')
        self.rowconfigure(0, weight=1)
        self.columnconfigure(0, weight=1)


class PlotWidget (PlotControl):
    """
    Plot Widget class. Resides inside the Plotwindow.
    """
    def __init__(self, parent, model):
        """Constructor.

        Parameters
        ----------
        parent : Tk
            Tkinter parent frame
        model :
            The Live viewer model
        """
        PlotControl.__init__(self,
                             parent,
                             add_toolbar=True,
                             figsize=(12, 6),
                             autoscale_axis=True,
                             no_x_autoscale=True,
                             min_y_axis_span=None
                             )

        self.parent = parent
        self.model = model

        self.model.live_plot = self

        self.title = 'Live Plot'
        self.show_grid = True
        self.data_source = self.model.plot_collection

        current_nopk = self.model.general_settings['number of points kept'].value
        current_y_min = self.model.general_settings['minimum y-axis span'].value

        self.ax.set_xlim([0, current_nopk])
        self.min_y_axis_span = current_y_min

    def destroy(self):
        # this is a workaround for the LiveViewer thread
        # This thread is usually waiting on a function return
        # Once we close this frame however, the call would be blocking forever
        # Hence we close it
        self.return_queue.put(None)
        PlotControl.destroy(self)


class CardManager(Frame):
    """
    Card manager frame, containing buttons and menus to add more cards.
    """
    def __init__(self, parent, controller, model):
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
        self._root = parent
        self.model = model
        self.parent = parent
        self.controller = controller
        Frame.__init__(self, parent, relief="groove", borderwidth=2)

        self.add_card_button = Button(self, text="Add Instrument", command=self.add_card)

        self.add_card_button.grid(row=0, column=0, sticky='EW')

        options = model.options

        self.selected_value = StringVar()
        self.selected_value.set([*options][0])

        self.card_selector = OptionMenu(self, self.selected_value, *[*options])

        self.card_selector.grid(row=1, column=0, sticky='EW')
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)

        self.ptable = ParameterTable(self)
        self.ptable.title = 'General Parameters'
        self.ptable.parameter_source = self.model.general_settings
        self.ptable.grid(row=0, column=1, sticky='NESW', padx=(12, 0))

        self.add_card_button = Button(self,
                                      text="Update Settings",
                                      command=lambda: self.controller.update_settings(self.ptable.to_meas_param()))
        self.add_card_button.grid(row=1, column=1, sticky='EW', padx=(12, 0))

    def add_card(self):
        """
        Wrapper function to add a new card.
        """
        self.model.cards.append((self.selected_value.get(), None))
        self.parent.set_cards()
