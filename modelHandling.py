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
#	along with monkeyprint.  If not, see <http://www.gnu.org/licenses/>.


import vtk
from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor
from vtk.util import numpy_support	# Functions to convert between numpy and vtk
import math
import cv2
import numpy
import random
import Tkinter, ttk	# TODO move all Tkinter stuff to extra module.
import Image, ImageTk

# TODO TODO TODO Replace the whole thing.
# 3d view with settings bar. Inherit from frame to use gui specific methods, e.g. pack().
class modelViewer(Tkinter.Frame):
	def __init__(self, parent, console=None, viewWidth=None, viewHeight=None, backgroundColour = (0.329412, 0.34902, 0.427451)):
		# Init super class Frame.
		Tkinter.Frame.__init__(self, parent)
		
		self.console = console
		
		self.frameView = Tkinter.Frame(self)
		
		self.camera =vtk.vtkCamera();
		self.camera.SetViewUp(0,0,1)
		self.camera.SetPosition(192/2+500, 108/2-450,650);
		self.camera.SetFocalPoint(192/2, 108/2, 150);
		self.camera.SetClippingRange(0.0001, 10000)

		
		self.renderer = vtk.vtkRenderer()
		self.renderer.SetBackground( backgroundColour )
		self.renderer.SetActiveCamera(self.camera);
		
		self.renderWindow = vtk.vtkRenderWindow()
		self.renderWindow.AddRenderer(self.renderer)
		
		self.renderWindowInteractor = vtkTkRenderWindowInteractor(self.frameView, rw=self.renderWindow, width = viewWidth, height = viewHeight)                   
		self.renderWindowInteractor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera())
		
		self.renderWindowInteractor.pack(side='top', fill='both', expand=1)
		self.renderWindowInteractor.Initialize()
		self.renderWindowInteractor.Start()
		
		self.paneSettings = ttk.Labelframe(self.frameView, text='View settings')
		self.paneSettings.pack(side='bottom', fill="x", padx=5)
		
		self.buttonReset = Tkinter.Button(self.paneSettings, text = 'Reset view', command = self.reset)
		self.buttonReset.pack(side='left')
		
		self.colorVar = Tkinter.IntVar()
		self.checkboxColour = Tkinter.Checkbutton(self.paneSettings, text='Colours (coming soon...)', variable=self.colorVar, command=self.setColors)
		self.checkboxColour.pack(side='left', padx=5, pady=5)
		self.colorVar.set(1)
		
		self.axesVar = Tkinter.IntVar()
		self.checkboxAxes = Tkinter.Checkbutton(self.paneSettings, text='Axes', variable=self.axesVar, command=self.setAxes)
		self.checkboxAxes.pack(side='left', padx=5, pady=5)
		self.axesVar.set(1)
		
#		self.infoLabel = Tkinter.Label(self.paneSettings, text='Rotate: LMB, Zoom: MMB, Pan: Shift+LMB')
#		self.infoLabel.pack(side='right', padx=5, pady=5)
		
		# Pack the whole frame into parent.
		self.frameView.pack(fill='both', expand=1)

		# Add axes.
		self.axesActor = vtk.vtkAxesActor()
		self.axesActor.SetTotalLength(30,30,30)
		self.axesActor.SetShaftTypeToCylinder()
		self.axesActor.SetCylinderRadius(.05)
		self.axesActor.GetXAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
		self.axesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
		self.axesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().ItalicOff()
		self.axesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().BoldOff()
		self.axesActor.GetXAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
		self.axesActor.GetYAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
		self.axesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
		self.axesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().ItalicOff()
		self.axesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().BoldOff()
		self.axesActor.GetYAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
		self.axesActor.GetZAxisCaptionActor2D().GetTextActor().SetTextScaleModeToNone()
		self.axesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().SetFontSize(12)
		self.axesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().ItalicOff()
		self.axesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().BoldOff()
		self.axesActor.GetZAxisCaptionActor2D().GetCaptionTextProperty().ShadowOff()
		self.addRenderActor(self.axesActor)
		
		# Add handling info.
		self.infoText = vtk.vtkTextActor()
		self.infoText.SetInput("Rotate:  Left mouse button\nPan:       Middle mouse button\nZoom:    Right mouse button")
		self.infoText.GetTextProperty()
		self.infoText.GetTextProperty().SetFontFamilyToArial()
		self.infoText.GetTextProperty().SetFontSize(11)
		self.infoText.GetTextProperty().SetColor(.6,.6,.6)
		self.infoText.SetDisplayPosition(20,30)
		self.addRenderActor(self.infoText)
		

	# Toggle colours.
	def setColors(self):
		if self.console:
			self.console.message("Not yet implemented. Sorry!")
		self.colorVar.set(1)
#		# We need to get all actors and set their colours. This should probably be done in the classes that provide these actors.
#		self.allActors = vtk.vtkActorCollection()
#		self.allActors = self.renderer.GetActors()
#		if self.allActors.GetNumberOfItems() > 2:	# Build volume and axes actor are always there...
#			if self.colorVar:
#				for actor in range(self.allActors.GetNumberOfItems()):
#					self.allActors.GetNextItem().GetProperty().SetColor(1,1,1)
#			else:
#				for actor in range(self.allActors.GetNumberOfItems()):
#					self.allActors.GetNextItem().GetProperty().UnsetColor()
	
	def setAxes(self):
		if self.console:
			self.console.message("View axes: " + str(self.axesVar.get()) + ".")
		self.axesActor.SetVisibility(self.axesVar.get())
		self.render()
	#	self.axesVar = not self.axesVar
	
	# Reset the camera of the render window.
	def reset(self):
		if self.console:
			self.console.message("View reset.")
		self.camera.SetViewUp(0,0,1)
		self.camera.SetPosition(192/2+500, 108/2-450,650);
		self.camera.SetFocalPoint(192/2, 108/2, 150);
		self.camera.SetClippingRange(0.0001, 10000)
		self.render()

	# Add an actor to the render window.
	def addRenderActor(self,actor):
		self.renderer.AddActor(actor)

	# Refresh the render window.	
	def render(self):
		self.renderWindow.Render()
		
	# Override superclass destroy function.
	def destroy(self):
		# Destroy the render window.
    		self.renderWindow.Finalize()
    		self.renderWindowInteractor.TerminateApp()
    		del self.renderWindow, self.renderWindowInteractor
    		# Don't forget to destroy the frame itself!
    		Tkinter.Frame.destroy(self)


class imageViewer:
	def __init__(self, parent, viewWidth, viewHeight, backgroundColour = (0.329412, 0.34902, 0.427451)):
		
		self.camera =vtk.vtkCamera();
		self.camera.SetViewUp(0,1,0)
		self.camera.SetPosition(192/2, 108/2 ,300);
		self.camera.SetFocalPoint(192/2, 108/2, 0);
		self.camera.SetClippingRange(0.0000, 10000)
		
		self.renderer = vtk.vtkRenderer()
		self.renderer.SetBackground( backgroundColour )
		self.renderer.SetActiveCamera(self.camera);
#		self.renderer.ResetCamera()
		
		self.renderWindow = vtk.vtkRenderWindow()
		self.renderWindow.AddRenderer(self.renderer)
		
		self.renderWindowInteractor = vtkTkRenderWindowInteractor(parent, rw=self.renderWindow, width=viewWidth, height=viewHeight)                   
		self.renderWindowInteractor.SetInteractorStyle(vtk.vtkInteractorStyleImage())
		
		self.renderWindowInteractor.pack(side='top', fill='both', expand=1)
		self.renderWindowInteractor.Initialize()
		self.renderWindowInteractor.Start()

