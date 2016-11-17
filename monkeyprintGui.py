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


import pygtk
pygtk.require('2.0')
import gtk, gobject
#import gtkGLExtVTKRenderWindowInteractor
import monkeyprintModelViewer
import monkeyprintGuiHelper
import monkeyprintSerial
import monkeyprintPrintProcess
import monkeyprintSocketCommunication
import subprocess # Needed to call avrdude.
import vtk
import threading
import Queue
import time
import signal
import zmq
import os
import shutil



################################################################################
# Define a class for standalone without main GUI. ##############################
################################################################################
# Inherit from projector display window.
class noGui(monkeyprintGuiHelper.projectorDisplay):

	# Override init function. #################################################
	def __init__(self, programSettings, modelCollection):

		# Initialise base class gtk window.********************
		monkeyprintGuiHelper.projectorDisplay.__init__(self, programSettings, modelCollection)
		# Set function for window close event.
		self.connect("delete-event", self.on_closing, None)
		# Show the window.
		self.show()

		# Internalise parameters.******************************
		self.modelCollection = modelCollection
		self.programSettings = programSettings


		# Create queues for inter-thread communication.********
		# Queue for setting print progess bar.
		self.queueSliceOut  = Queue.Queue(maxsize=1)
		self.queueSliceIn = Queue.Queue(maxsize=1)
		# Queue for status infos displayed above the status bar.
		self.queueStatus = Queue.Queue()
		# Queue for console messages.
		self.queueConsole = Queue.Queue()
		# Queue list.
		self.queues = [	self.queueSliceOut,
						self.queueStatus		]

		# Allow background threads.****************************
		# Very important, otherwise threads will be
		# blocked by gui main thread.
		gtk.gdk.threads_init()

		# Add thread listener functions to run every n ms.****
		# Check if the slicer threads have finished.
#		slicerListenerId = gobject.timeout_add(100, self.modelCollection.checkSlicerThreads)
		# Update the progress bar, projector image and 3d view. during prints.
		pollPrintQueuesId = gobject.timeout_add(50, self.pollPrintQueues)


		# Create additional variables.*************************
		# Flag to set during print process.
		self.printFlag = True
		self.programSettings['printOnRaspberry'].value = True

		# Create the print window.
#		self.projectorDisplay = monkeyprintGuiHelper.projectorDisplay(self.programSettings, self.modelCollection)

		# Create the print process thread.
		self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSliceOut, self.queueSliceIn, self.queueStatus, self.queueConsole)

		# Start the print process.
		self.printProcess.start()

		# Start main loop.
		self.main()

	def pollPrintQueues(self):
		# If slice number queue has slice number...
		if self.queueSliceOut.qsize():
			sliceNumber = self.queueSliceOut.get()
			# Set slice view to given slice. If sliceNumber is -1 black is displayed.
			#if self.projectorDisplay != None:
			#	self.projectorDisplay.updateImage(sliceNumber)
			self.updateImage(sliceNumber)
			# Set slice in queue to true as a signal to print process thread that it can start waiting.
			self.queueSliceIn.put(True)
		# If print info queue has info...
		if self.queueStatus.qsize():
			#self.progressBar.setText(self.queueStatus.get())
			message = self.queueStatus.get()
			if message == "destroy":
				self.printFlag = False
				del self.printProcess
				gtk.main_quit()
				self.destroy()
				del self
				return False
			else:
				return True
		# Return true, otherwise function won't run again.
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
		self.programSettings.saveFile()
		# Remove temp directory.on_closing(
		shutil.rmtree(self.programSettings['tmpDir'].value, ignore_errors=True)
		# Terminate the gui.
		gtk.main_quit()
		return False # returning False makes "destroy-event" be signalled to the window

	# Gui main function. ######################################################
	def main(self):
		# All PyGTK applications must have a gtk.main(). Control ends here
		# and waits for an event to occur (like a key press or mouse event).
		gtk.main()






################################################################################
# Define a class for the main GUI. #############################################
################################################################################
class gui(gtk.Window):

	# Override init function. #################################################
	def __init__(self, modelCollection, programSettings, console=None, filename=None, *args, **kwargs):


		# ********************************************************************
		# Initialise base class gtk window.***********************************
		# ********************************************************************
		gtk.Window.__init__(self, *args, **kwargs)
		# Set function for window close event.
		self.connect("delete-event", self.on_closing, None)
		# Set window title.
		self.set_title("Monkeyprint")
		# Set maximized.
		self.maximize()
		# Show the window.
		self.show()




		# ********************************************************************
		# Declare variables. *************************************************
		# ********************************************************************
		# Internalise parameters.
		self.modelCollection = modelCollection
		self.programSettings = programSettings
		self.console = console

		# Create queues for inter-thread communication.
		# Queue for setting print progess bar.
		self.queueSliceOut  = Queue.Queue(maxsize=1)
		self.queueSliceIn = Queue.Queue(maxsize=1)
		# Queues for controlling the file transmission thread.
		self.queueFileTransferIn = Queue.Queue(maxsize=1)
		self.queueFileTransferOut = Queue.Queue(maxsize=1)
		# Queue for print process commands.

		# Queue for status infos displayed above the status bar.
		self.queueStatus = Queue.Queue()
		# Queue for commands sent to print process.
		self.queueCommands = Queue.Queue(maxsize=1)
		# Queue for console messages.
		self.queueConsole = Queue.Queue()

		# Is this running from Raspberry Pi or from PC?
		self.runningOnRasPi = False
		# TODO: Use this flag to combine this class and server class.

		# Flag to set during print process.
		self.printFlag = False

		# Get current working directory and set paths.
		self.cwd = os.getcwd()
		self.programSettings['localMkpPath'].value = self.cwd + "/currentPrint.mkp"



		# ********************************************************************
		# Create print process. **********************************************
		# ********************************************************************
#		self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSliceOut, self.queueSliceIn, self.queueStatus, self.queueConsole)
#DO THIS LATER ON PRINT BUTTON PRESS!

		# TODO: make specific for Pi or PC
		# ********************************************************************
		# Create communication socket to Raspberry Pi. ***********************
		# ********************************************************************

		# Create the socket and connect.

		if self.runningOnRasPi:
			self.socket = monkeyprintSocketCommunication.communicationSocket(port=self.programSettings['networkPortRaspi'].value, ip=None, queueCommands=self.queueCommands)
		elif self.programSettings['printOnRaspberry'].value:
			self.socket = monkeyprintSocketCommunication.communicationSocket(port=self.programSettings['networkPortRaspi'].value, ip=self.programSettings['ipAddressRaspi'].value, queueStatus=self.queueStatus)
		# Add socket listener and connection timeout methods to GTK event loop.
		if self.runningOnRasPi or self.programSettings['printOnRaspberry'].value:
			gobject.io_add_watch(self.socket.fileDescriptor, gobject.IO_IN, self.socket.callbackIOActivity, self.socket.socket)
		if not self.runningOnRasPi and self.programSettings['printOnRaspberry'].value:
			# Connection poll.
			gobject.timeout_add(500, self.socket.pollRasPiConnection)
			# Connection timeout counter.
			gobject.timeout_add(1000, self.socket.countdownRasPiConnection)



		# ********************************************************************
		# Allow background threads. ******************************************
		# ********************************************************************
		# Very important, otherwise threads will be
		# blocked by gui main thread.
		gtk.gdk.threads_init()




		# ********************************************************************
		# Add thread listener functions to run every n ms.********************
		# ********************************************************************
		# Check if the slicer threads have finished.
		slicerListenerId = gobject.timeout_add(100, self.modelCollection.checkSlicerThreads)
		# Check if slice combiner has finished.
		sliceCombinerListenerId = gobject.timeout_add(100, self.modelCollection.checkSliceCombinerThread)
		# Update the progress bar, projector image and 3d view. during prints.
		pollPrintQueuesId = gobject.timeout_add(50, self.pollPrintQueues)
		# Request status info from raspberry pi.
	#	pollRasPiConnectionId = gobject.timeout_add(500, self.pollRasPiConnection)
		# Request status info from slicer.
		pollSlicerStatusId = gobject.timeout_add(100, self.pollSlicerStatus)
		# TODO: combine this with slicerListener.




		# ********************************************************************
		# Create file transmission thread. ***********************************
		# ********************************************************************

		# Only if this is not running on Raspberry Pi.
		if not self.runningOnRasPi and self.programSettings['printOnRaspberry'].value:
			ipFileClient = self.programSettings['ipAddressRaspi'].value
			portFileClient = self.programSettings['fileTransmissionPortRaspi'].value
			self.threadFileTransmission = monkeyprintSocketCommunication.fileSender(ip=ipFileClient, port=portFileClient, queueStatusIn=self.queueFileTransferIn, queueStatusOut=self.queueFileTransferOut)
			self.threadFileTransmission.start()




		# ********************************************************************
		# Create the main GUI. ***********************************************
		# ********************************************************************
		# Create main box inside of window.
		self.boxMain = gtk.VBox()
		self.add(self.boxMain)
		self.boxMain.show()

		# Create menu bar and pack inside main box at top.
		self.menuBar = self.createMenuBar()#menuBar(self.programSettings, self.on_closing)
		self.boxMain.pack_start(self.menuBar, expand=False, fill=False)
		self.menuBar.show()

		# Create work area box and pack below menu bar.
		self.boxWork = gtk.HBox()
		self.boxMain.pack_start(self.boxWork)
		self.boxWork.show()

		# Create render box and pack inside work area box.
		self.renderView = monkeyprintModelViewer.renderView(self.programSettings)
		self.renderView.show()
		self.boxWork.pack_start(self.renderView)#, expand=True, fill= True)

		# Create settings box and pack right of render box.
		self.boxSettings = self.createSettingsBox()
		self.boxSettings.show()
		self.boxWork.pack_start(self.boxSettings, expand=False, fill=False, padding = 5)

		# Handle sigterm to shut down gracefully.
		signal.signal(signal.SIGTERM, self.on_closing)



		# Prepare...
		# Print window.
		self.projectorDisplay = None

		# Set print progress values.
		self.queueSliceOut.put(0)
		self.queueStatus.put("idle:slice:0")


		# Add print job load function to be called once on startup.
		if filename != None:
			printjobLoadFunctionId = gobject.idle_add(self.loadPrintjob, filename)





	# *************************************************************************
	# Gui main function. ******************************************************
	# *************************************************************************
	def main(self):
		# All PyGTK applications must have a gtk.main(). Control ends here
		# and waits for an event to occur (like a key press or mouse event).
		gtk.main()




	# *************************************************************************
	# Override the close function. ********************************************
	# *************************************************************************
	def on_closing(self, widget, event, data):
		# Check if a print is running.
		if self.printFlag:
			self.console.addLine('Monkeyprint cannot be closed')
			self.console.addLine('during a print. Wait for')
			self.console.addLine('the print to finish or cancel')
			self.console.addLine('the print if you want to close.')
			return True # returning True avoids it to signal "destroy-event"
		else:
			# Create a dialog window with yes/no buttons.
			dialog = gtk.MessageDialog(self,
				gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
				gtk.MESSAGE_QUESTION,
				gtk.BUTTONS_YES_NO,
				"Do you really want to quit?")
     	     # Set the title.
			dialog.set_title("Quit Monkeyprint?")

			# Check the result and respond accordingly.
			response = dialog.run()
			dialog.destroy()
			if response == gtk.RESPONSE_YES:
				# Get all threads.
				runningThreads = threading.enumerate()
				# End kill threads. Main gui thread is the first...
				for i in range(len(runningThreads)):
					if i != 0:
						runningThreads[-1].join(timeout=1000)	# Timeout in ms.
						print "Background thread " + str(i) + " finished."
						del runningThreads[-1]
				# Clean up files.
				if os.path.isfile(self.programSettings['localMkpPath'].value):
					os.remove(self.programSettings['localMkpPath'].value)
				# Remove temp directory.
				shutil.rmtree(self.programSettings['tmpDir'].value, ignore_errors=True)
				# Save settings to file.
				self.programSettings.saveFile()
				# Terminate the gui.
				gtk.main_quit()
				return False # returning False makes "destroy-event" be signalled to the window.
			else:
				return True # returning True avoids it to signal "destroy-event"




	# *************************************************************************
	# Function that checks if one of the slicer threads is running. ***********
	# *************************************************************************
	# This runs every 100 ms as a gobject timeout function.
	def pollSlicerStatus(self):
		if self.modelCollection != None:
			self.buttonSaveSlices.set_sensitive(not self.modelCollection.slicerRunning())
		return True




	# *************************************************************************
	# Function that updates all relevant GUI elements during prints. **********
	# *************************************************************************
	# This runs every 100 ms as a gobject timeout function.
	# Updates 3d view and projector view. Also forwards status info.
	def pollPrintQueues(self):
		# Check the queues...
		# If slice number queue has slice number...
		if self.queueSliceOut.qsize():
			# ... get it from the queue.
			sliceNumber = self.queueSliceOut.get()
			# If it's an actual slice number...
			if sliceNumber >=0:
				# Set 3d view to given slice.
				self.modelCollection.updateAllSlices3d(sliceNumber)
				self.renderView.render()
			# Set slice view to given slice. If sliceNumber is -1 black is displayed.
			# Only if not printing from raspberry. In this case the projector display will not exist.
			if self.projectorDisplay != None:
				self.projectorDisplay.updateImage(sliceNumber)
			# Update slice preview in the gui.
			self.sliceView.updateImage(sliceNumber)
			# Signal to print process that slice image is set and exposure time can begin.
			if self.queueSliceIn.empty():
				self.queueSliceIn.put(True)

		# If status queue has info...
		if self.queueStatus.qsize():
			# ... get the status.
			message = self.queueStatus.get()
			#print message
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
					self.socket.sendMulti("status", message)

				# If not, update the GUI.
				else:
					self.processStatusMessage(message)
	#				print message

		# Poll the command queue.
		# Only do this when running on Raspberry Pi.
		# If command queue has info...
		if self.queueCommands.qsize():
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
		#if self.runningOnRasPi:
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
			elif command == "stop":
				print "command: stop"
				if self.printFlag:
					self.printProcessStop()
					#self.printProcess.stop()
			elif command == "pause":
				if self.printFlag:
					self.printProcess.pause()


	# *************************************************************************
	# Function to process the output of statusQueue and update the GUI. *******
	# *************************************************************************
	def processStatusMessage(self, message):
		# Split the string.
		status, param, value = message.split(":")
		# Check the status and retreive other data.
		printFlag = True
		if status == "slicing":
			if param == "nSlices":
				# Set number of slices for status bar.
				self.progressBar.setLimit(int(value))
			elif param == "slice":
				# Set current slice in status bar.
				currentSlice = int(value)
				# TODO get current slice, this will work once slicer thread returns single slices.
				if not self.queueSliceOut.qsize():
					self.queueSliceOut.put(int(currentSlice))
			self.progressBar.setText("Slicing.")
		elif status == "preparing":
			if param == "nSlices":
				self.progressBar.setLimit(int(value))
			if param == "homing":
				self.progressBar.setText("Homing build platform.")
			if param == "bubbles":
				self.progressBar.setText("Removing bubbles.")
		elif status == "printing":
			if param == "nSlices":
				# Set number of slices for status bar.
				self.progressBar.setLimit(int(value))
			if param == "slice":
				# Set current slice in status bar.
				self.progressBar.updateValue(int(value))
				self.progressBar.setText("Printing slice " + value + ".")
				if not self.queueSliceOut.qsize():
					self.queueSliceOut.put(int(value))
		elif status == "stopping":
			self.progressBar.setText("Stopping print.")
		elif status == "paused":
			self.progressBar.setText("Print paused.")
		elif status == "stopped":
			if param == "slice":
				self.progressBar.setText("Print stopped after " + value + " slices.")
			else:
				self.progressBar.setText("Print stopped.")
			# Reset stop button to insensitive.
			self.buttonPrintStart.set_sensitive(True)
			self.buttonPrintStop.set_sensitive(False)
		elif status == "idle":
			if param == "slice":
				self.progressBar.updateValue(int(value))
			printFlag = False
			self.progressBar.setText("Idle.")

		self.printFlag = printFlag








	# Create menu. ############################################################
	def createMenuBar(self):

		# Create the menu bar.
		menuBar = gtk.MenuBar()

		# Create file menu.
		# That's the container for the file menu items that
		# will pop up upon ckicking the file menu. Therefore, it
		# does not have to be shown here.
		fileMenu = gtk.Menu()
		# Create file menu items.
		self.menuItemOpen = gtk.MenuItem(label="Open project")
		self.menuItemSave = gtk.MenuItem(label="Save project")
		self.menuItemClose = gtk.MenuItem(label="Close project")
		self.menuItemQuit = gtk.MenuItem(label="Quit")
		# Set initial sensitivities.
		self.menuItemSave.set_sensitive(False)
		self.menuItemClose.set_sensitive(False)
		# Add to menu.
		fileMenu.append(self.menuItemOpen)
		fileMenu.append(self.menuItemSave)
		fileMenu.append(self.menuItemClose)
		fileMenu.append(self.menuItemQuit)
		# Connect menu items to callback signals.
		self.menuItemOpen.connect("activate", self.callbackOpen)
		self.menuItemSave.connect("activate", self.callbackSaveProject)
		self.menuItemClose.connect("activate", self.callbackClose)
		self.menuItemQuit.connect("activate", self.callbackQuit)
		# Show the items.
		self.menuItemOpen.show()
		self.menuItemSave.show()
		self.menuItemClose.show()
		self.menuItemQuit.show()


		# Create file menu (does not have to be shown).
		optionsMenu = gtk.Menu()
		# Create file menu items.
		self.menuItemSettings = gtk.MenuItem(label="Settings")
		self.menuItemFlash = gtk.MenuItem(label="Flash firmware")
		self.menuItemManualControl = gtk.MenuItem(label="Manual control")
		# Connect callbacks.
		self.menuItemSettings.connect("activate", self.callbackSettings)
		self.menuItemFlash.connect("activate", self.callbackFlash)
		self.menuItemManualControl.connect("activate", self.callbackManualControl)
		# Add to menu.
		optionsMenu.append(self.menuItemSettings)
		optionsMenu.append(self.menuItemFlash)
		optionsMenu.append(self.menuItemManualControl)
		# Show the items.
		self.menuItemSettings.show()
		self.menuItemFlash.show()
		self.menuItemManualControl.show()


		# Help menu.
		helpMenu = gtk.Menu()
		# Create file menu items.
		self.menuItemDocu = gtk.MenuItem(label="Documentation")
		self.menuItemAbout = gtk.MenuItem(label="About")
		self.menuItemDocu.set_sensitive(False)
		self.menuItemAbout.set_sensitive(False)
		# Connect callbacks.
		self.menuItemDocu.connect("activate", self.callbackSettings)
		self.menuItemAbout.connect("activate", self.callbackSettings)
		# Add to menu.
		helpMenu.append(self.menuItemDocu)
		helpMenu.append(self.menuItemAbout)
		# Show the items.
		self.menuItemDocu.show()
		self.menuItemAbout.show()


		# Create menu bar items.
		# File menu.
		menuItemFile = gtk.MenuItem(label="File")
		menuItemFile.set_submenu(fileMenu)
		menuBar.append(menuItemFile)
		menuItemFile.show()
		# Options menu.
		menuItemOptions = gtk.MenuItem(label="Options")
		menuItemOptions.set_submenu(optionsMenu)
		menuBar.append(menuItemOptions)
		menuItemOptions.show()
		# Help menu.
		menuItemHelp = gtk.MenuItem(label="Help")
		menuItemHelp.set_submenu(helpMenu)
		menuBar.append(menuItemHelp)
		menuItemHelp.show()


		# Return the menu.
		return menuBar





	def loadPrintjob(self, filename):
		# Check if file is an mkp. If not...
		if filename.lower()[-3:] != "mkp":
			# ... display message and nothing more.
			self.console.addLine("File \"" + filename + "\" is not a monkeyprint project file.")
		else:
			# Console message.
			self.console.addLine("Loading project \"" + filename.split('/')[-1] + "\".")
			# Save path for next use.
			self.programSettings['currentFolder'].value = filename[:-len(filename.split('/')[-1])]
			# Now that we have the new selection, we can delete the previously selected model.
			# First, remove the actors from the render view.
			self.renderView.removeActors(self.modelCollection.getAllActors())
			# Then, load the project into the model collection:
			self.modelCollection.loadProject(filename)
			# Update the list view.
			self.modelListView.update()
			# Set menu item sensitivities.
			self.menuItemSave.set_sensitive(True)
			self.menuItemClose.set_sensitive(True)

			# Hide the previous models bounding box.
	#		self.modelCollection.getCurrentModel().hideBox()
			# Load the model into the model collection.
	#		self.modelCollection.add(filename, filepath)
			# Add the filename to the list and set selected.
	#		self.add(filename, filename, filepath)
			# Activate the remove button which was deactivated when there was no model.
	#		self.buttonRemove.set_sensitive(True)

			# Add actor to render view.
			self.renderView.addActors(self.modelCollection.getAllActors())

			# Update 3d view.
			self.renderView.render()

			# Update menu to set sensitivities.
			self.updateMenu()
			# Update model list view to set sensitivities.
			self.modelListView.setSensitive(remove=self.modelCollection.modelsLoaded())
			# Update notebook to set sensitivities.
			self.updateAllEntries(state=1)
			self.notebook.set_current_page(0)


		# Return false so this method will not be called again when
		# called from gui idle functions stack.
		return False





	def callbackOpen(self, event):

		self.console.addLine("Opening print job...")

		# Open file chooser dialog."
		filepath = ""
		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Load project", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_modal(True)
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.programSettings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Monkeyprint project files")
		fileFilter.add_pattern("*.mkp")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Check the response.
		# If OK was pressed...
		if response == gtk.RESPONSE_OK:
			filename = dialog.get_filename()
			self.loadPrintjob(filename)
			'''
			# Check if file is an mkp. If not...
			if filename.lower()[-3:] != "mkp":
				# ... display message and nothing more.
				self.console.addLine("File \"" + filename + "\" is not a monkeyprint project file.")
			else:
				self.loadPrintjob(filename)

				# Console message.
				self.console.addLine("Loading project \"" + filename.split('/')[-1] + "\".")
				# Save path for next use.
				self.programSettings['currentFolder'].value = filename[:-len(filename.split('/')[-1])]
				# Now that we have the new selection, we can delete the previously selected model.
				# First, remove the actors from the render view.
				self.renderView.removeActors(self.modelCollection.getAllActors())
				# Then, load the project into the model collection:
				self.modelCollection.loadProject(filename)
				# Update the list view.
				self.modelListView.update()
				# Set menu item sensitivities.
				self.menuItemSave.set_sensitive(True)
				self.menuItemClose.set_sensitive(True)

				# Hide the previous models bounding box.
		#		self.modelCollection.getCurrentModel().hideBox()
				# Load the model into the model collection.
		#		self.modelCollection.add(filename, filepath)
				# Add the filename to the list and set selected.
		#		self.add(filename, filename, filepath)
				# Activate the remove button which was deactivated when there was no model.
		#		self.buttonRemove.set_sensitive(True)

				# Add actor to render view.
				self.renderView.addActors(self.modelCollection.getAllActors())

				# Update 3d view.
				self.renderView.render()

				# Update menu to set sensitivities.
				self.updateMenu()
				# Update model list view to set sensitivities.
				self.modelListView.setSensitive(remove=self.modelCollection.modelsLoaded())
				# Update notebook to set sensitivities.
				self.updateAllEntries(state=1)
				self.notebook.set_current_page(0)
			'''
			# Close dialog.
			dialog.destroy()

			# Update notebook to set sensitivities.
			self.updateAllEntries(state=2)

		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()

	def callbackSaveProject(self, event):
		# Open file saver dialog.
		# Open file chooser dialog."
		filepath = ""
		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Save project", None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_modal(True)
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.programSettings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Monkeyprint project files")
		fileFilter.add_pattern("*.mkp")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Process response. If OK...
		if response == gtk.RESPONSE_OK:
			# ... get file name.
			path = dialog.get_filename()
			#... add *.mkp file extension if necessary.
			if len(path) < 4 or path[-4:] != ".mkp":
				path += ".mkp"
			# Console message.
			self.console.addLine("Saving project to \"" + path.split('/')[-1] + "\".")
			# Save path without project name for next use.
			self.programSettings['currentFolder'].value = path[:-len(path.split('/')[-1])]
			# Save the model collection to the given location.
			self.modelCollection.saveProject(path)
			# Save the path for later.

			dialog.destroy()
		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()


	def callbackClose(self, event):
		# Create a dialog window with yes/no buttons.
		dialog = gtk.MessageDialog(self,
			gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
			gtk.MESSAGE_QUESTION,
			gtk.BUTTONS_YES_NO,
			"Do you really want to close the current project?")
          # Set the title.
		dialog.set_title("Close project?")
		# Check the result and respond accordingly.
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			self.console.addLine("Closing print job...")
			# Remove all actors from view.
			self.renderView.removeActors(self.modelCollection.getAllActors())
			# Remove all models.
			self.modelCollection.removeAll()
			# Set menu item sensitivities.
			# Update menu to set sensitivities.
			self.updateMenu()
			# Update model list view to set sensitivities.
			self.modelListView.setSensitive(remove=self.modelCollection.modelsLoaded())
			# Update notebook to set sensitivities.
			self.updateAllEntries(state=0)
			# Render.
			self.renderView.render()
