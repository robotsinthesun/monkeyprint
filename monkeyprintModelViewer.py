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


import pygtk
pygtk.require('2.0')
import gtk
import gtkGLExtVTKRenderWindowInteractor
import vtk

#import monkeyprintModelViewer
import monkeyprintModelHandling


class renderView(gtk.VBox):
	def __init__(self, settings, console=None, backgroundColour = (0.329412, 0.34902, 0.427451)):
		# Call base class initializer.
		gtk.VBox.__init__(self)
		
		# Internalise objects.
		self.settings = settings
		self.console = console
		
		# Create renderer.
		self.renderer = vtk.vtkRenderer()
		self.renderer.SetBackground( backgroundColour )
		
		# Create camera and set view options..
		self.camera =vtk.vtkCamera();
		self.camera.SetViewUp(0,0,1)
		self.camera.SetPosition(self.settings['buildSizeXYZ'].value[0]/2+200, self.settings['buildSizeXYZ'].value[1]/2-300,300);
		self.camera.SetFocalPoint(self.settings['buildSizeXYZ'].value[0]/2, self.settings['buildSizeXYZ'].value[1]/2, self.settings['buildSizeXYZ'].value[2]/2);
		self.camera.SetClippingRange(0.0001, 10000)
		self.renderer.SetActiveCamera(self.camera);

		# Create render window.
		self.renderWindow = vtk.vtkRenderWindow()
		self.renderWindow.AddRenderer(self.renderer)
		
		# Create the render window interactor.
		self.renderWindowInteractor = gtkGLExtVTKRenderWindowInteractor.GtkGLExtVTKRenderWindowInteractor(self)
		# Add renderer to view.

		# Pack it into the box.
		self.pack_start(self.renderWindowInteractor, expand=True, fill=True)
		
		# Set some options.
	#	renderWindowInteractor.SetDesiredUpdateRate(1000)
	#	self.renderWindowInteractor.set_size_request(400, 400)
		# prevents 'q' from exiting the app.
		self.renderWindowInteractor.AddObserver("ExitEvent", lambda o,e,x=None: x)
	#	self.renderWindowInteractor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera()) # This is set as default.
		# Initialise render interactor.
		self.renderWindowInteractor.show()
		self.renderWindowInteractor.Initialize()
		self.renderWindowInteractor.Start()

		self.renderWindowInteractor.GetRenderWindow().AddRenderer(self.renderer)
	#	self.renderWindowInteractor.SetRenderWindow(self.renderWindow)

		

		
		# Add text and axes info.
		self.createAnnotations()
		
		
		# Create an options panel.
		self.optionsBox = gtk.HBox()
		self.pack_start(self.optionsBox, expand=False, fill=False)
		self.optionsBox.show()

		# Make reset button.
		self.buttonReset = gtk.Button(label="Reset view")
		self.buttonReset.connect("clicked", self.callbackResetButton)
		self.optionsBox.pack_start(self.buttonReset, expand=False, fill=False)
		self.buttonReset.show()
		
		# Make colour checkbox.
		self.checkButtonColour = gtk.CheckButton(label="Show colours (coming soon)")
		self.checkButtonColour.connect("toggled", self.callbackCheckButtonColour)
		self.optionsBox.pack_start(self.checkButtonColour)
		self.checkButtonColour.show()
		
		# Make axes checkbox.
		self.checkButtonAxes = gtk.CheckButton(label="Show axes")
		self.checkButtonAxes.connect("toggled", self.callbackCheckButtonAxes)
		self.optionsBox.pack_start(self.checkButtonAxes)
		self.checkButtonAxes.set_active(True)
		self.checkButtonAxes.show()
		
		# Make build volume box.
		self.buildVolume = monkeyprintModelHandling.buildVolume(self.settings['buildSizeXYZ'].value)
		self.addActor(self.buildVolume.getActor())
		
	def callbackResetButton(self, widget, data=None):
		self.reset()
	
	def callbackCheckButtonColour(self, widget, data=None):
		pass
	
	def callbackCheckButtonAxes(self, widget, data=None):
		self.axesActor.SetVisibility(widget.get_active())	
		self.render()
		
	
	def createAnnotations(self):
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
		self.addActor(self.axesActor)
		
		# Add handling info.
		self.infoText = vtk.vtkTextActor()
		self.infoText.SetInput("Rotate:  Left mouse button\nPan:       Middle mouse button\nZoom:    Right mouse button")
		self.infoText.GetTextProperty()
		self.infoText.GetTextProperty().SetFontFamilyToArial()
		self.infoText.GetTextProperty().SetFontSize(11)
		self.infoText.GetTextProperty().SetColor(.6,.6,.6)
		self.infoText.SetDisplayPosition(20,30)
		self.addActor(self.infoText)


	# Reset the camera of the render window.
	def reset(self):
		if self.console:
			self.console.message("View reset.")
		self.camera.SetViewUp(0,0,1)
		self.camera.SetPosition(self.settings['buildSizeXYZ'].value[0]/2+200, self.settings['buildSizeXYZ'].value[1]/2-300,300);
		self.camera.SetFocalPoint(self.settings['buildSizeXYZ'].value[0]/2, self.settings['buildSizeXYZ'].value[1]/2, self.settings['buildSizeXYZ'].value[2]/2);
		self.camera.SetClippingRange(0.0001, 10000)
		self.render()

	# Add an actor to the render window.
	def addActor(self,actor):
		self.renderer.AddActor(actor)
	def addActors(self,actors):
		for actor in actors:
			self.renderer.AddActor(actor)
	
	# Remove an actor from the render view.
	def removeActors(self, actors):
		if type(actors) == tuple:
			for actor in actors:
				self.renderer.RemoveActor(actor)
		else:
			self.renderer.RemoveActor(actors)

	# Refresh the render window.	
	def render(self):
		self.renderWindowInteractor.Render()
		
	# Override superclass destroy function.
	def destroy(self):
		# Destroy the render window.
    		self.renderWindow.Finalize()
    		self.renderWindowInteractor.TerminateApp()
    		del self.renderWindow, self.renderWindowInteractor
    		# Don't forget to destroy the frame itself!
    		Tkinter.Frame.destroy(self)

		

		

'''	

class modelViewer(Tkinter.Frame):
	def __init__(self, parent, console=None, viewWidth=None, viewHeight=None, backgroundColour = (0.329412, 0.34902, 0.427451)):
		# Init super class Frame.
		Tkinter.Frame.__init__(self, parent)
		
		self.console = console
		
		self.frameView = Tkinter.Frame(self)
		

		

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
'''