#TODO: Maybe this should be AddViewPorp
	def addRenderActor(self,actor):
		self.renderer.AddActor(actor)
#TODO: doesn't work	
	def removeAllActors(self):
		self.renderer.removeAllViewProps()

		
	def render(self):
		self.renderWindow.Render()

	def destroy(self):
    		self.renderWindow.Finalize()
    		self.renderWindowInteractor.TerminateApp()
    		del self.renderWindow, self.renderWindowInteractor
    		
class imageViewerTkinter(Tkinter.Frame):
	def __init__(self, parent, viewWidth, viewHeight, backgroundColour = (0.329412, 0.34902, 0.427451)):
		self.width = viewWidth
		self.height = viewHeight
		
		# Init super class Frame.
		Tkinter.Frame.__init__(self, parent, width=self.width, height=self.height)
		
#		self.console = console
		
		# Create label to show image.
		self.sliceLabel = Tkinter.Label(self)
		self.sliceLabel.pack(side='top', expand=1, fill='both') 
		
		# Create dummy black image.
		self.imageBlack = numpy.zeros((self.height, self.width, 3), numpy.uint8)
		# Convert to Image object.
		self.imageBlackImg = Image.fromarray(self.imageBlack)
		self.imageBlackImgResized = self.imageBlackImg.resize((self.width, self.height),Image.ANTIALIAS)
		# Convert the Image object into a TkPhoto object
		self.imageBlackImgTk = ImageTk.PhotoImage(self.imageBlackImgResized) #keep a reference
		self.sliceLabel.configure(image = self.imageBlackImgTk)
		self.sliceLabel.image = self.imageBlackImgTk
		
	def update(self, image):
		# Convert to Image object.
		self.image = Image.fromarray(image)
		# Resize if neccessary.
		self.imageResized = self.image.resize((self.width, self.height),Image.ANTIALIAS)
		# Convert the Image object into a TkPhoto object
		self.imageRezisedTk = ImageTk.PhotoImage(self.imageResized) #keep a reference
		self.sliceLabel.configure(image = self.imageRezisedTk)
		self.sliceLabel.image = self.imageRezisedTk
	
	def setBlack(self):
		self.sliceLabel.configure(image = self.imageBlackImgTk)
		self.sliceLabel.image = self.imageBlackImgTk
		



################################################################################
################################################################################
################################################################################

class buildVolumeData:
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
		

################################################################################
################################################################################
################################################################################
# TODO TODO TODO: Replace the whole thing
class modelData:
	
	###########################################################################
	# Construction method definition. #########################################
	###########################################################################
	
	def __init__(self):
		# Set up variables.
		self.rotationXOld = 0
		self.rotationYOld = 0
		self.rotationZOld = 0
		self.filenameStl = None
		
		
		# Set up pipeline. ###################################################
		# Stl --> Polydata --> Calc normals --> Scale --> Move to origin --> Rotate --> Move to desired position.
		# Create stl source.
		self.stlReader = vtk.vtkSTLReader() # File name will be set later on when model is actually loaded.
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


		# Create stl mapper and actor. #######################################
		# Mapper.
		self.stlMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.stlMapper.SetInput(self.stlPositionFilter.GetOutput())
		else:
			self.stlMapper.SetInputConnection(self.stlPositionFilter.GetOutputPort())
		# Actor.
		self.stlActor = vtk.vtkActor()
		self.stlActor.SetMapper(self.stlMapper)
		
		
		# Model bounding box. #########################
		# Create cube.
		self.modelBoundingBox = vtk.vtkCubeSource()
		self.modelBoundingBox.SetCenter(self.getCenter())
		self.modelBoundingBox.SetXLength(self.getSize()[0])
		self.modelBoundingBox.SetYLength(self.getSize()[1])
		self.modelBoundingBox.SetZLength(self.getSize()[2])

		# Build volume outline filter.
		self.modelBoundingBoxOutline = vtk.vtkOutlineFilter()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.modelBoundingBoxOutline.SetInput(self.modelBoundingBox.GetOutput())
		else:
			self.modelBoundingBoxOutline.SetInputConnection(self.modelBoundingBox.GetOutputPort())

		# Build volume outline mapper.
		self.modelBoundingBoxMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
		    self.modelBoundingBoxMapper.SetInput(self.modelBoundingBoxOutline.GetOutput())
		else:
		    self.modelBoundingBoxMapper.SetInputConnection(self.modelBoundingBoxOutline.GetOutputPort())

		# Build volume outline actor.
		self.modelBoundingBoxActor = vtk.vtkActor()
		self.modelBoundingBoxActor.SetMapper(self.modelBoundingBoxMapper)
		
		# Display size as text.
		self.modelBoundingBoxTextActor = vtk.vtkCaptionActor2D()
		
		self.modelBoundingBoxTextActor.GetTextActor().SetTextScaleModeToNone()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontFamilyToArial()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetFontSize(12)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().SetColor(1,1,1)
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ShadowOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().ItalicOff()
		self.modelBoundingBoxTextActor.GetCaptionTextProperty().BoldOff()
		self.modelBoundingBoxTextActor.BorderOff()
		self.modelBoundingBoxTextActor.LeaderOff()
		self.modelBoundingBoxTextActor.SetPadding(0)
		
		
		# Get volume.
		self.modelVolume = vtk.vtkMassProperties()
		self.modelVolume.SetInput(self.stlPositionFilter.GetOutput())



	# #########################################################################
	# Public method definitions. ##############################################
	# #########################################################################


	# Analyse normal Z component.
	def getNormalZComponent(self, inputPolydata):
		normalsZ = vtk.vtkFloatArray()
		normalsZ.SetNumberOfValues(inputPolydata.GetPointData().GetArray('Normals').GetNumberOfTuples())
		normalsZ.CopyComponent(0,inputPolydata.GetPointData().GetArray('Normals'),2)
		inputPolydata.GetPointData().SetScalars(normalsZ)
		return inputPolydata
	
	
	def getHeight(self):
		return self.__getBounds(self.stlPositionFilter)[5]
	
	# Load a model of given filename.
	def loadInputFile(self, settings):	# Import 

		# Set filename.
#		self.filenameStl = filename
		# Load model.
		self.stlReader.SetFileName(settings.getFilename())#self.filenameStl)
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

	def getSize(self):
		return self.__getSize(self.stlPositionFilter)
	
	def getVolume(self):
		self.modelVolume.Update()
		return self.modelVolume.GetVolume()
	
	def getCenter(self):
		return self.__getCenter(self.stlPositionFilter)
		
	def getBounds(self):
		return self.__getBounds(self.stlPositionFilter)
		
	def getFilename(self):
		return self.filenameStl
	
	
	def getPolydata(self):
		return self.stlPositionFilter.GetOutput()

	
	def update(self, modelSettings): #scalingFactor, rotationX, rotationY, rotationZ, positionXRel, positionYRel, positionZ):
		# Limit and cast input values.
		# Scaling factor max and positionZ max depend on orientation and scaling and will be tested later on.
		if (modelSettings.getScaling() < 0.00001):
			modelSettings.setScaling(0.00001)
			
		if (modelSettings.getRotationXYZ()[0] > 359 or modelSettings.getRotationXYZ()[0] < 0):
			modelSettings.setRotationXYZ(0, modelSettings.getRotationXYZ()[1], modelSettings.getRotationXYZ()[2])
		if (modelSettings.getRotationXYZ()[1] > 359 or modelSettings.getRotationXYZ()[1] < 0):
			modelSettings.setRotationXYZ(modelSettings.getRotationXYZ()[0], 0, modelSettings.getRotationXYZ()[2])
		if (modelSettings.getRotationXYZ()[2] > 359 or modelSettings.getRotationXYZ()[2] < 0):
			modelSettings.setRotationXYZ(modelSettings.getRotationXYZ()[0], modelSettings.getRotationXYZ()[1], 0)

		if (modelSettings.getPositionXYRel()[0] < 0):
			modelSettings.setPositionXYRel(0, modelSettings.getPositionXYRel()[1])
		elif (modelSettings.getPositionXYRel()[0] > 100):
			modelSettings.setPositionXYRel(100, modelSettings.getPositionXYRel()[1])

		if (modelSettings.getPositionXYRel()[1] < 0):
			modelSettings.setPositionXYRel(modelSettings.getPositionXYRel()[0], 0)
		elif (modelSettings.getPositionXYRel()[1] > 100):
			modelSettings.setPositionXYRel(modelSettings.getPositionXYRel()[0], 100)

		if (modelSettings.getBottomClearance() < 0):
			modelSettings.setBottomClearance(0)

		
		# Move model to origin. ****
		self.stlCenterTransform.Translate(-self.__getCenter(self.stlScaleFilter)[0], -self.__getCenter(self.stlScaleFilter)[1], -self.__getCenter(self.stlScaleFilter)[2])
		self.stlCenterFilter.Update()
		
		# Rotate. ******************
		# Reset rotation.
