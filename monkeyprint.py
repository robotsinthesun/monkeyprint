#!/usr/bin/python
# -*- coding: latin-1 -*-

# Import the modules for the code
import Tkinter
import ttk					# Used for notebook widged.
from tkFileDialog import askopenfilename      # Open file dialog.
import tkMessageBox
import Image, ImageTk
import numpy

import threading
import Queue
import sys
import os
import math
import time

import cv2

import modelHandling
import printSettings
import serialCommunication

import vtk
from vtk.tk.vtkTkRenderWindowInteractor import vtkTkRenderWindowInteractor



# Create settings. #############################################################
settings = printSettings.printSettings()

filenameStl = ""
#threadPrint = None
wait = None
projector = None

printingFlag = False

frameSettingsWidth = 350


# Root window. #################################################################
root = Tkinter.Tk()
root.title( "Print-O-mat" )
root.attributes('-zoomed', True)

# Close function.
def on_closing():
	# Prevent closing if print is running.
	global projector
	if printingFlag:
		print "Please wait for print process to finish or cancel the print before closing."
	else:
		if tkMessageBox.askokcancel("Quit", "Do you want to quit?"):
			#TODO: Get focus on close event
			# We need to destroy the vtk viewer before the Tk gui gets destroyed.
			view.destroy()
			root.destroy()

# Bind close function to close event.
root.protocol("WM_DELETE_WINDOW", on_closing)


def on_resize( event ):
#	pass
	view.render() #
# Re-render on window resize.
root.bind( '<Configure>', on_resize)

# Frame for settings on the right.
frameSettings = Tkinter.Frame(root, width = frameSettingsWidth)
#frameSettings.pack(side='right', expand = 1, fill = 'y')
frameSettings.pack_propagate(False)
frameSettings.grid_propagate(False)

# Text console for some output.
class debugConsole(Tkinter.Text):
	def __init__(self, parent, height=10):
		Tkinter.Text.__init__(self, parent, height=height, state='disabled')
	def message(self, inputString):
		self.configure(state="normal")
		self.insert(Tkinter.END, inputString + '\n')
		self.configure(state="disabled")

console = debugConsole(frameSettings, height = 10)


# 3d-View and actors. ##########################################################
# Create the 3d view. Pass root as parent.
view = modelHandling.modelViewer(root, console)
view.pack(side='left', expand = 1, fill = 'both')

# Create model.
model = modelHandling.modelData()
# Add model actor.
view.addRenderActor(model.getActor()) 	# Do this later to avoid errors because of no input data.
model.hideActor()
# Add model bounding box with size label.
view.addRenderActor(model.getBoundingBoxActor()) 	# Do this later to avoid errors because of no input data.
view.addRenderActor(model.getBoundingBoxTextActor()) 	# Do this later to avoid errors because of no input data.
model.hideBoundingBoxActor()
model.hideBoundingBoxTextActor()

# Create build volume outline.
buildVolume = modelHandling.buildVolumeData(settings.getBuildVolumeSize())
# Add build volume outline actor.
view.addRenderActor(buildVolume.getActor())

#TODO: maybe it would be cleaner to simply pass model instance to all filters instead of model.getPolydata()
# Create bottom plate.
bottomPlate = modelHandling.bottomPlateData(model.getPolydata())
view.addRenderActor(bottomPlate.getActor())
bottomPlate.hideActor()

# Create clipped overhang polydata.
modelOverhang = modelHandling.modelOverhangData(model.getPolydata())
view.addRenderActor(modelOverhang.getActor())
modelOverhang.hideActor()

# Create supports polydata.
supports = modelHandling.supportsData(modelOverhang.getPolydata())
view.addRenderActor(supports.getActor())
supports.hideActor()

# Create slices polydata for slice tab..
slices = modelHandling.sliceData(model.getPolydata(), supports.getPolydata(), bottomPlate.getPolydata(), settings, console, printFlag=False)
view.addRenderActor(slices.getActor())
slices.hideActor()
#view.addRenderActor(slices.getExtruderActor())

# Create slices polydata for projector display.
slicesPrint = modelHandling.sliceData(model.getPolydata(), supports.getPolydata(), bottomPlate.getPolydata(), settings, console, printFlag=True)
view.addRenderActor(slicesPrint.getActor())
slicesPrint.hideActor()

# Notebook. ####################################################################
# Create notebook.
notebook = ttk.Notebook(frameSettings)

# Tab change event.
def tabChangedEvent(event):
	if notebook.index(notebook.select()) == 0:
		# Set render actor visibilities.
#TODO TODO TODO
		model.setOpacity(1)
		model.showBoundingBoxActor()
		model.setBoundingBoxOpacity(.1)
		model.showBoundingBoxTextActor()
		bottomPlate.hideActor()
		modelOverhang.hideActor()
		supports.hideActor()
		slices.hideActor()
#		slices.hideImageActor()
		slicesPrint.hideActor()
	elif notebook.index(notebook.select()) == 1:
		# Recalculate polydata.
		bottomPlate.update(settings)
		modelOverhang.update(settings)
		supports.update(settings)
		# Set render actor visibilities.
		model.showActor()
		model.hideBoundingBoxActor()
		model.hideBoundingBoxTextActor()
		model.setOpacity(0.2)
		modelOverhang.showActor()
		bottomPlate.showActor()
		bottomPlate.setOpacity(1.0)
		supports.showActor()
		supports.setOpacity(1.0)
		slices.hideActor()
#		slices.hideImageActor()
		slicesPrint.hideActor()
		# Enable slice and print tab.
		enableSliceTab()
	elif notebook.index(notebook.select()) == 2:
		# Recalculate polydata.
		bottomPlate.update(settings)
		modelOverhang.update(settings)
		supports.update(settings)
#		slices.update(settings)
		# Update layer slider to account for change in model height.
		updateLayerSlider()
		# Set render actor visibilities.
		model.setOpacity(0.2)
		model.hideBoundingBoxActor()
		model.hideBoundingBoxTextActor()
		bottomPlate.showActor()
		bottomPlate.setOpacity(0.2)
		modelOverhang.hideActor()
		supports.showActor()
		supports.setOpacity(0.2)
		slices.showActor()
#		slices.showImageActor()
		slicesPrint.hideActor()
		sliceView.update(slices.getCvImage())
	elif notebook.index(notebook.select()) == 3:
		# Recalculate polydata.
# TODO: updating her causes projector slice view to be white. Find out why...
#		bottomPlate.update(settings)
#		modelOverhang.update(settings)
#		supports.update(settings)
#		slices.update(settings)
		# Set actor visibilities.
		model.setOpacity(0.2)
		model.hideBoundingBoxActor()
		model.hideBoundingBoxTextActor()
		modelOverhang.hideActor()
		bottomPlate.showActor()
		bottomPlate.setOpacity(0.2)
		supports.showActor()
		supports.setOpacity(0.2)
		slices.hideActor()
#		slices.hideImageActor()
		slicesPrint.showActor()
		updateVolumeLabel()

	view.render()
#	imageView.render()
# Bind event handler to tab change event.
notebook.bind("<<NotebookTabChanged>>", tabChangedEvent)


# Function to enable supports, slice and print tabs.

def enableSupportsTab():
	notebook.tab(1, state="normal")

def enableSliceTab():
	notebook.tab(2, state="normal")
	notebook.tab(3, state="normal")

def disableTabsPrint():
	notebook.tab(0, state="disabled")
	notebook.tab(1, state="disabled")
	notebook.tab(2, state="disabled")

