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

import os
import sys
import shutil
import vtk
from vtk.util import numpy_support	# Functions to convert between numpy and vtk
import math
import cv2
import numpy
import time
import random
from PIL import Image#, ImageTk
import Queue, threading
import monkeyprintImageHandling as imageHandling
import gtk
import cPickle	# Save modelCollection to file.
import gzip
import tarfile
import copy

import monkeyprintSettings






 ##  ##  ####  #####   ##### ##        ####   ####  ##  ## ###### ####  ###### ##  ##  ##### #####
 ###### ##  ## ##  ## ##     ##       ##  ## ##  ## ### ##   ##  ##  ##   ##   ### ## ##     ##  ##
 ###### ##  ## ##  ## ####   ##       ##     ##  ## ######   ##  ##  ##   ##   ###### ####   ##  ##
 ##  ## ##  ## ##  ## ##     ##       ##     ##  ## ## ###   ##  ######   ##   ## ### ##     #####
 ##  ## ##  ## ##  ## ##     ##       ##  ## ##  ## ##  ##   ##  ##  ##   ##   ##  ## ##     ## ##
 ##  ##  ####  #####   ##### ######    ####   ####  ##  ##   ##  ##  ## ###### ##  ##  ##### ##  ##





class modelContainer:
	def __init__(self, filenameOrSettings, modelId, programSettings, console=None):

		# Check if a filename has been given or an existing model settings object.
		# If filename was given...
		if type(filenameOrSettings) == str:
			# ... create the model data with default settings.
			# Create settings object.
			self.settings = monkeyprintSettings.modelSettings()
			filename = filenameOrSettings
			# Save filename to settings.
			self.settings['filename'].value = filename
		# If settings object was given...
		else:
			# ... create the model data with the given settings.
			self.settings = filenameOrSettings
			# Get filename from settings object.
			filename = self.settings['filename'].value

		# Internalise remaining data.
		self.console=console

		# Get the slice path where slice images are saved.
		self.slicePath = programSettings['tmpDir'].value + '/slicer/' + modelId
		self.slicePath = self.slicePath.replace(' ', '') + '.d'

		# Create model object.
		self.model = modelData(filename, self.slicePath, self.settings, programSettings, self.console)

		# active flag. Only do updates if model is active.
		self.flagactive = True

		# Update model and supports.
		self.updateModel()
	#	self.updateSupports()	# Do this upon entering supports tab.

		# Set inital visibilities.
		self.hideOverhang()
		self.hideSupports()
		self.hideBottomPlate()
		self.hideSlices()
		self.hideClipModel()

		# Set changed flag to start slicer.
		self.setChanged()


	def getHeight(self):
		return self.model.getHeight()

	def setChanged(self):
		self.model.setChanged()

	def updateModel(self):
		#self.model.setChanged()
		return self.model.updateModel()

	def updateSupports(self):
		#self.model.setChanged()
		#self.model.updateBottomPlate()
		return self.model.updateSupports()

	def updateSlice3d(self, sliceNumber):
		self.model.updateSlice3d(sliceNumber)

	def updateSliceStack(self, force=False):
		return self.model.updateSliceStack()

	def sliceThreadListener(self):
#		self.model.setChanged()
		self.model.checkBackgroundSlicer()

	# Delete slice images.
	def cleanUp(self):
		# Empty the slicer temp directory.
		shutil.rmtree(self.slicePath, ignore_errors=True)


	def getAllActors(self):
		return (	self.getActor(),
				self.getBoxActor(),
				self.getBoxTextActor(),
				self.getOverhangActor(),
				self.getBottomPlateActor(),
				self.getSupportsActor(),
				self.getClipModelActor(),
				self.getSlicesActor()
				)
	def hideAllActors(self):
#		print "bar"
		self.hideModel(),
		self.hideBox(),
		self.hideOverhang(),
		self.hideBottomPlate(),
		self.hideSupports(),
		self.hideClipModel(),
		self.hideSlices()

	def showAllActors(self, state):
	#	if self.isactive():
			if state == 0:
				self.showActorsDefault()
			elif state == 1:
				self.showActorsSupports()
			elif state == 2:
				self.showActorsSlices()
			elif state == 3:
				self.showActorsPrint()
	#	else:
	#		self.ghostAllActors()

	def ghostAllActors(self):
		self.ghostModel()
		self.ghostSupports()
		self.ghostBottomPlate()
		self.ghostClipModel()
		self.ghostSlices()
		self.hideOverhang()

	# Adjust view for model manipulation.
	def showActorsDefault(self):
		self.opaqueModel()
		self.showModel()
		self.hideOverhang()
		self.hideBottomPlate()
		self.hideSupports()
		self.hideSlices()
		self.hideClipModel()
	# Adjust view for support generation.
	def showActorsSupports(self):
		self.transparentModel()
		self.showModel()
		self.showOverhang()
		self.opaqueBottomPlate()
		self.showBottomPlate()
		self.opaqueSupports()
		self.showSupports()
		self.hideSlices()
		self.hideClipModel()
	# Adjust view for slicing.
	def showActorsSlices(self):
#		self.transparentModel()
		self.hideModel()
		self.hideOverhang()
#		self.transparentBottomPlate()
		self.hideBottomPlate()
#		self.transparentSupports()
		self.hideSupports()
		self.opaqueSlices()
		self.showSlices()
		self.opaqueClipModel()
		self.showClipModel()
	def showActorsPrint(self):
		self.opaqueClipModel()
		self.showClipModel()
#		self.opaqueModel()
		self.hideModel()
		self.hideOverhang()
#		self.opaqueBottomPlate()
		self.hideBottomPlate()
#		self.opaqueSupports()
		self.hideSupports()
		self.hideSlices()

	def setactive(self, active):
		self.flagactive = active
		self.model.setactive(active)

	def isactive(self):
		return self.flagactive

	def getActor(self):
		return self.model.getActor()

	def getBoxActor(self):
		self.model.opacityBoundingBox(0.3)
		return self.model.getActorBoundingBox()

	def getBoxTextActor(self):
		self.model.opacityBoundingBoxText(0.7)
		return self.model.getActorBoundingBoxText()

	def getSupportsActor(self):
		return self.model.getActorSupports()

	def getBottomPlateActor(self):
		return self.model.getActorBottomPlate()

	def getOverhangActor(self):
		return self.model.getActorOverhang()

	def getClipModelActor(self):
		return self.model.getActorClipModel()

	def getSlicesActor(self):
		return self.model.getActorSlices()

	def showBox(self):
	#	if self.flagactive:
			self.model.showBoundingBox()
			self.model.showBoundingBoxText()

	def hideBox(self):
		self.model.hideBoundingBox()
		self.model.hideBoundingBoxText()

	def showModel(self):
		self.model.show()
		if not self.flagactive:
			self.model.opacity(.1)

	def hideModel(self):
		self.model.hide()

	def opaqueModel(self):
		self.model.opacity(1.0)

	def transparentModel(self):
		self.model.opacity(.5)

	def ghostModel(self):
		self.model.opacity(.1)

	def showOverhang(self):
		self.model.showActorOverhang()
		if not self.flagactive:
			self.hideOverhang()

	def hideOverhang(self):
		self.model.hideActorOverhang()

	def showBottomPlate(self):
		self.model.showActorBottomPlate()
		if not self.flagactive:
			self.model.setOpacityBottomPlate(.1)

	def hideBottomPlate(self):
		self.model.hideActorBottomPlate()

	def opaqueBottomPlate(self):
		self.model.setOpacityBottomPlate(1.0)

	def transparentBottomPlate(self):
		self.model.setOpacityBottomPlate(.5)

	def ghostBottomPlate(self):
		self.model.setOpacityBottomPlate(.1)

	def showSupports(self):
		self.model.showActorSupports()
		if not self.flagactive:
			self.model.setOpacitySupports(.1)

	def hideSupports(self):
		self.model.hideActorSupports()

	def opaqueSupports(self):
		self.model.setOpacitySupports(1.0)

	def transparentSupports(self):
		self.model.setOpacitySupports(.5)

	def ghostSupports(self):
		self.model.setOpacitySupports(.1)

	def showClipModel(self):
		self.model.showActorClipModel()
		if not self.flagactive:
			self.model.setOpacityClipModel(.1)

	def hideClipModel(self):
		self.model.hideActorClipModel()

	def opaqueClipModel(self):
		self.model.setOpacityClipModel(1.0)

	def transparentClipModel(self):
		self.model.setOpacityClipModel(.5)

	def ghostClipModel(self):
		self.model.setOpacityClipModel(.1)

	def showSlices(self):
		self.model.showActorSlices()
		if not self.flagactive:
			self.model.setOpacitySlices(.1)

	def opaqueSlices(self):
		self.model.setOpacitySlices(1.0)

	def ghostSlices(self):
		self.model.setOpacitySlices(.1)

	def hideSlices(self):
		self.model.hideActorSlices()







 ##  ##  ####  #####   ##### ##        ####   ####  ##     ##     ##### #### ###### ###### ####  ##  ##
 ###### ##  ## ##  ## ##     ##       ##  ## ##  ## ##     ##    ##    ##  ##  ##     ##  ##  ## ### ##
 ###### ##  ## ##  ## ####   ##       ##     ##  ## ##     ##    ####  ##      ##     ##  ##  ## ######
 ##  ## ##  ## ##  ## ##     ##       ##     ##  ## ##     ##    ##    ##      ##     ##  ##  ## ## ###
 ##  ## ##  ## ##  ## ##     ##       ##  ## ##  ## ##     ##    ##    ##  ##  ##     ##  ##  ## ##  ##
 ##  ##  ####  #####   ##### ######    ####   ####  ###### ###### ##### ####   ##   ###### ####  ##  ##







class modelCollection(dict):

	def __init__(self, programSettings, console=None):
		# Call super class init function. *********************
		dict.__init__(self)

		# Internalise settings. *******************************
		self.programSettings = programSettings
		self.console = console

		# Create slice image. *********************************
		#self.sliceImage = imageHandling.createImageGray(self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value, 0)
		#self.sliceImageBlack = numpy.empty_like(self.sliceImage)

		# Preview slice stack. ********************************
		self.sliceStackPreview = sliceStack()
		self.sliceNumbers = [0]
		self.sliceMode = "preview"
		self.currentSliceNumber = None
		self.currentSlice = imageHandling.createImageGray(self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value,0)
		self.sliceCombinerFinished = False
		#self.numberOfPreviewSlices = self.getMaxNumberOfPreviewSlices()
		#print "Maximum number of preview slices: " + str(self.numberOfPreviewSlices) + "."
		#self.stackHeightOld = self.sliceStackPreview.getStackHeight()
		# Queue for transferring slice images from model slicer threads
		# to slice combiner thread.
		self.queueModelCollectionToCombiner = Queue.Queue()
		self.queueCombinerToModelCollection = Queue.Queue()
		self.queueCombinerToModelCollectionSingle = Queue.Queue()
		# Slice combiner thread.
		self.threadSliceCombiner = sliceCombiner(self.programSettings, self.queueModelCollectionToCombiner, self.queueCombinerToModelCollection, self.queueCombinerToModelCollectionSingle, self.console)
		self.threadSliceCombiner.start()

		# Create calibration image. ***************************
		self.calibrationImage = None#numpy.empty_like(self.sliceImage)

		# Set defaults. ***************************************
		# Create current model id.
		self.currentModelId = ""
		# Load default model to fill settings for gui.
		self.add("default", "")	# Don't provide file name.

		# Create model list.***********************************
		# List will contain strings for dispayed name,
		# internal name and file name and a bool for active state.
		self.modelList = gtk.ListStore(str, str, str, bool)

		# Create job settings object. *************************
		#self.jobSettings = monkeyprintSettings.jobSettings(self.programSettings)


	# Reload calibration image.
	def subtractCalibrationImage(self, inputImage):
		# Get the image if it does not exist.
		if self.calibrationImage == None and self.programSettings['calibrationImage'].value:
			print "Loading calibration image."
			calibrationImage = None
			try:
				if os.path.isfile('./calibrationImage.png'):
					calibrationImage = cv2.imread('./calibrationImage.png')
				elif os.path.isfile('./calibrationImage.jpg'):
					calibrationImage = cv2.imread('./calibrationImage.jpg')
			except Error:
				print "Could not load calibration image. Skipping..."

			# If loading succeded...
			if calibrationImage != None:
				# Convert to grayscale.
				calibrationImage = cv2.cvtColor(calibrationImage, cv2.COLOR_BGR2GRAY)
				# ... scale the image according to projector size.
				calibrationImage = cv2.resize(calibrationImage, (self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value))
				# Blur the image to reduce the influence of noise.
				calibrationImage = cv2.GaussianBlur(calibrationImage, (21, 21), 0)
				# Turn into numpy array.
				self.calibrationImage = numpy.asarray(calibrationImage, dtype=numpy.uint8)
				# Find the lowest pixel value.
				minVal = numpy.amin(self.calibrationImage)
				# Shift pixel values down.
				# Darkest pixel should be black now.
				self.calibrationImage -= minVal

				#print calibrationImage.shape

		# If the image exists now...
		if self.calibrationImage != None and self.programSettings['calibrationImage'].value:

			# Resize in case of settings change.
			if self.calibrationImage.shape[0] != self.programSettings['projectorSizeY'].value or self.calibrationImage.shape[1] != self.programSettings['projectorSizeX'].value:
				self.calibrationImage = cv2.resize(self.calibrationImage, (self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value))
		#	print "Subtracting calibration image."
			# ... subtract the calibration image from the input image.
			inputImage = cv2.subtract(inputImage, self.calibrationImage)

		if not self.programSettings['calibrationImage'].value:
			self.calibrationImage = None

		return inputImage


	# Save model collection to compressed disk file. Works well with huge objects.
	def saveProject(self, filename, protocol = -1, fileSearchFnc=None):
		# Gather the relevant data.
		# Model settings.
		modelSettings = {}
		for model in self:
			if model != "default":
				modelSettings[model] = (self[model].settings)
		# Model list for GUI.
		# gtk.ListStores cannot be pickled, so we convert to list of lists.
		listStoreList = []
		for row in range(len(self.modelList)):
			i = self.modelList.get_iter(row)
			rowData = []
			for j in range(4):
				dat = self.modelList.get_value(i,j)
				rowData.append(dat)
			listStoreList.append(rowData)
		# Combine model settings with job settings.
		jobSettings = monkeyprintSettings.jobSettings(self.programSettings)
		data = [jobSettings, modelSettings, listStoreList]#TODO
		# Write the data into a pickled binary file.
		picklePath = os.getcwd() + '/pickle.bin'
		with open(picklePath, 'wb') as pickleFile:
			# Dump the data.
			cPickle.dump(data, pickleFile, protocol)


		# Add all relevant stl files.
		# First, create a list of the model file paths.
		modelPathList = []
		self.console.addLine("Packing the following stl files: ")
		for model in self:
			if model != "default":
				# Get the model file path.
				modelPath = self[model].settings['filename'].value
				# Append if not in list already.
				if modelPath not in modelPathList:
					modelPathList.append(modelPath)
					self.console.addLine("   " + modelPath.split('/')[-1])


		# Create a tar archive with gzip compression. This will be the mkp file.
		with tarfile.open(filename, 'w:gz') as mkpFile:
			# Add the pickled settings file.
			mkpFile.add(picklePath, arcname='pickle.bin', recursive=False)

			# Add the stl files. Use file name without path as name.
			for path in modelPathList:
				#print path.split('/')[-1]
				try:
					mkpFile.add(path, arcname=path.split('/')[-1])
				except IOError, OSError:
					print "Stl file not found..."
