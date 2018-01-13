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

# New imports for QT.
import signal
import sys

import PyQt4
from PyQt4 import QtGui, QtCore, Qt
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor


################################################################################
# Define a class for standalone without main GUI. ##############################
################################################################################
# Inherit from projector display window.
'''
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
		self.printRunning = True
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
				self.printRunning = False
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

'''


################################################################################
# Define a class for the main GUI. #############################################
################################################################################
class gui(QtGui.QApplication):

	# *************************************************************************
	# Override init function. *************************************************
	# *************************************************************************
	def __init__(self, modelCollection, programSettings, console=None, filename=None, *args, **kwargs):

		# Call super class function.
		super(gui, self).__init__(sys.argv)

		# Connect close event.
		#self.aboutToQuit.connect(self.onClose)

		# Internalise parameters.
		self.modelCollection = modelCollection
		self.programSettings = programSettings
		self.console = console

		# Create signal for Strg+C TODO: check out why this works.
		signal.signal(signal.SIGINT, signal.SIG_DFL)

		# Flag to set during print process.
		self.printRunning = False
		self.slicerRunning = False

		# Create queues for inter-thread communication.
		# Queue for setting print progess bar.
		self.queueSliceOut  = Queue.Queue(maxsize=1)
		self.queueSliceIn = Queue.Queue(maxsize=1)
		self.slicerFinished = False
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


		# Get current working directory and set paths.
		self.cwd = os.getcwd()
		self.programSettings['localMkpPath'].value = self.cwd + "/currentPrint.mkp"



		# ********************************************************************
		# Add thread listener functions to run every n ms.********************
		# ********************************************************************
		# Check if the slicer threads and/or slice combiner thread have finished. Needed in model collection.
		#self.timerSlicerListener = QtCore.QTimer()
		#self.timerSlicerListener.timeout.connect(self.modelCollection.checkSlicer)
		#self.timerSlicerListener.start(100)
		# Check if slicer has finished. Needed to update slice preview.
		self.timerSlicePreviewUpdater = QtCore.QTimer()
		self.timerSlicePreviewUpdater.timeout.connect(self.checkSlicer)#self.updateSlicerStatus)
		self.timerSlicePreviewUpdater.start(100)
		# Update the progress bar, projector image and 3d view during prints.
		self.timerPrintQueueListener = QtCore.QTimer()
		self.timerPrintQueueListener.timeout.connect(self.checkPrintQueues)
		self.timerPrintQueueListener.start(50)
		# Request status info from raspberry pi.
	#	pollRasPiConnectionId = gobject.timeout_add(500, self.pollRasPiConnection)
		# Request status info from slicer.
		#pollSlicerStatusId = gobject.timeout_add(100, self.pollSlicerStatus)
		# TODO: combine this with slicerListener.





		# ********************************************************************
		# Create the main GUI. ***********************************************
		# ********************************************************************
		#The Main window
		self.mainWindow = monkeyprintGuiHelper.mainWindow(self.checkPrinterRunning)
		self.mainWindow.showMaximized()
		self.centralWidget = QtGui.QWidget()
		self.mainWindow.setCentralWidget(self.centralWidget)

		# Create main box inside of window. This will hold the menu bar and the rest.
		self.boxMain = QtGui.QHBoxLayout()
		self.centralWidget.setLayout(self.boxMain)

		# Create menu bar and pack inside main box at top.
		self.menuBar = self.createMenuBar()#menuBar(self.programSettings, self.on_closing)
		#self.boxMain.addWidget(self.menuBar)
	#	self.boxMain.pack_start(self.menuBar, expand=False, fill=False)
	#	self.menuBar.show()

		# Create render box and pack inside work area box.
		self.renderView = monkeyprintModelViewer.renderView(self.programSettings)
		#self.renderView.show()
		self.boxMain.addWidget(self.renderView)
		self.renderView.renderWindowInteractor.Initialize()

		# Create settings box.
		widgetSettings = QtGui.QWidget()
		widgetSettings.setFixedWidth(250)
		self.boxMain.addWidget(widgetSettings)
		self.boxSettings =self.createSettingsBox()
		widgetSettings.setLayout(self.boxSettings)


		# Update.
		self.updateAllEntries()


	#	self.createButtons()
		self.mainWindow.show()
		self.mainWindow.raise_()


	def checkPrinterRunning(self):
		return self.printRunning

	# *************************************************************************
	# Function that updates all relevant GUI elements during prints. **********
	# *************************************************************************
	# This runs every 100 ms as a gobject timeout function.
	# Updates 3d view and projector view. Also forwards status info.
	def checkPrintQueues(self):
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
					self.printRunning = False
					del self.printProcess
					self.projectorDisplay.destroy()
					del self.projectorDisplay
					# Remove print file.
					if os.path.isfile(self.localPath + self.localFilename):
						os.remove(self.localPath + self.localFilename)
				# If not running on Raspberry Pi, destroy projector display and reset GUI.
				else:
					self.buttonPrintStart.setEnabled(True)
					self.buttonPrintStop.setEnabled(False)
					self.modelCollection.updateAllSlices3d(0)
					self.renderView.render()
					self.progressBar.updateValue(0)
					self.printRunning = False
					print "foo"
					del self.printProcess
					self.projectorDisplay.destroy()
					del self.projectorDisplay
					print "bar"
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
				if self.printRunning:
					pass
					# TODO: Send error message.
					#zmq_socket.send_multipart(["error", "Print running already."])
				else:
					# Start the print.
					self.printProcessStart()
			elif command == "stop":
				print "command: stop"
				if self.printRunning:
					self.printProcessStop()
					#self.printProcess.stop()
			elif command == "pause":
				if self.printRunning:
					self.printProcess.pause()


	# *************************************************************************
	# Function to process the output of statusQueue and update the GUI. *******
	# *************************************************************************
	def processStatusMessage(self, message):
		# Split the string.
		status, param, value = message.split(":")
		# Check the status and retreive other data.
		printRunning = True
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
				if value == 1:
					self.progressBar.setText("Print stopped after " + value + " slice.")
				else:
					self.progressBar.setText("Print stopped after " + value + " slices.")
			else:
				self.progressBar.setText("Print stopped.")
			# Reset stop button to insensitive.
			self.buttonPrintStart.setEnabled(True)
			self.buttonPrintStop.setEnabled(False)
		elif status == "idle":
			if param == "slice":
				self.progressBar.updateValue(int(value))
			printRunning = False
			self.progressBar.setText("Idle.")
			# Reset gui sensitivities.
			self.setGuiState(3)
		self.printRunning = printRunning







	# **************************************************************************
	# Gui main function. *******************************************************
	# **************************************************************************
	def main(self):
		# Run the QT event loop.
		self.exec_()



	# **************************************************************************
	# Gui setup functions. *****************************************************
	# **************************************************************************

	# Create the top menu (files, settings etc). *******************************
	def createMenuBar(self):
		# TODO: check shortcuts.
		# Create menu.
		bar = self.mainWindow.menuBar()
		# Create file menu.
		menuFile = bar.addMenu("File")
		# Item load.
		menuItemLoad = QtGui.QAction("Load project",self)
		menuFile.addAction(menuItemLoad)
		# Item save.
		menuItemSave = QtGui.QAction("Save project",self)
		menuFile.addAction(menuItemSave)
		# Item close.
		menuItemClose = QtGui.QAction("Close project",self)
		menuFile.addAction(menuItemClose)
		# Item quit.
		menuItemQuit = QtGui.QAction("Quit",self)
		menuFile.addAction(menuItemQuit)
		# Create options menu.
		menuOptions = bar.addMenu("Options")
		# Item settings.
		menuItemSettings = QtGui.QAction("Settings",self)
		menuOptions.addAction(menuItemSettings)
		# Item firmware.
		menuItemFirmware = QtGui.QAction("Flash firmware",self)
		menuOptions.addAction(menuItemFirmware)
		# Item manual control.
		menuItemManualControl = QtGui.QAction("Manual control",self)
		menuOptions.addAction(menuItemManualControl)
		menuOptions.triggered[QtGui.QAction].connect(self.callbackMenuClicked)
		return bar



	# Create the main settings box next to the render view. ********************
	def createSettingsBox(self):
		# Create settings box.
		boxSettings = QtGui.QVBoxLayout()
		boxSettings.setSpacing(5)
		boxSettings.setContentsMargins(0,0,0,0)

		# Create model list view.
		# Label.
		labelModelTableView = QtGui.QLabel('<b>Models</b>')
		boxSettings.addWidget(labelModelTableView, 0, QtCore.Qt.AlignTop)
		# Table view.
		self.modelTableView = monkeyprintGuiHelper.modelTableView(self.programSettings, self.modelCollection, self.console, self)
		boxSettings.addWidget(self.modelTableView, 0)



		#boxSettings.addWidget(self.modelTableView)

		# Create settings notebook.
		self.notebookSettings = monkeyprintGuiHelper.notebook()
		self.notebookSettings.addTab(self.createSettingsModel(), 'Model')
		self.notebookSettings.addTab(self.createSettingsSupports(), 'Supports')
		self.notebookSettings.addTab(self.createSettingsSlicing(), 'Slicing')
		self.notebookSettings.addTab(self.createSettingsPrint(),'Print')

		# Add notebook to gui.
		boxSettings.addWidget(self.notebookSettings)

		# Set tab switch functions.
		self.notebookSettings.setCustomFunction(0, self.tabSwitchModelUpdate)
		self.notebookSettings.setCustomFunction(1, self.tabSwitchSupportsUpdate)
		self.notebookSettings.setCustomFunction(2, self.tabSwitchSlicesUpdate)
		self.notebookSettings.setCustomFunction(3, self.tabSwitchPrintUpdate)

		# Set gui state. This controls which tabs are clickable.**************
		# 0: Model modifications active.
		# 1: Model modifications, supports and slicing active.
		# 2: All active.
		# Use setGuiState function to set the state. Do not set manually.
		self.setGuiState(0)

		# Create output log.
		self.consoleView = monkeyprintGuiHelper.consoleView(self.console)
		boxSettings.addLayout(self.consoleView)

		return boxSettings



	# Create the model, supports, slicer and print page for the notebook. ******
	def createSettingsModel(self):

		# Create widget.
		tabSettingsModel = QtGui.QWidget()
		# Create main tab box.
		boxSettingsModel = QtGui.QVBoxLayout()
		tabSettingsModel.setLayout(boxSettingsModel)
		# Create model modifications frame.
		frameSettingsModel = QtGui.QGroupBox("Model modifications")
		frameSettingsModel.setFlat(False)
		boxSettingsModel.addWidget(frameSettingsModel)
		# Create model modifications box.
		boxModelModifications = QtGui.QVBoxLayout()
		frameSettingsModel.setLayout(boxModelModifications)

		# Create entries.
		# Scaling.
		self.entryScaling = monkeyprintGuiHelper.entry('scaling', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxModelModifications.addWidget(self.entryScaling)
		# Rotation.
		self.entryRotationX = monkeyprintGuiHelper.entry('rotationX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryRotationX)
		self.entryRotationY = monkeyprintGuiHelper.entry('rotationY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryRotationY)
		self.entryRotationZ = monkeyprintGuiHelper.entry('rotationZ', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryRotationZ)
		# Position.
		self.entryPositionX = monkeyprintGuiHelper.entry('positionX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryPositionX)
		self.entryPositionY = monkeyprintGuiHelper.entry('positionY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryPositionY)
		# Bottom clearance.
		self.entryBottomClearance = monkeyprintGuiHelper.entry('bottomClearance', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addWidget(self.entryBottomClearance)

		boxSettingsModel.addStretch()
		return tabSettingsModel



	def createSettingsSupports(self):

		# Create widget.
		tabSettingsSupports = QtGui.QWidget()
		# Create main tab box.
		boxSettingsSupports = QtGui.QVBoxLayout()
		#boxSettingsSupports.setContentsMargins(0,0,0,0)
		tabSettingsSupports.setLayout(boxSettingsSupports)

		# Create support pattern frame.
		frameSettingsSupportPattern = QtGui.QGroupBox("Support pattern")
		boxSettingsSupports.addWidget(frameSettingsSupportPattern)
		# Create support pattern box.
		boxSupportPattern = QtGui.QVBoxLayout()
		frameSettingsSupportPattern.setLayout(boxSupportPattern)

		# Create entries.
		# Overhang angle.
		self.entryOverhangAngle = monkeyprintGuiHelper.entry('overhangAngle', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addWidget(self.entryOverhangAngle, 0)
		# Spacing.
		self.entrySupportSpacingX = monkeyprintGuiHelper.entry('spacingX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addWidget(self.entrySupportSpacingX)
		self.entrySupportSpacingY = monkeyprintGuiHelper.entry('spacingY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addWidget(self.entrySupportSpacingY, 0)
		# Max height.
		self.entrySupportMaxHeight = monkeyprintGuiHelper.entry('maximumHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addWidget(self.entrySupportMaxHeight, 0)
		# Bottom plate thickness.
		self.entrySupportBottomPlateThickness = monkeyprintGuiHelper.entry('bottomPlateThickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addWidget(self.entrySupportBottomPlateThickness, 0)

		# Create support geometry frame.
		frameSettingsSupportGeo = QtGui.QGroupBox("Support geometry")
		boxSettingsSupports.addWidget(frameSettingsSupportGeo)
		# Create support geometry box.
		boxSupportGeo = QtGui.QVBoxLayout()
		frameSettingsSupportGeo.setLayout(boxSupportGeo)

		# Position.
		self.entrySupportBaseDiameter = monkeyprintGuiHelper.entry('baseDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxSupportGeo.addWidget(self.entrySupportBaseDiameter)
		self.entrySupportTipDiameter = monkeyprintGuiHelper.entry('tipDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxSupportGeo.addWidget(self.entrySupportTipDiameter)
		# Bottom clearance.
		self.entrySupportTipHeight = monkeyprintGuiHelper.entry('coneHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])

		boxSupportGeo.addWidget(self.entrySupportTipHeight)

		return tabSettingsSupports



	def createSettingsSlicing(self):

		# Create widget.
		tabSettingsSlicing = QtGui.QWidget()

		# Create main tab box.
		boxSettingsSlicing = QtGui.QVBoxLayout()
		boxSettingsSlicing.setContentsMargins(3,3,3,3)
		tabSettingsSlicing.setLayout(boxSettingsSlicing)

		# Create slicing parameters frame.
		frameSettingsSlicingParameters = QtGui.QGroupBox("Slicing parameters")
		boxSettingsSlicing.addWidget(frameSettingsSlicingParameters)
		# Create slicing parameters box.
		boxSlicingParameters = QtGui.QVBoxLayout()
		boxSlicingParameters.setContentsMargins(0,3,0,3)

		frameSettingsSlicingParameters.setLayout(boxSlicingParameters)

		# Create entries.
		# Layer height.
		self.entryLayerHeight = monkeyprintGuiHelper.entry('layerHeight', settings=self.programSettings, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries])
		boxSlicingParameters.addWidget(self.entryLayerHeight)


		# Create fill parameters frame.
		frameSettingsFillParameters = QtGui.QGroupBox("Fill parameters")
		boxSettingsSlicing.addWidget(frameSettingsFillParameters)
		# Create fill parameters box.
		boxFillParameters = QtGui.QVBoxLayout()
		boxFillParameters.setContentsMargins(0,3,0,3)
		frameSettingsFillParameters.setLayout(boxFillParameters)
		# Create fill parameters checkbox box.
		boxFillParameterToggles = QtGui.QHBoxLayout()
		boxFillParameterToggles.setContentsMargins(0,0,0,0)
		boxFillParameters.addLayout(boxFillParameterToggles)

		# Create toggle buttons.
		# Hollow.
		self.toggleButtonHollow = monkeyprintGuiHelper.toggleButton('printHollow', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack])#, self.updateSlider, self.renderView.render, self.updateAllEntries, self.updateSlicingEntries])
		boxFillParameterToggles.addWidget(self.toggleButtonHollow, 0, QtCore.Qt.AlignLeft)
		# Fill.
		self.toggleButtonFill = monkeyprintGuiHelper.toggleButton('fill', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack])#, self.updateSlider, self.renderView.render, self.updateAllEntries, self.updateSlicingEntries])
		boxFillParameterToggles.addWidget(self.toggleButtonFill, 0, QtCore.Qt.AlignLeft)

		# Create entries.
		# Position.
		self.entryFillShellThickness = monkeyprintGuiHelper.entry('fillShellWallThickness', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries])
		boxFillParameters.addWidget(self.entryFillShellThickness)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('fillSpacing', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries])
		boxFillParameters.addWidget(self.entryFillSpacing)
		# Bottom clearance.
		self.entryFillThickness = monkeyprintGuiHelper.entry('fillPatternWallThickness', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries])
		boxFillParameters.addWidget(self.entryFillThickness)

		# Create preview frame.
		frameSlicePreview = QtGui.QGroupBox("Slice preview")
		boxSettingsSlicing.addWidget(frameSlicePreview)
		# Create fill parameters box.
		boxSlicePreview = QtGui.QVBoxLayout()
		frameSlicePreview.setLayout(boxSlicePreview)

		self.sliceSlider = monkeyprintGuiHelper.imageSlider(modelCollection=self.modelCollection, programSettings=self.programSettings, width=200, console=self.console, customFunctions=[self.modelCollection.updateAllSlices3d, self.renderView.render])
		boxSlicePreview.addLayout(self.sliceSlider)

		# Create save image stack frame.
		frameSaveSlices = QtGui.QGroupBox("Save slice images")
		boxSettingsSlicing.addWidget(frameSaveSlices)
		boxSaveSlices = QtGui.QVBoxLayout()
		boxSettingsSlicing.addLayout(boxSaveSlices)
		self.buttonSaveSlices = QtGui.QPushButton("Save")
		self.buttonSaveSlices.clicked.connect(self.callbackSaveSlices)
		self.buttonSaveSlices.setEnabled(False)
		boxSaveSlices.addWidget(self.buttonSaveSlices)


		return tabSettingsSlicing




	def createSettingsPrint(self):

		# Create widget.
		tabSettingsPrint = QtGui.QWidget()
		# Create main tab box.
		boxSettingsPrint = QtGui.QVBoxLayout()
		#boxSettingsPrint.setContentsMargins(0,0,0,0)
		tabSettingsPrint.setLayout(boxSettingsPrint)


		# Create slicing parameters frame.
		frameSettingsPrintParameters = QtGui.QGroupBox("Print parameters")
		boxSettingsPrint.addWidget(frameSettingsPrintParameters)
		# Create print parameters box.
		boxPrintParameters = QtGui.QVBoxLayout()
		boxPrintParameters.setContentsMargins(0,3,0,3)

		frameSettingsPrintParameters.setLayout(boxPrintParameters)

		# Create entries.
		self.entryExposure = monkeyprintGuiHelper.entry('exposureTime', settings=self.programSettings)
		boxPrintParameters.addWidget(self.entryExposure)
		self.entryExposureBase = monkeyprintGuiHelper.entry('exposureTimeBase', settings=self.programSettings)
		boxPrintParameters.addWidget(self.entryExposureBase)
		self.entryNumberOfBaseLayers = monkeyprintGuiHelper.entry('numberOfBaseLayers', settings=self.programSettings)
		boxPrintParameters.addWidget(self.entryNumberOfBaseLayers)
		#	self.entrySettleTime = monkeyprintGuiHelper.entry('Resin settle time', settings=self.programSettings)
		#	self.boxPrintParameters.pack_start(self.entrySettleTime, expand=True, fill=True)

		# Create model volume frame.
		frameResinVolume = QtGui.QGroupBox("Resin volume")
		boxSettingsPrint.addWidget(frameResinVolume)
		# Create print parameters box.
		boxResinVolume = QtGui.QVBoxLayout()
		boxResinVolume.setContentsMargins(0,3,0,3)
		frameResinVolume.setLayout(boxResinVolume)

		# Resin volume label.
		self.resinVolumeLabel = QtGui.QLabel("Volume: ")
		boxResinVolume.addWidget(self.resinVolumeLabel, 0, QtCore.Qt.AlignHCenter)

		'''
		# Create camerra trigger frame.
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
		'''
		# Create model volume frame.
		framePrintControl = QtGui.QGroupBox("Print control")
		boxSettingsPrint.addWidget(framePrintControl)


		# Create print control box.
		boxPrintControl = QtGui.QHBoxLayout()
		boxPrintControl.setContentsMargins(0,3,0,3)
		boxPrintControl.setSpacing(0)
		framePrintControl.setLayout(boxPrintControl)
		boxPrintControl.setSpacing(0)
		# Create print control buttons.
		self.buttonPrintStart = QtGui.QPushButton('Print')
		self.buttonPrintStart.setMaximumSize(QtCore.QSize(40,23))
		self.buttonPrintStart.clicked.connect(self.callbackStartPrintProcess)
		boxPrintControl.addWidget(self.buttonPrintStart)
		self.buttonPrintStop = QtGui.QPushButton('Stop')
		self.buttonPrintStop.setMaximumSize(QtCore.QSize(40,23))
		self.buttonPrintStop.clicked.connect(self.callbackStopPrintProcess)
		self.buttonPrintStop.setEnabled(False)
		boxPrintControl.addWidget(self.buttonPrintStop)
		# Create progress bar.
		self.progressBar = monkeyprintGuiHelper.printProgressBar()
		boxPrintControl.addWidget(self.progressBar)


		# Create preview frame.
		frameProjectorView = QtGui.QGroupBox("Projector view")
		boxSettingsPrint.addWidget(frameProjectorView)
		boxProjectorView = QtGui.QHBoxLayout()
		frameProjectorView.setLayout(boxProjectorView)
		# Create slice image.
		self.sliceView = monkeyprintGuiHelper.imageView(settings=self.programSettings, modelCollection=self.modelCollection, mode='full', width=self.programSettings['previewSliceWidth'].value)
		boxProjectorView.addWidget(self.sliceView)


		return tabSettingsPrint


	# **************************************************************************
	# Gui update functions. *****************************************************
	# **************************************************************************


	# *************************************************************************
	# Function that checks if one of the slicer threads is running. ***********
	# *************************************************************************
	def checkSlicer(self):
		# Call the model collections internal checker methods.
		self.modelCollection.checkSlicer()
		# Enable slice stack save button.
		self.buttonSaveSlices.setEnabled(self.modelCollection.sliceCombinerFinished and self.modelCollection.getNumberOfActiveModels() > 0)
		if self.slicerRunning and self.modelCollection.sliceCombinerFinished:
			# update the slider including the image and make print tab available.
			self.updateSlider()
			self.setGuiState(3)
			self.slicerRunning = False
		# If slicer is running...
		elif self.slicerRunning and not self.modelCollection.sliceCombinerFinished or self.modelCollection.getNumberOfActiveModels() == 0:
			# disable the print tab.
			if self.getGuiState() == 3:
				self.setGuiState(2)
		self.slicerRunning = not self.modelCollection.sliceCombinerFinished




	def updateSlicingEntries(self):
		print self.toggleButtonHollow.isChecked()
		print self.toggleButtonFill.isChecked()
		self.entryFillShellThickness.setEnabled(self.toggleButtonHollow.isChecked())
		enableFill = self.toggleButtonHollow.isChecked and self.toggleButtonFill.isChecked()
		self.entryFillSpacing.setEnabled(enableFill)
		self.entryFillThickness.setEnabled(enableFill)


	def updateVolume(self):
		self.resinVolumeLabel.setText("Volume: " + str(self.modelCollection.getTotalVolume()) + " ml.")



	def setGuiState(self, state):
		# State 4 is for printing.

		if state == 4:
			# Disable the model, supports and slicer tabs.
			for i in range(self.notebookSettings.count()):
				if i < 3:
					self.notebookSettings.setTabEnabled(i, False)
				else:
					self.notebookSettings.setTabEnabled(i, True)
			# Disable model list.
			self.modelTableView.setEnabled(False)
		# Loop through tabs and enable the ones up to the state.
		else:
			for i in range(self.notebookSettings.count()):
				if i<=state:
					self.notebookSettings.setTabEnabled(i, True)
				else:
					self.notebookSettings.setTabEnabled(i, False)
			self.modelTableView.setEnabled(True)




	def getGuiState(self):
		tab = 0
		for i in range(self.notebookSettings.count()):
			if self.notebookSettings.isTabEnabled(i):
				tab = i
		return tab



	# Function to update the current model after a change was made.
	# Updates model supports or slicing dependent on
	# the current page of the settings notebook.
	def updateCurrentModel(self):
		# Update model.

		if self.notebookSettings.getCurrentPage() == 0:
			changed = self.modelCollection.getCurrentModel().updateModel()
			# If model has changed, set gui state to supports.
			if changed:
				self.setGuiState(1)
		# Update supports
		elif self.notebookSettings.getCurrentPage() == 1:
			changed = self.modelCollection.getCurrentModel().updateSupports()
			# If supports have changed, set gui state to slicer.
			if changed:
				self.setGuiState(2)
		elif self.notebookSettings.getCurrentPage() == 2:
			self.modelCollection.getCurrentModel().updateSliceStack()
			# Don't set gui state, this will be done by a timeout method
			# that polls the slicer thread.



	def updateAllModels(self):
		if self.notebookSettings.getCurrentPage() == 2:
			self.modelCollection.updateSliceStack()
		elif self.notebookSettings.getCurrentPage() == 1:
			self.modelCollection.updateAllSupports()
		elif self.notebookSettings.getCurrentPage() == 0:
			self.modelCollection.updateAllModels()



	# Update all the settings if the current model has changed.
	def updateAllEntries(self, state=None, render=None):
		#print self.modelCollection.getCurrentModel()
		if not self.modelCollection.getCurrentModel().isActive() or self.modelCollection.getCurrentModelId() == 'default':
			self.entryScaling.setEnabled(False)
			self.entryRotationX.setEnabled(False)
			self.entryRotationY.setEnabled(False)
			self.entryRotationZ.setEnabled(False)
			self.entryPositionX.setEnabled(False)
			self.entryPositionY.setEnabled(False)
			self.entryBottomClearance.setEnabled(False)
			self.entryOverhangAngle.setEnabled(False)
			self.entrySupportSpacingX.setEnabled(False)
			self.entrySupportSpacingY.setEnabled(False)
			self.entrySupportMaxHeight.setEnabled(False)
			self.entrySupportBaseDiameter.setEnabled(False)
			self.entrySupportTipDiameter.setEnabled(False)
			self.entrySupportTipHeight.setEnabled(False)
			self.entrySupportBottomPlateThickness.setEnabled(False)
			self.entryFillSpacing.setEnabled(False)
			self.entryFillThickness.setEnabled(False)
			self.entryFillShellThickness.setEnabled(False)
			#self.checkboxFill.setEnabled(False)
			#self.checkboxHollow.setEnabled(False)
		else:
			self.entryScaling.setEnabled(True)
			self.entryRotationX.setEnabled(True)
			self.entryRotationY.setEnabled(True)
			self.entryRotationZ.setEnabled(True)
			self.entryPositionX.setEnabled(True)
			self.entryPositionY.setEnabled(True)
			self.entryBottomClearance.setEnabled(True)
			self.entryOverhangAngle.setEnabled(True)
			self.entrySupportSpacingX.setEnabled(True)
			self.entrySupportSpacingY.setEnabled(True)
			self.entrySupportMaxHeight.setEnabled(True)
			self.entrySupportBaseDiameter.setEnabled(True)
			self.entrySupportTipDiameter.setEnabled(True)
			self.entrySupportTipHeight.setEnabled(True)
			self.entrySupportBottomPlateThickness.setEnabled(True)
			self.entryFillSpacing.setEnabled(True)
			self.entryFillThickness.setEnabled(True)
			self.entryFillShellThickness.setEnabled(True)
			#self.checkboxFill.setEnabled(True)
			#self.checkboxHollow.setEnabled(True)
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
			self.entryFillShellThickness.update()
			#self.checkboxFill.update()
			#self.checkboxHollow.update()
		# Update job settings.
		self.entryLayerHeight.update()
	#	self.entryExposure.update()
	#	self.entryExposureBase.update()
		# Update menu sensitivities.
		self.updateMenu()
		if state != None:
			self.setGuiState(state)
			if state == 0:
				self.notebookSettings.setCurrentPage(0)
		# Update the volume label in the print tab.
		if self.notebookSettings.getCurrentPage() == 3:
			self.updateVolume()
		# Update model visibilities.
		if render == True:
			for model in self.modelCollection:
				self.modelCollection[model].updateAllActors(self.notebookSettings.getCurrentPage())
			self.renderView.render()
		# Hide camera trigger box when using G-Code.
	#	if self.programSettings['monkeyprintBoard'].value:
	#		self.frameCameraTrigger.show()
	#	else:
	#		self.frameCameraTrigger.hide()



	def updateSlider(self):
		self.sliceSlider.updateSlider()
		self.sliceSlider.updateImage()


	def updateMenu(self):
		pass
		'''
		self.menuItemSave.set_sensitive(self.modelCollection.modelsLoaded())
		self.menuItemClose.set_sensitive(self.modelCollection.modelsLoaded())
		'''


	def callbackMenuClicked(self,menu):
		pass
		'''
		print menu.text()+" is triggered"
		'''

	def callbackSaveSlices(self, widget, data=None):
		# Open a file chooser dialog.
		fileChooser = QtGui.QFileDialog()
		fileChooser.setFileMode(QtGui.QFileDialog.AnyFile)
		fileChooser.setFilter("Image files (*.png)")
		fileChooser.setWindowTitle("Save slices")
		fileChooser.setDirectory(self.programSettings['currentFolder'].getValue())
		filenames = QtCore.QStringList()
		# Only continue if OK was clicked.
		if fileChooser.exec_() == QtGui.QDialog.Accepted:
			# Get path.
			filepath = str(fileChooser.selectedFiles()[0])
			fileChooser.destroy()
			# Add *.png file extension if necessary.
			if filepath.lower()[-3:] != "png":
				filepath += '.png'
			# Console message.
			if self.console:
				self.console.addLine("Saving slice images to \"" + filepath.split('/')[-1] + "\".")
			# Save path without project name for next use.
			self.programSettings['currentFolder'].value = filepath[:-len(filepath.split('/')[-1])]
			# Create info window with progress bar
			infoWindow = monkeyprintGuiHelper.messageWindowSaveSlices(self.mainWindow, self.modelCollection, filepath)
			#
			self.console.addLine("Slice stack saved.")
			infoWindow.destroy()
		'''
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
		'''


	def callbackStartPrintProcess(self, data=None):
		# Create a print start dialog.
		self.dialogStart = monkeyprintGuiHelper.dialogStartPrint(parent = self.mainWindow)
		# Run the dialog and get the result.
		if self.dialogStart.exec_() == QtGui.QDialog.Accepted:
			#self.printProcessStart()
			if not self.queueCommands.qsize():
				self.queueCommands.put("start:")


	def callbackStopPrintProcess(self, data=None):
		# Create a dialog window with yes/no buttons.
		reply = QtGui.QMessageBox.question(	self.mainWindow,
											'Message',
											"Do you really want to cancel the print?",
											QtGui.QMessageBox.Yes,
											QtGui.QMessageBox.No)
		# Stop if desired.
		if reply == QtGui.QMessageBox.Yes:
			if not self.queueCommands.qsize():
				self.queueCommands.put("stop:")



	def printProcessStart(self):
		# If starting print process on PC...
		if not self.programSettings['printOnRaspberry'].value:
			#... create the projector window and start the print process.
			self.console.addLine("Starting print")
			# Disable window close event.
			self.printRunning = True
			# Set gui sensitivity.
			self.setGuiState(4)
			# Set progressbar limit according to number of slices.
			self.progressBar.setLimit(self.modelCollection.getNumberOfSlices())
			# Create the projector window.2
			self.projectorDisplay = monkeyprintGuiHelper.projectorDisplay(self.programSettings, self.modelCollection)
			# Start the print.
			self.printProcess = monkeyprintPrintProcess.printProcess(self.modelCollection, self.programSettings, self.queueSliceOut, self.queueSliceIn, self.queueStatus, self.queueConsole)
			self.printProcess.start()
		# Set button sensitivities.
		self.buttonPrintStart.setEnabled(False)
		self.buttonPrintStop.setEnabled(True)

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
		self.buttonPrintStop.setEnabled(False)


	# Notebook tab switch callback functions. ##################################
	# Model page.
	def tabSwitchModelUpdate(self):
		# Set render actor visibilities.
		self.modelCollection.viewState(0)
		self.renderView.render()
		# Enable model management load and remove buttons.
		self.modelTableView.setButtonsSensitive(load=True, remove=self.modelCollection.modelsLoaded())

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
		self.modelTableView.setButtonsSensitive(False,False)

	# Slicing page.
	def tabSwitchSlicesUpdate(self):
		# Update slice stack height.
		self.modelCollection.updateSliceStack()
		# Set render actor visibilites.
		self.modelCollection.viewState(2)
		self.renderView.render()
		# Activate print tab if not already activated.
		if self.getGuiState() == 2:
			pass
			#self.setGuiState(3)	# Is activated or deactivated in slicer status poll method.
		# Disable model management load and remove buttons.
		self.modelTableView.setButtonsSensitive(False,False)
		# Update slider.
		self.updateSlider()

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
		self.modelTableView.setButtonsSensitive(False, False)