def enableTabsPrint():
	global printingFlag
	notebook.tab(0, state="normal")
	notebook.tab(1, state="normal")
	notebook.tab(2, state="normal")
	# Enable Print button
	buttonPrint.configure(state = "normal")
	printingFlag = False
	# Disable cancel button
	buttonCancel.configure(state = "disabled")
	

# Create model frame. ##########################################################
frameModel = Tkinter.Frame(notebook)

labelModel = Tkinter.Label(frameModel, text='Please load and configure your stl file.', anchor='w', padx=5, pady=5)
labelModel.pack(side='top', fill='x')

frameModelOptions = Tkinter.Frame(frameModel)
frameModelOptions.pack(side='left', fill='both', expand=1, padx=5)

# # # # # # # # # # #
paneModelFile = ttk.Labelframe(frameModelOptions, text='Model file')
paneModelFile.pack(side='top', fill="x")

# File open button.
def callback():
	filenameStl = askopenfilename() 
	# Check if this is a valid stl file name.
	if filenameStl.lower()[-3:] != "stl":
		debugMessage("File \"" + filenameStl + "\" is not an stl file.")
	else:
		# Load new model.
		settings.setFilename(filenameStl)
		# Reset model settings to default.
		settings.resetModelSettings()
		# Reset gui settings to default.
		resetTransform()

		# Load model file with default settings.
		model.loadInputFile(settings)
		# Display the model.
		model.showActor()
		
		# Set slider top value for layer slider according to model height.
		updateLayerSlider()
		
		# Refresh render window.
		view.render()

		# Get filename without path.
		filenameStlParts = settings.getFilename().split('/')
		labelModelFile.configure(text="Model file: " + filenameStlParts[-1])
		debugMessage("Loaded model " + filenameStlParts[-1] + ".")
		
		# Enable support, slice and print tabs.
		enableSupportsTab()

errmsg = 'Error!' #TODO: what is this? 
buttonOpenFile = Tkinter.Button(paneModelFile, text='Load file', command=callback)
buttonOpenFile.pack(side='top')

# Current file label.
labelModelFile = Tkinter.Label(paneModelFile, text="Model file: none")
labelModelFile.pack(side='left', pady=5)

# # # # # # # # # # #
#class guiModelTransform

paneModelModification = ttk.Labelframe(frameModelOptions, text='Model modifications')
paneModelModification.pack(side='top', fill='both', expand=1)

# Event handler for Return and Tab events on model modification text entries.
def callbackTransform(event):
	# Get text entry handles.
	textEntries = [0 for i in range(7)]
	textEntries[0] = entryScaling
	textEntries[1] = entryRotationX
	textEntries[2] = entryRotationY
	textEntries[3] = entryRotationZ
	textEntries[4] = entryPositionX
	textEntries[5] = entryPositionY
	textEntries[6] = entryPositionZ
	
	# Create debug message strings.
	debugStrings = [0 for i in range(7)]
	
	settings.setScaling(float(entryScaling.get()))
	settings.setRotationXYZ((float(entryRotationX.get()), float(entryRotationY.get()), float(entryRotationZ.get())))
	settings.setPositionXYRel((float(entryPositionX.get()), float(entryPositionY.get())))
	settings.setBottomClearance(float(entryPositionZ.get()))

	# Transform model according to settings.
	# Settings are corrected to fit model into build volume if necessary.
	model.update(settings)

	# Update render view.
	view.render()

	# Debug output.
	debugMessage("New scale, rotation and position values:")
	
	# Set text entries if values have changed.
	scaleRotationPositionValues = [settings.getScaling(), settings.getRotationXYZ()[0], settings.getRotationXYZ()[1], settings.getRotationXYZ()[2], settings.getPositionXYRel()[0], settings.getPositionXYRel()[1], settings.getBottomClearance()]
	for i in range(7):
		if float(textEntries[i].get()) > scaleRotationPositionValues[i]:
			textEntries[i].delete(0,Tkinter.END)
			textEntries[i].insert(0,scaleRotationPositionValues[i])
			debugStrings[i] = "limited to "
		elif float(textEntries[i].get()) < scaleRotationPositionValues[i]:
			textEntries[i].delete(0,Tkinter.END)
			textEntries[i].insert(0,scaleRotationPositionValues[i])
			debugStrings[i] = "limited to "
		else:
			debugStrings[i] = "set to "
	
	debugMessage("   Scaling factor " + debugStrings[0] + textEntries[0].get() + ".")
	debugMessage("   Rotation X " + debugStrings[1] + textEntries[1].get() + "°.")
	debugMessage("   Rotation Y " + debugStrings[2] + textEntries[2].get() + "°.")
	debugMessage("   Rotation Z " + debugStrings[3] + textEntries[3].get() + "°.")
	debugMessage("   Position X " + debugStrings[4] + textEntries[4].get() + " %.")
	debugMessage("   Position Y " + debugStrings[5] + textEntries[5].get() + " %.")
	debugMessage("   Position Z " + debugStrings[6] + textEntries[6].get() + " mm.")
	debugMessage("   Model size: " + str(model.getSize()[0]) + ", " + str(model.getSize()[1]) + ", " + str(model.getSize()[2]) + " mm³.")
	


def resetTransform():
	entryScaling.delete(0,Tkinter.END)
	entryScaling.insert(0,settings.getScaling())
	entryRotationX.delete(0,Tkinter.END)
	entryRotationX.insert(0,settings.getRotationXYZ()[0])
	entryRotationY.delete(0,Tkinter.END)
	entryRotationY.insert(0,settings.getRotationXYZ()[1])
	entryRotationZ.delete(0,Tkinter.END)
	entryRotationZ.insert(0,settings.getRotationXYZ()[2])
	entryPositionX.delete(0,Tkinter.END)
	entryPositionX.insert(0,settings.getPositionXYRel()[0])
	entryPositionY.delete(0,Tkinter.END)
	entryPositionY.insert(0,settings.getPositionXYRel()[1])
	entryPositionZ.delete(0,Tkinter.END)
	entryPositionZ.insert(0,settings.getBottomClearance())


# Text entries for model modification.
labelScalingFactor = Tkinter.Label(paneModelModification, text='Scaling', anchor='w')
labelScalingFactor.grid(row=0, column=0, sticky='we')
entryScaling = Tkinter.Entry(paneModelModification)
entryScaling.insert(0,str(settings.getScaling()))
entryScaling.grid(row=0, column=1, sticky='we')
entryScaling.bind("<Return>", callbackTransform)
entryScaling.bind("<KP_Enter>", callbackTransform)
entryScaling.bind("<Tab>", callbackTransform)

labelRotationX = Tkinter.Label(paneModelModification, text='Rotation X [°]', anchor='w')
labelRotationX.grid(row=1, column=0, sticky='we')
entryRotationX = Tkinter.Entry(paneModelModification)
entryRotationX.insert(0, str(settings.getRotationXYZ()[0]))
entryRotationX.grid(row=1, column=1, sticky='we')
entryRotationX.bind("<Return>", callbackTransform)
entryRotationX.bind("<KP_Enter>", callbackTransform)
entryRotationX.bind("<Tab>", callbackTransform)