#		print "Orientation old: " + str(self.stlRotateTransform.GetOrientation())
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[0], 1,0,0)
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[1], 0,1,0)
		self.stlRotateTransform.RotateWXYZ(-self.stlRotateTransform.GetOrientation()[2], 0,0,1)
#		print "Orientation reset: " + str(self.stlRotateTransform.GetOrientation())
#		print "Orientation from settings: " + str(modelSettings.getRotationXYZ())
		# Rotate with new angles.
		self.stlRotateTransform.RotateWXYZ(modelSettings.getRotationXYZ()[0],1,0,0)
		self.stlRotateTransform.RotateWXYZ(modelSettings.getRotationXYZ()[1],0,1,0)
		self.stlRotateTransform.RotateWXYZ(modelSettings.getRotationXYZ()[2],0,0,1)
#		print "Orientation new: " + str(self.stlRotateTransform.GetOrientation())
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
		if (modelSettings.getBuildVolumeSize()[0] / self.dimX) <= (modelSettings.getBuildVolumeSize()[1] / self.dimY) and (modelSettings.getBuildVolumeSize()[0] / self.dimX) <= (modelSettings.getBuildVolumeSize()[2] / self.dimZ):
			smallestRatio =  modelSettings.getBuildVolumeSize()[0] / self.dimX * currentScale
		elif (modelSettings.getBuildVolumeSize()[1] / self.dimY) <= (modelSettings.getBuildVolumeSize()[0] / self.dimX) and (modelSettings.getBuildVolumeSize()[1] / self.dimY) <= (modelSettings.getBuildVolumeSize()[2] / self.dimZ):
			smallestRatio =  modelSettings.getBuildVolumeSize()[1] / self.dimY * currentScale
		elif (modelSettings.getBuildVolumeSize()[2] / self.dimZ) <= (modelSettings.getBuildVolumeSize()[0] / self.dimX) and (modelSettings.getBuildVolumeSize()[2] / self.dimZ) <= (modelSettings.getBuildVolumeSize()[1] / self.dimY):
			smallestRatio =  modelSettings.getBuildVolumeSize()[2] / self.dimZ * currentScale
		# Restrict input scalingFactor if necessary.
		if smallestRatio < modelSettings.getScaling():
			modelSettings.setScaling(smallestRatio)
		# Scale. *******************
		# First, reset scale to 1.
		self.stlScaleTransform.Scale(1/self.stlScaleTransform.GetScale()[0], 1/self.stlScaleTransform.GetScale()[1], 1/self.stlScaleTransform.GetScale()[2])
		# Change scale value.
		self.stlScaleTransform.Scale(modelSettings.getScaling(), modelSettings.getScaling(), modelSettings.getScaling())
		self.stlScaleFilter.Update()	# Update to get new bounds.

		# Position. ****************
		clearRangeX = modelSettings.getBuildVolumeSize()[0] - self.__getSize(self.stlRotationFilter)[0]
		clearRangeY = modelSettings.getBuildVolumeSize()[1] - self.__getSize(self.stlRotationFilter)[1]
		positionZMax = modelSettings.getBuildVolumeSize()[2] - self.__getSize(self.stlRotationFilter)[2]
		if modelSettings.getBottomClearance() > positionZMax:
			modelSettings.setBottomClearance(positionZMax)
		self.stlPositionTransform.Translate(  (self.__getSize(self.stlRotationFilter)[0]/2 + clearRangeX * (modelSettings.getPositionXYRel()[0] / 100.0)) - self.stlPositionTransform.GetPosition()[0],      (self.__getSize(self.stlRotationFilter)[1]/2 + clearRangeY * (modelSettings.getPositionXYRel()[1] / 100.0)) - self.stlPositionTransform.GetPosition()[1],       self.__getSize(self.stlRotationFilter)[2]/2 - self.stlPositionTransform.GetPosition()[2] + modelSettings.getBottomClearance())
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
		

	def getActor(self):
		return self.stlActor
		
	def hideActor(self):
		self.stlActor.SetVisibility(False)
	
	def showActor(self):
		self.stlActor.SetVisibility(True)
		
	def colorActor(self, r, g, b):
		self.stlActor.GetProperty().SetColor(r,g,b)
	
	def setOpacity(self, opacity):
		self.stlActor.GetProperty().SetOpacity(opacity)
	
	def getBoundingBoxActor(self):
		return self.modelBoundingBoxActor
		
	def hideBoundingBoxActor(self):
		self.modelBoundingBoxActor.SetVisibility(False)

	def showBoundingBoxActor(self):
		self.modelBoundingBoxActor.SetVisibility(True)
		
	def colorBoundingBoxActor(self, r, g, b):
		self.modelBoundingBoxActor.GetProperty().SetColor(r,g,b)
	
	def setBoundingBoxOpacity(self, opacity):
		self.modelBoundingBoxActor.GetProperty().SetOpacity(opacity)
	
	def getBoundingBoxTextActor(self):
		return self.modelBoundingBoxTextActor
	
	def hideBoundingBoxTextActor(self):
		self.modelBoundingBoxTextActor.SetVisibility(False)

	def showBoundingBoxTextActor(self):
		self.modelBoundingBoxTextActor.SetVisibility(True)
		
	def colorBoundingBoxTextActor(self, r, g, b):
		self.modelBoundingBoxTextActor.GetProperty().SetColor(r,g,b)
	
	def setBoundingBoxTextOpacity(self, opacity):
		self.modelBoundingBoxTextActor.GetProperty().SetOpacity(opacity)
		
		
		
		
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
################################################################################
################################################################################

class modelOverhangData:
	
	def __init__(self, inputPolydata):
		# Use normals to clip stl.
		# Create clipping filter.
		self.overhangClipFilter = vtk.vtkClipPolyData()
		self.overhangClipFilter.GenerateClipScalarsOff()
		self.overhangClipFilter.SetInsideOut(1)
		self.overhangClipFilter.GenerateClippedOutputOff()
		# Set input polydata.
		self.overhangClipFilter.SetInput(inputPolydata)

		# Create clipped stl mapper and actor.
		self.overhangClipMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.overhangClipMapper.SetInput(self.overhangClipFilter.GetOutput())
		else:
			self.overhangClipMapper.SetInputConnection(self.overhangClipFilter.GetOutputPort())

		# Create stl actor.
		self.overhangClipActor = vtk.vtkActor()
		self.overhangClipActor.SetMapper(self.overhangClipMapper)
		
		
