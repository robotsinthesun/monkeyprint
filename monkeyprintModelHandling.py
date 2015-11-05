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
import random
import Image, ImageTk

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
		
		# Set inital visibilities.
		self.hideOverhang()
		self.hideSupports()
		self.hideBottomPlate()
		self.hideSlices()

	def getHeight(self):
		return self.model.getHeight()
	
	def updateModel(self):
		self.model.updateModel()
	
	def updateSupports(self):
		self.model.updateBottomPlate()
		self.model.updateSupports()
	
	def updateSlices(self):
		pass
	
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
		# Create the image stack.
		self.sliceStack = sliceStack(self.programSettings)
		# Create current model id.
		self.currentModelId = ""
		# Load default model to fill settings for gui.
		self.add("default", "")	# Don't provide file name.
	
	# Function to retrieve id of the current model.
	def getCurrentModelId(self):
		return self.currentModelId
	
	# Function to retrieve current model.
	def getCurrentModel(self):
#		print "Returning model " + self.currentModelId + "."
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
		# Update slice stack height.
		self.updateSliceStack()
	
	# Function to remove a model from the model collection
	def remove(self, modelId):
		if self[modelId]:
			del self[modelId]
	
	# Function to retrieve the highest model. This dictates the slice stack height.
	def getMaxHeight(self):
		height = 0
		# Loop through all models.
		for model in self:
			# If model higher than current height value...
			if height < self[model].getHeight():
				# ... set new height value.
				height = self[model].getHeight()
		if self.console != None:
			self.console.addLine('Maximum model height: ' + str(height) + ' mm.')
		return height
	
	# Update the slice stack. Set it's height according to max model
	# height and layer height.
	def updateSliceStack(self):
		numberOfSlices = int(math.floor(self.getMaxHeight() / self.programSettings['Layer height'].value))
		self.console.addLine('Slice stack updated to ' + str(numberOfSlices) + ' slices.')
		self.sliceStack.update(numberOfSlices)
		
		
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
	
	def updateAllSupports(self):
		for model in self:
			# TODO: test if model is enabled.
			self[model].updateSupports()
	
	def updateAllSlices(self):
		for model in self:
			# TODO: test if model is enabled.
			self[model].updateSlices()
	
	
	



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
		# General.
		self.filenameStl = ""
		self.filename = filename
		self.flagActive = True
		self.settings = settings
		self.programSettings = programSettings
		self.console = console
		# For model positioning.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0
		# For slicing.
#TODO		self.printFlag = printFlag
		self.extrusionVector = (0,0,-1)
		
		
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
			# Set cone dimensions.
			cone.SetRadius(.01)
			cone.SetHeight(.01)
			cone.SetResolution(6)
			cone.SetCenter([-.1,-.1,-.1])
			self.combinedCutlines.AddInput(cone.GetOutput())
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
			# Create images for slice processing (hollowing, fill pattern).
			# Create a numpy array to set the vtkImageData scalars. That's much faster than looping through the points.
			# Make single channel image first as numpy_to_vtk only takes one channel.
			self.cvImage = numpy.ones((self.programSettings['Projector size Y'].value, self.programSettings['Projector size X'].value), numpy.uint8)
			self.cvImage *= 255.
			# Create black image.
			self.cvImageBlack = numpy.zeros((self.programSettings['Projector size Y'].value, self.programSettings['Projector size X'].value), numpy.uint8)
			# Create VTK image.
			self.image = vtk.vtkImageData()
			self.image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(self.cvImage))
			self.image.SetDimensions(programSettings['Projector size X'].value, programSettings['Projector size Y'].value,1)
			self.image.SetSpacing(0.1,0.1,0.1)
			self.image.SetExtent(0, programSettings['Projector size X'].value-1,0, programSettings['Projector size Y'].value-1,0,0)
			self.image.SetScalarTypeToUnsignedChar()
			self.image.SetNumberOfScalarComponents(1)
			self.image.AllocateScalars()