labelRotationY = Tkinter.Label(paneModelModification, text='Rotation Y [°]', anchor='w')
labelRotationY.grid(row=2, column=0, sticky='we')
entryRotationY = Tkinter.Entry(paneModelModification)
entryRotationY.insert(0, str(settings.getRotationXYZ()[1]))
entryRotationY.grid(row=2, column=1, sticky='we')
entryRotationY.bind("<Return>", callbackTransform)
entryRotationY.bind("<KP_Enter>", callbackTransform)
entryRotationY.bind("<Tab>", callbackTransform)

labelRotationZ = Tkinter.Label(paneModelModification, text='Rotation Z [°]', anchor='w')
labelRotationZ.grid(row=3, column=0, sticky='we')
entryRotationZ = Tkinter.Entry(paneModelModification)
entryRotationZ.insert(0, str(settings.getRotationXYZ()[2]))
entryRotationZ.grid(row=3, column=1, sticky='we')
entryRotationZ.bind("<Return>", callbackTransform)
entryRotationZ.bind("<KP_Enter>", callbackTransform)
entryRotationZ.bind("<Tab>", callbackTransform)

labelPositionX = Tkinter.Label(paneModelModification, text='Position X [%]', anchor='w')
labelPositionX.grid(row=4, column=0, sticky='we')
entryPositionX = Tkinter.Entry(paneModelModification)
entryPositionX.insert(0, str(settings.getPositionXYRel()[0]))
entryPositionX.grid(row=4, column=1, sticky='we')
entryPositionX.bind("<Return>", callbackTransform)
entryPositionX.bind("<KP_Enter>", callbackTransform)
entryPositionX.bind("<Tab>", callbackTransform)

labelPositionY = Tkinter.Label(paneModelModification, text='Position Y [%]', anchor='w')
labelPositionY.grid(row=5, column=0, sticky='we')
entryPositionY = Tkinter.Entry(paneModelModification)
entryPositionY.insert(0, str(settings.getPositionXYRel()[0]))
entryPositionY.grid(row=5, column=1, sticky='we')
entryPositionY.bind("<Return>", callbackTransform)
entryPositionY.bind("<KP_Enter>", callbackTransform)
entryPositionY.bind("<Tab>", callbackTransform)

labelPositionZ = Tkinter.Label(paneModelModification, text='Position Z [mm]', anchor='w')
labelPositionZ.grid(row=6, column=0, sticky='we')
entryPositionZ = Tkinter.Entry(paneModelModification)
entryPositionZ.insert(0, str(settings.getBottomClearance()))
entryPositionZ.grid(row=6, column=1, sticky='we')
entryPositionZ.bind("<Return>", callbackTransform)
entryPositionZ.bind("<KP_Enter>", callbackTransform)
entryPositionZ.bind("<Tab>", callbackTransform)



# Create supports frame. #######################################################
frameSupports = Tkinter.Frame(notebook)

labelSupports = Tkinter.Label(frameSupports, text='Please configure the support pattern and geometry.', anchor='w', padx=5, pady=5)
labelSupports.pack(side='top', fill='x')

# # # # # # # # # # #
paneSupportPattern = ttk.Labelframe(frameSupports, text='Support pattern')
paneSupportPattern.pack(side='top', fill="x", padx=5)

labelSupportOverhangAngle = Tkinter.Label(paneSupportPattern, text='Overhang angle [°]', anchor='w')
labelSupportOverhangAngle.grid(row=0, column=0, sticky='we')

def setSupportParameters(event):
	# TODO TODO TODO: Limits.
	# Modify settings according to input.
	settings.setOverhangAngle( float(entrySupportOverhangAngle.get()) )
	settings.setSupportSpacingXY( [ float(entrySupportSpacingX.get()),  float(entrySupportSpacingY.get()) ] )
	settings.setSupportBaseDiameter( float(entrySupportBaseDiameter.get()) )
	settings.setSupportTipDiameter( float(entrySupportTipDiameter.get()) )
	settings.setSupportTipHeight( float(entrySupportTipHeight.get()) )
	settings.setSupportMaxHeight( float(entrySupportMaxHeight.get()) )
	
	entrySupportMaxHeight.delete(0,Tkinter.END)
	entrySupportMaxHeight.insert(0,str(settings.getSupportMaxHeight()))
	
	# Update overhang model.
	modelOverhang.update(settings)#settings)#.getOverhangAngle)

	# Update supports.	
	supports.update(settings)#modelOverhang.getPolydata(), settings.getSupportSpacingXY()[0], settings.getSupportSpacingXY()[1], settings.getSupportTipDiameter(), settings.getSupportBaseDiameter(), settings.getSupportTipHeight())
	
	view.render()
	debugMessage("Support overhang angle to " + entrySupportOverhangAngle.get() + "°.")
	debugMessage("Support spacing X set to " + entrySupportSpacingX.get() + " mm.")
	debugMessage("Support spacing Y set to " + entrySupportSpacingY.get() + " mm.")
	debugMessage("Support maximum height set to " + str(settings.getSupportMaxHeight()) + " mm.")
	debugMessage("Support base diameter set to " + entrySupportBaseDiameter.get() + " mm.")
	debugMessage("Support tip diameter set to " + entrySupportTipDiameter.get() + " mm.")
	debugMessage("Support cone height set to " + entrySupportTipHeight.get() + " mm.")


entrySupportOverhangAngle = Tkinter.Entry(paneSupportPattern)
entrySupportOverhangAngle.insert(0, str(settings.getOverhangAngle()))
entrySupportOverhangAngle.grid(row=0, column=1, sticky='we')
entrySupportOverhangAngle.bind("<Return>", setSupportParameters)
entrySupportOverhangAngle.bind("<KP_Enter>", setSupportParameters)
entrySupportOverhangAngle.bind("<Tab>", setSupportParameters)

labelSupportSpacingX = Tkinter.Label(paneSupportPattern, text='Spacing X [mm]', anchor='w')
labelSupportSpacingX.grid(row=1, column=0, sticky='we')
entrySupportSpacingX = Tkinter.Entry(paneSupportPattern)
entrySupportSpacingX.insert(0, str(settings.getSupportSpacingXY()[0]))
entrySupportSpacingX.grid(row=1, column=1, sticky='we')
entrySupportSpacingX.bind("<Return>", setSupportParameters)
entrySupportSpacingX.bind("<KP_Enter>", setSupportParameters)
entrySupportSpacingX.bind("<Tab>", setSupportParameters)

labelSupportSpacingY = Tkinter.Label(paneSupportPattern, text='Spacing Y [mm]', anchor='w')
labelSupportSpacingY.grid(row=2, column=0, sticky='we')
entrySupportSpacingY = Tkinter.Entry(paneSupportPattern)
entrySupportSpacingY.insert(0, str(settings.getSupportSpacingXY()[1]))
entrySupportSpacingY.grid(row=2, column=1, sticky='we')
entrySupportSpacingY.bind("<Return>", setSupportParameters)
entrySupportSpacingY.bind("<KP_Enter>", setSupportParameters)
entrySupportSpacingY.bind("<Tab>", setSupportParameters)

labelSupportMaxHeight = Tkinter.Label(paneSupportPattern, text='Maximum support height [mm]', anchor='w')
labelSupportMaxHeight.grid(row=3, column=0, sticky='we')
entrySupportMaxHeight = Tkinter.Entry(paneSupportPattern)
entrySupportMaxHeight.insert(0, str(settings.getSupportMaxHeight()))
entrySupportMaxHeight.grid(row=3, column=1, sticky='we')
entrySupportMaxHeight.bind("<Return>", setSupportParameters)
entrySupportMaxHeight.bind("<KP_Enter>", setSupportParameters)
entrySupportMaxHeight.bind("<Tab>", setSupportParameters)

