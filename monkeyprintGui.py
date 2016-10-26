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
	
		#The Main window
		self.mainWindow = QtGui.QMainWindow()
		
		
		# ********************************************************************
		# Create the main GUI. ***********************************************
		# ********************************************************************
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




		'''
		# Create settings box and pack right of render box.
		self.boxSettings = self.createSettingsBox()
		self.boxSettings.show()
		self.boxWork.pack_start(self.boxSettings, expand=False, fill=False, padding = 5)


		# Main box.
		'''
		
		
	#	self.createButtons()
		self.mainWindow.show()
		self.mainWindow.raise_()

			
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
		
	def callbackMenuClicked(self,menu):
		print menu.text()+" is triggered"
		
	# *************************************************************************
	# Gui main function. ******************************************************
	# *************************************************************************
	def main(self):
		# Run the QT event loop.
		self.exec_()
			


	def createSettingsBox(self):
		# Create settings box.
		boxSettings = QtGui.QVBoxLayout()
		
		# Create model list view.
		self.modelTableView = monkeyprintGuiHelper.modelTableView()
		boxSettings.addWidget(self.modelTableView)
		
		# Create settings notebook.
		self.notebookSettings = monkeyprintGuiHelper.notebook()
		self.notebookSettings.addTab(self.createSettingsModel(),'Model')
		self.notebookSettings.addTab(self.createSettingsSupports(),'Supports')
		self.notebookSettings.addTab(self.createSettingsSlicing(),'Slicing')
		self.notebookSettings.addTab(QtGui.QWidget(),'Print')
		# Disable print tab on start-up.
		self.notebookSettings.setTabEnabled(3, False)
		boxSettings.addWidget(self.notebookSettings)
		
		# Create output log.
		self.consoleView = monkeyprintGuiHelper.consoleView(self.console)
		boxSettings.addLayout(self.consoleView)
		
		
		return boxSettings
	
	
	
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
		self.entryScaling = monkeyprintGuiHelper.entry('scaling', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryScaling)
		# Rotation.
		self.entryRotationX = monkeyprintGuiHelper.entry('rotationX', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryRotationX)
		self.entryRotationY = monkeyprintGuiHelper.entry('rotationY', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryRotationY)
		self.entryRotationZ = monkeyprintGuiHelper.entry('rotationZ', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryRotationZ)
		# Position.
		self.entryPositionX = monkeyprintGuiHelper.entry('positionX', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryPositionX)
		self.entryPositionY = monkeyprintGuiHelper.entry('positionY', modelCollection=self.modelCollection )
		boxModelModifications.addLayout(self.entryPositionY)
		# Bottom clearance.
		self.entryBottomClearance = monkeyprintGuiHelper.entry('bottomClearance', modelCollection=self.modelCollection )
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
		self.entryOverhangAngle = monkeyprintGuiHelper.entry('overhangAngle', modelCollection=self.modelCollection )
		boxSupportPattern.addLayout(self.entryOverhangAngle)
		# Spacing.
		self.entrySupportSpacingX = monkeyprintGuiHelper.entry('spacingX', modelCollection=self.modelCollection )
		boxSupportPattern.addLayout(self.entrySupportSpacingX)
		self.entrySupportSpacingY = monkeyprintGuiHelper.entry('spacingY', modelCollection=self.modelCollection )
		boxSupportPattern.addLayout(self.entrySupportSpacingY)
		# Max height.		
		self.entrySupportMaxHeight = monkeyprintGuiHelper.entry('maximumHeight', modelCollection=self.modelCollection )
		boxSupportPattern.addLayout(self.entrySupportMaxHeight)
		
		# Create support geometry frame.
		frameSettingsSupportGeo = QtGui.QGroupBox("Support geometry")
		boxSettingsSupports.addWidget(frameSettingsSupportGeo)
		# Create support geometry box.
		boxSupportGeo = QtGui.QVBoxLayout()
		frameSettingsSupportGeo.setLayout(boxSupportGeo)
		
		# Position.
		self.entrySupportBaseDiameter = monkeyprintGuiHelper.entry('baseDiameter', modelCollection=self.modelCollection )
		boxSupportGeo.addLayout(self.entrySupportBaseDiameter)
		self.entrySupportTipDiameter = monkeyprintGuiHelper.entry('tipDiameter', modelCollection=self.modelCollection )
		boxSupportGeo.addLayout(self.entrySupportTipDiameter)
		# Bottom clearance.
		self.entrySupportTipHeight = monkeyprintGuiHelper.entry('coneHeight', modelCollection=self.modelCollection )
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
		self.entryLayerHeight = monkeyprintGuiHelper.entry('layerHeight', settings=self.programSettings )
		boxSlicingParameters.addLayout(self.entryLayerHeight)

		
		# Create fill parameters frame.
		frameSettingsFillParameters = QtGui.QGroupBox("Fill parameters")
		boxSettingsSlicing.addWidget(frameSettingsFillParameters)
		# Create fill parameters box.
		boxFillParameters = QtGui.QVBoxLayout()
		frameSettingsFillParameters.setLayout(boxFillParameters)
		
		# Position.
		self.entryFillShellThickness = monkeyprintGuiHelper.entry('fillShellWallThickness', modelCollection=self.modelCollection )
		boxFillParameters.addLayout(self.entryFillShellThickness)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('fillSpacing', modelCollection=self.modelCollection )
		boxFillParameters.addLayout(self.entryFillSpacing)
		# Bottom clearance.
		self.entryFillThickness = monkeyprintGuiHelper.entry('fillPatternWallThickness', modelCollection=self.modelCollection )
		boxFillParameters.addLayout(self.entryFillThickness)
		
		return tabSettingsSlicing

		
		
