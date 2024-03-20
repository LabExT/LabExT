#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import json
from collections import OrderedDict


class AutosaveDict(OrderedDict):
    """
    Dictionary Class which automatically saves its content over time.
    """

    def __init__(self, freq=10, file_path="tmp.json", auto_save=True, *args, **kwargs):
        """
        Constructor

        Parameters
        ----------
        freq : int
            Number of accesses and modifications between saving
        file_path : str
            The file path to the file we want to save.
        """
        super().__init__(*args, **kwargs)
        self.freq = freq
        self.file_path = file_path
        self.modify_count = 0
        self.auto_save = auto_save

    def __setitem__(self, *args, **kwargs):
        self.modified()
        return super().__setitem__(*args, **kwargs)

    def __getitem__(self, *args, **kwargs):
        self.modified()
        return super().__getitem__(*args, **kwargs)

    def modified(self):
        """
        Should be called whenever the object is modified. This increases the number of times the file has been modified
        since last saving it and it saves itself to a file when we need to.
        """
        if self.auto_save:
            self.modify_count += 1
            if self.modify_count >= self.freq:
                self.modify_count = 0
                self.save()

    def save(self, indented: bool = True) -> None:
        """
        Saves itself to a file.
        """
        if indented:
            with open(self.file_path, "w+") as f:
                json.dump(self, f, indent="\t")
        else:
            with open(self.file_path, "w+") as f:
                json.dump(self, f)
