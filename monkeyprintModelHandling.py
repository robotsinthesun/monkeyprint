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

class modelContainer:
	def __init__(self, filenameOrSettings, programSettings, console=None):

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

		# Create model object.
		self.model = modelData(filename, self.settings, programSettings, self.console)

		# active flag. Only do updates if model is active.
		self.flagactive = True

		# Update model and supports.
		self.updateModel()
		self.updateSupports()

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
		self.model.updateModel()

	def updateSupports(self):
		#self.model.setChanged()
		self.model.updateBottomPlate()
		self.model.updateSupports()

	def updateSlice3d(self, sliceNumber):
		self.model.updateSlice3d(sliceNumber)

	def updateSliceStack(self):
		self.model.startBackgroundSlicer()

	def sliceThreadListener(self):
#		self.model.setChanged()
		self.model.checkBackgroundSlicer()

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
		print "bar"
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


################################################################################
################################################################################
################################################################################

class modelCollection(dict):
	def __init__(self, programSettings, console=None):
		# Call super class init function. *********************
		dict.__init__(self)

		# Internalise settings. *******************************
		self.programSettings = programSettings
		self.console = console

		# Create slice image. *********************************
		self.sliceImage = imageHandling.createImageGray(self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value, 0)
		self.sliceImageBlack = numpy.empty_like(self.sliceImage)

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
		self.jobSettings = monkeyprintSettings.jobSettings(self.programSettings)

	# Reload calibration image.
	def subtractCalibrationImage(self, inputImage):
		# Get the image if it does not exist.
		if self.calibrationImage == None and self.programSettings['calibrationImage'].value:
	#		print "Loading calibration image."
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

				print calibrationImage.shape

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


	# Save slice stack.
	def saveSliceStack(self, path, updateFunction=None):
		# Get number of slices.
		nSlices = self.getNumberOfSlices()
		digits = len(str(nSlices))
		for i in range(nSlices):
			# Update progress bar.
			if updateFunction != None:
				updateFunction(i)
				while gtk.events_pending():
					gtk.main_iteration(False)
			# Format number string.
			numberString = str(i).zfill(digits)
			# Create image file string.
			fileString = path[:-4] + numberString + path[-4:]
			print "Saving image " + fileString + "."
			image = Image.fromarray(self.updateSliceImage(i))
			image.save(fileString)


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
		data = [self.jobSettings, modelSettings, listStoreList]#TODO
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
				print path.split('/')[-1]
				try:
					mkpFile.add(path, arcname=path.split('/')[-1])
				except IOError, OSError:
					print "Stl file not found..."
# TODO: Handle file not found error in GUI.
# TODO: Maybe copy stls into temporary dir upon load?
# This would be consistent with loading an mkp file and saving stls to tmp dir.

	# Load a compressed model collection from disk.
	def loadProject(self, filename):
		# Create temporary working directory.
		tmpPath = os.getcwd()+'/tmp'
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
		self.jobSettings = data[0]
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
		self[modelId] = modelContainer(filenameOrSettings, self.programSettings, self.console)
		# Set new model as current model.
		self.currentModelId = modelId

	# Function to remove a model from the model collection
	def remove(self, modelId):
		if self[modelId]:
			self[modelId].model.killBackgroundSlicer()
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
		height = 0
		# Loop through all models.
		for model in self:
			# If model higher than current height value...
			if height < self[model].getHeight():
				# ... set new height value.
				height = self[model].getHeight()
		if self.console != None:
			self.console.addLine('Maximum model height: ' + str(height) + ' mm.')
		numberOfSlices = int(math.floor(height / self.programSettings['layerHeight'].value))
		return numberOfSlices

	# Update the slice stack. Set it's height according to max model
	# height and layerHeight.
	def updateSliceStack(self):
		# Update all models' slice stacks.
		for model in self:
			self[model].updateSliceStack()



	# Create the projector frame from the model slice stacks.
	def updateSliceImage(self, i):
		# Make sure index is an integer.
		i = int(i)
		# Get slice images from all models and add to projector frame.
		# Reset projector frame.
		self.sliceImage = imageHandling.createImageGray(self.programSettings['projectorSizeX'].value, self.programSettings['projectorSizeY'].value, 0)
	#	print "Projector dimensions: " + str(self.sliceImage.shape) + "."
		# Get slice images from models.
		# Append the slice image and its position on the projector frame.
		imgList = []
		for model in self:
	#		self[model].updateSlice3d(sliceNumber)
			if model != "default" and self[model].isactive() and i<len(self[model].model.sliceStack):
	#			print "Image dimensions: " + str(self[model].model.sliceStack[i].shape) + "."
				imgList.append((self[model].model.sliceStack[i], self[model].model.getSlicePosition()))
		# Add list of slice images to projector frame.
		for i in range(len(imgList)):
			self.sliceImage = imageHandling.imgAdd(self.sliceImage, imgList[i][0], imgList[i][1])
		# Subtract calibration image.
		self.sliceImage = self.subtractCalibrationImage(self.sliceImage)
		return self.sliceImage



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

	def slicerRunning(self):
		# Return True if one of the slicers is still running.
		running = False
		for model in self:
		#	if self[model].model.flagSlicerRunning:
		#		print ("Slicer of model " + model + " is running.")
			running = running or self[model].model.flagSlicerRunning
		#	print running
		return running


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




