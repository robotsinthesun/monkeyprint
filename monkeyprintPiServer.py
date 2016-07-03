#! /usr/bin/python
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
import pygtk
pygtk.require('2.0')
import gtk, gobject
import Queue
import monkeyprintSocketCommunication
import zmq
import time
import sys
import monkeyprintModelHandling
import monkeyprintPrintProcess
import monkeyprintGuiHelper
import monkeyprintSettings
import os


class monkeyprintPiServer:
	def __init__(self, port, debug):
	
		self.runningOnRasPi = True

		self.port = port
		self.debug = debug
		
		self.console = None
		
		# Printer messages.
		# Status can be: Idle, Slicing, Printing, Done

		self.sliceNumber = 0
		
		self.printFlag = False
		
		# Local file path.
		self.localPath = os.getcwd() + "/tmpServerFiles"
		self.localFilename = "/currentPrint.mkp"
		
		# Create the working directory.
		if not os.path.isdir(self.localPath):
			os.mkdir(self.localPath)
		
		self.printProcess = None


		# Allow background threads.****************************
		# Very important, otherwise threads will be
		# blocked by gui main thread.
		gtk.gdk.threads_init()
		
		
		# Register timeout functions. *************************
		pollPrintQueuesId = gobject.timeout_add(50, self.pollPrintQueues)
	#	statusUpdateId = gobject.timeout_add(10, self.pollPrinterStatus)


		
		# Create file transfer socket.
		self.queueFileTransferIn = Queue.Queue(maxsize=1)
		self.queueFileTransferOut = Queue.Queue(maxsize=1)
		self.fileReceiver = monkeyprintSocketCommunication.fileReceiver(ip="*", port="6000", queueFileTransferIn=self.queueFileTransferIn, queueFileTransferOut=self.queueFileTransferOut)
		self.fileReceiver.start()
		
		
		# Create queues for inter-thread communication.********
		# Queue for setting print progess bar.
		self.queueSliceOut = Queue.Queue(maxsize=1)
		self.queueSliceIn = Queue.Queue(maxsize=1)
		# Queue for commands.
		self.queueCommands = Queue.Queue(maxsize=1)
		# Queue for status infos displayed above the status bar.
		self.queueStatus = Queue.Queue()
		# Queue for console messages.
		self.queueConsole = Queue.Queue()

		

		# Create settings dictionary object for machine and program settings.
		self.programSettings = monkeyprintSettings.programSettings()
	
		# Update settings from file.	
		self.programSettings.readFile()
		
		
		
		# Create communication socket.
		self.socket = monkeyprintSocketCommunication.communicationSocket(port=self.programSettings['Network port RasPi'].value, ip=None, queueCommands=self.queueCommands)
		# Add socket listener to GTK event loop.
		gobject.io_add_watch(self.socket.fileDescriptor, gobject.IO_IN, self.socket.callbackIOActivity, self.socket.socket)
		#gobject.io_add_watch(self.socket.fileDescriptor, gobject.IO_IN, self.zmq_callback, self.socket.socket)
		
				

		# Set debug mode if specified.
		if self.debug==True:
			self.programSettings['Debug'].value = debug
			print "Debug mode active."
		else:
			self.programSettings['Debug'].value = False
	
		# Create model collection object.
		# This object contains model data and settings data for each model.
		# Pass program settings.
		self.modelCollection = monkeyprintModelHandling.modelCollection(self.programSettings)
	
	
		#TODO disable this...
		self.modelCollection.jobSettings['Exposure time'].value = 0.1
		print ("Exposure time: " + str(self.modelCollection.jobSettings['Exposure time'].value) + ".")

		
		print "Monkeyprint started in server mode."
		gtk.main()
	
	
	def printProcessStart(self, filename):
		self.queueStatus.put("preparing:transferring:")
		self.parameter = ""
		self.value = ""
		self.sliceNumber = 0
		print ("Starting print job from file " + filename + ".")
		
		
		# Make sure status messages get sent.
		self.pollPrintQueues()
				
				
		# Request settings file from PC.
		print "Loading settings file from master."
		self.queueFileTransferIn.put(("get", "./programSettings.txt"+":"+self.localPath+"/programSettings.txt"))
		# Wait until transmission is complete.
		while not self.queueFileTransferOut.qsize():
			time.sleep(0.1)
		transmissionResult = self.queueFileTransferOut.get()
		if transmissionResult != "success":
			print "Transmission failed. Cancelling."
			return
			
			
			
		# Make sure status messages get sent.
		self.pollPrintQueues()
		
		
		
		# Update settings from file.	
		self.programSettings.readFile(self.localPath+"/programSettings.txt")
		
		# Set rasperry pi setting.
		self.programSettings['Print from Raspberry Pi?'].value = True
