# -*- coding: latin-1 -*-
#
#	Copyright (c) 2015-2016 Paul Bomke
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
import monkeyprintCommands
import time








class printProcess(threading.Thread):

	# Init function.
	def __init__(self, modelCollection, settings, queueSliceOut, queueSliceIn, queueStatus, queueConsole, queueCarryOn=None):
	# TODO: implement hold until carry on communication with gui.
	# TODO: merge all queues into one, send tuple with [infoType, info]

		# Internalise settings.
		self.settings = settings
		self.modelCollection = modelCollection
		self.queueSliceOut = queueSliceOut
		self.queueSliceIn = queueSliceIn
		self.queueStatus = queueStatus
		self.queueConsole = queueConsole

		# Are we in debug mode?
		self.debug = self.settings['debug'].value

		# Initialise stop flag.
		self.stopThread = threading.Event()

		# Initialise hold flag.
		self.holdThread = threading.Event()

		# Call super class init function.
		super(printProcess, self).__init__()

		# Create serial port.
		self.serialPrinter = self.createSerial()

		# Create serial port for projector. Will be None if not existant.
		self.serialProjector = self.createProjectorSerial()

		# Submit success message.
		self.queueConsole.put("Print process initialised.")
		print "Print process initialised."




		# Create G-Code string maker.
		self.stringEvaluator = monkeyprintCommands.stringEvaluator(self.settings, self.modelCollection)

		# Set up slice number.
		self.numberOfSlices = 0
		self.slice = 1
		self.exposureTime = 1.0



	def run(self):
		# Get the print process command list.
		self.printProcessList = self.settings.getPrintProcessList()

		# Index of current position in print process command list.
		commandIndex = 0

		self.slice = 0
		self.numberOfSlices = self.modelCollection.getNumberOfSlices()




		# Run pre-loop commands. *********************************************
		print "Running pre-loop commands. ************************************"
		while(True):
			# Check if we are done with pre-loop commands.
			if self.printProcessList[commandIndex][0] == "Start loop":
				commandIndex += 1
				break
			# If not, run next command.
			else:
				self.commandRun(self.printProcessList[commandIndex])
				commandIndex += 1

		# Save index of loop start.
		loopStartIndex = commandIndex


		# Run loop commands for each slice. **********************************
		print "Running loop commands. ****************************************"
		# Loop through slices.
		while self.slice < self.numberOfSlices and not self.stopThread.isSet():
			print "Printing slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ". *********"
			self.queueStatus.put("printing:nSlices:" + str(self.numberOfSlices))
			self.queueStatus.put("printing:slice:" + str(self.slice))
			# For each slice, loop through loop commands.
			while(True):
				if self.printProcessList[commandIndex][0] == "End loop":
					print "End loop found."
					# If number of slices is reached or stop flag was set...
					if self.slice == self.numberOfSlices - 1 or self.stopThread.isSet():
						#... set command index to first post loop command.
						commandIndex += 1
					# If ordinary loop end...
					else:
						# ... reset command index to start of loop.
						commandIndex = loopStartIndex
					self.slice += 1
					break
				else:
					self.commandRun(self.printProcessList[commandIndex])
					commandIndex += 1


		# Run post-loop commands. ********************************************
		print "Running post-loop commands. ***********************************"
		while(commandIndex < len(self.printProcessList)):
			self.commandRun(self.printProcessList[commandIndex])
			commandIndex += 1


		# Shut down nicely. **************************************************
		print "Print stopped after " + str(self.slice-1) + " slices."
		self.queueStatus.put("stopped:slice:"+ str(self.slice-1))
		# Wait a bit to give people a chance to read the last message.
		time.sleep(3)
		# Return main thread to idle mode and send projector window destroy message.
		self.queueStatus.put("idle:slice:0")
		self.queueStatus.put("destroy")





	def commandRun(self, command):
		# Pause if on hold.
		while(self.holdThread.isSet()):
			time.sleep(0.5)
		# Run internal commands.
		if command[3] == 'internal':
			print "Internal command:    \"" + command[0] + "\""
			# Run the respective command.
			if command[0] == "Expose":
				self.expose()
			elif command[0] == "Wait":
				self.wait(eval(command[1]))
			elif command[0] == "Projector on":
				self.serialProjector.activate()
			elif command[0] == "Projector off":
				self.serialProjector.deactivate()


		# Run gCode serial command.
		elif command[3] == 'serialGCode':
			commandString = self.stringEvaluator.parseCommand(command[1])
			print "G-Code command:      \"" + command[0] + "\": "  + commandString
			self.serialPrinter.sendGCode([commandString, None, True,None])

		# Run monkeyprint serial command.
		elif command[3] == 'serialMonkeyprint':
			commandString = command[2]
			print "Monkeyprint command: \"" + command[0] + "\": "  + command[2]
			self.serialPrinter.send([commandString, None, True,None])





	# Internal print commands. ################################################

	# Start exposure by writing slice number to queue.
	def expose(self):
		# Get exposure time.
		if self.slice == 0:
			self.exposureTime = self.settings['exposureTimeBase'].value
		elif self.slice > 0:
			self.exposureTime = self.settings['exposureTime'].value
		self.queueConsole.put("   Exposing with " + str(self.exposureTime) + " s.")
		self.setGuiSlice(self.slice)
		# Wait during exposure. Wait function also fires camera trigger if exposure triggering has been selected.
		self.wait(self.exposureTime, trigger=(not self.debug and self.settings['camTriggerWithExposure'].value))
		# Stop exposure by writing -1 to queue.
		self.setGuiSlice(-1)
		# Fire the camera trigger if after exposure triggering has been selected.
		if not self.debug and self.settings['camTriggerAfterExposure'].value == True and self.settings['monkeyprintBoard'].value == True:
				self.queueConsole.put("   Triggering camera.")
				print "Triggering camera."
				self.serialPrinter.send(['triggerCam', None, False, None])




	# Helper methods. #########################################################

	# Stop the thread.
	def stop(self):
		#self.queueStatus.put("Cancelled. Finishing current action.")
		self.queueStatus.put("stopping::")
		# Stop printer process by setting stop flag.
		self.stopThread.set()

	# Send slice number to GUI if nothing's in the queue.
	def queueSliceSend(self, sliceNumber):
		# Empty the response queue.
		if not self.queueSliceIn.empty():
			self.queueSliceIn.get();
		# Send the new slice number.
		while not self.queueSliceOut.empty():
			time.sleep(0.1)
		self.queueSliceOut.put(sliceNumber)

	# Wait until response from GUI arrives.
	def queueSliceRecv(self):
		while not self.queueSliceIn.qsize():
			time.sleep(0.1)
		result = self.queueSliceIn.get()
		return result

	#
	def setGuiSlice(self, sliceNumber):
		# Set slice number to queue.
		self.queueSliceSend(sliceNumber)

		# Wait until gui acks that slice is set.
		# self.queueSliceRecv blocks until slice is set in gui.
		if self.queueSliceRecv() and self.debug:
			if sliceNumber >=0:
				pass
	#			print "Set slice " + str(sliceNumber) + "."
			else:
				pass
	#			print "Set black."

	def setBlack(self):
		self.setGuiSlice(-1)


	# Non blocking wait function.
	def wait(self, timeInterval, trigger=False):
		timeCount = 0
		timeStart = time.time()
		index = 0
		while timeCount < timeInterval:
			# Fire the camera during exposure if desired.
			# Do not wait for ack to keep exposure time precise.
			if not self.debug and trigger and index == 2 and self.settings['monkeyprintBoard'].value == True:
				self.queueConsole.put("   Triggering camera.")
				self.serialPrinter.send(['triggerCam', None, False, None])
			time.sleep(.1)
			timeCount = time.time() - timeStart
			index += 1

	def hold(self):
		pass


	def createSerial(self):
	# Create printer serial port.