#TODO: update doesn't work right after instantiation			
	def update(self, settings):#, overhangAngle):
		# Calculate clipping threshold based on Z component..
		# Z normals are 1 if pointing upwards, -1 if downwards and 0 if pointing sideways.
		# Turn angle into value between -1 and 0.
		self.clipThreshold = -math.cos(settings.getOverhangAngle()/180.0*math.pi)
		self.overhangClipFilter.SetValue(self.clipThreshold)
		self.overhangClipFilter.Update()

		
	def getPolydata(self):
		return self.overhangClipFilter.GetOutput()
		
	
	def getActor(self):
		return self.overhangClipActor
		
	def hideActor(self):
		self.overhangClipActor.SetVisibility(False)
	
	def showActor(self):
		self.overhangClipActor.SetVisibility(True)
		
	def colorActor(self, r, g, b):
		self.overhangClipActor.GetProperty().SetColor(r,g,b)		
	
	def setOpacity(self, opacity):
		self.overhangClipActor.GetProperty().SetOpacity(opacity)	

	
################################################################################
################################################################################
################################################################################

class bottomPlateData:
	
	def __init__(self, inputPolydata):
		self.inputPolydata = inputPolydata
		# Create box polydata.
		# Edge length 1 mm, place outside of build volume by 1 mm.
		self.bottomPlate = vtk.vtkCubeSource()
		self.bottomPlate.SetXLength(1)
		self.bottomPlate.SetYLength(1)
		self.bottomPlate.SetZLength(1)
		self.bottomPlate.SetCenter((-1, -1, -1))

		# Bottom plate mapper.
		self.bottomPlateMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
		    self.bottomPlateMapper.SetInput(self.bottomPlate.GetOutput())
		else:
		    self.bottomPlateMapper.SetInputConnection(self.bottomPlate.GetOutputPort())

		# Build volume outline actor.
		self.bottomPlateActor = vtk.vtkActor()
		self.bottomPlateActor.SetMapper(self.bottomPlateMapper)
	
	def update(self, settings):#sizeX, sizeY, sizeZ, centerX, centerY, centerZ):
		self.bottomPlate.SetXLength(self.inputPolydata.GetBounds()[1] - self.inputPolydata.GetBounds()[0])
		self.bottomPlate.SetYLength(self.inputPolydata.GetBounds()[3] - self.inputPolydata.GetBounds()[2])
		self.bottomPlate.SetZLength(settings.getBottomPlateThickness())
		self.bottomPlate.SetCenter( (self.inputPolydata.GetBounds()[0] + self.inputPolydata.GetBounds()[1]) / 2.0, (self.inputPolydata.GetBounds()[2] + self.inputPolydata.GetBounds()[3]) / 2.0, settings.getBottomPlateThickness()/2.0)
		self.bottomPlate.Update()

	def getPolydata(self):
		return self.bottomPlate.GetOutput()
	
	def getActor(self):
		return self.bottomPlateActor
		
	def hideActor(self):
		self.bottomPlateActor.SetVisibility(False)
	
	def showActor(self):
		self.bottomPlateActor.SetVisibility(True)
		
	def colorActor(self, r, g, b):
		self.bottomPlateActor.GetProperty().SetColor(r,g,b)		
	
	def setOpacity(self, opacity):
		self.bottomPlateActor.GetProperty().SetOpacity(opacity)	


################################################################################
################################################################################
################################################################################

class supportsData:



	def __init__(self, inputPolydata):
		
		self.inputPolydata = inputPolydata
#TODO	# Filter overhang regions by size.
#		self.overhangRegionFilter = vtk.vtkConnectivityFilter()
#		self.overhangRegionFilter.SetInput(inputPolydata)
#		self.overhangRegionFilter.SetExtractionModeToAllRegions(); 

		# Define cell locator.
		self.locator = vtk.vtkCellLocator()
		self.locator.SetDataSet(inputPolydata)	#TODO: change to selected region input.
		
		# Create cones polydata.
		self.cones = vtk.vtkAppendPolyData()
		
		# Create  mapper.
		self.conesMapper = vtk.vtkPolyDataMapper()
		if vtk.VTK_MAJOR_VERSION <= 5:
			self.conesMapper.SetInput(self.cones.GetOutput())
		else:
			self.conesMapper.SetInputConnection(self.cones.GetOutput())
		
		self.conesActor = vtk.vtkActor()
		self.conesActor.SetMapper(self.conesMapper)

	def getPolydata(self):
		return self.cones.GetOutput()
	
	def getActor(self):
		return self.conesActor
		
	def hideActor(self):
		self.conesActor.SetVisibility(False)
	
	def showActor(self):
		self.conesActor.SetVisibility(True)
		
	def colorActor(self, r, g, b):
		self.conesActor.GetProperty().SetColor(r,g,b)		
	
	def setOpacity(self, opacity):
		self.conesActor.GetProperty().SetOpacity(opacity)
	
	# Update supports.
	def update(self, settings):
		
		# Clear all inputs from cones data.
		self.cones.RemoveAllInputs()

#TODO: Add support regions using	overhangRegionFilter.Update();

		# Update the cell locator.
		self.locator.BuildLocator()
		self.locator.Update()

		# Get input data bounds to set up support pattern.
		# Bounds are absolute coordinates.
		bounds = [0 for i in range(6)]
		self.inputPolydata.GetBounds(bounds)
		
		# Get input data center.
		center = [0 for i in range(3)]
		center[0] = (bounds[1] + bounds[0]) / 2.0
		center[1] = (bounds[3] + bounds[2]) / 2.0
		center[2] = (bounds[5] + bounds[4]) / 2.0

		# Create support pattern bounds.
		# Number of supports in each direction of center.
		nXMin = int(math.floor((center[0] - bounds[0]) / settings.getSupportSpacingXY()[0]))
		nXMax = int(math.floor((bounds[1] - center[0]) / settings.getSupportSpacingXY()[0]))
		nYMin = int(math.floor((center[1] - bounds[2]) / settings.getSupportSpacingXY()[1]))
		nYMax = int(math.floor((bounds[3] - center[1]) / settings.getSupportSpacingXY()[1]))

		
		# Start location, first point of pattern.
		startX = center[0] - nXMin * settings.getSupportSpacingXY()[0]
		startY = center[1] - nYMin * settings.getSupportSpacingXY()[1]

		
		# Number of points in X and Y.
		nX = nXMin + nXMax + 1	# +1 because of center support, nXMin and nXMax only give number of supports to each side of center.
		nY = nYMin + nYMax + 1	# +1 because of center support...
		
		# Loop through point grid and check for intersections.
		for iX in range(nX):
			for iY in range(nY):
				# Get X and Y values.
				pointX = startX + iX * settings.getSupportSpacingXY()[0]
				pointY = startY + iY * settings.getSupportSpacingXY()[1]
				
				# Combine to bottom and top point.
				pointBottom = [pointX, pointY, 0]
				pointTop = [pointX, pointY, settings.getSupportMaxHeight()]
				
				# Create outputs for intersector.
				t = vtk.mutable(0)			# not needed.
				pos = [0.0, 0.0, 0.0]		# that's what we're looking for.
				pcoords = [0.0, 0.0, 0.0]	# not needed.
				subId = vtk.mutable(0)		# not needed.
				tolerance = 0.001
		
				# Intersect.
				self.locator.IntersectWithLine(pointBottom, pointTop, tolerance, t, pos, pcoords, subId)

				# Create cone f intersection point found.
				if pos != [0,0,0]:
					# Create cone.
					cone = vtk.vtkConeSource()
					# Set cone dimensions.
					cone.SetRadius(settings.getSupportBaseDiameter()/2.0)
					cone.SetHeight(settings.getSupportTipHeight())
					cone.SetResolution(20)
					# Set cone position (at cone center) according to current point.
					pos[2] = pos[2]-settings.getSupportTipHeight()/2.0
					# Adjust cone Z position to meet tip connection diameter.
					pos[2] = pos[2]+1.0*settings.getSupportTipHeight()/(1.0*settings.getSupportBaseDiameter()/settings.getSupportTipDiameter())
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
					cylinder.SetRadius(settings.getSupportBaseDiameter()/2.0)
					cylinder.SetHeight(pos[2]-settings.getSupportTipHeight()/2.0)
					cylinder.SetResolution(20)
					
					# Set cylinder position.
					# Adjust height to fit beneath corresponding cone.
					pos[2] = (pos[2]-settings.getSupportTipHeight()/2.0)/2.0
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
					self.cones.AddInput(coneGeomFilter.GetOutput())
					# Delete the cone. Vtk delete() method does not work in python because of garbage collection.
					del cone
					# Append the cylinder to the cones polydata.
					self.cones.AddInput(cylinderGeomFilter.GetOutput())
					del cylinder