################################################################################
################################################################################
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


################################################################################
################################################################################
################################################################################

class modelData:

	###########################################################################
	# Construction method definition. #########################################
	###########################################################################

	def __init__(self, filename, settings, programSettings, console=None):

		# Create VTK error observer to catch errors.
		self.errorObserver = ErrorObserver()

		# Set up variables.
		# Internalise settings.
		self.filenameStl = ""
		self.filename = filename
		self.flagactive = True
		self.settings = settings
		self.programSettings = programSettings
		self.console = console

		# Set up values for model positioning.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0

		self.flagChanged = False

		self.flagSlicerRunning = False

		# Set up the slice stack. Has one slice only at first...
		self.sliceStack = sliceStack()
		self.slicePosition = (0,0)

		# Background thread for updating the slices on demand.
		self.queueSlicerIn = Queue.Queue()
		self.queueSlicerOut = Queue.Queue()
		if self.filename != "":
			# Initialise the thread.
			if self.console!=None:
				self.console.addLine("Starting slicer thread")
			self.slicerThread = backgroundSlicer(self.settings, self.programSettings, self.queueSlicerIn, self.queueSlicerOut, self.console)
			self.slicerThread.start()


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
			# Create stl source.
			self.stlReader = vtk.vtkSTLReader() # File name will be set later on when model is actually loaded.
			self.stlReader.SetFileName(self.filename)
			self.stlReader.Update() # Required with VTK6, otherwise the file isn't loaded
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
			else:
				self.volumeModel.SetInputConnection(self.stlPositionFilter.GetOutputPort())
			self.volumeSupports = vtk.vtkMassProperties()
			self.volumeSupports.AddObserver('WarningEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.volumeSupports.SetInput(self.supports.GetOutput())
			else:
				self.volumeSupports.SetInputConnection(self.supports.GetOutputPort())
			self.volumeBottomPlate = vtk.vtkMassProperties()
			self.volumeBottomPlate.AddObserver('WarningEvent', self.errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				self.volumeBottomPlate.SetInput(self.bottomPlate.GetOutput())
			else:
				self.volumeBottomPlate.SetInputConnection(self.bottomPlate.GetOutputPort())


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
			# Only update supports volume if there are supports in the appendPolyData.
			if self.supports.GetNumberOfInputConnections(0) > 0:
				self.volumeSupports.Update()
				if self.programSettings['showVtkErrors'].value and self.errorObserver.WarningOccurred():
					print "VTK Warning: " + self.errorObserver.WarningMessage()
				elif self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
					print "VTK Error: " + self.errorObserver.ErrorMessage()
			self.volumeBottomPlate.Update()
			if self.programSettings['showVtkErrors'].value and self.errorObserver.ErrorOccurred():
				print "VTK Error: " + self.errorObserver.ErrorMessage()

			# Get volume in mm³.
			if self.supports.GetNumberOfInputConnections(0) > 0:
				volume = self.volumeModel.GetVolume() + self.volumeSupports.GetVolume() + self.volumeBottomPlate.GetVolume()
			else:
				volume = self.volumeModel.GetVolume() + self.volumeBottomPlate.GetVolume()
			# Convert to cm³ and round to 2 decimals.
			volume = math.trunc(volume / 10.) /100.
			return volume
		else:
			return 0.0


	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)

	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)

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



	###########################################################################
	# Update methods. #########################################################
	###########################################################################
	def updateModel(self):
		if self.filename != "" and self.isactive():
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
			#
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
			# Update slice stack if it was filled before (if the slice tab was opened before).
