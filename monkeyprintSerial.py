# -*- coding: latin-1 -*-

#	Copyright (c) 2015 Paul Bomke
#	Distributed under the GNU GPL v2.
#
#	This file is part of monkeyprint.
#
#	monkeyprint is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	monkeyprint is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You have received a copy of the GNU General Public License
#    along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.

# -*- coding: latin-1 -*-

#	Copyright (c) 2015 Paul Bomke
#	Distributed under the GNU GPL v2.
#
#	This file is part of monkeyprint.
#
#	monkeyprint is free software: you can redistribute it and/or modify
#	it under the terms of the GNU General Public License as published by
#	the Free Software Foundation, either version 3 of the License, or
#	(at your option) any later version.
#
#	monkeyprint is distributed in the hope that it will be useful,
#	but WITHOUT ANY WARRANTY; without even the implied warranty of
#	MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#	GNU General Public License for more details.
#
#	You have received a copy of the GNU General Public License
#    along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.


import serial
import threading

class serialThread(threading.Thread):
	# Override init function.
	def __init__(self):
		# Call super class init function.
		super(serialThread, self).__init__()


class printer(threading.Thread):
	def __init__(self, settings, queue):

		# Internalise parameters.
		self.settings = settings
		self.queue = queue
		
		# Stop event.
		self.stopThread = threading.Event()
		
		# Configure and open serial.
		try:
			self.serial = serial.Serial(
				port=self.settings['Port'].value,
				baudrate=self.settings['Baud rate'].value,
				bytesize = serial.EIGHTBITS, #number of bits per bytes
				parity = serial.PARITY_NONE, #set parity check: no parity
				stopbits = serial.STOPBITS_ONE,
				timeout = 0	# Wait for incoming bytes forever.
				)
		# If serial port does not exist...
		except serial.SerialException:
			# ... define a dummy.
			self.serial = None

		# Call super class init function.
		super(serialThread, self).__init__()


	# Override run function.
	# Send a command string with optional value.
	# Method allows to retry sending until ack is received as well
	# as waiting for printer to process the command.
	def run(self, value=None, retry=False, wait=None):
		# If serial exists...
		if self.serial != None:
			# ... start infinite loop that sends and waits for ack.
			count = 0
			while count < 5 and not self.stopThread.isSet():
				# Set timeout to 5 seconds.
				self.serial.timeout = 5
				# Create command string from string and value.
				# Separate string and value by space.
				if value != None:
					string = string + " " + str(value)
				# Place send message in queue.
				self.queue.put("Sending command \"" + string + "\".")
				# Send command.
				self.serial.write(string)
				# If retry flag is set...
				if retry:
					# ... listen for ack until timeout.
					printerResponse = self.serial.readline().strip()
					# Compare ack with sent string. If match...
					if retry and printerResponse == string:
						# Place success message in queue.
						self.queue.put("Command \"" + string + "\" sent successfully.")
						if wait != None:
							self.queue.put("Wait for printer to finish...")
						# ... exit the send loop.
						break
				# If retry flag is not set...
				else:
					# ... exit the loop.
					break
				# Increment counter.
				count += 1
				# Place giving up message in queue if necessary.
				if counter == 5:
					self.queue.put("Printer not responding. Giving up...")
		
			# Wait for response from printer that signals end of action.		
			# If wait value is provided...
			if wait != None:
				while count < wait and not self.stopThread.isSet():
					# ... set timeout to one second...
					self.serial.timeout = 1
					# ... and listen for "done" string until timeout.
					printerResponse = self.serial.readline().strip()
					# Listen for "done" string.Check if return string is "done".
					if printerResponse == "done":
						self.queue.put("Printer done.")
						break
					else:
						count += 1
				# In case of timeout...
				if count == wait:
					# ... place fail message.
					self.queue.put("Printer did not finish within timeout.")
			# Reset the timeout.
			self.serial.timeout = None
		
	# Send a command string with optional value.
	# Method allows to retry sending until ack is received as well
	# as waiting for printer to process the command.
	def sendCommand(string, value=None, retry=False, wait=None):
		self.run(string, value, retry, wait)
	
	def stop()
		self.queue.put("Stopping serial.")
		self.stopThread.set()
		
	def close(self):
		self.serial.close
	
	# Commands.
	def buildHome(self):
		self.serial.write("buildHome")
		self.waitForAckInfinite()
		
	def buildBaseUp(self):
		while 1:
			self.serial.timeout = 5
			self.serial.write("buildBaseUp")
			printerResponse = self.serial.readline()           # Wait for 5 sec for anything
			print "PRINTER RESPONSE: " + printerResponse
			printerResponse = printerResponse.strip()
			if printerResponse == "done":
				break
			else:
				print "      No response from printer. Resending command..."
		self.serial.timeout = None


		
	def buildUp(self):
		while 1:
			self.serial.write("buildUp")
			self.serial.timeout = 5
			printerResponse = self.serial.readline()           # Wait for 5 sec for anything
			print "PRINTER RESPONSE: " + printerResponse
			printerResponse = printerResponse.strip()
			if printerResponse == "done":
				break
			else:
				print "      No response from printer. Resending command..."
		self.serial.timeout = None
		
	def buildTop(self):
		self.serial.write("buildTop")
		self.waitForAckInfinite()
		
	def tilt(self):
		self.serial.write("tilt")
		self.waitForAckInfinite()
		
	def setStart(self):
		self.serial.write("printingFlag 1")
		
	def setStop(self):
		self.serial.write("printingFlag 0")
		
	# Settings.
	def setLayerHeight(self):
		self.serial.write("buildLayer " + str(self.settings.getLayerHeight() * self.settings.getStepsPerMm()))
		
	def setBaseLayerHeight(self):
		self.serial.write("buildBaseLayer " + str(self.settings.getBaseLayerHeight() * self.settings.getStepsPerMm()))
		
	def setBuildSpeed(self):
		self.serial.write("buildSpeed " + str(self.settings.getBuildSpeed))
			
	def setTiltSpeedSlow(self):
		self.serial.write("tiltSpeed " + str(self.settings.getTiltSpeedSlow))

	def setTiltSpeedFast(self):
		self.serial.write("tiltSpeed " + str(self.settings.getTiltSpeedFast))
		
	def setTiltAngle(self):
		self.serial.write("tiltAngle " + str(self.settings.getTiltAngle))
		
	def setNumberOfSlices(self, numberOfSlices):
		self.serial.write("nSlices " + str(numberOfSlices))
		
	def setCurrentSlice(self, currentSlice):
		self.serial.write("slice " + str(currentSlice))
	