class sliceData:
	def __init__(self, inputModelPolydata, inputSupportsPolydata, inputBottomPlatePolydata, settings, console, printFlag=False):
		
		self.inputModelPolydata = inputModelPolydata
		self.inputSupportsPolydata = inputSupportsPolydata
		self.inputBottomPlatePolydata = inputBottomPlatePolydata
		
		self.settings = settings
		self.console = console
		self.printFlag = printFlag

		self.extrusionVector = (0,0,-1)

		# The following is for 3D slice data. ################################

		# Create cutting plane.
		self.cuttingPlane = vtk.vtkPlane()
		self.cuttingPlane.SetNormal(0,0,1)
		self.cuttingPlane.SetOrigin(0,0,0.001)	# Make sure bottom plate is cut properly.
	
		# Create cutting filter for model.
		self.cuttingFilterModel = vtk.vtkCutter()
		self.cuttingFilterModel.SetCutFunction(self.cuttingPlane)
		self.cuttingFilterModel.SetInput(self.inputModelPolydata)
		
		# Create cutting filter for supports.
		self.cuttingFilterSupports = vtk.vtkCutter()
		self.cuttingFilterSupports.SetCutFunction(self.cuttingPlane)
		self.cuttingFilterSupports.SetInput(self.inputSupportsPolydata)
		
		# Create cutting filter for bottom plate.
		self.cuttingFilterBottomPlate = vtk.vtkCutter()
		self.cuttingFilterBottomPlate.SetCutFunction(self.cuttingPlane)
		self.cuttingFilterBottomPlate.SetInput(self.inputBottomPlatePolydata)
	
		# Create polylines from cutter output for model.
		self.sectionStripperModel = vtk.vtkStripper()
		self.sectionStripperModel.SetInput(self.cuttingFilterModel.GetOutput())
#TODO: remove scalars so color is white.
#		self.sectionStripperModel.GetOutput().GetPointData().RemoveArray('normalsZ')
		
		# Turn into polydata.
#		self.sectionStripperPolydataModel = vtk.vtkPolyData()
#		self.sectionStripperPolydataModel.SetPoints(self.sectionStripperModel.GetOutput().GetPoints())
#		self.sectionStripperPolydataModel.SetPolys(self.sectionStripperModel.GetOutput().GetLines())
		
		# Create polylines from cutter output for supports.
		self.sectionStripperSupports = vtk.vtkStripper()
		self.sectionStripperSupports.SetInput(self.cuttingFilterSupports.GetOutput())
		
		# Create polylines from cutter output for bottom plate.
		self.sectionStripperBottomPlate = vtk.vtkStripper()
		self.sectionStripperBottomPlate.SetInput(self.cuttingFilterBottomPlate.GetOutput())
		
		# Combine cut lines from model, supports and bottom plate.
		self.combinedCutlines = vtk.vtkAppendPolyData()
		self.combinedCutlines.AddInput(self.sectionStripperModel.GetOutput())
		self.combinedCutlines.AddInput(self.sectionStripperSupports.GetOutput())
		self.combinedCutlines.AddInput(self.sectionStripperBottomPlate.GetOutput())
		
		# Cut mapper for model.
		self.cuttingFilterMapper = vtk.vtkPolyDataMapper()
		self.cuttingFilterMapper.SetInput(self.combinedCutlines.GetOutput())
		
		# Cut actor for model.
		self.cuttingFilterActor = vtk.vtkActor()
		self.cuttingFilterActor.SetMapper(self.cuttingFilterMapper)
		
		
		
		# The following is for slice images. #################################
		
		# Create black image for opencv.
	#	self.cvImage = numpy.zeros((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0], 3), numpy.uint8)

		# Create a numpy array to set the vtkImageData scalars. That's much faster than looping through the points.
		# Make single channel image first as numpy_to_vtk only takes one channel.
		self.cvImage = numpy.ones((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0]), numpy.uint8)
		self.cvImage *= 255.
		# Create image.
		self.image = vtk.vtkImageData()
		self.image.GetPointData().SetScalars(numpy_support.numpy_to_vtk(self.cvImage))
		self.image.SetDimensions(settings.getProjectorSizeXY()[0], settings.getProjectorSizeXY()[1],1)
		self.image.SetSpacing(0.1,0.1,0.1)
		self.image.SetExtent(0, settings.getProjectorSizeXY()[0]-1,0, settings.getProjectorSizeXY()[1]-1,0,0)
		self.image.SetScalarTypeToUnsignedChar()
		self.image.SetNumberOfScalarComponents(1)
		self.image.AllocateScalars()
		# TODO: What's the best order to do the image allocation?
		
		# Create an opencv image with rectangular pattern for filling large model areas.
		# Only, if object is created for printing. Otherwise this is a little slow...
		self.cvImagePattern = self.updateFillPattern()
#		self.cvImagePattern = numpy.zeros((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0]), numpy.uint8)
#
		self.cvImageBlack = numpy.zeros((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0]), numpy.uint8)
#
#		# Set every Nth vertical line (and it's  neighbour or so) white.
#		N = 20.0
#		for pixelX in range(settings.getProjectorSizeXY()[0]):
#			if pixelX / N - math.floor(pixelX / N) < .2:		# TODO: set spacing values from settings dict.
#				self.cvImagePattern[:,pixelX-1] = 255
#		# Set every 15th horizontal line (and it's  neighbour or so) white.
#		for pixelY in range(settings.getProjectorSizeXY()[1]):
#			if pixelY / N - math.floor(pixelY / N) < .2:		# TODO: set spacing values from settings dict.
#				self.cvImagePattern[pixelY-1,:] = 255
#		
#		# Reshape...
#		self.cvImagePattern = self.cvImagePattern.reshape(1, 1080, 1920)
#		self.cvImagePattern = self.cvImagePattern.transpose(1,2,0)
#		
#		# Expand to 3 channels per pixel.	
#		self.cvImagePattern = numpy.repeat(self.cvImagePattern, 3, axis = 2)
		
		# Copy to use as base for eroded image and wall image later.
		self.imageArrayNumpyEroded = self.cvImagePattern
		self.imageArrayNumpyWall = self.cvImagePattern
		self.imageArrayNumpy = self.cvImageBlack


		# Extrude cut polyline.
		self.extruderModel = vtk.vtkLinearExtrusionFilter()
		self.extruderModel.SetInput(self.sectionStripperModel.GetOutput())
		self.extruderModel.SetScaleFactor(1)
		self.extruderModel.CappingOn()
		self.extruderModel.SetExtrusionTypeToVectorExtrusion()
		self.extruderModel.SetVector(self.extrusionVector)	# Adjust this later on to extrude each slice to Z = 0.
		
		# Extrude cut polyline.
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
		