#		else:
#			return True # returning True avoids it to signal "destroy-event"



	def callbackQuit(self, event):
		self.on_closing(None, None, None)

	def callbackSettings(self, event):
		dialogSettings(self.programSettings, parentWindow=self)

	def callbackFlash(self, event):
		dialogFirmware(self.programSettings, parent=self)

	def callbackManualControl(self, event):
		dialogManualControl(self.programSettings, parent=self)

	def callbackDocu(self, event):
		pass

	def callbackAbout(self, event):
		pass


	# Create the notebook.#####################################################
	def createSettingsBox(self):

		boxSettings = gtk.VBox()


		# Create model management editor. ************************************
		self.frameModels = gtk.Frame(label="Models")
		boxSettings.pack_start(self.frameModels, padding = 5)
		self.frameModels.show()
		# Create model list view using the model list.
		self.modelListView = modelListView(self.programSettings, self.modelCollection, self.renderView, self.updateAllEntries, self.console)
		self.frameModels.add(self.modelListView)
		self.modelListView.show()


		# Create notebook. ***************************************************
		self.notebook = monkeyprintGuiHelper.notebook()
		boxSettings.pack_start(self.notebook)
		self.notebook.show()

		# Create model page, append to notebook and pass custom function.
		self.createModelTab()
		self.notebook.append_page(self.modelTab, gtk.Label('Models'))
		self.notebook.set_custom_function(0, self.tabSwitchModelUpdate)

		# Create supports page, append to notebook and pass custom function.
		self.createSupportsTab()
		self.notebook.append_page(self.supportsTab, gtk.Label('Supports'))
		self.notebook.set_custom_function(1, self.tabSwitchSupportsUpdate)

		# Add slicing page, append to notebook and pass custom function.
		self.createSlicingTab()
		self.notebook.append_page(self.slicingTab, gtk.Label('Slicing'))
		self.notebook.set_custom_function(2, self.tabSwitchSlicesUpdate)

		# Add print page.
		self.createPrintTab()
		self.notebook.append_page(self.printTab, gtk.Label('Print'))
		self.notebook.set_custom_function(3, self.tabSwitchPrintUpdate)


		# Set gui state. This controls which tabs are clickable.**************
		# 0: Model modifications active.
		# 1: Model modifications, supports and slicing active.
		# 2: All active.
		# Use setGuiState function to set the state. Do not set manually.
		self.setGuiState(0)


		# Create console for debug output.************************************
		# Create frame.
		self.frameConsole = gtk.Frame(label="Output log")
		boxSettings.pack_start(self.frameConsole, padding=5)
		self.frameConsole.show()
		# Custom scrolled window.
		self.consoleView = monkeyprintGuiHelper.consoleView(self.console)
		self.frameConsole.add(self.consoleView)


		# Return the box. ****************************************************
		return boxSettings





	# Create notebook pages. ##################################################
	# Model page.
	def createModelTab(self):
		# Create tab box.
		self.modelTab = gtk.VBox()
		self.modelTab.show()

		# Create model modification frame.
		self.frameModifications = gtk.Frame(label="Model modifications")
		self.modelTab.pack_start(self.frameModifications, expand=True, fill=True, padding=5)
		self.frameModifications.show()
		self.boxModelModifications = gtk.VBox()
		self.frameModifications.add(self.boxModelModifications)
		self.boxModelModifications.show()
		self.entryScaling = monkeyprintGuiHelper.entry('scaling', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryScaling, expand=False, fill=False)
		self.entryRotationX = monkeyprintGuiHelper.entry('rotationX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationX, expand=False, fill=False)
		self.entryRotationY = monkeyprintGuiHelper.entry('rotationY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationY, expand=False, fill=False)
		self.entryRotationZ = monkeyprintGuiHelper.entry('rotationZ', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationZ, expand=False, fill=False)
		self.entryPositionX = monkeyprintGuiHelper.entry('positionX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryPositionX, expand=False, fill=False)
		self.entryPositionY = monkeyprintGuiHelper.entry('positionY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryPositionY, expand=False, fill=False)
		self.entryBottomClearance = monkeyprintGuiHelper.entry('bottomClearance', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryBottomClearance, expand=False, fill=False)

	# Supports page.
	def createSupportsTab(self):
		# Create tab box.
		self.supportsTab = gtk.VBox()
		self.supportsTab.show()

		# Create support pattern frame.
		self.frameSupportPattern = gtk.Frame(label="Support pattern")
		self.supportsTab.pack_start(self.frameSupportPattern, expand=False, fill=False, padding=5)
		self.frameSupportPattern.show()
		self.boxSupportPattern = gtk.VBox()
		self.frameSupportPattern.add(self.boxSupportPattern)
		self.boxSupportPattern.show()
		self.entryOverhangAngle = monkeyprintGuiHelper.entry('overhangAngle', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entryOverhangAngle, expand=False, fill=False)
		self.entrySupportSpacingX = monkeyprintGuiHelper.entry('spacingX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportSpacingX, expand=False, fill=False)
		self.entrySupportSpacingY = monkeyprintGuiHelper.entry('spacingY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportSpacingY, expand=False, fill=False)
		self.entrySupportMaxHeight = monkeyprintGuiHelper.entry('maximumHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportMaxHeight, expand=False, fill=False)

		# Create support geometry frame.
		self.frameSupportGeometry = gtk.Frame(label="Support geometry")
		self.supportsTab.pack_start(self.frameSupportGeometry, expand=False, fill=False, padding=5)
		self.frameSupportGeometry.show()
		self.boxSupportGeometry = gtk.VBox()
		self.frameSupportGeometry.add(self.boxSupportGeometry)
		self.boxSupportGeometry.show()
		self.entrySupportBaseDiameter = monkeyprintGuiHelper.entry('baseDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportBaseDiameter, expand=False, fill=False)
		self.entrySupportTipDiameter = monkeyprintGuiHelper.entry('tipDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportTipDiameter, expand=False, fill=False)
		self.entrySupportTipHeight = monkeyprintGuiHelper.entry('coneHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportTipHeight, expand=False, fill=False)

		# Create bottom plate frame.
		self.frameBottomPlate = gtk.Frame(label="Bottom plate")
		self.supportsTab.pack_start(self.frameBottomPlate, expand=False, fill=False, padding=5)
		self.frameBottomPlate.show()
		self.boxBottomPlate = gtk.VBox()
		self.frameBottomPlate.add(self.boxBottomPlate)
		self.boxBottomPlate.show()
		self.entrySupportBottomPlateThickness = monkeyprintGuiHelper.entry('bottomPlateThickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxBottomPlate.pack_start(self.entrySupportBottomPlateThickness, expand=False, fill=False)

	# Slicing page.
	def createSlicingTab(self):
		# Create tab box.
		self.slicingTab = gtk.VBox()
		self.slicingTab.show()

		# Create slicing parameters frame.
		self.frameSlicing = gtk.Frame(label="Slicing parameters")
		self.slicingTab.pack_start(self.frameSlicing, padding = 5)
		self.frameSlicing.show()
		self.boxSlicingParameters = gtk.VBox()
		self.frameSlicing.add(self.boxSlicingParameters)
		self.boxSlicingParameters.show()
		# layerHeight entry.
		self.entryLayerHeight = monkeyprintGuiHelper.entry('layerHeight', settings=self.programSettings, customFunctions=[self.updateAllModels, self.updateSlider, self.renderView.render, self.updateAllEntries])
		self.boxSlicingParameters.pack_start(self.entryLayerHeight, expand=False, fill=False)

		# Create hollow and fill frame.
		self.frameFill = gtk.Frame(label="Fill parameters")
		self.slicingTab.pack_start(self.frameFill, padding = 5)
		self.frameFill.show()
		self.boxFill = gtk.VBox()
		self.frameFill.add(self.boxFill)
		self.boxFill.show()
		self.boxFillCheckbuttons = gtk.HBox()
		self.boxFill.pack_start(self.boxFillCheckbuttons)
		self.boxFillCheckbuttons.show()
		# Checkbox for hollow prints.
		self.checkboxHollow = monkeyprintGuiHelper.toggleButton(string='printHollow', settings=None, modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel])#gtk.CheckButton(label="Print hollow?")
		self.boxFillCheckbuttons.pack_start(self.checkboxHollow, expand=True, fill=True)
		# Checkbox for fill structures.
		self.checkboxFill = monkeyprintGuiHelper.toggleButton(string='fill', settings=None, modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel])#gtk.CheckButton(label="Print hollow?")
		self.boxFillCheckbuttons.pack_start(self.checkboxFill, expand=True, fill=True)
		# Entries.
		self.entryShellThickness = monkeyprintGuiHelper.entry('fillShellWallThickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryShellThickness, expand=True, fill=True)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('fillSpacing', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryFillSpacing, expand=True, fill=True)
		self.entryFillThickness = monkeyprintGuiHelper.entry('fillPatternWallThickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryFillThickness, expand=True, fill=True)

		# Create preview frame.
		self.framePreview = gtk.Frame(label="Slice preview")
		self.slicingTab.pack_start(self.framePreview, padding = 5)
		self.framePreview.show()
		self.boxPreview = gtk.HBox()
		self.framePreview.add(self.boxPreview)
		self.boxPreview.show()
		self.sliceSlider = monkeyprintGuiHelper.imageSlider(modelCollection=self.modelCollection, programSettings=self.programSettings, width = 200, console=self.console, customFunctions=[self.modelCollection.updateAllSlices3d, self.renderView.render])
		self.boxPreview.pack_start(self.sliceSlider, expand=True, fill=True, padding=5)
		self.sliceSlider.show()
		# Register slice image update function to GUI main loop.
	#	listenerSliceSlider = gobject.timeout_add(100, self.sliceSlider.updateImage)

		# Create save image stack frame.
		self.frameSaveSlices = gtk.Frame("Save slice images")
		self.slicingTab.pack_start(self.frameSaveSlices, expand=True, fill=True, padding=5)
		self.frameSaveSlices.show()
		self.boxSaveSlices = gtk.HBox()
		self.frameSaveSlices.add(self.boxSaveSlices)
		self.boxSaveSlices.show()
		self.buttonSaveSlices = gtk.Button("Save")
		self.buttonSaveSlices.set_sensitive(False)
		self.buttonSaveSlices.connect('clicked', self.callbackSaveSlices)
		self.boxSaveSlices.pack_start(self.buttonSaveSlices, expand=True, fill=True, padding=5)
		self.buttonSaveSlices.show()

	# Print page.
	def createPrintTab(self):
		# Create tab box.
		self.printTab = gtk.VBox()
		self.printTab.show()

		# Create print parameters frame.
		self.framePrint = gtk.Frame(label="Print parameters")
		self.printTab.pack_start(self.framePrint, expand=False, fill=False, padding = 5)
		self.framePrint.show()
		self.boxPrintParameters = gtk.VBox()
		self.framePrint.add(self.boxPrintParameters)
		self.boxPrintParameters.show()

		# Create entries.
		self.entryExposureBase = monkeyprintGuiHelper.entry('exposureTimeBase', settings=self.programSettings)
		self.boxPrintParameters.pack_start(self.entryExposureBase, expand=True, fill=True)
		self.entryExposure = monkeyprintGuiHelper.entry('exposureTime', settings=self.programSettings)
		self.boxPrintParameters.pack_start(self.entryExposure, expand=True, fill=True)
	#	self.entrySettleTime = monkeyprintGuiHelper.entry('Resin settle time', settings=self.programSettings)
	#	self.boxPrintParameters.pack_start(self.entrySettleTime, expand=True, fill=True)

		# Create model volume frame.
		self.frameResinVolume = gtk.Frame(label="Resin volume")
		self.printTab.pack_start(self.frameResinVolume, expand=False, fill=False, padding = 5)
		self.frameResinVolume.show()
		self.boxResinVolume = gtk.HBox()
		self.frameResinVolume.add(self.boxResinVolume)
		self.boxResinVolume.show()
		self.boxResinVolumeV = gtk.VBox()
		self.boxResinVolume.pack_start(self.boxResinVolumeV, expand=False, fill=False, padding=5)
		self.boxResinVolumeV.show()

		# Resin volume label.
		self.resinVolumeLabel = gtk.Label("Volume: ")
		self.boxResinVolumeV.pack_start(self.resinVolumeLabel, expand=False, fill=False, padding=5)
		self.resinVolumeLabel.show()

		# Create camera trigger frame.
		self.frameCameraTrigger = gtk.Frame(label="Camera trigger")
		self.printTab.pack_start(self.frameCameraTrigger, expand=False, fill=False, padding = 5)
		self.frameCameraTrigger.show()
		self.boxCameraTrigger = gtk.HBox()
		self.frameCameraTrigger.add(self.boxCameraTrigger)
		self.boxCameraTrigger.show()

		# Camera trigger checkbuttons.
#TODO		self.checkButtonCameraTrigger1 = monkeyprintGuiHelper.toggleButton(string="During exposure",)
		self.labelCamTrigger1 = gtk.Label("During exposure")
		self.boxCameraTrigger.pack_start(self.labelCamTrigger1, expand=False, fill=False, padding=5)
		self.labelCamTrigger1.show()
		self.checkboxCameraTrigger1 = gtk.CheckButton()
		self.boxCameraTrigger.pack_start(self.checkboxCameraTrigger1, expand=False, fill=False, padding=5)
		self.checkboxCameraTrigger1.set_active(self.programSettings['camTriggerWithExposure'].value)
		self.checkboxCameraTrigger1.connect("toggled", self.callbackCheckButtonTrigger1)
		self.checkboxCameraTrigger1.show()
		self.labelCamTrigger2 = gtk.Label("After exposure")
		self.boxCameraTrigger.pack_start(self.labelCamTrigger2, expand=False, fill=False, padding=5)
		self.labelCamTrigger2.show()
		self.checkboxCameraTrigger2 = gtk.CheckButton()
		self.boxCameraTrigger.pack_start(self.checkboxCameraTrigger2, expand=False, fill=False, padding=5)
		self.checkboxCameraTrigger2.set_active(self.programSettings['camTriggerAfterExposure'].value)
		self.checkboxCameraTrigger2.connect("toggled", self.callbackCheckButtonTrigger2)
		self.checkboxCameraTrigger2.show()

		# Create print control frame.
		self.framePrintControl = gtk.Frame(label="Print control")
		self.printTab.pack_start(self.framePrintControl, expand=False, fill=False, padding = 5)
		self.framePrintControl.show()
		self.boxPrintControl = gtk.HBox()
		self.framePrintControl.add(self.boxPrintControl)
		self.boxPrintControl.show()

		# Create print control buttons.
		self.boxPrintButtons = gtk.HBox()
		self.boxPrintControl.pack_start(self.boxPrintButtons, expand=False, fill=False)
		self.boxPrintButtons.show()
		self.buttonPrintStart = gtk.Button('Print')
		self.boxPrintButtons.pack_start(self.buttonPrintStart, expand=False, fill=False)
		self.buttonPrintStart.connect('clicked', self.callbackStartPrintProcess)
		self.buttonPrintStart.show()
		self.buttonPrintStop = gtk.Button('Stop')
		self.boxPrintButtons.pack_start(self.buttonPrintStop, expand=False, fill=False)
		self.buttonPrintStop.set_sensitive(False)
		self.buttonPrintStop.show()
		self.buttonPrintStop.connect('clicked', self.callbackStopPrintProcess)

		# Create progress bar.
		self.progressBar = monkeyprintGuiHelper.printProgressBar()
		self.boxPrintControl.pack_start(self.progressBar, expand=True, fill=True)
		self.progressBar.show()

		# Create preview frame.
		self.framePreviewPrint = gtk.Frame(label="Slice preview")
		self.printTab.pack_start(self.framePreviewPrint, padding = 5)
		self.framePreviewPrint.show()
		self.boxPreviewPrint = gtk.HBox()
		self.framePreviewPrint.add(self.boxPreviewPrint)
		self.boxPreviewPrint.show()

		# Create slice image.
		self.sliceView = monkeyprintGuiHelper.imageView(settings=self.programSettings, modelCollection=self.modelCollection, width=200)
		self.boxPreviewPrint.pack_start(self.sliceView, expand=True, fill=True)
		self.sliceView.show()




	# Notebook tab switch callback functions. #################################
	# Model page.
	def tabSwitchModelUpdate(self):
		# Set render actor visibilities.
		self.modelCollection.viewState(0)
		self.renderView.render()
		# Enable model management load and remove buttons.
		self.modelListView.setSensitive(remove=self.modelCollection.modelsLoaded())

	# Supports page.
	def tabSwitchSupportsUpdate(self):
		# Update supports.
		self.modelCollection.updateAllSupports()
		# Set render actor visibilities.
		self.modelCollection.viewState(1)
		self.renderView.render()
		# Activate slice tab if not already activated.
		if self.getGuiState() == 1:
			self.setGuiState(2)
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False,False)

	# Slicing page.
	def tabSwitchSlicesUpdate(self):
		# Update slider.
		self.sliceSlider.updateSlider()
		# Update slice stack height.
		self.modelCollection.updateSliceStack()
		# Set render actor visibilites.
		self.modelCollection.viewState(2)
		self.renderView.render()
		# Activate print tab if not already activated.
		if self.getGuiState() == 2:
			self.setGuiState(3)
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False,False)

	# Print page.
	def tabSwitchPrintUpdate(self):
		# Set render actor visibilites.
		self.modelCollection.viewState(3)
		# Set current slice to 0.
		self.modelCollection.updateAllSlices3d(0)
		self.renderView.render()
		# Update the model volume.
		self.updateVolume()
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False, False)





	# Other callback function. ################################################

	def callbackCheckButtonHollow(self, widget, data=None):
		self.modelCollection.getCurrentModel().settings['printHollow'].setValue(widget.get_active())
		# Update model.
		self.updateCurrentModel()

	def callbackCheckButtonFill(self, widget, data=None):
		self.modelCollection.getCurrentModel().settings['fill'].setValue(widget.get_active())
		self.updateCurrentModel()

	def callbackSaveSlices(self, widget, data=None):
		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Save slices", None, gtk.FILE_CHOOSER_ACTION_SAVE, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_SAVE, gtk.RESPONSE_OK))
		dialog.set_modal(True)
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.programSettings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Image files")
		fileFilter.add_pattern("*.png")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Process response. If OK...
		if response == gtk.RESPONSE_OK:
			# ... get file name.
			path = dialog.get_filename()
			dialog.destroy()
			#... add *.png file extension if necessary.
			if len(path) < 4 or path[-4:] != ".png":
				path += ".png"
			# Console message.
			self.console.addLine("Saving slice images to \"" + path.split('/')[-1] + "\".")
			# Save path without project name for next use.
			self.programSettings['currentFolder'].value = path[:-len(path.split('/')[-1])]
			# Create info window with progress bar.
			infoWindow = gtk.Window()
			infoWindow.set_title("Saving slice images")
			infoWindow.set_modal(True)
			infoWindow.set_transient_for(self)
			infoWindow.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
			infoWindow.show()
			infoBox = gtk.VBox()
			infoWindow.add(infoBox)
			infoBox.show()
			infoLabel = gtk.Label("Saving slice images.")
			infoBox.pack_start(infoLabel, expand=True, fill=True, padding=5)
			infoLabel.show()
			progressBar = monkeyprintGuiHelper.printProgressBar()
			infoBox.pack_start(progressBar, padding=5)
			# We work in percent here...
			progressBar.setLimit(100)#self.modelCollection.getNumberOfSlices())
			progressBar.show()
			# Update the gui.
			while gtk.events_pending():
				gtk.main_iteration(False)
			# Save the model collection to the given location.
			self.modelCollection.saveSliceStack(path=path, updateFunction=progressBar.updateValue)
			#TODO: self.progressBar.setText(message)
			# Close info window.
			infoWindow.destroy()
			self.console.addLine("Slice stack saved.")


		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()

	def callbackCheckButtonTrigger1(self, widget, data=None):
		# Uncheck other option if both are true.
		if self.checkboxCameraTrigger1.get_active() and self.checkboxCameraTrigger2.get_active():
			self.checkboxCameraTrigger2.set_active(False)
		# Write to settings.
		self.programSettings['camTriggerWithExposure'].setValue(widget.get_active())

	def callbackCheckButtonTrigger2(self, widget, data=None):
		# Uncheck other option if both are true.
		if self.checkboxCameraTrigger1.get_active() and self.checkboxCameraTrigger2.get_active():
			self.checkboxCameraTrigger1.set_active(False)
		# Write to settings.
		self.programSettings['camTriggerAfterExposure'].setValue(widget.get_active())

	def callbackStartPrintProcess(self, data=None):
		# Create a print start dialog.
		self.dialogStart = dialogStartPrint(parent = self)
		# Run the dialog and get the result.
		response = self.dialogStart.run()
		self.dialogStart.destroy()
		if response == True:
			#self.printProcessStart()
			if not self.queueCommands.qsize():
				self.queueCommands.put("start:")

	def printProcessStart(self, filename=None):	# Filename is needed for print on Raspberry.
		if filename == "":
			filename = None

		# If starting print process on PC...
		if not self.programSettings['printOnRaspberry'].value:
			#... create the projector window and start the print process.
			self.console.addLine("Starting print")
			# Disable window close event.
			self.printFlag = True
			# Set progressbar limit according to number of slices.
			self.progressBar.setLimit(self.modelCollection.getNumberOfSlices())
			# Create the projector window.2
			self.projectorDisplay = monkeyprintGuiHelper.projectorDisplay(self.programSettings, self.modelCollection)
			# Start the print.
			self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSliceOut, self.queueSliceIn, self.queueStatus, self.queueConsole)
			self.printProcess.start()
		# If starting print process on Raspberry Pi...
		elif self.programSettings['printOnRaspberry'].value:
			print "Starting print from Raspberry Pi."
			#... pack the data and send it to the Pi.
			path = self.programSettings['localMkpPath'].value		#os.getcwd() + "/currentPrint.mkp"
			# Console message.
			self.console.addLine("Saving project to \"" + path.split('/')[-1] + "\".")
			# Save the model collection to the given location.
			self.modelCollection.saveProject(path)
			#command = "print"

			self.socket.sendMulti("command", "start:" + path)

			print "Commands sent."
		# Set button sensitivities.
		self.buttonPrintStart.set_sensitive(False)
		self.buttonPrintStop.set_sensitive(True)



	def callbackStopPrintProcess(self, data=None):
		# Create a dialog window with yes/no buttons.
		dialog = gtk.MessageDialog(	None,
								gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
								gtk.MESSAGE_QUESTION,
								gtk.BUTTONS_YES_NO,
								"Do you really want to cancel the print?")
          # Set the title.
		dialog.set_title("Cancel print?")
		# Check the result and respond accordingly.
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			#self.printProcessStop()
			if not self.queueCommands.qsize():
				self.queueCommands.put("stop:")



	def printProcessStop(self, data=None):
		# Stop the print process.
		# If print is running on Pi...
		if self.programSettings['printOnRaspberry'].value:
			# ... send the stop command.
			command = "stop"
			path = ""
			self.socket.sendMulti(command, path)
		else:
			self.printProcess.stop()
		# Reset stop button to insensitive.
		self.buttonPrintStop.set_sensitive(False)





	def updateVolume(self):
		self.resinVolumeLabel.set_text("Volume: " + str(self.modelCollection.getTotalVolume()) + " ml.")



	def setGuiState(self, state):
		for i in range(self.notebook.get_n_pages()):
			if i<=state:
				self.notebook.set_tab_sensitive(i, True)
			else:
				self.notebook.set_tab_sensitive(i, False)



	def getGuiState(self):
		tab = 0
		for i in range(self.notebook.get_n_pages()):
			if self.notebook.is_tab_sensitivte(i):
				tab = i
		return tab



	# Function to update the current model after a change was made.
	# Updates model supports or slicing dependent on
	# the current page of the settings notebook.
	def updateCurrentModel(self):
		if self.notebook.getCurrentPage() == 0:
			self.modelCollection.getCurrentModel().updateModel()
			self.modelCollection.getCurrentModel().updateSupports()
		elif self.notebook.getCurrentPage() == 1:
			self.modelCollection.getCurrentModel().updateSupports()
		elif self.notebook.getCurrentPage() == 2:
			self.modelCollection.getCurrentModel().setChanged()
			self.modelCollection.getCurrentModel().updateSliceStack()
		elif self.notebook.getCurrentPage() == 3:
			self.modelCollection.getCurrentModel().updatePrint()



	def updateAllModels(self):
		if self.notebook.getCurrentPage() in [2,3]:
			self.modelCollection.updateAllModels()
			self.modelCollection.updateSliceStack()
		elif self.notebook.getCurrentPage() in [0,1]:
			self.modelCollection.updateAllModels()



	# Update all the settings if the current model has changed.
	def updateAllEntries(self, state=None, render=None):
		if not self.modelCollection.getCurrentModel().isactive():
			self.entryScaling.set_sensitive(False)
			self.entryRotationX.set_sensitive(False)
			self.entryRotationY.set_sensitive(False)
			self.entryRotationZ.set_sensitive(False)
			self.entryPositionX.set_sensitive(False)
			self.entryPositionY.set_sensitive(False)
			self.entryBottomClearance.set_sensitive(False)
			self.entryOverhangAngle.set_sensitive(False)
			self.entrySupportSpacingX.set_sensitive(False)
			self.entrySupportSpacingY.set_sensitive(False)
			self.entrySupportMaxHeight.set_sensitive(False)
			self.entrySupportBaseDiameter.set_sensitive(False)
			self.entrySupportTipDiameter.set_sensitive(False)
			self.entrySupportTipHeight.set_sensitive(False)
			self.entrySupportBottomPlateThickness.set_sensitive(False)
			self.entryFillSpacing.set_sensitive(False)
			self.entryFillThickness.set_sensitive(False)
			self.entryShellThickness.set_sensitive(False)
			self.checkboxFill.set_sensitive(False)
			self.checkboxHollow.set_sensitive(False)
		else:
			self.entryScaling.set_sensitive(True)
			self.entryRotationX.set_sensitive(True)
			self.entryRotationY.set_sensitive(True)
			self.entryRotationZ.set_sensitive(True)
			self.entryPositionX.set_sensitive(True)
			self.entryPositionY.set_sensitive(True)
			self.entryBottomClearance.set_sensitive(True)
			self.entryOverhangAngle.set_sensitive(True)
			self.entrySupportSpacingX.set_sensitive(True)
			self.entrySupportSpacingY.set_sensitive(True)
			self.entrySupportMaxHeight.set_sensitive(True)
			self.entrySupportBaseDiameter.set_sensitive(True)
			self.entrySupportTipDiameter.set_sensitive(True)
			self.entrySupportTipHeight.set_sensitive(True)
			self.entrySupportBottomPlateThickness.set_sensitive(True)
			self.entryFillSpacing.set_sensitive(True)
			self.entryFillThickness.set_sensitive(True)
			self.entryShellThickness.set_sensitive(True)
			self.checkboxFill.set_sensitive(True)
			self.checkboxHollow.set_sensitive(True)
			self.entryScaling.update()
			self.entryRotationX.update()
			self.entryRotationY.update()
			self.entryRotationZ.update()
			self.entryPositionX.update()
			self.entryPositionY.update()
			self.entryBottomClearance.update()
			self.entryOverhangAngle.update()
			self.entrySupportSpacingX.update()
			self.entrySupportSpacingY.update()
			self.entrySupportMaxHeight.update()
			self.entrySupportBaseDiameter.update()
			self.entrySupportTipDiameter.update()
			self.entrySupportTipHeight.update()
			self.entrySupportBottomPlateThickness.update()
			self.entryFillSpacing.update()
			self.entryFillThickness.update()
			self.entryShellThickness.update()
			self.checkboxFill.update()
			self.checkboxHollow.update()
		# Update job settings.
		self.entryLayerHeight.update()
		self.entryExposure.update()
		self.entryExposureBase.update()
		# Update menu sensitivities.
		self.updateMenu()
		if state != None:
			self.setGuiState(state)
			if state == 0:
				self.notebook.setCurrentPage(0)
		# Update the volume label in the print tab.
		if self.notebook.getCurrentPage() == 3:
			self.updateVolume()
		# Update model visibilities.
		if render == True:
			self.modelCollection.getCurrentModel().showAllActors(self.notebook.getCurrentPage())
			self.renderView.render()
		# Hide camera trigger box when using G-Code.
		if self.programSettings['monkeyprintBoard'].value:
			self.frameCameraTrigger.show()
		else:
			self.frameCameraTrigger.hide()



	def updateSlider(self):
		self.sliceSlider.updateSlider()



	def updateMenu(self):
		self.menuItemSave.set_sensitive(self.modelCollection.modelsLoaded())
		self.menuItemClose.set_sensitive(self.modelCollection.modelsLoaded())




# Model list. ##################################################################
class modelListView(gtk.VBox):
	def __init__(self, settings, modelCollection, renderView, guiUpdateFunction, console=None):
		gtk.VBox.__init__(self)
		self.show()

		# Internalise settings.
		self.settings = settings
		# Internalise model collection and optional console.
		self.modelCollection = modelCollection
		self.modelList = self.modelCollection.modelList
		# Import the render view so we are able to add and remove actors.
		self.renderView = renderView
		self.guiUpdateFunction = guiUpdateFunction
		self.console = console

		self.modelRemovedFlag = False
		self.previousSelection = None

		# Create the scrolled window.
		self.scrolledWindow = gtk.ScrolledWindow()
		self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.pack_start(self.scrolledWindow, expand=True, fill=True, padding = 5)
		self.scrolledWindow.show()
		# Create view for model list.
		self.viewModels = gtk.TreeView()
		self.viewModels.set_model(self.modelList)
		self.viewModels.show()
#		self.viewModels.set_headers_visible(False)	# Make column invisible.
		self.viewModels.set_headers_clickable(True)
		self.viewModels.set_reorderable(True)
		self.scrolledWindow.add(self.viewModels)
		# Add model name column and respective text cell renderer.
		self.columnModel = gtk.TreeViewColumn('Model name')
		self.viewModels.append_column(self.columnModel)
		self.cellModel = gtk.CellRendererText()
		self.cellModel.set_property('editable', True)
		self.cellModel.connect('edited', self.callbackEdited, self.modelList)
		self.columnModel.pack_start(self.cellModel, True)
		self.columnModel.add_attribute(self.cellModel, 'text', 0)
		self.columnModel.set_sort_column_id(0)
		# Add active? column and respective toggle cell renderer.
		self.columnactive = gtk.TreeViewColumn('active?')
		self.viewModels.append_column(self.columnactive)
		self.cellactive = gtk.CellRendererToggle()
		self.cellactive.set_property('activatable', True)
		self.cellactive.connect("toggled", self.callbackToggleChanged, self.modelList)
		self.columnactive.pack_start(self.cellactive, False)
		self.columnactive.add_attribute(self.cellactive, 'active', 3)
		self.columnactive.set_sort_column_id(3)

		# Create item selection.
		self.modelSelection = self.viewModels.get_selection()
		# Avoid multiple selection.
		self.modelSelection.set_mode(gtk.SELECTION_SINGLE)
		# Connect to selection change event function.
		self.modelSelection.connect('changed', self.onSelectionChanged)

		# Create button box.
		self.boxButtons = gtk.HBox()
		self.boxButtons.show()
		self.pack_start(self.boxButtons, expand=False)
		# Create model load and remove button.
		self.buttonLoad = gtk.Button("Load")
		self.buttonLoad.show()
		self.buttonLoad.connect("clicked", self.callbackLoad)
		self.boxButtons.pack_start(self.buttonLoad)
		self.buttonRemove = gtk.Button("Remove")
		self.buttonRemove.set_sensitive(False)
		self.buttonRemove.show()
		self.buttonRemove.connect("clicked", self.callbackRemove)
		self.boxButtons.pack_start(self.buttonRemove)

	# Add an item and set it selected.
	def add(self, displayName, internalName, filename):
		# Append list item and get its iter.
		newIter = self.modelList.append([displayName, internalName, filename, True])
		# Set the iter selected.
		self.modelSelection.select_iter(newIter)
		# Make supports and slice tab available if this is the first model.
		if len(self.modelList)< 2:
			self.guiUpdateFunction(state=1)

	# Remove an item and set the selection to the next.
	def remove(self, currentIter):
		# Get the path of the current iter.
		currentPath = self.modelList.get_path(currentIter)[0]
		deletePath = currentPath
		# Check what to select next.
		# If current selection at end of list but not the last element...
		if currentPath == len(self.modelList) - 1 and len(self.modelList) > 1:
			# ... select the previous item.
			currentPath -= 1
			self.modelSelection.select_path(currentPath)
		# If current selection is somewhere in the middle...
		elif currentPath < len(self.modelList) - 1 and len(self.modelList) > 1:
			# ... selected the next item.
			currentPath += 1
			self.modelSelection.select_path(currentPath)
		# If current selection is the last element remaining...
		elif len(self.modelList)	== 1:
			# ... set the default model as current model.
			self.modelCollection.setCurrentModelId("default")
			# Deactivate the remove button.
			self.buttonRemove.set_sensitive(False)
			# Update the gui.
			self.guiUpdateFunction(state=0)

		# Now that we have the new selection, we can delete the previously selected model.
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getActor())
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getBoxActor())
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getBoxTextActor())
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getAllActors())
		# Some debug output...
		if self.console:
			self.console.addLine("Removed model " + self.modelList.get_value(currentIter,0) + ".")
		# Remove the model from the model collection object.
		self.modelCollection.remove(self.modelList[currentIter][1])
		# Remove the item and check if there's a next item.
		iterValid = self.modelList.remove(currentIter)
		# Update the slice stack.
	#	self.modelCollection.updateSliceStack()
		# Update the slider.
		self.guiUpdateFunction()
		# Refresh view.
		self.renderView.render()


	# Load a new item into the model list and set it selected.
	def callbackLoad(self, widget, data=None):
		filepath = ""

		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Load model", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.settings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Stl files")
		fileFilter.add_pattern("*.stl")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Check the response.
		# If OK was pressed...
		if response == gtk.RESPONSE_OK:
			filepath = dialog.get_filename()
			# Check if file is an stl. If yes, load.
			if filepath.lower()[-3:] != "stl":
				if self.console:
					self.console.addLine("File \"" + filepath + "\" is not an stl file.")
			else:
				# Get filename without path.
				filenameStlParts = filepath.split('/')
				filename = filenameStlParts[-1]
				if self.console:
					self.console.addLine("Loading file \"" + filename + "\".")
				# Save path for next use.
				self.settings['currentFolder'].value = filepath[:-len(filenameStlParts[-1])]
				# Check if there is a file with the same name loaded already.
				# Use the permanent file id in second row for this.
				copyNumber = 0
				for row in self.modelList:
					# Check if filename already loaded.
					if filename == row[1][:len(filename)]:
						# If so, set the copy number to 1.
						copyNumber = 1
						# Check if this is a copy already.
						if len(row[1]) > len(filename):
							if int(row[1][len(filename)+2:len(row[1])-1]) >= copyNumber:
								copyNumber = int(row[1][len(filename)+2:len(row[1])-1]) + 1
				if copyNumber > 0:
					filename = filename + " (" + str(copyNumber) + ")"
			# Hide the previous models bounding box.
			self.modelCollection.getCurrentModel().hideBox()
			# Load the model into the model collection.
			self.modelCollection.add(filename, filepath)
			# Add the filename to the list and set selected.
			self.add(filename, filename, filepath)
			# Activate the remove button which was deactivated when there was no model.
			self.buttonRemove.set_sensitive(True)
			# Add actor to render view.
			self.renderView.addActors(self.modelCollection.getCurrentModel().getAllActors())

			# Update 3d view.
			self.renderView.render()

			dialog.destroy()
		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()

	# Delete button callback.
	def callbackRemove(self, widget, data=None):
		model, treeiter = self.modelSelection.get_selected()
		self.remove(treeiter)

	# Name edited callback.
	def callbackEdited(self, cell, path, new_text, model):
		model[path][0] = new_text

	# active state toggled callback.
	def callbackToggleChanged(self, cell, path, model):
		# Save previous selection. Contains tree model and selection iter.
		model, treeiter = self.modelSelection.get_selected()
		# Select the row that has been clicked.
		self.modelSelection.select_path(path)
		# Toggle active flag in model list.
		model[path][3] = not model[path][3]
		# Set active flag in model collection.
		self.modelCollection.getCurrentModel().setactive(model[path][3])
		# Show box.
		self.modelCollection.getCurrentModel().showBox()
		# Call gui update function to change actor visibilities.
		self.guiUpdateFunction(render=True)
		# Console output.
		if self.console:
			if model[path][3] == True:
				self.console.addLine("Model " + model[path][0] + " activated.")
			else:
				self.console.addLine("Model " + model[path][0] + " deactivated.")
		# Restore previous selection. Only on deactivation.
		if model[path][3] == False:
			self.modelSelection.select_iter(treeiter)
		else:
	#		# Update model.
			self.modelCollection.getCurrentModel().updateModel()
			self.modelCollection.getCurrentModel().updateSupports()
			self.renderView.render()
	#		self.modelCollection.getCurrentModel().updateSliceStack()


	# Selection changed callback.
	def onSelectionChanged(self, selection):
		# Hide the previous models bounding box actor.
		self.modelCollection.getCurrentModel().hideBox()
		model, treeiter = selection.get_selected()
		if treeiter != None:	# Make sure someting is selected.
			if self.console:
				self.console.addLine("Model " + model[treeiter][0] + " selected.")
			# Set current model in model collection.
			self.modelCollection.setCurrentModelId(model[treeiter][1])
			# Show bounding box.
			self.modelCollection.getCurrentModel().showBox()
			self.renderView.render()
			# Update the gui.
			self.guiUpdateFunction()
		# Save for later.
		self.previousSelection = treeiter

	# Disable buttons so models can only be loaded in first tab.
	def setSensitive(self, load=True, remove=True):
		self.buttonLoad.set_sensitive(load)
		self.buttonRemove.set_sensitive(remove)

	def update(self):
		# Update list.
	#	self.modelList = self.modelCollection.modelList
		# Select first model.
		self.modelSelection.select_iter(self.modelList.get_iter(0))



# Window for firmware upload. ##################################################
class dialogFirmware(gtk.Window):
	# Override init function.
	def __init__(self, settings, parent):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		# Set title.
		self.set_title("Update firmware")
		# Set modal.
		self.set_modal(True)
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
		self.set_transient_for(parent)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.show()


		# Internalise settings.
		self.settings = settings


		# If G-Code board is used append GCode to settings strings.
		if self.settings['monkeyprintBoard'].value:
			self.postfix = ""
		else:
			self.postfix = "GCode"


		# Create avrdude queue.
		self.queueAvrdude = Queue.Queue()

		# Create avrdude thread.
		#self.threadAvrdude = monkeyprintGuiHelper.avrdudeThread(self.settings, self.queueAvrdude)

		# Main container.
		box = gtk.VBox()
		self.add(box)
		box.show()

		# Description.
		boxLabel = gtk.HBox()
		box.pack_start(boxLabel, padding=5)
		boxLabel.show()
		label = gtk.Label("Push your board's reset button twice and press \"Flash firmware\"!")
		boxLabel.pack_start(label, expand=False, fill=False, padding=5)
		label.show()

		# Horizontal container for entries and buttons.
		boxEntriesAndButtons = gtk.HBox()
		box.pack_start(boxEntriesAndButtons, padding=5)
		boxEntriesAndButtons.show()

		frameEntries = gtk.Frame("Settings")
		boxEntriesAndButtons.pack_start(frameEntries, padding=5)
		frameEntries.show()

		# Make a box for the entries.
		boxEntries = gtk.VBox()
		frameEntries.add(boxEntries)
		boxEntries.show()

		# Avrdude option entries.
		self.entryMCU = monkeyprintGuiHelper.entry('avrdudeMcu'+self.postfix, settings=self.settings, width=20)#, displayString="MCU")
		boxEntries.pack_start(self.entryMCU)
		self.entryProgrammer = monkeyprintGuiHelper.entry('avrdudeProgrammer'+self.postfix, settings=self.settings, width=20)#, displayString="Programmer")
		boxEntries.pack_start(self.entryProgrammer)
		self.entryPort = monkeyprintGuiHelper.entry('avrdudePort'+self.postfix, settings=self.settings, width=20)#, displayString="Port")
		boxEntries.pack_start(self.entryPort)
		self.entryBaud = monkeyprintGuiHelper.entry('avrdudeBaudrate'+self.postfix, settings=self.settings, width=20)#, displayString="Baud rate")
		boxEntries.pack_start(self.entryBaud)
		self.entryOptions = monkeyprintGuiHelper.entry('avrdudeOptions'+self.postfix, settings=self.settings, customFunctions=[self.entryOptionsUpdate], width=20)#, displayString="Options")
		boxEntries.pack_start(self.entryOptions)
		boxPath = gtk.HBox()
		boxEntries.pack_start(boxPath)
		boxPath.show()
		self.entryPath = monkeyprintGuiHelper.entry('avrdudeFirmwarePath'+self.postfix, settings=self.settings, width=14)#, displayString="Firmware path")
		boxPath.pack_start(self.entryPath)
		self.buttonPath = gtk.Button('…')
		boxPath.pack_start(self.buttonPath, expand=False, fill=False, padding=5)
		self.buttonPath.connect('clicked', self.callbackButtonPath)
		self.buttonPath.show()


		# Make a box for the buttons.
		boxButtons = gtk.VBox()
		boxEntriesAndButtons.pack_start(boxButtons, expand=True, fill=True, padding=5)
		boxButtons.show()

		# Flash button.
		self.buttonFlash = gtk.Button("Flash firmware")
		boxButtons.pack_start(self.buttonFlash, expand=True, fill=True)
		self.buttonFlash.connect("clicked", self.callbackFlash)
		self.buttonFlash.show()

		# Create an output window for avrdude feedback.
		boxConsole = gtk.HBox()
		box.pack_start(boxConsole, padding=5)
		boxConsole.show()
		self.console = monkeyprintGuiHelper.consoleText()
		self.consoleView = monkeyprintGuiHelper.consoleView(self.console)
		boxConsole.pack_start(self.consoleView, padding=5)
		self.consoleView.show()

		# Button box.
		boxClose = gtk.HBox()
		box.pack_start(boxClose, padding=5)
		boxClose.show()
		# Close button.
		buttonClose = gtk.Button("Close")
		boxClose.pack_end(buttonClose, expand=False, fill=False, padding=5)
		buttonClose.connect("clicked", self.callbackClose)
		buttonClose.show()
		# Back to defaults button.
		buttonDefaults = gtk.Button("Restore defaults")
		boxClose.pack_end(buttonDefaults, expand=False, fill=False)
		buttonDefaults.connect("clicked", self.callbackDefaults)
		buttonDefaults.show()


	def entryOptionsUpdate(self):
		# Process options.
		# Extract additional options into list and eliminate '-' from options.
		optionList = self.entryOptions.entry.get_text().replace('-','')
		# Split into option list.
		optionList = optionList.split(' ')
		# Add '-' to options. This way users can input options with and without '-'.
		optionList = ['-' + option for option in optionList]
		# Concatenate into string for settings object.
		optionString = ''
		for option in optionList:
			if option != "-":
				optionString = optionString + option + ' '
		# Remove trailing space.
		optionString = optionString[:-1]
		# Write to settings and set entry string.
		self.settings['avrdudeOptions'+self.postfix].value = optionString
		self.entryOptions.entry.set_text(optionString)

	def callbackButtonPath(self, widget, data=None):
		# Open file chooser dialog."
		filepath = ""
		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Choose firmware file", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_modal(True)
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(''.join(self.settings['avrdudeFirmwarePath'+self.postfix].value.split("/")[:-1]))
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Firmware files")
		fileFilter.add_pattern("*.hex")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Check the response.
		# If OK was pressed...
		if response == gtk.RESPONSE_OK:
			self.settings['avrdudeFirmwarePath'+self.postfix].value = dialog.get_filename()
			self.entryPath.update()
			# Close dialog.
			dialog.destroy()
		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()

	def callbackFlash(self, widget, data=None):
		# Change button sensititvity and label.
		self.buttonFlash.set_sensitive(False)
		self.buttonFlash.set_label("Flashing. Please wait...")
		# Console output.
		self.console.addLine('Running avrdude with options:')
		self.console.addLine('-p ' + self.settings['avrdudeMcu'+self.postfix].value + ' -P ' + self.settings['avrdudePort'+self.postfix].value + ' -c ' + self.settings['avrdudeProgrammer'+self.postfix].value + ' -b ' + str(self.settings['avrdudeBaudrate'+self.postfix].value) + ' -U ' + 'flash:w:' + self.settings['avrdudeFirmwarePath'+self.postfix].value + " " + self.settings['avrdudeOptions'+self.postfix].value)
		self.console.addLine("")
		# Create avrdude thread.
		self.threadAvrdude = monkeyprintGuiHelper.avrdudeThread(self.settings, self.queueAvrdude)
		# Add avrdude thread listener to gui main loop.
		listenerIdAvrdude = gobject.timeout_add(100, self.listenerAvrdudeThread)
		# Start avrdude thread.
		self.threadAvrdude.start()


	def flash(self):
		# Create avrdude commandline string.
		avrdudeCommandList = [	'avrdude',
							'-p', self.settings['avrdudeMcu'+self.postfix].value,
							'-P', self.settings['avrdudePort'+self.postfix].value,
							'-c', self.settings['avrdudeProgrammer'+self.postfix].value,
							'-b', str(self.settings['avrdudeBaudrate'+self.postfix].value),
							'-U', 'flash:w:' + self.settings['avrdudeFirmwarePath'+self.postfix].value
							]
		# Append additional options.
		optionList = self.settings['avrdudeOptions'+self.postfix].value.split(' ')
		for option in optionList:
			avrdudeCommandList.append(option)
		# Call avrdude and get it's output.
		# Redirect error messages to stdout and stdout to PIPE
		avrdudeProcess = subprocess.Popen(avrdudeCommandList, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		output = avrdudeProcess.communicate()[0]
		# If an error occured...
		if avrdudeProcess.returncode !=0:
			#... display the error message.
			self.console.addLine("Error code: " + str(avrdudeProcess.returncode))
			self.console.addLine("Error message: " + output)
			self.console.addLine("Make sure the Arduino is connected correctly.")
		# In case of success...
		else:
			# Print the output.
			self.console.addLine(output)
			self.console.addLine("Firmware flashed successfully!")
		# Restore button.
		self.buttonFlash.set_sensitive(True)
		self.buttonFlash.set_label("Flash firmware")

	def listenerAvrdudeThread(self):
		# Add a dot to the console to let people know the program is not blocked...
		self.console.addString(".")
		# If a message is in the queue...
		if self.queueAvrdude.qsize():
			# ... we know that avrdude is done.
			# Get the message and display it.
			message = self.queueAvrdude.get()
			self.console.addLine(message)
			# Restore flash button.
			self.buttonFlash.set_sensitive(True)
			self.buttonFlash.set_label("Flash firmware")
			# Delete the thread.
			del self.threadAvrdude
			# Return False to remove listener from timeout.
			return False
		else:
			# Return True to keep listener in timeout.
			return True


	def callbackDefaults(self, widget, data=None):
		# Set default settings.
		self.settings.loadDefaults()
		# Update entries.
		self.entryMCU.update()
		self.entryProgrammer.update()
		self.entryPort.update()
		self.entryBaud.update()
		self.entryPath.update()
		self.entryOptions.update()

	def callbackClose(self, widget, data=None):
		self.destroy()





class dialogManualControl(gtk.Window):
	# Override init function.
	def __init__(self, settings, parent):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		# Set title.
		self.set_title("Manual printer control?")
		# Set modal.
		self.set_modal(True)
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
		self.set_transient_for(parent)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.show()

		# Internalise settings.
		self.settings = settings

		# Create queue for communication between gui and serial.
		self.queueSerial = Queue.Queue()
		self.queueSerialCommands = Queue.Queue()

		# Create serial.
		self.serialPrinter = monkeyprintSerial.printer(self.settings, self.queueSerial, self.queueSerialCommands)

		# Create gui widgets.
		box = gtk.VBox()
		self.add(box)
		box.show()

		frameCommands = gtk.Frame()
		box.pack_start(frameCommands, padding=5)
		frameCommands.show()

		boxCommands = gtk.HBox()
		frameCommands.add(boxCommands)
		boxCommands.show()

		labelCommand = gtk.Label("Command")
		boxCommands.pack_start(labelCommand)
		labelCommand.show()

		self.entry = gtk.Entry(10)
		self.entry.set_text("tilt")
		boxCommands.pack_start(self.entry)
		self.entry.show()

		labelWait = gtk.Label("Wait")
		boxCommands.pack_start(labelWait)
		labelWait.show()

		self.entryWait = gtk.Entry(5)
		self.entryWait.set_text("5")
		boxCommands.pack_start(self.entryWait)
		self.entryWait.show()

		self.checkbuttonRetry = gtk.CheckButton("Retry?")
		self.checkbuttonRetry.set_active(True)
		boxCommands.pack_start(self.checkbuttonRetry)
		self.checkbuttonRetry.show()

		self.buttonSend = gtk.Button("   Send   ")
		boxCommands.pack_start(self.buttonSend)
		self.buttonSend.show()
		self.buttonSend.connect("clicked", self.callbackButtonSend)

		boxConsole = gtk.HBox()
		box.pack_start(boxConsole, padding=5)
		boxConsole.show()

		self.console = monkeyprintGuiHelper.consoleText()
		consoleView = monkeyprintGuiHelper.consoleView(self.console)
		boxConsole.pack_start(consoleView, padding=5)
		consoleView.show()

		# Start serial send loop.
		self.serialPrinter.start()

		# Set initial message if any.
		for i in range(self.queueSerial.qsize()):
			self.console.addLine(self.queueSerial.get())


	def callbackButtonSend(self, widget, data=None):
		self.buttonSend.set_sensitive(False)
		self.buttonSend.set_label("Sending...")
		# Add avrdude thread listener to gui main loop.
		listenerIdSerial = gobject.timeout_add(100, self.listenerSerialThread)
		wait = self.entryWait.get_text()
		if wait == "None": wait = None
#		self.queueSerialCommands.put([self.entry.get_text(), None, self.checkbuttonRetry.get_active(), wait])
		self.serialPrinter.send([self.entry.get_text(), None, self.checkbuttonRetry.get_active(), wait])


	def listenerSerialThread(self):
		# If a message is in the queue...
		if self.queueSerial.qsize():
			# ... we know that avrdude is done.
			# Get the message and display it.
			message = self.queueSerial.get()
			if message != 'done':
				self.console.addLine(message)
				return True
			else:
				# Restore flash button.
				self.buttonSend.set_sensitive(True)
				self.buttonSend.set_label("   Send   ")
				# Return False to remove listener from timeout.
				return False
		else:
			# Add a dot to the console to let people know the program is not blocked...
			self.console.addString(".")
			# Return True to keep listener in timeout.
			return True


	# Override destroy function.
	def destroy(self):
		self.serialPrinter.stop()
		self.serialPrinter.close()
		del self.serialPrinter
		del self





# Settings window. #############################################################
# Define a window for all the settings that are related to the printer.

class dialogSettings(gtk.Window):
	# Override init function.
	def __init__(self, settings, parentWindow):

		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		self.set_title("Monkeyprint settings")
		self.set_modal(True)
		self.set_transient_for(parentWindow)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.show()


		# Internalise settings.
		self.settings = settings

		self.parentWindow = parentWindow

		# Save settings in case of cancelling.
		#self.settingsBackup = settings

		# Tooltips object.
		self.tooltips = gtk.Tooltips()

		# Vertical box for settings and bottom buttons.
		self.boxMain = gtk.VBox()
		self.add(self.boxMain)
		self.boxMain.show()

		# Create notebook.
		self.notebookSettings = monkeyprintGuiHelper.notebook()
		self.boxMain.pack_start(self.notebookSettings, expand=True, fill=True)
		self.notebookSettings.show()

		# Create notebook pages.
		self.tabMainSettings = self.createMainSettingsTab()
		self.notebookSettings.append_page(self.tabMainSettings, gtk.Label('Main settings'))
		self.tabMainSettings.show()

		self.tabCommunicationSettings = self.createCommunicationTab()
		self.notebookSettings.append_page(self.tabCommunicationSettings, gtk.Label('Communication'))
		self.tabCommunicationSettings.show()


		self.tabProjectorSettings = self.createProjectorTab()
		self.notebookSettings.append_page(self.tabProjectorSettings, gtk.Label('Projector'))
		self.tabProjectorSettings.show()

		self.tabMotionSettings = self.createMotionTab()
		self.notebookSettings.append_page(self.tabMotionSettings, gtk.Label('Motion'))
		if self.settings['monkeyprintBoard'].value:
			self.tabMotionSettings.show()
		else:
			self.tabMotionSettings.hide()

		self.tabPrintProcessSettings = self.createPrintProcessTab()
		self.notebookSettings.append_page(self.tabPrintProcessSettings, gtk.Label('Print process'))
		self.tabPrintProcessSettings.show()

		# Set sensitivities according to toggle buttons in main settings tab.
		self.callbackRaspiToggle(None, None)

		# Toggle entry visibility regarding G-Code or Monkeyprint board.
		self.toggleGCodeEntries()

		# Create bottom buttons.
		# Horizontal box for buttons.
		self.boxButtons = gtk.HBox()
		self.boxMain.pack_start(self.boxButtons, expand=False, fill=False)
		self.boxButtons.show()

		# Close button.
		self.buttonClose = gtk.Button("Close")
		self.boxButtons.pack_end(self.buttonClose, expand=False, fill=False)
		self.buttonClose.connect("clicked", self.callbackClose)
		self.buttonClose.show()

		# Cancel button.
	#	self.buttonCancel = gtk.Button("Cancel")
	#	self.boxButtons.pack_end(self.buttonCancel, expand=False, fill=False)
	#	self.buttonCancel.connect("clicked", self.callbackCancel)
	#	self.buttonCancel.show()

		# Restore defaults button.
		self.buttonDefaults = gtk.Button("Load defaults")
		self.boxButtons.pack_end(self.buttonDefaults, expand=False, fill=False)
		self.buttonDefaults.connect("clicked", self.callbackDefaults)
		self.buttonDefaults.show()


	# Main settings tab.
	def createMainSettingsTab(self):

		boxMainSettings = gtk.VBox()

		# Frame for Raspberry setting.
		self.frameRaspberry = gtk.Frame('Hardware setup')
		boxMainSettings.pack_start(self.frameRaspberry, expand=False, fill=False, padding=5)
		self.frameRaspberry.show()
		self.boxRaspberry = gtk.VBox()
		self.frameRaspberry.add(self.boxRaspberry)
		self.boxRaspberry.show()
		# Add entries.
		# Use Raspberry Pi?
		self.labelRaspi = gtk.Label("Where do you want your prints to run from?")
		self.boxRaspberry.pack_start(self.labelRaspi, expand=True, fill=True, padding=5)
		self.labelRaspi.set_alignment(xalign=0, yalign=0.5)
		self.labelRaspi.show()
		self.labelRaspi.set_sensitive(False)
		self.radioButtonRaspiOff = gtk.RadioButton(group=None, label="Print from PC")
		self.radioButtonRaspiOff.connect("toggled", self.callbackRaspiToggle, "standalone")
		self.radioButtonRaspiOff.set_active(not self.settings['printOnRaspberry'].value)
		self.radioButtonRaspiOff.set_sensitive(False)
		self.boxRaspberry.pack_start(self.radioButtonRaspiOff, expand=True, fill=True)
		self.radioButtonRaspiOff.show()
		self.tooltips.set_tip(self.radioButtonRaspiOff, "Use this option if you want print jobs to run directly from your PC. Your PC has to remain connected to the printer during prints.")
		self.radioButtonRaspiOn = gtk.RadioButton(group=self.radioButtonRaspiOff, label="Print from Raspberry Pi")
		self.radioButtonRaspiOn.set_active(self.settings['printOnRaspberry'].value)
		self.radioButtonRaspiOn.connect("toggled", self.callbackRaspiToggle, "raspberry")
		self.boxRaspberry.pack_start(self.radioButtonRaspiOn, expand=True, fill=True)
		self.radioButtonRaspiOn.show()
		self.radioButtonRaspiOn.set_sensitive(False)
		self.tooltips.set_tip(self.radioButtonRaspiOn, "Use this option if you want print jobs to run from a Raspberry Pi. You can remove your PC during prints.")
		# Use Monkeyprint board?
		self.labelBoard = gtk.Label("Which board are you using?")
		self.boxRaspberry.pack_start(self.labelBoard, expand=True, fill=True, padding=5)
		self.labelBoard.set_alignment(xalign=0, yalign=0.5)
		self.labelBoard.show()
		self.radioButtonMonkeyprintBoardOn = gtk.RadioButton(group=None, label="Monkeyprint board")
		self.radioButtonMonkeyprintBoardOn.connect("toggled", self.callbackBoardToggle, "monkeyprintBoard")
		self.radioButtonMonkeyprintBoardOn.set_active(self.settings['monkeyprintBoard'].value)
		self.boxRaspberry.pack_start(self.radioButtonMonkeyprintBoardOn, expand=True, fill=True)
		self.radioButtonMonkeyprintBoardOn.show()
		self.tooltips.set_tip(self.radioButtonMonkeyprintBoardOn, "Use this option if you want to use the Monkeyprint board for controlling your hardware.")
		self.radioButtonMonkeyprintBoardOff = gtk.RadioButton(group=self.radioButtonMonkeyprintBoardOn, label="G-Code based board")
		self.radioButtonMonkeyprintBoardOff.set_active(not self.settings['monkeyprintBoard'].value)
		self.radioButtonMonkeyprintBoardOff.connect("toggled", self.callbackBoardToggle, "raspberry")
		self.boxRaspberry.pack_start(self.radioButtonMonkeyprintBoardOff, expand=True, fill=True)
		self.radioButtonMonkeyprintBoardOff.show()
		self.tooltips.set_tip(self.radioButtonMonkeyprintBoardOff, "Use this option if you want to use a G-Code based board for controlling your hardware.")
		# Frame for build volume settings.
		self.frameBuildVolume = gtk.Frame('Build volume')
		boxMainSettings.pack_start(self.frameBuildVolume, expand=False, fill=False, padding=5)
		self.frameBuildVolume.show()
		self.boxBuildVolume = gtk.VBox()
		self.frameBuildVolume.add(self.boxBuildVolume)
		self.boxBuildVolume.show()
		# Add entries.
		self.entryBuildSizeX= monkeyprintGuiHelper.entry('buildSizeX', self.settings, width=15)#, displayString="Build size X")
		self.boxBuildVolume.pack_start(self.entryBuildSizeX, expand=False, fill=False)
		self.entryBuildSizeX.show()
		self.entryBuildSizeY= monkeyprintGuiHelper.entry('buildSizeY', self.settings, width=15)#, displayString="Build size Y")
		self.boxBuildVolume.pack_start(self.entryBuildSizeY, expand=False, fill=False)
		self.entryBuildSizeY.show()
		self.entryBuildSizeZ= monkeyprintGuiHelper.entry('buildSizeZ', self.settings, width=15)#, displayString="Build size Z")
		self.boxBuildVolume.pack_start(self.entryBuildSizeZ, expand=False, fill=False)
		self.entryBuildSizeZ.show()

		# Frame for build volume settings.
		self.frameDebug = gtk.Frame('Debug')
		boxMainSettings.pack_start(self.frameDebug, expand=False, fill=False, padding=5)
		self.frameDebug.show()
		self.boxDebug = gtk.HBox()
		self.frameDebug.add(self.boxDebug)
		self.boxDebug.show()
		# Add entry.
		self.checkbuttonDebug = monkeyprintGuiHelper.toggleButton('debug', settings=self.settings)
		self.boxDebug.pack_start(self.checkbuttonDebug, expand=False, fill=False, padding=5)
		self.checkbuttonDebug.show()
		'''
		self.labelDebug = gtk.Label('debug')
		self.boxDebug.pack_start(self.labelDebug, expand=False, fill=False, padding=5)
		self.labelDebug.show()
		self.checkboxDebug = gtk.CheckButton()
		self.boxDebug.pack_start(self.checkboxDebug, expand=False, fill=False, padding=5)
		self.checkboxDebug.set_active(self.settings['debug'].value)
		self.checkboxDebug.show()
		self.checkboxDebug.connect('toggled', self.callbackDebug)
		'''

		boxMainSettings.show()

		return boxMainSettings

	# Communication tab.
	def createCommunicationTab(self):

		# Communication settings box.
		boxCommunication = gtk.VBox()


		# USB to serial frame.
		self.frameSerialUsb = gtk.Frame('PC serial connection')
		boxCommunication.pack_start(self.frameSerialUsb, expand=False, fill=False, padding=5)
		self.frameSerialUsb.show()
		self.boxSerialUsb = gtk.VBox()
		self.frameSerialUsb.add(self.boxSerialUsb)
		self.boxSerialUsb.show()
		# Add entries.
		# Port.
		self.entryPort = monkeyprintGuiHelper.entry('port', self.settings, width=15)
		self.boxSerialUsb.pack_start(self.entryPort, expand=False, fill=False)
		self.entryPort.show()
		# Baud rate.
		self.entryBaud = monkeyprintGuiHelper.entry('baudrate', self.settings, width=15)#, displayString="Baud rate")
		self.boxSerialUsb.pack_start(self.entryBaud, expand=False, fill=False)
		self.entryBaudGCode = monkeyprintGuiHelper.entry('baudrateGCode', settings=self.settings, width=15)#, displayString="Baud rate")
		self.boxSerialUsb.pack_start(self.entryBaudGCode)
		if self.settings['monkeyprintBoard'].value:
			self.entryBaudGCode.hide()
		else:
			self.entryBaud.hide()
		#self.entryBaud.show()

		# Raspberry Pi serial frame.
		self.frameSerialPi = gtk.Frame('Raspberry Pi serial connection')
		boxCommunication.pack_start(self.frameSerialPi, expand=False, fill=False, padding=5)
		self.frameSerialPi.show()
		self.boxSerialPi = gtk.VBox()
		self.frameSerialPi.add(self.boxSerialPi)
		self.boxSerialPi.show()
		# Add entries.
		# Port.
		self.entryPortPi = monkeyprintGuiHelper.entry('portRaspi', self.settings, width=15)#, displayString='Port')
		self.boxSerialPi.pack_start(self.entryPortPi, expand=False, fill=False)
		self.entryPortPi.show()
		# Baud rate.
		self.entryBaudPi = monkeyprintGuiHelper.entry('baudrateRaspi', self.settings, width=15)#, displayString="Baud rate")
		self.boxSerialPi.pack_start(self.entryBaudPi, expand=False, fill=False)
		self.entryBaudPi.show()

		# Raspberry Pi network frame.
		self.frameNetworkPi = gtk.Frame('Raspberry Pi network connection')
		boxCommunication.pack_start(self.frameNetworkPi, expand=False, fill=False, padding=5)
		self.frameNetworkPi.show()
		self.boxNetworkPi = gtk.VBox()
		self.frameNetworkPi.add(self.boxNetworkPi)
		self.boxNetworkPi.show()
		# Add entries.
		# IP adress.
		self.entryIpPi = monkeyprintGuiHelper.entry('ipAddressRaspi', self.settings, width=15)#, displayString="IP address")
		self.boxNetworkPi.pack_start(self.entryIpPi, expand=False, fill=False)
		self.entryIpPi.show()
		# Communication port.
		self.entryPortPi = monkeyprintGuiHelper.entry('networkPortRaspi', self.settings, width=15)#, displayString="Communication port")
		self.boxNetworkPi.pack_start(self.entryPortPi, expand=False, fill=False)
		self.entryPortPi.show()
		# File transfer port.
		self.entryPortPiFiles = monkeyprintGuiHelper.entry('fileTransmissionPortRaspi', self.settings, width=15)#, displayString="File transfer port")
		self.boxNetworkPi.pack_start(self.entryPortPiFiles, expand=False, fill=False)
		self.entryPortPiFiles.show()
		'''
		# User name.
		self.entrySshPi = monkeyprintGuiHelper.entry('SSH user name', self.settings, width=15)
		self.boxNetworkPi.pack_start(self.entrySshPi, expand=False, fill=False)
		self.entrySshPi.show()
		# User password.
		self.entrySshPiPW = monkeyprintGuiHelper.entry('SSH password', self.settings, width=15)
		self.boxNetworkPi.pack_start(self.entrySshPiPW, expand=False, fill=False)
		self.entrySshPiPW.show()
		'''

		# Console for serial test.
		self.consoleSerial = monkeyprintGuiHelper.consoleText()

		return boxCommunication


	def createProjectorTab(self):

		boxProjectorSettings = gtk.VBox()

		# Frame for projector resolution.
		self.frameProjector = gtk.Frame('Resolution & Position')
		boxProjectorSettings.pack_start(self.frameProjector, expand=False, fill=False, padding=5)
		self.frameProjector.show()
		self.boxProjector = gtk.VBox()
		self.frameProjector.add(self.boxProjector)
		self.boxProjector.show()

		self.entryProjectorSizeX= monkeyprintGuiHelper.entry('projectorSizeX', self.settings, width=15)#, displayString="Projector size X")
		self.boxProjector.pack_start(self.entryProjectorSizeX, expand=False, fill=False)
		self.entryProjectorSizeX.show()
		self.entryProjectorSizeY= monkeyprintGuiHelper.entry('projectorSizeY', self.settings, width=15)#, displayString="Projector size Y")
		self.boxProjector.pack_start(self.entryProjectorSizeY, expand=False, fill=False)
		self.entryProjectorSizeY.show()
		self.entryProjectorPositionX= monkeyprintGuiHelper.entry('projectorPositionX', self.settings, width=15)#, displayString="Projector position X")
		self.boxProjector.pack_start(self.entryProjectorPositionX, expand=False, fill=False)
		self.entryProjectorPositionX.show()
		self.entryProjectorPositionY= monkeyprintGuiHelper.entry('projectorPositionY', self.settings, width=15)#, displayString="Projector position Y")
		self.boxProjector.pack_start(self.entryProjectorPositionY, expand=False, fill=False)
		self.entryProjectorPositionY.show()

		# Frame projector control.
		self.frameProjectorControl = gtk.Frame('Projector control')
		boxProjectorSettings.pack_start(self.frameProjectorControl, expand=False, fill=False, padding=5)
		self.frameProjectorControl.show()
		self.boxProjectorControl = gtk.VBox()
		self.frameProjectorControl.add(self.boxProjectorControl)
		self.boxProjectorControl.show()
		# Check box for using projector control via serial.
		self.checkbuttonProjectorControl = monkeyprintGuiHelper.toggleButton(string="projectorControl", settings=self.settings, modelCollection=None, customFunctions=[self.callbackProjectorControl])#, displayString="Projector control")
		self.boxProjectorControl.pack_start(self.checkbuttonProjectorControl, expand=True, fill=True, padding=5)
		if self.settings['monkeyprintBoard'].value==True:
			self.checkbuttonProjectorControl.show()
		else:
			self.checkbuttonProjectorControl.hide()
		#self.boxProjectorControlCheckbox = gtk.HBox()
		#self.boxProjectorControl.pack_start(self.boxProjectorControlCheckbox, expand=True, fill=True)
		#self.boxProjectorControlCheckbox.show()
		#self.labelProjectorControl = gtk.Label('Projector control')
		#self.boxProjectorControlCheckbox.pack_start(self.labelProjectorControl, expand=True, fill=True)
		#self.labelProjectorControl.show()
		#self.checkboxProjectorControl = gtk.CheckButton()
		#self.boxProjectorControlCheckbox.pack_start(self.checkboxProjectorControl)
		#self.checkboxProjectorControl.set_active(self.settings['Projector control'].value)
		#self.checkboxProjectorControl.show()
		#self.checkboxProjectorControl.connect('toggled', self.callbackProjectorControl)
		# Entries.
		self.entryProjectorOnCommand= monkeyprintGuiHelper.entry('projectorOnCommand', self.settings, width=15)#, displayString="Projector ON command")
		self.boxProjectorControl.pack_start(self.entryProjectorOnCommand, expand=False, fill=False)
		self.entryProjectorOnCommand.show()
		self.entryProjectorOffCommand= monkeyprintGuiHelper.entry('projectorOffCommand', self.settings, width=15)#, displayString="Projector OFF command")
		self.boxProjectorControl.pack_start(self.entryProjectorOffCommand, expand=False, fill=False)
		self.entryProjectorOffCommand.show()

		self.entryProjectorPort= monkeyprintGuiHelper.entry('projectorPort', self.settings, width=15)#, displayString="Projector port")
		self.boxProjectorControl.pack_start(self.entryProjectorPort, expand=False, fill=False)
		if self.settings['monkeyprintBoard'].value==False:
			self.entryProjectorPort.show()
		self.entryProjectorBaud= monkeyprintGuiHelper.entry('projectorBaudrate', self.settings, width=15)#, displayString="Projector baud rate")
		self.boxProjectorControl.pack_start(self.entryProjectorBaud, expand=False, fill=False)
		if self.settings['monkeyprintBoard'].value==False:
			self.entryProjectorBaud.show()



		# Frame for projector calibration image.
		self.frameCalImage = gtk.Frame('Calibration image')
		boxProjectorSettings.pack_start(self.frameCalImage, expand=False, fill=False, padding=5)
		self.frameCalImage.show()
		self.boxCalImage = gtk.VBox()
		self.frameCalImage.add(self.boxCalImage)
		self.boxCalImage.show()
		# Image container to load from file.
		self.imageContainer = monkeyprintGuiHelper.imageFromFile(self.settings, 200)
		self.boxCalImage.pack_start(self.imageContainer)
		self.imageContainer.show()

		return boxProjectorSettings


	def createMotionTab(self):

		boxMotionSettings = gtk.VBox()

		# First, make the frames for Monkeyprint board. **********************
		# Frame for Tilt stepper.
		self.frameTiltStepper = gtk.Frame('Tilt stepper')
		boxMotionSettings.pack_start(self.frameTiltStepper, expand=False, fill=False, padding=5)
		self.frameTiltStepper.show()
		self.boxTilt = gtk.VBox()
		self.frameTiltStepper.add(self.boxTilt)
		self.boxTilt.show()
		# Entries.
		# Enable?
		self.checkbuttonTilt = monkeyprintGuiHelper.toggleButton(string='tiltEnable', settings=self.settings, modelCollection=None, customFunctions=[self.setTiltSensitive])
		self.boxTilt.pack_start(self.checkbuttonTilt, expand=False, fill=False)
		self.checkbuttonTilt.show()
		# Reverse?
		self.checkbuttonTiltReverse = monkeyprintGuiHelper.toggleButton(string='tiltReverse', settings=self.settings, modelCollection=None, customFunctions=[self.setTiltSensitive])#, displayString="Reverse tilt direction?")
		self.boxTilt.pack_start(self.checkbuttonTiltReverse, expand=False, fill=False)
		self.checkbuttonTiltReverse.show()
#		# G-Code entry.
#		self.entryTiltGCode = monkeyprintGuiHelper.entry('Tilt GCode', self.settings, width=30)
#		self.boxTilt.pack_start(self.entryTiltGCode, expand=False, fill=False)
#		self.entryTiltGCode.show()
#		self.entryTiltGCode.set_sensitive(self.settings['tiltEnable'].value)
#		# G-Code distance.
#		self.entryTiltDistanceGCode = monkeyprintGuiHelper.entry('Tilt distance GCode', self.settings, width=15)
#		self.boxTilt.pack_start(self.entryTiltDistanceGCode, expand=False, fill=False)
#		self.entryTiltDistanceGCode.show()
#		self.entryTiltDistanceGCode.set_sensitive(self.settings['tiltEnable'].value)
		# Resolution.
		self.entryTiltStepAngle = monkeyprintGuiHelper.entry('tiltStepAngle', self.settings, width=15)
		self.boxTilt.pack_start(self.entryTiltStepAngle, expand=False, fill=False)
		self.entryTiltStepAngle.show()
		self.entryTiltStepAngle.set_sensitive(self.settings['tiltEnable'].value)
		# Resolution.
		self.entryTiltMicrostepping = monkeyprintGuiHelper.entry('tiltMicroStepsPerStep', self.settings, width=15)
		self.boxTilt.pack_start(self.entryTiltMicrostepping, expand=False, fill=False)
		self.entryTiltMicrostepping.show()
		self.entryTiltMicrostepping.set_sensitive(self.settings['tiltEnable'].value)
		# Tilt angle.
		self.entryTiltAngle = monkeyprintGuiHelper.entry('tiltAngle', self.settings, width=15)
		self.boxTilt.pack_start(self.entryTiltAngle, expand=False, fill=False)
		self.entryTiltAngle.show()
		self.entryTiltAngle.set_sensitive(self.settings['tiltEnable'].value)
		# Set entry sensitivities.
		self.setTiltSensitive()

		# Frame for build stepper.
		self.frameBuildStepper = gtk.Frame('Build platform stepper')
		boxMotionSettings.pack_start(self.frameBuildStepper, expand=False, fill=False, padding=5)
		self.frameBuildStepper.show()
		self.boxBuildStepper = gtk.VBox()
		self.frameBuildStepper.add(self.boxBuildStepper)
		self.boxBuildStepper.show()
		# Entries.
		# Reverse?
		self.checkbuttonBuildReverse = monkeyprintGuiHelper.toggleButton(string="reverseBuild", settings=self.settings, modelCollection=None, customFunctions=[self.setTiltSensitive])#, displayString="reverseBuild direction?")
		self.boxBuildStepper.pack_start(self.checkbuttonBuildReverse, expand=False, fill=False)
		self.checkbuttonBuildReverse.show()
		# GCode entry.
	#	self.entryBuildGCode = monkeyprintGuiHelper.entry('Build platform GCode', self.settings, width=30)
	#	self.boxBuildStepper.pack_start(self.entryBuildGCode, expand=False, fill=False)
	#	self.entryBuildGCode.show()
		# Resolution.
		self.entryBuildStepAngle = monkeyprintGuiHelper.entry('buildStepAngle', self.settings, width=15)
		self.boxBuildStepper.pack_start(self.entryBuildStepAngle, expand=False, fill=False)
		self.entryBuildStepAngle.show()
		# Resolution.
		self.entryBuildMicrosteps = monkeyprintGuiHelper.entry('buildMicroStepsPerStep', self.settings, width=15)
		self.boxBuildStepper.pack_start(self.entryBuildMicrosteps, expand=False, fill=False)
		self.entryBuildMicrosteps.show()
		# Resolution.
		self.entryBuildMmPerTurn = monkeyprintGuiHelper.entry('buildMmPerTurn', self.settings, width=15)
		self.boxBuildStepper.pack_start(self.entryBuildMmPerTurn, expand=False, fill=False)
		self.entryBuildMmPerTurn.show()
		# Ramp slope.
		#self.entryBuildRampSlope = monkeyprintGuiHelper.entry('buildRampSlope', self.settings, width=15)
		#self.boxBuildStepper.pack_start(self.entryBuildRampSlope, expand=False, fill=False)
		#self.entryBuildRampSlope.show()
		# Build speed.
		#self.entryBuildSpeed = monkeyprintGuiHelper.entry('buildPlatformSpeed', self.settings, width=15)
		#self.boxBuildStepper.pack_start(self.entryBuildSpeed, expand=False, fill=False)
		#self.entryBuildSpeed.show()

		# Frame for shutter servo.
		self.frameShutterServo = gtk.Frame('Shutter servo')
		boxMotionSettings.pack_start(self.frameShutterServo, expand=False, fill=False, padding=5)
		self.frameShutterServo.show()
		self.boxShutterServo = gtk.VBox()
		self.frameShutterServo.add(self.boxShutterServo)
		self.boxShutterServo.show()
		# Entries.
		# Enable?
		self.checkbuttonShutter = monkeyprintGuiHelper.toggleButton(string="enableShutterServo", settings=self.settings, modelCollection=None, customFunctions=[self.setShutterSensitive])#, displayString="Enable shutter servo?")
		self.boxShutterServo.pack_start(self.checkbuttonShutter, expand=False, fill=False)
		self.checkbuttonShutter.show()
		# G-Code entry.
	#	self.entryShutterOpenGCode = monkeyprintGuiHelper.entry('Shutter open GCode', self.settings, width=30)
	#	self.boxShutterServo.pack_start(self.entryShutterOpenGCode, expand=False, fill=False)
	#	self.entryShutterOpenGCode.show()
		# G-Code entry.
	#	self.entryShutterCloseGCode = monkeyprintGuiHelper.entry('Shutter close GCode', self.settings, width=30)
	#	self.boxShutterServo.pack_start(self.entryShutterCloseGCode, expand=False, fill=False)
	#	self.entryShutterCloseGCode.show()
		# G-Code open position.
	#	self.entryShutterPositionOpenGCode = monkeyprintGuiHelper.entry('Shutter position open GCode', self.settings, width=15, displayString='Shutter position open')
	#	self.boxShutterServo.pack_start(self.entryShutterPositionOpenGCode, expand=False, fill=False)
	#	self.entryShutterPositionOpenGCode.show()
		# G-Code closed position.
	#	self.entryShutterPositionClosedGCode = monkeyprintGuiHelper.entry('Shutter position closed GCode', self.settings, width=15, displayString='Shutter position closed')
	#	self.boxShutterServo.pack_start(self.entryShutterPositionClosedGCode, expand=False, fill=False)
	#	self.entryShutterPositionClosedGCode.show()
		# Open position.
		self.entryShutterPositionOpen = monkeyprintGuiHelper.entry('shutterPositionOpen', self.settings, width=15)#, displayString='Shutter position open')
		self.boxShutterServo.pack_start(self.entryShutterPositionOpen, expand=False, fill=False)
		self.entryShutterPositionOpen.show()
		# Closed position.
		self.entryShutterPositionClosed = monkeyprintGuiHelper.entry('shutterPositionClosed', self.settings, width=15)#, displayString='Shutter position closed')
		self.boxShutterServo.pack_start(self.entryShutterPositionClosed, expand=False, fill=False)
		self.entryShutterPositionClosed.show()
		# Set sensitivities.
		self.setShutterSensitive()


		boxMotionSettings.show()
		return boxMotionSettings




	def createPrintProcessTab(self):

		boxPrintProcessSettings = gtk.VBox()
		self.listViewModules = modulesListView(self.settings, parentWindow=self)
		boxPrintProcessSettings.pack_start(self.listViewModules, expand=True, fill=True, padding=5)
		self.listViewModules.show()

	#	boxPrintProcessSettings.show()
		return boxPrintProcessSettings




	def toggleGCodeEntries(self):
		# If G-Code is used:
		if not self.settings['monkeyprintBoard'].value:
			self.entryBaudGCode.show()
			self.entryBaud.hide()
			# Hide monkeyprint entries.
			self.entryTiltAngle.hide()
			self.entryTiltMicrostepping.hide()
			self.entryTiltStepAngle.hide()
			#self.entryBuildSpeed.hide()
			self.entryBuildMmPerTurn.hide()
			self.entryBuildMicrosteps.hide()
			#self.entryBuildRampSlope.hide()
			self.entryBuildStepAngle.hide()
			self.entryShutterPositionClosed.hide()
			self.entryShutterPositionOpen.hide()
			# Show GCode entries.
		#	self.entryTiltGCode.show()
		#	self.entryTiltDistanceGCode.show()
		#	self.entryBuildGCode.show()
		#	self.entryShutterPositionOpenGCode.show()
		#	self.entryShutterPositionClosedGCode.show()
			self.entryProjectorPort.show()
			self.entryProjectorBaud.show()
			self.checkbuttonProjectorControl.hide()
		#	self.entryShutterCloseGCode.show()
		#	self.entryShutterOpenGCode.show()
		#	self.checkbuttonShutter.hide()
			self.tabMotionSettings.hide()
		# If Monkeyprint board is used:
		else:
			self.entryBaudGCode.hide()
			self.entryBaud.show()
			# Show monkeyprint entries.
			self.entryTiltAngle.show()
			self.entryTiltMicrostepping.show()
			self.entryTiltStepAngle.show()
			#self.entryBuildSpeed.show()
			self.entryBuildMmPerTurn.show()
			self.entryBuildMicrosteps.show()
			#self.entryBuildRampSlope.show()
			self.entryBuildStepAngle.show()
			self.entryShutterPositionClosed.show()
			self.entryShutterPositionOpen.show()
			# Hide GCode entries.
	#		self.entryTiltGCode.hide()
	#		self.entryTiltDistanceGCode.hide()
	#		self.entryBuildGCode.hide()
	#		self.entryShutterPositionOpenGCode.hide()
	#		self.entryShutterPositionClosedGCode.hide()
	#		self.entryShutterCloseGCode.hide()
	#		self.entryShutterOpenGCode.hide()
			self.tabMotionSettings.show()
			self.checkbuttonProjectorControl.show()
			self.entryProjectorPort.hide()
			self.entryProjectorBaud.hide()
		# Update the print process views.
		self.listViewModules.updateModuleListModel()
		self.listViewModules.updatePrintProcessListModel()


	def callbackRaspiToggle(self, widget, data=None):
		self.settings['printOnRaspberry'].value = self.radioButtonRaspiOn.get_active()
		if self.settings['printOnRaspberry'].value == True:
			try:
				self.boxSerialUsb.set_sensitive(False)
				self.boxSerialPi.set_sensitive(True)
				self.boxNetworkPi.set_sensitive(True)
			except AttributeError:
				pass
		else:
			try:
				self.boxSerialUsb.set_sensitive(True)
				self.boxSerialPi.set_sensitive(False)
				self.boxNetworkPi.set_sensitive(False)
			except AttributeError:
				pass

	def callbackBoardToggle(self, widget, data=None):
		self.settings['monkeyprintBoard'].value = self.radioButtonMonkeyprintBoardOn.get_active()
		if self.settings['monkeyprintBoard'].value == True:
			try:
				print "Using Monkeyprint board."
				self.toggleGCodeEntries()
				#TODO: make motion tab change to monkeyprint controls.
			except AttributeError:
				pass
		else:
			try:
				self.toggleGCodeEntries()
				print "Using G-Code based board."
				#TODO: make motion tab change to GCode controls.
			except AttributeError:
				pass

		'''
		# Horizontal box for columns.
		self.boxSettings = gtk.HBox()
		self.boxMain.pack_start(self.boxSettings)
		self.boxSettings.show()

		# Vertical box for column 1.
		self.boxCol1 = gtk.VBox()
		self.boxSettings.pack_start(self.boxCol1, padding=5)
		self.boxCol1.show()

		# Frame for serial settings.
		self.frameSerial = gtk.Frame('Serial communication')
		self.boxCol1.pack_start(self.frameSerial, padding=5)
		self.frameSerial.show()
		self.boxSerial = gtk.VBox()
		self.frameSerial.add(self.boxSerial)
		self.boxSerial.show()
		# Add entries.
		# Port.
		self.entryPort = monkeyprintGuiHelper.entry('Port', self.settings, width=15)
		self.boxSerial.pack_start(self.entryPort)
		self.entryPort.show()
		# Baud rate.
		self.entryBaud = monkeyprintGuiHelper.entry('Baud rate', self.settings, width=15)
		self.boxSerial.pack_start(self.entryBaud)
		self.entryBaud.show()
		# Test button and output for serial communication.
		# Console.
		self.consoleViewSerial = monkeyprintGuiHelper.consoleView(self.consoleSerial)
		self.boxSerial.pack_start(self.consoleViewSerial, expand=True, fill=True)
		self.consoleViewSerial.show()
		# Box for button and text output.
		self.boxSerialTest = gtk.HBox()
		self.boxSerial.pack_start(self.boxSerialTest)
		self.boxSerialTest.show()
		# Button connect.
		self.buttonSerialTest = gtk.Button("Test serial")
		self.boxSerialTest.pack_end(self.buttonSerialTest, expand=False, fill=False)
		self.buttonSerialTest.connect("clicked", self.callbackSerialTest)
		self.buttonSerialTest.show()
		# Button ping.
#		self.buttonSerialPing = gtk.Button("Connect")
#		self.boxSerialTest.pack_start(self.buttonSerialPing, expand=False, fill=False)
#		self.buttonSerialPing.connect("clicked", self.callbackSerialPing)
#		self.buttonSerialPing.show()
		# Text entry to show connection test result.
	#	self.textOutputSerialTest = gtk.Entry()
	#	self.boxSerialTest.pack_start(self.textOutputSerialTest, expand=False, fill=False)
	#	self.textOutputSerialTest.show()
		'''


	# Tilt enable function.
	def setTiltSensitive(self):
		self.checkbuttonTiltReverse.set_sensitive(self.settings['tiltEnable'].value)
		self.entryTiltStepAngle.set_sensitive(self.settings['tiltEnable'].value)
		self.entryTiltMicrostepping.set_sensitive(self.settings['tiltEnable'].value)
		self.entryTiltAngle.set_sensitive(self.settings['tiltEnable'].value)
	#	self.entryTiltGCode.set_sensitive(self.settings['tiltEnable'].value)
	#	self.entryTiltDistanceGCode.set_sensitive(self.settings['tiltEnable'].value)

	def setShutterSensitive(self):
		self.entryShutterPositionOpen.set_sensitive(self.settings['enableShutterServo'].value)
		self.entryShutterPositionClosed.set_sensitive(self.settings['enableShutterServo'].value)
	#	self.entryShutterPositionOpenGCode.set_sensitive(self.settings['enableShutterServo'].value)
	#	self.entryShutterPositionClosedGCode.set_sensitive(self.settings['enableShutterServo'].value)
	#	self.entryShutterCloseGCode.set_sensitive(self.settings['enableShutterServo'].value)
	#	self.entryShutterOpenGCode.set_sensitive(self.settings['enableShutterServo'].value)


	# Serial connect function.
	def callbackSerialTest(self, widget, data=None):
		# Create communication queues.
		self.queueSerial = Queue.Queue()
		queueSerialCommands = Queue.Queue()
		self.command = ["ping", None, True, None]	# No value, retry, don't wait.
		# Make button insensitive.
		self.buttonSerialTest.set_sensitive(False)
		self.buttonSerialTest.set_label("    Wait...    ")
		self.consoleSerial.addLine("Connecting...")
		# Start queue listener.
		listenerIdSerial = gobject.timeout_add(500, self.listenerSerialThread)
		self.serial = monkeyprintSerial.printer(self.settings, self.queueSerial, queueSerialCommands)
		# Send ping.
		if self.serial.serial != None:
			self.serial.send(self.command)


	def listenerSerialThread(self):
		# If a message is in the queue...
		if self.queueSerial.qsize():
			# Get the message and display it.
			message = self.queueSerial.get()
			self.consoleSerial.addLine(message)
			self.consoleSerial.addLine("")
			# Check if the message was the end message.
			if message == "Command \"" + self.command[0] + "\" sent successfully." or message == "Printer not responding. Giving up...":
				# Restore send button.
				self.buttonSerialTest.set_sensitive(True)
				self.buttonSerialTest.set_label("Test serial")
				# Close and delete serial.
				self.serial.stop()
				self.serial.close()
				del self.serial
				# Return False to remove listener from timeout.
				return False
			else:
				return True
		else:
			# Add a dot to the console to let people know the program is not blocked...
			self.consoleSerial.addString(".")
			# Return True to keep listener in timeout.
			return True

	def callbackDebug(self, widget, data=None):
		self.settings['debug'].value = str(self.checkboxDebug.get_active())

	def callbackProjectorControl(self, data=None):
		self.settings['Projector control'].value = self.checkbuttonProjectorControl.get_active()
		self.entryProjectorOnCommand.set_sensitive(self.settings['Projector control'].value)
		self.entryProjectorOffCommand.set_sensitive(self.settings['Projector control'].value)
	#	self.entryProjectorPort.set_sensitive(self.settings['Projector control'].value)
	#	self.entryProjectorBaud.set_sensitive(self.settings['Projector control'].value)

	# Defaults function.
	def callbackDefaults(self, widget, data=None):
		# Load default settings.
		self.settings.loadDefaults()
		self.imageContainer.updateImage()

	# Cancel function.
#	def callbackCancel(self, widget, data=None):
#		# Restore values.
#		print ("Before: " + str(self.settingsBackup['calibrationImage'].value))
#		self.settings = self.settingsBackup
#		print ("After: " + str(self.settings['calibrationImage'].value))
#		# Delete the calibration image in case it was just added.
#		if (self.settings['calibrationImage'].value == False): self.imageContainer.deleteImageFile()
#		# Close with old values restored.
#		self.destroy()

	# Destroy function.
	def callbackClose(self, widget, data=None):
		# Delete the calibration image in case it was just added.
		if (self.settings['calibrationImage'].value == False):
			self.imageContainer.deleteImageFile()
		# Restart the file transmission thread.
		if self.settings['printOnRaspberry'].value:
			ipFileClient = self.settings['ipAddressRaspi'].value
			portFileClient = self.settings['fileTransmissionPortRaspi'].value
			if self.parentWindow.threadFileTransmission != None:
				self.parentWindow.threadFileTransmission.join(100)
				self.parentWindow.threadFileTransmission.reset(ipFileClient, portFileClient)
				self.parentWindow.threadFileTransmission.run()

		# Restart the communication socket.
		if self.settings['printOnRaspberry'].value:
			ipCommClient = self.settings['ipAddressRaspi'].value
			portCommClient = self.settings['networkPortRaspi'].value
			self.parentWindow.socket.reset(ipCommClient, portCommClient)

		# Set print process modules to settings.
		self.settings.setPrintProcessList(self.listViewModules.getPrintProcessList())

		# Set print resolution.
		self.settings['pxPerMm'].value = self.settings['projectorSizeX'].value / self.settings['buildSizeX'].value

		# Update parent window in response to changing boards.
		self.parentWindow.updateAllModels()
		self.parentWindow.updateAllEntries(render=True)

		# Close.
		self.destroy()






# Model list. ##################################################################
class modulesListView(gtk.HBox):
	def __init__(self, settings, parentWindow, console=None):

		# Init super class.
		gtk.HBox.__init__(self)
		self.show()

		# Internalise settings.
		self.settings = settings
		self.console = console
		self.parentWindow = parentWindow

		# Frame for print process.
		self.framePrintProcess = gtk.Frame('Print process')
		self.pack_start(self.framePrintProcess, expand=True, fill=True, padding=5)
		self.framePrintProcess.show()

		# Create the print process scrolled window.
		self.boxPrintProcess = gtk.VBox()
		self.framePrintProcess.add(self.boxPrintProcess)
		self.boxPrintProcess.show()
		self.scrolledWindowPrintProcess = gtk.ScrolledWindow()
		self.scrolledWindowPrintProcess.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.boxPrintProcess.pack_start(self.scrolledWindowPrintProcess, expand=True, fill=True, padding = 5)
		self.scrolledWindowPrintProcess.show()
		# Create view for model list.
		self.viewPrintProcess = gtk.TreeView()
		# Create model for print process view.
		self.printProcessListModel = gtk.ListStore(str,str,str,str,bool)
		self.updatePrintProcessListModel()
		self.viewPrintProcess.show()
	#	self.viewPrintProcess.set_headers_visible(False)	# Make column invisible.
		self.viewPrintProcess.set_headers_clickable(False)
		self.viewPrintProcess.set_reorderable(False)
		self.scrolledWindowPrintProcess.add(self.viewPrintProcess)
		# Add model name column and respective text cell renderer.
		self.columnModelPrintProcess = gtk.TreeViewColumn('Module')
		self.viewPrintProcess.append_column(self.columnModelPrintProcess)
		self.cellModelPrintProcess = gtk.CellRendererText()
	#	self.cellModelPrintProcess.set_property('editable', True)
	#	self.cellModelPrintProcess.connect('edited', self.callbackPrintProcessNameEdited, self.printProcessListModel)
		self.columnModelPrintProcess.pack_start(self.cellModelPrintProcess, True)
		self.columnModelPrintProcess.add_attribute(self.cellModelPrintProcess, 'text', 0)
	#	self.columnModelPrintProcess.set_sort_column_id(0)
		# Add active? column and respective toggle cell renderer.
		self.columnValuePrintProcess = gtk.TreeViewColumn('Value')
		self.viewPrintProcess.append_column(self.columnValuePrintProcess)
		self.cellValuePrintProcess = gtk.CellRendererText()
	#	self.cellValuePrintProcess.set_property('editable', True)
	#	self.cellValuePrintProcess.connect('edited', self.callbackPrintProcessValueEdited, self.printProcessListModel)
		self.columnValuePrintProcess.pack_start(self.cellValuePrintProcess, False)
		self.columnValuePrintProcess.add_attribute(self.cellValuePrintProcess, 'text', 1)
	#	self.columnValuePrintProcess.set_sort_column_id(3)

		# Create button box that goes below print process list view.
		self.boxButtons = gtk.HBox()
		self.boxPrintProcess.pack_start(self.boxButtons, expand=False, fill=False, padding=5)
		self.boxButtons.show()

		# Create drop down menu with available modules list.
		self.dropdownModulesSimple = gtk.combo_box_new_text()
		self.boxButtons.pack_start(self.dropdownModulesSimple, True, True, padding=5)
		self.dropdownModulesSimple.connect('changed',self.callbackModuleDropdownSelectionChanged)
		# Create the list model for the dropdown combo box.
		self.moduleListModel = gtk.ListStore(str,str,str,str,bool)
		self.updateModuleListModel()
		# Set first item active.
		self.dropdownModulesSimple.set_active(0)
		self.dropdownModulesSimple.show()

		# Create buttons.
		# Add button.
		self.buttonAdd = gtk.Button("Add")
		self.boxButtons.pack_start(self.buttonAdd, expand=True, fill=True, padding=5)
		self.buttonAdd.show()
		self.buttonAdd.connect("clicked", self.callbackPrintProcessAdd)
		# Edit button.
		self.buttonEdit = gtk.Button("Edit")
		self.boxButtons.pack_start(self.buttonEdit)
		self.buttonEdit.set_sensitive(False)
		self.buttonEdit.show()
		self.buttonEdit.connect("clicked", self.callbackPrintProcessEdit)
		# Up button.
		self.buttonUp = gtk.Button(u'\u2191')
		self.boxButtons.pack_start(self.buttonUp, expand=True, fill=True, padding=5)
		if len(self.printProcessListModel) == 0:
			self.buttonUp.set_sensitive(False)
		self.buttonUp.show()
		self.buttonUp.connect("clicked", self.callbackPrintProcessUp)
		# Down button.
		self.buttonDown = gtk.Button(u'\u2193')
		self.boxButtons.pack_start(self.buttonDown, expand=True, fill=True, padding=5)
		if len(self.printProcessListModel) == 0:
			self.buttonDown.set_sensitive(False)
		self.buttonDown.show()
		self.buttonDown.connect("clicked", self.callbackPrintProcessDown)
		# Remove button.
		self.buttonRemove = gtk.Button("Remove")
		self.boxButtons.pack_start(self.buttonRemove, expand=True, fill=True, padding=5)
		if len(self.printProcessListModel) == 0:
			self.buttonRemove.set_sensitive(False)
		self.buttonRemove.show()
		self.buttonRemove.connect("clicked", self.callbackPrintProcessRemove)

		# Create item selection.
		self.printProcessModuleSelection = self.viewPrintProcess.get_selection()
		# Avoid multiple selection.
		self.printProcessModuleSelection.set_mode(gtk.SELECTION_SINGLE)
		# Connect to selection change event function.
		self.printProcessModuleSelection.connect('changed', self.onSelectionChangedPrintProcess)
		# Select first item.
		self.printProcessModuleSelection.select_iter(self.printProcessListModel.get_iter_first())



	# Update list model for dropdown.
	def updateModuleListModel(self):
		# Get module list from settings.
		model = gtk.ListStore(str,str,str,str,bool)
		moduleList = self.settings.getModuleList()
		for row in moduleList:
			model.append(row)
		self.moduleListModel = model
		self.dropdownModulesSimple.set_model(self.moduleListModel)


	# Update list model for print process list.
	def updatePrintProcessListModel(self):
		# Get module list from settings.
		model = gtk.ListStore(str,str,str,str,bool)
		moduleList = self.settings.getPrintProcessList()
		for row in moduleList:
			model.append(row)
		self.printProcessListModel = model
		self.viewPrintProcess.set_model(self.printProcessListModel)


	def getPrintProcessList(self):
		moduleList = []
		for row in self.printProcessListModel:
			rowList = []
			for item in row:
				rowList.append(item)
			moduleList.append(rowList)
		return moduleList


	def callbackModuleDropdownSelectionChanged(self, combobox):
		pass # Noting happening here...
		#print self.dropdownModulesSimple.get_active()


	# Insert the module selected in drop down into the print process list.
	def callbackPrintProcessAdd(self, widget, data=None):
		# Get selected iter.
		model, treeiter = self.printProcessModuleSelection.get_selected()
		# Get item to add.
		item = self.dropdownModulesSimple.get_active()
		if item >= 0:
			# If list is not empty...
			if treeiter != None:
				#... insert after selected iter.
				path = self.printProcessListModel.get_path(treeiter)
				newIter = self.printProcessListModel.insert(path[0]+1, self.moduleListModel[item])
			# If list is empty...
			else:
				#... append item.
				newIter = self.printProcessListModel.append(self.moduleListModel[item])
			self.printProcessModuleSelection.select_iter(newIter)


	# Delete the selected module from the print process list.
	def callbackPrintProcessRemove(self, widget, data=None):
		model, treeiter = self.printProcessModuleSelection.get_selected()
		# Get the path of the current iter.
		if len(self.printProcessListModel) > 0:
			currentPath = self.printProcessListModel.get_path(treeiter)[0]
			deletePath = currentPath
			# Check what to select next.
			# If current selection at end of list but not the last element remaining...
			if currentPath == len(self.printProcessListModel) - 1 and len(self.printProcessListModel) > 1:
				# ... select the previous item.
				currentPath -= 1
				self.printProcessModuleSelection.select_path(currentPath)
			# If current selection is somewhere in the middle...
			elif currentPath < len(self.printProcessListModel) - 1 and len(self.printProcessListModel) > 1:
				# ... selected the next item.
				currentPath += 1
				self.printProcessModuleSelection.select_path(currentPath)
		# Remove the item and check if there's a next item.
		iterValid = self.printProcessListModel.remove(treeiter)
		# Set button sensitivities.
		self.setButtonSensitivities()


	def callbackPrintProcessEdit(self, widget, data=None):
		model, treeiter = self.printProcessModuleSelection.get_selected()
		if treeiter != None:
			editDialog = dialogEditPrintModule(parent=self.parentWindow, modelItem=model[treeiter])
			editedModelItem = editDialog.run()
			editDialog.destroy()
			model[treeiter] = editedModelItem


	def callbackPrintProcessUp(self, widget, data=None):
		# Get iter of selected item and previous item.
		model, treeiter = self.printProcessModuleSelection.get_selected()
		path = model.get_path(treeiter)[0]
		pathPrevious = path - 1
		treeiterPrevious = model.get_iter(pathPrevious)
		# Swap items.
		model.swap(treeiter, treeiterPrevious)
		# Reset sensitivities manually.
		self.setButtonSensitivities()


	def callbackPrintProcessDown(self, widget, data=None):
		# Get iter of selected item and next item.
		model, treeiter = self.printProcessModuleSelection.get_selected()
		path = model.get_path(treeiter)[0]
		pathNext = path + 1
		treeiterNext = model.get_iter(pathNext)
		# Swap the items.
		model.swap(treeiter, treeiterNext)
		# Reset sensitivities manually.
		self.setButtonSensitivities()


	# Selection changed callback.
	def onSelectionChangedPrintProcess(self, selection):
		# Get selected iter.
		model, treeIter = selection.get_selected()
		# If iter is valid...
		if treeIter != None:
			# Handle button sensitivities.
			self.setButtonSensitivities()
		# If iter is not valid (nothing selected) but list is not empty...
		elif len(model) > 0:
			# ... select first item.
			self.printProcessModuleSelection.select_iter(model.get_iter(0)) # Does this invoke selection change event?


	def setButtonSensitivities(self):
		model, treeiter = self.printProcessModuleSelection.get_selected()
		if treeiter != None:
			# Add button is always sensitive.
			# Set edit button sensitivity.
			self.buttonEdit.set_sensitive(len(model)>0 and model[treeiter][-1])
			# Set remove button sensitivity.
			# Set up button sensitivity.
			self.buttonUp.set_sensitive(model.get_path(treeiter)[0] != 0 and len(model) > 1)
			# Set down button sensitivity.
			self.buttonDown.set_sensitive(model.get_path(treeiter)[0] != len(model)-1 and len(model) > 1)
			# Set remove button sensitivity.
			self.buttonRemove.set_sensitive(len(model)>0)
		else:
			self.buttonEdit.set_sensitive(False)
			self.buttonUp.set_sensitive(False)
			self.buttonDown.set_sensitive(False)
			self.buttonRemove.set_sensitive(False)



class dialogEditPrintModule(gtk.Window):
	# Override init function.
	def __init__(self, parent, modelItem):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
#		self.show()
		# Set title.
		self.set_title("Edit print module")
		# Set modal.
		self.set_modal(True)
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
		self.set_transient_for(parent)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.set_default_size(10,10) # Window was too large, so let's make it small and resize by content.
		self.show()

		self.modelItem = modelItem

		self.mainBox = gtk.VBox()
		self.add(self.mainBox)
		self.mainBox.show()

		# Add a short explanation.
		self.labelExplanation = gtk.Label()
		if modelItem[0] == 'Wait':
			self.labelExplanation.set_text('Enter the wait interval in seconds.')
		elif modelItem[3] == 'serialGCode':
			self.labelExplanation.set_text('Enter a name and the G-Code command.')
		self.mainBox.pack_start(self.labelExplanation, expand=False, fill=False, padding=5)
		self.labelExplanation.show()

		# Create the text fields.
		self.entryBoxName = gtk.HBox()
		self.mainBox.pack_start(self.entryBoxName, expand=False, fill=False, padding=5)
		self.entryBoxName.show()
		self.entryBoxValue = gtk.HBox()
		self.mainBox.pack_start(self.entryBoxValue, expand=False, fill=False, padding=5)
		self.entryBoxValue.show()

		self.labelName = gtk.Label('Name')
		self.entryBoxName.pack_start(self.labelName, expand=False, fill=False, padding=5)
		self.entryName = gtk.Entry()
		self.entryName.set_width_chars(50)
		self.entryName.set_text(self.modelItem[0])
		self.entryBoxName.pack_start(self.entryName, expand=False, fill=False, padding=5)

		if modelItem[3] == 'serialGCode':
			self.labelName.show()
			self.entryName.show()

		self.labelValue = gtk.Label('Value')
		self.entryBoxValue.pack_start(self.labelValue, expand=False, fill=False, padding=5)
		self.labelValue.show()

		self.entryValue = gtk.Entry()
		self.entryValue.set_width_chars(50)
		self.entryValue.set_text(self.modelItem[1])
		self.entryBoxValue.pack_start(self.entryValue, expand=False, fill=False, padding=5)
		self.entryValue.show()

		# OK and cancel buttons.
		self.boxButtons = gtk.HBox()
		self.mainBox.pack_start(self.boxButtons, expand=False, fill=False, padding=5)
		self.boxButtons.show()
		# Cancel button.
		self.buttonCancel = gtk.Button('Cancel')
		self.boxButtons.pack_start(self.buttonCancel, expand=True, fill=True, padding=5)
		self.buttonCancel.show()
		self.buttonCancel.connect('clicked', self.callbackCancel)
		# OK button.
		self.buttonOK = gtk.Button('OK')
		self.boxButtons.pack_start(self.buttonOK, expand=True, fill=True, padding=5)
		self.buttonOK.show()
		self.buttonOK.connect('clicked', self.callbackOK)


	def callbackOK(self, data=None):
		if self.modelItem[0] == 'Wait':
			try:
				number=float(self.entryValue.get_text())
			except ValueError:
				number=1.0
			self.modelItem[1] = str(number)
		else:
			self.modelItem[0] = self.entryName.get_text()
			self.modelItem[1] = self.entryValue.get_text()
		self.hide()
		gtk.mainquit()

	def callbackCancel(self, data=None):
		self.hide()
		gtk.mainquit()

	# Create run function to start own main loop.
	# This will wait for button events from the current window.
	def run(self):
		gtk.mainloop()
		return self.modelItem

	# Override destroy function.
	def destroy(self):
		del self




# Start print dialogue. ########################################################
# Start the dialog, evaluate the check boxes on press of OK and exit,
# or just exit on cancel.
class dialogStartPrint(gtk.Window):
	# Override init function.
	def __init__(self, parent):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
#		self.show()
		# Set title.
		self.set_title("Ready to print?")
		# Set modal.
		self.set_modal(True)
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
		self.set_transient_for(parent)
		self.set_type_hint(gtk.gdk.WINDOW_TYPE_HINT_DIALOG)
		self.show()

		self.result = False
		# Create check buttons.
		self.boxCheckbuttons = gtk.VBox()
		self.add(self.boxCheckbuttons)
		self.boxCheckbuttons.show()
		# Checkbutton resin.
		self.checkboxResin = gtk.CheckButton(label="VAT filled with resin?")
		self.boxCheckbuttons.pack_start(self.checkboxResin, expand=True, fill=True)
		self.checkboxResin.set_active(False)
		self.checkboxResin.show()
		# Checkbutton build platform.
		self.checkboxBuild = gtk.CheckButton(label="Build platform empty?")
		self.boxCheckbuttons.pack_start(self.checkboxBuild, expand=True, fill=True)
		self.checkboxBuild.set_active(False)
		self.checkboxBuild.show()
		# Checkbutton 3rd condition.
		self.checkboxCustom = gtk.CheckButton(label="Everything else OK?")
		self.boxCheckbuttons.pack_start(self.checkboxCustom, expand=True, fill=True)
		self.checkboxCustom.set_active(False)
		self.checkboxCustom.show()

		# Create OK and Cancel button.
		self.buttonBox = gtk.HBox()
		self.boxCheckbuttons.pack_start(self.buttonBox, expand=False, fill=False)
		self.buttonBox.show()
		self.buttonCancel = gtk.Button("Cancel")
		self.buttonBox.pack_start(self.buttonCancel)
		self.buttonCancel.show()

		self.buttonOK = gtk.Button("OK")
		self.buttonOK.set_sensitive(False)
		self.buttonBox.pack_start(self.buttonOK)
		self.buttonOK.show()


		# Set callbacks
		self.buttonOK.connect("clicked", self.callbackOK)
		self.buttonCancel.connect("clicked", self.callbackCancel)
		self.checkboxCustom.connect("toggled", self.checkboxCallback)
		self.checkboxBuild.connect("toggled", self.checkboxCallback)
		self.checkboxResin.connect("toggled", self.checkboxCallback)

	def checkboxCallback(self, data=None):
		if self.checkboxResin.get_active() and self.checkboxBuild.get_active() and self.checkboxCustom.get_active():
			self.buttonOK.set_sensitive(True)
		else:
			self.buttonOK.set_sensitive(False)

	def callbackOK(self, data=None):
		self.result=True
		self.hide()
		gtk.mainquit()

	def callbackCancel(self, data=None):
		self.result=False
		self.hide()
		gtk.mainquit()

	# Create run function to start own main loop.
	# This will wait for button events from the current window.
	def run(self):
		self.set_transient_for(self.parent)
		self.show()
		gtk.mainloop()
		return self.result