#		self.programSettings['Debug'].value = True
		
		
		
		# Get the mkp file.
		print "Loading project file from master."
		self.queueFileTransferIn.put(("get", filename + ":"+self.localPath+self.localFilename))
		# Wait until transmission is complete.
		while not self.queueFileTransferOut.qsize():
			time.sleep(0.1)
		transmissionResult = self.queueFileTransferOut.get()
		if transmissionResult != "success":
			print "Transmission failed. Cancelling."
			return
		
		
		# Make sure status messages get sent.
		self.pollPrintQueues()
		
		

		self.queueStatus.put("preparing:loading:")
		print "Preparing print."
		print self.localPath + self.localFilename
		self.modelCollection.loadProject(self.localPath + self.localFilename)
		print ("Project file: " + str(filename) + " loaded successfully.")
		print "Found the following models:"
		for model in self.modelCollection:
			if model != 'default':
				print ("   " + model)
		
		
		# Send number of slices to gui.
		self.queueStatus.put("slicing:nSlices:" + str(self.modelCollection.getNumberOfSlices()))
		
		
		# Make sure status messages get sent.
		self.pollPrintQueues()
		
		
		# Start the slicer.
		#self.status = "slicing"
		self.modelCollection.updateSliceStack()
					# TODO: get current slice number to show on progress bar.
		print ("Starting slicer.")

		# Wait for all slicer threads to finish.
		while(self.modelCollection.slicerRunning()):
			self.modelCollection.checkSlicerThreads()
			time.sleep(.5)
			sys.stdout.write('.')
			sys.stdout.flush()
	
		# Start print process when slicers are done.
		print "\nSlicer done. Starting print process."
		
		
		# Make sure status messages get sent.
		self.pollPrintQueues()
		
		
		
		# Create the projector window.
		# Initialise base class gtk window.********************
		self.projectorDisplay = monkeyprintGuiHelper.projectorDisplay(self.programSettings, self.modelCollection)
		# Set function for window close event.
		self.projectorDisplay.connect("delete-event", self.on_closing, None)
		# Show the window.
		self.projectorDisplay.show()
		
		
		# Make sure status messages get sent.
		self.pollPrintQueues()
		
		
		
		# Register image update
		# Update the progress bar, projector image and 3d view. during prints.
	#	printProcessUpdateId = gobject.timeout_add(10, self.updateSlicePrint)
		
		
		# Create the print process thread.
		# TODO make queueConsole an optional argument to printProcess.__init__
		self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSliceOut, self.queueSliceIn, self.queueStatus, self.queueConsole)
		
		# Start the print process.
		self.printProcess.start()

		
