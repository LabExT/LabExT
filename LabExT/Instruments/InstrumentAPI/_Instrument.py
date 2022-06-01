#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
LabExT  Copyright (C) 2021  ETH Zurich and Polariton Technologies AG
This program is free software and comes with ABSOLUTELY NO WARRANTY; for details see LICENSE file.
"""

import logging
from functools import wraps

import pyvisa
from pyvisa import InvalidSession

from LabExT.Instruments.ReusingResourceManager import ReusingResourceManager
from LabExT.Utils import get_visa_lib_string

try:
    from LabExT.ExperimentManager import RESOURCE_MANAGER
except ImportError:
    RESOURCE_MANAGER = None


#
# Decorator to assert opened instrument connection.
#

def assert_instrument_connected(func):
    """
    Use this decorator to assert that any method of an Instrument is only executed
    when the instrument connection has been opened with open().
    """

    @wraps(func)
    def wrapper(instr, *args, **kwargs):
        if instr._open:
            try:
                return func(instr, *args, **kwargs)
            except Exception as exc:
                # When the communication with the instrument is cut off at the wrong time, We cannot communicate with it
                # anymore until we close and reopen the communication.
                # See https://github.com/pyvisa/pyvisa/issues/367#issuecomment-427500683
                if type(exc).__name__ == "RPCError":
                    instr.logger.warn("RPCError occurred, closing and reopening instrument connection.")
                    instr._inst.close()
                    instr._inst.open()
                else:
                    raise exc
            return func(instr, *args, **kwargs)
        else:
            raise RuntimeError("Instrument connection is not open. Cannot do any I/O with instrument.")

    return wrapper


#
# Exception used in case instruments report errors.
#

class InstrumentException(Exception):
    """ Exception thrown when Instrument signals an error in `check_instrument_errors`."""
    pass


#
# Instrument Superclass
#

class Instrument(object):
    """Super class of all instrument drivers for LabExT.

    The methods in this class implement all the basic necessary instrument-related functionality, mainly
    communication via the VISA library, error checks, setup and teardown.

    Important: every instrument tries to use the LabExT-global
    [pyvisa resource manager](https://pyvisa.readthedocs.io/en/latest/api/resourcemanager.html)
    instantiated on LabExT startup. If it cannot be found (e.g. on standalone driver usage w/o LabExT GUI) it will
    instantiate a resource manager ad-hoc.

    Attributes:
        error_query_string (str): String to query the instrument's error queue. By default `'SYST:ERR?'` matching most
            modern SCPI-enabled instruments. Change this according to your instrument to use the built-in error
            checking features.
        ignored_SCPI_error_numbers (list of int): include all error numbers of the SCPI error queue which should be
            ignored. This can be for example useful if your instrument reports warnings also in the error queue.
        channel (int): channel number for multi-channel instruments (e.g. laser mainframe, most DSOs, etc.), None if
            a single channel instrument is used.
        instrument_config_descriptor (dict): A verbatim copy of the instruments.config entry used for this instance of
            the driver. Set during driver initialization in InstrumentAPI.
        networked_instrument_properties (list): Add to this list all object properties which should get freshly fetched
            and added to self.instrument_parameters on each get_instrument_parameter() call.
    """

    # error numbers to ignore for this instrument when
    # querying the error queue
    error_query_string = 'SYST:ERR?'
    ignored_SCPI_error_numbers = [0]

    def __init__(self,
                 visa_address,
                 channel=None,
                 **kwargs):
        """Constructor of the Instrument class.

        Arguments:
            visa_address (str): the VISA address of the requested device
            channel (int): if the instrument has multiple channels associated, fill its number in here
            **kwargs: kwargs are saved in the `self._kwargs` property and can be accessed there by any sub-class
        """
        self.logger = logging.getLogger()

        self._inst = None  # type: pyvisa.resources.Resource
        self._address = visa_address
        self._category = "Laboratory Instrument"
        self._kwargs = kwargs

        #: int: channel number for multi-channel instruments (e.g. laser mainframe, most DSOs, etc.) otherwise None
        self.channel = channel

        #: dict: set during driver initialization, verbatim copy of the instruments.config entry used for this instance
        self.instrument_config_descriptor = None

        # instrument parameter on network, add to this list all object properties which should get freshly fetched
        # and added to self.instrument_parameters on each get_instrument_parameter() call.
        self.networked_instrument_properties = []

        # instrument parameter dictionary
        self.instrument_parameters = {
            'class': self.__class__.__name__,
            'visa': self._address,
            'channel': channel,
            **self._kwargs
        }

        # get reference to VISA resource manager or create new instance if not available via import
        if RESOURCE_MANAGER is not None:
            self._resource_manager = RESOURCE_MANAGER
            self.logger.debug("Found existing resource manager with id {:s}".format(str(id(self._resource_manager))))
        else:
            self._resource_manager = ReusingResourceManager(get_visa_lib_string())
            self.logger.debug('Opened NEW ReusingResourceManager with id {:s}'.format(str(id(RESOURCE_MANAGER))))

        self.logger.debug('Instrument class initialised with visa_address: %s', visa_address)

    def get_instrument_parameter(self):
        """Return the currently set instrument parameters.

        Reads all properties directly from instrument if connection to instrument can be opened. This method is called
        before and after a measurement execution in LabExT to save the instrument state as meta data.

        Include all property names you want to read in the `self.networked_instrument_properties` list.
        """
        ret_dict = self.instrument_parameters.copy()

        need_closing = False
        if not self._open:
            try:
                self.open()
                need_closing = True
            except Exception as e:
                msg = self.__class__.__name__ + \
                      ": ERROR getting up-to-date parameters from remote instrument! " \
                      + repr(e)
                ret_dict["remote_instrument_properties"] = msg
                self.logger.warning(msg)

        if self._open:  # skip getting properties if instrument was not successfully opened above
            ret_dict['idn'] = self.idn()
            for prop in self.networked_instrument_properties:
                try:
                    val = getattr(self, prop)  # network access here
                except AttributeError as e:
                    val = "Attribute not found! class: " + str(self.__class__) + " " + str(e)
                    self.logger.error(val)
                except Exception as e:
                    val = "ERROR getting up-to-date parameter " + prop + ": " + repr(e)
                    self.logger.warning(val)
                ret_dict[prop] = val

        if need_closing:
            self.close()

        return ret_dict

    #
    # connection status functions
    #

    def __del__(self):
        self.close()

    @property
    def _open(self):
        """ checks if underlying VISA session is open or not """
        if self._inst is None:
            return False
        try:
            _ = self._inst.session
            return True
        except InvalidSession:
            return False

    def open(self):
        """Open the connection to the instrument.

        Automatically re-uses any old connection if it is already open with the reusing-resource manager.
        """
        self._inst = self._resource_manager.open_resource(self._address)
        self.logger.debug('opened instrument at %s.', self._address)

    def close(self):
        """Close the connection to the instrument.

        Also clears all IO buffers.
        """
        if self._inst is not None:
            self._resource_manager.close_resource(self._inst)
        self._inst = None
        self.logger.debug('closed instrument %s.', self._address)

    @property
    def thread_lock(self):
        """Thread-lock for exclusive instrument access.

        Use this lock to acquire exclusive access to an instrument without any other thread meddling with it.
        Caution: A mainframe containing multiple instruments still counts as one connection and hence these instruments
        share this lock!

        LabExT does not enforce any exclusivity of the instruments itself. You need to take care that you do not
        deadlock the instruments yourself.

        Do NOT save the reference of this lock anywhere!

        This lock can only be acquired if this instrument is open. Otherwise having a lock does not work.

        Returns:
             threading.Lock: a lock exclusive for this instrument's connection
        """
        if not self._open:
            raise ValueError('An instruments lock can only be acquired if the instrument is open.')

        return self._inst.lrm_rlock

    #
    # functions implementing commonly used IEEE-488.1 and .2 commands
    #

    @assert_instrument_connected
    def clear(self):
        """Clears all status registers.
        """
        self._inst.write('*CLS')

    @assert_instrument_connected
    def idn(self):
        """Query the ID string of the lab instrument.
        """
        ans = self._inst.query('*IDN?').strip()
        return ans

    @assert_instrument_connected
    def reset(self):
        """Reset the laboratory instrument.
        """
        self._inst.write('*RST')

    @assert_instrument_connected
    def ready_check_sync(self):
        """Query the OPC register in the instrument for a blocking ready-check.

        Queries the operation complete (OPC) bit in the instrument's status register.
        This call is BLOCKING until the instrument signals completion. If the instrument
        does not return an answer within the timeout, this call errors.
        """
        self._inst.query('*OPC?')
        return True

    @assert_instrument_connected
    def ready_check_async_setup(self):
        """Prepare asynchronous read-checks.

        Signal the instrument to reset the event status register (ESR) and start listening
        to operation complete signals to store into the ESR.
        """
        self._inst.write('*CLS')  # clear event status register
        self._inst.write('*OPC')  # signal OPC bit to be set in ESR upon operation completion (not a query!)

    @assert_instrument_connected
    def ready_check_async(self):
        """Query the ESR register in the instrument for a non-blocking ready-check.

        Queries the operation complete (OPC) bit in the instrument's status register.
        This call is NON-BLOCKING. It will return immediately with the result:
        False if the instrument's operation is not complete, and True if it is.

        Before using this function, tell the instrument that it should fill its status register by calling
        ready_check_async_setup()!

        Returns:
            bool: True if operation complete bit set, False otherwise
        """
        esr_value = int(self._inst.query('*ESR?'))
        opc_bit_value = esr_value & 0x01  # OPC bit is bit 0 in ESR register
        if opc_bit_value > 0:
            return True
        else:
            return False

    @assert_instrument_connected
    def check_instrument_errors(self):
        """Checks the internal error queue of the instrument.

        This form of error checking should work for all instruments adhering to the SCPI
        standard (notably all Agilent / Keysight ones). If it does not work for your instrument,
        don't hesitate to implement a working version.

        Raises:
            InstrumentException: if the instrument reports an error
        """
        errors = []
        while True:
            err_value = self._inst.query(self.error_query_string).strip()
            err_number = int(err_value.split(',')[0])  # format of SCPI error messages: '+0,"No error"\n'
            if err_number != 0:
                # only add not ignored errors to the error list
                if err_number not in self.ignored_SCPI_error_numbers:
                    errors.append(err_value)
            else:
                # the error queue is empty as soon as we read a 0 from it
                break
        if errors:
            raise InstrumentException("Error queue reports these errors: " + str(errors))

    #
    # functions for I/O to and from instrument
    #

    def command(self, command_str):
        """High-level write call incl. ready-check and error check.

        Sends a SCPI text command to the instrument, waits until its completion and checks that there was
        no error in communicating. Use this function to send standard, non timing critical SCPI commands.

        Arguments:
            command_str (str): the command string to send to the instrument.
        """
        self.write(command_str)  # send the command
        self.ready_check_sync()  # wait until instrument signalled completion

        self.check_instrument_errors()  # make sure there was no error

    def command_channel(self, subsystem_str, command_str):
        """High-level shortcut function to send a command to a channel in a multi-channeled instrument.

        This function blocks until command completion and makes sure that there was no communication
        error.

        Arguments:
            subsystem_str (str): first part of the command string, before the channel number
            command_str (str): second part of the command string, after the channel number
        """
        if self.channel is not None:
            self.command(subsystem_str + str(self.channel) + command_str)
        else:
            raise TypeError("Instrument does not have channel attribute set. Cannot command_channel().")

    def request(self, request_str):
        """High-level query call incl. ready-check and error check.

        Sends a SCPI text request to the instrument, waits until its completion and checks that there was
        no error in communicating. Then returns the answer.
        Use this function to execute standard, non timing critical SCPI queries.

        Arguments:
            request_str: string to be queried
        Returns:
            str: the answer from the instrument
        """
        ans = self.query(request_str)
        self.check_instrument_errors()
        return ans

    def request_channel(self, subsystem_str, request_str):
        """High-level shortcut function to send a request to a channel in a multi-channeled instrument.

        This function blocks until command completion and makes sure that there was no communication
        error.

        Arguments:
            subsystem_str (str): first part of the request string, before the channel number
            request_str (str): second part of the request string, after the channel number
        Returns:
            str: the answer from the instrument
        """
        if self.channel is not None:
            return self.request(subsystem_str + str(self.channel) + request_str)
        else:
            raise TypeError("Instrument does not have channel attribute set. Cannot request_channel().")

    #
    # lower-level I/O functions for instruments
    #

    @assert_instrument_connected
    def query(self, query_str):
        """Low-level query function.

        Send the query_str to the instrument and read its response. No ready-check or error check is performed.

        Arguments:
            query_str (str): string to be sent to the instrument
        Returns:
             str: the answer from the instrument
        """
        ans = self._inst.query(query_str)
        return ans

    def query_channel(self, subsystem_str, write_str):
        """Low-level query function for channelized instruments.

        Shortcut function to query commands from a channel in a multi-channeled instrument.

        Arguments:
            subsystem_str (str): first part of the send string, before the channel number
            write_str (str): second part of the send string, after the channel number
        Returns:
             str: the answer from the instrument
        """
        if self.channel is not None:
            return self.query(subsystem_str + str(self.channel) + write_str)
        else:
            raise TypeError("Instrument does not have channel attribute set. Cannot query_channel().")

    @assert_instrument_connected
    def write(self, write_str):
        """Low-level write function.

        Send the write_str to the instrument. This function does not check command completion nor
        error free-ness, you must do both manually if desired.

        Arguments:
             write_str (str): string to be written
        """
        self._inst.write(write_str)

    def write_channel(self, subsystem_str, write_str):
        """Low-level write function for channelized instruments.

        Shortcut function to write commands to a channel in a multi-channeled instrument.
        This function does not check command completion nor error free-ness, you must do both manually if desired.

        Arguments:
            subsystem_str (str): first part of the send string, before the channel number
            write_str (str): second part of the send string, after the channel number
        """
        if self.channel is not None:
            self.write(subsystem_str + str(self.channel) + write_str)
        else:
            raise TypeError("Instrument does not have channel attribute set. Cannot write_channel().")

    @assert_instrument_connected
    def query_raw_bytes(self, query_str, N_bytes, chunk_size=None, break_on_termchar=False):
        """Send a query to the instrument and read the answer in raw bytes.

        Send the query_str to the instrument and read N_bytes from the answer and return the raw bytes object.
        This is essentially a wrapper for [self._inst.read_bytes(N_bytes)](https://pyvisa.readthedocs.io/en/latest/api/resources.html?highlight=read_bytes#pyvisa.resources.MessageBasedResource.read_bytes)
        with the difference, that there is no error checking after the writing, since we expect an answer.
        Unpack the answer from this query with the struct module.

        Arguments:
            query_str (str): the string to query the instrument with (optional, to not send anything, set to None)
            N_bytes (int): the number of bytes to expect as the instrument's response
            chunk_size (int): The chunk size to perform the reading with.
            break_on_termchar (bool): Should the reading stop when the termination character is encountered?

        Returns:
            bytes: the raw bytes read
        """
        if query_str is not None:
            self._inst.write(query_str)

        return self._inst.read_bytes(N_bytes, chunk_size, break_on_termchar)

    @assert_instrument_connected
    def query_ascii_values(self, query_str, converter='f', separator=',', container=list):
        """Send a query to the instruments and read the answer into a Python container type.

        Send the query_str to the instrument and read data in ASCII format from the answer. The answer is then
        interpreted as multiple separated numerical values which are filled into a container class.
        This is essentially a wrapper for [self._inst.queary_ascii_values(query_str)](https://pyvisa.readthedocs.io/en/latest/api/resources.html?highlight=query_ascii_values#pyvisa.resources.MessageBasedResource.query_ascii_values)

        Arguments:
            query_str (str): the string to query the instrument with
            converter (str): string format to convert each value. Default is "f" (float).
            separator (str): character, which separates the individual data points. Default is ",".
            container (type): container type to use for the output data. Possible values are: list, tuple,
                np.ndarray among others.

        Returns:
            container: The container
        :return: list of numbers
        """
        return self._inst.query_ascii_values(query_str,
                                             converter=converter,
                                             separator=separator,
                                             container=container)
