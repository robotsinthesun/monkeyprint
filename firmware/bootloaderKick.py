#!/usr/bin/env python
import serial, sys

# This will just open the serial port shortly with BAUD 1200 to activate the serial port.
serialPort = sys.argv[1]
ser = serial.Serial(
    port=serialPort,
    baudrate=1200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)
ser.isOpen()
ser.close() # always close port