#		# Mapper.
#		self.extruderMapper = vtk.vtkPolyDataMapper()
#		if vtk.VTK_MAJOR_VERSION <= 5:
#			self.extruderMapper.SetInput(self.extruderModel.GetOutput())
#		else:
#			self.extruderMapper.SetInputConnection(self.extruderModel.GetOutputPort())
#		# Actor.
#		self.extruderActor = vtk.vtkActor()
#		self.extruderActor.SetMapper(self.extruderMapper)
		
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
		
		
		# Combine
		self.combinedSliceImageModelSupports = vtk.vtkImageMathematics()
		self.combinedSliceImageModelSupports.SetInput1(self.stencilModel.GetOutput())
		self.combinedSliceImageModelSupports.SetInput2(self.stencilSupports.GetOutput())
		self.combinedSliceImageModelSupports.SetOperationToAdd()
		
		self.combinedSliceImageModelSupportsBottomPlate = vtk.vtkImageMathematics()
		self.combinedSliceImageModelSupportsBottomPlate.SetInput1(self.combinedSliceImageModelSupports.GetOutput())
		self.combinedSliceImageModelSupportsBottomPlate.SetInput2(self.stencilBottomPlate.GetOutput())
		self.combinedSliceImageModelSupportsBottomPlate.SetOperationToAdd()


		# Optional image writer...
#		self.imageWriter = vtk.vtkPNGWriter()
#		self.imageWriter.SetFileName("labelImage.png")
#		self.imageWriter.SetInput(self.imageNew)
		
#		# Image slice actor.
#		self.imageActor = vtk.vtkImageActor()
#		self.imageActor.SetInput(self.combinedSliceImageModelSupportsBottomPlate.GetOutput())

	def updateFillPattern(self):
		# Create an opencv image with rectangular pattern for filling large model areas.
		self.cvImagePattern = numpy.zeros((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0]), numpy.uint8)

		# Limit fill pattern spacing.
		if self.settings.getFillSpacing() < 1.0:		# TODO: get min and max values from settings dict
			self.settings.setFillSpacing(1.0)
		elif self.settings.getFillSpacing() > 10.0:
			self.settings.setFillSpacing(10.0)
		
		# Limit fill wall thickness.
		if self.settings.getFillWallThickness() < 0.1:		# TODO: get min and max values from settings dict
			self.settings.setFillWallThickness(0.1)
		elif self.settings.getFillWallThickness() > 0.5:
			self.settings.setFillWallThickness(0.5)		

		# Set every Nth vertical line (and it's  neighbour or so) white.
		spacing = self.settings.getFillSpacing() * self.settings.getPxPerMm()
		wallThickness = self.settings.getFillWallThickness() * self.settings.getPxPerMm()
		for pixelX in range(self.settings.getProjectorSizeXY()[0]):
			if (pixelX / spacing - math.floor(pixelX / spacing)) * spacing < wallThickness:		# TODO: set spacing values from settings dict.
				self.cvImagePattern[:,pixelX-1] = 255
		# Set every 15th horizontal line (and it's  neighbour or so) white.
		for pixelY in range(self.settings.getProjectorSizeXY()[1]):
			if (pixelY / spacing - math.floor(pixelY / spacing)) * spacing < wallThickness:		# TODO: set spacing values from settings dict.
				self.cvImagePattern[pixelY-1,:] = 255
		
		# Reshape...
		self.cvImagePattern = self.cvImagePattern.reshape(1, self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0])
		self.cvImagePattern = self.cvImagePattern.transpose(1,2,0)
		
		# Expand to 3 channels per pixel.	
		self.cvImagePattern = numpy.repeat(self.cvImagePattern, 3, axis = 2)	
		
		return self.cvImagePattern


	def update(self, layerHeight, sliceNumber):
		print "UPDATING SLICE " + str(sliceNumber) + "."
		self.cuttingPlane.SetOrigin(0,0,layerHeight*sliceNumber)
		self.extruderModel.SetVector(0,0,-sliceNumber*layerHeight-1)
		self.extruderSupports.SetVector(0,0,-sliceNumber*layerHeight-1)
		self.extruderBottomPlate.SetVector(0,0,-sliceNumber*layerHeight-1)
		self.combinedSliceImageModelSupportsBottomPlate.Update()
		
		# Limit shell thickness.
		if self.settings.getShellThickness() < 1.0:		# TODO: get min and max values from settings dict
			self.settings.setShellThickness(1.0)
		elif self.settings.getShellThickness() > 5.0:
			self.settings.setShellThickness(5.0)	
		
		# Get pixel values from vtk image data. ################################
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
		
		
		# Update fill pattern image.
#		self.cvImagePattern = self.updateFillPattern()
				
		# Get pixel values from 10 slices above and below. ##################
		# We need to analyse these to be able to generate closed bottom and top surfaces.
		# Only use model slice data. Supports and bottom plate have no internal pattern anyway.
		# Check if we are in the first or last mm of the model, then there should not be a pattern anyways, so we set everything black.
		# Only do this whole thing if fillFlag is set and fill is shown or print is going.
		if self.settings.getHollow() == True and (self.settings.getFillShow() == True or self.printFlag == True):
			wallThicknessTopBottom = self.settings.getShellThickness()	# [mm]
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
			wallThickness = self.settings.getShellThickness()	* self.settings.getPxPerMm()	# [px]
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
#			self.imageArrayNumpyWall = cv2.add(self.imageArrayNumpyWall, self.imageArrayNumpyEroded)
			if self.settings.getFill():
				self.imageArrayNumpy = cv2.add(self.imageArrayNumpyWall, self.imageArrayNumpyEroded)
			else:
				self.imageArrayNumpy = self.imageArrayNumpyWall
		
		
