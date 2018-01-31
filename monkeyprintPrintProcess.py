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

import time
import re
import threading, Queue
import monkeyprintSerial







class stringEvaluator:

	def __init__(self, settings, modelCollection):
		self.settings = settings
		self.modelCollection = modelCollection

	def parseCommand(self,command):
		# Find stuff in curly braces.
		# Add () around [...]+ to suppress the curly braces in the result.
		#curlyBraceContents = re.findall(r"\{[A-Za-z\$\+\*\-\/]+\}", command)
		curlyBraceContents = re.findall(r"\{[^\{^\}]+\}", command)
		# Find substrings.
		curlyBraceContentsEvaluated = []
		for expression in curlyBraceContents:
			# Strip the curly braces.
			expressionContent = expression[1:-1]
#			print "Found expression: " + expressionContent
			# Test if there are prohibited chars inside.
			# We only want letters, spaces and +-*/.
			# Create a pattern that matches what we don't want.
			allowedPattern = re.compile('[^A-Z^a-z^\+^\-^\*^\/^\$^ ]+')
			# Findall will return a list of prohibited chars if it finds any.
			prohibitedChars = allowedPattern.findall(expressionContent)
			# If not...
			if len(prohibitedChars) == 0:
#				print "   Expression valid. Processing..."
				# ... do the processing.

				# Replace all $-variables with the corresponding values.
				#values = []
				# First, find all $-variables.
				variables = re.findall(r"\$[A-Za-z]+", expressionContent)
#				print "   Found variables: " + str(variables)
				# Iterate through the $-variables...
				for variable in variables:
					# ... and get the corresponding value from the settings.
					#values.append(self.replaceWithValue(variable))
					value = self.replaceWithValue(variable[1:])
					expressionContent = expressionContent.replace(variable, value)
#				print "   Replaced variables: " + str(expressionContent)
				# Evaluate the expression.
				result = "0"
				try:
					result = str(eval(expressionContent))
#					print "Result: " + result
				except SyntaxError:
					print "   Something went wrong while parsing G-Code variables. Replacing by \"0\""
				#curlyBraceContentsEvaluated.append(result)

				# Replace curly brace expression by result.
				command = command.replace(expression, result)

			# If we found prohibited chars...
			else:
#				print "Prohibited characters " + str(prohibitedChars) + " found. Check your G-Code string."
				command = command.replace(expression, "0")
#		print "Finished G-Code command: " + command

		return command


	def replaceWithValue(self, variable):
#		print "      Processing variable: " + variable
		variableValid = True
		if variable == "layerHeight":
			value = str(self.settings['layerHeight'].value)
		elif variable == "buildDir":
			if self.settings['Reverse build'].value:
				value = "-1"
			else:
				value = "1"
		elif variable == "tiltDist":
			value = str(self.settings['Tilt distance GCode'].value)
		elif variable == "tiltDir":
			if self.settings['Reverse tilt'].value:
				value = "-1"
			else:
				value = "1"
		elif variable == "shutterPosOpen":
			value = str(self.settings['Shutter position open GCode'].value)
		elif variable == "shutterPosClosed":
			value = str(self.settings['Shutter position closed GCode'].value)
		else:
			value = "0"
			variableValid = False

		if variableValid:
			pass
#			print "      Replacing by " + value + "."
		else:
			print "      Unknown G-Code variable found: \"" + variable + "\". Replacing by \"0\"."

		return value










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
		self.stringEvaluator = stringEvaluator(self.settings, self.modelCollection)

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
	# TODO: Pass GCode command to expose method.
	# Can be used to trigger camera during exposure.
	def expose(self):
		# Get exposure time.
		if self.slice < self.settings['numberOfBaseLayers'].value:
			self.exposureTime = self.settings['exposureTimeBase'].value
		else:#elif self.slice > 0:
			self.exposureTime = self.settings['exposureTime'].value
		self.queueConsole.put("   Exposing with " + str(self.exposureTime) + " s.")
		self.setGuiSlice(self.slice)
		# Wait during exposure.
		self.wait(self.exposureTime)
		# Stop exposure by writing -1 to queue.
		self.setGuiSlice(-1)





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
	def wait(self, timeInterval):
		timeCount = 0
		timeStart = time.time()
		index = 0
		while timeCount < timeInterval:
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
				#TODO: do this for GCode board.
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

