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

		# Internalise parameters.
		self.modelCollection = modelCollection
		self.programSettings = programSettings
		self.console = console

		# Create signal for Strg+C TODO: check out why this works.
		signal.signal(signal.SIGINT, signal.SIG_DFL)


		# ********************************************************************
		# Add thread listener functions to run every n ms.********************
		# ********************************************************************
		# Check if the slicer threads have finished. Needed in model collection.
		self.timerSlicerListener = QtCore.QTimer()
		self.timerSlicerListener.timeout.connect(self.modelCollection.checkSlicerThreads)#self.updateSlicerStatus)
		self.timerSlicerListener.start(100)
		# Check if slice combiner has finished. Needed in model collection.
		self.timerSliceCombinerListener = QtCore.QTimer()
		self.timerSliceCombinerListener.timeout.connect(self.modelCollection.checkSliceCombinerThread)#self.updateSlicerStatus)
		self.timerSliceCombinerListener.start(100)
		# Check if slicer has finished. Needed to update slice preview.
		self.slicerRunning = False
		self.timerSlicePreviewUpdater = QtCore.QTimer()
		self.timerSlicePreviewUpdater.timeout.connect(self.checkSlicer)#self.updateSlicerStatus)
		self.timerSlicePreviewUpdater.start(100)

		#sliceCombinerListenerId = gobject.timeout_add(100, self.modelCollection.checkSliceCombinerThread)
		# Update the progress bar, projector image and 3d view. during prints.
		'''
		self.timerPollPrintQueues = QtCore.QTimer()
		self.timerPollPrintQueues.timeout.connect(self.pollPrintQueues)
		self.timerPollPrintQueues.start(50)
		'''
		#pollPrintQueuesId = gobject.timeout_add(50, self.pollPrintQueues)
		# Request status info from raspberry pi.
	#	pollRasPiConnectionId = gobject.timeout_add(500, self.pollRasPiConnection)
		# Request status info from slicer.
		'''
		self.timerPollSlicerStatus = QtCore.QTimer()
		self.timerPollSlicerStatus.timeout.connect(self.pollSlicerStatus)
		self.timerPollSlicerStatus.start(100)
		'''
		#pollSlicerStatusId = gobject.timeout_add(100, self.pollSlicerStatus)
		# TODO: combine this with slicerListener.



		# ********************************************************************
		# Create the main GUI. ***********************************************
		# ********************************************************************
		#The Main window
		self.mainWindow = QtGui.QMainWindow()
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
		self.boxSettings =self.createSettingsBox()
		self.boxMain.addLayout(self.boxSettings)


		# Update.
		self.updateAllEntries()


	#	self.createButtons()
		self.mainWindow.show()
		self.mainWindow.raise_()



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
		self.toggleButtonHollow = monkeyprintGuiHelper.toggleButton('printHollow', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries, self.updateSlicingEntries])
		boxFillParameterToggles.addWidget(self.toggleButtonHollow, 0, QtCore.Qt.AlignLeft)
		# Fill.
		self.toggleButtonFill = monkeyprintGuiHelper.toggleButton('fill', modelCollection=self.modelCollection, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries, self.updateSlicingEntries])
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
		# Register slice image update function to GUI main loop.
	#	listenerSliceSlider = gobject.timeout_add(100, self.sliceSlider.updateImage)
		'''

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
		'''
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
		# Create print parameters box.
		boxPrintControl = QtGui.QHBoxLayout()
		boxPrintControl.setContentsMargins(0,3,0,3)
		boxPrintControl.setSpacing(0)
		framePrintControl.setLayout(boxPrintControl)
		boxPrintControl.setSpacing(0)


		# Create print control buttons.
		self.buttonPrintStart = QtGui.QPushButton('Print')
		self.buttonPrintStart.setMaximumSize(QtCore.QSize(40,23))
		boxPrintControl.addWidget(self.buttonPrintStart)
		self.buttonPrintStop = QtGui.QPushButton('Stop')
		self.buttonPrintStop.setMaximumSize(QtCore.QSize(40,23))
		self.buttonPrintStop.setEnabled(False)
		boxPrintControl.addWidget(self.buttonPrintStop)
		'''
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
		'''
		# Create progress bar.
		#self.progressBar1 = monkeyprintGuiHelper.MyBar()
		#boxPrintControl.addWidget(self.progressBar1)

		self.progressBar = monkeyprintGuiHelper.printProgressBar()
		boxPrintControl.addWidget(self.progressBar)
		'''
		# Create preview frame.
		self.framePreviewPrint = gtk.Frame(label="Slice preview")
		self.printTab.pack_start(self.framePreviewPrint, padding = 5)
		self.framePreviewPrint.show()
		self.boxPreviewPrint = gtk.HBox()
		self.framePreviewPrint.add(self.boxPreviewPrint)
		self.boxPreviewPrint.show()

		# Create slice image.
		self.sliceView = monkeyprintGuiHelper.imageView(settings=self.programSettings, modelCollection=self.modelCollection, width=self.programSettings['previewSliceWidth'].value)
		self.boxPreviewPrint.pack_start(self.sliceView, expand=True, fill=True)
		self.sliceView.show()
		'''

		return tabSettingsPrint


	# **************************************************************************
	# Gui update function. *****************************************************
	# **************************************************************************

	def checkSlicer(self):
		if self.slicerRunning and self.modelCollection.sliceCombinerFinished:
			self.updateSlider()
			self.setGuiState(3)
			self.slicerRunning = False
		elif self.slicerRunning and not self.modelCollection.sliceCombinerFinished:
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
		# Disables the model, supports and slicer tabs.
		if state == 4:
			for i in range(self.notebookSettings.count()):
				if i < 3:
					self.notebookSettings.setTabEnabled(i, False)
				else:
					self.notebookSettings.setTabEnabled(i, True)
		else:
			for i in range(self.notebookSettings.count()):
				if i<=state:
					print "foo"
					self.notebookSettings.setTabEnabled(i, True)
				else:
					self.notebookSettings.setTabEnabled(i, False)




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
