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
import gtk, gobject
#import gtkGLExtVTKRenderWindowInteractor
import monkeyprintModelViewer
import monkeyprintGuiHelper
import subprocess # Needed to call avrdude.
import vtk
import threading
import Queue
import time

boxSettingsWidth = 350

################################################################################
# Define a class for the main GUI. #############################################
################################################################################
class gui(gtk.Window):

	# Override init function. #################################################
	def __init__(self, modelCollection, programSettings, console=None, *args, **kwargs):
		
		# Initialise base class gtk window.********************
		gtk.Window.__init__(self, *args, **kwargs)
		# Set function for window close event.
		self.connect("delete-event", self.on_closing, None)
		# Set window title.
		self.set_title("Monkeyprint")
		# Set maximized.
		self.maximize()
		# Show the window.
		self.show()
		
		
		
		# Internalise parameters.******************************
		self.modelCollection = modelCollection
		self.programSettings = programSettings
		self.console = console
		
		
		
		# Create model list.***********************************
		# List will contain strings for dispayed name,
		# internal name and file name and a bool for active state.
		self.modelList = gtk.ListStore(str, str, str, bool)
		
		
		
		# Create queues for inter-thread communication.********
		# Queue for setting print progess bar.
		self.sliceQueue = Queue.Queue(maxsize=1)
		# Queue for status infos displayed above the status bar.
		self.infoQueue = Queue.Queue(maxsize=1)
		# Queue list.
		self.queues = [	self.sliceQueue,
						self.infoQueue		]
		
		
		
		# Allow background threads.****************************
		# Very important, otherwise threads will be
		# blocked by gui main thread.
		gtk.gdk.threads_init()
		
		# Add thread listener functions to run every 10 ms.****
		slicerListenerId = gobject.timeout_add(10, modelCollection.checkSlicerThreads)
		progressBarUpdateId = gobject.timeout_add(100, self.updateProgressbar)
		
		self.infoQueue.put("bar")
		self.sliceQueue.put(7)
		
		
		
		# Create additional variables.*************************
		# Flag to set during print process.
		self.printFlag = False		
		
		
		
		# Create the main layout. *****************************
		# Create main box inside of window.
		self.boxMain = gtk.VBox()
		self.add(self.boxMain)
		self.boxMain.show()
		
		# Create menu bar and pack inside main box at top.
		self.menuBar = menuBar(self.programSettings)
		self.boxMain.pack_start(self.menuBar, expand=False, fill=False)
		self.menuBar.show()
		
		# Create work area box and pack below menu bar.
		self.boxWork = gtk.HBox()
		self.boxMain.pack_start(self.boxWork)
		self.boxWork.show()
		
		# Create render box and pack inside work area box.
		self.renderView = monkeyprintModelViewer.renderView(self.programSettings)
		self.renderView.show()
		self.boxWork.pack_start(self.renderView)#, expand=True, fill= True)
		
		# Create settings box and pack right of render box.
		self.boxSettings = self.createSettingsBox()
		self.boxSettings.show()
		self.boxWork.pack_start(self.boxSettings, expand=False, fill=False, padding = 5)
		



		
	# Override the close function. ############################################
	def on_closing(self, widget, event, data):
		# Check if a print is running.
		if self.printFlag:
			self.console.addLine('Monkeyprint cannot be closed')
			self.console.addLine('during a print. Wait for')
			self.console.addLine('the print to finish or cancel')
			self.console.addLine('the print if you want to close.')
		else:
			# Create a dialog window with yes/no buttons.
			dialog = gtk.MessageDialog(self,
				gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
				gtk.MESSAGE_QUESTION,
				gtk.BUTTONS_YES_NO,
				"Do you really want to quit?")
     	     # Set the title.
			dialog.set_title("Quit Monkeyprint?")
		
			# Check the result and respond accordingly.
			response = dialog.run()
			dialog.destroy()
			if response == gtk.RESPONSE_YES:
				# Get all threads.
				runningThreads = threading.enumerate()
				# End kill threads. Main gui thread is the first...
				for i in range(len(runningThreads)):
					if i != 0:
						runningThreads[-1].join(timeout=10000)	# Timeout in ms.
						print "Slicer thread " + str(i) + " finished."
						del runningThreads[-1]
				# Save settings to file.
				self.programSettings.saveFile()
				# Terminate the gui.
				gtk.main_quit()
				return False # returning False makes "destroy-event" be signalled to the window.
			else:
				return True # returning True avoids it to signal "destroy-event"




	
	# Gui main function. ######################################################
	def main(self):
		# All PyGTK applications must have a gtk.main(). Control ends here
		# and waits for an event to occur (like a key press or mouse event).
		gtk.main()




	
	# Create the notebook.#####################################################
	def createSettingsBox(self):
		
		boxSettings = gtk.VBox()
		
		
		# Create model management editor. ************************************
		self.frameModels = gtk.Frame(label="Models")
		boxSettings.pack_start(self.frameModels, padding = 5)
		self.frameModels.show()
		# Create model list view using the model list.
		self.modelListView = modelListView(self.programSettings, self.modelList, self.modelCollection, self.renderView, self.updateAllEntries, self.console)
		self.frameModels.add(self.modelListView)
		self.modelListView.show()
		

		# Create notebook. ***************************************************
		self.notebook = monkeyprintGuiHelper.notebook()
		boxSettings.pack_start(self.notebook)
		self.notebook.show()
		
		# Create model page, append to notebook and pass custom function.
		self.createModelTab()
		self.notebook.append_page(self.modelTab, gtk.Label('Models'))
		self.notebook.set_custom_function(0, self.tabSwitchModelUpdate)
		
		# Create supports page, append to notebook and pass custom function.
		self.createSupportsTab()
		self.notebook.append_page(self.supportsTab, gtk.Label('Supports'))
		self.notebook.set_custom_function(1, self.tabSwitchSupportsUpdate)

		# Add slicing page, append to notebook and pass custom function.
		self.createSlicingTab()
		self.notebook.append_page(self.slicingTab, gtk.Label('Slicing'))
		self.notebook.set_custom_function(2, self.tabSwitchSlicesUpdate)

		# Add print page.
		self.createPrintTab()
		self.notebook.append_page(self.printTab, gtk.Label('Print'))
		self.notebook.set_custom_function(3, self.tabSwitchPrintUpdate)


		# Set gui state. This controls which tabs are clickable.**************
		# 0: Model modifications active.
		# 1: Model modifications, supports and slicing active.
		# 2: All active.
		# Use setGuiState function to set the state. Do not set manually.
		self.setGuiState(0)


		# Create console for debug output.************************************
		# Create frame.
		self.frameConsole = gtk.Frame(label="Output log")
		boxSettings.pack_start(self.frameConsole, padding=5)
		self.frameConsole.show()
		# Custom scrolled window.
		self.consoleView = consoleView(self.console)
		self.frameConsole.add(self.consoleView)
	
	
		# Return the box. ****************************************************
		return boxSettings
	
	
	
	
	# Create notebook pages. ##################################################
	# Model page.
	def createModelTab(self):
		# Create tab box.
		self.modelTab = gtk.VBox()
		self.modelTab.show()
		
		# Create model modification frame.
		self.frameModifications = gtk.Frame(label="Model modifications")
		self.modelTab.pack_start(self.frameModifications, expand=True, fill=True)
		self.frameModifications.show()
		self.boxModelModifications = gtk.VBox()
		self.frameModifications.add(self.boxModelModifications)
		self.boxModelModifications.show()
		self.entryScaling = monkeyprintGuiHelper.entry('Scaling', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryScaling, expand=False, fill=False)
		self.entryRotationX = monkeyprintGuiHelper.entry('Rotation X', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationX, expand=False, fill=False)
		self.entryRotationY = monkeyprintGuiHelper.entry('Rotation Y', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationY, expand=False, fill=False)
		self.entryRotationZ = monkeyprintGuiHelper.entry('Rotation Z', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryRotationZ, expand=False, fill=False)
		self.entryPositionX = monkeyprintGuiHelper.entry('Position X', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryPositionX, expand=False, fill=False)
		self.entryPositionY = monkeyprintGuiHelper.entry('Position Y', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryPositionY, expand=False, fill=False)
		self.entryBottomClearance = monkeyprintGuiHelper.entry('Bottom clearance', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxModelModifications.pack_start(self.entryBottomClearance, expand=False, fill=False)

	# Supports page.
	def createSupportsTab(self):
		# Create tab box.
		self.supportsTab = gtk.VBox()
		self.supportsTab.show()
		
		# Create support pattern frame.
		self.frameSupportPattern = gtk.Frame(label="Support pattern")
		self.supportsTab.pack_start(self.frameSupportPattern, expand=False, fill=False)
		self.frameSupportPattern.show()
		self.boxSupportPattern = gtk.VBox()
		self.frameSupportPattern.add(self.boxSupportPattern)
		self.boxSupportPattern.show()
		self.entryOverhangAngle = monkeyprintGuiHelper.entry('Overhang angle', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entryOverhangAngle, expand=False, fill=False)
		self.entrySupportSpacingX = monkeyprintGuiHelper.entry('Spacing X', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportSpacingX, expand=False, fill=False)
		self.entrySupportSpacingY = monkeyprintGuiHelper.entry('Spacing Y', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportSpacingY, expand=False, fill=False)
		self.entrySupportMaxHeight = monkeyprintGuiHelper.entry('Maximum height', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportPattern.pack_start(self.entrySupportMaxHeight, expand=False, fill=False)
		
		# Create support geometry frame.
		self.frameSupportGeometry = gtk.Frame(label="Support geometry")
		self.supportsTab.pack_start(self.frameSupportGeometry, expand=False, fill=False)
		self.frameSupportGeometry.show()
		self.boxSupportGeometry = gtk.VBox()
		self.frameSupportGeometry.add(self.boxSupportGeometry)
		self.boxSupportGeometry.show()
		self.entrySupportBaseDiameter = monkeyprintGuiHelper.entry('Base diameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportBaseDiameter, expand=False, fill=False)
		self.entrySupportTipDiameter = monkeyprintGuiHelper.entry('Tip diameter', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportTipDiameter, expand=False, fill=False)
		self.entrySupportTipHeight = monkeyprintGuiHelper.entry('Cone height', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxSupportGeometry.pack_start(self.entrySupportTipHeight, expand=False, fill=False)

		# Create bottom plate frame.
		self.frameBottomPlate = gtk.Frame(label="Bottom plate")
		self.supportsTab.pack_start(self.frameBottomPlate, expand=False, fill=False)
		self.frameBottomPlate.show()
		self.boxBottomPlate = gtk.VBox()
		self.frameBottomPlate.add(self.boxBottomPlate)
		self.boxBottomPlate.show()
		self.entrySupportBottomPlateThickness = monkeyprintGuiHelper.entry('Bottom plate thickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxBottomPlate.pack_start(self.entrySupportBottomPlateThickness, expand=False, fill=False)
	
	# Slicing page.
	def createSlicingTab(self):
		# Create tab box.
		self.slicingTab = gtk.VBox()
		self.slicingTab.show()

		# Create slicing parameters frame.
		self.frameSlicing = gtk.Frame(label="Slicing parameters")
		self.slicingTab.pack_start(self.frameSlicing, padding = 5)
		self.frameSlicing.show()
		self.boxSlicingParameters = gtk.VBox()
		self.frameSlicing.add(self.boxSlicingParameters)
		self.boxSlicingParameters.show()
		# Layer height entry.
		self.entryLayerHeight = monkeyprintGuiHelper.entry('Layer height', settings=self.programSettings, customFunctions=[self.updateAllModels, self.updateSlider, self.renderView.render, self.updateAllEntries])
		self.boxSlicingParameters.pack_start(self.entryLayerHeight, expand=False, fill=False)
		
		# Create hollow and fill frame.
		self.frameFill = gtk.Frame(label="Fill parameters")
		self.slicingTab.pack_start(self.frameFill, padding = 5)
		self.frameFill.show()
		self.boxFill = gtk.VBox()
		self.frameFill.add(self.boxFill)
		self.boxFill.show()
		self.boxFillCheckbuttons = gtk.HBox()
		self.boxFill.pack_start(self.boxFillCheckbuttons)
		self.boxFillCheckbuttons.show()
		# Checkbox for hollow prints.
		self.checkboxHollow = gtk.CheckButton(label="Print hollow?")
		self.boxFillCheckbuttons.pack_start(self.checkboxHollow, expand=True, fill=True)
		self.checkboxHollow.set_active(True)
		self.checkboxHollow.show()
		self.checkboxHollow.connect("toggled", self.callbackCheckButtonHollow)
		# Checkbox for fill structures.
		self.checkboxFill = gtk.CheckButton(label="Use fill?")
		self.boxFillCheckbuttons.pack_start(self.checkboxFill, expand=True, fill=True)
		self.checkboxFill.set_active(True)
		self.checkboxFill.show()
		self.checkboxFill.connect("toggled", self.callbackCheckButtonFill)
		# Entries.
		self.entryShellThickness = monkeyprintGuiHelper.entry('Shell wall thickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryShellThickness, expand=True, fill=True)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('Fill spacing', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryFillSpacing, expand=True, fill=True)
		self.entryFillThickness = monkeyprintGuiHelper.entry('Fill wall thickness', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxFill.pack_start(self.entryFillThickness, expand=True, fill=True)
		
		# Create preview frame.
		self.framePreview = gtk.Frame(label="Slice preview")
		self.slicingTab.pack_start(self.framePreview, padding = 5)
		self.framePreview.show()
		self.boxPreview = gtk.HBox()
		self.framePreview.add(self.boxPreview)
		self.boxPreview.show()
		self.sliceSlider = monkeyprintGuiHelper.imageSlider(self.modelCollection, self.programSettings, self.console, customFunctions=[self.modelCollection.updateAllSlices3d, self.renderView.render])
		self.boxPreview.pack_start(self.sliceSlider, expand=True, fill=True, padding=5)
		self.sliceSlider.show()
	
	# Print page.
	def createPrintTab(self):
		# Create tab box.
		self.printTab = gtk.VBox()
		self.printTab.show()

		# Create print parameters frame.
		self.framePrint = gtk.Frame(label="Print parameters")
		self.printTab.pack_start(self.framePrint, expand=False, fill=False, padding = 5)
		self.framePrint.show()
		self.boxPrintParameters = gtk.VBox()
		self.framePrint.add(self.boxPrintParameters)
		self.boxPrintParameters.show()
		
		# Create entries.
		self.entryShellThickness = monkeyprintGuiHelper.entry('Exposure time base', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxPrintParameters.pack_start(self.entryShellThickness, expand=True, fill=True)
		self.entryFillSpacing = monkeyprintGuiHelper.entry('Exposure time', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxPrintParameters.pack_start(self.entryFillSpacing, expand=True, fill=True)
		self.entryFillThickness = monkeyprintGuiHelper.entry('Resin settle time', modelCollection=self.modelCollection, customFunctions=[self.updateCurrentModel, self.renderView.render, self.updateAllEntries])
		self.boxPrintParameters.pack_start(self.entryFillThickness, expand=True, fill=True)
		
		# Create model volume frame.
		self.frameResinVolume = gtk.Frame(label="Resin volume")
		self.printTab.pack_start(self.frameResinVolume, expand=False, fill=False, padding = 5)
		self.frameResinVolume.show()
		self.boxResinVolume = gtk.HBox()
		self.frameResinVolume.add(self.boxResinVolume)
		self.boxResinVolume.show()
		
		# Resin volume label.
		self.resinVolumeLabel = gtk.Label("Volume: ")
		self.boxResinVolume.pack_start(self.resinVolumeLabel, expand=False, fill=False)
		self.resinVolumeLabel.show()
		
		# Create print control frame.
		self.framePrintControl = gtk.Frame(label="Print control")
		self.printTab.pack_start(self.framePrintControl, expand=False, fill=False, padding = 5)
		self.framePrintControl.show()
		self.boxPrintControl = gtk.HBox()
		self.framePrintControl.add(self.boxPrintControl)
		self.boxPrintControl.show()
		
		# Create print control buttons.
		self.boxPrintButtons = gtk.HBox()
		self.boxPrintControl.pack_start(self.boxPrintButtons, expand=False, fill=False)
		self.boxPrintButtons.show()
		self.buttonPrintStart = gtk.Button('Print')
		self.boxPrintButtons.pack_start(self.buttonPrintStart, expand=False, fill=False)
		self.buttonPrintStart.connect('clicked', self.callbackStartPrintProcess)
		self.buttonPrintStart.show()
		self.buttonPrintStop = gtk.Button('Stop')
		self.boxPrintButtons.pack_start(self.buttonPrintStop, expand=False, fill=False)
		self.buttonPrintStop.show()
		self.buttonPrintStop.connect('clicked', self.callbackStopPrintProcess)
		
		# Create progress bar.
		self.progressBar = monkeyprintGuiHelper.printProgressBar()
		self.boxPrintControl.pack_start(self.progressBar, expand=True, fill=True)
		self.progressBar.show()
		self.progressBar.setLimit(100)
		self.progressBar.setText('foo')
		self.progressBar.updateValue(50)		
	
	
	# Notebook tab switch callback functions. #################################
	# Model page.
	def tabSwitchModelUpdate(self):
		# Set render actor visibilities.
		self.modelCollection.viewDefault()
		self.renderView.render()
		# Enable model management load and remove buttons.
		self.modelListView.setSensitive(True)

	# Supports page.
	def tabSwitchSupportsUpdate(self):
		# Update supports.
		self.modelCollection.updateAllSupports()
		# Set render actor visibilities.
		self.modelCollection.viewSupports()
		self.renderView.render()
		# Activate slice tab if not already activated.
		if self.getGuiState() == 1:
			self.setGuiState(2)
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False)

	# Slicing page.
	def tabSwitchSlicesUpdate(self):
		# Update slider.
		self.sliceSlider.updateSlider()
		# Update slice stack height.
		self.modelCollection.updateSliceStack()
		# Set render actor visibilites.
		self.modelCollection.viewSlices()
		self.renderView.render()
		# Activate print tab if not already activated.
		if self.getGuiState() == 2:
			self.setGuiState(3)
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False)
	
	# Print page.
	def tabSwitchPrintUpdate(self):
		# Set render actor visibilites.
		self.modelCollection.viewPrint()
		self.renderView.render()
		# Update the model volume.
		self.updateVolume()
		# Disable model management load and remove buttons.
		self.modelListView.setSensitive(False)
	

	
	
	
	# Other callback function. ################################################
	
	def callbackCheckButtonHollow(self, widget, data=None):
		self.modelCollection.getCurrentModel().settings['Print hollow'].setValue(widget.get_active())
		# Update model.
		self.updateCurrentModel()
		
	def callbackCheckButtonFill(self, widget, data=None):
		self.modelCollection.getCurrentModel().settings['Fill'].setValue(widget.get_active())
		self.updateCurrentModel()

	def callbackStartPrintProcess(self, data=None):
		# Create a print start dialog.
		self.dialogStart = dialogStartPrint()
		# Run the dialog and get the result.
		response = self.dialogStart.run()
		self.dialogStart.destroy()
		if response==True:
			self.console.addLine("Starting print")
			# Disable window close event.
			self.printFlag = True
			# Start the print.
			self.printWindow = monkeyprintGuiHelper.projectorDisplay(self.programSettings)

	def callbackStopPrintProcess(self, data=None):
		# Create a dialog window with yes/no buttons.
		dialog = gtk.MessageDialog(	None,
								gtk.DIALOG_MODAL | gtk.DIALOG_DESTROY_WITH_PARENT,
								gtk.MESSAGE_QUESTION,
								gtk.BUTTONS_YES_NO,
								"Do you really want to cancel the print?")
          # Set the title.
		dialog.set_title("Cancel print?")
		
		# Check the result and respond accordingly.
		response = dialog.run()
		dialog.destroy()
		if response == gtk.RESPONSE_YES:
			self.console.addLine("Cancelling print")
			self.printFlag = False
			# Stop the print process.
			self.printWindow.stop()	
	




	# Gui update functions. ###################################################
	def updateProgressbar(self):
		# If slice number queue has slice number...
		if self.queues[0].qsize():
			# ... get slice number and set progress bar.
			self.progressBar.updateValue(self.queues[0].get()) 
			# Set 3d view to given slice.
			# TODO
			# Set slice view to given slice.
			# TODO
		# If print info queue has info...
		if self.queues[1].qsize():
			self.progressBar.setText(self.queues[1].get()) 
	
	
	
	def updateVolume(self):
		self.resinVolumeLabel.set_text("Volume: " + str(self.modelCollection.getTotalVolume()) + " ml.")
	


	def setGuiState(self, state):
		for i in range(self.notebook.get_n_pages()):
			if i<=state:
				self.notebook.set_tab_sensitive(i, True)
			else:
				self.notebook.set_tab_sensitive(i, False)
	
	
	
	def getGuiState(self):
		tab = 0
		for i in range(self.notebook.get_n_pages()):
			if self.notebook.is_tab_sensitivte(i):
				tab = i
		return tab
	
	
	
	# Function to update the current model after a change was made.
	# Updates model supports or slicing dependent on
	# the current page of the settings notebook.
	def updateCurrentModel(self):
		if self.notebook.getCurrentPage() == 0:
			self.modelCollection.getCurrentModel().updateModel()
		elif self.notebook.getCurrentPage() == 1:
			self.modelCollection.getCurrentModel().updateSupports()
		elif self.notebook.getCurrentPage() == 2:
			self.modelCollection.getCurrentModel().setChanged()
			self.modelCollection.getCurrentModel().updateSliceStack()
		elif self.notebook.getCurrentPage() == 3:
			self.modelCollection.getCurrentModel().updatePrint()
	
	
	
	def updateAllModels(self):
		if self.notebook.getCurrentPage() == 2:
			self.modelCollection.updateSliceStack()
			
	
	
	# Update all the settings if the current model has changed.
	def updateAllEntries(self, state=None):
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
#		self.sliceSlider.updateSlider()
		if state != None:
			self.setGuiState(state)
			if state == 0:
				self.notebook.setCurrentPage(0)
	
	
				
	def updateSlider(self):
		self.sliceSlider.updateSlider()
	
	
	







# Main menu. ###################################################################	

class menuBar(gtk.MenuBar):
	# Override init function.
	def __init__(self, settings):
		# Call super class init function.
		gtk.MenuBar.__init__(self)
		self.show()
		
		self.settings = settings
		
		# Create file menu (does not have to be shown).
		fileMenu = gtk.Menu()
		
		# Create file menu items.
		menuItemOpen = gtk.MenuItem(label="Open project")
		menuItemSave = gtk.MenuItem(label="Save project")
		menuItemClose = gtk.MenuItem(label="Close project")
		menuItemQuit = gtk.MenuItem(label="Quit")
		
		# Add to menu.
		fileMenu.append(menuItemOpen)
		fileMenu.append(menuItemSave)
		fileMenu.append(menuItemClose)
		fileMenu.append(menuItemQuit)
		
		# Connect menu items to callback signals.
#		menuItemOpen.connect_object("activate", menuitem_response, "file.open")
#		menuItemSave.connect_object("activate", menuitem_response, "file.save")
#		menuItemClose.connect_object("activate", menuitem_response, "file.close")
#		menuItemQuit.connect_object ("activate", destroy, "file.quit")
		
		# Show the items.
		menuItemOpen.show()
		menuItemSave.show()
		menuItemClose.show()
		menuItemQuit.show()
		
		
		
		# Create file menu (does not have to be shown).
		optionsMenu = gtk.Menu()
		
		# Create file menu items.
		menuItemSettings = gtk.MenuItem(label="Settings")
		menuItemFlash = gtk.MenuItem(label="Flash firmware")
		menuItemManualControl = gtk.MenuItem(label="Manual control")
		
		# Connect callbacks.
		menuItemSettings.connect("activate", self.callbackSettings)
		menuItemFlash.connect("activate", self.callbackFlash)

		# Add to menu.
		optionsMenu.append(menuItemSettings)
		optionsMenu.append(menuItemFlash)
		optionsMenu.append(menuItemManualControl)

		
		# Connect menu items to callback signals.
#		menuItemOpen.connect_object("activate", menuitem_response, "file.open")
#		menuItemSave.connect_object("activate", menuitem_response, "file.save")
#		menuItemClose.connect_object("activate", menuitem_response, "file.close")
#		menuItemQuit.connect_object ("activate", destroy, "file.quit")
		
		# Show the items.
		menuItemSettings.show()
		menuItemFlash.show()
		menuItemManualControl.show()
		

		# Create menu bar items.
		menuItemFile = gtk.MenuItem(label="File")
		menuItemFile.set_submenu(fileMenu)
		self.append(menuItemFile)
		menuItemFile.show()
		
		menuItemOptions = gtk.MenuItem(label="Options")
		menuItemOptions.set_submenu(optionsMenu)
		self.append(menuItemOptions)
		menuItemOptions.show()
	
	def callbackSettings(self, event):
		dialogSettings(self.settings)
		
	def callbackFlash(self, event):
		firmwareDialog(self.settings)





# Model list. ##################################################################
class modelListView(gtk.VBox):
	def __init__(self, settings, modelList, modelCollection, renderView, guiUpdateFunction, console=None):
		gtk.VBox.__init__(self)
		self.show()

		# Internalise settings.
		self.settings = settings
		# Internalise model collection and optional console.
		self.modelList = modelList
		self.modelCollection = modelCollection
		# Import the render view so we are able to add and remove actors.
		self.renderView = renderView
		self.guiUpdateFunction = guiUpdateFunction
		self.console = console
		
		self.modelRemovedFlag = False
		
		# Create the scrolled window.
		self.scrolledWindow = gtk.ScrolledWindow()
		self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.pack_start(self.scrolledWindow, expand=True, fill=True, padding = 5)
		self.scrolledWindow.show()
		# Create view for model list.
		self.viewModels = gtk.TreeView()
		self.viewModels.set_model(self.modelList)
		self.viewModels.show()
#		self.viewModels.set_headers_visible(False)	# Make column invisible.
		self.viewModels.set_headers_clickable(True)
		self.viewModels.set_reorderable(True)
		self.scrolledWindow.add(self.viewModels)
		# Add model name column and respective text cell renderer.
		self.columnModel = gtk.TreeViewColumn('Model name')
		self.viewModels.append_column(self.columnModel)
		self.cellModel = gtk.CellRendererText()
		self.cellModel.set_property('editable', True)
		self.cellModel.connect('edited', self.callbackEdited, self.modelList)
		self.columnModel.pack_start(self.cellModel, True)
		self.columnModel.add_attribute(self.cellModel, 'text', 0)
		self.columnModel.set_sort_column_id(0)
		# Add active? column and respective toggle cell renderer.
		self.columnActive = gtk.TreeViewColumn('Active?')
		self.viewModels.append_column(self.columnActive)
		self.cellActive = gtk.CellRendererToggle()
		self.cellActive.set_property('activatable', True)
		self.cellActive.connect("toggled", self.callbackToggleChanged, self.modelList)
		self.columnActive.pack_start(self.cellActive, False)
		self.columnActive.add_attribute(self.cellActive, 'active', 3)
		self.columnActive.set_sort_column_id(3)

		# Create item selection.
		self.modelSelection = self.viewModels.get_selection()
		# Avoid multiple selection.
		self.modelSelection.set_mode(gtk.SELECTION_SINGLE)
		# Connect to selection change event function.
		self.modelSelection.connect('changed', self.onSelectionChanged)
		
		# Create button box.
		self.boxButtons = gtk.HBox()
		self.boxButtons.show()
		self.pack_start(self.boxButtons, expand=False)
		# Create model load and remove button.
		self.buttonLoad = gtk.Button("Load")
		self.buttonLoad.show()
		self.buttonLoad.connect("clicked", self.callbackLoad)
		self.boxButtons.pack_start(self.buttonLoad)
		self.buttonRemove = gtk.Button("Remove")
		self.buttonRemove.set_sensitive(False)
		self.buttonRemove.show()
		self.buttonRemove.connect("clicked", self.callbackRemove)
		self.boxButtons.pack_start(self.buttonRemove)
	
	# Add an item and set it selected.
	def add(self, displayName, internalName, filename):
		# Append list item and get its iter.
		newIter = self.modelList.append([displayName, internalName, filename, True])
		# Set the iter selected.
		self.modelSelection.select_iter(newIter)
		# Make supports and slice tab available if this is the first model.
		if len(self.modelList)< 2:
			self.guiUpdateFunction(state=1)
	
	# Remove an item and set the selection to the next.
	def remove(self, currentIter):
		# Get the path of the current iter.
		currentPath = self.modelList.get_path(currentIter)[0]
		deletePath = currentPath
		# Check what to select next.
		# If current selection at end of list but not the last element...
		if currentPath == len(self.modelList) - 1 and len(self.modelList) > 1:
			# ... select the previous item.
			currentPath -= 1
			self.modelSelection.select_path(currentPath)		
		# If current selection is somewhere in the middle...
		elif currentPath < len(self.modelList) - 1 and len(self.modelList) > 1:
			# ... selected the next item.
			currentPath += 1
			self.modelSelection.select_path(currentPath)
		# If current selection is the last element remaining...
		elif len(self.modelList)	== 1:
			# ... set the default model as current model.
			self.modelCollection.setCurrentModelId("default")
			# Deactivate the remove button.
			self.buttonRemove.set_sensitive(False)
			# Update the gui.
			self.guiUpdateFunction(state=0)
			# TODO: Disable all the input entries and the supports/slicing/print tabs.
		
		# Now that we have the new selection, we can delete the previously selected model.
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getActor())
		self.renderView.removeActors(self.modelCollection.getModel(self.modelList[(deletePath,0,0)][1]).getBoxActor())
		# Some debug output...
		if self.console:
			self.console.addLine("Removed model " + self.modelList.get_value(currentIter,0) + ".")
		# Remove the model from the model collection object.
		self.modelCollection.remove(self.modelList[currentIter][1])
		# Remove the item and check if there's a next item.
		iterValid = self.modelList.remove(currentIter)
		# Update the slice stack.
	#	self.modelCollection.updateSliceStack()
		# Update the slider.
		self.guiUpdateFunction()
		# Refresh view.
		self.renderView.render()
		
	
	# Load a new item into the model list and set it selected.
	def callbackLoad(self, widget, data=None):
		filepath = ""

		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Load model", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.settings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Stl files")
		fileFilter.add_pattern("*.stl")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Close the dialog.
		print response
		# Check the response.
		# If OK was pressed...
		if response == gtk.RESPONSE_OK:
			filepath = dialog.get_filename()		
			# Check if file is an stl. If yes, load.
			if filepath.lower()[-3:] != "stl":
				if self.console:
					self.console.addLine("File \"" + filepath + "\" is not an stl file.")
			else:
				# Get filename without path.
				filenameStlParts = filepath.split('/')
				filename = filenameStlParts[-1]
				if self.console:
					self.console.addLine("Loading file \"" + filename + "\".")
				# Save path for next use.
				self.settings['currentFolder'].value = filepath[:-len(filenameStlParts[-1])]
				# Check if there is a file with the same name loaded already.
				# Use the permanent file id in second row for this.
				copyNumber = 0
				for row in self.modelList:
					# Check if filename already loaded.
					if filename == row[1][:len(filename)]:
						# If so, set the copy number to 1.
						copyNumber = 1
						# Check if this is a copy already.
						if len(row[1]) > len(filename):
							if int(row[1][len(filename)+2:len(row[1])-1]) >= copyNumber:
								copyNumber = int(row[1][len(filename)+2:len(row[1])-1]) + 1
				if copyNumber > 0:
					filename = filename + " (" + str(copyNumber) + ")"
			# Hide the previous models bounding box.
			self.modelCollection.getCurrentModel().hideBox()
			# Load the model into the model collection.
			self.modelCollection.add(filename, filepath)
			# Add the filename to the list and set selected.
			self.add(filename, filename, filepath)	
			# Activate the remove button which was deactivated when there was no model.
			self.buttonRemove.set_sensitive(True)
			# Add actor to render view.
			self.renderView.addActors(self.modelCollection.getCurrentModel().getAllActors())

			# Update 3d view.
			self.renderView.render()
			
			dialog.destroy()
		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()
			
	# Delete button callback.
	def callbackRemove(self, widget, data=None):
		model, treeiter = self.modelSelection.get_selected()
		self.remove(treeiter)

	# Name edited callback.
	def callbackEdited(self, cell, path, new_text, model):
		model[path][0] = new_text
		
	# Active state toggled callback.
	def callbackToggleChanged(self, cell, path, model):
		# Toggle active flag in model list.
		model[path][3] = not model[path][3]
		# Toggle active flag in model collection.
		self.modelCollection.getCurrentModel().setActive(model[path][3])
		# Console output.
		if self.console:
			if model[path][3] == True:
				self.console.addLine("Model " + model[path][0] + " activated.")
			else:
				self.console.addLine("Model " + model[path][0] + " deactivated.")

	# Selection changed callback.
	def onSelectionChanged(self, selection):
		# Hide the previous models bounding box actor.
		self.modelCollection.getCurrentModel().hideBox()
		model, treeiter = selection.get_selected()
		if treeiter != None:	# Make sure someting is selected.
			if self.console:
				self.console.addLine("Model " + model[treeiter][0] + " selected.")
			# Set current model in model collection.
			self.modelCollection.setCurrentModelId(model[treeiter][1])
			# Show bounding box.
			self.modelCollection.getCurrentModel().showBox()
			self.renderView.render()
			# Update the gui.
			self.guiUpdateFunction()
	
	# Disable buttons so models can only be loaded in first tab.
	def setSensitive(self, sensitive):
		self.buttonLoad.set_sensitive(sensitive)
		self.buttonRemove.set_sensitive(sensitive)



# Window for firmware upload. ##################################################
class firmwareDialog(gtk.Window):
	# Override init function.
	def __init__(self, settings):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		self.show()
		
		# Internalise settings.
		self.settings = settings
		
		# Main container.
		box = gtk.VBox()
		self.add(box)
		box.show()
#TODO: Rebuild with entry objects.		
		# Description.
		label = gtk.Label("Push the reset button on your controller board and press \"Flash firmware\"!")
		box.pack_start(label, expand=False, fill=False)
		label.show()
		
		# Make a box for the entries.
		boxEntries = gtk.VBox()
		box.pack_start(boxEntries)
		boxEntries.show()
		# Avrdude option entries.
		self.entryPath = monkeyprintGuiHelper.entry('Firmware path', settings=self.settings, width=20)
		boxEntries.pack_start(self.entryPath)
		self.entryMCU = monkeyprintGuiHelper.entry('MCU', settings=self.settings, width=20)
		boxEntries.pack_start(self.entryMCU)
		self.entryProgrammer = monkeyprintGuiHelper.entry('Programmer', settings=self.settings, width=20)
		boxEntries.pack_start(self.entryProgrammer)
		self.entryPort = monkeyprintGuiHelper.entry('Port', settings=self.settings, width=20)
		boxEntries.pack_start(self.entryPort)
		self.entryBaud = monkeyprintGuiHelper.entry('Baud', settings=self.settings, width=20)
		boxEntries.pack_start(self.entryBaud)
		self.entryOptions = monkeyprintGuiHelper.entry('Options', settings=self.settings, customFunctions=[self.entryOptionsUpdate], width=20)
		boxEntries.pack_start(self.entryOptions)

		# Make a box for the buttons.
		boxButtons = gtk.HBox()
		box.pack_start(boxButtons, expand=False, fill=False)
		boxButtons.show()
		# Flash button.
		buttonFlash = gtk.Button("Flash firmware")
		boxButtons.pack_start(buttonFlash, expand=False, fill=False)
		buttonFlash.connect("clicked", self.callbackFlash)
		buttonFlash.show()
		# Back to defaults button.
		buttonDefaults = gtk.Button("Restore defaults")
		boxButtons.pack_start(buttonDefaults, expand=False, fill=False)
		buttonDefaults.connect("clicked", self.callbackDefaults)
		buttonDefaults.show()
		# Close button.
		buttonClose = gtk.Button("Close")
		boxButtons.pack_start(buttonClose, expand=False, fill=False)
		buttonClose.connect("clicked", self.callbackClose)
		buttonClose.show()
		
		# Create an output window for avrdude feedback.
		self.console = consoleText()
		self.consoleView = consoleView(self.console)
		box.pack_start(self.consoleView)
		self.consoleView.show()
		

	def entryOptionsUpdate(self):
		# Process options.
		# Extract additional options into list and eliminate '-' from options.
		optionList = self.entryOptions.entry.get_text().replace('-','')
		# Split into option list.
		optionList = optionList.split(' ')
		# Add '-' to options. This way users can input options with and without '-'.
		optionList = ['-' + option for option in optionList]
		# Concatenate into string for settings object.
		optionString = ''
		for option in optionList:
			if option != "-":
				optionString = optionString + option + ' '
		# Remove trailing space.
		optionString = optionString[:-1]
		# Write to settings and set entry string.
		self.settings['Options'].value = optionString
		self.entryOptions.entry.set_text(optionString)


	def callbackFlash(self, widget, data=None):
		# Create avrdude commandline string.
		avrdudeCommandList = [	'avrdude',
							'-p', self.settings['MCU'].value,
							'-P', self.settings['Port'].value,
							'-c', self.settings['Programmer'].value,
							'-b', self.settings['Baud'].value,
							'-U', 'flash:w:' + self.settings['Firmware path'].value
							]
		# Append additional options.
		optionList = self.settings['Options'].value.split(' ')
		for option in optionList:
			avrdudeCommandList.append(option)
		# Console output.
		self.console.addLine('Running avrdude with options:')
		self.console.addLine('-p ' + self.settings['MCU'].value + '-P ' + self.settings['Port'].value + '-c ' + self.settings['Programmer'].value + '-b ' + self.settings['Baud'].value + '-U ' + 'flash:w:' + self.settings['Firmware path'].value)
		time.sleep(1)
		# Call avrdude and get it's output.
		# Redirect error messages to stdout and stdout to PIPE
		avrdudeProcess = subprocess.Popen(avrdudeCommandList, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		output = avrdudeProcess.communicate()[0]
		# If an error occured...
		if avrdudeProcess.returncode !=0:
			#... display the error message.
			self.console.addLine("Error code: " + str(avrdudeProcess.returncode))
			self.console.addLine("Error message: " + output)
			self.console.addLine("Make sure the Arduino is connected correctly.")
		# In case of success...
		else:
			# Print the output.
			self.console.addLine(output)
			self.console.addLine("Firmware flashed successfully!")


	def callbackDefaults(self, widget, data=None):
		# Set default settings.
		self.settings.loadDefaults()
		# Update entries.
		self.entryMCU.update()
		self.entryProgrammer.update()
		self.entryPort.update()
		self.entryBaud.update()
		self.entryPath.update()
		self.entryOptions.update()

	def callbackClose(self, widget, data=None):
		self.destroy()



# Settings window. #############################################################
# Define a window for all the settings that are related to the printer.

class dialogSettings(gtk.Window):
	# Override init function.
	def __init__(self, settings):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
		self.show()
		
		# Internalise settings.
		self.settings = settings
		
		# Save settings in case of cancelling.
		self.settingsBackup = settings
		
		# Vertical box for settings and bottom buttons.
		self.boxMain = gtk.VBox()
		self.add(self.boxMain)
		self.boxMain.show()
		
		# Horizontal box for columns.
		self.boxSettings = gtk.HBox()
		self.boxMain.pack_start(self.boxSettings)
		self.boxSettings.show()

		# Vertical box for column 1.
		self.boxCol1 = gtk.VBox()
		self.boxSettings.pack_start(self.boxCol1)
		self.boxCol1.show()
		
		# Frame for serial settings.
		self.frameSerial = gtk.Frame('Serial communication')
		self.boxCol1.pack_start(self.frameSerial)
		self.frameSerial.show()
		self.boxSerial = gtk.VBox()
		self.frameSerial.add(self.boxSerial)
		self.boxSerial.show()
		# Add entries.
		# Port.
		self.entryPort = monkeyprintGuiHelper.entry('Port', self.settings)
		self.boxSerial.pack_start(self.entryPort)
		self.entryPort.show()
		# Baud rate.
		self.entryBaud = monkeyprintGuiHelper.entry('Baud rate', self.settings)
		self.boxSerial.pack_start(self.entryBaud)
		self.entryBaud.show()
		# Test button and output for serial communication.
		# Box for button and text output.
		self.boxSerialTest = gtk.HBox()
		self.boxSerial.pack_start(self.boxSerialTest)
		self.boxSerialTest.show()
		# Button.
		self.buttonSerialTest = gtk.Button("Test connection")
		self.boxSerialTest.pack_start(self.buttonSerialTest, expand=False, fill=False)
		self.buttonSerialTest.connect("clicked", self.callbackSerialTest)
		self.buttonSerialTest.show()
		# Text entry to show connection test result.
		self.textOutputSerialTest = gtk.Entry()
		self.boxSerialTest.pack_start(self.textOutputSerialTest, expand=False, fill=False)
		self.textOutputSerialTest.show()
		
		
		# Frame for build volume settings.
		self.frameBuildVolume = gtk.Frame('Build volume')
		self.boxCol1.pack_start(self.frameBuildVolume)
		self.frameBuildVolume.show()
		self.boxBuildVolume = gtk.VBox()
		self.frameBuildVolume.add(self.boxBuildVolume)
		self.boxBuildVolume.show()
		# Add entries.
		self.entryBuildSizeX= monkeyprintGuiHelper.entry('Build size X', self.settings)
		self.boxBuildVolume.pack_start(self.entryBuildSizeX)
		self.entryBuildSizeX.show()
		self.entryBuildSizeY= monkeyprintGuiHelper.entry('Build size Y', self.settings)
		self.boxBuildVolume.pack_start(self.entryBuildSizeY)
		self.entryBuildSizeY.show()
		self.entryBuildSizeZ= monkeyprintGuiHelper.entry('Build size Z', self.settings)
		self.boxBuildVolume.pack_start(self.entryBuildSizeZ)
		self.entryBuildSizeZ.show()
		
		# Frame for projector settings.
		self.frameProjector = gtk.Frame('Projector')
		self.boxCol1.pack_start(self.frameProjector, expand=False, fill=False)
		self.frameProjector.show()
		self.boxProjector = gtk.VBox()
		self.frameProjector.add(self.boxProjector)
		self.boxProjector.show()
		self.entryProjectorSizeX= monkeyprintGuiHelper.entry('Projector size X', self.settings)
		self.boxProjector.pack_start(self.entryProjectorSizeX, expand=False, fill=False)
		self.entryProjectorSizeX.show()
		self.entryProjectorSizeY= monkeyprintGuiHelper.entry('Projector size Y', self.settings)
		self.boxProjector.pack_start(self.entryProjectorSizeY, expand=False, fill=False)
		self.entryProjectorSizeY.show()
		self.entryProjectorPositionX= monkeyprintGuiHelper.entry('Projector position X', self.settings)
		self.boxProjector.pack_start(self.entryProjectorPositionX, expand=False, fill=False)
		self.entryProjectorPositionX.show()
		self.entryProjectorPositionY= monkeyprintGuiHelper.entry('Projector position Y', self.settings)
		self.boxProjector.pack_start(self.entryProjectorPositionY, expand=False, fill=False)
		self.entryProjectorPositionY.show()
		
		# Vertical box for column 2.
		self.boxCol2 = gtk.VBox()
		self.boxSettings.pack_start(self.boxCol2)
		self.boxCol2.show()
		
		# Frame for Tilt stepper.
		self.frameTiltStepper = gtk.Frame('Tilt stepper')
		self.boxCol2.pack_start(self.frameTiltStepper, expand=False, fill=False)
		self.frameTiltStepper.show()
		self.boxTilt = gtk.VBox()
		self.frameTiltStepper.add(self.boxTilt)
		self.boxTilt.show()
		# Entries.
		# Resolution.
		self.entryTiltStepsPerDeg = monkeyprintGuiHelper.entry('Tilt steps / °', self.settings)
		self.boxTilt.pack_start(self.entryTiltStepsPerDeg, expand=False, fill=False)
		self.entryTiltStepsPerDeg.show()
		# Tilt angle.
		self.entryTiltAngle = monkeyprintGuiHelper.entry('Tilt angle', self.settings)
		self.boxTilt.pack_start(self.entryTiltAngle, expand=False, fill=False)
		self.entryTiltAngle.show()
		# Tilt speed.
		self.entryTiltSpeed = monkeyprintGuiHelper.entry('Tilt speed', self.settings)
		self.boxTilt.pack_start(self.entryTiltSpeed, expand=False, fill=False)
		self.entryTiltSpeed.show()
		
		# Frame for Tilt stepper.
		self.frameBuildStepper = gtk.Frame('Build platform stepper')
		self.boxCol2.pack_start(self.frameBuildStepper, expand=False, fill=False)
		self.frameBuildStepper.show()
		self.boxBuildStepper = gtk.VBox()
		self.frameBuildStepper.add(self.boxBuildStepper)
		self.boxBuildStepper.show()
		# Entries.
		# Resolution.
		self.entryBuildStepsPerMm = monkeyprintGuiHelper.entry('Build steps / mm', self.settings)
		self.boxBuildStepper.pack_start(self.entryBuildStepsPerMm, expand=False, fill=False)
		self.entryBuildStepsPerMm.show()
		# Ramp slope.
		self.entryBuildRampSlope = monkeyprintGuiHelper.entry('Ramp slope', self.settings)
		self.boxBuildStepper.pack_start(self.entryBuildRampSlope, expand=False, fill=False)
		self.entryBuildRampSlope.show()
		# Tilt speed.
		self.entryBuildSpeed = monkeyprintGuiHelper.entry('Build platform speed', self.settings)
		self.boxBuildStepper.pack_start(self.entryBuildSpeed, expand=False, fill=False)
		self.entryBuildSpeed.show()
		
		# Horizontal box for buttons.
		self.boxButtons = gtk.HBox()
		self.boxMain.pack_start(self.boxButtons, expand=False, fill=False)
		self.boxButtons.show()
		
		# Close button.
		self.buttonClose = gtk.Button("Close")
		self.boxButtons.pack_end(self.buttonClose, expand=False, fill=False)
		self.buttonClose.connect("clicked", self.callbackClose)
		self.buttonClose.show()
		
		# Cancel button.
		self.buttonCancel = gtk.Button("Cancel")
		self.boxButtons.pack_end(self.buttonCancel, expand=False, fill=False)
		self.buttonCancel.connect("clicked", self.callbackCancel)
		self.buttonCancel.show()
		
		# Restore defaults button.
		self.buttonDefaults = gtk.Button("Load defaults")
		self.boxButtons.pack_end(self.buttonDefaults, expand=False, fill=False)
		self.buttonDefaults.connect("clicked", self.callbackDefaults)
		self.buttonDefaults.show()

	
	# Serial test function.
	def callbackSerialTest(self, widget, data=None):
		# TODO
		pass
	
	# Defaults function.
	def callbackDefaults(self, widget, data=None):
		# Load default settings.
		self.settings.loadDefaults()
		
	# Cancel function.
	def callbackCancel(self, widget, data=None):
		# Restore values.
		self.settings = self.settingsBackup
		# Close without saving.
		self.destroy()

	# Destroy function.
	def callbackClose(self, widget, data=None):
		# Close and reopen serial if it is open.
		# TODO
		# Close.
		self.destroy()




# Start print dialogue. ########################################################
# Start the dialog, evaluate the check boxes on press of OK and exit,
# or just exit on cancel.
class dialogStartPrint(gtk.Window):
	# Override init function.
	def __init__(self):
		# Call super class init function.
		gtk.Window.__init__(self, gtk.WINDOW_TOPLEVEL)
#		self.show()
		# Set title.
		self.set_title("Ready to print?")
		# Set modal.
		self.set_modal(True)
		# Associate with parent window (no task bar icon, hide if parent is hidden etc)
#TODO	print self.get_parent().get_parent_window()
#TODO	self.set_transient_for(self.get_parent_window())
		self.result = False
		# Create check buttons.
		self.boxCheckbuttons = gtk.VBox()
		self.add(self.boxCheckbuttons)
		self.boxCheckbuttons.show()
		# Checkbutton resin.
		self.checkboxResin = gtk.CheckButton(label="VAT filled with resin?")
		self.boxCheckbuttons.pack_start(self.checkboxResin, expand=True, fill=True)
		self.checkboxResin.set_active(False)
		self.checkboxResin.show()
		# Checkbutton build platform.
		self.checkboxBuild = gtk.CheckButton(label="Build platform empty?")
		self.boxCheckbuttons.pack_start(self.checkboxBuild, expand=True, fill=True)
		self.checkboxBuild.set_active(False)
		self.checkboxBuild.show()
		# Checkbutton 3rd condition.
		self.checkboxCustom = gtk.CheckButton(label="Everything else OK?")
		self.boxCheckbuttons.pack_start(self.checkboxCustom, expand=True, fill=True)
		self.checkboxCustom.set_active(False)
		self.checkboxCustom.show()
	
		# Create OK and Cancel button.
		self.buttonBox = gtk.HBox()
		self.boxCheckbuttons.pack_start(self.buttonBox, expand=False, fill=False)
		self.buttonBox.show()
		self.buttonCancel = gtk.Button("Cancel")
		self.buttonBox.pack_start(self.buttonCancel)
		self.buttonCancel.show()

		self.buttonOK = gtk.Button("OK")
		self.buttonOK.set_sensitive(False)
		self.buttonBox.pack_start(self.buttonOK)
		self.buttonOK.show()

		
		# Set callbacks
		self.buttonOK.connect("clicked", self.callbackOK)
		self.buttonCancel.connect("clicked", self.callbackCancel)
		self.checkboxCustom.connect("toggled", self.checkboxCallback)
		self.checkboxBuild.connect("toggled", self.checkboxCallback)
		self.checkboxResin.connect("toggled", self.checkboxCallback)
		
	def checkboxCallback(self, data=None):
		if self.checkboxResin.get_active() and self.checkboxBuild.get_active() and self.checkboxCustom.get_active():
			self.buttonOK.set_sensitive(True)
		else:
			self.buttonOK.set_sensitive(False)
	
	def callbackOK(self, data=None):
		self.result=True
		self.hide()
		gtk.mainquit()
		
	def callbackCancel(self, data=None):
		self.result=False
		self.hide()
		gtk.mainquit()

	# Create run function to start own main loop.
	# This will wait for button events from the current window.
	def run(self):
		self.set_transient_for(self.parent)
		self.show()
		gtk.mainloop()
		return self.result




# Output console. ##############################################################
# We define the console view and its text buffer 
# separately. This way we can have multiple views that share
# the same text buffer on different tabs...

class consoleText(gtk.TextBuffer):
	# Override init function.
	def __init__(self):
		gtk.TextBuffer.__init__(self)
	# Add text method.
	def addLine(self, string):
		self.insert(self.get_end_iter(),"\n"+string)	


# Creates a text viewer window that automatically scrolls down on new entries.
class consoleView(gtk.Frame):#ScrolledWindow):
	# Override init function.
	def __init__(self, textBuffer):
		gtk.Frame.__init__(self)
		self.show()
		# Create box for content.
		self.box = gtk.VBox()
		self.add(self.box)
		self.box.show()
		
		# Create the scrolled window.
		self.scrolledWindow = gtk.ScrolledWindow()
		self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.box.pack_start(self.scrolledWindow, expand=True, fill=True, padding=5)
		self.scrolledWindow.show()
		# Text view.
		self.textViewConsole = gtk.TextView(buffer=textBuffer)
		self.textViewConsole.set_editable(False)
		self.textViewConsole.set_wrap_mode(gtk.WRAP_WORD)
		self.scrolledWindow.add(self.textViewConsole)
		self.textViewConsole.show()
		# Get text buffer to write to.
#		self.textBuffer = self.textViewConsole.get_buffer()	
		# Insert start up message.
#		self.textBuffer.insert(self.textBuffer.get_end_iter(),"Monkeyprint " + "VERSION")
		# Get adjustment object to rescroll to bottom.
		self.vAdjustment = self.textViewConsole.get_vadjustment()
		# Connect changed signal to rescroll function.
		self.vAdjustment.connect('changed', lambda a, s=self.scrolledWindow: self.rescroll(a,s))

	# Rescroll to bottom if text added.
	def rescroll(self, adj, scroll):
		adj.set_value(adj.upper-adj.page_size)
		scroll.set_vadjustment(adj)

