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

class monkeyprintPiServer:
	def __init__(self, port, debug):
	
		self.port = port
		self.debug = debug
		
		
		# Printer messages.
		self.status = "Idle"
		self.printFlag = False
		
		# Local file path.
		self.localPath = "currentPrint.mkp"


		# Allow background threads.****************************
		# Very important, otherwise threads will be
		# blocked by gui main thread.
		gtk.gdk.threads_init()
		
		
		# Create communication socket.
		self.context = zmq.Context()
		self.socket = self.context.socket(zmq.PAIR)	# Response type socket.
		self.socket.bind("tcp://*:"+port)
		
		
		# Add socket listener to GTK event loop.
		self.zmq_fd = self.socket.getsockopt(zmq.FD)
		gobject.io_add_watch(self.zmq_fd, gobject.IO_IN, self.zmq_callback, self.socket)

		
		# Create file transfer socket.
		self.queueFileTransferIn = Queue.Queue(maxsize=1)
		self.queueFileTransferOut = Queue.Queue(maxsize=1)
		self.fileReceiver = monkeyprintSocketCommunication.fileReceiver(ip="*", port="6000", queueFileTransferIn=self.queueFileTransferIn, queueFileTransferOut=self.queueFileTransferOut)
		self.fileReceiver.start()
		
		
		# Create queues for inter-thread communication.********
		# Queue for setting print progess bar.
		self.queueSlice = Queue.Queue(maxsize=1)
		# Queue for status infos displayed above the status bar.
		self.queueStatus = Queue.Queue()
		# Queue for console messages.
		self.queueConsole = Queue.Queue()
		# Queue list.
		self.queues = [	self.queueSlice,
						self.queueStatus		]
		

		# Create settings dictionary object for machine and program settings.
		self.programSettings = monkeyprintSettings.programSettings()
	
		# Update settings from file.	
		self.programSettings.readFile()
		
		

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
	
	
	def startPrint(self, filename):
		print ("Starting print job from file " + filename + ".")
		
		# Request settings file from PC.
		print "Loading settings file from master."
		self.queueFileTransferIn.put(("get", "./programSettings.txt"))
		# Wait until transmission is complete.
		while not self.queueFileTransferOut.qsize():
			time.sleep(0.1)
		transmissionResult = self.queueFileTransferOut.get()
		if transmissionResult != "success":
			print "Transmission failed. Cancelling."
			return
		
		# Update settings from file.	
		self.programSettings.readFile()
		
		# Set rasperry pi setting.
		self.programSettings['runOnRaspberry'].value = True
		self.programSettings['Debug'].value = True
		
		
		
		# Get the mkp file.
		print "Loading project file from master."
		self.queueFileTransferIn.put(("get", filename))
		# Wait until transmission is complete.
		while not self.queueFileTransferOut.qsize():
			time.sleep(0.1)
		transmissionResult = self.queueFileTransferOut.get()
		if transmissionResult != "success":
			print "Transmission failed. Cancelling."
			return

		print "Preparing print."
		
		self.modelCollection.loadProject(self.localPath)
		print ("Project file: " + str(filename) + " loaded successfully.")
		print "Found the following models:"
		for model in self.modelCollection:
			if model != 'default':
				print ("   " + model)
		
		
		# Start the slicer.
		self.modelCollection.updateSliceStack()
		print ("Starting slicer.")

		# Wait for all slicer threads to finish.
		while(self.modelCollection.slicerRunning()):
			self.modelCollection.checkSlicerThreads()
			time.sleep(.2)
			sys.stdout.write('.')
			sys.stdout.flush()
	
		# Start print process when slicers are done.
		print "\nSlicer done. Starting print process."
		
		
		# Create the projector window.
		# Initialise base class gtk window.********************
		self.projectorDisplay = monkeyprintGuiHelper.projectorDisplay(self.programSettings, self.modelCollection)
		# Set function for window close event.
		self.projectorDisplay.connect("delete-event", self.on_closing, None)
		# Show the window.
		self.projectorDisplay.show()
		
		
		# Register image update
		# Update the progress bar, projector image and 3d view. during prints.
		printProcessUpdateId = gobject.timeout_add(10, self.updateSlicePrint)
		
		
		# Create the print process thread.
		# TODO make queueConsole an optional argument to printProcess.__init__
		self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSlice, self.queueStatus, self.queueConsole)
		
		# Start the print process.
		self.printProcess.start()
		
		
	def updateSlicePrint(self):
		# If slice number queue has slice number...
		if self.queueSlice.qsize():
			sliceNumber = self.queueSlice.get()
			# Set slice view to given slice. If sliceNumber is -1 black is displayed.
			#if self.windowPrint != None:
			#	self.windowPrint.updateImage(sliceNumber)
			self.projectorDisplay.updateImage(sliceNumber)
		# If print info queue has info...
		if self.queueStatus.qsize():
			#self.progressBar.setText(self.queueStatus.get()) 
			message = self.queueStatus.get()
			if message == "destroy":
				print "Print process finished! Idling..."
				self.printFlag = False
				del self.printProcess
				#gtk.main_quit()
				self.projectorDisplay.destroy()
				del self.projectorDisplay
				return False	# Remove funktion from GTK timeout queue.
			else:
				return True	# Keep funktion in GTK timeout queue.
		# Return true, otherwise function won't run again.
		return True	
		
		
		
	
	def zmq_callback(self, fd, condition, zmq_socket):
		while zmq_socket.getsockopt(zmq.EVENTS) & zmq.POLLIN:
			msg = zmq_socket.recv_multipart()
			command, parameter = msg
			if parameter != "":
				print ("Received command \"" + command + "\" with parameter \"" + parameter + "\".")
			else:
				print ("Received command \"" + command + "\".")
				
			
			if command == "print":
				if self.printFlag:
					zmq_socket.send_multipart(["error", "Print running already."])
				else:
					zmq_socket.send_multipart(["status", "Starting print"])
					self.status = "Printing"
					self.startPrint(parameter)
				
				
			elif command == "status":
				zmq_socket.send_multipart(["status", status])

				
		return True


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


	
