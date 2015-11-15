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

import vtk
from vtk.util import numpy_support	# Functions to convert between numpy and vtk
import math
import cv2
import numpy
import time
import random
import Image, ImageTk
import Queue, threading
#from matplotlib import pyplot as plot
import monkeyprintImageHandling as imageHandling

import monkeyprintSettings

class modelContainer:
	def __init__(self, filename, programSettings, console=None):
	
		# Internalise data.
		self.filename = filename
		self.console=console
		
		# Create settings object.
		self.settings = monkeyprintSettings.modelSettings()
		
		# Create model object.
		self.model = modelData(filename, self.settings, programSettings, self.console)
		
		# Active flag. Only do updates if model is active.
		self.flagActive = True
		
		# Update model and supports.
		self.updateModel()
		self.updateSupports()
		
		# Set inital visibilities.
		self.hideOverhang()
		self.hideSupports()
		self.hideBottomPlate()
		self.hideSlices()

		

	def getHeight(self):
		return self.model.getHeight()
	
	def setChanged(self):
		self.model.setChanged()
	
	def updateModel(self):
		self.model.updateModel()
		self.model.setChanged()
	
	def updateSupports(self):
		self.model.updateBottomPlate()
		self.model.updateSupports()
		self.model.setChanged()
	
	def updateSlice3d(self, sliceNumber):
		self.model.updateSlice3d(sliceNumber)
	
	def updateSliceStack(self):
		self.model.startBackgroundSlicer()
	
	def sliceThreadListener(self):
		self.model.setChanged()
		self.model.checkBackgroundSlicer()
	
	def getAllActors(self):
		return (	self.getActor(),
				self.getBoxActor(),
				self.getBoxTextActor(),
				self.getOverhangActor(),
				self.getBottomPlateActor(),
				self.getSupportsActor(),
				self.getSlicesActor()
				)
	
	def setActive(self, active):
		self.flagActive = active
	
	def isActive(self):
		return self.flagActive
	
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
	
	def getSlicesActor(self):
		return self.model.getActorSlices()

	def showBox(self):
		self.model.showBoundingBox()
		self.model.showBoundingBoxText()
		
	def hideBox(self):
		self.model.hideBoundingBox()
		self.model.hideBoundingBoxText()
	
	def showModel(self):
		pass
	
	def hideModel(self):
		pass
	
	def opaqueModel(self):
		self.model.opacity(1.0)
	
	def transparentModel(self):
		self.model.opacity(.5)
	
	def showOverhang(self):
		self.model.showActorOverhang()

	def hideOverhang(self):
		self.model.hideActorOverhang()
	
	def showBottomPlate(self):
		self.model.showActorBottomPlate()

	def hideBottomPlate(self):
		self.model.hideActorBottomPlate()
	
	def opaqueBottomPlate(self):
		self.model.setOpacityBottomPlate(1.0)
	
	def transparentBottomPlate(self):
		self.model.setOpacityBottomPlate(.5)
			
	def showSupports(self):
		self.model.showActorSupports()
	
	def hideSupports(self):
		self.model.hideActorSupports()
	
	def opaqueSupports(self):
		self.model.setOpacitySupports(1.0)
	
	def transparentSupports(self):
		self.model.setOpacitySupports(.5)
	
	def showSlices(self):
		self.model.showActorSlices()
	
	def hideSlices(self):
		self.model.hideActorSlices()
	

################################################################################
################################################################################
################################################################################