# # # # # # # # # # #
paneSupportGeometry = ttk.Labelframe(frameSupports, text='Support geometry')
paneSupportGeometry.pack(side='top', fill="x", padx=5)

labelSupportBaseDiameter = Tkinter.Label(paneSupportGeometry, text='Base diameter [mm]', anchor='w')
labelSupportBaseDiameter.grid(row=0, column=0, sticky='we')
entrySupportBaseDiameter = Tkinter.Entry(paneSupportGeometry)
entrySupportBaseDiameter.insert(0, str(settings.getSupportBaseDiameter()))
entrySupportBaseDiameter.grid(row=0, column=1, sticky='we')
entrySupportBaseDiameter.bind("<Return>", setSupportParameters)
entrySupportBaseDiameter.bind("<KP_Enter>", setSupportParameters)
entrySupportBaseDiameter.bind("<Tab>", setSupportParameters)

labelSupportTipDiameter = Tkinter.Label(paneSupportGeometry, text='Tip diameter [mm]', anchor='w')
labelSupportTipDiameter.grid(row=1, column=0, sticky='we')
entrySupportTipDiameter = Tkinter.Entry(paneSupportGeometry)
entrySupportTipDiameter.insert(0, str(settings.getSupportTipDiameter()))
entrySupportTipDiameter.grid(row=1, column=1, sticky='we')
entrySupportTipDiameter.bind("<Return>", setSupportParameters)
entrySupportTipDiameter.bind("<KP_Enter>", setSupportParameters)
entrySupportTipDiameter.bind("<Tab>", setSupportParameters)

labelSupportTipHeight = Tkinter.Label(paneSupportGeometry, text='Cone height [mm]', anchor='w')
labelSupportTipHeight.grid(row=2, column=0, sticky='we')
entrySupportTipHeight = Tkinter.Entry(paneSupportGeometry)
entrySupportTipHeight.insert(0, str(settings.getSupportTipHeight()))
entrySupportTipHeight.grid(row=2, column=1, sticky='we')
entrySupportTipHeight.bind("<Return>", setSupportParameters)
entrySupportTipHeight.bind("<KP_Enter>", setSupportParameters)
entrySupportTipHeight.bind("<Tab>", setSupportParameters)



# # # # # # # # # # #
paneSupportBottomPlate = ttk.Labelframe(frameSupports, text='Support bottom plate')
paneSupportBottomPlate.pack(side='top', fill="x", padx=5)

labelSupportBottomPlateThickness = Tkinter.Label(paneSupportBottomPlate, text='Thickness [mm]', anchor='w')
labelSupportBottomPlateThickness.grid(row=0, column=0, sticky='we')

def setSupportBottomPlateThickness(event):
	settings.setBottomPlateThickness( float(entrySupportBottomPlateThickness.get()) )
	# Adjust bottom plate accordingly.
	bottomPlate.update(settings)
#	bottomPlate.setSize(model.getSize()[0], model.getSize()[1], bottomPlateThickness, model.getCenter()[0], model.getCenter()[1], bottomPlateThickness/2.0)
	debugMessage("Support bottom plate thickness set to " + str(settings.getBottomPlateThickness()) + " mm.")
	entrySupportBottomPlateThickness.delete(0,Tkinter.END)
	entrySupportBottomPlateThickness.insert(0,settings.getBottomPlateThickness())
	view.render()

entrySupportBottomPlateThickness = Tkinter.Entry(paneSupportBottomPlate)
entrySupportBottomPlateThickness.insert(0, str(settings.getBottomPlateThickness()))
entrySupportBottomPlateThickness.grid(row=0, column=1, sticky='we')
entrySupportBottomPlateThickness.bind("<Return>", setSupportBottomPlateThickness)
entrySupportBottomPlateThickness.bind("<KP_Enter>", setSupportBottomPlateThickness)
entrySupportBottomPlateThickness.bind("<Tab>", setSupportBottomPlateThickness)

labelSupportBottomPlateBorder = Tkinter.Label(paneSupportBottomPlate, text='Border width [mm]', anchor='w')
labelSupportBottomPlateBorder.grid(row=2, column=0, sticky='we')

def setSupportBottomPlateBorder(event):
	debugMessage("Bottom plate border is not supported yet...")

entrySupportBottomPlateBorder = Tkinter.Entry(paneSupportBottomPlate)
entrySupportBottomPlateBorder.insert(10,"Not supported yet...")
entrySupportBottomPlateBorder.grid(row=2, column=1, sticky='we')
entrySupportBottomPlateBorder.bind("<Return>", setSupportBottomPlateBorder)
entrySupportBottomPlateBorder.bind("<KP_Enter>", setSupportBottomPlateBorder)
entrySupportBottomPlateBorder.bind("<Tab>", setSupportBottomPlateBorder)



# Create slicing frame. ########################################################
frameSlicing = Tkinter.Frame(notebook)

labelSlicing = Tkinter.Label(frameSlicing, text='Please configure the slicing settings.', anchor='w', padx=5, pady=5)
labelSlicing.pack(side='top', fill='x')

# # # # # # # # # # #
paneSlicingLayerHeight = ttk.Labelframe(frameSlicing, text='Slicing parameters')
paneSlicingLayerHeight.pack(side='top', fill="x", padx=5)


labelLayerHeight = Tkinter.Label(paneSlicingLayerHeight, text='Layer height [mm]', anchor='w')
labelLayerHeight.grid(row=2, column=0, sticky='we')

def setLayerHeight(event):
	settings.setLayerHeight(float(entryLayerHeight.get()))
#TODO: limits.
	debugMessage("Layer height set to " + entryLayerHeight.get() + " mm.")
	updateLayerSlider()
	view.render()

entryLayerHeight = Tkinter.Entry(paneSlicingLayerHeight)
entryLayerHeight.insert(0, str(settings.getLayerHeight()))
entryLayerHeight.grid(row=2, column=1, sticky='we')
entryLayerHeight.bind("<Return>", setLayerHeight)
entryLayerHeight.bind("<KP_Enter>", setLayerHeight)
entryLayerHeight.bind("<Tab>", setLayerHeight)

# # # # # # # # # # #
paneSlicingFill = ttk.Labelframe(frameSlicing, text='Fill parameters')
paneSlicingFill.pack(side='top', fill="x", padx=5)



def callbackCheckbuttonHollow():
	if hollow.get()==1 :
		settings.setHollow(True)
#		checkbuttonFillShow.configure(state='normal')
		checkbuttonFill.configure(state='normal')
	else:
		# Adjust settings object.
		settings.setHollow(False)
		settings.setFill(False)
#		settings.setFillShow(False)
		# Adjust other checkbutton values.
		fill.set(False)
#		fillShow.set(False)
		# Adjust other checkbotton states.
		checkbuttonFill.configure(state='disabled')
#		checkbuttonFillShow.configure(state='disabled')
		# Adjust entry state. TODO
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	sliceView.update(slices.getCvImage())

hollow = Tkinter.IntVar()
checkbuttonHollow = Tkinter.Checkbutton(paneSlicingFill, text='Print hollow?', variable=hollow, command=callbackCheckbuttonHollow)
checkbuttonHollow.grid(row=0, column=0, sticky='w')
hollow.set(True)




def callbackCheckbuttonFill():
	if fill.get()==1 :
		settings.setFill(True)