# TODO: What's the best order to do the image allocation?
			# Create an opencv image with rectangular pattern for filling large model areas.
			# Only, if object is created for printing. Otherwise this is a little slow...
			self.cvImagePattern = self.updateFillPattern()
			# Copy to use as base for eroded image and wall image later.
			self.imageArrayNumpyEroded = self.cvImagePattern
			self.imageArrayNumpyWall = self.cvImagePattern
			self.imageArrayNumpy = self.cvImageBlack
			# Create image stencil from extruded polyline for model.
			self.extruderStencilModel = vtk.vtkPolyDataToImageStencil()
			self.extruderStencilModel.SetTolerance(0)
			self.extruderStencilModel.SetInput(self.extruderModel.GetOutput())
			self.extruderStencilModel.SetOutputOrigin((0,0,0))
			self.extruderStencilModel.SetOutputSpacing((0.1,0.1,0.1))
			self.extruderStencilModel.SetOutputWholeExtent(self.image.GetExtent())
			# Create image stencil from extruded polyline for supports.
			self.extruderStencilSupports = vtk.vtkPolyDataToImageStencil()
			self.extruderStencilSupports.SetTolerance(0)
			self.extruderStencilSupports.SetInput(self.extruderSupports.GetOutput())
			self.extruderStencilSupports.SetOutputOrigin((0,0,0))
			self.extruderStencilSupports.SetOutputSpacing((0.1,0.1,0.1))
			self.extruderStencilSupports.SetOutputWholeExtent(self.image.GetExtent())
			# Create image stencil from extruded polyline for bottom plate.
			self.extruderStencilBottomPlate = vtk.vtkPolyDataToImageStencil()
			self.extruderStencilBottomPlate.SetTolerance(0)
			self.extruderStencilBottomPlate.SetInput(self.extruderBottomPlate.GetOutput())
			self.extruderStencilBottomPlate.SetOutputOrigin((0,0,0))
			self.extruderStencilBottomPlate.SetOutputSpacing((0.1,0.1,0.1))
			self.extruderStencilBottomPlate.SetOutputWholeExtent(self.image.GetExtent())
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
			# Add up model and supports images.
			self.combinedSliceImageModelSupports = vtk.vtkImageMathematics()
			self.combinedSliceImageModelSupports.SetInput1(self.stencilModel.GetOutput())
			self.combinedSliceImageModelSupports.SetInput2(self.stencilSupports.GetOutput())
			self.combinedSliceImageModelSupports.SetOperationToAdd()
			# Add model/supports and bottom plate images.
			self.combinedSliceImageModelSupportsBottomPlate = vtk.vtkImageMathematics()
			self.combinedSliceImageModelSupportsBottomPlate.SetInput1(self.combinedSliceImageModelSupports.GetOutput())
			self.combinedSliceImageModelSupportsBottomPlate.SetInput2(self.stencilBottomPlate.GetOutput())
			self.combinedSliceImageModelSupportsBottomPlate.SetOperationToAdd()

		
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
			self.updateModel()





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
	'''
	# Load a model of given filename.
	def loadInputFile(self, filename, settings):	# Import 

		# Set filename.
#		self.filenameStl = filename
		# Load model.
#		self.stlReader.SetFileName(filename)#settings.getFilename())#self.filenameStl)
		self.stlPositionFilter.Update()
		# If there are no points in 'vtkPolyData' something went wrong
		if self.stlPolyData.GetNumberOfPoints() == 0:
			print "No points found in stl file."
		else:
			print 'Model loaded successfully.'
			print '   ' + str(self.stlPolyData.GetNumberOfPoints()) + " points loaded."
			print '   ' + str(self.stlPolyData.GetNumberOfPolys()) + " polygons loaded."

		# Set up the initial model scaling, rotation and position. ###########
		# Now, all we need to do is to set up the transformation matrices.
		# Fortunately, we have a method for this. Inputs: scaling, rotX [°], rotY [°], rotZ [°], posXRel [%], posYRel [%], posZ [mm].
#		self.setTransform(modelSettings.[0], modelSettings.[1], modelSettings.[2], modelSettings.[3], modelSettings.[4], modelSettings.[5], modelSettings.[6])
		self.update(settings)
	'''
	def getSize(self):
		return self.__getSize(self.stlPositionFilter)
	
	def getVolume(self):
		self.modelVolume.Update()
		return self.modelVolume.GetVolume()
	
	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)
		
	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)
	
	def getBoundsOverhang(self):
		return self.__getBounds(self.overhangClipFilter)
		
	def getFilename(self):
		return self.filename
	
	
	def getPolydata(self):
		return self.stlPositionFilter.GetOutput()

	###########################################################################
	# Update methods. #########################################################
	###########################################################################
	#TODO: use internal settings object.
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
			# Compare the ratio of model size to build volume size in all dimensions with each other.
			# Return smallest ratio as maximum scaling.
			smallestRatio = 1
			if (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) <= (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) and (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
				smallestRatio =  self.programSettings['buildSizeXYZ'].value[0] / self.dimX * currentScale
			elif (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) <= (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) and (self.programSettings['buildSizeXYZ'].value[1] / self.dimY) <= (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ):
				smallestRatio =  self.programSettings['buildSizeXYZ'].value[1] / self.dimY * currentScale
			elif (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= (self.programSettings['buildSizeXYZ'].value[0] / self.dimX) and (self.programSettings['buildSizeXYZ'].value[2] / self.dimZ) <= (self.programSettings['buildSizeXYZ'].value[1] / self.dimY):
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
			clearRangeX = self.programSettings['buildSizeXYZ'].value[0] - self.__getSize(self.stlRotationFilter)[0]
			clearRangeY = self.programSettings['buildSizeXYZ'].value[1] - self.__getSize(self.stlRotationFilter)[1]
			positionZMax = self.programSettings['buildSizeXYZ'].value[2] - self.__getSize(self.stlRotationFilter)[2]
			if self.settings['Bottom clearance'].value > positionZMax:
				self.settings['Bottom clearance'].setValue(positionZMax)
			self.stlPositionTransform.Translate(  (self.__getSize(self.stlRotationFilter)[0]/2 + clearRangeX * (self.settings['Position X'].value / 100.0)) - self.stlPositionTransform.GetPosition()[0],      (self.__getSize(self.stlRotationFilter)[1]/2 + clearRangeY * (self.settings['Position Y'].value / 100.0)) - self.stlPositionTransform.GetPosition()[1],       self.__getSize(self.stlRotationFilter)[2]/2 - self.stlPositionTransform.GetPosition()[2] + self.settings['Bottom clearance'].value)
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
		
	
	#TODO: update doesn't work right after instantiation			
	def updateOverhang(self):#, overhangAngle):
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

	# Update slices. ##########################################################
	def updateFillPattern(self):
		# Create an opencv image with rectangular pattern for filling large model areas.
		self.cvImagePattern = numpy.zeros((self.programSettings['Projector size Y'].value, self.programSettings['Projector size X'].value), numpy.uint8)

		# Limit operation to within model bounds.
		roi = [	self.getBounds()[0], self.getBounds()[1],
				self.getBounds()[2], self.getBounds()[3]	]

		# Limit fill pattern spacing.
#		if self.settings.getFillSpacing() < 1.0:		# TODO: get min and max values from settings dict
#			self.settings.setFillSpacing(1.0)
#		elif self.settings.getFillSpacing() > 10.0:
#			self.settings.setFillSpacing(10.0)
#		
#		# Limit fill wall thickness.
#		if self.settings.getFillWallThickness() < 0.1:		# TODO: get min and max values from settings dict
#			self.settings.setFillWallThickness(0.1)
#		elif self.settings.getFillWallThickness() > 0.5:
#			self.settings.setFillWallThickness(0.5)		

		# TODO use ROI.
		# Set every Nth vertical line (and it's  neighbour or so) white.
		spacing = self.settings['Fill spacing'].value * self.programSettings['pxPerMm'].value
		wallThickness = self.settings['Fill wall thickness'].value * self.programSettings['pxPerMm'].value
		for pixelX in range(self.programSettings['Projector size X'].value):
			if (pixelX / spacing - math.floor(pixelX / spacing)) * spacing < wallThickness:		# TODO: set spacing values from settings dict.
				self.cvImagePattern[:,pixelX-1] = 255
		# Set every 15th horizontal line (and it's  neighbour or so) white.
		for pixelY in range(self.programSettings['Projector size Y'].value):
			if (pixelY / spacing - math.floor(pixelY / spacing)) * spacing < wallThickness:		# TODO: set spacing values from settings dict.
				self.cvImagePattern[pixelY-1,:] = 255
		
		# Reshape...
		self.cvImagePattern = self.cvImagePattern.reshape(1, self.programSettings['Projector size Y'].value, self.programSettings['Projector size X'].value)
		self.cvImagePattern = self.cvImagePattern.transpose(1,2,0)
		
		# Expand to 3 channels per pixel.	
		self.cvImagePattern = numpy.repeat(self.cvImagePattern, 3, axis = 2)	
		
		return self.cvImagePattern
	
	# Update slice image.
	def updateSlice(self, layerHeight, sliceNumber):
		if self.filename != "" and self.isActive():
						
			print "UPDATING SLICE " + str(sliceNumber) + "."
			self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber)
			self.extruderModel.SetVector(0,0,-sliceNumber*layerHeight-1)
			self.extruderSupports.SetVector(0,0,-sliceNumber*layerHeight-1)
			self.extruderBottomPlate.SetVector(0,0,-sliceNumber*layerHeight-1)
			self.combinedSliceImageModelSupportsBottomPlate.Update()
		
#			# Limit shell thickness.
#			if self.settings.getShellThickness() < 1.0:		# TODO: get min and max values from settings dict
#				self.settings.setShellThickness(1.0)
#			elif self.settings.getShellThickness() > 5.0:
#				self.settings.setShellThickness(5.0)	
		
			# Get pixel values from vtk image data. #########################
			self.imageArray = self.combinedSliceImageModelSupportsBottomPlate.GetOutput().GetPointData().GetScalars()

			# Get numpy array from vtk image data.
			self.imageArrayNumpy = numpy_support.vtk_to_numpy(self.imageArray)

			# Get dimensions from vtk image data.
			dims = self.combinedSliceImageModelSupportsBottomPlate.GetOutput().GetDimensions()

			# Reshape the numpy array according to image dimensions.
			self.imageArrayNumpy = self.imageArrayNumpy.reshape(dims[2], dims[1], dims[0])
			self.imageArrayNumpy = self.imageArrayNumpy.transpose(1,2,0)
		
			# Cast to uint8.
			self.imageArrayNumpy = numpy.uint8(self.imageArrayNumpy)

			# Repeat in 3d dimension to get an rgb image.
			self.imageArrayNumpy = numpy.repeat(self.imageArrayNumpy, 3, axis = 2)
		
# TODO: is it better to update fill with ROI or to use old full image pattern and shift it?		
			# Update fill pattern image.
#			self.cvImagePattern = self.updateFillPattern()
				
			# Get pixel values from 10 slices above and below. ##################
			# We need to analyse these to be able to generate closed bottom and top surfaces.
			# Only use model slice data. Supports and bottom plate have no internal pattern anyway.
			# Check if we are in the first or last mm of the model, then there should not be a pattern anyways, so we set everything black.
			# Only do this whole thing if fillFlag is set and fill is shown or print is going.
			if self.settings['Print hollow'].value == True and (self.programSettings['Show fill'].value == True or self.printFlag == True):
				wallThicknessTopBottom = self.settings['Shell wall thickness'].value	# [mm]
# TODO: why not get layer height from settings?
				if self.inputModelPolydata.GetBounds()[5] > layerHeight*sliceNumber+wallThicknessTopBottom and self.inputModelPolydata.GetBounds()[4] < layerHeight*sliceNumber-wallThicknessTopBottom:
					# Set cutting plate + wall thickness.
					self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber+wallThicknessTopBottom)
					self.extruderModel.SetVector(0,0,-sliceNumber+wallThicknessTopBottom*layerHeight-1)
					self.stencilModel.Update()
			
					# Get data.	
					self.imageArrayTopMask = self.stencilModel.GetOutput().GetPointData().GetScalars()
			
					# Set cutting plate - wall thickness.
					self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber-wallThicknessTopBottom)
					self.extruderModel.SetVector(0,0,-sliceNumber+wallThicknessTopBottom*layerHeight-1)
					self.stencilModel.Update()
			
					# Get data.
					self.imageArrayBottomMask = self.stencilModel.GetOutput().GetPointData().GetScalars()
			
					# Get numpy array from vtk image data.
					self.imageArrayTopMaskNumpy = numpy_support.vtk_to_numpy(self.imageArrayTopMask)
					self.imageArrayBottomMaskNumpy = numpy_support.vtk_to_numpy(self.imageArrayBottomMask)
				else:
					self.imageArrayTopMaskNumpy = self.cvImageBlack
					self.imageArrayBottomMaskNumpy = self.cvImageBlack
		
		
				# Get dimensions from vtk image data.
				dims = self.stencilModel.GetOutput().GetDimensions()

				# Reshape the numpy array according to image dimensions.
				self.imageArrayTopMaskNumpy = self.imageArrayTopMaskNumpy.reshape(dims[2], dims[1], dims[0])
				self.imageArrayBottomMaskNumpy = self.imageArrayBottomMaskNumpy.reshape(dims[2], dims[1], dims[0])
				self.imageArrayTopMaskNumpy = self.imageArrayTopMaskNumpy.transpose(1,2,0)
				self.imageArrayBottomMaskNumpy = self.imageArrayBottomMaskNumpy.transpose(1,2,0)
	
				# Cast to uint8.
				self.imageArrayTopMaskNumpy = numpy.uint8(self.imageArrayTopMaskNumpy)
				self.imageArrayBottomMaskNumpy = numpy.uint8(self.imageArrayBottomMaskNumpy)

				# Repeat in 3d dimension to get an rgb image.
				self.imageArrayTopMaskNumpy = numpy.repeat(self.imageArrayTopMaskNumpy, 3, axis = 2)
				self.imageArrayBottomMaskNumpy = numpy.repeat(self.imageArrayBottomMaskNumpy, 3, axis = 2)		

		
				# Combine current slice with internal structure pattern. ################
				# Erode slice image to create wall thickness.
				wallThickness = self.settings['Shell wall thickness'].value	* self.programSettings['pxPerMm'].value	# [px]
				self.imageArrayNumpyEroded = cv2.erode(self.imageArrayNumpy, numpy.ones((wallThickness,wallThickness), numpy.uint8), iterations=1)
	
				# Multiply mask images with eroded image to prevent wall where mask images are black.
				self.imageArrayNumpyEroded = cv2.multiply(self.imageArrayNumpyEroded, self.imageArrayTopMaskNumpy)
				self.imageArrayNumpyEroded = cv2.multiply(self.imageArrayNumpyEroded, self.imageArrayBottomMaskNumpy)
	
				# Subtract eroded image from original slice image to create the wall.
				self.imageArrayNumpyWall = self.imageArrayNumpy
				self.imageArrayNumpyWall = cv2.subtract(self.imageArrayNumpy, self.imageArrayNumpyEroded)
		
				# Shift internal pattern 1 pixel to prevent burning in the pdms coating.
				patternShift = 1
				self.cvImagePattern = numpy.roll(self.cvImagePattern, patternShift, axis=0)
				self.cvImagePattern = numpy.roll(self.cvImagePattern, patternShift, axis=1)
		
				# Cut out internal pattern using the eroded image.
				self.imageArrayNumpyEroded = cv2.multiply(self.imageArrayNumpyEroded, self.cvImagePattern)
		
				# Add internal pattern to wall. Write result to original slice image.