#		if not self.debug and not self.stopThread.isSet():
			self.queueStatus.put("preparing:connecting:")
			serialPrinter = monkeyprintSerial.printerStandalone(self.settings)
			# Check if serial is operational.
			if serialPrinter.serial == None and not self.debug:
				self.queueStatus.put("error:connectionFail:")
				#self.queueStatus.put("Serial port " + self.settings['Port'].value + " not found. Aborting.")
				self.queueConsole.put("Serial port " + self.settings['port'].value + " not found. Aborting.\nMake sure your board is plugged in and you have defined the correct serial port in the settings menu.")
				print "Connection to printer not established. Aborting print process. Check your settings!"
				self.stopThread.set()
			elif not self.debug:
				# Send ping to test connection.
				if self.settings['monkeyprintBoard'].value:
					if serialPrinter.send(["ping", None, True, None]) == True:
						self.queueStatus.put("preparing:connectionSuccess:")
						#self.queueStatus.put("Connection to printer established.")
						print "Connection to printer established."
			return serialPrinter
#		else:
#			return None


	# Create projector serial port.
	def createProjectorSerial(self):
#		if not self.debug and not self.stopThread.isSet():
			#self.queueStatus.put("Connecting to projector...")
			self.queueStatus.put("preparing:startingProjector:")
			serialProjector = monkeyprintSerial.projector(self.settings)
			if serialProjector.serial == None:
				#self.queueStatus.put("Projector not found on port " + self.settings['Port'].value + ". Start manually.")
				self.queueStatus.put("error:projectorNotFound:")
				self.queueConsole.put("Projector not found on port " + self.settings['port'].value + ". \nMake sure you have defined the correct serial port in the settings menu.")
				projectorControl = False
			else:
				#self.queueStatus.put("Projector started.")
				self.queueStatus.put("preparing:projectorConnected:")
			return serialProjector

