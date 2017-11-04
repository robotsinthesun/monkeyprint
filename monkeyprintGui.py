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

# New imports for QT.
import signal
import sys

import PyQt4
from PyQt4 import QtGui, QtCore
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor






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
		# Check if the slicer threads have finished.
		self.timerSlicerListener = QtCore.QTimer()
		self.timerSlicerListener.timeout.connect(self.modelCollection.checkSlicerThreads)#self.updateSlicerStatus)
		self.timerSlicerListener.start(100)
		#slicerListenerId = gobject.timeout_add(100, self.modelCollection.checkSlicerThreads)
		# Check if slice combiner has finished.
		'''
		self.timerSliceCombinerListener = QtCore.QTimer()
		self.timerSliceCombinerListener.timeout.connect(self.modelCollection.checkSliceCombinerThread)#self.updateSlicerStatus)
		self.timerSliceCombinerListener.start(100)
		'''
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

		# Create model list view.
		self.modelTableView = monkeyprintGuiHelper.modelTableView(self.programSettings, self.modelCollection, self.console, self)
		boxSettings.addWidget(self.modelTableView)

		# Create settings notebook.
		self.notebookSettings = monkeyprintGuiHelper.notebook()
		self.notebookSettings.addTab(self.createSettingsModel(),'Model')
		self.notebookSettings.addTab(self.createSettingsSupports(),'Supports')
		self.notebookSettings.addTab(self.createSettingsSlicing(),'Slicing')
		self.notebookSettings.addTab(QtGui.QWidget(),'Print')

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
		boxModelModifications.addLayout(self.entryScaling)
		# Rotation.
		self.entryRotationX = monkeyprintGuiHelper.entry('rotationX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryRotationX)
		self.entryRotationY = monkeyprintGuiHelper.entry('rotationY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryRotationY)
		self.entryRotationZ = monkeyprintGuiHelper.entry('rotationZ', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryRotationZ)
		# Position.
		self.entryPositionX = monkeyprintGuiHelper.entry('positionX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryPositionX)
		self.entryPositionY = monkeyprintGuiHelper.entry('positionY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryPositionY)
		# Bottom clearance.
		self.entryBottomClearance = monkeyprintGuiHelper.entry('bottomClearance', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxModelModifications.addLayout(self.entryBottomClearance)

		boxSettingsModel.addStretch()
		return tabSettingsModel



	def createSettingsSupports(self):

		# Create widget.
		tabSettingsSupports = QtGui.QWidget()
		# Create main tab box.
		boxSettingsSupports = QtGui.QVBoxLayout()
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
		boxSupportPattern.addLayout(self.entryOverhangAngle)
		# Spacing.
		self.entrySupportSpacingX = monkeyprintGuiHelper.entry('spacingX', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addLayout(self.entrySupportSpacingX)
		self.entrySupportSpacingY = monkeyprintGuiHelper.entry('spacingY', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addLayout(self.entrySupportSpacingY)
		# Max height.
		self.entrySupportMaxHeight = monkeyprintGuiHelper.entry('maximumHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addLayout(self.entrySupportMaxHeight)
		# Bottom plate thickness.
		self.entrySupportBottomPlateThickness = monkeyprintGuiHelper.entry('bottomPlateThickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries] )
		boxSupportPattern.addLayout(self.entrySupportBottomPlateThickness)

		# Create support geometry frame.
		frameSettingsSupportGeo = QtGui.QGroupBox("Support geometry")
		boxSettingsSupports.addWidget(frameSettingsSupportGeo)
		# Create support geometry box.
		boxSupportGeo = QtGui.QVBoxLayout()
		frameSettingsSupportGeo.setLayout(boxSupportGeo)

		# Position.
		self.entrySupportBaseDiameter = monkeyprintGuiHelper.entry('baseDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxSupportGeo.addLayout(self.entrySupportBaseDiameter)
		self.entrySupportTipDiameter = monkeyprintGuiHelper.entry('tipDiameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxSupportGeo.addLayout(self.entrySupportTipDiameter)
		# Bottom clearance.
		self.entrySupportTipHeight = monkeyprintGuiHelper.entry('coneHeight', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		boxSupportGeo.addLayout(self.entrySupportTipHeight)

		return tabSettingsSupports



	def createSettingsSlicing(self):

		# Create widget.
		tabSettingsSlicing = QtGui.QWidget()
		# Create main tab box.
		boxSettingsSlicing = QtGui.QVBoxLayout()
		tabSettingsSlicing.setLayout(boxSettingsSlicing)

		# Create slicing parameters frame.
		frameSettingsSlicingParameters = QtGui.QGroupBox("Slicing parameters")
		boxSettingsSlicing.addWidget(frameSettingsSlicingParameters)
		# Create slicing parameters box.
		boxSlicingParameters = QtGui.QVBoxLayout()
		frameSettingsSlicingParameters.setLayout(boxSlicingParameters)

		# Create entries.
		# Layer height.
		self.entryLayerHeight = monkeyprintGuiHelper.entry('layerHeight', settings=self.programSettings, customFunctions=[self.modelCollection.updateSliceStack, self.updateSlider, self.renderView.render, self.updateAllEntries])
		boxSlicingParameters.addLayout(self.entryLayerHeight)


		# Create fill parameters frame.
		frameSettingsFillParameters = QtGui.QGroupBox("Fill parameters")
		boxSettingsSlicing.addWidget(frameSettingsFillParameters)
		# Create fill parameters box.
		boxFillParameters = QtGui.QVBoxLayout()
		frameSettingsFillParameters.setLayout(boxFillParameters)

		# Position.
		self.entryFillShellThickness = monkeyprintGuiHelper.entry('fillShellWallThickness', modelCollection=self.modelCollection)
		boxFillParameters.addLayout(self.entryFillShellThickness)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('fillSpacing', modelCollection=self.modelCollection )
		boxFillParameters.addLayout(self.entryFillSpacing)
		# Bottom clearance.
		self.entryFillThickness = monkeyprintGuiHelper.entry('fillPatternWallThickness', modelCollection=self.modelCollection )
		boxFillParameters.addLayout(self.entryFillThickness)

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



	# **************************************************************************
	# Gui update function. *****************************************************
	# **************************************************************************


	def updateVolume(self):
		self.resinVolumeLabel.set_text("Volume: " + str(self.modelCollection.getTotalVolume()) + " ml.")



	def setGuiState(self, state):
		# State for is for printing.
		if state == 4:
			for i in range(self.notebookSettings.count()):
				if i < 3:
					self.notebookSettings.setTabEnabled(i, False)
				else:
					self.notebookSettings.setTabEnabled(i, True)
		else:
			for i in range(self.notebookSettings.count()):
				if i<=state:
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
		if not self.modelCollection.getCurrentModel().isactive() or self.modelCollection.getCurrentModelId() == 'default':
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
		pass
		'''
		self.sliceSlider.updateSlider()
		self.sliceSlider.updateImage()
		'''



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
		# Update slider.
	#	self.sliceSlider.updateSlider()
		# Update slice stack height.
	#	self.modelCollection.updateSliceStack()
		# Set render actor visibilites.
		self.modelCollection.viewState(2)
		self.renderView.render()
		# Activate print tab if not already activated.
		if self.getGuiState() == 2:
			pass
			#self.setGuiState(3)	# Is activated or deactivated in slicer status poll method.
		# Disable model management load and remove buttons.
		self.modelTableView.setButtonsSensitive(False,False)

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