# *************************************************************************
	# Function that updates all relevant GUI elements during prints. **********
	# *************************************************************************
	# This runs every 100 ms as a gobject timeout function.
	# Updates 3d view and projector view. Also forwards status info.
	def pollPrintQueues(self):
	#	print "polling print queues"
		# Check the queues...
		# If slice number queue has slice number...
		if self.queueSliceOut.qsize():
			# ... get it from the queue.
			sliceNumber = self.queueSliceOut.get()
			# If it's an actual slice number...
			if not self.runningOnRasPi:
				# Update gui stuff.
				if sliceNumber >=0:
					# Set 3d view to given slice.
					self.modelCollection.updateAllSlices3d(sliceNumber)
					self.renderView.render()
					# Update slice preview in the gui.
					self.sliceView.updateImage(sliceNumber)
			# Set slice view to given slice. If sliceNumber is -1 black is displayed.
			if self.projectorDisplay != None:
				self.projectorDisplay.updateImage(sliceNumber)
			
			# Signal to print process that slice image is set and exposure time can begin.
			if self.queueSliceIn.empty():
				self.queueSliceIn.put(True)

		# If status queue has info...
		if self.queueStatus.qsize():
			print "Found status message: " + message + ""
			# ... get the status.
			message = self.queueStatus.get()
			# Check if this is the destroy message for terminating the print window.
			if message == "destroy":
				# If running on Raspberry, destroy projector display and clean up files.
				if self.runningOnRasPi:
					print "Print process finished! Idling..."
					self.printFlag = False
					del self.printProcess
					self.projectorDisplay.destroy()
					del self.projectorDisplay
					# Remove print file.
					if os.path.isfile(self.localPath + self.localFilename):
						os.remove(self.localPath + self.localFilename)
				# If not running on Raspberry Pi, destroy projector display and reset GUI.
				else:
					self.buttonPrintStart.set_sensitive(True)
					self.buttonPrintStop.set_sensitive(False)
					self.modelCollection.updateAllSlices3d(0)
					self.renderView.render()
					self.progressBar.updateValue(0) 
					self.printFlag = False
					del self.printProcess
					self.projectorDisplay.destroy()
					del self.projectorDisplay
			else:
				# If running on Raspberry forward the message to the socket connection.
				if self.runningOnRasPi:
					print "Sending: " + message
					self.socket.sendMulti("status", message)
				# If not, update the GUI.
				else:
					self.processStatusMessage(message)
		
		# Poll the command queue.
		# Only do this when running on Raspberry Pi.
		# If command queue has info...
		if self.runningOnRasPi and self.queueCommands.qsize():
			# ... get the command.
			command = self.queueCommands.get()
			self.processCommandMessage(command)

		# If console queue has info...
		if self.queueConsole.qsize():
			if self.console != None:
				self.console.addLine(self.queueConsole.get())

		# Return true, otherwise function won't run again.
		return True	



	# *************************************************************************
	# Function to process output of commandQueue and control print process. ***
	# *************************************************************************
	def processCommandMessage(self, message):
		# Only needed on Rasperry Pi.
		if self.runningOnRasPi:
			# Split the string.
			command, parameter = message.split(":")
			if command == "start":
				if self.printFlag:
					pass
					# TODO: Send error message.
					#zmq_socket.send_multipart(["error", "Print running already."])
				else:
					# Start the print. Parameter is the file path in case of running from Pi.
					self.printProcessStart(parameter)
					print "started print process"
			elif command == "stop":
				if self.printFlag:
					self.printProcessStop()
					#self.printProcess.stop()
			elif command == "pause":
				if self.printFlag:
					self.printProcess.pause()
		



	
	# React to commands received from master PC via socket connection.
	'''
	def zmq_callback(self, fd, condition, zmq_socket):
		print "foo"
		while zmq_socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:
			# Read message from the socket.
			msg = zmq_socket.recv_multipart()
			command, parameter = msg
			print command
			
			if command == "print":
				if self.printFlag:
					zmq_socket.send_multipart(["error", "Print running already."])
				else:
					zmq_socket.send_multipart(["status", "preparing", "", ""])
					self.startPrint(parameter)
			
			elif command == "stop":
				if self.printFlag:
					self.printProcess.stop()
			
				
			elif command == "status":
				zmq_socket.send_multipart(["status", self.status, self.parameter, self.value])
			#	if self.status=="slicing":
			#		zmq_socket.send_multipart(["status", self.status, "slice", str(self.sliceNumber)])
			#	elif self.status=="preparing":
			#		zmq_socket.send_multipart(["status", self.status, "homing", ""])
				
		return True
	'''

	def on_closing(self, widget, event, data):
		# Get all threads.
		runningThreads = threading.enumerate()
		# End kill threads. Main gui thread is the first...
		for i in range(len(runningThreads)):
			if i != 0:
				runningThreads[-1].join(timeout=10000)	# Timeout in ms.
				print "Slicer thread " + str(i) + " finished."
				del runningThreads[-1]
		# Save settings to file.
		#self.programSettings.saveFile()
		# Terminate the gui.
		gtk.main_quit()
		return False # returning False makes "destroy-event" be signalled to the window
	
	
	def exit(self):
		pass
		# TODO
	