#		# Reset image.
#		self.cvImage = numpy.zeros((self.settings.getProjectorSizeXY()[1], self.settings.getProjectorSizeXY()[0], 3), numpy.uint8)
##		print self.cvImage.shape
#		print "foo 1"
#		# Get polylines from model stripper.
#		self.stripPoints = vtk.vtkPoints()
#		self.stripPoints = self.sectionStripperModel.GetOutput().GetPoints()
#		self.stripCells = vtk.vtkCellArray()
#		self.stripCells = self.sectionStripperModel.GetOutput().GetLines()
#		self.numberOfCells = self.stripCells.GetNumberOfCells()
#		# Create point id list.
#		ids = vtk.vtkIdList()
#		# Initialise cell id.
#		self.stripCells.InitTraversal()
#		cellCounter = 0
#		# Loop through cells.
#		# Writes the indices of current cell's points to ids.
#		# Actual cells might be represented by a number of cells which we have to merge first.
#		# So we first make an array of polylines, then merge the ones that share common end points.
#		print "foo 2"
#		polylines = []
#		while self.stripCells.GetNextCell(ids):	# GetNextCell returns 1 until the last cell, then it returns 0.
#			cellCounter += 1
##			print '         Current contour: ' + str(ids.GetNumberOfIds()) + ' points.'
#			polyline = []
#			# Loop through current contour's points and write them to the svg file.
#			for iPoint in range(ids.GetNumberOfIds()):
#				currentPoint = [0,0,0]
#				self.stripPoints.GetPoint(ids.GetId(iPoint), currentPoint)	# Take current point's id and write point to input 	argument 2.
#				polyline.append((currentPoint[0], self.settings.getBuildVolumeSize()[1] - currentPoint[1]))
#			# Write current polyline to polyline array.
#			polylines.append(polyline)
#	
#		print "foo 3"		
#		# Draw polylines.
#		# Iterate through all polylines, convert them to a numpy array of special format and append to numpyPolylines.
#		numpyPolylines = []
#		for i in range(len(polylines)):
#			numpyPolyline = numpy.asarray(polylines[i])
#			numpyPolyline = numpyPolyline.reshape((-1,1,2))	# 1st dim: number of polygons, second dim: ?, third dim: points.
#			# Convert mm to px.
#			numpyPolyline *= self.settings.getPxPerMm()
#			numpyPolyline = numpy.int32(numpyPolyline)
#			numpyPolylines.append(numpyPolyline)
#		print "foo 4"
##		numpyPolylines = numpy.int32(numpyPolylines)
#		print "foo 5"
#		print "Found " + str(len(numpyPolylines)) + " polylines."
#		cv2.fillPoly(self.cvImage, numpyPolylines, (255,255,255), lineType=0, shift=0)
##			cv2.polylines(self.cvImage,numpy.int32([numpyPolyline]),False,(random.randint(100,255),random.randint(100,255),random.randint(100,255)),4,8)
##			cv2.fillConvexPoly(self.cvImage, numpy.int32(numpyPolyline), (255,255,255), lineType=0, shift=0)
#
#
#		# Get polylines from bottom plate stripper.
#		self.stripPoints = vtk.vtkPoints()
#		self.stripPoints = self.sectionStripperBottomPlate.GetOutput().GetPoints()
#		self.stripCells = vtk.vtkCellArray()
#		self.stripCells = self.sectionStripperBottomPlate.GetOutput().GetLines()
#		self.numberOfCells = self.stripCells.GetNumberOfCells()
#		# Create point id list.
#		ids = vtk.vtkIdList()
#		# Initialise cell id.
#		self.stripCells.InitTraversal()
#		cellCounter = 0
#		# Loop through cells.
#		# Writes the indices of current cell's points to ids.
#		# Actual cells might be represented by a number of cells which we have to merge first.
#		# So we first make an array of polylines, then merge the ones that share common end points.
#		polylines = []
#		while self.stripCells.GetNextCell(ids):	# GetNextCell returns 1 until the last cell, then it returns 0.
#			cellCounter += 1
##			print '         Current contour: ' + str(ids.GetNumberOfIds()) + ' points.'
#			polyline = []
#			# Loop through current contour's points and write them to the svg file.
#			for iPoint in range(ids.GetNumberOfIds()):
#				currentPoint = [0,0,0]
#				self.stripPoints.GetPoint(ids.GetId(iPoint), currentPoint)	# Take current point's id and write point to input 	argument 2.
#				polyline.append((currentPoint[0], self.settings.getBuildVolumeSize()[1] - currentPoint[1]))
#			# Write current polyline to polyline array.
#			polylines.append(polyline)
#	
#		# Draw polylines.
##		print len(polylines)
#		for i in range(len(polylines)):
#			numpyPolyline = numpy.asarray(polylines[i])
#			numpyPolyline = numpyPolyline.reshape((-1,1,2))
#			numpyPolyline *= self.settings.getPxPerMm()
#			cv2.fillPoly(self.cvImage, numpy.int32([numpyPolyline]), (255,255,255), lineType=0, shift=0)
##			cv2.polylines(self.cvImage,numpy.int32([numpyPolyline]),False,(random.randint(100,255),random.randint(100,255),random.randint(100,255)),4,8)
##			cv2.fillConvexPoly(self.cvImage, numpy.int32(numpyPolyline), (255,255,255), lineType=0, shift=0)		
#
#
#		# Get polylines from supports stripper.
#		self.stripPoints = vtk.vtkPoints()
#		self.stripPoints = self.sectionStripperSupports.GetOutput().GetPoints()
#		self.stripCells = vtk.vtkCellArray()
#		self.stripCells = self.sectionStripperSupports.GetOutput().GetLines()
#		self.numberOfCells = self.stripCells.GetNumberOfCells()
#		# Create point id list.
#		ids = vtk.vtkIdList()
#		# Initialise cell id.
#		self.stripCells.InitTraversal()
#		cellCounter = 0
#		# Loop through cells.
#		# Writes the indices of current cell's points to ids.
#		# Actual cells might be represented by a number of cells which we have to merge first.
#		# So we first make an array of polylines, then merge the ones that share common end points.
#		polylines = []
#		while self.stripCells.GetNextCell(ids):	# GetNextCell returns 1 until the last cell, then it returns 0.
#			cellCounter += 1
##			print '         Current contour: ' + str(ids.GetNumberOfIds()) + ' points.'
#			polyline = []
#			# Loop through current contour's points and write them to the svg file.
#			for iPoint in range(ids.GetNumberOfIds()):
#				currentPoint = [0,0,0]
#				self.stripPoints.GetPoint(ids.GetId(iPoint), currentPoint)	# Take current point's id and write point to input 	argument 2.
#				polyline.append((currentPoint[0], self.settings.getBuildVolumeSize()[1] - currentPoint[1]))
#			# Write current polyline to polyline array.
#			polylines.append(polyline)
#	
#		# Draw polylines.
##		print len(polylines)
#		for i in range(len(polylines)):
#			numpyPolyline = numpy.asarray(polylines[i])
#			numpyPolyline = numpyPolyline.reshape((-1,1,2))
#			numpyPolyline *= self.settings.getPxPerMm()
#			cv2.fillPoly(self.cvImage, numpy.int32([numpyPolyline]), (255,255,255), lineType=0, shift=0)
##			cv2.polylines(self.cvImage,numpy.int32([numpyPolyline]),False,(random.randint(100,255),random.randint(100,255),random.randint(100,255)),4,8)
##			cv2.fillConvexPoly(self.cvImage, numpy.int32(numpyPolyline), (255,255,255), lineType=0, shift=0)	
#
				
##		self.imageWriter.Write()

	def pointsEqual(self, pointA, pointB, tolerance):
		return (abs(pointA[0] - pointB[0]) < tolerance and abs(pointA[1] - pointB[1]) < tolerance)
		

	def getNumberOfSlices(self):
		return int(math.floor(self.inputModelPolydata.GetBounds()[5] / self.settings.getLayerHeight()))

	def getExtruderActor(self):
		return self.extruderActor
	
	def getCvImage(self):
	#	return self.cvImagePattern
	#	return self.cvImagePatternEroded
	#	return self.imageArrayNumpyEroded
#		# Return image with fill if desired or if slice object is for print process.
#		if self.self.settings.getFillShow() == True or self.printFlag == True:
#			# Return image with fill.
#			return self.imageArrayNumpyWall
#		# Return image without fill.
#		else:
#			return self.imageArrayNumpy
		return self.imageArrayNumpy		
	#	return self.imageArrayTopMaskNumpy


	def getPolydata(self):
		return self.cuttingFilter.GetOutput()
	
#	def getImageActor(self):
#		return self.imageActor
#	
#	def hideImageActor(self):
#		self.imageActor.SetVisibility(False)
#	
#	def showImageActor(self):
#		self.imageActor.SetVisibility(True)
	
	def getActor(self):
		return self.cuttingFilterActor
		
	def hideActor(self):
		self.cuttingFilterActor.SetVisibility(False)
	
	def showActor(self):
		self.cuttingFilterActor.SetVisibility(True)
		
	def colorActor(self, r, g, b):
		self.cuttingFilterActor.GetProperty().SetColor(r,g,b)		
	
	def setOpacity(self, opacity):
		self.cuttingFilterActor.GetProperty().SetOpacity(opacity)


















