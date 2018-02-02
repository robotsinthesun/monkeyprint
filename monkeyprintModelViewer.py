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



import vtk
import monkeyprintModelHandling
import monkeyprintGuiHelper
from PyQt4 import QtCore, QtGui
from vtk.qt4.QVTKRenderWindowInteractor import QVTKRenderWindowInteractor



class renderView(QtGui.QFrame):

	def __init__(self, settings, console=None, backgroundColour = (0.329412, 0.34902, 0.427451)):
		# Call base class initializer.
		super(renderView, self).__init__()

		# Internalise objects.
		self.settings = settings
		self.console = console

		# Create the widget.
		# Create layout box.
		self.box = QtGui.QVBoxLayout()

		# Create vtk widget and pass main frame.
		self.vtkWidget = QVTKRenderWindowInteractor(self)

		# Pack vtk widget in box.
		self.box.addWidget(self.vtkWidget)

		# Get render window.
		self.renderWindow = self.vtkWidget.GetRenderWindow()

		# Create renderer.
		self.renderer = vtk.vtkRenderer()
		self.renderWindow.AddRenderer(self.renderer)

		# Create other elements.
		# Create camera and set view options..
		self.camera =vtk.vtkCamera();
		self.camera.SetViewUp(0,0,1)
		self.camera.SetPosition(self.settings['buildSizeX'].value/2+200, self.settings['buildSizeY'].value/2-300,300);
		self.camera.SetFocalPoint(self.settings['buildSizeX'].value/2, self.settings['buildSizeY'].value/2, self.settings['buildSizeZ'].value/2);
		self.camera.SetClippingRange(0.0001, 10000)
		self.renderer.SetActiveCamera(self.camera);

		# Background color.
		self.renderer.SetBackground( backgroundColour )

		# Get interactor.
		self.renderWindowInteractor = self.renderWindow.GetInteractor()
		self.renderWindowInteractor.SetInteractorStyle(vtk.vtkInteractorStyleTrackballCamera()) # This is set as default.

		# Pack the frame into the widget.
		self.setLayout(self.box)

		# Create options box.
		self.boxOptions = QtGui.QHBoxLayout()
		self.box.addLayout(self.boxOptions)

		# Make reset button.
		self.buttonReset = monkeyprintGuiHelper.button("Reset view", self.callbackResetButton)
		self.boxOptions.addWidget(self.buttonReset)

		# Make axes view toggle.
		self.buttonAxes = monkeyprintGuiHelper.checkbox("Show axes", self.callbackCheckButtonAxes, True)
		self.boxOptions.addWidget(self.buttonAxes)
		self.boxOptions.addStretch(1)

		# Add text and axes info.
		self.createAnnotations()

		# Make build volume box.
		self.buildVolume = monkeyprintModelHandling.buildVolume([self.settings['buildSizeX'].value, self.settings['buildSizeY'].value, self.settings['buildSizeZ'].value])
		self.addActor(self.buildVolume.getActor())

		'''
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
		'''


	def callbackResetButton(self):
		self.reset()


	def callbackCheckButtonColour(self, widget, data=None):
		pass

	def callbackCheckButtonAxes(self, visibility):
		self.axesActor.SetVisibility(visibility)
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
		self.camera.SetPosition(self.settings['buildSizeX'].value/2+200, self.settings['buildSizeY'].value/2-300,300);
		self.camera.SetFocalPoint(self.settings['buildSizeX'].value/2, self.settings['buildSizeY'].value/2, self.settings['buildSizeZ'].value/2);
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
		if type(actors) == tuple or type(actors) == list:
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


	# IMPORTANT: call this AFTER the widget has been placed!
	def initialize(self):
		self.renderWindowInteractor.Initialize()
		self.renderWindowInteractor.Start()
