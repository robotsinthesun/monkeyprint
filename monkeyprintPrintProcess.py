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

import threading, Queue
import monkeyprintSerial
import time



class printProcess(threading.Thread):

	# Init function.
	def __init__(self, modelCollection, settings, queueSlice, queueStatus, queueConsole, queueCarryOn=None):
	# TODO: implement hold until carry on communication with gui.
	# TODO: merge all queues into one, send tuple with [infoType, info]
		# Internalise settings.
		self.settings = settings
		self.queueSlice = queueSlice
		self.queueStatus = queueStatus
		self.queueConsole = queueConsole
		# Get other relevant values.
		self.numberOfSlices = modelCollection.getNumberOfSlices()
		self.buildStepsPerMm = int(360. / float(self.settings['Build step angle'].value) * float(self.settings['Build microsteps per step'].value))
		self.buildMinimumMove = int(self.buildStepsPerMm * float(self.settings['Build minimum move'].value))
		self.layerHeight = int(float(modelCollection.jobSettings['Layer height'].value) / float(self.settings['Build minimum move'].value))
		self.tiltAngle = int(float(self.settings['Tilt angle'].value) / (float(self.settings['Tilt step angle'].value) / float(self.settings['Tilt microsteps per step'].value)))
		self.tiltStepsPerTurn = int(360. / float(self.settings['Tilt step angle'].value) * float(self.settings['Tilt microsteps per step'].value))

		# Are we in debug mode?
		self.debug = self.settings['Debug'].value
		
		# Initialise stop flag.
		self.stopThread = threading.Event()
		
		# Call super class init function.
		super(printProcess, self).__init__()
		
		self.queueConsole.put("Print process initialised.")
	
	# Stop the thread.	
	def stop(self):
		self.queueStatus.put("Cancelled. Finishing current action.")
		# Stop printer process by setting stop flag.
		self.stopThread.set()
	
	def queueSliceSend(self, sliceNumber):
		while not self.queueSlice.empty():
			time.sleep(0.1)
		self.queueSlice.put(sliceNumber)
	
	# Non blocking wait function.
	def wait(self, timeInterval, trigger=False):
		timeCount = 0
		timeStart = time.time()
		index = 0
		while timeCount < timeInterval:
			# Fire the camera during exposure if desired.
			# Do not wait for ack to keep exposure time precise.
			if trigger and index == 2:
				self.queueConsole.put("   Triggering camera.")
				self.serialPrinter.send(['triggerCam', None, False, None])
			time.sleep(.1)
			timeCount = time.time() - timeStart
			index += 1
	
	
	# Listen to the carry on command queue until the carry on command is issued.
	def holdUntilConfirm(self):
		pass
		
	
	# Override run function.
	def run(self):
		# Print process:
		#	Start up projector.
		# 	Homing build platform.
		#	Start slice projection with black image.
		#	Activating projector.
		#	Tilting for bubbles.
		#	Start loop.
		
		# Find out if this is a debug session without serial and projector.
		debug = self.settings['Debug'].value
		projectorControl = True
		
		
		# Initialise printer. ################################################
		self.queueStatus.put("Initialising print process.")
		self.queueConsole.put("Initialising print process.")


		# Reset print parameters.
		self.slice = 1
		self.exposureTime = 5.


		# Create printer serial port.
		if not debug and not self.stopThread.isSet():
			self.queueStatus.put("Connecting to printer...")
			self.serialPrinter = monkeyprintSerial.printerStandalone(self.settings)
			if self.serialPrinter.serial == None:
				self.queueStatus.put("Serial port " + self.settings['Port'].value + " not found. Aborting.")
				self.queueConsole.put("Serial port " + self.settings['Port'].value + " not found. Aborting.\nMake sure your board is plugged in and you have defined the correct serial port in the settings menu.")
			else:
				# Send ping to test connection.
				if self.serialPrinter.send(["ping", None, True, None]) == True:
					self.queueStatus.put("Connection to printer established.")
		
		
		# Send print parameters to printer.
		if not debug and not self.stopThread.isSet():
			self.serialPrinter.send(['nSlices', self.numberOfSlices, True, None])
			self.serialPrinter.send(['buildRes', self.buildStepsPerMm, True, None])
			self.serialPrinter.send(['buildMinMove', self.buildMinimumMove, True, None])
			self.serialPrinter.send(['tiltRes', self.tiltStepsPerTurn, True, None])
			self.serialPrinter.send(['tiltAngle', self.tiltAngle, True, None])
		elif not self.stopThread.isSet():
			self.queueConsole.put("Debug: number of slices: " + str(self.numberOfSlices))
			self.queueConsole.put("Debug: build steps per mm: " + str(self.buildStepsPerMm))
			self.queueConsole.put("Debug: build minimum move: " + str(self.buildMinimumMove))
			self.queueConsole.put("Debug: tilt steps per turn: " + str(self.tiltStepsPerTurn))
			self.queueConsole.put("Debug: tilt angle steps: " + str(self.tiltAngle))

			
			
		
		# Create projector serial port.
		if not debug and not self.stopThread.isSet():
			self.queueStatus.put("Connecting to projector...")
			self.serialProjector = monkeyprintSerial.projector(self.settings)
			if self.serialProjector.serial == None:
				self.queueStatus.put("Projector not found on port " + self.settings['Port'].value + ". Start manually.")
				self.queueConsole.put("Projector not found on port " + self.settings['Port'].value + ". \nMake sure you have defined the correct serial port in the settings menu.")
				projectorControl = False
			else:
				self.queueStatus.put("Projector started.")
		
		# Display black.
		self.queueSliceSend(-1)
		
		# Activate projector.
		if not debug and projectorControl and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Activating projector.")
			self.queueStatus.put("Activating projector.")
			# Send projector command.
			self.serialProjector.activate()
		
		
		# Homing build platform.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Homing build platform.")
			self.queueStatus.put("Homing build platform.")
			# Send printer command.
			self.serialPrinter.send(["buildHome", None, True, 240]) # Retry, wait 240 seconds.
		
		
		# Tilt to get rid of bubbles.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Tilting to get rid of bubbles.")
			self.queueStatus.put("Removing bubbles.")
			# Tilt 5 times.
			for tilts in range(5):
				self.serialPrinter.send(["tilt", None, True, 20])
		
		
		# Wait for resin to settle.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			self.queueStatus.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			# Wait...
			self.wait(self.settings['Resin settle time'].value)


		

		# Send printing flag to printer.
		if not debug and not self.stopThread.isSet():
			self.serialPrinter.send(['printingFlag', 1, True, None])
		
		# Start the print loop.
		while not self.stopThread.isSet() and self.slice < self.numberOfSlices+1:
			self.queueConsole.put("Printing slice " + str(self.slice) + ".")
			self.queueStatus.put("Printing slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ".")
			# Send slice number to printer.
			if not debug:
				pass
				# TODO change to new syntax: self.serialPrinter.setCurrentSlice(self.slice)
			# Get settings and adjust exposure time and tilt speed.
			# For first layer use base exposure time.
			# Use slow tilt from start.
			# Use fast tilt from 20th layer.
			if self.slice == 1:
	#			if not debug:
	#	TODO fix speed			self.serialPrinter.send(["tiltSpeed", self.settings['Tilt speed slow'].value, True, None])
				self.exposureTime = self.settings['Exposure time base'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['Exposure time base'].value) + " s.")
			elif self.slice == 2:
				self.exposureTime = self.settings['Exposure time'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['Exposure time base'].value) + " s.")
			elif self.slice == 20:
	#			if not debug:
	#				self.serialPrinter.send(["tiltSpeed", self.settings['Tilt speed'].value, True, None])
				self.queueConsole.put("   Switched to fast tilting.")
			# Start exposure by writing slice number to queue.
			self.queueSliceSend(self.slice)
			self.queueConsole.put("   Exposing with " + str(self.exposureTime) + " seconds.")
			
			# Wait during exposure. Wait function also fires camera trigger if necessary.
			self.wait(self.exposureTime, trigger=(not self.debug and self.settings['camTriggerWithExposure'].value))
				
			# Stop exposure by writing -1 to queue.
			self.queueSliceSend(-1)
			
			# Fire the camera after exposure if desired.
			if not debug and self.settings['camTriggerAfterExposure'].value:
				self.queueConsole.put("   Triggering camera.")
				self.serialPrinter.send(['triggerCam', None, False, None])
			
			# Tilt.
			self.queueConsole.put("   Tilting.")
			if not debug:
				self.serialPrinter.send(['tilt', None, True, 20])

			# Move build platform up by one layer.
			self.queueConsole.put("   Moving build platform.")
			if self.slice == 1:
				if not debug:
					self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
			else:
				if not debug:
					self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
			
			# Waiting for resin to settle.
			self.queueConsole.put("   Waiting for resin to settle.")
			self.wait(self.settings['Resin settle time'].value)
			
			self.slice+=1
		
		self.queueStatus.put("Stopping print.")
		self.queueConsole.put("Stopping print.")
		
		# Display black.
		self.queueSliceSend(-1)

		
		if not debug:
			# TODO
			# Move build platform to top.
			self.serialPrinter.send(["buildTop", None, True, 240]) # Retry, wait 240 seconds.
			# Send printing stop flag to printer.
			self.serialPrinter.send(["printingFlag", 0, True, None]) # Retry, wait 240 seconds.prin
			# Deactivate projector.
			if projectorControl:
				self.serialProjector.deactivate()
			# Close and delete communication ports.
			self.serialPrinter.close()
			del self.serialPrinter
			if projectorControl:
				self.serialProjector.close()
				del self.serialProjector

		
		self.queueStatus.put("Print stopped after " + str(self.slice) + " slices.")
		
		time.sleep(3)
		# TODO find a good way to destroy this object.
		self.queueStatus.put("Idle...")
	#	self.queueSliceSend(0)
		self.queueStatus.put("destroy")
