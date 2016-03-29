#!/usr/bin/env python
import serial, sys
import time

# This will just open the serial port shortly with BAUD 1200 to activate the boot loader.
serialPort = sys.argv[1]
ser = serial.Serial(
    port=serialPort,
    baudrate=1200,
    parity=serial.PARITY_NONE,
    stopbits=serial.STOPBITS_ONE,
    bytesize=serial.EIGHTBITS
)
ser.open()
time.sleep(0.1)
ser.close() # always close port