'''


class printProcess(threading.Thread):

	# Init function.
	def __init__(self, modelCollection, settings, queueSliceOut, queueSliceIn, queueStatus, queueConsole, queueCarryOn=None):
	# TODO: implement hold until carry on communication with gui.
	# TODO: merge all queues into one, send tuple with [infoType, info]
		# Internalise settings.
		self.settings = settings
		self.queueSliceOut = queueSliceOut
		self.queueSliceIn = queueSliceIn
		self.queueStatus = queueStatus
		self.queueConsole = queueConsole


		self.runGCode = not self.settings['monkeyprintBoard'].value

		# Create GCode commands.
		if self.runGCode:
			# Create parser object.
			self.gCodeParser = monkeyprintCommands.stringEvaluator(self.settings, modelCollection)
			# Parse GCode variables.
			self.gCodeTiltCommand = self.gCodeParser.parseCommand(self.settings['Tilt GCode'].value)
			self.gCodeBuildCommand = self.gCodeParser.parseCommand(self.settings['Build platform GCode'].value)
			self.gCodeShutterOpenCommand = self.gCodeParser.parseCommand(self.settings['Shutter open GCode'].value)
			self.gCodeShutterCloseCommand = self.gCodeParser.parseCommand(self.settings['Shutter close GCode'].value)
			# Get start and end code.
			self.gCodeStartCommands = self.settings['Start commands GCode'].value
			self.gCodeEndCommands = self.settings['End commands GCode'].value
			self.gCodeHomeCommand = self.settings['Home GCode'].value

			print "Tilt command: " + self.gCodeTiltCommand
			print "Build command: " + self.gCodeBuildCommand
			print "Shutter open command: " + self.gCodeShutterOpenCommand
			print "Shutter close command: " + self.gCodeShutterCloseCommand
			print "Start command: " + self.gCodeStartCommands
			print "End command: " + self.gCodeEndCommands
			print "Home command: " + self.gCodeHomeCommand

		# Get other relevant values.
		self.numberOfSlices = modelCollection.getNumberOfSlices()
		self.buildStepsPerMm = int(360. / float(self.settings['buildStepAngle'].value) * float(self.settings['buildMicroStepsPerStep'].value))
		self.buildMinimumMove = int(self.buildStepsPerMm * float(self.settings['buildMinimumMove'].value))
		self.layerHeight = int(float(modelCollection.jobSettings['layerHeight'].value) / float(self.settings['buildMinimumMove'].value))
		self.tiltAngle = int(float(self.settings['tiltAngle'].value) / (float(self.settings['tiltStepAngle'].value) / float(self.settings['tiltMicroStepsPerStep'].value)))
		self.tiltStepsPerTurn = int(360. / float(self.settings['tiltStepAngle'].value) * float(self.settings['tiltMicroStepsPerStep'].value))

		# Are we in debug mode?
		self.debug = self.settings['debug'].value

		# Initialise stop flag.
		self.stopThread = threading.Event()

		# Call super class init function.
		super(printProcess, self).__init__()

		self.queueConsole.put("Print process initialised.")
		print "Print process initialised."

	# Stop the thread.
	def stop(self):
		#self.queueStatus.put("Cancelled. Finishing current action.")
		self.queueStatus.put("stopping::")
		# Stop printer process by setting stop flag.
		self.stopThread.set()

	def queueSliceSend(self, sliceNumber):
		# Empty the response queue.
		if not self.queueSliceIn.empty():
			self.queueSliceIn.get();
		# Send the new slice number.
		while not self.queueSliceOut.empty():
			time.sleep(0.1)
		self.queueSliceOut.put(sliceNumber)

	def queueSliceRecv(self):
		while not self.queueSliceIn.qsize():
			time.sleep(0.1)
		result = self.queueSliceIn.get()
		return result

	def setGuiSlice(self, sliceNumber):
		# Set slice number to queue.
		self.queueSliceSend(sliceNumber)

		# Wait until gui acks that slice is set.
		# self.queueSliceRecv blocks until slice is set in gui.
		if self.queueSliceRecv() and self.debug:
			if sliceNumber >=0:
				print "Set slice " + str(sliceNumber) + "."
			else:
				print "Set black."

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
		debug = self.settings['debug'].value
		if debug: print "Debug mode enabled."
		else: print "Debug mode disabled."
		projectorControl = True


		# Initialise printer. ################################################
		#self.queueStatus.put("Initialising print process.")
		self.queueStatus.put("preparing:nSlices:" + str(self.numberOfSlices))
		self.queueConsole.put("Initialising print process.")



		# Reset print parameters.
		self.slice = 1
		self.exposureTime = 5.


		# Create printer serial port.
		if not debug and not self.stopThread.isSet():
			self.queueStatus.put("preparing:connecting:")
			self.serialPrinter = monkeyprintSerial.printerStandalone(self.settings)
			if self.serialPrinter.serial == None:
				self.queueStatus.put("error:connectionFail:")
				#self.queueStatus.put("Serial port " + self.settings['Port'].value + " not found. Aborting.")
				self.queueConsole.put("Serial port " + self.settings['Port'].value + " not found. Aborting.\nMake sure your board is plugged in and you have defined the correct serial port in the settings menu.")
				print "Connection to printer not established. Aborting print process. Check your settings!"
				self.stopThread.set()
			else:
				# Send ping to test connection.
				if not self.runGCode:
					if self.serialPrinter.send(["ping", None, True, None]) == True:
						self.queueStatus.put("preparing:connectionSuccess:")
						#self.queueStatus.put("Connection to printer established.")
						print "Connection to printer established."


		# Send print parameters to printer.
		if not debug and not self.stopThread.isSet():
			if not self.runGCode:
				self.serialPrinter.send(['nSlices', self.numberOfSlices, True, None])
				self.serialPrinter.send(['buildRes', self.buildStepsPerMm, True, None])
				self.serialPrinter.send(['buildMinMove', self.buildMinimumMove, True, None])
				self.serialPrinter.send(['tiltRes', self.tiltStepsPerTurn, True, None])
				self.serialPrinter.send(['tiltAngle', self.tiltAngle, True, None])
				self.serialPrinter.send(['shttrOpnPs', self.settings['Shutter position open'].value, True, None])
				self.serialPrinter.send(['shttrClsPs', self.settings['Shutter position closed'].value, True, None])
			else:
				# Send start-up commands.
				#self.serialPrinter.send([self.gCodeStartCommands, None, False, None])
				pass
		elif not self.stopThread.isSet():
			if not self.runGCode:
				self.queueConsole.put("Debug: number of slices: " + str(self.numberOfSlices))
				self.queueConsole.put("Debug: build steps per mm: " + str(self.buildStepsPerMm))
				self.queueConsole.put("Debug: build minimum move: " + str(self.buildMinimumMove))
				self.queueConsole.put("Debug: tilt steps per turn: " + str(self.tiltStepsPerTurn))
				self.queueConsole.put("Debug: tilt angle steps: " + str(self.tiltAngle))
			else:
				print "Debug: GCode command: " + self.gCodeStartCommands




		# Create projector serial port.
		if not debug and not self.stopThread.isSet():
			#self.queueStatus.put("Connecting to projector...")
			self.queueStatus.put("preparing:startingProjector:")
			self.serialProjector = monkeyprintSerial.projector(self.settings)
			if self.serialProjector.serial == None:
				#self.queueStatus.put("Projector not found on port " + self.settings['Port'].value + ". Start manually.")
				self.queueStatus.put("error:projectorNotFound:")
				self.queueConsole.put("Projector not found on port " + self.settings['Port'].value + ". \nMake sure you have defined the correct serial port in the settings menu.")
				projectorControl = False
			else:
				#self.queueStatus.put("Projector started.")
				self.queueStatus.put("preparing:projectorConnected:")

		# Display black.
		print "setting slice"
		self.setGuiSlice(-1)
		print "slice set"
		# Activate projector.
		if not debug and projectorControl and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Activating projector.")
			#self.queueStatus.put("Activating projector.")
			self.queueStatus.put("preparing:startingProjector:")
			# Send projector command.
			self.serialProjector.activate()


		# Activate shutter servo.
		if not debug and not self.stopThread.isSet() and self.settings['enableShutterServo'].value:
			if not self.runGCode:
				self.serialPrinter.send(["shutterClose", None, True, None])
				self.serialPrinter.send(["shutterEnable", None, True, None])
			else:
				#self.serialPrinter.send([self.gCodeShutterCloseCommand, None, False, None])
				pass
			print "Shutter enabled."
		elif not self.stopThread.isSet() and self.settings['enableShutterServo'].value:
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeShutterCloseCommand


		# Homing build platform.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Homing build platform.")
			#self.queueStatus.put("Homing build platform.")
			self.queueStatus.put("preparing:homing:")
			print "Homing build platform."
			# Send printer command.
			if not self.runGCode:
				self.serialPrinter.send(["buildHome", None, True, 240]) # Retry, wait 240 seconds.
			else:
				#self.serialPrinter.send([self.gCodeHomeCommand, None, False, None])
				pass
		elif not self.stopThread.isSet():
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeHomeCommand


		# Tilt to get rid of bubbles.
		if not debug and not self.stopThread.isSet() and self.settings['tiltEnable'].value:
			# Send info to gui.
			self.queueConsole.put("Tilting to get rid of bubbles.")
			#self.queueStatus.put("Removing bubbles.")
			self.queueStatus.put("preparing:bubbles:")
			print "Tilting to get rid of bubbles."
			# Tilt 5 times.
			for tilts in range(3):
				print "Tilting..."
				if not self.runGCode:
					self.serialPrinter.send(["tilt", None, True, 20])
				else:
					#self.serialPrinter.send([self.gCodeTiltCommand, None, False, None])
					pass
		elif not self.stopThread.isSet() and self.settings['tiltEnable'].value:
			if self.runGCode:
				print "Debug: GCode command: " + self.gCodeTiltCommand


		# Wait for resin to settle.
		if not debug and not self.stopThread.isSet():
			# Send info to gui.
			self.queueConsole.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			#self.queueStatus.put("Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle.")
			self.queueStatus.put("preparing:resinSettle:" + str(self.settings['Resin settle time'].value))
			print "Waiting " + str(self.settings['Resin settle time'].value) + " seconds for resin to settle."
			# Wait...
			self.wait(self.settings['Resin settle time'].value)




		# Send printing flag to printer.
		if not debug and not self.stopThread.isSet():
			if not self.runGCode:
				self.serialPrinter.send(['printingFlag', 1, True, None])

		# Start the print loop.
		while not self.stopThread.isSet() and self.slice < self.numberOfSlices+1:
			self.queueConsole.put("Printing slice " + str(self.slice) + ".")
			#self.queueStatus.put("Printing slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ".")
			self.queueStatus.put("printing:nSlices:" + str(self.numberOfSlices))
			self.queueStatus.put("printing:slice:" + str(self.slice))
			if self.settings['runningOnRaspberry'].value == True:
				print ("Current slice " + str(self.slice) + " of " + str(self.numberOfSlices) + ".")
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
	#	TODO fix speed			self.serialPrinter.send(["tiltSpeed", self.settings['tiltSpeedSlow'].value, True, None])
				self.exposureTime = self.settings['exposureTimeBase'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['exposureTimeBase'].value) + " s.")
			elif self.slice == 2:
				self.exposureTime = self.settings['exposureTime'].value
				self.queueConsole.put("   Set exposure time to " + str(self.settings['exposureTime'].value) + " s.")
			elif self.slice == 20:
				#TODO: slow and fast tilting.
	#			if not debug:
	#				self.serialPrinter.send(["tiltSpeed", self.settings['Tilt speed'].value, True, None])
				self.queueConsole.put("   Switched to fast tilting.")


			# Move build platform up by one layer.
			if not debug:
				self.queueConsole.put("   Moving build platform.")
				print "Moving build platform."

				if self.slice == 1:
					if not self.runGCode:
						self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
					else:
						#self.serialPrinter.send([self.gCodeBuildCommand, None, False, None])
						pass
				else:
					if not self.runGCode:
						self.serialPrinter.send(['buildMove', self.layerHeight, True, 20])
					else:
						#self.serialPrinter.send([self.gCodeBuildCommand, None, False, None])
						pass
			else:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeBuildCommand

			# Waiting for resin to settle.
			if not debug and self.settings['Resin settle time'].value != 0.0:
				self.queueConsole.put("   Waiting for resin to settle.")
				print "Waiting for resin to settle."
				self.wait(self.settings['Resin settle time'].value)

			# Open shutter.
			if not debug and self.settings['enableShutterServo'].value:
				self.queueConsole.put("   Opening shutter.")
				print "Opening shutter."
				if not self.runGCode:
					self.serialPrinter.send(["shutterOpen", None, True, None])
				else:
					#self.serialPrinter.send([self.gCodeShutterOpenCommand, None, False, None])
					pass
			elif self.settings['enableShutterServo'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeShutterOpenCommand


			# Start exposure by writing slice number to queue.
			self.setGuiSlice(self.slice)
			# Wait during exposure. Wait function also fires camera trigger if necessary.
			self.wait(self.exposureTime, trigger=(not self.debug and self.settings['camTriggerWithExposure'].value))
			# Stop exposure by writing -1 to queue.
			self.setGuiSlice(-1)


			# Close shutter.
			if not debug and self.settings['enableShutterServo'].value:
				self.queueConsole.put("   Closing shutter.")
				print "Closing shutter."
				if not self.runGCode:
					self.serialPrinter.send(["shutterClose", None, True, None])
				else:
					#self.serialPrinter.send([self.gCodeShutterCloseCommand, None, False, None])
					pass
			elif self.settings['enableShutterServo'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeShutterCloseCommand

			# Fire the camera after exposure if desired.
			if not debug and self.settings['camTriggerAfterExposure'].value:
				self.queueConsole.put("   Triggering camera.")
				print "Triggering camera."
				self.serialPrinter.send(['triggerCam', None, False, None])

			# Tilt.
			if not debug and self.settings['tiltEnable'].value:
				self.queueConsole.put("   Tilting.")
				print "Tilting."
				if not self.runGCode:
					self.serialPrinter.send(['tilt', None, True, 20])
				else:
					#self.serialPrinter.send([self.gCodeTiltCommand, None, False, None])
					pass
			elif self.settings['tiltEnable'].value:
				if self.runGCode:
					print "Debug: GCode command: " + self.gCodeTiltCommand




			self.slice+=1

		#self.queueStatus.put("Stopping print.")
		self.queueStatus.put("stopping::")
		self.queueConsole.put("Stopping print.")
		print "Stopping print."

		# Display black.
		self.queueSliceSend(-1)

		# Disable shutter.
		if not debug and not self.stopThread.isSet()  and self.settings['enableShutterServo'].value:
			if not self.runGCode:
				self.serialPrinter.send(["shutterDisable", None, True, None])
			print "Shutter disabled."


		if not debug and not self.stopThread.isSet():
			# TODO
			# Move build platform to top.
			print "Moving build platform to top."
			if not self.runGCode:
				self.serialPrinter.send(["buildTop", None, True, 240]) # Retry, wait 240 seconds.
				# Send printing stop flag to printer.
				self.serialPrinter.send(["printingFlag", 0, True, None]) # Retry, wait 240 seconds.prin
			else:
				#self.serialPrinter.send([self.gCodeHomeCommand, None, False, None])
				#self.serialPrinter.send([self.gCodeEndCommands, None, False, None])
				pass
			# Deactivate projector.
			if projectorControl and self.serialProjector != None:
				self.serialProjector.deactivate()
			# Close and delete communication ports.
			self.serialPrinter.close()
			del self.serialPrinter
			if projectorControl:
				self.serialProjector.close()
				del self.serialProjector
		elif not self.stopThread.isSet():
			if self.runGCode:
					print "Debug: GCode command: " + self.gCodeHomeCommand
					print "Debug: GCode command: " + self.gCodeEndCommands


		#self.queueStatus.put("Print stopped after " + str(self.slice) + " slices.")
		self.queueStatus.put("stopped:slice:"+ str(self.slice-1))
		print "Print stopped after " + str(self.slice) + " slices."

		time.sleep(3)
		# TODO find a good way to destroy this object.
		self.queueStatus.put("idle:slice:0")
	#	self.queueSliceSend(0)
		self.queueStatus.put("destroy")
'''