#			if len(self.sliceStack) > 1:
#				print "foo"
#				self.startBackgroundSlicer()
#			else:
#				print "bar"


	def updateBottomPlate(self):
		if self.filename != "" and self.isactive():
			modelBounds = self.getBounds()
			self.bottomPlate.SetXLength(modelBounds[1] - modelBounds[0])
			self.bottomPlate.SetYLength(modelBounds[3] - modelBounds[2])
			self.bottomPlate.SetZLength(self.settings['bottomPlateThickness'].value)
			self.bottomPlate.SetCenter( (modelBounds[0] + modelBounds[1]) / 2.0, (modelBounds[2] + modelBounds[3]) / 2.0, self.settings['bottomPlateThickness'].value/2.0)
			self.bottomPlate.Update()
			self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()) )


	def updateOverhang(self):
		if self.filename != "" and self.isactive():
			# Calculate clipping threshold based on Z component..
			# Z normals are 1 if pointing upwards, -1 if downwards and 0 if pointing sideways.
			# Turn angle into value between -1 and 0.
			self.clipThreshold = -math.cos(self.settings['overhangAngle'].value/180.0*math.pi)
			self.overhangClipFilter.SetValue(self.clipThreshold)
			self.overhangClipFilter.Update()


	# Update supports. ########################################################
	def updateSupports(self):

		if self.filename != "" and self.isactive():
			# Update overhang.
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

	#TODO: Add support regions using	overhangRegionFilter.Update();

			# Update the cell locator.
			self.locator.BuildLocator()
			self.locator.Update()

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
						else:
							support_inputs += 2
							self.supports.SetNumberOfInputs(support_inputs)
							self.supports.SetInputConnectionByNumber(support_inputs - 2, coneGeomFilter.GetOutputPort())
						# Delete the cone. Vtk delete() method does not work in python because of garbage collection.
						del cone
						# Append the cylinder to the cones polydata.
						if vtk.VTK_MAJOR_VERSION <= 5:
							self.supports.AddInput(cylinderGeomFilter.GetOutput())
						else:
							self.supports.SetInputConnectionByNumber(support_inputs - 1, cylinderGeomFilter.GetOutputPort())
						del cylinder
		#				i += 1
		#	print "Created " + str(i) + " supports."
			self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()) )



	# Update slice actor.
	def updateSlice3d(self, sliceNumber):
		if self.filename != "" and self.isactive():
			# Update pipeline with slice position given by layerHeight and slice number.
			if sliceNumber == 0:
				zPosition = 0.01
			else:
				zPosition = self.programSettings['layerHeight'].value*sliceNumber
			self.cuttingPlane.SetOrigin(0,0,zPosition)
			self.combinedCutlines.Update()
			self.combinedClipModels.Update()



	def startBackgroundSlicer(self):
		# Only update if this is not default flag and the
		# model or supports have been changed before.
		if self.filename!="" and self.flagChanged and self.isactive():
			if self.console != None:
				self.console.addLine('Slicer started.')
			# Reset the slice stack.
			self.sliceStack.reset(self.getSliceSize()[0], self.getSliceSize()[1], self.getNumberOfSlices())
			# If there's nothing in the queue...
			if self.queueSlicerIn.empty():
				# ... write the model polydata to the queue.
				#test = vtk.vtkPolyData()
				#test.DeepCopy(self.stlPositionFilter.GetOutput())
				#print self.stlPositionFilter.GetOutput()
				self.queueSlicerIn.put([self.stlPositionFilter.GetOutput(), self.supports.GetOutput(), self.bottomPlate.GetOutput()])
			self.flagChanged = False
			self.flagSlicerRunning = True


	# Listen for the slicer threads output if it has finished.
	def checkBackgroundSlicer(self):
		# If a slice stack is in the output queue...
		if self.queueSlicerOut.qsize():
			# ... get it.
			if self.console != None:
				self.console.addLine('Slicer done.')
			self.sliceStack[:] = self.queueSlicerOut.get()
			self.flagSlicerRunning = False




	def killBackgroundSlicer(self):
		self.slicerThread.stop()



	def getSizePxXY(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get layerHeight in mm.
		layerHeight =	self.programSettings['layerHeight'].value
		# Calc number of layers.
		numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
		# Get rim size in pixels.
		rim = int(self.programSettings['modelSafetyDistance'].value * self.programSettings['pxPerMm'].value)
		# Get position in pixels. Include rim.
		position = [bounds[0]/self.programSettings['pxPerMm'].value-rim, bounds[2]/self.programSettings['pxPerMm'].value-rim, 0]
		# Get size in pixels. Add rim twice.
		width = int(math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2)
		height = int(math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2)

		return (width, height, numberOfSlices, position)



	# Return slice size (width, height).
	def getSliceSize(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get rim size in pixels.
		rim = int(self.programSettings['modelSafetyDistance'].value * self.programSettings['pxPerMm'].value)
		# Get size in pixels. Add rim twice.
		width = int(math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2)
		height = int(math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2)
		size = (width, height)
		return size



	def getNumberOfSlices(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get layerHeight in mm.
		layerHeight =	self.programSettings['layerHeight'].value
		# Calc number of layers.
		numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
		return numberOfSlices



	def getSlicePosition(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get rim size in pixels.
		rim = int(self.programSettings['modelSafetyDistance'].value * self.programSettings['pxPerMm'].value)
		# Get position in pixels. Include rim.
		position = (bounds[0]*self.programSettings['pxPerMm'].value-rim, bounds[2]*self.programSettings['pxPerMm'].value-rim)
		return position



	###########################################################################
	# Public methods to retrieve actors and other data. #######################
	###########################################################################

	# Get number if slices for the layer slider in the gui.
#	def getNumberOfSlices(self):
#		return int(math.floor(self.inputModelPolydata.GetBounds()[5] / self.settings.getLayerHeight()))

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






################################################################################
# A list of all the slices. ####################################################
################################################################################
# Contains all slices for preview and will be continuously updated
# in a background thread.
class sliceStack(list):
	def __init__(self, programSettings=None):
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


	# Add new image stack at given position.
	def newModelStack(self, bounds, start=0):
		# Get layerHeight from settings.
		stackHeight = int(bounds[5] / self.programSettings['layerHeight'].value)
		# Convert position and size to pixels, height to number of slices.
		# Define rim size in pixel.
		rim = 0
		# Get position. Add rim.
		position = [int(bounds[0] * self.programSettings['pxPerMm'].value - rim), int(bounds[2] * self.programSettings['pxPerMm'].value - rim)]
		print position
		# Get size in pixels. Add rim twice.
		width = math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2
		print width
		height = math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2
		print height

		for i in range(start, stackHeight):
			img = imageHandling.createImageGray(width, height, 0)	# 0=black, 255=white
			img = img + i # Just for testing...
			self[i] = imageHandling.insert(self[i], img, position)#self.sliceArray[i][bounds[0]:bounds[1],bounds[2]:bounds[3]] = img



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


	# Function to add an image to a specific slice and at a specific position.
	def addSlice(self, index, image, position):
		position = [	position[0] * self.programSettings['pxPerMm'].value,
					position[1] * self.programSettings['pxPerMm'].value	]
		# If index in bounds...
		if index < len(self):
			# Get the image.
			self[int(index)] =  imageHandling.imgAdd(self[int(index)], image, position)






################################################################################
# A thread to slice the model in background.	###################################
################################################################################
class backgroundSlicer(threading.Thread):
	def __init__(self, settings, programSettings, queueSlicerIn, queueSlicerOut, console=None):
		# Internalise inputs.
#		self.slicingFunction = slicingFunction
		self.settings = settings
		self.programSettings = programSettings
		self.queueSlicerIn = queueSlicerIn
		self.queueSlicerOut = queueSlicerOut
		self.console = console
		# Thread stop event.
		self.stopThread = threading.Event()
		# Call super class init function.
		super(backgroundSlicer, self).__init__()

		self.sliceStackNew = []

	# Overload the run method.
	# This will automatically run once the init function is done.
	def run(self):
		if self.console:
			self.console.addLine("Slicer thread initialised")
		# Go straight into idle mode.
		self.idle()

	# Check for input models in the queue.
	def newInputInQueue(self):
		if self.queueSlicerIn.qsize():
			return True
		else:
			return False

	# Continuously check queue for start signals.
	def idle(self):
		# Do nothing as long as nothing is in the queue.
		while not self.newInputInQueue() and not self.stopThread.isSet():
			time.sleep(0.1)
		# If input has arrived get the input run slicer function.
		if not self.stopThread.isSet():
			newInput = self.queueSlicerIn.get()
			self.runSlicer(newInput)


	def runSlicer(self, inputModel):
		# Don't run if stop condition is set.
		while not self.stopThread.isSet():
			# Check if new input is in queue. If not...
			if not self.newInputInQueue():
				# ...do the slicing.
				self.sliceStackNew = self.updateSlices(inputModel)
				if self.programSettings['debug'].value:
					print "Slicer done."

			# If yes...
			else:
				# Break the loop, return to idle mode and restart from there.
				break
			# Write the model to the output queue.
			self.queueSlicerOut.put(self.sliceStackNew)
			break
		# Go back to idle mode.
		self.idle()

	def stop(self):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()

	def join(self, timeout=None):
		if self.console != None:
			self.console.addLine("Stopping slicer thread")
		self.stopThread.set()
		threading.Thread.join(self, timeout)


	# Update slice stack.
	def updateSlices(self, inputModel):
		if not self.stopThread.isSet():

			# Set up slice stack as list.
			sliceStack = []

			# Create VTK error observer to catch errors.
			errorObserver = ErrorObserver()

			# Create model containers.
			polyDataModel = vtk.vtkPolyData()
			polyDataSupports = vtk.vtkPolyData()
			polyDataBottomPlate = vtk.vtkPolyData()

			# Create the VTK pipeline.
			extrusionVector = (0,0,-1)
			# Create cutting plane.
			cuttingPlane = vtk.vtkPlane()
			cuttingPlane.SetNormal(0,0,1)
			cuttingPlane.SetOrigin(0,0,0.001)	# Make sure bottom plate is cut properly.
			# Create cutting filter for model.
			cuttingFilterModel = vtk.vtkCutter()
			cuttingFilterModel.SetCutFunction(cuttingPlane)
			# Create cutting filter for supports.
			cuttingFilterSupports = vtk.vtkCutter()
			cuttingFilterSupports.SetCutFunction(cuttingPlane)
			# Create cutting filter for bottom plate.
			cuttingFilterBottomPlate = vtk.vtkCutter()
			cuttingFilterBottomPlate.SetCutFunction(cuttingPlane)
			# Create polylines from cutter output for model.
			sectionStripperModel = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				sectionStripperModel.SetInput(cuttingFilterModel.GetOutput())
			else:
				sectionStripperModel.SetInputConnection(cuttingFilterModel.GetOutputPort())
			# Create polylines from cutter output for supports.
			sectionStripperSupports = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				sectionStripperSupports.SetInput(cuttingFilterSupports.GetOutput())
			else:
				sectionStripperSupports.SetInputConnection(cuttingFilterSupports.GetOutputPort())
			# Create polylines from cutter output for bottom plate.
			sectionStripperBottomPlate = vtk.vtkStripper()
			if vtk.VTK_MAJOR_VERSION <= 5:
				sectionStripperBottomPlate.SetInput(cuttingFilterBottomPlate.GetOutput())
			else:
				sectionStripperBottomPlate.SetInputConnection(cuttingFilterBottomPlate.GetOutputPort())
			# Extrude cut polyline of model.
			extruderModel = vtk.vtkLinearExtrusionFilter()
			extruderModel.AddObserver('ErrorEvent', errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderModel.SetInput(sectionStripperModel.GetOutput())
			else:
				extruderModel.SetInputConnection(sectionStripperModel.GetOutputPort())
			extruderModel.SetScaleFactor(1)
			extruderModel.CappingOn()
			extruderModel.SetExtrusionTypeToVectorExtrusion()
			extruderModel.SetVector(extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
			# Extrude cut polyline of supports.
			extruderSupports = vtk.vtkLinearExtrusionFilter()
			extruderSupports.AddObserver('ErrorEvent', errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderSupports.SetInput(sectionStripperSupports.GetOutput())
			else:
				extruderSupports.SetInputConnection(sectionStripperSupports.GetOutputPort())
			extruderSupports.SetScaleFactor(1)
			extruderSupports.CappingOn()
			extruderSupports.SetExtrusionTypeToVectorExtrusion()
			extruderSupports.SetVector(extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
			# Extrude cut polyline.
			extruderBottomPlate = vtk.vtkLinearExtrusionFilter()
			extruderBottomPlate.AddObserver('ErrorEvent', errorObserver)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderBottomPlate.SetInput(sectionStripperBottomPlate.GetOutput())
			else:
				extruderBottomPlate.SetInputConnection(sectionStripperBottomPlate.GetOutputPort())
			extruderBottomPlate.SetScaleFactor(1)
			extruderBottomPlate.CappingOn()
			extruderBottomPlate.SetExtrusionTypeToVectorExtrusion()
			extruderBottomPlate.SetVector(extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
			# Create single channel VTK image.
			image = vtk.vtkImageData()
			if vtk.VTK_MAJOR_VERSION <= 5:
				image.SetScalarTypeToUnsignedChar()
				image.SetNumberOfScalarComponents(1)
			else:
				image.SetPointDataActiveScalarInfo(image.GetInformation(), vtk.VTK_UNSIGNED_CHAR, 1)

			# Create image stencil from extruded polyline for model.
			extruderStencilModel = vtk.vtkPolyDataToImageStencil()
			extruderStencilModel.SetTolerance(0)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderStencilModel.SetInput(extruderModel.GetOutput())
			else:
				extruderStencilModel.SetInputConnection(extruderModel.GetOutputPort())
			# Create image stencil from extruded polyline for supports.
			extruderStencilSupports = vtk.vtkPolyDataToImageStencil()
			extruderStencilSupports.SetTolerance(0)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderStencilSupports.SetInput(extruderSupports.GetOutput())
			else:
				extruderStencilSupports.SetInputConnection(extruderSupports.GetOutputPort())
			# Create image stencil from extruded polyline for bottom plate.
			extruderStencilBottomPlate = vtk.vtkPolyDataToImageStencil()
			extruderStencilBottomPlate.SetTolerance(0)
			if vtk.VTK_MAJOR_VERSION <= 5:
				extruderStencilBottomPlate.SetInput(extruderBottomPlate.GetOutput())
			else:
				extruderStencilBottomPlate.SetInputConnection(extruderBottomPlate.GetOutputPort())
			# Cut white image with stencil.
			stencilModel = vtk.vtkImageStencil()
			if vtk.VTK_MAJOR_VERSION <= 5:
				stencilModel.SetInput(image)
				stencilModel.SetStencil(extruderStencilModel.GetOutput())
			else:
				stencilModel.SetInputData(image)
				stencilModel.SetStencilConnection(extruderStencilModel.GetOutputPort())
			stencilModel.ReverseStencilOff()
			stencilModel.SetBackgroundValue(0.0)
			# Cut white image with stencil.
			stencilSupports = vtk.vtkImageStencil()
			if vtk.VTK_MAJOR_VERSION <= 5:
				stencilSupports.SetInput(image)
				stencilSupports.SetStencil(extruderStencilSupports.GetOutput())
			else:
				stencilSupports.SetInputData(image)
				stencilSupports.SetStencilConnection(extruderStencilSupports.GetOutputPort())
			stencilSupports.ReverseStencilOff()
			stencilSupports.SetBackgroundValue(0.0)
			# Cut white image with stencil.
			stencilBottomPlate = vtk.vtkImageStencil()
			if vtk.VTK_MAJOR_VERSION <= 5:
				stencilBottomPlate.SetInput(image)
				stencilBottomPlate.SetStencil(extruderStencilBottomPlate.GetOutput())
			else:
				stencilBottomPlate.SetInputData(image)
				stencilBottomPlate.SetStencilConnection(extruderStencilBottomPlate.GetOutputPort())
			stencilBottomPlate.ReverseStencilOff()
			stencilBottomPlate.SetBackgroundValue(0.0)

			# Copy model data.
			polyDataModel.DeepCopy(inputModel[0])
			polyDataSupports.DeepCopy(inputModel[1])
			polyDataBottomPlate.DeepCopy(inputModel[2])

			# Set inputs.
			if vtk.VTK_MAJOR_VERSION <= 5:
				cuttingFilterModel.SetInput(polyDataModel)
				cuttingFilterModel.Update()
				cuttingFilterSupports.SetInput(polyDataSupports)
				cuttingFilterBottomPlate.SetInput(polyDataBottomPlate)
			else:
				cuttingFilterModel.SetInputData(polyDataModel)
				cuttingFilterModel.Update()
				cuttingFilterSupports.SetInputData(polyDataSupports)
				cuttingFilterBottomPlate.SetInputData(polyDataBottomPlate)

			# Calc slice stack parameters.
			# Get size of the model in mm.
			bounds = [0 for i in range(6)]
			polyDataModel.GetBounds(bounds)
			print "Model bounds: " + str(bounds) + "."
			# Get layerHeight in mm.
			layerHeight =	self.programSettings['layerHeight'].value
			# Calc number of layers.
			numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
			# Get rim size in pixels.
			rim = int(self.programSettings['modelSafetyDistance'].value * self.programSettings['pxPerMm'].value)
			# Get position in pixels. Include rim.
			position = (int(bounds[0]*self.programSettings['pxPerMm'].value-rim), int(bounds[2]*self.programSettings['pxPerMm'].value-rim), 0)
			positionMm = (bounds[0]-rim/self.programSettings['pxPerMm'].value, bounds[2]-rim/self.programSettings['pxPerMm'].value, 0)
			# Get size in pixels. Add rim twice.
			width = int(math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2)
			height = int(math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2)
			print "Width and height: " + str((width, height)) + "."
			# Get pixel spacing from settings.
			spacing = (1./self.programSettings['pxPerMm'].value,)*3
			# Prepare images.
			imageWhite = numpy.ones((height, width), numpy.uint8)
			imageWhite *= 255
			imageBlack = numpy.zeros((height, width), numpy.uint8)
			imageFill = self.createFillPattern(width, height)

			# Prepare vtk image and extruder stencils.
			image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(imageWhite))
			image.SetOrigin(positionMm[0], positionMm[1], 0)	# mm
			image.SetDimensions(width, height, 1)
			image.SetSpacing(spacing)
			if vtk.VTK_MAJOR_VERSION <= 5:
				image.AllocateScalars()
			else:
				image.AllocateScalars(vtk.VTK_UNSIGNED_CHAR, 1)

			# Set new position for extruder stencils.
			# Model.
			extruderStencilModel.SetOutputOrigin(positionMm)
			extruderStencilModel.SetOutputWholeExtent(image.GetExtent())
			extruderStencilModel.SetOutputSpacing(spacing)
			# Supports.
			extruderStencilSupports.SetOutputOrigin(positionMm)
			extruderStencilSupports.SetOutputWholeExtent(image.GetExtent())
			extruderStencilSupports.SetOutputSpacing(spacing)
			# Bottom plate.
			extruderStencilBottomPlate.SetOutputOrigin(positionMm)
			extruderStencilBottomPlate.SetOutputWholeExtent(image.GetExtent())
			extruderStencilBottomPlate.SetOutputSpacing(spacing)


			# Loop through slices.
			for sliceNumber in range(numberOfSlices):
				# Make breakable by new input or termination request.
				if not self.newInputInQueue() and not self.stopThread.isSet():
					# Sleep for a very short period to allow GUI thread some CPU usage.
					time.sleep(0.01)
					print "Slice " + str(sliceNumber) + "."
					# Start time measurement.
					if self.programSettings['debug'].value:
						interval = time.time()

					# Set new height for the cutting plane and extruders.
					if sliceNumber == 0:
						slicePosition = 0.001
					else:
						slicePosition = layerHeight*sliceNumber
					cuttingPlane.SetOrigin(0,0,slicePosition)
					extruderModel.SetVector(0,0,-slicePosition-1)
					extruderSupports.SetVector(0,0,-slicePosition-1)
					extruderBottomPlate.SetVector(0,0,-slicePosition-1)

					# Update the pipeline.
					stencilModel.Update()
					if self.programSettings['showVtkErrors'].value and errorObserver.ErrorOccurred():
						print "VTK Error: " + errorObserver.ErrorMessage()
					stencilSupports.Update()
					if self.programSettings['showVtkErrors'].value and errorObserver.ErrorOccurred():
						print "VTK Error: " + errorObserver.ErrorMessage()
					stencilBottomPlate.Update()
					if self.programSettings['showVtkErrors'].value and errorObserver.ErrorOccurred():
						print "VTK Error: " + errorObserver.ErrorMessage()

					# End and restart time measurement.
					if self.programSettings['debug'].value:
						interval = time.time() - interval
						print "Slice creation time: " + str(interval) + " s."
						interval = time.time()

					# Get pixel values from vtk image data and turn into numpy array.
					imageModel = numpy_support.vtk_to_numpy(stencilModel.GetOutput().GetPointData().GetScalars())
					imageSupports = numpy_support.vtk_to_numpy(stencilSupports.GetOutput().GetPointData().GetScalars())
					imageBottomPlate = numpy_support.vtk_to_numpy(stencilBottomPlate.GetOutput().GetPointData().GetScalars())
					# Now we have the pixel values in a long list. Transform them into a 2d array.
					imageModel = imageModel.reshape(1, height, width)
					imageModel = imageModel.transpose(1,2,0)
					imageSupports = imageSupports.reshape(1, height, width)
					imageSupports = imageSupports.transpose(1,2,0)
					imageBottomPlate = imageBottomPlate.reshape(1, height, width)
					imageBottomPlate = imageBottomPlate.transpose(1,2,0)
					# Remove 3rd dimension.
					imageModel = numpy.squeeze(imageModel)
					imageSupports = numpy.squeeze(imageSupports)
					imageBottomPlate = numpy.squeeze(imageBottomPlate)
					# Cast to uint8.
					imageModel = numpy.uint8(imageModel)
					imageSupports = numpy.uint8(imageSupports)
					imageBottomPlate = numpy.uint8(imageBottomPlate)

					# End and restart time measurement.
					if self.programSettings['debug'].value:
						interval = time.time() - interval
						print "Slice to image time: " + str(interval) + " s."
						interval = time.time()

					# Create fill pattern. #####################################
					# Get pixel values from 10 slices above and below.
					# We need to analyse these to be able to generate closed bottom and top surfaces.
					# Only use model slice data. Supports and bottom plate have no internal pattern anyway.
					# Check if we are in the first or last mm of the model, then there should not be a pattern anyways, so we set everything black.
					# Only do this whole thing if fillFlag is set and fill is shown or print is going.
					if self.settings['printHollow'].value == True:# and (self.programSettings['showFill'].value == True or self.printFlag == True):


						# Get wall thickness from settings.
						wallThickness = self.settings['fillShellWallThickness'].value	# [mm]
						wallThicknessPx = wallThickness * self.programSettings['pxPerMm'].value

						# Get top and bottom masks for wall thickness.
						# Only if we one wall thickness below top or above bottom.
						if bounds[5] > layerHeight*sliceNumber+wallThickness and bounds[4] < layerHeight*sliceNumber-wallThickness:

							# Set cutting plane + wall thickness for top mask.
							cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber+wallThickness)
							extruderModel.SetVector(0,0,-sliceNumber+wallThickness*layerHeight-1)
							stencilModel.Update()

							# Get mask image data as numpy array.
							imageTopMask = numpy_support.vtk_to_numpy(stencilModel.GetOutput().GetPointData().GetScalars())

							# Set cutting plate - wall thickness for bottom mask.
							cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber-wallThickness)
							extruderModel.SetVector(0,0,-sliceNumber+wallThickness*layerHeight-1)
							stencilModel.Update()

							# Get mask image data as numpy array.
							imageBottomMask = numpy_support.vtk_to_numpy(stencilModel.GetOutput().GetPointData().GetScalars())

							# Now we have the pixel values in a long list. Transform them into a 2d array.
							imageTopMask = imageTopMask.reshape(1, height, width)
							imageTopMask = imageTopMask.transpose(1,2,0)
							imageBottomMask = imageBottomMask.reshape(1, height, width)
							imageBottomMask = imageBottomMask.transpose(1,2,0)

							# Cast to uint8.
							imageTopMask = numpy.uint8(imageTopMask)
							imageBottomMask = numpy.uint8(imageBottomMask)

						# If cutting plane is inside top or bottom wall...
						else:
							# ... set masks black.
							imageTopMask = imageBlack
							imageBottomMask = imageBlack


						# Erode model image to create wall thickness.
						imageEroded = cv2.erode(imageModel, numpy.ones((wallThicknessPx,wallThicknessPx), numpy.uint8), iterations=1)

						# Multiply mask images with eroded image to prevent wall where mask images are black.
						imageEroded = cv2.multiply(imageEroded, imageTopMask)
						imageEroded = cv2.multiply(imageEroded, imageBottomMask)

						# Add internal pattern to wall. Write result to original slice image.
						if self.settings['fill'].value == True:

							# Shift internal pattern 1 pixel to prevent burning in the pdms coating.
							patternShift = 1	# TODO: implement setting for pattern shift.
							imageFill = numpy.roll(imageFill, patternShift, axis=0)
							imageFill = numpy.roll(imageFill, patternShift, axis=1)

							# Mask internal pattern using the eroded image.
							imageEroded = cv2.multiply(imageEroded, imageFill)

						# Subtract cavity with our without fill pattern from model.
						imageModel = cv2.subtract(imageModel, imageEroded)

						# End time measurement.
						if self.programSettings['debug'].value:
							interval = time.time() - interval
							print "Fill pattern time: " + str(interval) + "."

					# Combine model, supports and bottom plate images.
					imageModel = cv2.add(imageModel, imageSupports)
					imageModel = cv2.add(imageModel, imageBottomPlate)

					# Save image.
			#		im = Image.fromarray(self.imageModel)
			#		fileString = "sliceprint%03d.jpeg" % (sliceNumber,)
			#		im.save(fileString)

					# Write slice image to slice stack.
#test				self.sliceStack.append(self.imageModel)
					sliceStack.append(imageModel)			# test
				else:
					# If new stack is in queue, break. //return the current stack.
					if self.console:
						self.console.addLine("Restarting slicer.")
					break
					#return self.sliceStack
			return sliceStack



	def createFillPattern(self, width, height):
		if not self.stopThread.isSet():
			# Create an opencv image with rectangular pattern for filling large model areas.
			imageFill = numpy.ones((height, width), numpy.uint8) * 255

			# Set every Nth vertical line (and it's  neighbour or so) white.
			spacing = self.settings['fillSpacing'].value * self.programSettings['pxPerMm'].value
			wallThickness = self.settings['fillPatternWallThickness'].value * self.programSettings['pxPerMm'].value
			for pixelX in range(width):
				if (pixelX / spacing - math.floor(pixelX / spacing)) * spacing < wallThickness:
					imageFill[:,pixelX-1] = 0
			for pixelY in range(height):
				if (pixelY / spacing - math.floor(pixelY / spacing)) * spacing < wallThickness:
					imageFill[pixelY-1,:] = 0
			return imageFill




################################################################################
# Print process thread. ########################################################
################################################################################