# TODO: Handle file not found error in GUI.
# TODO: Maybe copy stls into temporary dir upon load?
# This would be consistent with loading an mkp file and saving stls to tmp dir.

	# Load a compressed model collection from disk.
	def loadProject(self, filename):
		# Create temporary working directory path.
		#tmpPath = os.getcwd()+'/tmp'
		tmpPath = self.programSettings['tmpDir'].value
		# Delete the tmp directory, just in case it is there already.
		shutil.rmtree(tmpPath, ignore_errors=True)
		# Extract project files to tmp directory.
		with tarfile.open(filename, 'r:gz') as mkpFile:
			mkpFile.extractall(path=tmpPath)
		# Read the pickled settings file.
		data=None
		with open(tmpPath+'/pickle.bin', 'rb') as pickleFile:
			# Dump the data.
			data = cPickle.load(pickleFile)

		# Clear all models from current model collection.
		self.removeAll()
		# Get the relevant parts from the object.
		# First is job settings, second is list of model settings.
		jobSettings = data[0]
		jobSettings.setProgramSettings(self.programSettings)
		settingsList = data[1]
		# Import the model settings from the file into the model collection.
		for model in settingsList:
			if model != "default":
				# Make the model file path point to the tmp directory.
				modelFilename = settingsList[model]['filename'].value.split('/')[-1]
				settingsList[model]['filename'].value = tmpPath+'/'+modelFilename
				# Create a new model from the modelId and settings.
				self.add(model, settingsList[model])
				self.getCurrentModel().hideBox()
		# Get the model list and convert to list store.
		modelListData = data[2]
		for row in modelListData:
			if row[0] != "default":
				self.modelList.append(row)
		# Delete the tmp directory.
	#	shutil.rmtree(tmpPath)


	# Function to retrieve id of the current model.
	def getCurrentModelId(self):
		return self.currentModelId


	# Function to retrieve current model.
	def getCurrentModel(self):
		return self[self.currentModelId]


	# Function to change to current model.
	def setCurrentModelId(self, modelId):
		self.currentModelId = modelId


	# Function to retrieve a model object.
	def getModel(self, modelId):
		return self[modelId]


	# Add a model to the collection.
	def add(self, modelId, filenameOrSettings):
		self[modelId] = modelContainer(filenameOrSettings, modelId, self.programSettings, self.console)
		# Set new model as current model.
		self.currentModelId = modelId


	# Function to remove a model from the model collection
	def remove(self, modelId):
		if self[modelId]:
			self[modelId].model.killBackgroundSlicer()
			self[modelId].cleanUp()
			# Explicitly delete model data to free memory from slice images.
			del self[modelId].model
			del self[modelId]


	def removeAll(self):
		# Set current model to default.
		self.setCurrentModelId("default")
		# Get list of model ids.
		modelIDs = []
		for model in self:
			if model != "default":
				modelIDs.append(model)
		for i in range(len(modelIDs)):
			self.remove(modelIDs[i])

		# Empty existing model list.
		listIters = []
		for row in range(len(self.modelList)):
			listIters.append(self.modelList.get_iter(row))
		for i in listIters:
			if self.modelList.get_value(i,0) != "default":
				self.modelList.remove(i)


	# Function to retrieve the highest model. This dictates the slice stack height.
	def getNumberOfSlices(self):
		modelHeights = []
		for model in self:
			if model != "default":
				modelHeights.append(self[model].model.getNumberOfSlices())
		if modelHeights != []:
			return sorted(modelHeights)[-1]
		# Return 0 if no model has been loaded yet.
		else:
			return 0


	def getMaxNumberOfPreviewSlices(self):
		return self.programSettings['previewSlicesMax'].value


	# Return the calculated preview stack height.
	def getPreviewStackHeight(self):
		if self.getMaxNumberOfPreviewSlices() >= self.getNumberOfSlices():
			if self.getNumberOfSlices() > 0:
				return self.getNumberOfSlices()
			else:
				return 0
		else:
			return self.getMaxNumberOfPreviewSlices()


	# Return the current preview stack height.
	# This might be 1 if slicer is still running.
	def getPreviewStackHeightCurrent(self):
		print len(self.sliceStackPreview)
		return len(self.sliceStackPreview)


	def getPreviewSliceHeight(self):
		# Calc number of preview slices from settings.
		# Get slice multiplier.
		if self.getMaxNumberOfPreviewSlices() >= self.getNumberOfSlices():
			sliceMultiplier = 1
		else:
			sliceMultiplier = (self.getNumberOfSlices()) / float(self.getMaxNumberOfPreviewSlices())
		return sliceMultiplier


	# Gather slicer input info.
	def createSlicerInputInfo(self, mode="preview", savePath=None):
		assert mode == "preview" or mode == "full" or mode.split(' ')[0] == "single"
		# Create model height list.
		# Data: create preview, number of prev slices, prev slice height,
		# slice paths, number of model slices, model position, model size.
		# Mode can be preview, full or slice number.
		modelNamesAndHeights = [self.getPreviewStackHeight(), self.getPreviewSliceHeight(), [],[],[],[], mode, savePath]
		# Update all models' slice stacks.
		for model in self:
			if model != 'default':
				modelNamesAndHeights[2].append(self[model].slicePath)
				modelNamesAndHeights[3].append(self[model].model.getNumberOfSlices())
				modelNamesAndHeights[4].append(self[model].model.getSlicePositionPx(border=False))
				modelNamesAndHeights[5].append(self[model].model.getSliceSizePx(border=True))
		return modelNamesAndHeights


	# Update the slice stack.
	# This is called from the GUI and starts all model
	# slicers if the respective model has changed.
	# The force option will start all model slicers
	# even if the models have not been changed.
	# This method also starts the slice combiner.
	def updateSliceStack(self, force=False):
		# Update model slice stacks.
		for model in self:
			self[model].updateSliceStack(force)
		# Reset preview slice stack.
		self.sliceStackPreview.update(1)
		self.sliceNumbers = [0]
		# Update preview slice stack.
		if self.getNumberOfSlices() > 0:
			self.queueModelCollectionToCombiner.put(self.createSlicerInputInfo(mode="preview"))
			self.sliceCombinerFinished = False


	# Save slice stack.
	# Update function is a gui function that moves a progress bar.
	def saveSliceStack(self, path, updateFunction=None):
		# Set slice mode to full to block slice combiner checker
		# timeout function to read slicer status from the slice
		# combiner output queue.
		self.sliceMode = "full"
		# Get number of slices.
		nSlices = self.getNumberOfSlices()
		# Update preview slice stack. This will automatically
		# save the images to the temp directory.
		self.queueModelCollectionToCombiner.put(self.createSlicerInputInfo(mode="full", savePath=path))
		# Update the status bar.
		while True:
			while not self.queueCombinerToModelCollection.qsize():
				time.sleep(0.1)
			status = self.queueCombinerToModelCollection.get()
			# Update progress bar.
			if updateFunction != None:
				updateFunction(int(status))
				while gtk.events_pending():
					gtk.main_iteration(False)
			if int(status) == 100:
				break
		# Reset slice mode to preview.
		self.sliceMode = "preview"


	# Create the projector frame from the model slice stacks.
	def updateSliceImage(self, i, mode='preview'):
		assert mode == 'preview' or mode == 'full'
		# Make sure index is an integer.
		i = int(i)
		if mode == 'preview':
			# Return preview image.
			return self.sliceStackPreview[i]
		elif mode == 'full':
			# Check if the current slice is requested again.
			if self.currentSliceNumber != None and i == self.currentSliceNumber:
				return self.currentSlice
			# If not, create it.
			else:
				# Send request to slice combiner.
				self.queueModelCollectionToCombiner.put(self.createSlicerInputInfo(mode="single "+str(i)))
				# Wait for response.
				while not self.queueCombinerToModelCollectionSingle.qsize():
					time.sleep(0.1)
				# Get slice image.
				self.currentSlice = self.queueCombinerToModelCollectionSingle.get()
				self.currentSliceNumber = i
				# Return slice.
				return self.currentSlice




	def viewState(self, state):
		if state == 0:
			for model in self:
				self[model].showActorsDefault()
		elif state == 1:
			for model in self:
				self[model].showActorsSupports()
		elif state == 2:
			for model in self:
				self[model].showActorsSlices()
		elif state == 3:
			for model in self:
				self[model].showActorsPrint()
	'''
	# Adjust view for model manipulation.
	def viewDefault(self):
		for model in self:
			self[model].opaqueModel()
			self[model].hideOverhang()
			self[model].hideBottomPlate()
			self[model].hideSupports()
			self[model].hideSlices()
	# Adjust view for support generation.
	def viewSupports(self):
		for model in self:
			self[model].transparentModel()
			self[model].showOverhang()
			self[model].showBottomPlate()
			self[model].opaqueBottomPlate()
			self[model].showSupports()
			self[model].opaqueSupports()
			self[model].hideSlices()
	# Adjust view for slicing.
	def viewSlices(self):
		for model in self:
			self[model].transparentModel()
			self[model].hideOverhang()
			self[model].showBottomPlate()
			self[model].transparentBottomPlate()
			self[model].showSupports()
			self[model].transparentSupports()
			self[model].showSlices()

	def viewPrint(self):
		for model in self:
			self[model].transparentModel()
			self[model].hideOverhang()
			self[model].showBottomPlate()
			self[model].transparentBottomPlate()
			self[model].showSupports()
			self[model].transparentSupports()
			self[model].showSlices()

	'''
	def updateAllModels(self):
		for model in self:
			self[model].updateModel()

	# Update supports.
	def updateAllSupports(self):
		for model in self:
			self[model].updateSupports()

	# Update the 3d slice view for all models.
	def updateAllSlices3d(self, sliceNumber):
		for model in self:
			self[model].model.updateSlice3d(sliceNumber)

	# Function that is called every n milliseconds from gtk main loop to
	# check the slicer queue.
	def checkSlicerThreads(self):
		for model in self:
			self[model].sliceThreadListener()
		 # Return true, otherwise the function will not run again.
		return True

	def checkSliceCombinerThread(self):
		if self.sliceMode == "preview":
			if self.queueCombinerToModelCollection.qsize():
				sliceCombinerOutput = self.queueCombinerToModelCollection.get()
				if type(sliceCombinerOutput) == str:
					self.console.addLine('Slicer progress: ' + sliceCombinerOutput + '%.')
				else:
					self.sliceStackPreview, self.sliceNumbers = sliceCombinerOutput
					self.sliceCombinerFinished = True
		return True

	def slicerRunning(self):
		# Return True if one of the slicers is still running.
		running = False
		for model in self:
			if model != "default":
				running = running or self[model].model.flagSlicerRunning
		#	print running
		return running


	def slicerThreadsFinished(self):
		finished = False
		for model in self:
			if model != "default":
				finished = finished or self[model].model.flagSlicerFinished
		#	print running
		#print finished
		return finished


	# Get all model volumes.
	def getTotalVolume(self):
		volume = 0
		for model in self:
			if self[model].isactive():
				volume += self[model].model.getVolume()
		return volume


	def getAllActors(self):
		allActors = []
		for model in self:
			modelActors = self[model].getAllActors()
			for actor in modelActors:
				allActors.append(actor)
		return allActors


	def modelsLoaded(self):
		if len(self) > 1:
			return True
		else:
			return False


################################################################################
# Create an error observer for the VTK error messages. #########################
################################################################################
# Taken from here: http://www.vtk.org/pipermail/vtkusers/2012-June/074703.html
class ErrorObserver:

   def __init__(self):
       self.__ErrorOccurred = False
       self.__WarningOccurred = False
       self.__ErrorMessage = None
       self.__WarningMessage = None
       self.CallDataType = 'string0'

   def __call__(self, obj, event, message):
       if event == 'WarningEvent':
           self.__WarningOccurred = True
           self.__WarningMessage = message
       else:
           self.__ErrorOccurred = True
           self.__ErrorMessage = message

   def ErrorOccurred(self):
       occ = self.__ErrorOccurred
       self.__ErrorOccurred = False
       return occ

   def WarningOccurred(self):
       occ = self.__WarningOccurred
       self.__WarningOccurred = False
       return occ

   def ErrorMessage(self):
       return self.__ErrorMessage

   def WarningMessage(self):
       return self.__WarningMessage






 #####  ##  ## ###### ##     #####    ##  ##  ####  ##    ##  ## ##  ##  #####   #####   #### ###### ####
 ##  ## ##  ##   ##   ##     ##  ##   ##  ## ##  ## ##    ##  ## ###### ##       ##  ## ##  ##  ##  ##  ##
 #####  ##  ##   ##   ##     ##  ##   ##  ## ##  ## ##    ##  ## ###### ####     ##  ## ##  ##  ##  ##  ##
 ##  ## ##  ##   ##   ##     ##  ##   ##  ## ##  ## ##    ##  ## ##  ## ##       ##  ## ######  ##  ######
 ##  ## ##  ##   ##   ##     ##  ##    ####  ##  ## ##    ##  ## ##  ## ##       ##  ## ##  ##  ##  ##  ##
 #####   ####  ###### ###### #####      ##    ####  ###### ####  ##  ##  #####   #####  ##  ##  ##  ##  ##





################################################################################
# Build volume. ################################################################
################################################################################
class buildVolume:
	def __init__(self, buildVolumeSize):
		# Create build volume.
		self.buildVolume = vtk.vtkCubeSource()
		self.buildVolume.SetCenter(buildVolumeSize[0]/2.0, buildVolumeSize[1]/2.0, buildVolumeSize[2]/2.0)
		self.buildVolume.SetXLength(buildVolumeSize[0])
		self.buildVolume.SetYLength(buildVolumeSize[1])
		self.buildVolume.SetZLength(buildVolumeSize[2])

		# Build volume outline filter.
		self.outlineFilter = vtk.vtkOutlineFilter()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.outlineFilter.SetInput(self.buildVolume.GetOutput())
		else:
			self.outlineFilter.SetInputConnection(self.buildVolume.GetOutputPort())

		# Build volume outline mapper.
		self.buildVolumeMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
		    self.buildVolumeMapper.SetInput(self.outlineFilter.GetOutput())
		else:
		    self.buildVolumeMapper.SetInputConnection(self.outlineFilter.GetOutputPort())

		# Build volume outline actor.
		self.buildVolumeActor = vtk.vtkActor()
		self.buildVolumeActor.SetMapper(self.buildVolumeMapper)

	def getActor(self):
		return self.buildVolumeActor

	def resize(self, buildVolumeSize):
		self.buildVolume.SetCenter(buildVolumeSize[0]/2.0, buildVolumeSize[1]/2.0, buildVolumeSize[2]/2.0)
		self.buildVolume.SetXLength(buildVolumeSize[0])
		self.buildVolume.SetYLength(buildVolumeSize[1])
		self.buildVolume.SetZLength(buildVolumeSize[2])






 ##  ##  ####  #####   ##### ##       #####   #### ###### ####
 ###### ##  ## ##  ## ##     ##       ##  ## ##  ##  ##  ##  ##
 ###### ##  ## ##  ## ####   ##       ##  ## ##  ##  ##  ##  ##
 ##  ## ##  ## ##  ## ##     ##       ##  ## ######  ##  ######
 ##  ## ##  ## ##  ## ##     ##       ##  ## ##  ##  ##  ##  ##
 ##  ##  ####  #####   ##### ######   #####  ##  ##  ##  ##  ##