#				self.imageArrayNumpyWall = cv2.add(self.imageArrayNumpyWall, self.imageArrayNumpyEroded)
				if self.settings.getFill():
					self.imageArrayNumpy = cv2.add(self.imageArrayNumpyWall, self.imageArrayNumpyEroded)
				else:
					self.imageArrayNumpy = self.imageArrayNumpyWall

# TODO is this needed any more?	
	def pointsEqual(self, pointA, pointB, tolerance):
		return (abs(pointA[0] - pointB[0]) < tolerance and abs(pointA[1] - pointB[1]) < tolerance)
		
	# Get number if slices for the layer slider in the gui.
	def getNumberOfSlices(self):
		return int(math.floor(self.inputModelPolydata.GetBounds()[5] / self.settings.getLayerHeight()))
	
	# Get slice image for gui and print.
	def getCvImage(self):
		return self.imageArrayNumpy		


#	def getPolydataBottomPlate(self):
#		return self.bottomPlate.GetOutput()
	
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
					
#	def getPolydataOverhang(self):
#		return self.overhangClipFilter.GetOutput()
		
	
#	def getPolydataBottomPlate(self):
#		return self.bottomPlate.GetOutput()
	
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
		
#	def getPolydataSupports(self):
#		return self.supports.GetOutput()
	
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
class sliceStack():
	def __init__(self, programSettings):
		# Internalise settings.
		self.programSettings = programSettings
		# Create noisy images.
		self.numberOfNoisyImages = 10
		self.imagesNoisy = [self.createImageNoisy()]
		for i in range(1,self.numberOfNoisyImages):
			self.imagesNoisy.append(self.createImageNoisy())
		# Create black dummy image.
		# TODO: convert whole workflow to single channel 8 bit.
		self.imageBlack = numpy.zeros((self.programSettings['Projector size X'].value, self.programSettings['Projector size Y'].value, 3), numpy.uint8)
		# Create error image. TODO make this a monkey skull...
		self.imageError = self.imageBlack
		# Create the slice array with a first black image.
		self.sliceArray = [self.imageBlack]

	# Create random noise image.
	def createImageNoisy(self):
		imageNoisy = numpy.random.rand(self.programSettings['Projector size X'].value, self.programSettings['Projector size Y'].value, 3) * 255
		imageNoisy = numpy.uint8(imageNoisy)
		return imageNoisy
	
	
	# Update the height of the stack if a new model has been added.
	def update(self, stackHeight):
		# If stack is smaller than given height...
		if len(self.sliceArray) < stackHeight:
			# Last random number.
			noisyImageIndex = 0
			# ... add black images.
			for i in range(stackHeight - len(self.sliceArray)):
				# Add a noisy image randomly chosen from the noisy image list.
				self.sliceArray.append(self.imagesNoisy[noisyImageIndex])
				if noisyImageIndex < self.numberOfNoisyImages-1:
					noisyImageIndex = noisyImageIndex +1
				else:
					noisyImageIndex = 0
		# If stack is higher than given height...
		elif len(self.sliceArray) > stackHeight:
			# ... remove obsolete slices.
			self.sliceArray = self.sliceArray[:stackHeight]
	

	# Return stack height.
	def getStackHeight(self):
		return len(self.sliceArray)


	# Function to return an image.
	def getImage(self,index):
		# If index in bounds...
		if int(index) < len(self.sliceArray):
			# ... return the image.
			return self.sliceArray[int(index)]
		else:
			return self.imageError
		
			
	# Function to add an image to a specific slice and at a specific position.
	def addImage(self, image, index, position):
		# If index in bounds...
		if index < len(self.sliceArray):
			# Get the image.
			img = self.sliceArray[index]
			# Add it to the existing slice.
			# Set region black for testing.
			self.sliceArray[index][10:20][50:150][:] = zeros(10,100,3)
		
	
	
	
				
		