#		checkbuttonFillShow.configure(state='normal')
	else:
		settings.setFill(False)
#		settings.setFillShow(False)
#		fillShow.set(False)
#		checkbuttonFillShow.configure(state='disabled')
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	sliceView.update(slices.getCvImage())

fill = Tkinter.IntVar()
checkbuttonFill = Tkinter.Checkbutton(paneSlicingFill, text='Use fill structures?', variable=fill, command=callbackCheckbuttonFill)
checkbuttonFill.grid(row=1, column=0, sticky='w')
fill.set(True)


#def callbackCheckbuttonFillShow():
#	if fillShow.get()==True :
#		settings.setFillShow(True)
#	else:
#		settings.setFillShow(False)
#	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
#	sliceView.update(slices.getCvImage())

#fillShow = Tkinter.IntVar()
#checkbuttonFillShow = Tkinter.Checkbutton(paneSlicingFill, text='Show fill structures? (slow...)', variable=fillShow, command=callbackCheckbuttonFillShow)
#checkbuttonFillShow.grid(row=2, column=0, sticky='w')
#fillShow.set(True)

def callbackShellThickness(event):
	# Set value to settings object.
	settings.setShellThickness(float(entryShellThickness.get()))
	# Update slice object and redraw slice view.
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	sliceView.update(slices.getCvImage())
	# Set text entry if limits have been applied by slice object.
	entryShellThickness.delete(0,Tkinter.END)
	entryShellThickness.insert(0,settings.getShellThickness())


labelShellThickness = Tkinter.Label(paneSlicingFill, text='Shell thickness [mm]', anchor='w')
labelShellThickness.grid(row=3, column=0, sticky='we')
entryShellThickness = Tkinter.Entry(paneSlicingFill)
entryShellThickness.insert(0, str(settings.getShellThickness()))
entryShellThickness.grid(row=3, column=1, sticky='we')
entryShellThickness.bind("<Return>", callbackShellThickness)
entryShellThickness.bind("<KP_Enter>", callbackShellThickness)
entryShellThickness.bind("<Tab>", callbackShellThickness)

def callbackFillSpacing(event):
	# Set value to settings object.
	settings.setFillSpacing(float(entryFillSpacing.get()))
	# Update slice object and redraw slice view.
	slices.updateFillPattern()
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	sliceView.update(slices.getCvImage())
	# Set text entry if limits have been applied by slice object.
	entryFillSpacing.delete(0,Tkinter.END)
	entryFillSpacing.insert(0,settings.getFillSpacing())


labelFillSpacing = Tkinter.Label(paneSlicingFill, text='Fill spacing [mm]', anchor='w')
labelFillSpacing.grid(row=4, column=0, sticky='we')
entryFillSpacing = Tkinter.Entry(paneSlicingFill)
entryFillSpacing.insert(0, str(settings.getFillSpacing()))
entryFillSpacing.grid(row=4, column=1, sticky='we')
entryFillSpacing.bind("<Return>", callbackFillSpacing)
entryFillSpacing.bind("<KP_Enter>", callbackFillSpacing)
entryFillSpacing.bind("<Tab>", callbackFillSpacing)

def callbackFillWallThickness(event):
	# Set value to settings object.
	settings.setFillWallThickness(float(entryFillWallThickness.get()))
	# Update slice object and redraw slice view.
	slices.updateFillPattern()
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	sliceView.update(slices.getCvImage())
	# Set text entry if limits have been applied by slice object.
	entryFillWallThickness.delete(0,Tkinter.END)
	entryFillWallThickness.insert(0,settings.getFillWallThickness())

labelFillWallThickness = Tkinter.Label(paneSlicingFill, text='Fill wall thickness [mm]', anchor='w')
labelFillWallThickness.grid(row=5, column=0, sticky='we')
entryFillWallThickness = Tkinter.Entry(paneSlicingFill)
entryFillWallThickness.insert(0, str(settings.getFillWallThickness()))
entryFillWallThickness.grid(row=5, column=1, sticky='we')
entryFillWallThickness.bind("<Return>", callbackFillWallThickness)
entryFillWallThickness.bind("<KP_Enter>", callbackFillWallThickness)
entryFillWallThickness.bind("<Tab>", callbackFillWallThickness)



# # # # # # # # # # #
paneCurrentSlice = ttk.Labelframe(frameSlicing, text='Current layer')
paneCurrentSlice.pack(side='top', fill="x", padx=5)

# Layer slider.
# Function to set max value according to current model.
def updateLayerSlider():
	sliderCurrentLayer.configure(to=slices.getNumberOfSlices(), tickinterval=slices.getNumberOfSlices() / 10)

	
# Callback function.
def setLayer(event): #TODO: Check if current layer should start at 1 or 0.
	slices.update(settings.getLayerHeight(), int(sliderCurrentLayer.get()))
	view.render()
	sliceView.update(slices.getCvImage())


# Create slider.
sliderCurrentLayer = Tkinter.Scale(paneCurrentSlice, from_=1, to=1, orient=Tkinter.HORIZONTAL, command=setLayer)
sliderCurrentLayer.set(1)
sliderCurrentLayer.pack(side='top', fill="x",expand = 1)

# Add image preview.
#imageView = modelHandling.imageViewer(frameSlicing, 200, 200)
#imageView.addRenderActor(slices.getImageActor())
#slices.hideImageActor()
#imageView.render()

sliceView = modelHandling.imageViewerTkinter(frameSlicing,frameSettingsWidth, int(frameSettingsWidth/1.77777))
sliceView.pack(side='top',expand=1, fill='both', padx=5)
sliceView.setBlack()


## Add Tkinter image widget for openCv image.
## Convert the Image object into a TkPhoto object
#img = numpy.ones((settings.getProjectorSizeXY()[0], settings.getProjectorSizeXY()[1], 3), numpy.uint8)
#img *= [255, 0, 0]
#im = Image.fromarray(img)
#imResized = im.resize((240,135),Image.ANTIALIAS)
#sliceImage = ImageTk.PhotoImage(image=imResized) 
#
## Put it in the display window
#sliceLabel = Tkinter.Label(frameSlicing, padx = 5, pady = 5,text='test', image=sliceImage)
#sliceLabel.image = sliceImage
#sliceLabel.pack(side = 'top') 
# Create printing frame. ########################################################
framePrinting = Tkinter.Frame(notebook)

labelPrint = Tkinter.Label(framePrinting, text='Please fill the VAT with a sufficient amount of resin.', anchor='w', padx=5, pady=5)
labelPrint.pack(side='top', fill='x')

panePrintSettings = ttk.Labelframe(framePrinting, text='Print settings')
panePrintSettings.pack(side='top', fill="x", padx=5)

def setPrintSettings(event):
	settings.setExposureTime(float(entryExposureTime.get()))
	settings.setExposureTimeBase(float(entryExposureTimeBase.get()))
	settings.setSettleTime(float(entrySettleTime.get()))
	
	# Reset entries in case of limits.
	entryExposureTime.delete(0,Tkinter.END)
	entryExposureTime.insert(0, str(settings.getExposureTime()))
	entryExposureTimeBase.delete(0,Tkinter.END)
	entryExposureTimeBase.insert(0, str(settings.getExposureTimeBase()))
	entrySettleTime.delete(0,Tkinter.END)
	entrySettleTime.insert(0, str(settings.getSettleTime()))
