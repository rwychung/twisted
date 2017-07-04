# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
Tests for L{twisted.internet.serialport}.
"""

import os
import shutil
import tempfile

from twisted.trial import unittest
from twisted.internet.protocol import Protocol
from twisted.python.runtime import platform
from twisted.internet.test.test_serialport import DoNothing

try:
    from twisted.internet import serialport
    import serial
except ImportError as e:
    serialport = None
    serial = None


if serialport is not None:
    # class TestableSerialPortBase(serialport.SerialPort):
    #     """
    #     Base testable version of Windows
    #     C{twisted.internet.serialport.SerialPort}.
    #     """
    #
    #     # Fake this out; it calls into win32 library.
    #     def _finishPortSetup(self):
    #         pass

    class RegularFileSerial(serial.Serial):
        def __init__(self, *args, **kwargs):
            super(RegularFileSerial, self).__init__(*args, **kwargs)
            self.captured_args = args
            self.captured_kwargs = kwargs

        def _reconfigurePort(self):
            pass

        def _reconfigure_port(self):
            pass


    class RegularFileSerialPort(serialport.SerialPort):
        _serialFactory = RegularFileSerial

        def __init__(self, *args, **kwargs):
            cbInQue = kwargs.get('cbInQue')

            if 'cbInQue' in kwargs:
                del kwargs['cbInQue']

            self.comstat = serial.win32.COMSTAT
            self.comstat.cbInQue = cbInQue

            super(RegularFileSerialPort, self).__init__(*args, **kwargs)

        def _clearCommError(self):
            return True, self.comstat


class Win32SerialPortTests(unittest.TestCase):
    """
    Minimal testing for Twisted's Win32 serial port support.
    """

    if not platform.isWindows():
        skip = "This test must run on Windows."

    elif not serialport:
        skip = "Windows serial port support is not available."

    def setUp(self):
        # Re-usable protocol and reactor
        self.protocol = Protocol()
        self.reactor = DoNothing()

        self.directory = tempfile.mkdtemp()
        self.path = os.path.join(self.directory, 'fake_serial')

        data = b'1234'
        with open(self.path, 'wb') as f:
            f.write(data)

    def tearDown(self):
        shutil.rmtree(self.directory)

    def test_serialPortDefaultArgs(self):
        """
        Test correct positional and keyword arguments have been
        passed to the C{serial.Serial} object.
        """
        port = RegularFileSerialPort(self.protocol, self.path, self.reactor)
        # Validate args
        self.assertEqual((self.path,), port._serial.captured_args)
        # Validate kwargs
        kwargs = port._serial.captured_kwargs
        self.assertEqual(9600,                kwargs["baudrate"])
        self.assertEqual(serial.EIGHTBITS,    kwargs["bytesize"])
        self.assertEqual(serial.PARITY_NONE,  kwargs["parity"])
        self.assertEqual(serial.STOPBITS_ONE, kwargs["stopbits"])
        self.assertEqual(0,                   kwargs["xonxoff"])
        self.assertEqual(0,                   kwargs["rtscts"])
        self.assertEqual(None,                kwargs["timeout"])
        port.connectionLost(reason='Cleanup')

    def test_serialPortInitiallyConnected(self):
        """
        Test the port is connected at initialization time, and
        C{Protocol.makeConnection} has been called on the desired protocol.
        """
        self.assertEqual(0,    self.protocol.connected)

        port = RegularFileSerialPort(self.protocol, self.path, self.reactor)
        self.assertEqual(1, port.connected)
        self.assertEqual(1, self.protocol.connected)
        self.assertEqual(port, self.protocol.transport)
        port.connectionLost(reason='Cleanup')

    def common_exerciseHandleAccess(self, cbInQue):
        port = RegularFileSerialPort(
            protocol=self.protocol,
            deviceNameOrPortNumber=self.path,
            reactor=self.reactor,
            cbInQue=cbInQue,
        )
        port.serialReadEvent()
        port.write(b'abcd')
        port.write(b'ABCD')
        port.serialWriteEvent()
        port.serialWriteEvent()
        port.connectionLost(reason='Cleanup')

        # No assertion since the point is simply to make sure that in all cases
        # the port handle resolves instead of raising an exception.

    def test_exerciseHandleAccess_1(self):
        self.common_exerciseHandleAccess(cbInQue=False)

    def test_exerciseHandleAccess_2(self):
        self.common_exerciseHandleAccess(cbInQue=True)