class modelCollection(dict):
	def __init__(self, programSettings, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise settings.
		self.programSettings = programSettings
		self.console = console
		# Create slice image.
		self.sliceImage = imageHandling.createImageGray(self.programSettings['Projector size X'].value, self.programSettings['Projector size Y'].value, 0)
		self.sliceImageBlack = numpy.empty_like(self.sliceImage)
		# Create current model id.
		self.currentModelId = ""
		# Load default model to fill settings for gui.
		self.add("default", "")	# Don't provide file name.
	
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
	def add(self, modelId, filename):
		self[modelId] = modelContainer(filename, self.programSettings, self.console)
		# Set new model as current model.
		self.currentModelId = modelId
	
	# Function to remove a model from the model collection
	def remove(self, modelId):
		if self[modelId]:
			self[modelId].model.killBackgroundSlicer()
			# Explicitly delete model data to free memory from slice images.
			del self[modelId].model
			del self[modelId]
	
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
		numberOfSlices = int(math.floor(height / self.programSettings['Layer height'].value))
		return numberOfSlices
	
	# Update the slice stack. Set it's height according to max model
	# height and layer height.
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
		self.sliceImage = imageHandling.createImageGray(self.programSettings['Projector size X'].value, self.programSettings['Projector size Y'].value, 0)
		# Get slice images from models.
		imgList = []
		for model in self:
	#		self[model].updateSlice3d(sliceNumber)
			if model != "default" and i<len(self[model].model.sliceStack):
				imgList.append((self[model].model.sliceStack[i], self[model].model.getSlicePosition()))
		# Add list of slice images to projector frame.
		for i in range(len(imgList)):
			self.sliceImage = imageHandling.imgAdd(self.sliceImage, imgList[i][0], imgList[i][1])
		return self.sliceImage
		

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
		return True


	



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
		# Set up variables.
		# Internalise settings.
		self.filenameStl = ""
		self.filename = filename
		self.flagActive = True
		self.settings = settings
		self.programSettings = programSettings
		self.console = console
		
		# Set up values for model positioning.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0
		
		self.flagChanged = False
		
		# Set up the slice stack. Has one slice only at first...
		self.sliceStack = sliceStack()
		self.slicePosition = (0,0)
	
		# Background thread for updating the slices on demand.
		self.queueSlicerIn = Queue.Queue()
		self.queueSlicerOut = Queue.Queue()
		if self.filename != "":
			# Initialise the thread.
			self.slicerThread = backgroundSlicer(self.settings, self.programSettings, self.queueSlicerIn, self.queueSlicerOut)
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
			# Get polydata from stl file.
			self.stlPolyData = vtk.vtkPolyData
			self.stlPolyData = self.stlReader.GetOutput()
			# Calculate normals.
			self.stlPolyDataNormals = vtk.vtkPolyDataNormals()
			self.stlPolyDataNormals.SetInput(self.stlPolyData)
			self.stlPolyDataNormals.SplittingOff()	# Don't split sharp edges using feature angle.
			self.stlPolyDataNormals.ComputePointNormalsOn()
			self.stlPolyDataNormals.ComputeCellNormalsOff()
		#	stlNormals.Update()
			# Move to origin filter. Input is stl polydata.
			self.stlCenterTransform = vtk.vtkTransform() # Empty transformation matrix.
			self.stlCenterFilter = vtk.vtkTransformFilter()
			self.stlCenterFilter.SetTransform(self.stlCenterTransform)
			self.stlCenterFilter.SetInput(self.stlPolyDataNormals.GetOutput())
			# Scale filter. Input is scale filter.
			self.stlScaleTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlScaleFilter = vtk.vtkTransformFilter()
			self.stlScaleFilter.SetTransform(self.stlScaleTransform)
			self.stlScaleFilter.SetInput(self.stlCenterFilter.GetOutput())	# Note: stlPolyData is a data object, hence no GetOutput() method is needed.
			# Rotate filter. Input is move filter.
			self.stlRotateTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlRotationFilter=vtk.vtkTransformPolyDataFilter()
			self.stlRotationFilter.SetTransform(self.stlRotateTransform)
			self.stlRotationFilter.SetInputConnection(self.stlScaleFilter.GetOutputPort())
			# Move to position filter. Input is rotate filter.
			self.stlPositionTransform = vtk.vtkTransform()	# Empty transformation matrix.
			self.stlPositionFilter = vtk.vtkTransformFilter()
			self.stlPositionFilter.SetTransform(self.stlPositionTransform)
			self.stlPositionFilter.SetInput(self.stlRotationFilter.GetOutput())
			# Create clipping filter. Use normals to clip stl.
			self.overhangClipFilter = vtk.vtkClipPolyData()
			self.overhangClipFilter.GenerateClipScalarsOff()
			self.overhangClipFilter.SetInsideOut(1)
			self.overhangClipFilter.GenerateClippedOutputOff()
			self.overhangClipFilter.SetInput(self.stlPositionFilter.GetOutput())
			# Define cell locator for intersections of support pattern and overhang model.
			self.locator = vtk.vtkCellLocator()
			self.locator.SetDataSet(self.overhangClipFilter.GetOutput())	#TODO: change to selected region input.
		
			# Create supports polydata.
			self.supports = vtk.vtkAppendPolyData()

			# Create bottom plate polydata. Edge length 1 mm, place outside of build volume by 1 mm.	
			self.bottomPlate = vtk.vtkCubeSource()
			self.bottomPlate.SetXLength(1)
			self.bottomPlate.SetYLength(1)
			self.bottomPlate.SetZLength(1)
			self.bottomPlate.SetCenter((-1, -1, -1))


			# The following is for 3D slice data. ################################
			# Create cutting plane, cutting filter and cut line polydata twice,
			# one for 3d display and one for slice image generation in background.
			self.extrusionVector = (0,0,-1)
			# Create cutting plane.
			self.cuttingPlane = vtk.vtkPlane()
			self.cuttingPlane.SetNormal(0,0,1)
			self.cuttingPlane.SetOrigin(0,0,0.001)	# Make sure bottom plate is cut properly.
			# Create cutting filter for model.
			self.cuttingFilterModel = vtk.vtkCutter()
			self.cuttingFilterModel.SetCutFunction(self.cuttingPlane)
			self.cuttingFilterModel.SetInput(self.stlPositionFilter.GetOutput())
			# Create cutting filter for supports.
			self.cuttingFilterSupports = vtk.vtkCutter()
			self.cuttingFilterSupports.SetCutFunction(self.cuttingPlane)
			self.cuttingFilterSupports.SetInput(self.supports.GetOutput())
			# Create cutting filter for bottom plate.
			self.cuttingFilterBottomPlate = vtk.vtkCutter()
			self.cuttingFilterBottomPlate.SetCutFunction(self.cuttingPlane)
			self.cuttingFilterBottomPlate.SetInput(self.bottomPlate.GetOutput())
			# Create polylines from cutter output for model.
			self.sectionStripperModel = vtk.vtkStripper()
			self.sectionStripperModel.SetInput(self.cuttingFilterModel.GetOutput())
			#TODO: remove scalars so color is white.
			#self.sectionStripperModel.GetOutput().GetPointData().RemoveArray('normalsZ')
			# Create polylines from cutter output for supports.
			self.sectionStripperSupports = vtk.vtkStripper()
			self.sectionStripperSupports.SetInput(self.cuttingFilterSupports.GetOutput())
			# Create polylines from cutter output for bottom plate.
			self.sectionStripperBottomPlate = vtk.vtkStripper()
			self.sectionStripperBottomPlate.SetInput(self.cuttingFilterBottomPlate.GetOutput())
			# Combine cut lines from model, supports and bottom plate. This is for display only.
			self.combinedCutlines = vtk.vtkAppendPolyData()
			self.combinedCutlines.AddInput(self.sectionStripperModel.GetOutput())
			self.combinedCutlines.AddInput(self.sectionStripperSupports.GetOutput())
			self.combinedCutlines.AddInput(self.sectionStripperBottomPlate.GetOutput())
			# Create a small cone to have at least one input
			# to the slice line vtkAppendPolyData in case no
			# model intersections were found.
			cone = vtk.vtkConeSource()
			cone.SetRadius(.01)
			cone.SetHeight(.01)
			cone.SetResolution(6)
			cone.SetCenter([-.1,-.1,-.1])
			self.combinedCutlines.AddInput(cone.GetOutput())
		
			# Bounding box. Create cube and set outline filter.
			self.modelBoundingBox = vtk.vtkCubeSource()
			self.modelBoundingBox.SetCenter(self.getCenter())
			self.modelBoundingBox.SetXLength(self.getSize()[0])
			self.modelBoundingBox.SetYLength(self.getSize()[1])
			self.modelBoundingBox.SetZLength(self.getSize()[2])
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
			self.supportsMapper.SetInputConnection(self.supports.GetOutput())
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
			self.modelVolume = vtk.vtkMassProperties()
			self.modelVolume.SetInput(self.stlPositionFilter.GetOutput())

		

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

			# Set up the initial model scaling, rotation and position. ###########
		#	self.updateModel()





	# #########################################################################
	# Public method definitions. ##############################################
	# #########################################################################

	# Change active flag.
	def setActive(self, active):
		self.flagActive = active
	
	# Check active flag.
	def isActive(self):
		return self.flagActive

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
		self.modelVolume.Update()
		return self.modelVolume.GetVolume()
	
	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)
		
	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)

	def getBoundsSafety(self):
		bounds = self.__getBounds(self.stlPositionFilter)
		dist = self.programSettings['Model safety distance'].value
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
		if self.filename != "" and self.isActive():
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
			self.stlRotateTransform.RotateWXYZ(self.settings['Rotation X'].value,1,0,0)
			self.stlRotateTransform.RotateWXYZ(self.settings['Rotation Y'].value,0,1,0)
			self.stlRotateTransform.RotateWXYZ(self.settings['Rotation Z'].value,0,0,1)
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
			if ((self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) / self.dimX) <= ((self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) / self.dimY) and ((self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) / self.dimX) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
				smallestRatio =  (self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) / self.dimX * currentScale
			elif ((self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) / self.dimY) <= ((self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) / self.dimX) and ((self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) / self.dimY) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
				smallestRatio =  (self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) / self.dimY * currentScale
			elif (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= ((self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) / self.dimX) and (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= ((self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) / self.dimY):
				smallestRatio =  self.programSettings['buildSizeXYZ'].value[2] / self.dimZ * currentScale
			# Restrict input scalingFactor if necessary.
			if smallestRatio < self.settings['Scaling'].value:
				self.settings['Scaling'].setValue(smallestRatio)
			
			# Scale. *******************
			# First, reset scale to 1.
			self.stlScaleTransform.Scale(1/self.stlScaleTransform.GetScale()[0], 1/self.stlScaleTransform.GetScale()[1], 1/self.stlScaleTransform.GetScale()[2])
			# Change scale value.
			self.stlScaleTransform.Scale(self.settings['Scaling'].value, self.settings['Scaling'].value, self.settings['Scaling'].value)
			self.stlScaleFilter.Update()	# Update to get new bounds.

			# Position. ****************
			# Subtract safety distance from build volume in X and Y directions. Z doesn't need safety space.
			clearRangeX = (self.programSettings['buildSizeXYZ'].value[0]-2*self.programSettings['Model safety distance'].value) - self.__getSize(self.stlRotationFilter)[0]
			clearRangeY = (self.programSettings['buildSizeXYZ'].value[1]-2*self.programSettings['Model safety distance'].value) - self.__getSize(self.stlRotationFilter)[1]
			positionZMax = self.programSettings['buildSizeXYZ'].value[2] - self.__getSize(self.stlRotationFilter)[2]
			if self.settings['Bottom clearance'].value > positionZMax:
				self.settings['Bottom clearance'].setValue(positionZMax)
			self.stlPositionTransform.Translate(  ((self.__getSize(self.stlRotationFilter)[0]/2 + clearRangeX * (self.settings['Position X'].value / 100.0)) - self.stlPositionTransform.GetPosition()[0]) + self.programSettings['Model safety distance'].value,      ((self.__getSize(self.stlRotationFilter)[1]/2 + clearRangeY * (self.settings['Position Y'].value / 100.0)) - self.stlPositionTransform.GetPosition()[1]) + self.programSettings['Model safety distance'].value,       self.__getSize(self.stlRotationFilter)[2]/2 - self.stlPositionTransform.GetPosition()[2] + self.settings['Bottom clearance'].value)
			self.stlPositionFilter.Update()

			# Recalculate normals.
			self.getNormalZComponent(self.stlPositionFilter.GetOutput())
		
			# Reposition bounding box.
			self.modelBoundingBox.SetCenter(self.getCenter())
			self.modelBoundingBox.SetXLength(self.getSize()[0])
			self.modelBoundingBox.SetYLength(self.getSize()[1])
			self.modelBoundingBox.SetZLength(self.getSize()[2])
			self.modelBoundingBoxTextActor.SetCaption("x: %6.2f mm\ny: %6.2f mm\nz: %6.2f mm\nVolume: %6.2f ml"	% (self.getSize()[0], self.getSize()[1], self.getSize()[2], self.getVolume()/1000.0) )
			self.modelBoundingBoxTextActor.SetAttachmentPoint(self.getBounds()[1], self.getBounds()[3], self.getBounds()[5])


	def updateBottomPlate(self):
		if self.filename != "" and self.isActive():
			modelBounds = self.getBounds()
			self.bottomPlate.SetXLength(modelBounds[1] - modelBounds[0])
			self.bottomPlate.SetYLength(modelBounds[3] - modelBounds[2])
			self.bottomPlate.SetZLength(self.settings['Bottom plate thickness'].value)
			self.bottomPlate.SetCenter( (modelBounds[0] + modelBounds[1]) / 2.0, (modelBounds[2] + modelBounds[3]) / 2.0, self.settings['Bottom plate thickness'].value/2.0)
			self.bottomPlate.Update()
		

	def updateOverhang(self):
		if self.filename != "" and self.isActive():
			# Calculate clipping threshold based on Z component..
			# Z normals are 1 if pointing upwards, -1 if downwards and 0 if pointing sideways.
			# Turn angle into value between -1 and 0.
			self.clipThreshold = -math.cos(self.settings['Overhang angle'].value/180.0*math.pi)
			self.overhangClipFilter.SetValue(self.clipThreshold)
			self.overhangClipFilter.Update()


	# Update supports. ########################################################
	def updateSupports(self):
		if self.filename != "" and self.isActive():
			# Update overhang.
			self.updateOverhang()
		
			# Clear all inputs from cones data.
			self.supports.RemoveAllInputs()
			
			# Create one super small cone to have at least one input
			# to the vtkAppendPolyData in case no model intersections
			# were found.
			cone = vtk.vtkConeSource()
			# Set cone dimensions.
			cone.SetRadius(.01)
			cone.SetHeight(.01)
			cone.SetResolution(6)
			cone.SetCenter([-.1,-.1,-.1])
			self.supports.AddInput(cone.GetOutput())
	
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
			nXMin = int(math.floor((center[0] - bounds[0]) / self.settings['Spacing X'].value))
			nXMax = int(math.floor((bounds[1] - center[0]) / self.settings['Spacing X'].value))
			nYMin = int(math.floor((center[1] - bounds[2]) / self.settings['Spacing Y'].value))
			nYMax = int(math.floor((bounds[3] - center[1]) / self.settings['Spacing Y'].value))	

		
			# Start location, first point of pattern.
			startX = center[0] - nXMin * self.settings['Spacing X'].value
			startY = center[1] - nYMin * self.settings['Spacing Y'].value

		
			# Number of points in X and Y.
			nX = nXMin + nXMax + 1	# +1 because of center support, nXMin and nXMax only give number of supports to each side of center.
			nY = nYMin + nYMax + 1	# +1 because of center support...
			i = 0
			# Loop through point grid and check for intersections.
			for iX in range(nX):
				for iY in range(nY):
					# Get X and Y values.
					pointX = startX + iX * self.settings['Spacing X'].value
					pointY = startY + iY * self.settings['Spacing Y'].value
				
					# Combine to bottom and top point.
					pointBottom = [pointX, pointY, 0]
					pointTop = [pointX, pointY, self.settings['Maximum height'].value]
				
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
						cone.SetRadius(self.settings['Base diameter'].value/2.0)
						cone.SetHeight(self.settings['Cone height'].value)
						cone.SetResolution(20)
						# Set cone position (at cone center) according to current point.
						pos[2] = pos[2]-self.settings['Cone height'].value/2.0
						# Adjust cone Z position to meet tip connection diameter.
						pos[2] = pos[2]+1.0*self.settings['Cone height'].value/(1.0*self.settings['Base diameter'].value/self.settings['Tip diameter'].value)
						cone.SetCenter(pos)
					
						# Rotate the cone tip upwards.
						coneRotation = vtk.vtkRotationFilter()
						coneRotation.SetInput(cone.GetOutput())
						coneRotation.SetAxisToY()
						coneRotation.SetCenter(pos)
						coneRotation.SetAngle(-90)
						coneRotation.SetNumberOfCopies(1)
						coneRotation.CopyInputOff()
					
						# Use a geometry filter to convert rotation filter output
						# from unstructuredGrid to polyData.
						coneGeomFilter = vtk.vtkGeometryFilter()
						coneGeomFilter.SetInput(coneRotation.GetOutput())
						coneGeomFilter.Update()
					
						# Create cylinder.
						cylinder = vtk.vtkCylinderSource()
						# Set cylinder dimensions.
						cylinder.SetRadius(self.settings['Base diameter'].value/2.0)
						cylinder.SetHeight(pos[2]-self.settings['Cone height'].value/2.0)
						cylinder.SetResolution(20)
					
						# Set cylinder position.
						# Adjust height to fit beneath corresponding cone.
						pos[2] = (pos[2]-self.settings['Cone height'].value/2.0)/2.0
						cylinder.SetCenter(pos)
		
						# Rotate the cone tip upwards.
						cylinderRotation = vtk.vtkRotationFilter()
						cylinderRotation.SetInput(cylinder.GetOutput())
						cylinderRotation.SetAxisToX()
						cylinderRotation.SetCenter(pos)
						cylinderRotation.SetAngle(-90)
						cylinderRotation.SetNumberOfCopies(1)
						cylinderRotation.CopyInputOff()
	
						# Use a geometry filter to convert rotation filter output
						# from unstructuredGrid to polyData.
						cylinderGeomFilter = vtk.vtkGeometryFilter()
						cylinderGeomFilter.SetInput(cylinderRotation.GetOutput())
						cylinderGeomFilter.Update()
		
						# Append the cone to the cones polydata.
						self.supports.AddInput(coneGeomFilter.GetOutput())
						# Delete the cone. Vtk delete() method does not work in python because of garbage collection.
						del cone
						# Append the cylinder to the cones polydata.
						self.supports.AddInput(cylinderGeomFilter.GetOutput())
						del cylinder
						i += 1
			print "Created " + str(i) + " supports."


	# Update slice actor.
	def updateSlice3d(self, sliceNumber):
		if self.filename != "" and self.isActive():
			# Update pipeline with slice position given by layer height and slice number.
			self.cuttingPlane.SetOrigin(0,0,self.programSettings['Layer height'].value*sliceNumber)
			self.combinedCutlines.Update()
	
	def startBackgroundSlicer(self):
		# Only update if this is not default flag and the 
		# model or supports have been changed before.
		if self.filename!="" and self.flagChanged==True and self.isActive():
			if self.console != None:
				self.console.addLine('Slicer started.')
			# Reset the slice stack.
			self.sliceStack.reset(self.getSliceSize()[0], self.getSliceSize()[1], self.getNumberOfSlices())
			# If there's nothing in the queue...
			if self.queueSlicerIn.empty():
				# ... write the model polydata to the queue.
				self.queueSlicerIn.put([self.stlPositionFilter.GetOutput(), self.supports.GetOutput(), self.bottomPlate.GetOutput()])
			self.flagChanged = False

	def checkBackgroundSlicer(self):
		# If a slice stack is in the output queue...
		if self.queueSlicerOut.qsize():
			# ... get it.
			if self.console != None:
				self.console.addLine('Slicer done.')
			self.sliceStack[:] = self.queueSlicerOut.get()
	
	def killBackgroundSlicer(self):
		self.slicerThread.stop()
		
	def getSizePxXY(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get layer height in mm.
		layerHeight = 	self.programSettings['Layer height'].value
		# Calc number of layers.
		numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
		# Get rim size in pixels.
		rim = int(self.programSettings['Model safety distance'].value * self.programSettings['pxPerMm'].value)
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
		rim = int(self.programSettings['Model safety distance'].value * self.programSettings['pxPerMm'].value)
		# Get size in pixels. Add rim twice.
		width = int(math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2)
		height = int(math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2)
		size = (width, height)
		return size
	
	def getNumberOfSlices(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get layer height in mm.
		layerHeight = 	self.programSettings['Layer height'].value
		# Calc number of layers.
		numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
		return numberOfSlices
	
	def getSlicePosition(self):
		# Get bounds.
		bounds = self.getBounds()
		# Get rim size in pixels.
		rim = int(self.programSettings['Model safety distance'].value * self.programSettings['pxPerMm'].value)
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
			print 'foo'
			# use projector width and height.
			self.width = self.programSettings['Projector size X'].value
			self.height = self.programSettings['Projector size Y'].value
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
		# Get layer height from settings.
		stackHeight = int(bounds[5] / self.programSettings['Layer height'].value)
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
	def __init__(self, settings, programSettings, queueSlicerIn, queueSlicerOut):
		# Internalise inputs.
#		self.slicingFunction = slicingFunction
		self.settings = settings
		self.programSettings = programSettings
		self.queueSlicerIn = queueSlicerIn
		self.queueSlicerOut = queueSlicerOut
		# Thread stop event.
		self.stopThread = threading.Event()
		# Call super class init function.
		super(backgroundSlicer, self).__init__()
		
		# Set up slice stack as list.
		self.sliceStack = []
		
		# Create the VTK pipeline.
		self.extrusionVector = (0,0,-1)
		# Create cutting plane.
		self.cuttingPlane = vtk.vtkPlane()
		self.cuttingPlane.SetNormal(0,0,1)
		self.cuttingPlane.SetOrigin(0,0,0.001)	# Make sure bottom plate is cut properly.
		# Create cutting filter for model.
		self.cuttingFilterModel = vtk.vtkCutter()
		self.cuttingFilterModel.SetCutFunction(self.cuttingPlane)
		# Create cutting filter for supports.
		self.cuttingFilterSupports = vtk.vtkCutter()
		self.cuttingFilterSupports.SetCutFunction(self.cuttingPlane)
		# Create cutting filter for bottom plate.
		self.cuttingFilterBottomPlate = vtk.vtkCutter()
		self.cuttingFilterBottomPlate.SetCutFunction(self.cuttingPlane)
		# Create polylines from cutter output for model.
		self.sectionStripperModel = vtk.vtkStripper()
		self.sectionStripperModel.SetInput(self.cuttingFilterModel.GetOutput())
		# Create polylines from cutter output for supports.
		self.sectionStripperSupports = vtk.vtkStripper()
		self.sectionStripperSupports.SetInput(self.cuttingFilterSupports.GetOutput())
		# Create polylines from cutter output for bottom plate.
		self.sectionStripperBottomPlate = vtk.vtkStripper()
		self.sectionStripperBottomPlate.SetInput(self.cuttingFilterBottomPlate.GetOutput())
		# Extrude cut polyline of model.
		self.extruderModel = vtk.vtkLinearExtrusionFilter()
		self.extruderModel.SetInput(self.sectionStripperModel.GetOutput())
		self.extruderModel.SetScaleFactor(1)
		self.extruderModel.CappingOn()
		self.extruderModel.SetExtrusionTypeToVectorExtrusion()
		self.extruderModel.SetVector(self.extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
		# Extrude cut polyline of supports.
		self.extruderSupports = vtk.vtkLinearExtrusionFilter()
		self.extruderSupports.SetInput(self.sectionStripperSupports.GetOutput())
		self.extruderSupports.SetScaleFactor(1)
		self.extruderSupports.CappingOn()
		self.extruderSupports.SetExtrusionTypeToVectorExtrusion()
		self.extruderSupports.SetVector(self.extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
		# Extrude cut polyline.
		self.extruderBottomPlate = vtk.vtkLinearExtrusionFilter()
		self.extruderBottomPlate.SetInput(self.sectionStripperBottomPlate.GetOutput())
		self.extruderBottomPlate.SetScaleFactor(1)
		self.extruderBottomPlate.CappingOn()
		self.extruderBottomPlate.SetExtrusionTypeToVectorExtrusion()
		self.extruderBottomPlate.SetVector(self.extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
		# Create single channel VTK image.
		self.image = vtk.vtkImageData()
		self.image.SetScalarTypeToUnsignedChar()
		self.image.SetNumberOfScalarComponents(1)
		# Create image stencil from extruded polyline for model.
		self.extruderStencilModel = vtk.vtkPolyDataToImageStencil()
		self.extruderStencilModel.SetTolerance(0)
		self.extruderStencilModel.SetInput(self.extruderModel.GetOutput())
		# Create image stencil from extruded polyline for supports.
		self.extruderStencilSupports = vtk.vtkPolyDataToImageStencil()
		self.extruderStencilSupports.SetTolerance(0)
		self.extruderStencilSupports.SetInput(self.extruderSupports.GetOutput())
		# Create image stencil from extruded polyline for bottom plate.
		self.extruderStencilBottomPlate = vtk.vtkPolyDataToImageStencil()
		self.extruderStencilBottomPlate.SetTolerance(0)
		self.extruderStencilBottomPlate.SetInput(self.extruderBottomPlate.GetOutput())
		# Cut white image with stencil.
		self.stencilModel = vtk.vtkImageStencil()
		self.stencilModel.SetInput(self.image)
		self.stencilModel.SetStencil(self.extruderStencilModel.GetOutput())
		self.stencilModel.ReverseStencilOff()
		self.stencilModel.SetBackgroundValue(0.0)
		# Cut white image with stencil.
		self.stencilSupports = vtk.vtkImageStencil()
		self.stencilSupports.SetInput(self.image)
		self.stencilSupports.SetStencil(self.extruderStencilSupports.GetOutput())
		self.stencilSupports.ReverseStencilOff()
		self.stencilSupports.SetBackgroundValue(0.0)
		# Cut white image with stencil.
		self.stencilBottomPlate = vtk.vtkImageStencil()
		self.stencilBottomPlate.SetInput(self.image)
		self.stencilBottomPlate.SetStencil(self.extruderStencilBottomPlate.GetOutput())
		self.stencilBottomPlate.ReverseStencilOff()
		self.stencilBottomPlate.SetBackgroundValue(0.0)

		
	# Overload the run method.
	# This will automatically run once the init function is done.	
	def run(self):
		print "Slicer thread initialised"
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
				self.sliceStack = self.updateSlices(inputModel)
			# If yes...
			else:
				# Break the loop, return to idle mode and restart from there.
				break
			# Write the model to the output queue.
			self.queueSlicerOut.put(self.sliceStack)
			break
		# Go back to idle mode.
		self.idle()
	
	def stop(self):
		print "Stopping slicer thread"
		self.stopThread.set()
	
	def join(self, timeout=None):
		print "Stopping slicer thread"
		self.stopThread.set()
		threading.Thread.join(self, timeout)
	
	
	# Update slice stack.
	def updateSlices(self, inputModel):
		if not self.stopThread.isSet():
			# Reset slice stack.
			self.sliceStack = []
			
			# Set inputs.
			self.cuttingFilterModel.SetInput(inputModel[0])
			self.cuttingFilterModel.Update()
			self.cuttingFilterSupports.SetInput(inputModel[1])
			self.cuttingFilterBottomPlate.SetInput(inputModel[2])
			
			# Calc slice stack parameters.
			# Get size of the model in mm.
			bounds = [0 for i in range(6)]
			inputModel[0].GetBounds(bounds)
			# Get layer height in mm.
			layerHeight = 	self.programSettings['Layer height'].value
			# Calc number of layers.
			numberOfSlices = int(math.ceil(bounds[5] / layerHeight))
			# Get rim size in pixels.
			rim = int(self.programSettings['Model safety distance'].value * self.programSettings['pxPerMm'].value)
			# Get position in pixels. Include rim.
			position = (int(bounds[0]*self.programSettings['pxPerMm'].value-rim), int(bounds[2]*self.programSettings['pxPerMm'].value-rim), 0)
			positionMm = (bounds[0]-rim/self.programSettings['pxPerMm'].value, bounds[2]-rim/self.programSettings['pxPerMm'].value, 0)
			# Get size in pixels. Add rim twice.
			width = int(math.ceil((bounds[1]-bounds[0]) * self.programSettings['pxPerMm'].value) + rim*2)
			height = int(math.ceil((bounds[3]-bounds[2]) * self.programSettings['pxPerMm'].value) + rim*2)
			# Get pixel spacing from settings.
			spacing = (1./self.programSettings['pxPerMm'].value,)*3
			# Prepare images.
			self.imageWhite = numpy.ones((height, width), numpy.uint8)
			self.imageWhite *= 255.
			self.imageBlack = numpy.zeros((height, width), numpy.uint8)
			self.imageFill = self.createFillPattern(width, height)

			# Prepare vtk image and extruder stencils.
			self.image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(self.imageWhite))
			self.image.SetOrigin(positionMm[0], positionMm[1], 0)	# mm
			self.image.SetDimensions(width, height, 1)
			self.image.SetSpacing(spacing)
			self.image.AllocateScalars()
			
			# Set new position for extruder stencils.
			# Model.
			self.extruderStencilModel.SetOutputOrigin(positionMm)
			self.extruderStencilModel.SetOutputWholeExtent(self.image.GetExtent())
			self.extruderStencilModel.SetOutputSpacing(spacing)
			# Supports.
			self.extruderStencilSupports.SetOutputOrigin(positionMm)
			self.extruderStencilSupports.SetOutputWholeExtent(self.image.GetExtent())
			self.extruderStencilSupports.SetOutputSpacing(spacing)
			# Bottom plate.
			self.extruderStencilBottomPlate.SetOutputOrigin(positionMm)
			self.extruderStencilBottomPlate.SetOutputWholeExtent(self.image.GetExtent())
			self.extruderStencilBottomPlate.SetOutputSpacing(spacing)
			

			# Loop through slices.
			for sliceNumber in range(numberOfSlices):
				# Sleep for a very short period to allow GUI thread some CPU usage.
				time.sleep(0.01)
				# Set new height for the cutting plane and extruders.
				if sliceNumber == 0:
					slicePosition = 0.001
				else:
					slicePosition = layerHeight*sliceNumber
				self.cuttingPlane.SetOrigin(0,0,slicePosition)
				self.extruderModel.SetVector(0,0,-slicePosition-1)
				self.extruderSupports.SetVector(0,0,-slicePosition-1)
				self.extruderBottomPlate.SetVector(0,0,-slicePosition-1)
			
				# Update the pipeline.
				self.stencilModel.Update()
				self.stencilSupports.Update()
				self.stencilBottomPlate.Update()
		
				# Get pixel values from vtk image data and turn into numpy array.
				self.imageModel = numpy_support.vtk_to_numpy(self.stencilModel.GetOutput().GetPointData().GetScalars())
				self.imageSupports = numpy_support.vtk_to_numpy(self.stencilSupports.GetOutput().GetPointData().GetScalars())
				self.imageBottomPlate = numpy_support.vtk_to_numpy(self.stencilBottomPlate.GetOutput().GetPointData().GetScalars())
				# Now we have the pixel values in a long list. Transform them into a 2d array.
				self.imageModel = self.imageModel.reshape(1, height, width)
				self.imageModel = self.imageModel.transpose(1,2,0)
				self.imageSupports = self.imageSupports.reshape(1, height, width)
				self.imageSupports = self.imageSupports.transpose(1,2,0)
				self.imageBottomPlate = self.imageBottomPlate.reshape(1, height, width)
				self.imageBottomPlate = self.imageBottomPlate.transpose(1,2,0)
				# Remove 3rd dimension.
				self.imageModel = numpy.squeeze(self.imageModel)
				self.imageSupports = numpy.squeeze(self.imageSupports)
				self.imageBottomPlate = numpy.squeeze(self.imageBottomPlate)
				# Cast to uint8.
				self.imageModel = numpy.uint8(self.imageModel)
				self.imageSupports = numpy.uint8(self.imageSupports)
				self.imageBottomPlate = numpy.uint8(self.imageBottomPlate)

				# Create fill pattern. #####################################
				# Get pixel values from 10 slices above and below.
				# We need to analyse these to be able to generate closed bottom and top surfaces.
				# Only use model slice data. Supports and bottom plate have no internal pattern anyway.
				# Check if we are in the first or last mm of the model, then there should not be a pattern anyways, so we set everything black.
				# Only do this whole thing if fillFlag is set and fill is shown or print is going.
				if self.settings['Print hollow'].value == True:# and (self.programSettings['Show fill'].value == True or self.printFlag == True):
					
					# Get wall thickness from settings.
					wallThickness = self.settings['Shell wall thickness'].value	# [mm]
					wallThicknessPx = wallThickness * self.programSettings['pxPerMm'].value
					
					# Get top and bottom masks for wall thickness.
					# Only if we one wall thickness below top or above bottom.
					if bounds[5] > layerHeight*sliceNumber+wallThickness and bounds[4] < layerHeight*sliceNumber-wallThickness:	
						
						# Set cutting plane + wall thickness for top mask.
						self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber+wallThickness)
						self.extruderModel.SetVector(0,0,-sliceNumber+wallThickness*layerHeight-1)
						self.stencilModel.Update()
				
						# Get mask image data as numpy array.
						self.imageTopMask = numpy_support.vtk_to_numpy(self.stencilModel.GetOutput().GetPointData().GetScalars())
				
						# Set cutting plate - wall thickness for bottom mask.
						self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber-wallThickness)
						self.extruderModel.SetVector(0,0,-sliceNumber+wallThickness*layerHeight-1)
						self.stencilModel.Update()
				
						# Get mask image data as numpy array.
						self.imageBottomMask = numpy_support.vtk_to_numpy(self.stencilModel.GetOutput().GetPointData().GetScalars())
						
						# Now we have the pixel values in a long list. Transform them into a 2d array.
						self.imageTopMask = self.imageTopMask.reshape(1, height, width)
						self.imageTopMask = self.imageTopMask.transpose(1,2,0)
						self.imageBottomMask = self.imageBottomMask.reshape(1, height, width)
						self.imageBottomMask = self.imageBottomMask.transpose(1,2,0)
						
						# Cast to uint8.
						self.imageTopMask = numpy.uint8(self.imageTopMask)
						self.imageBottomMask = numpy.uint8(self.imageBottomMask)
					
					# If cutting plane is inside top or bottom wall...
					else:
						# ... set masks black.
						self.imageTopMask = self.imageBlack
						self.imageBottomMask = self.imageBlack
	

					# Erode model image to create wall thickness.
					self.imageEroded = cv2.erode(self.imageModel, numpy.ones((wallThicknessPx,wallThicknessPx), numpy.uint8), iterations=1)
		
					# Multiply mask images with eroded image to prevent wall where mask images are black.
					self.imageEroded = cv2.multiply(self.imageEroded, self.imageTopMask)
					self.imageEroded = cv2.multiply(self.imageEroded, self.imageBottomMask)
		
					# Subtract eroded image from original slice image to create the wall.
					self.imageWall = self.imageModel
					self.imageWall = cv2.subtract(self.imageModel, self.imageEroded)
			
					
					# Add internal pattern to wall. Write result to original slice image.
					if self.settings['Fill'].value == True:
					
						# Shift internal pattern 1 pixel to prevent burning in the pdms coating.
						patternShift = 1	# TODO: implement setting for pattern shift.
						self.imageFill = numpy.roll(self.imageFill, patternShift, axis=0)
						self.imageFill = numpy.roll(self.imageFill, patternShift, axis=1)
			
						# Cut out internal pattern using the eroded image.
						# Don't write to image pattern as we need it later.
						self.imageEroded = cv2.multiply(self.imageEroded, self.imageFill)
						# Set image.
						self.imageModel = cv2.add(self.imageWall, self.imageEroded)
					else:
						self.imageModel = self.imageWall
					
				# Combine model, supports and bottom plate images.
				self.imageModel = cv2.add(self.imageModel, self.imageSupports)
				self.imageModel = cv2.add(self.imageModel, self.imageBottomPlate)
				
				# Write slice image to slice stack.
				self.sliceStack.append(self.imageModel)
			return self.sliceStack
		
		
		
	def createFillPattern(self, width, height):
		if not self.stopThread.isSet():
			# Create an opencv image with rectangular pattern for filling large model areas.
			imageFill = numpy.zeros((height, width), numpy.uint8)
	
			# Set every Nth vertical line (and it's  neighbour or so) white.
			spacing = self.settings['Fill spacing'].value * self.programSettings['pxPerMm'].value
			wallThickness = self.settings['Fill wall thickness'].value * self.programSettings['pxPerMm'].value
			for pixelX in range(width):
				if (pixelX / spacing - math.floor(pixelX / spacing)) * spacing < wallThickness:
					imageFill[:,pixelX-1] = 255
			for pixelY in range(height):
				if (pixelY / spacing - math.floor(pixelY / spacing)) * spacing < wallThickness:
					imageFill[pixelY-1,:] = 255		
			return imageFill
			