#TODO: limits.
	debugMessage("Exposure time set to " + entryExposureTime.get() + " mm.")
	debugMessage("Exposure time base set to " + entryExposureTimeBase.get() + " mm.")
	debugMessage("Settle time set to " + entrySettleTime.get() + " mm.")

labelExposureTimeBase = Tkinter.Label(panePrintSettings, text='Exposure time base [s]', anchor='w')
labelExposureTimeBase.grid(row=0, column=0, sticky='we')
entryExposureTimeBase = Tkinter.Entry(panePrintSettings)
entryExposureTimeBase.insert(0, str(settings.getExposureTimeBase()))
entryExposureTimeBase.grid(row=0, column=1, sticky='we')
entryExposureTimeBase.bind("<Return>", setPrintSettings)
entryExposureTimeBase.bind("<KP_Enter>", setPrintSettings)
entryExposureTimeBase.bind("<Tab>", setPrintSettings)

labelExposureTime = Tkinter.Label(panePrintSettings, text='Exposure time [s]', anchor='w')
labelExposureTime.grid(row=1, column=0, sticky='we')
entryExposureTime = Tkinter.Entry(panePrintSettings)
entryExposureTime.insert(0, str(settings.getExposureTime()))
entryExposureTime.grid(row=1, column=1, sticky='we')
entryExposureTime.bind("<Return>", setPrintSettings)
entryExposureTime.bind("<KP_Enter>", setPrintSettings)
entryExposureTime.bind("<Tab>", setPrintSettings)

labelSettleTime = Tkinter.Label(panePrintSettings, text='Resin settle time [s]', anchor='w')
labelSettleTime.grid(row=2, column=0, sticky='we')
entrySettleTime = Tkinter.Entry(panePrintSettings)
entrySettleTime.insert(0, str(settings.getSettleTime()))
entrySettleTime.grid(row=2, column=1, sticky='we')
entrySettleTime.bind("<Return>", setPrintSettings)
entrySettleTime.bind("<KP_Enter>", setPrintSettings)
entrySettleTime.bind("<Tab>", setPrintSettings)


panePrintVolume = ttk.Labelframe(framePrinting, text='Amount of resin needed')
panePrintVolume.pack(side='top', fill="x", padx=5, pady=10)

labelPrintVolume = Tkinter.Label(panePrintVolume, text='Volume:', anchor='w')
labelPrintVolume.pack(side='left', padx=5, expand=1, fill='both')

def updateVolumeLabel():
	labelPrintVolume.configure(text="Volume: %6.2f ml" %(model.getVolume()/1000+50))

panePrint = ttk.Labelframe(framePrinting, text='Print control')
panePrint.pack(side='top', fill="x", padx=5)


## Print start button
def callbackPrintStart():
	result = 0
	
	# Open dialogue.
	dialogue = startPrintDialogue(root, result, title="Ready to print?")
	print dialogue.getValue()
	global projector
	global printingFlag
	if dialogue.getValue() == 1:
		# Check if print running and start if not.
		# Disable model, supports and slicing tabs.
		disableTabsPrint()
		if not projector:
			projector = projectorDisplay(root, view, sliceViewPrint, settings, slicesPrint, progressBar, console, enableTabsPrint)
		
		# Enable cancel button
		buttonCancel.configure(state = "normal")

		# Disable Print button
		buttonPrint.configure(state = "disabled")
		
		# Set printing flag.
		printingFlag = True
			
			

buttonPrint = Tkinter.Button(panePrint, text='Print!', command=callbackPrintStart)
buttonPrint.pack(side='left')

## Print stop button
def callbackPrintStop():
	if tkMessageBox.askyesno("Cancel print", "Do you want to cancel the print?"):
		# Disable cancel button
		buttonCancel.configure(state = "disabled")


		global projector
		# Check if print running and stop if true.
		if projector:
			# Start projector window and print thread
			projector.stop()
			projector = None			

		
		
		


buttonCancel = Tkinter.Button(panePrint, text='Cancel', command=callbackPrintStop, state = "disabled")
buttonCancel.pack(side='left')


# Progress bar and status stuff. ########################################
class progressBar(Tkinter.Frame):
	def __init__(self, parent):
		Tkinter.Frame.__init__(self, parent)
#		self.frame = Tkinter.Frame(self,parent)
		self.labelRemainingTime = Tkinter.Label(self, text='Remaining time: --:-- [hh:mm]', anchor='w')
		self.labelRemainingTime.pack(side='bottom', padx=5, expand=1, fill='both')
		self.labelPrintStatus = Tkinter.Label(self, text='Status: idle', anchor='w')
		self.labelPrintStatus.pack(side='bottom', padx=5, expand=1, fill='both')
		self.progressbar = ttk.Progressbar(self, orient=Tkinter.HORIZONTAL, length=200, mode='determinate')#, variable=self.progress, maximum=self.endTime)
		self.progressbar.pack(side='bottom')
#		self.frame.pack()
	
	def setStatus(self, status, time="--:--"):
		self.labelPrintStatus.configure(text='Status: ' + status)
		self.labelRemainingTime.configure(text=("Remaining time [hh:mm]: " + time))

	def setProgress(self, progress, maximum):
		self.progressbar.configure(maximum=maximum)
		self.progressbar.configure(value=progress)
		#progressbar.step()

progressBar = progressBar(panePrint)
progressBar.pack(side='right', expand=1)

sliceViewPrint = modelHandling.imageViewerTkinter(framePrinting, frameSettingsWidth, int(frameSettingsWidth/1.77777))
sliceViewPrint.pack(side='bottom',expand=1,fill='both', padx=5)
sliceViewPrint.setBlack()




# Start print dialogue. ########################################################
class startPrintDialogue(Tkinter.Toplevel):
	def __init__(self, parent, result=0, title=None):
		Tkinter.Toplevel.__init__(self, parent)
		
		self.result = result
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
		self.transient(parent)
		
		# Window title if supplied.
		if title:
			self.title(title)
		
		self.parent = parent
		self.result = None
		
		# Construct frame.
		body = Tkinter.Frame(self)
		#Set focus.
		self.initial_focus = self.body(body)
		body.pack(padx=5, pady=5)
		
		# Create checkboxes.
		self.checkboxes()
		
		# Make modal (what is this?)
		self.grab_set()
		
		# Set focus again (why?)
		if not self.initial_focus:
			self.initial_focus = self
		
		# Handle close button.
		self.protocol("WM_DELETE_WINDOW", self.cancel)
		
		# Set position relative to parent.