#	def setTimeout(self, timeout):
#		self.serial.timeout = timeout	# Timeout for readline command. 0 is infinity, other values are seconds.

#	def waitForAckFinite(self,timeout):
#		self.serial.timeout = timeout
#		printerResponse = self.serial.readline()           # Wait for 5 sec for anything
#		print "PRINTER RESPONSE: " + printerResponse
#		printerResponse = printerResponse.strip()
#		if printerResponse=="done":
#			return 1
#		elif printerResponse != "done":
#			print "Got strange response from printer: " + printerResponse
#			return 0
#		elif printerResponse == ""
#			return 0


	def waitForAckInfinite(self):
		print "waitForAck"
		self.serial.timeout = None
		printerResponse = self.serial.readline()           # Wait forever for anything
		print "PRINTER RESPONSE: " + printerResponse
		printerResponse = printerResponse.strip()
		if printerResponse=="done":
			return "done"
		elif printerResponse != "done":
			print "Got strange response from printer: " + printerResponse
			return None
		else:
			return None

	
	def ping(self):
		self.serial.write("ping")
		self.serial.timeout = 10
		printerResponse = self.serial.readline()           # Wait forever for anything
		printerResponse = printerResponse.strip()
		if printerResponse!="ping":
			return 0
		else:
			return 1
			
	def close(self):
		self.serial.close()
#		print "printer serial closed"


#dontNeedThis = serialPrinter.flushInput()		

class projector:

	def __init__(self):
		self.serial = serial.Serial(
			port='/dev/ttyUSB0',
			baudrate=9600,
			bytesize = serial.EIGHTBITS, #number of bits per bytes
			parity = serial.PARITY_NONE, #set parity check: no parity
			stopbits = serial.STOPBITS_ONE
	)
	
	def activate(self):
		self.serial.write("* 0 IR 001"+'\r')

	def deactivate(self):
		self.serial.write("* 0 IR 002"+'\r')

	def close(self):
		self.serial.close()
#		print "projector serial closed"
