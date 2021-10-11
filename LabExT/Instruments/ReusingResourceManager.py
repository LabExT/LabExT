#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
import threading

import pyvisa as visa


class OpenedResource:
    def __init__(self, resource_obj):
        self.resource_obj = resource_obj
        self.counter = 1


class ReusingResourceManager(visa.ResourceManager):
    """
    Subclass of the pyvisa ResourceManager which implements reusing of resource upon when opening connections.
    """

    _inst_ref = None

    def __new__(cls, visa_library=''):
        # force reusing of the same object, regardless where it was imported from
        if ReusingResourceManager._inst_ref is not None:
            obj = ReusingResourceManager._inst_ref
        else:
            obj = super(ReusingResourceManager, cls).__new__(cls, visa_library)
            ReusingResourceManager._inst_ref = obj
            obj._lrm_visa_lib_str = visa_library

            # keep track of opened resources and keep a counter
            obj._lrm_opened_resources = {}
            obj._lrm_logger = logging.getLogger()
            obj._lrm_tlock = threading.Lock()

        obj._lrm_logger.debug(
            'Initialized ReusingResourceManager using VISA library {:s} with object id {:s}'.format(
                visa_library, str(id(obj))))

        return obj

    @property
    def lrm_opened_resources(self):
        """
        Thread-safe-ly Returns a dict of all opened resources through this ReusingResourceManager.
        The dict keys are the visa addresses, the dict values the resource objects.
        """
        with self._lrm_tlock:
            return self._lrm_opened_resources.copy()

    def open_resource(self, resource_name, *args, **kwargs):
        """
        Before actually opening the resource, check if we already have it available and reuse it if necessary.
        """
        with self._lrm_tlock:
            if resource_name in self._lrm_opened_resources:
                # resource is already open, increase counter and return obj
                log = self._lrm_opened_resources[resource_name]
                log.counter += 1
                self._lrm_logger.debug("Found resource with name {:s} already open. New reference count: {:d}.".format(
                    resource_name, log.counter
                ))
                return log.resource_obj
            else:
                # no resource with this name open yet, create new one, store in log, and return obj
                resource_obj = super().open_resource(resource_name, *args, **kwargs)

                # pyvisa parses the resource name, save the input manually to the object for later use
                resource_obj.lrm_user_resource_name = resource_name

                # assign a thread lock to each resource, so we can assert thread save instrument access
                # within LabExT
                resource_obj.lrm_rlock = threading.Lock()

                log = OpenedResource(resource_obj)
                self._lrm_logger.debug("Created new resource with name {:s} and reference count: {:d}.".format(
                    resource_name, log.counter
                ))
                self._lrm_opened_resources[resource_name] = log
                return resource_obj

    def close_resource(self, resource_obj):
        """
        Use this function to close all VISA resources to keep track of the internal counting.

        :param resource_obj: the VISA resource you like to close
        """
        with self._lrm_tlock:
            # fetch resource name from object
            resource_name = resource_obj.lrm_user_resource_name

            if resource_name not in self._lrm_opened_resources:
                # this should never happen when all resources are opened through this class.
                # Inform user of this mistake but close the connection anyway.
                self._lrm_logger.info(
                    "Could not find an opened resource with name " + str(resource_name) + ". Closing anyway.")
                resource_obj.close()
                return

            log = self._lrm_opened_resources[resource_name]
            log.counter -= 1

            if log.counter == 0:
                # references to this instrument reached 0, close and delete log
                self._lrm_logger.debug("Resource with name {:s} reached 0 references. Closing resource.".format(
                    resource_name
                ))
                resource_obj.close()
                log.resource_obj = None
                del self._lrm_opened_resources[resource_name]
            else:
                self._lrm_logger.debug("Not closing resource {:s} as there are {:d} references left.".format(
                    resource_name, log.counter
                ))

    def force_close_resource(self, resource_obj):
        """
        Use this function to force closing a VISA resource and delete all existing references.

        :param resource_obj: the VISA resource you like to force close
        """
        with self._lrm_tlock:
            # fetch resource name from object
            resource_name = resource_obj.lrm_user_resource_name

            # force close it
            resource_obj.close()

            # delete from internal bookkeeping
            if resource_name in self._lrm_opened_resources:
                log = self._lrm_opened_resources[resource_name]
                log.counter = 0
                log.resource_obj = None
                del self._lrm_opened_resources[resource_name]

    def discard_resource_buffers(self, resource_obj):
        """
        Use this function to discard all data in all buffers for this VISA resource. This can be useful, e.g. after
        a timeout exception where the instrument sent the data back too late and you want to clear it.

        :param resource_obj: the VISA resource you like discard the data for.
        """
        with self._lrm_tlock:
            prev_timeout = resource_obj.timeout
            resource_obj.timeout = 100  # [ms]
            while True:
                try:
                    resource_obj.read_bytes(1)
                except visa.VisaIOError:
                    break
            resource_obj.timeout = prev_timeout