#		self.geometry("+ %d + %d" (parent.winfo_rootx+50, parent.winfo_rooty+50))
		
		self.initial_focus.focus_set()
		
		# Wait for user interaction.
		self.wait_window(self)
		
	def body(self,master):
		pass
	
	# Checkboxes.
	def checkboxes(self):
		box = Tkinter.Frame(self)
		self.resin = Tkinter.IntVar()
		self.buildPlatform = Tkinter.IntVar()
		self.otherCondition = Tkinter.IntVar()
		c1 = Tkinter.Checkbutton(box, text='VAT filled with resin?', variable=self.resin, command=self.checkboxCallback)
		c1.pack(side='top', padx=5, pady=5)
		c2 = Tkinter.Checkbutton(box, text='Build platform clean?', variable=self.buildPlatform, command=self.checkboxCallback)
		c2.pack(side='top', padx=5, pady=5)
		c3 = Tkinter.Checkbutton(box, text='Everything else OK?', variable=self.otherCondition, command=self.checkboxCallback)
		c3.pack(side='top', padx=5, pady=5)
						
		self.buttonOk = Tkinter.Button(box, text="OK", width=10, command=self.ok, state=Tkinter.DISABLED)
		self.buttonOk.pack(side='left', padx=5, pady=5)
		self.buttonCancel = Tkinter.Button(box, text="Cancel", width=10, command=self.cancel)
		self.buttonCancel.pack(side='left', padx=5, pady=5)
		
		self.bind("<Return>", self.ok)
		self.bind("<Escape>", self.cancel)
		
		box.pack()
	
	def checkboxCallback(self):
			if self.resin.get()==1 and self.buildPlatform.get()==1 and self.otherCondition.get()==1:
				self.buttonOk.configure(state=Tkinter.NORMAL)
			else:
				self.buttonOk.configure(state=Tkinter.DISABLED)
	
	# Button actions.
	def ok(self, event=None):
		if not self.validate():
			self.initial_focus.focus_set() # put focus back
			return
		# Hide dialogue.
		self.withdraw()
		self.update_idletasks()	# What the ...?
		
		# Set values.
		self.apply()
		
		self.result = 1
		
		# Close dialogue.
		self.parent.focus_set()
		self.destroy()
		
	def cancel(self, event=None):
		self.result = 0
		# Focus back to parent.
		self.parent.focus_set()
		self.destroy()
	
	# Command hooks.
	def validate(self):
		return 1	#override
	def apply(self):
		pass	#override
	
	def getValue(self):
		return self.result



	

	
class projectorDisplay:
	def __init__(self, parent, parentView, parentSliceView, settings, slicesPrint, progressBar, console, guiResetFunction):
		# Queue to communicate between print thread and slice display in GUI.
		self.queueSliceNumber = Queue.Queue(maxsize=1)
		self.queueStatus = Queue.Queue(maxsize=1)
		self.parent = parent
		self.settings = settings
		self.parentView = parentView
		self.parentSliceView = parentSliceView
		self.console = console
		self.guiResetFunction = guiResetFunction
		self.currentSlice = 1	# TODO: Check if this should be 0 instead...
		self.remainingTime = 0
		self.startTime = 0
		self.timeString = "--:--"
		
#		self.slices = slices
		self.progressBar = progressBar
		self.pollInterval = 100 #ms
		self.printWindow = Tkinter.Toplevel(parent)
		self.printWindow.withdraw()
		self.printWindow.overrideredirect(1)
		self.printWindow.wm_deiconify()		#TODO: this came after geometry. check if it is ok here.
		if self.settings.getDebugStatus():
			self.printWindow.geometry("%ix%i+%i+%i" % (self.settings.getProjectorSizeXYDebug()[0], self.settings.getProjectorSizeXYDebug()[1], self.settings.getProjectorPositionXYDebug()[0], self.settings.getProjectorPositionXY()[1]) ) #("100x50+800+200")#("1920x1080+1280+0")	# TODO: get from settings!
		else:
			self.printWindow.geometry("%ix%i+%i+%i" % (self.settings.getProjectorSizeXY()[0], self.settings.getProjectorSizeXY()[1], self.settings.getProjectorPositionXY()[0], self.settings.getProjectorPositionXY()[1]) ) #("100x50+800+200")#("1920x1080+1280+0")	# TODO: get from settings!

		# Create image viewer for slices.
#		self.sliceView = modelHandling.imageViewer(self.printWindow,  self.settings.getProjectorSizeXY()[0], self.settings.getProjectorSizeXY()[1], (0,0,0)) #black background
		if self.settings.getDebugStatus():
			self.sliceImageView = modelHandling.imageViewerTkinter(self.printWindow, viewWidth=self.settings.getProjectorSizeXYDebug()[0], viewHeight=self.settings.getProjectorSizeXYDebug()[1])
		else:
			self.sliceImageView = modelHandling.imageViewerTkinter(self.printWindow, viewWidth=self.settings.getProjectorSizeXY()[0], viewHeight=self.settings.getProjectorSizeXY()[1])
		self.sliceImageView.pack()
#		self.slices.update(self.settings.getLayerHeight(), self.currentSlice)
		slicesPrint.updateFillPattern()
		slicesPrint.update(self.settings.getLayerHeight(), self.currentSlice)
		self.sliceImageView.setBlack()
		# Reset render view in main window.
		self.parentView.render()
#		self.sliceView.addRenderActor(slicesPrint.getImageActor())
#		slicesPrint.hideImageActor()
#		self.sliceView.render()
#TODO: handle restarting the print		
		#Start thread
#		self.wait = waitExposure(self.settings, self.queueSliceNumber, self.queueStatus, self.slices.getNumberOfSlices())
		self.wait = waitExposure(self.settings, self.queueSliceNumber, self.queueStatus, slicesPrint.getNumberOfSlices(), self.console)
		self.pollPrintProcess()
		self.wait.start()


	def stop(self):
		# Stop thread
		self.wait.stop()

	
	def pollPrintProcess(self):
		if self.wait:
			# Check slice number queue.
			if self.queueSliceNumber.qsize():
				self.currentSlice = self.queueSliceNumber.get()
				if self.currentSlice == -1:
					self.console.message("Display black.")
#					self.slices.hideImageActor()
					self.sliceImageView.setBlack()
					self.parentSliceView.setBlack()
#					slicesPrint.hideImageActor()
#					self.sliceView.render()
				else:
					if self.currentSlice==1:
						self.startTime = time.time()
						self.timeString = "--:--"
					else:
						self.timeRemaining = ((time.time() - self.startTime) / self.currentSlice) * (slicesPrint.getNumberOfSlices()-self.currentSlice)
						m, s = divmod(self.timeRemaining, 60)
						h, m = divmod(m, 60)
						self.timeString = ("%2d:%2d" %(h, m))
#					self.slices.update(self.settings.getLayerHeight(), self.currentSlice)
					slicesPrint.update(self.settings.getLayerHeight(), self.currentSlice)
#					self.slices.showImageActor()
#					slicesPrint.showImageActor()
					self.sliceImageView.update(slicesPrint.getCvImage())
					self.parentView.render()
					self.parentSliceView.update(slicesPrint.getCvImage())
#					self.sliceView.render()
					# Update layer slider to account for change in model height.
#					self.progressBar.setStatus("Printing slice " + str(self.currentSlice) + " of " + str(self.slices.getNumberOfSlices()) + ".")
					self.progressBar.setStatus(("Printing slice " + str(self.currentSlice) + " of " + str(slicesPrint.getNumberOfSlices()) + "."), self.timeString)
#					self.progressBar.setProgress(self.currentSlice,self.slices.getNumberOfSlices())
					self.progressBar.setProgress(self.currentSlice,slicesPrint.getNumberOfSlices())
			if self.queueStatus.qsize():
				self.status = self.queueStatus.get()
				if self.status == "Destroy":
					print "Print process stopped."
					# Close image renderer.
					self.sliceImageView.destroy()
					# Close slice display window.
					self.printWindow.destroy()
					self.wait = None
					self.progressBar.setStatus("Idle.")
					self.progressBar.setProgress(0,100)
					self.guiResetFunction()
		#			self.destroy()

				else:
					self.progressBar.setStatus(self.status, self.timeString)
			
			
				
			# Put control back to gui and call method again after interval seconds.
			self._poll_job_id = self.parent.after(self.pollInterval, self.pollPrintProcess)
		
	