################################################################################
# Model data. ##################################################################
################################################################################
class modelData:
	""" Create a model object containing the whole 3d data, the preview
	slice stack as well as all the methods for changing (scaling etc.)
	the model, slicing and retrieving info about the model. This also
	includes actors for rendering and the preview slice stack.
	"""

	def __init__(self, filename, slicePath, settings, programSettings, console=None):


		# Set up variables.
		# Internalise settings.
		self.filenameStl = ""
		self.filename = filename
		self.flagactive = True
		self.slicePath = slicePath
		self.settings = settings
		self.programSettings = programSettings
		self.console = console

		# Set up values for model positioning.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0

		self.flagChanged = False
		self.flagUpdateSupports = False
		self.flagUpdateSlices = False

		# Get settings.
		# Model settings.
		self.active = self.settings['active'].value
		self.scaling = self.settings['scaling'].value
		self.rotationX = self.settings['rotationX'].value
		self.rotationY = self.settings['rotationY'].value
		self.rotationZ = self.settings['rotationZ'].value
		self.positionX = self.settings['positionX'].value
		self.positionY = self.settings['positionY'].value
		self.bottomClearance = self.settings['bottomClearance'].value
		self.modelSafetyDistance = self.programSettings['modelSafetyDistance'].value
		self.buildSizeX = self.programSettings['buildSizeX'].value
		self.buildSizeY = self.programSettings['buildSizeY'].value
		self.buildSizeZ = self.programSettings['buildSizeZ'].value



		# Support settings.
		self.createBottomPlate = self.settings['createBottomPlate'].value
		self.createSupports = self.settings['createSupports'].value
		self.bottomPlateThickness = self.settings['bottomPlateThickness'].value
		self.overhangAngle = self.settings['overhangAngle'].value
		self.spacingX = self.settings['spacingX'].value
		self.spacingY = self.settings['spacingY'].value
		self.maximumHeight = self.settings['maximumHeight'].value
		self.baseDiameter = self.settings['baseDiameter'].value
		self.tipDiameter = self.settings['tipDiameter'].value
		self.coneHeight = self.settings['coneHeight'].value
		# Slicer settings.
		self.projectorSizeX = self.programSettings['projectorSizeX'].value
		self.projectorSizeY = self.programSettings['projectorSizeY'].value
		#self.previewSlicesMax = self.programSettings['previewSlicesMax'].value
		self.previewSliceWidth = self.programSettings['previewSliceWidth'].value
		self.layerHeight = self.programSettings['layerHeight'].value
		self.printHollow = self.settings['printHollow'].value
		self.fill = self.settings['fill'].value
		self.fillShellWallThickness = self.settings['fillShellWallThickness'].value
		self.fillSpacing = self.settings['fillSpacing'].value
		self.fillPatternWallThickness = self.settings['fillPatternWallThickness'].value




		self.flagSlicerRunning = False
		self.flagSlicerFinished = False

		# Set up the slice stack. Has one slice only at first...
		self.sliceStack = sliceStack()
		self.slicePosition = (0,0)




		# Set up pipeline. ###################################################
		# Stl
		# --> Polydata
		# --> Calc normals
		# --> Scale
		# --> Move to origin
		# --> Rotate
		# --> Move to desired position.
		# --> Create overhang model.
		# --> Intersect support pattern with overhang model.
		# --> Create supports on intersection points.
		if self.filename != "":
			# Create VTK error observer to catch errors.
			self.errorObserver = ErrorObserver()
			# Create stl source.
			self.stlReader = vtk.vtkSTLReader() # File name will be set later on when model is actually loaded.
			self.stlReader.ScalarTagsOn() # Assign a scalar value to polydata to identify individual solids.
			self.stlReader.SetFileName(self.filename)
			self.stlReader.Update() # Required with VTK6, otherwise the file isn't loaded

			'''
			# TEST CONNECTIVITY.
			stlRegionFilter = vtk.vtkConnectivityFilter()
			stlRegionFilter.SetInput(self.stlReader.GetOutput())
			stlRegionFilter.SetExtractionModeToAllRegions()
			stlRegionFilter.ScalarConnectivityOff()
			stlRegionFilter.ColorRegionsOn()
			stlRegionFilter.Update()
			# Check if multi body checking is enabled.
					#	stlRegionFilter.Update()
			print stlRegionFilter.GetOutput()
			print stlRegionFilter.GetOutput().GetCellData().GetScalars().GetSize()

			for i in range(stlRegionFilter.GetOutput().GetCellData().GetScalars().GetSize()):
				print "i: " + str(i)
				print stlRegionFilter.GetOutput().GetCellData().GetScalars().GetValue(i)

		  	# Loop through regions and get cells.
			# 			for region in range(stlRegionFilter.GetNumberOfExtractedRegions()):
			#				print "Extracting cells from region " + str(region)
				#			stlThreshold.ThresholdBetween(region, region)
			  	#			stlThreshold.Update()
			  	#			print stlThreshold.GetOutput()
		  			#print stlThreshold.GetOutput()
		  	# END TEST CONNECTIVITY.
			'''

			# Get polydata from stl file.
			self.stlPolyData = self.stlReader.GetOutput()
			# Calculate normals.
			self.stlPolyDataNormals = vtk.vtkPolyDataNormals()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.stlPolyDataNormals.SetInput(self.stlPolyData)	# Note: stlPolyData is a data object, hence no GetOutput() method is needed.
			else:
				self.stlPolyDataNormals.SetInputConnection(self.stlReader.GetOutputPort())
			self.stlPolyDataNormals.SplittingOff()	# Don't split sharp edges using feature angle.
			self.stlPolyDataNormals.ComputePointNormalsOn()
			self.stlPolyDataNormals.ComputeCellNormalsOff()
			#self.stlPolyDataNormals.Update()
			# Move to origin filter. Input is stl polydata.
			self.stlCenterTransform = vtk.vtkTransform() # Empty transformation matrix.
			self.stlCenterFilter = vtk.vtkTransformFilter()
			self.stlCenterFilter.SetTransform(self.stlCenterTransform)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.stlCenterFilter.SetInput(self.stlPolyDataNormals.GetOutput())
			else:
				self.stlCenterFilter.SetInputConnection(self.stlPolyDataNormals.GetOutputPort())
			# Scale filter. Input is scale filter.
			self.stlScaleTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlScaleFilter = vtk.vtkTransformFilter()
			self.stlScaleFilter.SetTransform(self.stlScaleTransform)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.stlScaleFilter.SetInput(self.stlCenterFilter.GetOutput())
			else:
				self.stlScaleFilter.SetInputConnection(self.stlCenterFilter.GetOutputPort())
			# Rotate filter. Input is move filter.
			self.stlRotateTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlRotationFilter=vtk.vtkTransformPolyDataFilter()
			self.stlRotationFilter.SetTransform(self.stlRotateTransform)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.stlRotationFilter.SetInput(self.stlScaleFilter.GetOutput())
			else:
				self.stlRotationFilter.SetInputConnection(self.stlScaleFilter.GetOutputPort())
			# Move to position filter. Input is rotate filter.
			self.stlPositionTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlPositionFilter = vtk.vtkTransformFilter()
			self.stlPositionFilter.SetTransform(self.stlPositionTransform)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.stlPositionFilter.SetInput(self.stlRotationFilter.GetOutput())
			else:
				self.stlPositionFilter.SetInputConnection(self.stlRotationFilter.GetOutputPort())
			# Create clipping filter. Use normals to clip stl.
			self.overhangClipFilter = vtk.vtkClipPolyData()
			self.overhangClipFilter.GenerateClipScalarsOff()
			self.overhangClipFilter.SetInsideOut(1)
			self.overhangClipFilter.GenerateClippedOutputOff()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.overhangClipFilter.SetInput(self.stlPositionFilter.GetOutput())
			else:
				self.overhangClipFilter.SetInputConnection(self.stlPositionFilter.GetOutputPort())
			# Define cell locator for intersections of support pattern and overhang model.
			self.locator = vtk.vtkCellLocator()
			self.locator.SetDataSet(self.overhangClipFilter.GetOutput())	#TODO: change to selected region input.

			# Create supports polydata.
			self.supports = vtk.vtkAppendPolyData()
			self.supports.AddObserver('ErrorEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION >= 6:
				self.supports.UserManagedInputsOn()

			# Create bottom plate polydata. Edge length 1 mm, place outside of build volume by 1 mm.
			self.bottomPlate = vtk.vtkCubeSource()
			self.bottomPlate.SetXLength(1)
			self.bottomPlate.SetYLength(1)
			self.bottomPlate.SetZLength(1)
			self.bottomPlate.SetCenter((-1, -1, -1))


			# The following is for 3D slice data. ################################
			# Create cutting plane, clip filter, cutting filter and cut line polydata.
			self.extrusionVector = (0,0,-1)
			# Create cutting plane.
			self.cuttingPlane = vtk.vtkPlane()
			self.cuttingPlane.SetNormal(0,0,-1)
			self.cuttingPlane.SetOrigin(0,0,0.001)	# Make sure bottom plate is cut properly.
			# Create clip filter for model.
			self.clipFilterModel = vtk.vtkClipPolyData()
			self.clipFilterModel.SetClipFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.clipFilterModel.SetInput(self.stlPositionFilter.GetOutput())
			else:
				self.clipFilterModel.SetInputConnection(self.stlPositionFilter.GetOutputPort())
			# Create clip filter for model.
			self.clipFilterSupports = vtk.vtkClipPolyData()
			self.clipFilterSupports.SetClipFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.clipFilterSupports.SetInput(self.supports.GetOutput())
			else:
				self.clipFilterSupports.SetInputConnection(self.supports.GetOutputPort())
			# Create clip filter for model.
			self.clipFilterBottomPlate = vtk.vtkClipPolyData()
			self.clipFilterBottomPlate.SetClipFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.clipFilterBottomPlate.SetInput(self.bottomPlate.GetOutput())
			else:
				self.clipFilterBottomPlate.SetInputConnection(self.bottomPlate.GetOutputPort())
			# Combine clipped models.
			self.combinedClipModels = vtk.vtkAppendPolyData()
			self.combinedClipModels.AddObserver('ErrorEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.combinedClipModels.AddInput(self.clipFilterModel.GetOutput())
				self.combinedClipModels.AddInput(self.clipFilterSupports.GetOutput())
				self.combinedClipModels.AddInput(self.clipFilterBottomPlate.GetOutput())
			else:
				self.combinedClipModels.UserManagedInputsOn()
				self.combinedClipModels.SetNumberOfInputs(3)
				self.combinedClipModels.SetInputConnectionByNumber(0, self.clipFilterModel.GetOutputPort())
				self.combinedClipModels.SetInputConnectionByNumber(1, self.clipFilterSupports.GetOutputPort())
				self.combinedClipModels.SetInputConnectionByNumber(2, self.clipFilterBottomPlate.GetOutputPort())
			# Create cutting filter for model.
			self.cuttingFilterModel = vtk.vtkCutter()
			self.cuttingFilterModel.SetCutFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.cuttingFilterModel.SetInput(self.stlPositionFilter.GetOutput())
			else:
				self.cuttingFilterModel.SetInputConnection(self.stlPositionFilter.GetOutputPort())
			# Create cutting filter for supports.
			self.cuttingFilterSupports = vtk.vtkCutter()
			self.cuttingFilterSupports.SetCutFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.cuttingFilterSupports.SetInput(self.supports.GetOutput())
			else:
				self.cuttingFilterSupports.SetInputConnection(self.supports.GetOutputPort())
			# Create cutting filter for bottom plate.
			self.cuttingFilterBottomPlate = vtk.vtkCutter()
			self.cuttingFilterBottomPlate.SetCutFunction(self.cuttingPlane)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.cuttingFilterBottomPlate.SetInput(self.bottomPlate.GetOutput())
			else:
				self.cuttingFilterBottomPlate.SetInputConnection(self.bottomPlate.GetOutputPort())
			# Create polylines from cutter output for model.
			self.sectionStripperModel = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.sectionStripperModel.SetInput(self.cuttingFilterModel.GetOutput())
			else:
				self.sectionStripperModel.SetInputConnection(self.cuttingFilterModel.GetOutputPort())
			#TODO: remove scalars so color is white.
			#self.sectionStripperModel.GetOutput().GetPointData().RemoveArray('normalsZ')
			# Create polylines from cutter output for supports.
			self.sectionStripperSupports = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.sectionStripperSupports.SetInput(self.cuttingFilterSupports.GetOutput())
			else:
				self.sectionStripperSupports.SetInputConnection(self.cuttingFilterSupports.GetOutputPort())
			# Create polylines from cutter output for bottom plate.
			self.sectionStripperBottomPlate = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.sectionStripperBottomPlate.SetInput(self.cuttingFilterBottomPlate.GetOutput())
			else:
				self.sectionStripperBottomPlate.SetInputConnection(self.cuttingFilterBottomPlate.GetOutputPort())
			# Combine cut lines from model, supports and bottom plate. This is for display only.
			self.combinedCutlines = vtk.vtkAppendPolyData()
			self.combinedCutlines.AddObserver('ErrorEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.combinedCutlines.AddInput(self.sectionStripperModel.GetOutput())
				self.combinedCutlines.AddInput(self.sectionStripperSupports.GetOutput())
				self.combinedCutlines.AddInput(self.sectionStripperBottomPlate.GetOutput())
			else:
				self.combinedCutlines.UserManagedInputsOn()
				self.combinedCutlines.SetNumberOfInputs(4)
				self.combinedCutlines.SetInputConnectionByNumber(0, self.sectionStripperModel.GetOutputPort())
				self.combinedCutlines.SetInputConnectionByNumber(1, self.sectionStripperSupports.GetOutputPort())
				self.combinedCutlines.SetInputConnectionByNumber(2, self.sectionStripperBottomPlate.GetOutputPort())

			# Create a small cone to have at least one input
			# to the slice line vtkAppendPolyData in case no
			# model intersections were found.
			cone = vtk.vtkConeSource()
			cone.SetRadius(.01)
			cone.SetHeight(.01)
			cone.SetResolution(6)
			cone.SetCenter([-.1,-.1,-.1])
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.combinedCutlines.AddInput(cone.GetOutput())
			else:
				self.combinedCutlines.SetInputConnectionByNumber(3, cone.GetOutputPort())

			# Bounding box. Create cube and set outline filter.
			self.modelBoundingBox = vtk.vtkCubeSource()
			self.modelBoundingBox.SetCenter(self.getCenter()[0], self.getCenter()[1], self.getBounds()[5]/2)
			self.modelBoundingBox.SetXLength(self.getSize()[0])
			self.modelBoundingBox.SetYLength(self.getSize()[1])
			self.modelBoundingBox.SetZLength(self.getBounds()[5])
			# Model bounding box outline filter.
			self.modelBoundingBoxOutline = vtk.vtkOutlineFilter()
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.modelBoundingBoxOutline.SetInput(self.modelBoundingBox.GetOutput())
			else:
				self.modelBoundingBoxOutline.SetInputConnection(self.modelBoundingBox.GetOutputPort())

			self.updateSlice3d(0)

		######################################################################
		# Create mappers and actors. #########################################
		######################################################################

		# Create model mapper. ***********************************************
		self.stlMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
			self.stlMapper.SetInput(self.stlPositionFilter.GetOutput())
		elif self.filename != "":
			self.stlMapper.SetInputConnection(self.stlPositionFilter.GetOutputPort())
		# Create model actor.
		self.stlActor = vtk.vtkActor()
		if self.filename != "":
			self.stlActor.SetMapper(self.stlMapper)

		# Create overhang mapper. ********************************************
		self.overhangClipMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
			self.overhangClipMapper.SetInput(self.overhangClipFilter.GetOutput())
		elif self.filename != "":
			self.overhangClipMapper.SetInputConnection(self.overhangClipFilter.GetOutputPort())
		# Create overhang actor.
		self.overhangClipActor = vtk.vtkActor()
		if self.filename != "":
			self.overhangClipActor.SetMapper(self.overhangClipMapper)

		# Create supports mapper. ********************************************
		# TODO: this throws empty pipeline errors on instatiation as self.supports does not have any input yet.
		self.supportsMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
			self.supportsMapper.SetInput(self.supports.GetOutput())
		elif self.filename != "":
			self.supportsMapper.SetInputConnection(self.supports.GetOutputPort())
		# Create supports actor.
		self.supportsActor = vtk.vtkActor()
		if self.filename != "":
			self.supportsActor.SetMapper(self.supportsMapper)

		# Bottom plate mapper. ***********************************************
		self.bottomPlateMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
		    self.bottomPlateMapper.SetInput(self.bottomPlate.GetOutput())
		elif self.filename != "":
		    self.bottomPlateMapper.SetInputConnection(self.bottomPlate.GetOutputPort())
		# Bottom plate actor.
		self.bottomPlateActor = vtk.vtkActor()
		if self.filename != "":
			self.bottomPlateActor.SetMapper(self.bottomPlateMapper)

		# Bounding box outline mapper with annotation. ***********************
		self.modelBoundingBoxMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
		    self.modelBoundingBoxMapper.SetInput(self.modelBoundingBoxOutline.GetOutput())
		elif self.filename != "":
		    self.modelBoundingBoxMapper.SetInputConnection(self.modelBoundingBoxOutline.GetOutputPort())
		# Bounding box outline actor.
		self.modelBoundingBoxActor = vtk.vtkActor()
		if self.filename != "":
			self.modelBoundingBoxActor.SetMapper(self.modelBoundingBoxMapper)

		# Clipped model mapper. **********************************************
		self.clipFilterMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
			self.clipFilterMapper.SetInput(self.combinedClipModels.GetOutput())
		elif self.filename != "":
			self.clipFilterMapper.SetInputConnection(self.combinedClipModels.GetOutputPort())
		# Cut lines actor.
		self.clipFilterActor = vtk.vtkActor()
		if self.filename != "":
			self.clipFilterActor.SetMapper(self.clipFilterMapper)

		# Cut lines mapper. **************************************************
		self.cuttingFilterMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5 and self.filename != "":
			self.cuttingFilterMapper.SetInput(self.combinedCutlines.GetOutput())
		elif self.filename != "":
			self.cuttingFilterMapper.SetInputConnection(self.combinedCutlines.GetOutputPort())
		# Cut lines actor.
		self.cuttingFilterActor = vtk.vtkActor()
		if self.filename != "":
			self.cuttingFilterActor.SetMapper(self.cuttingFilterMapper)

		# Text actor for model size. *****************************************
		self.modelBoundingBoxTextActor = vtk.vtkCaptionActor2D()
		self.modelBoundingBoxTextActor.GetTextActor().SetTextScaleModeToNone()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontFamilyToArial()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontSize(11)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetOpacity(.5)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ShadowOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ItalicOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().BoldOff()
		self.modelBoundingBoxTextActor.BorderOff()
		self.modelBoundingBoxTextActor.LeaderOff()
		self.modelBoundingBoxTextActor.SetPadding(0)



		######################################################################
		# Other stuff. #######################################################
		######################################################################

		# Get volume.
		if self.filename != "":
			self.volumeModel = vtk.vtkMassProperties()
			self.volumeModel.AddObserver('WarningEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.volumeModel.SetInput(self.stlPositionFilter.GetOutput())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()
			else:
				self.volumeModel.SetInputConnection(self.stlPositionFilter.GetOutputPort())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()
			self.volumeSupports = vtk.vtkMassProperties()
			self.volumeSupports.AddObserver('WarningEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.volumeSupports.SetInput(self.supports.GetOutput())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()
			else:
				self.volumeSupports.SetInputConnection(self.supports.GetOutputPort())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()
			self.volumeBottomPlate = vtk.vtkMassProperties()
			self.volumeBottomPlate.AddObserver('WarningEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.volumeBottomPlate.SetInput(self.bottomPlate.GetOutput())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()
			else:
				self.volumeBottomPlate.SetInputConnection(self.bottomPlate.GetOutputPort())
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Warning: " + self.errorObserver.ErrorMessage()


		# Finally, update the pipeline.
		if self.filename != "":
			self.stlPositionFilter.Update()
			# If there are no points in 'vtkPolyData' something went wrong
			if self.stlPolyData.GetNumberOfPoints() == 0:
				if self.console:
					self.console.addLine("No points found in stl file.")
			else:
				if self.console:
					self.console.addLine('Model loaded successfully.')
					self.console.addLine('   ' + str(self.stlPolyData.GetNumberOfPoints()) + " points loaded.")
					self.console.addLine('   ' + str(self.stlPolyData.GetNumberOfPolys()) + " polygons loaded.")


		########################################################################
		# Create background thread for updating the slices on demand. ##########
		########################################################################
		self.queueSlicerIn = Queue.Queue()
		self.queueSlicerOut = Queue.Queue()
		if self.filename != "":
			# Initialise the thread.
			if self.console!=None:
				self.console.addLine("Starting slicer thread")
			self.slicerThread = backgroundSlicer(self.slicePath, self.stlPositionFilter.GetOutput(), self.supports.GetOutput(), self.bottomPlate.GetOutput(), self.queueSlicerIn, self.queueSlicerOut, self.console)
			self.slicerThread.start()


	# #########################################################################
	# Public method definitions. ##############################################
	# #########################################################################

	# Change active flag.
	def setactive(self, active):
		self.flagactive = active

	# Check active flag.
	def isactive(self):
		return self.flagactive

	# Analyse normal Z component.
	def getNormalZComponent(self, inputPolydata):
		normalsZ = vtk.vtkFloatArray()
		normalsZ.SetNumberOfValues(inputPolydata.GetPointData().GetArray('Normals').GetNumberOfTuples())
		normalsZ.CopyComponent(0,inputPolydata.GetPointData().GetArray('Normals'),2)
		inputPolydata.GetPointData().SetScalars(normalsZ)
		return inputPolydata

	def getHeight(self):
		if self.filename != "":
			return self.__getBounds(self.stlPositionFilter)[5]
		else:
			return 0


	def getSize(self):
		return self.__getSize(self.stlPositionFilter)

	def getVolume(self):
		if self.filename != "":

			self.volumeModel.Update()
			if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
				print "VTK Warning: " + self.errorObserver.ErrorMessage()
			# TODO: mass properties throws some errors here, possibly because the support polydata contains non-triangles.
			# THis can only be the cylinders.
			# Maybe triangulate them first somehow...
			# Only update supports volume if there are supports in the appendPolyData.
			if self.supports.GetNumberOfInputConnections(0) > 0:
				self.volumeSupports.Update()
				if self.programSettings['showVtkErrors'].value and self.errorObserver.WarningOccurred():
					print "VTK Warning: " + self.errorObserver.WarningMessage()
#				elif self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
#					print "VTK Error: " + self.errorObserver.ErrorMessage()
			self.volumeBottomPlate.Update()
			if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()

			# Get volume in mm³.
			if self.supports.GetNumberOfInputConnections(0) > 0:

				volume = self.volumeModel.GetVolume() + self.volumeSupports.GetVolume() + self.volumeBottomPlate.GetVolume()
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Error: " + self.errorObserver.ErrorMessage()
			else:
				volume = self.volumeModel.GetVolume() + self.volumeBottomPlate.GetVolume()
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Error: " + self.errorObserver.ErrorMessage()
			# Convert to cm³ and round to 2 decimals.
			volume = math.trunc(volume / 10.) /100.
			return volume
		else:
			return 0.0


	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)

	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)

	def getHeightSupports(self):
		if self.filename != "":
			return self.__getBounds(self.supports)[5]
		else:
			return 0


	def getBoundsSafety(self):
		bounds = self.__getBounds(self.stlPositionFilter)
		dist = self.programSettings['modelSafetyDistance'].value
		bounds = [	bounds[0]-dist,
					bounds[1]+dist,
					bounds[2]-dist,
					bounds[3]+dist,
					bounds[4]-dist,
					bounds[5]+dist	]
		return bounds

	def getBoundsOverhang(self):
		return self.__getBounds(self.overhangClipFilter)

	def getFilename(self):
		return self.filename


	def getPolydata(self):
		return self.stlPositionFilter.GetOutput()


	def setChanged(self):
		self.flagChanged = True

	def setChangedSupports(self):
		self.flagChangedSupports = True



	###########################################################################
	# Update methods. #########################################################
	###########################################################################
	def updateModel(self):
		if self.filename != "":
			if self.isactive() and self.settingsChangedModel():
				#print "   UPDATING MODEL"
				self.flagSlicerFinished = False

				# TEST: print multi body scalars.
	#			print self.stlReader.GetScalarTags()
	#			print self.stlReader.GetOutput()#.GetCellData().GetScalars()
	#			print self.stlReader.GetScalarTags()






				# Move model to origin. ****
				self.stlCenterTransform.Translate(-self.__getCenter(self.stlScaleFilter)[0], -self.__getCenter(self.stlScaleFilter)[1], -self.__getCenter(self.stlScaleFilter)[2])
				self.stlCenterFilter.Update()

				# Rotate. ******************
				# Reset rotation.
	#			print "Orientation old: " + str(self.stlRotateTransform.GetOrientation())
				self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[0], 1,0,0)
				self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[1], 0,1,0)
				self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[2], 0,0,1)
	#			print "Orientation reset: " + str(self.stlRotateTransform.GetOrientation())
	#			print "Orientation from settings: " + str(modelSettings.getRotationXYZ())
				# Rotate with new angles.
				self.stlRotateTransform.RotateWXYZ(self.settings['rotationX'].value,1,0,0)
				self.stlRotateTransform.RotateWXYZ(self.settings['rotationY'].value,0,1,0)
				self.stlRotateTransform.RotateWXYZ(self.settings['rotationZ'].value,0,0,1)
	#			print "Orientation new: " + str(self.stlRotateTransform.GetOrientation())
				# Update filter.
				self.stlRotationFilter.Update()

				# Check if scaling factor has to be adjusted to make model fit in build space.
				# Get current scaling factor.
				currentScale = self.stlScaleTransform.GetScale()[0]
				# Get current size after rotation.
				self.dimX = self.__getSize(self.stlRotationFilter)[0]
				self.dimY = self.__getSize(self.stlRotationFilter)[1]
				self.dimZ = self.__getSize(self.stlRotationFilter)[2]

				# Compare the ratio of model size plus safety distance to build volume size in all dimensions with each other.
				# Return smallest ratio as maximum scaling.
				smallestRatio = 1
				if ((self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimX) <= ((self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimY) and ((self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimX) <= (self.programSettings['buildSizeZ'].value / self.dimZ):
					smallestRatio =  (self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimX * currentScale
				elif ((self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimY) <= ((self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimX) and ((self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimY) <= (self.programSettings['buildSizeZ'].value / self.dimZ):
					smallestRatio =  (self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimY * currentScale
				elif (self.programSettings['buildSizeZ'].value / self.dimZ) <= ((self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimX) and (self.programSettings['buildSizeZ'].value / self.dimZ) <= ((self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) / self.dimY):
					smallestRatio =  self.programSettings['buildSizeZ'].value / self.dimZ * currentScale
				# Restrict input scalingFactor if necessary.
				if smallestRatio < self.settings['scaling'].value:
					self.settings['scaling'].setValue(smallestRatio)

				# Scale. *******************
				# First, reset scale to 1.
				self.stlScaleTransform.Scale(1/self.stlScaleTransform.GetScale()[0], 1/self.stlScaleTransform.GetScale()[1], 1/self.stlScaleTransform.GetScale()[2])
				# Change scale value.
				self.stlScaleTransform.Scale(self.settings['scaling'].value, self.settings['scaling'].value, self.settings['scaling'].value)
				self.stlScaleFilter.Update()	# Update to get new bounds.

				# Position. ****************
				# Subtract safety distance from build volume in X and Y directions. Z doesn't need safety space.
				clearRangeX = (self.programSettings['buildSizeX'].value-2*self.programSettings['modelSafetyDistance'].value) - self.__getSize(self.stlRotationFilter)[0]
				clearRangeY = (self.programSettings['buildSizeY'].value-2*self.programSettings['modelSafetyDistance'].value) - self.__getSize(self.stlRotationFilter)[1]
				positionZMax = self.programSettings['buildSizeZ'].value - self.__getSize(self.stlRotationFilter)[2]
				if self.settings['bottomClearance'].value > positionZMax:
					self.settings['bottomClearance'].setValue(positionZMax)
				self.stlPositionTransform.Translate(  ((self.__getSize(self.stlRotationFilter)[0]/2 + clearRangeX * (self.settings['positionX'].value / 100.0)) - self.stlPositionTransform.GetPosition()[0]) + self.programSettings['modelSafetyDistance'].value,      ((self.__getSize(self.stlRotationFilter)[1]/2 + clearRangeY * (self.settings['positionY'].value / 100.0)) - self.stlPositionTransform.GetPosition()[1]) + self.programSettings['modelSafetyDistance'].value,       self.__getSize(self.stlRotationFilter)[2]/2 - self.stlPositionTransform.GetPosition()[2] + self.settings['bottomClearance'].value)
				self.stlPositionFilter.Update()
				# Recalculate normals.
				self.getNormalZComponent(self.stlPositionFilter.GetOutput())
				# Reposition bounding box.
				self.modelBoundingBox.SetCenter(self.getCenter()[0], self.getCenter()[1],self.getBounds()[5]/2)
				self.modelBoundingBox.SetXLength(self.getSize()[0])
				self.modelBoundingBox.SetYLength(self.getSize()[1])
				self.modelBoundingBox.SetZLength(self.getBounds()[5])
				self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()) )
				self.modelBoundingBoxTextActor.SetAttachmentPoint(self.getBounds()[1], self.getBounds()[3], self.getBounds()[5])

				self.flagChanged = True
				self.flagUpdateSupports = True

				# Return true if model was changed.
				return True
			# Return false if model was not changed.
			return False
		# Return false if this is default model.
		return False


	def updateBottomPlate(self):
		if self.filename != "" and self.isactive() and self.flagUpdateSupports:
			self.flagSlicerFinished = False
			modelBounds = self.getBounds()
			self.bottomPlate.SetXLength(modelBounds[1] - modelBounds[0])
			self.bottomPlate.SetYLength(modelBounds[3] - modelBounds[2])
			self.bottomPlate.SetZLength(self.settings['bottomPlateThickness'].value)
			self.bottomPlate.SetCenter( (modelBounds[0] + modelBounds[1]) / 2.0, (modelBounds[2] + modelBounds[3]) / 2.0, self.settings['bottomPlateThickness'].value/2.0)
			self.bottomPlate.Update()
			self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()) )

			self.flagChanged = True
			self.flagUpdateSlices = True

	def updateOverhang(self):
		if self.filename != "" and self.isactive():
			self.flagSlicerFinished = False
			# Calculate clipping threshold based on Z component..
			# Z normals are 1 if pointing upwards, -1 if downwards and 0 if pointing sideways.
			# Turn angle into value between -1 and 0.
			self.clipThreshold = -math.cos(self.settings['overhangAngle'].value/180.0*math.pi)
			self.overhangClipFilter.SetValue(self.clipThreshold)
			self.overhangClipFilter.Update()

	#		self.flagChanged = True

	# Update supports. ########################################################
	def updateSupports(self):
		# Conditions to update supports:
		# - Model is not default model.
		# - Model is active.
		# - Model has been updated or support settings have been changed.
		if self.filename != "":
			if self.isactive() and (self.flagUpdateSupports or self.settingsChangedSupports()):
				#print "   UPDATING SUPPORTS"
				self.flagSlicerFinished = False

				self.updateBottomPlate()
				self.updateOverhang()

				# Clear all inputs from cones data.
				if vtk.VTK_MAJOR_VERSION <= 5:
					self.supports.RemoveAllInputs()
				else:
					support_inputs = 1
					self.supports.SetNumberOfInputs(0)
					self.supports.SetNumberOfInputs(support_inputs)

				# Create one super small cone to have at least one input
				# to the vtkAppendPolyData in case no model intersections
				# were found.
				cone = vtk.vtkConeSource()
				# Set cone dimensions.
				cone.SetRadius(.01)
				cone.SetHeight(.01)
				cone.SetResolution(6)
				cone.SetCenter([-.1,-.1,-.1])
				if vtk.VTK_MAJOR_VERSION <= 5:
					self.supports.AddInput(cone.GetOutput())
				else:
					self.supports.SetInputConnectionByNumber(0, cone.GetOutputPort())

		#TODO: Add support regions using overhangRegionFilter.Update();

				# Update the cell locator.
				self.locator.BuildLocator()
				self.locator.Update()
				if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Error: " + self.errorObserver.ErrorMessage()

				# Get overhang bounds to set up support pattern.
				# Bounds are absolute coordinates.
				bounds = [0 for i in range(6)]
				bounds = self.getBoundsOverhang()

				# Get input data center.
				center = [0 for i in range(3)]
				center[0] = (bounds[1] + bounds[0]) / 2.0
				center[1] = (bounds[3] + bounds[2]) / 2.0
				center[2] = (bounds[5] + bounds[4]) / 2.0

				# Create support pattern bounds.
				# Number of supports in each direction of center.
				nXMin = int(math.floor((center[0] - bounds[0]) / self.settings['spacingX'].value))
				nXMax = int(math.floor((bounds[1] - center[0]) / self.settings['spacingX'].value))
				nYMin = int(math.floor((center[1] - bounds[2]) / self.settings['spacingY'].value))
				nYMax = int(math.floor((bounds[3] - center[1]) / self.settings['spacingY'].value))


				# Start location, first point of pattern.
				startX = center[0] - nXMin * self.settings['spacingX'].value
				startY = center[1] - nYMin * self.settings['spacingY'].value


				# Number of points in X and Y.
				nX = nXMin + nXMax + 1	# +1 because of center support, nXMin and nXMax only give number of supports to each side of center.
				nY = nYMin + nYMax + 1	# +1 because of center support...
			#	i = 0
				# Loop through point grid and check for intersections.
				for iX in range(nX):
					for iY in range(nY):
						# Get X and Y values.
						pointX = startX + iX * self.settings['spacingX'].value
						pointY = startY + iY * self.settings['spacingY'].value

						# Combine to bottom and top point.
						pointBottom = [pointX, pointY, 0]
						pointTop = [pointX, pointY, self.settings['maximumHeight'].value]

						# Create outputs for intersector.
						t = vtk.mutable(0)			# not needed.
						pos = [0.0, 0.0, 0.0]		# that's what we're looking for.
						pcoords = [0.0, 0.0, 0.0]	# not needed.
						subId = vtk.mutable(0)		# not needed.
						tolerance = 0.001

						# Intersect.
						self.locator.IntersectWithLine(pointBottom, pointTop, tolerance, t, pos, pcoords, subId)
						if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
							print "VTK Error: " + self.errorObserver.ErrorMessage()

						# Create cone if intersection point found.
						if pos != [0,0,0]:
							# Create cone.
							cone = vtk.vtkConeSource()
							# Set cone dimensions.
							cone.SetRadius(self.settings['baseDiameter'].value/2.0)
							cone.SetHeight(self.settings['coneHeight'].value)
							cone.SetResolution(20)
							# Set cone position (at cone center) according to current point.
							pos[2] = pos[2]-self.settings['coneHeight'].value/2.0
							# Adjust cone Z position to meet tip connection diameter.
							pos[2] = pos[2]+1.0*self.settings['coneHeight'].value/(1.0*self.settings['baseDiameter'].value/self.settings['tipDiameter'].value)
							cone.SetCenter(pos)

							# Rotate the cone tip upwards.
							coneRotation = vtk.vtkRotationFilter()
							if vtk.VTK_MAJOR_VERSION <= 5:
								coneRotation.SetInput(cone.GetOutput())
							else:
								coneRotation.SetInputConnection(cone.GetOutputPort())
							coneRotation.SetAxisToY()
							coneRotation.SetCenter(pos)
							coneRotation.SetAngle(-90)
							coneRotation.SetNumberOfCopies(1)
							coneRotation.CopyInputOff()

							# Use a geometry filter to convert rotation filter output
							# from unstructuredGrid to polyData.
							coneGeomFilter = vtk.vtkGeometryFilter()
							if vtk.VTK_MAJOR_VERSION <= 5:
								coneGeomFilter.SetInput(coneRotation.GetOutput())
							else:
								coneGeomFilter.SetInputConnection(coneRotation.GetOutputPort())
							coneGeomFilter.Update()

							# Create cylinder.
							cylinder = vtk.vtkCylinderSource()
							# Set cylinder dimensions.
							cylinder.SetRadius(self.settings['baseDiameter'].value/2.0)
							cylinder.SetHeight(pos[2]-self.settings['coneHeight'].value/2.0)
							cylinder.SetResolution(20)

							# Set cylinder position.
							# Adjust height to fit beneath corresponding cone.
							pos[2] = (pos[2]-self.settings['coneHeight'].value/2.0)/2.0
							cylinder.SetCenter(pos)

							# Rotate the cone tip upwards.
							cylinderRotation = vtk.vtkRotationFilter()
							if vtk.VTK_MAJOR_VERSION <= 5:
								cylinderRotation.SetInput(cylinder.GetOutput())
							else:
								cylinderRotation.SetInputConnection(cylinder.GetOutputPort())
							cylinderRotation.SetAxisToX()
							cylinderRotation.SetCenter(pos)
							cylinderRotation.SetAngle(-90)
							cylinderRotation.SetNumberOfCopies(1)
							cylinderRotation.CopyInputOff()

							# Use a geometry filter to convert rotation filter output
							# from unstructuredGrid to polyData.
							cylinderGeomFilter = vtk.vtkGeometryFilter()
							if vtk.VTK_MAJOR_VERSION <= 5:
								cylinderGeomFilter.SetInput(cylinderRotation.GetOutput())
							else:
								cylinderGeomFilter.SetInputConnection(cylinderRotation.GetOutputPort())
							cylinderGeomFilter.Update()

							# Append the cone to the cones polydata.
							if vtk.VTK_MAJOR_VERSION <= 5:
								self.supports.AddInput(coneGeomFilter.GetOutput())
								if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
									print "VTK Error: " + self.errorObserver.ErrorMessage()
							else:
								support_inputs += 2
								self.supports.SetNumberOfInputs(support_inputs)
								self.supports.SetInputConnectionByNumber(support_inputs - 2, coneGeomFilter.GetOutputPort())
								if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
									print "VTK Error: " + self.errorObserver.ErrorMessage()
							# Delete the cone. Vtk delete() method does not work in python because of garbage collection.
							del cone
							# Append the cylinder to the cones polydata.
							if vtk.VTK_MAJOR_VERSION <= 5:
								self.supports.AddInput(cylinderGeomFilter.GetOutput())
								if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
									print "VTK Error: " + self.errorObserver.ErrorMessage()
							else:
								self.supports.SetInputConnectionByNumber(support_inputs - 1, cylinderGeomFilter.GetOutputPort())
								if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
									print "VTK Error: " + self.errorObserver.ErrorMessage()
							del cylinder
			#				i += 1
			#	print "Created " + str(i) + " supports."
				self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()) )

				self.flagUpdateSupports = False
				self.flagUpdateSlices = True

				# Return true if supports were changed.
				return True
			# Return false if supports were not changed.
			return False
		# Return false if this is default model.
		return False


	def updateSliceStack(self, force=False):
		# Run in the following conditions:
		# - This is not the default model.
		# - Reslice flag is set
		# - Slicer settings have changed
		if self.filename!="":
			# Check if layer height was changed in settings.
			#if not self.layerHeight == self.programSettings['layerHeight'].value:
			#	self.layerHeight = self.programSettings['layerHeight'].value
			#	self.flagChanged = True
			# Only update if this is not default flag and the
			# model or supports have been changed before.
			# Also update in preview mode if forced.
			if self.isactive() and (self.flagUpdateSlices or self.settingsChangedSlicer()):
				#print "UPDATING SLICES"
				if self.console != None:
					self.console.addLine('Slicer started.')

				# Assemble the slicer info.
				slicerInputInfo = {}
				slicerInputInfo['pxPerMmX'] = self.programSettings['pxPerMmX'].value
				slicerInputInfo['pxPerMmY'] = self.programSettings['pxPerMmY'].value
				slicerInputInfo['layerHeight'] = self.programSettings['layerHeight'].value
				slicerInputInfo['numberOfSlices'] = self.getNumberOfSlices()#int(math.floor(self.bounds[5] / self.layerHeight))
				slicerInputInfo['position'] = self.getSlicePositionPx(border=True)
				slicerInputInfo['size'] = self.getSliceSizePx(border=True)
				slicerInputInfo['wallThickness'] = self.settings['fillShellWallThickness'].value
				slicerInputInfo['fillPatternSpacingPxX'] = self.settings['fillSpacing'].value
				slicerInputInfo['fillPatternSpacingPxY'] = self.settings['fillSpacing'].value
				slicerInputInfo['fillPatternWallThickness'] = self.settings['fillPatternWallThickness'].value
				slicerInputInfo['supportHeight'] = self.getHeightSupports()
				slicerInputInfo['createSupports'] = self.settings['createSupports'].value
				slicerInputInfo['createBottomPlate'] = self.settings['createBottomPlate'].value
				slicerInputInfo['debug'] = self.programSettings['debug'].value
				slicerInputInfo['printHollow'] = self.settings['printHollow'].value
				slicerInputInfo['fill'] = self.settings['fill'].value
				slicerInputInfo['showVtkErrors'] = self.programSettings['showVtkErrors'].value
				slicerInputInfo['polylineClosingThreshold'] = self.programSettings['polylineClosingThreshold'].value
				slicerInputInfo['multiBodySlicing'] = self.programSettings['multiBodySlicing'].value
			#
				# If there's nothing in the queue...
				if self.queueSlicerIn.empty():
					# ... write the slicer info to the queue.
					self.queueSlicerIn.put(slicerInputInfo)
				self.flagChanged = False
				self.flagUpdateSlices = False
				self.flagSlicerRunning = True
				self.flagSlicerFinished = False
			# Set finished flag if model was not resliced.
			elif self.isactive():#not self.flagChanged:
				self.flagSlicerFinished = True


	# Listen for the slicer threads output if it has finished.
	def checkBackgroundSlicer(self):
		# If a slice stack is in the output queue...
		if self.queueSlicerOut.qsize():
			# ... get it.
			#if self.console != None:
			#	self.console.addLine('Slicer done.')
			warningSlices = self.queueSlicerOut.get()
			if len(warningSlices) > 0:
					self.console.addLine("Warning: Possible errors in slices " + str(warningSlices))
			self.flagSlicerRunning = False
			self.flagSlicerFinished = True


	def killBackgroundSlicer(self):
		self.slicerThread.stop()


	def settingsChangedModel(self):
		# Check for changes.
		settingsChanged = []
		settingsChanged.append(self.active != self.settings['active'].value)
		settingsChanged.append(self.scaling != self.settings['scaling'].value)
		settingsChanged.append(self.rotationX != self.settings['rotationX'].value)
		settingsChanged.append(self.rotationY != self.settings['rotationY'].value)
		settingsChanged.append(self.rotationZ != self.settings['rotationZ'].value)
		settingsChanged.append(self.positionX != self.settings['positionX'].value)
		settingsChanged.append(self.positionY != self.settings['positionY'].value)
		settingsChanged.append(self.bottomClearance == self.settings['bottomClearance'].value)
		settingsChanged.append(self.createBottomPlate != self.settings['createBottomPlate'].value)
		settingsChanged.append(self.modelSafetyDistance != self.programSettings['modelSafetyDistance'].value)
		settingsChanged.append(self.buildSizeX != self.programSettings['buildSizeX'].value)
		settingsChanged.append(self.buildSizeY != self.programSettings['buildSizeY'].value)
		settingsChanged.append(self.buildSizeZ != self.programSettings['buildSizeZ'].value)

		# Update.
		self.active = self.settings['active'].value
		self.scaling = self.settings['scaling'].value
		self.rotationX = self.settings['rotationX'].value
		self.rotationY = self.settings['rotationY'].value
		self.rotationZ = self.settings['rotationZ'].value
		self.positionX = self.settings['positionX'].value
		self.positionY = self.settings['positionY'].value
		self.bottomClearance = self.settings['bottomClearance'].value
		self.modelSafetyDistance = self.programSettings['modelSafetyDistance'].value
		self.createBottomPlate = self.settings['createBottomPlate'].value
		self.buildSizeX = self.programSettings['buildSizeX'].value
		self.buildSizeY = self.programSettings['buildSizeY'].value
		self.buildSizeZ = self.programSettings['buildSizeZ'].value

		# Return change status.
		return any(settingsChanged)


	def settingsChangedSupports(self):
		# Check for changes.
		settingsChanged = []
		settingsChanged.append(self.createSupports != self.settings['createSupports'].value)
		settingsChanged.append(self.bottomPlateThickness != self.settings['bottomPlateThickness'].value)
		settingsChanged.append(self.overhangAngle != self.settings['overhangAngle'].value)
		settingsChanged.append(self.spacingX != self.settings['spacingX'].value)
		settingsChanged.append(self.spacingY != self.settings['spacingY'].value)
		settingsChanged.append(self.maximumHeight != self.settings['maximumHeight'].value)
		settingsChanged.append(self.baseDiameter != self.settings['baseDiameter'].value)
		settingsChanged.append(self.tipDiameter != self.settings['tipDiameter'].value)
		settingsChanged.append(self.coneHeight != self.settings['coneHeight'].value)
		# Update.
		self.createSupports = self.settings['createSupports'].value
		self.bottomPlateThickness = self.settings['bottomPlateThickness'].value
		self.overhangAngle = self.settings['overhangAngle'].value
		self.spacingX = self.settings['spacingX'].value
		self.spacingY = self.settings['spacingY'].value
		self.maximumHeight = self.settings['maximumHeight'].value
		self.baseDiameter = self.settings['baseDiameter'].value
		self.tipDiameter = self.settings['tipDiameter'].value
		self.coneHeight = self.settings['coneHeight'].value
		# Return change status.
		return any(settingsChanged)


	def settingsChangedSlicer(self):
		# Check for changes.
		settingsChanged = []
		settingsChanged.append(self.projectorSizeX != self.programSettings['projectorSizeX'].value)
		settingsChanged.append(self.projectorSizeY != self.programSettings['projectorSizeY'].value)
		#settingsChanged.append(self.previewSlicesMax != self.programSettings['previewSlicesMax'].value)
		settingsChanged.append(self.previewSliceWidth != self.programSettings['previewSliceWidth'].value)
		settingsChanged.append(self.layerHeight != self.programSettings['layerHeight'].value)
		settingsChanged.append(self.printHollow != self.settings['printHollow'].value)
		settingsChanged.append(self.fill != self.settings['fill'].value)
		settingsChanged.append(self.fillShellWallThickness != self.settings['fillShellWallThickness'].value)
		settingsChanged.append(self.fillSpacing != self.settings['fillSpacing'].value)
		settingsChanged.append(self.fillPatternWallThickness != self.settings['fillPatternWallThickness'].value)
		# Update.
		self.projectorSizeX = self.programSettings['projectorSizeX'].value
		self.projectorSizeY = self.programSettings['projectorSizeY'].value
		#self.previewSlicesMax = self.programSettings['previewSlicesMax'].value
		self.previewSliceWidth = self.programSettings['previewSliceWidth'].value
		self.layerHeight = self.programSettings['layerHeight'].value
		self.printHollow = self.settings['printHollow'].value
		self.fill = self.settings['fill'].value
		self.fillShellWallThickness = self.settings['fillShellWallThickness'].value
		self.fillSpacing = self.settings['fillSpacing'].value
		self.fillPatternWallThickness = self.settings['fillPatternWallThickness'].value
		# Return change status.
		return any(settingsChanged)



	# Update slice actor.
	def updateSlice3d(self, sliceNumber):
		if self.filename != "" and self.isactive():
			# Switch to non zero based indexing.
			sliceNumber += 1
			# Update pipeline with slice position given by layerHeight and slice number.
			zPosition = self.programSettings['layerHeight'].value*sliceNumber
			self.cuttingPlane.SetOrigin(0,0,zPosition)
			self.combinedCutlines.Update()
			self.combinedClipModels.Update()


	# Return slice size (width, height).
	def getSliceSizePx(self, border=False):
		# Get bounds.
		bounds = self.getBounds()
		# Limit size so that slice cannot protrude over projector limits.
		size = (   int(min([math.ceil(bounds[1] * self.programSettings['pxPerMmX'].value), self.programSettings['projectorSizeX'].value]) - self.getSlicePositionPx()[0]),   int(min([math.ceil(bounds[3] * self.programSettings['pxPerMmY'].value), self.programSettings['projectorSizeY'].value]) - self.getSlicePositionPx()[1])   )
		# Add a safety boarder that is needed for erosion (hollowing).
		if border:
			size = tuple([int(dim + self.programSettings['sliceBorderWidth'].value * 2) for dim in size])
		return size


	def getNumberOfSlices(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get layerHeight in mm.
		layerHeight = 	self.programSettings['layerHeight'].value
		# Calc number of layers.
		numberOfSlices = int(math.floor(bounds[5] / float(layerHeight)))
		return numberOfSlices


	def getSlicePositionPx(self, border=False):
		# Get bounds.
		bounds = self.getBounds()
		# Limit position to (0,0), just in case the model slightly protrudes out of the build volume.
		positionPx = (   int(max([0, math.floor(bounds[0] * self.programSettings['pxPerMmX'].value)])),   int(max([0, math.floor(bounds[2] * self.programSettings['pxPerMmY'].value)]))   )
		# Add a safety boarder that is needed for erosion (hollowing).
		if border:
			positionPx = tuple([int(dim - self.programSettings['sliceBorderWidth'].value) for dim in positionPx])
		return positionPx


	###########################################################################
	# Public methods to retrieve actors and other data. #######################
	###########################################################################

	# Get slice image for gui and print.
	def getCvImage(self):
		return self.imageArrayNumpy

	def getActorBottomPlate(self):
		return self.bottomPlateActor

	def hideActorBottomPlate(self):
		self.bottomPlateActor.SetVisibility(False)

	def showActorBottomPlate(self):
		self.bottomPlateActor.SetVisibility(True)

	def colorActorBottomPlate(self, r, g, b):
		self.bottomPlateActor.GetProperty().SetColor(r,g,b)

	def setOpacityBottomPlate(self, opacity):
		self.bottomPlateActor.GetProperty().SetOpacity(opacity)

	def getActorBottomPlate(self):
		return self.bottomPlateActor

	def hideActorBottomPlate(self):
		self.bottomPlateActor.SetVisibility(False)

	def showActorBottomPlate(self):
		self.bottomPlateActor.SetVisibility(True)

	def colorActorBottomPlate(self, r, g, b):
		self.bottomPlateActor.GetProperty().SetColor(r,g,b)

	def setOpacityBottomPlate(self, opacity):
		self.bottomPlateActor.GetProperty().SetOpacity(opacity)

	def getActorOverhang(self):
		return self.overhangClipActor

	def hideActorOverhang(self):
		self.overhangClipActor.SetVisibility(False)

	def showActorOverhang(self):
		self.overhangClipActor.SetVisibility(True)

	def colorActorOverhang(self, r, g, b):
		self.overhangClipActor.GetProperty().SetColor(r,g,b)

	def setOpacityOverhang(self, opacity):
		self.overhangClipActor.GetProperty().SetOpacity(opacity)

	def getActor(self):
		return self.stlActor

	def hide(self):
		self.stlActor.SetVisibility(False)

	def show(self):
		self.stlActor.SetVisibility(True)

	def color(self, r, g, b):
		self.stlActor.GetProperty().SetColor(r,g,b)

	def opacity(self, opacity):
		self.stlActor.GetProperty().SetOpacity(opacity)

	def getActorBoundingBox(self):
		return self.modelBoundingBoxActor

	def hideBoundingBox(self):
		self.modelBoundingBoxActor.SetVisibility(False)

	def showBoundingBox(self):
		self.modelBoundingBoxActor.SetVisibility(True)

	def colorBoundingBox(self, r, g, b):
		self.modelBoundingBoxActor.GetProperty().SetColor(r,g,b)

	def opacityBoundingBox(self, opacity):
		self.modelBoundingBoxActor.GetProperty().SetOpacity(opacity)

	def getActorBoundingBoxText(self):
		return self.modelBoundingBoxTextActor

	def hideBoundingBoxText(self):
		self.modelBoundingBoxTextActor.SetVisibility(False)

	def showBoundingBoxText(self):
		self.modelBoundingBoxTextActor.SetVisibility(True)

	def colorBoundingBoxText(self, r, g, b):
		self.modelBoundingBoxTextActor.GetProperty().SetColor(r,g,b)

	def opacityBoundingBoxText(self, opacity):
		self.modelBoundingBoxTextActor.GetProperty().SetOpacity(opacity)

	def getActorSupports(self):
		return self.supportsActor

	def hideActorSupports(self):
		self.supportsActor.SetVisibility(False)

	def showActorSupports(self):
		self.supportsActor.SetVisibility(True)

	def colorActorSupports(self, r, g, b):
		self.supportsActor.GetProperty().SetColor(r,g,b)

	def setOpacitySupports(self, opacity):
		self.supportsActor.GetProperty().SetOpacity(opacity)

	def getActorClipModel(self):
		return self.clipFilterActor

	def hideActorClipModel(self):
		self.clipFilterActor.SetVisibility(False)

	def showActorClipModel(self):
		self.clipFilterActor.SetVisibility(True)

	def colorActorClipModel(self, r, g, b):
		self.clipFilterActor.GetProperty().SetColor(r,g,b)

	def setOpacityClipModel(self, opacity):
		self.clipFilterActor.GetProperty().SetOpacity(opacity)

	def getActorSlices(self):
		return self.cuttingFilterActor

	def getActorSliceImage(self):
		self.imageActor.SetVisibility(True)
		return self.imageActor

	def hideActorSlices(self):
		self.cuttingFilterActor.SetVisibility(False)

	def showActorSlices(self):
		self.cuttingFilterActor.SetVisibility(True)

	def colorActorSlices(self, r, g, b):
		self.cuttingFilterActor.GetProperty().SetColor(r,g,b)

	def setOpacitySlices(self, opacity):
		self.cuttingFilterActor.GetProperty().SetOpacity(opacity)


	###########################################################################
	# Private method definitions. #############################################
	###########################################################################

	def __getBounds(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = [0 for i in range(6)]
		inputFilter.GetOutput().GetBounds(bounds)
		return bounds


	def __getSize(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = self.__getBounds(inputFilter)
		size = [0 for i in range(3)]
		size[0] = bounds[1] - bounds[0]
		size[1] = bounds[3] - bounds[2]
		size[2] = bounds[5] - bounds[4]
		return size


	def __getCenter(self, inputFilter):
		# Update filter and get bounds.
		inputFilter.Update()
		bounds = self.__getBounds(inputFilter)
		size = self.__getSize(inputFilter)
		center = [0 for i in range(3)]
		center[0] = bounds[0] + size[0] / 2.0
		center[1] = bounds[2] + size[1] / 2.0
		center[2] = bounds[4] + size[2] / 2.0
		return center







  ##### ##     ###### ####   #####    ##### ###### ####   ####  ##  ##
 ##     ##       ##  ##  ## ##       ##       ##  ##  ## ##  ## ## ##
  ####  ##       ##  ##     ####      ####    ##  ##  ## ##     ####
     ## ##       ##  ##     ##           ##   ##  ###### ##     ####
     ## ##       ##  ##  ## ##           ##   ##  ##  ## ##  ## ## ##
 #####  ###### ###### ####   #####   #####    ##  ##  ##  ####  ##  ##



################################################################################
# A list to hold all the slice images.	########################################
################################################################################
class sliceStack(list):
	""" Contains all slices for preview and will be continuously updated
	in a background thread.
	"""

	def __init__(self, programSettings=None, empty=False):
		# Call super class init function.
		list.__init__(self)
		self.programSettings = programSettings
		# Set width and height.
		# If program settings are supplied...
		if programSettings != None:
			# use projector width and height.
			self.width = self.programSettings['projectorSizeX'].value
			self.height = self.programSettings['projectorSizeY'].value
		else:
			# use dummy width and height until setSize function is called.
			self.width = 100
			self.height = 100
		# Load initial images.
		self.createDummyImages()
		# Create the slice array with a first black image.
		if not empty:
			self.append(self.imagesNoisy[0])

	# Set size function.
	def setSize(self, width, height):
		self.width = width
		self.height = height


	def reset(self, width, height, numberOfSlices, imgType="noisy"):
		# Set size of dummy image.
		self.setSize(width, height)
		self.createDummyImages()
		# Remove all slices.
		self[:] = []
		# Add new noisy slices.
		noisyImageIndex = 0
		for i in range(numberOfSlices):
			# Get image.
			if imgType == 'noisy':
				img = self.imagesNoisy[noisyImageIndex]
			elif imgType == 'black':
				img = (self.imageBlack)
			# Set image.
			self.append(numpy.copy(img))
			# Set next noisy image index.
			if noisyImageIndex < self.numberOfNoisyImages-1:
				noisyImageIndex = noisyImageIndex +1
			else:
				noisyImageIndex = 0

	# Create dummy images.
	def createDummyImages(self):
		# Create some different noisy images.
		self.numberOfNoisyImages = 10
		self.imagesNoisy = [imageHandling.createImageNoisy(self.width, self.height)]
		for i in range(1,self.numberOfNoisyImages):
			self.imagesNoisy.append(imageHandling.createImageNoisy(self.width, self.height))
		# Create black dummy image.
		self.imageBlack = imageHandling.createImageGray(self.width, self.height,0)
		# Create error image. TODO make this a monkey skull...
		self.imageError = imageHandling.createImageNoisy(self.width, self.height)


	# Set stack with "uniform" image. Type may be 'black' or 'noisy'
	def update(self, end, start=0, imgType='black'):
		# Last random number.
		noisyImageIndex = 0
		for i in range(start, end):
			# Get image.
			if imgType == 'noisy':
				img = self.imagesNoisy[noisyImageIndex]
			elif imgType == 'black':
				img = (self.imageBlack)
			# If slice exists...
			if i < self.getStackHeight():
				# set image.
				self[i] = numpy.copy(img)
			# If slice doesn't exist...
			elif i >= self.getStackHeight():
				# append image.
				self.append(numpy.copy(img))
			# Set next noisy image index.
			if noisyImageIndex < self.numberOfNoisyImages-1:
				noisyImageIndex = noisyImageIndex +1
			else:
				noisyImageIndex = 0


	def updateHeight(self, height):
		while(self.getStackHeight() < height):
			self.append(numpy.copy(self.imageBlack))
		if self.getStackHeight() > height:
			del self[height:]


	def deleteRegion(self, position, size):
		for imageSlice in self:
			pass#imageSlice[]


	# Return stack height.
	def getStackHeight(self):
		return len(self)


	# Function to return an image.
	def getImage(self,index):
		# If index in bounds...
		if int(index) < len(self):
			# ... return the image.
			return self[int(index)]
		else:
			return self.imageError






  ##### ##     ###### ####   #####    ####   ####  ##  ## ##### ###### ##  ##  ##### #####
 ##     ##       ##  ##  ## ##       ##  ## ##  ## ###### ##  ##  ##   ### ## ##     ##  ##
  ####  ##       ##  ##     ####     ##     ##  ## ###### #####   ##   ###### ####   ##  ##
     ## ##       ##  ##     ##       ##     ##  ## ##  ## ##  ##  ##   ## ### ##     #####
     ## ##       ##  ##  ## ##       ##  ## ##  ## ##  ## ##  ##  ##   ##  ## ##     ## ##
 #####  ###### ###### ####   #####    ####   ####  ##  ## ##### ###### ##  ##  ##### ##  ##



################################################################################
# A thread that checks the slicer temp directories an combines the slices. #####
################################################################################
class sliceCombiner(threading.Thread):
	def __init__(self, programSettings, queueIn, queueOut, queueOutSingle=None, console=None):

		# Internalise parameters.
		self.programSettings = programSettings
		self.queueIn = queueIn
		self.queueOut = queueOut
		self.queueOutSingle = queueOutSingle
		self.console = console

		# Thread stop event.
		self.stopThread = threading.Event()

		# Call super class init function.
		super(sliceCombiner, self).__init__()


	def run(self):
		if self.console:
			self.console.addLine("Slice combiner thread initialised.")
		# Go straight into idle mode.
		self.idle()


	# Check if input queue holds new items.
	def newInputInQueue(self):
		if self.queueIn.qsize():
			return True
		else:
			return False


	# Idle and wait for queue data to arrive.
	# Call slicer if new data has arrived.
	def idle(self):
		# Loop until termination.
		while not self.stopThread.isSet():
			# Do nothing as long as nothing is in the queue.
			while not self.newInputInQueue() and not self.stopThread.isSet():
				time.sleep(0.01)
			# If input has arrived get the input run slicer function.
			if not self.stopThread.isSet():
				newInput = self.queueIn.get()
				sliceStackPreviewAndNumbers = self.processInput(newInput)
				if sliceStackPreviewAndNumbers != None:
					self.queueOut.put(sliceStackPreviewAndNumbers)


	# Process the slicer info that came in through the queue.
	def processInput(self, modelNamesAndHeights):

		interval = time.time()

		# Create slicer output directory.
		self.sliceOutputPath = self.programSettings['tmpDir'].value + '/slicerOutput'

		# Delete slicer temp directory if it exists.
		if os.path.isdir(self.sliceOutputPath):
			shutil.rmtree(self.sliceOutputPath, ignore_errors=True)
		os.makedirs(self.sliceOutputPath)

		# Check if preview stack or full stack.
		mode = modelNamesAndHeights[6].split(' ')[0]

		# Get path for saving slices in full mode.
		savePath = modelNamesAndHeights[7]

		# Get number of preview slices.
		numberOfPreviewSlices = modelNamesAndHeights[0]

		# Get preview slice multiplier.
		sliceMultiplier = modelNamesAndHeights[1]

		# Get highest model.
		stackHeight = sorted(modelNamesAndHeights[3])[-1]

		# Get model slice paths.
		modelSlicePaths = modelNamesAndHeights[2]

		# Get model heights.
		modelHeights = modelNamesAndHeights[3]

		# Slice size.
		sliceHeight = self.programSettings['projectorSizeY'].value
		sliceWidth = self.programSettings['projectorSizeX'].value
		sliceBorderWidth = self.programSettings['sliceBorderWidth'].value

		aspectRatio = float(sliceHeight) / float(sliceWidth)
		previewHeight = self.programSettings['previewSliceWidth'].value * aspectRatio
		previewDimensions = (int(self.programSettings['previewSliceWidth'].value), int(previewHeight))

		sliceHeight += 2 * self.programSettings['sliceBorderWidth'].value
		sliceWidth +=  2 * self.programSettings['sliceBorderWidth'].value

		# Get model slice positions and sizes.
		modelSlicePositions = modelNamesAndHeights[4]
		modelSliceSizes = modelNamesAndHeights[5]

		# Get calibration image.
		self.calibrationImage = None
		if self.programSettings['calibrationImage'].value:# and os.path.isfile(self.programSettings['calibrationImagePath'].value):
			# Load image.
			if os.path.isfile(self.programSettings['calibrationImagePath'].value + ".png"):
				self.calibrationImage = cv2.imread(self.programSettings['calibrationImagePath'].value + ".png")
			elif os.path.isfile(self.programSettings['calibrationImagePath'].value + ".jpg"):
				self.calibrationImage = cv2.imread(self.programSettings['calibrationImagePath'].value + ".jpg")
			# Convert to grayscale.
			self.calibrationImage = cv2.cvtColor(self.calibrationImage, cv2.COLOR_BGR2GRAY)
			# ... scale the image according to projector size.
			if self.calibrationImage.shape[0] != self.programSettings['projectorSizeY'].value or self.calibrationImage.shape[1] != self.programSettings['projectorSizeX'].value:
				self.calibrationImage = cv2.resize(self.calibrationImage, (self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value))
			# Blur the image to reduce the influence of noise.
			self.calibrationImage = cv2.GaussianBlur(self.calibrationImage, (21, 21), 0)
			# Turn into numpy array.
			self.calibrationImage = numpy.asarray(self.calibrationImage, dtype=numpy.uint8)
			# Find the lowest pixel value.
			minVal = numpy.amin(self.calibrationImage)
			# Shift pixel values down.
			# Darkest pixel should be black now.
			self.calibrationImage -= minVal

		# Create slice number list that reduces number of slices so the max
		# number is not surpassed.
		if mode == "preview":
			# First and last index are fixed, all in between are approximated.
			sliceNumbers = [0]
			sliceNumbers += [int(round((previewSlice)*sliceMultiplier)) for previewSlice in range(1, numberOfPreviewSlices-1)]
			sliceNumbers += [stackHeight-1]
		elif mode == "full":
			sliceNumbers = range(stackHeight)
		elif mode == "single":#type(eval(mode)) == int or type(eval(mode)) == float:
			sliceNumbers = [int(modelNamesAndHeights[6].split(' ')[1])]

		# Create slice stack.
		sliceStackPreview = sliceStack(self.programSettings, empty=True)

		# Set progress percentage.
		readyPercentage = 0

		# Create base image.
		imageBlack = imageHandling.createImageGray(sliceWidth, sliceHeight,0)

		# Then, walk through slices and check if they are complete.
		for i in sliceNumbers:

			if not self.stopThread.isSet() and not self.newInputInQueue():
				# Prepare image.
				imageSlice = imageBlack

				# Get models that reach up to current slice.
				currentPaths = []
				currentPositions = []
				currentSizes = []
				for modelIndex in range(len(modelHeights)):
					if modelHeights[modelIndex]-1 >= i:
						currentPaths.append(modelSlicePaths[modelIndex] + '/slice' + str(int(i)).zfill(6) + '.png')
						currentPositions.append(modelSlicePositions[modelIndex])
						currentSizes.append(modelSliceSizes[modelIndex])
				if currentPaths == []:
					break

				# Wait until all models needed for the current slice are available.
				allModelsAvailable = False
				while not allModelsAvailable and not self.stopThread.isSet() and not self.newInputInQueue():
					currentSliceModelPathsFound = [os.path.exists(path) for path in currentPaths]
					allModelsAvailable = all(currentSliceModelPathsFound)
					if not allModelsAvailable:
						time.sleep(0.01)

				# Once all slice model images are available, combine them.
				while len(currentPaths) > 0 and not self.stopThread.isSet() and not self.newInputInQueue():
						if os.path.exists(currentPaths[0]):
							retry = True
							while retry:
								try:
									# Load the model slice image from file.
									imageSliceModel = Image.open(currentPaths[0])
									retry = False
									try:
										imageSliceModel = numpy.array(imageSliceModel.getdata())
										retry = False
									except SyntaxError:
										retry = True
								except IOError:
									retry = True
							imageSliceModel = imageSliceModel.reshape(currentSizes[0][1], currentSizes[0][0],-1).squeeze()
							imageSliceModel = numpy.flipud(imageSliceModel)
							imageSlice = self.addModelSliceImage(imageSlice, imageSliceModel, currentPositions[0])
							# In case of success, clear the model slice path.
							del currentPaths[0]
							del currentPositions[0]
							del currentSizes[0]
				imageSlice = numpy.flipud(imageSlice)
				# Clip border.
				imageSlice = imageSlice[sliceBorderWidth:sliceHeight-sliceBorderWidth, sliceBorderWidth:sliceWidth-sliceBorderWidth]

				# Once the slice image is complete, subtract the calibration image.
				if self.calibrationImage != None:
					imageSlice = cv2.subtract(imageSlice, self.calibrationImage)
				# Then, add the image to the stack or write it to disk.
				if mode == "preview":#i in sliceNumbers:
					# ... resize according to preview width and
					# send it to the preview stack if this is a preview slice.
					sliceStackPreview.append(cv2.resize(imageSlice, previewDimensions, interpolation = cv2.INTER_AREA))
					# TODO: scale down according to settings.
				elif mode == "full":
					# ... or, write it to file.
					self.writeSliceToDisk(imageSlice, i, savePath)
				elif mode == 'single' and self.queueOutSingle != None:
					# Check if queue is empty.
					while self.queueOutSingle.qsize():
						time.sleep(0.1)
					self.queueOutSingle.put(imageSlice)

				# Send progress string.
				if int((i/float(stackHeight))*100) > readyPercentage:
					readyPercentage = int((i/float(stackHeight))*100)
					if not self.queueOut.qsize() and mode != "single":
						self.queueOut.put(str(readyPercentage))

		# Shrink slice number array to stack height if necessary.
		if mode != "single":
			sliceNumbers = sliceNumbers[:len(sliceStackPreview)]
			self.queueOut.put(str(100))

		if self.newInputInQueue():
			return None
		else:
			print "Slicer run time: " + str(time.time() - interval) + " s."
			if mode == "preview":
				return [sliceStackPreview, sliceNumbers]


	def addModelSliceImage(self, imageSlice, imageSliceModel, position):
		return imageHandling.imgAdd(imageSlice, imageSliceModel, position)

	# Write a slice image to the given path.
	def writeSliceToDisk(self, imageSlice, sliceNumber, savePath=None):
		# Format number string.
		digits = 6
		numberString = str(int(sliceNumber)).zfill(digits)
		# Create image file string.
		if savePath != None:
			# Save path comes with full file name.
			# Squeeze slice number between name and postfix.
			fileString = savePath[:-4] + numberString + ".png"
		else:
			fileString = self.sliceOutputPath + "/slice" + numberString + ".png"
		image = Image.fromarray(imageSlice)
		image.save(fileString)

	# Stop thread.
	def stop(self):
		if self.console != None:
			self.console.addLine("Stopping combiner thread")
		self.stopThread.set()


	# Stop thread and wait for it to finish.
	def join(self, timeout=None):
		if self.console != None:
			self.console.addLine("Stopping combiner thread")
		self.stopThread.set()
		threading.Thread.join(self, timeout)






  ##### ##     ###### ####   ##### #####    ###### ##  ## #####   #####  ####  #####
 ##     ##       ##  ##  ## ##     ##  ##     ##   ##  ## ##  ## ##     ##  ## ##  ##
  ####  ##       ##  ##     ####   ##  ##     ##   ###### ##  ## ####   ##  ## ##  ##
     ## ##       ##  ##     ##     #####      ##   ##  ## #####  ##     ###### ##  ##
     ## ##       ##  ##  ## ##     ## ##      ##   ##  ## ## ##  ##     ##  ## ##  ##
 #####  ###### ###### ####   ##### ##  ##     ##   ##  ## ##  ##  ##### ##  ## #####



################################################################################
# A thread to slice the model in background.	################################
################################################################################
class backgroundSlicer(threading.Thread):

	# Overload init function.
	def __init__(self, slicePath, polyDataModel, polyDataSupports, polyDataBottomPlate, queueSlicerIn, queueSlicerOut, console=None):

		# Internalise inputs. ******************************
		self.queueSlicerIn = queueSlicerIn
		self.queueSlicerOut = queueSlicerOut
		self.console = console
		self.slicePath = slicePath
		self.polyDataModel = polyDataModel
		self.polyDataSupports = polyDataSupports
		self.polyDataBottomPlate = polyDataBottomPlate

		# Create new polydata objects. *********************
		# We cannot use the reference to the original polydata in
		# this separate thread, so we need to deep copy the polydata
		# into these interal objects on start of the slicer.
		self.polyDataModelInternal = vtk.vtkPolyData()
		self.polyDataModelInternal.DeepCopy(self.polyDataModel)
		self.polyDataSupportsInternal = vtk.vtkPolyData()
		self.polyDataSupportsInternal.DeepCopy(self.polyDataSupports)
		self.polyDataBottomPlateInternal = vtk.vtkPolyData()
		self.polyDataBottomPlateInternal.DeepCopy(self.polyDataBottomPlate)

		# Extract polydata regions.
		# First, assign a region id to each cell.
		self.polyDataModelConnectivity = vtk.vtkConnectivityFilter()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.polyDataModelConnectivity.SetInput(self.polyDataModelInternal)
		else:
			self.polyDataModelConnectivity.SetInputData(self.polyDataModelInternal)
		self.polyDataModelConnectivity.SetExtractionModeToAllRegions()
		self.polyDataModelConnectivity.ScalarConnectivityOff()
		self.polyDataModelConnectivity.ColorRegionsOn()
		self.polyDataModelConnectivity.Update()
		#for i in range(self.polyDataModelConnectivity.GetOutput().GetCellData().GetScalars().GetSize()):
		#	print self.polyDataModelConnectivity.GetOutput().GetCellData().GetScalars().GetValue(i)

		# Use threshold filter to extract cells of each region.
		self.polyDataModelRegions = vtk.vtkThreshold()
		if vtk.VTK_MAJOR_VERSION <= 5:
  			self.polyDataModelRegions.SetInput(self.polyDataModelConnectivity.GetOutput())
  		else:
  			self.polyDataModelRegions.SetInputConnection(self.polyDataModelConnectivity.GetOutputPort())

		# Create VTK error observer to catch errors.
		self.errorObserver = ErrorObserver()

		# Create the VTK pipeline. *************************
		self.extrusionVector = (0,0,-1)
		# Create cutting plane.
		self.cuttingPlane = vtk.vtkPlane()
		self.cuttingPlane.SetNormal(0,0,1)
		self.cuttingPlane.SetOrigin(0,0,0.001)	# Make sure the bottom plate is cut properly.
		# Create cutting filter for model.
		self.cuttingFilterModel = vtk.vtkCutter()
		self.cuttingFilterModel.SetCutFunction(self.cuttingPlane)
		# Create cutting filter for supports.
		self.cuttingFilterSupports = vtk.vtkCutter()
		self.cuttingFilterSupports.SetCutFunction(self.cuttingPlane)
		# Create cutting filter for bottom plate.
		self.cuttingFilterBottomPlate = vtk.vtkCutter()
		self.cuttingFilterBottomPlate.SetCutFunction(self.cuttingPlane)
		# Set inputs for cutting filters.
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.cuttingFilterModel.SetInput(self.polyDataModelRegions.GetOutput())
			#self.cuttingFilterModel.SetInput(self.polyDataModelConnectivity.GetOutput())#self.polyDataModelInternal)
			self.cuttingFilterSupports.SetInput(self.polyDataSupportsInternal)
			self.cuttingFilterBottomPlate.SetInput(self.polyDataBottomPlateInternal)
		else:
			self.cuttingFilterModel.SetInputData(self.polyDataModelConnectivity.GetOutput())#self.polyDataModelInternal)
			self.cuttingFilterSupports.SetInputData(self.polyDataSupportsInternal)
			self.cuttingFilterBottomPlate.SetInputData(self.polyDataBottomPlateInternal)
		# Create polylines from cutter outputs.
		self.sectionStripperModel = vtk.vtkStripper()
		self.sectionStripperSupports = vtk.vtkStripper()
		self.sectionStripperBottomPlate = vtk.vtkStripper()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.sectionStripperModel.SetInput(self.cuttingFilterModel.GetOutput())
			self.sectionStripperSupports.SetInput(self.cuttingFilterSupports.GetOutput())
			self.sectionStripperBottomPlate.SetInput(self.cuttingFilterBottomPlate.GetOutput())
		else:
			self.sectionStripperModel.SetInputConnection(self.cuttingFilterModel.GetOutputPort())
			self.sectionStripperSupports.SetInputConnection(self.cuttingFilterSupports.GetOutputPort())
			self.sectionStripperBottomPlate.SetInputConnection(self.cuttingFilterBottomPlate.GetOutputPort())




		# Thread stop event.
		self.stopThread = threading.Event()
		# Call super class init function.
		super(backgroundSlicer, self).__init__()

		#print "Slicer thread running at " + self.slicePath + "."


	# Overload the run method.
	# This will automatically run once the init function is done.
	# Jumps straight into idle mode.
	def run(self):
		if self.console:
			self.console.addLine("Slicer thread initialised")
		# Go straight into idle mode.
		self.idle()


	# Check if input queue holds new items.
	def newInputInQueue(self):
		if self.queueSlicerIn.qsize():
			return True
		else:
			return False


	# Idle and wait for queue data to arrive.
	# Call slicer if new data has arrived.
	def idle(self):
		# Loop this until termination.
		while not self.stopThread.isSet():
			# Do nothing as long as nothing is in the queue.
			while not self.newInputInQueue() and not self.stopThread.isSet():
				time.sleep(0.1)
			# If input has arrived get the input run slicer function.
			if not self.stopThread.isSet():
				slicerInputInfo = self.queueSlicerIn.get()
				self.runSlicer(slicerInputInfo)


	# Run the slicer, send back data through the output queue
	# and return to idle mode when done.
	def runSlicer(self, slicerInputInfo):
		# Don't run if stop condition is set.
		while not self.stopThread.isSet():
			# Check if new input is in queue. If not...
			if not self.newInputInQueue():
				# ...do the slicing.
				warningSlices = self.updateSlices(slicerInputInfo)
				if self.debug:
					print "Slicer done."
			# If new input has arrivied...
			else:
				# Break the loop, return to idle mode and restart from there.
				break
			# Write the model to the output queue.
			self.queueSlicerOut.put((warningSlices))
			break


	# Stop thread.
	def stop(self):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()


	# Stop thread and wait for it to finish.
	def join(self, timeout=None):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()
		threading.Thread.join(self, timeout)


	# Update the slice stack. This will run on any new input in the
	# input queue.
	def updateSlices(self, slicerInputInfo):

		if not self.stopThread.isSet():

			# Empty the slicer temp directory.
			shutil.rmtree(self.slicePath, ignore_errors=True)
			# Create slicer temp directory.
			if not os.path.isdir(self.slicePath):
				os.makedirs(self.slicePath)

			# Deep copy the model data into thread internal objects.
			self.polyDataModelInternal.DeepCopy(self.polyDataModel)
			self.polyDataSupportsInternal.DeepCopy(self.polyDataSupports)
			self.polyDataBottomPlateInternal.DeepCopy(self.polyDataBottomPlate)

			# Update the connectivity.
			self.polyDataModelConnectivity.Update()

			# Update slice image width, position, number of slices etc.
			self.pxPerMmX = slicerInputInfo['pxPerMmX']
			self.pxPerMmY = slicerInputInfo['pxPerMmY']
			# Get layerHeight in mm.
			self.layerHeight = 	slicerInputInfo['layerHeight']
			# Calc number of layers.
			self.numberOfSlices = slicerInputInfo['numberOfSlices']
			# Get position in pixels.
			self.position = slicerInputInfo['position']
			self.size = slicerInputInfo['size']
			# Get support height.
			self.supportHeight = slicerInputInfo['supportHeight']
			# Get wall thickness for hollowing.
			self.wallThicknessLayers = slicerInputInfo['wallThickness'] / float(self.layerHeight)
			self.wallThicknessPxX = slicerInputInfo['wallThickness'] * self.pxPerMmX
			self.wallThicknessPxY = slicerInputInfo['wallThickness'] * self.pxPerMmY
			self.fillPatternSpacingPxX = slicerInputInfo['fillPatternSpacingPxX'] * self.pxPerMmX
			self.fillPatternSpacingPxY = slicerInputInfo['fillPatternSpacingPxY'] * self.pxPerMmX
			self.fillPatternWallThicknessPxX = slicerInputInfo['fillPatternWallThickness'] * self.pxPerMmX
			self.fillPatternWallThicknessPxY = slicerInputInfo['fillPatternWallThickness'] * self.pxPerMmY
			self.printHollow = slicerInputInfo['printHollow']
			self.fill = slicerInputInfo['fill']
			self.showVtkErrors = slicerInputInfo['showVtkErrors']
			self.polylineClosingThreshold = slicerInputInfo['polylineClosingThreshold']
			self.multiBodySlicing = slicerInputInfo['multiBodySlicing']


			# Prepare buffer stack for hollowing. **********
			# Images will be fed into this buffer to generate
			# the fill structures for the center image.
			sliceStackBuffer = sliceBuffer(int(self.wallThicknessLayers*2)+1)
			# Prepare a buffer with eroded images.
			sliceStackBufferEroded = sliceBuffer(int(self.wallThicknessLayers*2)+1)
			self.erodeKernel = cv2.getStructuringElement(cv2.MORPH_RECT,(int(self.wallThicknessPxX),int(self.wallThicknessPxY)))

			# Prepare images. ******************************
			self.imageBlack = numpy.zeros((self.size[1], self.size[0]), numpy.uint8)
			self.imageFill = self.createFillPattern()

			# Check if supports and bottom plate shall be used.
			useSupports = slicerInputInfo['createSupports']
			useBottomPlate = slicerInputInfo['createBottomPlate']
			self.debug = slicerInputInfo['debug']

			warningSlices = []

			# Loop through slices.
			for sliceNumber in range(int(self.numberOfSlices + self.wallThicknessLayers)):
				# Make breakable by new input or termination request.
				if not self.newInputInQueue() and not self.stopThread.isSet():
					# Sleep for a very short period to allow GUI thread some CPU usage.
					time.sleep(0.00001)

					# Create the slice image and feed into buffer.
					if sliceNumber < self.numberOfSlices:
						# Create slice image.
						imageSlice, imageSliceCorrupted = self.createSliceImage(sliceNumber, model=True)
						# Handle corrupted polylines.
						if imageSliceCorrupted is not None:
							print "Slice " + str(sliceNumber) + ": Warning: there are open polyline segments. Please check if your model is watertight."
							warningSlices.append(sliceNumber)
							# TODO: display this in GUI.
						# Append image to slice stack buffer.
						sliceStackBuffer.addSlice(imageSlice)
						# Append eroded image to buffer.
						if self.printHollow:
							imageSliceEroded = cv2.erode(imageSlice, self.erodeKernel, iterations=1)
							sliceStackBufferEroded.addSlice(imageSliceEroded)
					else:
						# Keep shifting the buffer, even if no slice images are left.
						sliceStackBuffer.addSlice(None)
						if self.printHollow:
							sliceStackBufferEroded.addSlice(None)

					# If slice buffer is filled up to center, start to generate slices.
					if sliceNumber >= self.wallThicknessLayers:
						currentSlice = sliceStackBuffer.getCenter()
						if self.debug:
							print "Generating slice " + str(sliceNumber-self.wallThicknessLayers) + "."
						if self.printHollow:
							if sliceStackBuffer.getBelowCenter()[0] is not None and sliceStackBuffer.getAboveCenter()[-1] is not None:
								currentSlice = self.hollowSliceImage(currentSlice, imageSliceEroded, sliceStackBuffer.getBelowCenter(), sliceStackBuffer.getAboveCenter(), sliceStackBufferEroded.getBelowCenter(), sliceStackBufferEroded.getAboveCenter())
						# Add supports to the slice image.
						if sliceNumber-self.wallThicknessLayers <= self.supportHeight / self.layerHeight:
							if useSupports and useBottomPlate:
								imageSupports, imageCorrupted = self.createSliceImage(sliceNumber-self.wallThicknessLayers, supports=True, bottomPlate=True)
							elif useBottomPlate:
								imageSupports, imageCorrupted = self.createSliceImage(sliceNumber-self.wallThicknessLayers, bottomPlate=True)
							currentSlice = cv2.add(currentSlice, imageSupports)
						# Write slice image to disk.
						self.writeSliceToDisk(currentSlice, sliceNumber-self.wallThicknessLayers)
					else:
						if self.debug:
							print "Filling slice buffer."
				# Break if new input is in slice stack queue.
				else:
					if self.console:
						self.console.addLine("Restarting slicer.")
					break

			return (warningSlices)


	# Write a slice image to the given path.
	def writeSliceToDisk(self, imageSlice, sliceNumber):
		# Format number string.
		digits = 6
		numberString = str(int(sliceNumber)).zfill(digits)
		# Create image file string.
		fileString = self.slicePath + "/slice" + numberString + ".png"
		image = Image.fromarray(imageSlice)
		image.save(fileString)


	# Create an image that has a square pattern for filling a hollowed model.
	def createFillPattern(self):

		if not self.stopThread.isSet():
			# Create an opencv image with rectangular pattern for filling large model areas.
			# Height and width should be a multiple of the fill spacing.
			height = int(math.ceil(self.size[1] / self.fillPatternSpacingPxY) * self.fillPatternSpacingPxY)#int(math.ceil(self.height / spacing) * spacing)
			width = int(math.ceil(self.size[0] / self.fillPatternSpacingPxX) * self.fillPatternSpacingPxX)#int(math.ceil(self.width / spacing) * spacing)
			imageFill = numpy.ones((height, width), numpy.uint8) * 255

			# Set every Nth vertical line (and it's  neighbour or so) white.
			for pixelX in range(width):
				if (pixelX / self.fillPatternSpacingPxX - math.floor(pixelX / self.fillPatternSpacingPxX)) * self.fillPatternSpacingPxX < self.fillPatternWallThicknessPxX:
					imageFill[:,pixelX-1] = 0
			for pixelY in range(height):
				if (pixelY / self.fillPatternSpacingPxY - math.floor(pixelY / self.fillPatternSpacingPxY)) * self.fillPatternSpacingPxY < self.fillPatternWallThicknessPxY:
					imageFill[pixelY-1,:] = 0
			return imageFill


	# Hollow a slice image using the slice images above and
	# below that are within the wall thickness.
	# This also creates a fill pattern if needed.
	def hollowSliceImage(self, imageSlice, imageSliceEroded, imageStackBelow, imageStackAbove, imageStackBelowEroded, imageStackAboveEroded):

		# Get top and bottom masks for wall thickness.
		# Masks are created from the images below and above the
		# current slice which are within the wall thickness.
		imageTopMask = numpy.ones((self.size[1], self.size[0]), numpy.uint8) * 255
		imageBottomMask = numpy.ones((self.size[1], self.size[0]), numpy.uint8) * 255
		# TODO: creates a numpy deprecation warning.
		for imageAboveEroded in imageStackAboveEroded:
			if imageAboveEroded is None:
				break
			else:
				imageTopMask = cv2.multiply(imageTopMask, imageAboveEroded)
		for imageBelowEroded in reversed(imageStackBelowEroded):
			if imageBelowEroded is None:
				break
			else:
				imageBottomMask = cv2.multiply(imageBottomMask, imageBelowEroded)

		# Multiply mask images with eroded image to prevent wall where mask images are black.
		imageSliceEroded = cv2.multiply(imageSliceEroded, imageTopMask)
		imageSliceEroded = cv2.multiply(imageSliceEroded, imageBottomMask)
		#END NEW
		'''
		# TODO: creates a numpy deprecation warning.
		for imageAbove in imageStackAbove:
			if imageAbove is None:
				break
			else:
				imageAbove = cv2.erode(imageAbove, self.erodeKernel, iterations=1)
				imageTopMask = cv2.multiply(imageTopMask, imageAbove)
		for imageBelow in reversed(imageStackBelow):
			if imageBelow is None:
				break
			else:
				imageBelow = cv2.erode(imageBelow, self.erodeKernel, iterations=1)
				imageBottomMask = cv2.multiply(imageBottomMask, imageBelow)
		# Erode model image to create wall thickness.
		imageEroded = cv2.erode(imageSlice, self.erodeKernel, iterations=1)

		# Multiply mask images with eroded image to prevent wall where mask images are black.
		imageEroded = cv2.multiply(imageEroded, imageTopMask)
		imageEroded = cv2.multiply(imageEroded, imageBottomMask)
		'''
		# Add internal pattern to slice image if asked for.
		if self.fill:
			# Shift internal pattern 1 pixel to prevent burning in the pdms coating.
			patternShift = 1	# TODO: implement setting for pattern shift.
			self.imageFill = numpy.roll(self.imageFill, patternShift, axis=0)
			self.imageFill = numpy.roll(self.imageFill, patternShift, axis=1)

			# Mask internal pattern using the eroded image.
			# The fill image is a little larger, so get a slice sized subimage.
			imageSliceEroded = cv2.multiply(imageSliceEroded, self.imageFill[:self.size[1],:self.size[0]])

		# Subtract cavity with or without fill pattern from model.
		imageSlice = cv2.subtract(imageSlice, imageSliceEroded)

		# Return the modified slice image.
		return imageSlice


	# Create a slice image that may include model, supports and/or bottom plate.
	def createSliceImage(self, sliceNumber, model=False, supports=False, bottomPlate=False):

		# Skip slice 0 right at the vat floor.
		sliceNumber += 1

		activationFlags = [model, supports, bottomPlate]
		#print activationFlags

		# Create a black slice image. **********************
		imageSlice = numpy.zeros((self.size[1], self.size[0]), numpy.uint8)#numpy.zeros((self.height, self.width), numpy.uint8)
		imageSliceCorrupted = numpy.zeros((self.size[1], self.size[0]), numpy.uint8)#numpy.zeros((self.height, self.width), numpy.uint8)

		# Create the slice image. **************************
		# Set new height for the cutting plane.
		if sliceNumber == 0:
			slicePosition = 0.00001
		else:
			slicePosition = self.layerHeight*sliceNumber

		# Get the slice contours.
		# Slice contours contains two levels:
		# 1: multiple parts of a model
		# 2: multiple polylines of the same part
		sliceContours, sliceContoursCorrupted = self.createSliceContour(slicePosition, model, supports, bottomPlate)

		# Draw polygons to image.
		# To get antialiased drawing, the point coordinates are
		# multiplied by 2^fractionalBits and converted to ints.
		# The fractionalBits are given to the drawing function.
		# Line type has to be set to cv2.CV_AA for antialiasing.

		fractionalBits = 3
		for i in range(len(sliceContours)):
			sliceContours[i] = [ numpy.array(numpy.multiply(polyline, pow(2, fractionalBits)), dtype=numpy.int32) for polyline in sliceContours[i]]

			cv2.fillPoly(imageSlice, sliceContours[i], color=255, shift=fractionalBits, lineType=cv2.CV_AA) # Shift is the number of digits behind the point coordinate comma --> subpixel accuracy.

		# Add corrupted polygonds to extra image.
		if len(sliceContoursCorrupted) > 0:
			cv2.polylines(imageSliceCorrupted, sliceContoursCorrupted[0], isClosed=False, color=255)

		# Return images.
		if len(sliceContoursCorrupted) > 0:
			return (imageSlice, imageSliceCorrupted)
		else:
			return (imageSlice, None)


	# Create the intersection polylines between cutting plane and model.
	# Can be done for model, supports and bottom plate separately.
	def createSliceContour(self, slicePosition, model=False, supports=False, bottomPlate=False):

		# Set the cutting plane position.
		self.cuttingPlane.SetOrigin(0,0,slicePosition)

  		pointsInputAll = []
  		linesInputAll = []
  		numberOfPolylinesInputAll = []

		# Update cutting filters.
		if model:
			# Update for each region.
			for region in range(self.polyDataModelConnectivity.GetNumberOfExtractedRegions()):
				# Get current region.
				self.polyDataModelRegions.ThresholdBetween(region, region)
				# Get section polylines from cutter.
				self.sectionStripperModel.Update()
				if self.showVtkErrors and self.errorObserver.ErrorOccurred():
					print "VTK Error: " + self.errorObserver.ErrorMessage()
				# Extract points and lines.
				points = self.sectionStripperModel.GetOutput().GetPoints()
				lines = self.sectionStripperModel.GetOutput().GetLines()
				# If intersections were found:
				if lines.GetNumberOfCells() > 0:
					# Convert to  numpy array.
					pointsInputAll.append(numpy_support.vtk_to_numpy(points.GetData()))
					linesInputAll.append(numpy_support.vtk_to_numpy(lines.GetData()))
					numberOfPolylinesInputAll.append(lines.GetNumberOfCells())

		if supports:
			self.cuttingFilterSupports.Update()
			if self.showVtkErrors and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()
			self.sectionStripperSupports.Update()
			if self.showVtkErrors and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()
			# Extract points and lines.
			points = self.sectionStripperSupports.GetOutput().GetPoints()
			lines = self.sectionStripperSupports.GetOutput().GetLines()
			# If intersections were found:
			if lines.GetNumberOfCells() > 0:
				# Convert to  numpy array.
				pointsInputAll.append(numpy_support.vtk_to_numpy(points.GetData()))
				linesInputAll.append(numpy_support.vtk_to_numpy(lines.GetData()))
				numberOfPolylinesInputAll.append(lines.GetNumberOfCells())

		if bottomPlate:
			self.cuttingFilterBottomPlate.Update()
			if self.showVtkErrors and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()
			self.sectionStripperBottomPlate.Update()
			if self.showVtkErrors and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()
			# Extract points and lines.
			points = self.sectionStripperBottomPlate.GetOutput().GetPoints()
			lines = self.sectionStripperBottomPlate.GetOutput().GetLines()
			# If intersections were found:
			if lines.GetNumberOfCells() > 0:
				# Convert to  numpy array.
				pointsInputAll.append(numpy_support.vtk_to_numpy(points.GetData()))
				linesInputAll.append(numpy_support.vtk_to_numpy(lines.GetData()))
				numberOfPolylinesInputAll.append(lines.GetNumberOfCells())

		# Now we have an array that contains slice contour point and line
		# arrays for each indiviual model region and for supports and bottom plate.
		# We'll loop over these arrays and try to combine stray lines into closed polylines.
		# Start timer.
		if self.debug:
			interval = time.time()
		polylinesClosedAll = []
		polylinesCorruptedAll = []

		for i in range(len(pointsInputAll)):
			# Get current points.
			points = pointsInputAll[i]
			# Remove Z dimension.
			points = points[:,0:2]
			# Scale to fit the image (convert from mm to px).
			points[:,0] *= self.pxPerMmX
			points[:,1] *= self.pxPerMmX
			# Move points to center of image.
			points[:,0] -= self.position[0]
			points[:,1] -= self.position[1]
			# Flip points y-wise because image coordinates start at top.
			points[:,1] = abs(points[:,1] - self.size[1])

			# Get current lines.
			# Lines contain point indices in the right order for each polyline.
			# However, there might be polyline segments that are not connected.
			# We need to connect all polyline segments.
			lines = linesInputAll[i]
			numberOfPolylines = numberOfPolylinesInputAll[i]

			polylineIndicesClosed = []
			polylineIndicesOpen = []
			startIndex = 0

			# Check if there are connecting polylines.
			# This is necessary because some polylines from the stripper output may still be segmented.
			# Two polylines are connected if the start or end point indices are equal.
			# Test for start/start, end/end, start/end, end/start.
			# NOTE: The lines array contains point indices for all polylines.
			# It consists of multiple blocks, each block starting with the
			# number of points, followed by the point indices. Then, the next block starts with the
			# next number of points, followed by the point indices and so on...
			for polyline in range(numberOfPolylines):
				#print "Polyline " + str(polyline) + ". ****************"
				numberOfPoints = lines[startIndex]
				#print "   Start point: " + str(points[lines[startIndex+1]]) + "."
				#print "   End point: " + str(points[lines[startIndex+numberOfPoints]]) + "." # -1
				# Get the indices starting just behind the start index.
				polylineInd = lines[startIndex+1:startIndex+1+numberOfPoints]

				# Check if polyline is closed. If yes, append to closed list.
				if polylineInd[0] == polylineInd[-1]:
					#print "   Found closed polyline."
					polylineIndicesClosed.append(polylineInd)
				# If not, check if this is the first open one. If yes, append.
				else:# len(polylineIndicesOpen) == 0:
					#print "   Found open polyline."
					polylineIndicesOpen.append(polylineInd)

				# Set start index to next polyline.
				startIndex += numberOfPoints+1


			# Get closed polyline points according to indices.
			polylinesClosed = []
			for polyline in polylineIndicesClosed:
				polylinePoints = points[polyline]
				polylinesClosed.append(polylinePoints)


			# Get open polyline points according to indices.
			polylinesOpen = []
			for polyline in polylineIndicesOpen:
				polylinePoints = points[polyline]
				polylinesOpen.append(polylinePoints)

			#print "   Found " + str(len(polylinesClosed)) + " closed segments."
			#print "   Found " + str(len(polylinesOpen)) + " open segments."

			# Loop over open polyline parts and pick the ones that connect.
			# Do this until everything is connected.
			#print "Trying to connect open segments."
			polylinesCorrupted = []
			# Create list of flags for matched segments.
			matched = [False for i in range(len(polylinesOpen))]
			# Loop through open segments.
			for i in range(len(polylinesOpen)):
				#print "Testing open segment " + str(i) + ". ********************************"

				# Get a segment and try to match it to any other segment.
				# Only do this if the segment has not been matched before.
				if matched[i] == True:
					pass
					#print "   Segment was matched before. Skipping."
				else:
					segmentA = polylinesOpen[i]

					#print (segmentA[0] == segmentA[0]).all()

					# Flag that signals if any of the other segments was a match.
					runAgain = True # Set true to start first loop.
					while runAgain == True:
						# Set false to stop loop if no match is found.
						runAgain = False
						isClosed = False
						# Loop through all other segments check for matches.
						for j in range(len(polylinesOpen)):
							# Only if this is not segmentA and if it still unmatched.
							if j != i and matched[j] == False:

								# Get next piece to match to current piece.
								segmentB = polylinesOpen[j]

								# Compare current piece and next piece start and end points.
								# If a match is found, add next piece to current piece.
								# Loop over next pieces until no match is found or the piece is closed.
								# Start points equal: flip new array and prepend.
								if (segmentB[0] == segmentA[0]).all():
									#print "   Start-start match with segment " + str(j) + "."
									segmentA = numpy.insert(segmentA, 0, numpy.flipud(segmentB[1:]), axis=0)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now is closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True


								elif (segmentB[0] == segmentA[-1]).all():
									#print "   Start-end match with segment " + str(j) + "."
									segmentA = numpy.append(segmentA, segmentB[1:])
									segmentA = segmentA.reshape(-1,2)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

								elif (segmentB[-1] == segmentA[0]).all():
									#print "   End-start match with segment " + str(j) + "."
									segmentA = numpy.insert(segmentA, 0, segmentB[:-1], axis=0)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

								elif (segmentB[-1] == segmentA[-1]).all():
									#print "   End-end match with segment " + str(j) + "."
									segmentA = numpy.append(segmentA, numpy.flipud(segmentB[:-1]), axis=0)
									segmentA = segmentA.reshape(-1,2)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

						# If no match was found and segmentA is still open,
						# copy it to defective segments array.
						if runAgain == False and isClosed == False:
							endPointDistance = math.sqrt( pow((segmentA[0][0] -segmentA[-1][0])/self.pxPerMmX, 2) + pow((segmentA[0][1] -segmentA[-1][1])/self.pxPerMmY, 2) )
							if endPointDistance < (self.polylineClosingThreshold):
								#print "      End point distance below threshold. Closing manually."
								polylinesClosed.append(segmentA)
							else:
								#print "      Giving up on this one..."
								polylinesCorrupted.append(segmentA)
						elif runAgain == False and isClosed == True:
							pass
							#print "   Segment is closed. Advancing to next open segment."
						else:
							pass
							#print "   Matches were found. Restarting loop to find more..."

			polylinesClosedAll.append(polylinesClosed)

			if len(polylinesCorrupted) != 0:
				polylinesCorruptedAll.append(polylinesCorrupted)

		# End timer.
		if self.debug:
			interval = time.time() - interval
			print "Polyline point sort time: " + str(interval) + " s."

		# Return polylines.
		return (polylinesClosedAll, polylinesCorruptedAll)

		'''
		polylinesClosedAll = []
		polylinesCorruptedAll = []
		# Do this for model, supports and bottom plate.
		sectionStrippers = [self.sectionStripperModel, self.sectionStripperSupports, self.sectionStripperBottomPlate]
		activationFlags = [model, supports, bottomPlate]
		for i in range(len(sectionStrippers)):#[self.sectionStripperModel, self.sectionStripperSupports, self.sectionStripperBottomPlate]:
			numberOfPolylines = 0
			sectionStripper = sectionStrippers[i]
			if activationFlags[i]:

				#print "Sorting polyline pieces. ************************"
				# Get the polyline points. These are not ordered.
				points = sectionStripper.GetOutput().GetPoints().GetData()
				# Convert to  numpy array.
				points = numpy_support.vtk_to_numpy(points)
				# Remove Z dimension.
				points = points[:,0:2]
				# Scale to fit the image (convert from mm to px).
				points[:,0] *= self.pxPerMmX
				points[:,1] *= self.pxPerMmX
				# Move points to center of image.
				points[:,0] -= self.position[0]
				points[:,1] -= self.position[1]
				# Flip points y-wise because image coordinates start at top.
				points[:,1] = abs(points[:,1] - self.size[1])

				# Get the lines. These contain point indices in the right order for each polyline.
				lines = sectionStripper.GetOutput().GetLines()#.GetData()
				numberOfPolylines = lines.GetNumberOfCells()
			if numberOfPolylines < 1:
				#print "   No polylines found."
				polylinesClosedAll.append([])
			else:
				#print "   Found " + str(numberOfPolylines) + " polylines."
				lines = lines.GetData()
				# Convert to numpy array.
				lines = numpy_support.vtk_to_numpy(lines)


				polylineIndicesClosed = []
				polylineIndicesOpen = []
				startIndex = 0

				# Check if there are connecting polylines.
				# This is necessary because some polylines from the stripper output may still be segmented.
				# Two polylines are connected if the start or end point indices are equal.
				# Test for start/start, end/end, start/end, end/start.
				for polyline in range(numberOfPolylines):
					#print "Polyline " + str(polyline) + ". ****************"
					numberOfPoints = lines[startIndex]
					#print "   Start point: " + str(points[lines[startIndex+1]]) + "."
					#print "   End point: " + str(points[lines[startIndex+numberOfPoints]]) + "." # -1
					# Get the indices starting just behind the start index.
					polylineInd = lines[startIndex+1:startIndex+1+numberOfPoints]

					# Check if polyline is closed. If yes, append to closed list.
					if polylineInd[0] == polylineInd[-1]:
						#print "   Found closed polyline."
						polylineIndicesClosed.append(polylineInd)
					# If not, check if this is the first open one. If yes, append.
					else:# len(polylineIndicesOpen) == 0:
						#print "   Found open polyline."
						polylineIndicesOpen.append(polylineInd)

					# Set start index to next polyline.
					startIndex += numberOfPoints+1


				# Get polyline points according to indices.
				polylinesClosed = []
				for polyline in polylineIndicesClosed:
					polylinePoints = points[polyline]
					# Convert to numpy array. dtype must be int32 for cv2.fillPoly
				#	polylinePoints = numpy.array(polylinePoints, dtype=numpy.int32) # DO THIS LATER AFTER CONVERTING TO FP.
					# Save as integers.
					polylinesClosed.append(polylinePoints)


				# Get polyline points according to indices.
				polylinesOpen = []
				for polyline in polylineIndicesOpen:
					polylinePoints = points[polyline]
					# Convert to numpy array. dtype must be int32 for cv2.fillPoly
				#	polylinePoints = numpy.array(polylinePoints, dtype=numpy.int32)
					# Save as integers.
					polylinesOpen.append(polylinePoints)

				#if sectionStripper == self.sectionStripperModel:
					#print "##########################################################"
					#print "Found " + str(len(polylinesClosed)) + " closed segments."
					#print "Found " + str(len(polylinesOpen)) + " open segments."
					#print "##########################################################"

				# Loop over open polyline parts and pick the ones that connect.
				# Do this until everything is connected.
				#print "Trying to connect open segments."
				polylinesCorrupted = []
				# Create list of flags for matched segments.
				matched = [False for i in range(len(polylinesOpen))]
				# Loop through open segments.
				for i in range(len(polylinesOpen)):
					#print "Testing open segment " + str(i) + ". ********************************"

					# Get a segment and try to match it to any other segment.
					# Only do this if the segment has not been matched before.
					if matched[i] == True:
						pass
						#print "   Segment was matched before. Skipping."
					else:
						segmentA = polylinesOpen[i]

						#print (segmentA[0] == segmentA[0]).all()

						# Flag that signals if any of the other segments was a match.
						runAgain = True # Set true to start first loop.
						while runAgain == True:
							# Set false to stop loop if no match is found.
							runAgain = False
							isClosed = False
							# Loop through all other segments check for matches.
							for j in range(len(polylinesOpen)):
								# Only if this is not segmentA and if it still unmatched.
								if j != i and matched[j] == False:

									# Get next piece to match to current piece.
									segmentB = polylinesOpen[j]

									# Compare current piece and next piece start and end points.
									# If a match is found, add next piece to current piece.
									# Loop over next pieces until no match is found or the piece is closed.
									# Start points equal: flip new array and prepend.
									if (segmentB[0] == segmentA[0]).all():
										#print "   Start-start match with segment " + str(j) + "."
										segmentA = numpy.insert(segmentA, 0, numpy.flipud(segmentB[1:]), axis=0)
										matched[j] = True
										# Check if this closes the line.
										if (segmentA[0] == segmentA[-1]).all():
											#print "      Polyline now is closed."
											polylinesClosed.append(segmentA)
											isClosed = True
											runAgain = False
											break
										else:
											runAgain = True


									elif (segmentB[0] == segmentA[-1]).all():
										#print "   Start-end match with segment " + str(j) + "."
										segmentA = numpy.append(segmentA, segmentB[1:])
										segmentA = segmentA.reshape(-1,2)
										matched[j] = True
										# Check if this closes the line.
										if (segmentA[0] == segmentA[-1]).all():
											#print "      Polyline now closed."
											polylinesClosed.append(segmentA)
											isClosed = True
											runAgain = False
											break
										else:
											runAgain = True

									elif (segmentB[-1] == segmentA[0]).all():
										#print "   End-start match with segment " + str(j) + "."
										segmentA = numpy.insert(segmentA, 0, segmentB[:-1], axis=0)
										matched[j] = True
										# Check if this closes the line.
										if (segmentA[0] == segmentA[-1]).all():
											#print "      Polyline now closed."
											polylinesClosed.append(segmentA)
											isClosed = True
											runAgain = False
											break
										else:
											runAgain = True

									elif (segmentB[-1] == segmentA[-1]).all():
										#print "   End-end match with segment " + str(j) + "."
										segmentA = numpy.append(segmentA, numpy.flipud(segmentB[:-1]), axis=0)
										segmentA = segmentA.reshape(-1,2)
										matched[j] = True
										# Check if this closes the line.
										if (segmentA[0] == segmentA[-1]).all():
											#print "      Polyline now closed."
											polylinesClosed.append(segmentA)
											isClosed = True
											runAgain = False
											break
										else:
											runAgain = True

							# If no match was found and segmentA is still open,
							# copy it to defective segments array.
							if runAgain == False and isClosed == False:
								endPointDistance = math.sqrt( pow((segmentA[0][0] -segmentA[-1][0])/self.pxPerMmX, 2) + pow((segmentA[0][1] -segmentA[-1][1])/self.pxPerMmY, 2) )
								if endPointDistance < (self.polylineClosingThreshold):
									#print "      End point distance below threshold. Closing manually."
									polylinesClosed.append(segmentA)
								else:
									#print "      Giving up on this one..."
									polylinesCorrupted.append(segmentA)
							elif runAgain == False and isClosed == True:
								pass
								#print "   Segment is closed. Advancing to next open segment."
							else:
								pass
								#print "   Matches were found. Restarting loop to find more..."

				polylinesClosedAll.append(polylinesClosed)

				if len(polylinesCorrupted) != 0:
					polylinesCorruptedAll.append(polylinesCorrupted)






		# End timer.
		if self.debug:
			interval = time.time() - interval
			print "Polyline point sort time: " + str(interval) + " s."

		# Return polylines.
		return (polylinesClosedAll, polylinesCorruptedAll)
		'''






  ##### ##     ###### ####   #####   #####  ##  ##  ##### ##### ##### #####
 ##     ##       ##  ##  ## ##       ##  ## ##  ## ##    ##    ##     ##  ##
  ####  ##       ##  ##     ####     #####  ##  ## ####  ####  ####   ##  ##
     ## ##       ##  ##     ##       ##  ## ##  ## ##    ##    ##     #####
     ## ##       ##  ##  ## ##       ##  ## ##  ## ##    ##    ##     ## ##
 #####  ###### ###### ####   #####   #####   ####  ##    ##     ##### ##  ##



################################################################################
# A list with some additional access features.	################################
################################################################################
class sliceBuffer:

	# Create buffer of odd length.
	def __init__(self, size):
		# Add one if size is even.
		if size % 2 != 1:
			size += 1
		self.size = size
		self.stack = [None for i in range(self.size)]
		self.center = int(math.floor(size / 2)) # 0-based!


	# Shift buffer and push new image to end.
	def addSlice(self, sliceImage):
		del self.stack[0]
		self.stack.append(sliceImage)


	# Get the center item.
	def getCenter(self):
		return self.stack[self.center]


	# Get the buffer contents above the center.
	def getAboveCenter(self):
		return self.stack[self.center+1:]


	# Get the buffer contents below the center.
	def getBelowCenter(self):
		return self.stack[:self.center]




################################################################################
# EOF ##########################################################################
################################################################################