#		allPolylines = []
#		
#		# Loop through cells.
#		# Writes the indices of current cell's points to ids.
#		while self.stripCells.GetNextCell(ids):		# GetNextCell returns 1 until the last cell, then it returns 0.
#			cellCounter +=1
#			
#			# Get current contours points.
#			for iPoint in range(ids.GetNumberOfIds()):
#				currentPoint = [0,0,0]
#				self.stripPoints.GetPoint(ids.GetId(iPoint), currentPoint)	# Take current point's id and write point to input 	argument 2.
#				allPolylines.append((currentPoint[0], self.settings.getBuildVolumeSize()[1] - currentPoint[1]))
#	#	print allPolylines
#		
#		# loop through all points and find reoccuring points. These mark the beginning and end of a polygon.
#		currentPolyline = []
##		currentPolylineCounter = 0
#		for pt in range(1,len(allPolylines)):
#			
#			# Start new polyline.
#			if len(currentPolyline) == 0:	#currentPolylineCounter == 0:
#				currentPolyline.append(allPolylines[pt])
#				print allPolylines[pt]
#				print "start"
##				currentPolylineCounter += 1
#			# Append to existing polyline.
#			else:
#				# Check if same as previous point --> end and start of polylines that belong together. Skip point.
##				print allPolylines[pt]
##				print currentPolyline[len(currentPolyline)-1]
#				if self.pointsEqual(allPolylines[pt], currentPolyline[-1], 0.001):
#					print "skip"
#					pass
#					
#				# Check if same as current polyline start point --> end of current polyline.
#				elif self.pointsEqual(allPolylines[pt], currentPolyline[0], 0.001):
#					# End polyline and paint.
#					numpyPolyline = numpy.asarray(currentPolyline)
#					numpyPolyline = numpyPolyline.reshape((-1,1,2))
#					numpyPolyline *= self.settings.getPxPerMm()
#					print numpyPolyline
##					cv2.polylines(self.cvImage,numpy.int32([numpyPolyline]),False,(255,255,255),1,8)
#					cv2.fillPoly(self.cvImage, numpy.int32([numpyPolyline]), (255,255,255), lineType=0, shift=0)
#					print "end"
#					currentPolyline = []
##					currentPolylineCounter = 0
#				else:
#					currentPolyline.append(allPolylines[pt])
#	#				print "pass"
#
#	#		print currentPolyline[0]
#	#		print allPolylines[pt]













#		print polylines
##			endpoints.append([polyline[0],polyline[-1])
#		
#		# Empty list for sorted polylines.
#		polylinesSorted = []
#		# Append first polyline.
#		polylinesSorted.append(polylines[0])
#		while len(polylines) > 0:
#			for i in range(len(polylines)):
#				# Search for polyline that shares end point with last polyline.
#				if self.pointsEqual(polylinesSorted[-1][-1], polylines[i][0], 0.01):
#					polylinesSorted.append(polylines[i])
#					del polylines[i]
#					break
#				elif self.pointsEqual(polylinesSorted[-1][-1], polylines[i][-1], 0.01):
#					polylines[i].reverse()
#					polylinesSorted.append(polylines[i])
#					del polylines[i]
#					break
#				# Copy last polyline if no adjacent polyline has been found.
#				if i == len(polylines)-1:
#					polylinesSorted.append(polylines[i])
#		j = 0
#		# Merge adjacent polylines.
#		while j < len(polylinesSorted)-1:
#			if self.pointsEqual(polylinesSorted[j][-1], polylinesSorted[j+1][0], 0.001):
#				polylinesSorted[j][-1:-1] = polylinesSorted[j+1]
#				del polylinesSorted[j+1]
#				print j
#				
#			else:
#				j += 1
#				print "foo"
#			
#			
##
#		
#		
#		if len(polylines) > 0 and True:
#			print "Sorting polylines."
#		
#			# Cluster polylines that belong to the same polygon.
#			polylinesChanged = True
#			loopCounter = 0
#			case1Counter = 0
#			case2Counter = 0
#			case3Counter = 0
#			case4Counter = 0
#			# Loop through polylines until everything is sorted.
#			while polylinesChanged:
#				loopCounter += 1
#				polylinesChanged = False
#				iPoly = 0
#				# Loop through polylines.
#				while iPoly < len(polylines):
#					# Compare with each other polyline.
#					jPoly = 0
#					while jPoly < len(polylines):
#						# Avoid comparing polyline with itself.
#						if iPoly != jPoly:
#							# Skip closed contours.
#							if not self.pointsEqual(polylines[iPoly][0], polylines[iPoly][-1], 0.001):
#								# Start points are equal.
##								print "Index i: " + str(iPoly) + ", index j: " + str(jPoly)
#			#					if self.pointsEqual(polylines[iPoly][0], polylines[jPoly][0], 0.001):
#			#						# Move the matching polyline to current polyline and delete.
#			#						# Reverse point order.
#			#						polylines[jPoly].reverse()
#			#						# Remove last point.
#			#						del polylines[jPoly][-1]
#			#						# Insert at start.
#			#						polylines[iPoly][0:0]=polylines[jPoly]
#			#						del polylines[jPoly] 
#			#						print "Polyline at " + str(jPoly) + " moved to " + str(iPoly) + "."
#			#						polylinesChanged = True
#			#						jPoly -= 1
#			#						iPoly -= 1
#			#						case1Counter += 1
#			#						break
#								# Start and end point are equal.
#								if self.pointsEqual(polylines[iPoly][0], polylines[jPoly][-1], 0.001):
#									# Move the matching polyline to current polyline and delete.
#									# Remove last point.
#									del polylines[jPoly][-1]
#									# Insert at start
#									polylines[iPoly][0:0] = polylines[jPoly]
#									del polylines[jPoly] 
#									print "Polyline at " + str(jPoly) + " moved to " + str(iPoly) + "."
#									polylinesChanged = True
#									jPoly -= 1
#									iPoly -= 1
#									case2Counter += 1
#									break
#								# End and start point are equal.
#								elif self.pointsEqual(polylines[iPoly][-1], polylines[jPoly][0], 0.001):
#									# Move the matching polyline to current polyline and delete.
#									# Remove first point.
#									del polylines[jPoly][0]
#									polylines[iPoly][-1:-1] = polylines[jPoly]
#									del polylines[jPoly]
#									print "Polyline at " + str(jPoly) + " moved to " + str(iPoly) + "."
#									polylinesChanged = True
#									jPoly -= 1
#									iPoly -= 1
#									case3Counter += 1
#									break
#								# End points are equal.
#				#				elif self.pointsEqual(polylines[iPoly][-1], polylines[jPoly][-1], 0.001):
#				#					# Move the matching polyline to current polyline and delete.
#				#					polylines[jPoly].reverse()
#				#					# Remove first point.
#				#					del polylines[jPoly][0]
#				#					polylines[iPoly][-1:-1] = polylines[jPoly]
#				#					del polylines[jPoly] 
#				#					print "Polyline at " + str(jPoly) + " moved to " + str(iPoly) + "."
#				#					polylinesChanged = True
#				#					jPoly -= 1
#				#					iPoly -= 1
#				#					case4Counter += 1
#				#					break
#								# Start and end points are equal.
#				#				elif self.pointsEqual(polylines[iPoly][-1], polylines[jPoly][-1], 0.001):
#								
#							
#						jPoly += 1
#					iPoly += 1
#				if loopCounter < 5:
#					polylinesChanged = True
#				
#			print "Sorting done."
#			print len(polylines)
#			print loopCounter
#			print case1Counter
#			print case2Counter
#			print case3Counter
#			print case4Counter
#		