class waitExposure(threading.Thread):

	def __init__(self, settings, queueSliceNumber, queueStatus, numberOfSlices, console):
		# Internalise variables
		self.numberOfSlices = numberOfSlices
		self.settings = settings
		self.console = console
		self.queueSliceNumber = queueSliceNumber
		self.queueStatus = queueStatus
		super(waitExposure, self).__init__()	# Calls base class init function for us.
		self.__stop = threading.Event()

		self.stopFlag = False	# Flag to signal stop event to loop.

		# Initialise printer.
		if self.queueStatus.empty():
				self.queueStatus.put("Initialising printer.")
		self.slice = 1
		self.consoleMessage("Starting printer communication.")
		# Serial communication
		if not self.settings.getDebugStatus():
			# Printer serial.
			self.serialPrinter = serialCommunication.serialPrinter(self.settings)
			if self.serialPrinter.ping() != 1:
				self.consoleMessage("Communication to printer not established!")
			else:
				self.consoleMessage("Communication to printer established!")
			# Projector serial
			self.serialProjector = serialCommunication.serialProjector()


	def stop(self):
		self.consoleMessage("Waiting to finish slice.")
		if self.queueStatus.empty():
			self.queueStatus.put("Waiting to finish slice.")
		# Stop printer process by setting stop flag.
		self.stopFlag = True

		
	
	def stopped(self):
		return self.__stop.isSet()
		
	def wait(self, timeInterval):
		timeCount = 0
		timeStart = time.time()
		while timeCount < timeInterval:
			time.sleep(.1)
			timeCount = time.time() - timeStart
	
	def run(self):
		# Print process:
		# 	Homing build platform.
		#	Start slice projection with black image.
		#	Activating projector.
		#	Tilting for bubbles.
		#	Start loop.

		# Activate projector.
		self.consoleMessage("Activating projector.")
		# Send status string to gui.
		if self.queueStatus.empty():
			self.queueStatus.put("Activating projector.")
		# Display black.
		if self.queueSliceNumber.empty():
			self.queueSliceNumber.put(-1)
			# Activate projector.
		if not self.settings.getDebugStatus():
			self.serialProjector.activate()


		# Homing build platform.
		self.consoleMessage("Homing build platform.")
		# Send status string to gui.
		if self.queueStatus.empty():
			self.queueStatus.put("Homing build platform.")
		# Send printer command.
		if not self.settings.getDebugStatus():
			self.serialPrinter.buildHome()


		# Tilt to get rid of bubbles.
		if not self.settings.getDebugStatus():
			self.consoleMessage("Tilting to get rid of bubbles.")
			# Send status string to gui.
			if self.queueStatus.empty():
				self.queueStatus.put("Removing bubbles.")
			for tilts in range(5):
				print str(tilts+1) + " of 5."
				self.serialPrinter.tilt()
		
		# Wait for resin to settle.
		self.consoleMessage("Waiting " + str(self.settings.getSettleTime()) + " seconds for resin to settle.")
		# Send status string to gui.
		if self.queueStatus.empty():
			self.queueStatus.put("Waiting " + str(self.settings.getSettleTime()) + " seconds for resin to settle.")
#		time.sleep(self.settings.getSettleTime())
		self.wait(self.settings.getSettleTime())

		# Reset slice.
		self.slice = 1
		
		# Send number of slices to printer.
		if not self.settings.getDebugStatus():
			self.serialPrinter.setNumberOfSlices(self.numberOfSlices)
		
		# Send printing flag to printer.
		if not self.settings.getDebugStatus():
			self.serialPrinter.setStart()
		self.exposureTime = 5.
		
		while not self.stopFlag and self.slice < self.numberOfSlices+1:
			self.consoleMessage("Printing slice " + str(self.slice) + ".")
			# Send slice number to printer.
			if not self.settings.getDebugStatus():
				self.serialPrinter.setCurrentSlice(self.slice)
			#TODO: why?
#			time.sleep(.5)

			# Get settings and adjust exposure time and tilt speed.
			if self.slice == 1:
				if not self.settings.getDebugStatus():
					self.serialPrinter.setTiltSpeedSlow()
				self.exposureTime = self.settings.getExposureTimeBase()
			elif self.slice == 2:
				self.exposureTime = self.settings.getExposureTime()
			elif self.slice == 20:
				if not self.settings.getDebugStatus():
					self.serialPrinter.setTiltSpeedFast()

			# Start exposure by writing slice number to queue.
			if self.queueSliceNumber.empty():
				self.queueSliceNumber.put(self.slice)
			self.consoleMessage("   Exposing with " + str(self.exposureTime) + " seconds.")
#			time.sleep(self.exposureTime)
			self.wait(self.exposureTime)
			# Stop exposure by writing -1 to queue.
			if self.queueSliceNumber.empty():
				self.queueSliceNumber.put(-1)
			
			# Tilt.
			self.consoleMessage("   Tilting.")
			if not self.settings.getDebugStatus():
				self.serialPrinter.tilt()

			# Move build platform up by one layer.
			self.consoleMessage("   Moving build platform.")
			if self.slice == 1:
				if not self.settings.getDebugStatus():
					self.serialPrinter.buildBaseUp()
			else:
				if not self.settings.getDebugStatus():
					self.serialPrinter.buildUp()
			
			# Waiting for resin to settle.
			self.consoleMessage("  Waiting for resin to settle.")
			time.sleep(self.settings.getSettleTime())
			
			self.slice+=1
		
		if self.queueStatus.empty():
			self.queueStatus.put("Stopping print.")
		self.consoleMessage("Stopping print.")
		
		# Display black.
		self.queueSliceNumber.put(-1)

		# Move build platform to top.
		if not self.settings.getDebugStatus():
			self.serialPrinter.buildTop()
		# Send printing stop flag to printer.
		if not self.settings.getDebugStatus():
			self.serialPrinter.setStop()
		# Deactivate projector.
		if not self.settings.getDebugStatus():
			self.serialProjector.deactivate()
		# Close and delete communication ports.
		if not self.settings.getDebugStatus():
			self.serialPrinter.close()
			del self.serialPrinter
			self.serialProjector.close()
			del self.serialProjector

		
		if self.queueStatus.empty():
			self.queueStatus.put("Print stopped after " + str(self.slice) + " slices.")
		
		time.sleep(5)
		if self.queueStatus.empty():
			self.queueStatus.put("Destroy")
		
	#	self.__stop.set()
	def consoleMessage(self,message):
		if self.console:
			self.console.message(message)
	

# Add frames to notebook.
notebook.add(frameModel, text='Model')
notebook.add(frameSupports, text='Supports')
notebook.add(frameSlicing, text='Slicing')
notebook.add(framePrinting, text='Print')

# Supports, slice and print tabs are disabled if no model is loaded.
notebook.tab(1, state="disabled")
notebook.tab(2, state="disabled")
notebook.tab(3, state="disabled")

# Pack notebook into main window.
notebook.pack( side='top')#fill=Tkinter.BOTH, expand=1, side=Tkinter.TOP )



# Create debug text output console. ############################################
entryDebugConsole = Tkinter.Text(frameSettings, height=10, state="disabled")
entryDebugConsole.pack(side='bottom', padx=5)

def debugMessage(inputString):
	entryDebugConsole.configure(state="normal")
	entryDebugConsole.insert(Tkinter.END, inputString + '\n')
	entryDebugConsole.configure(state="disabled")

console.pack(side='bottom', padx=5, pady=5)


frameSettings.pack(side='right',fill = 'both')


root.mainloop()
