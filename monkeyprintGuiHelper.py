# -*- coding: latin-1 -*-

import pygtk
pygtk.require('2.0')
import gtk

import numpy
import random
import Image
import inspect	# Provides methdos to check arguments of a function.
import monkeyprintImageHandling as imageHandling
import Queue, threading, subprocess

# Extended gtk notebook that handles sensitivity of its tabs.
# This is done by setting the tab labels' sensitivity and
# checking for this property during the tab switch.
# It also allows one custom function per page that runs
# when the page is switched to.
class notebook(gtk.Notebook):
	
	# Override init function.
	def __init__(self, customFunctions=None):
		# Call superclass init function. Nothing special here...
		gtk.Notebook.__init__(self)
		# Create custom function list to add to.
		self.customFunctions = [None]
		# Connect the page switch signal to a custom event handler.
		# Tab sensitivity checking is done there.
		self.connect("switch-page", self.callbackPageSwitch, customFunctions)
		
	# Function to set tab sensitivity for a given page.
	def set_tab_sensitive(self, page, sens):
		# If given page exists...
		if self.get_nth_page(page) != None:
			# ... set the tab labels' sensititvity according to input.
			self.get_tab_label(self.get_nth_page(page)).set_sensitive(sens)
	
	# Function to retrieve sensitivity for a given page.
	def is_tab_sensitivte(self, page):
		# If given page exists...
		if self.get_nth_page(page) != None:
			return self.get_tab_label(self.get_nth_page(page)).get_sensitive()
	
	# Set a page specific custom function to be called on page switch.
	def set_custom_function(self, page, fcn):
		# Add the function to the list at the index specified by page.
		# If page > list length, add at end and fill with Nones.
		listIndexMax = len(self.customFunctions)-1	
		# If the function will be placed for a page that is
		# beyond the function list index...
		if page > listIndexMax and page < self.get_n_pages():
			# ... append nones until just before page index...
			for i in range((page-1)-listIndexMax):
				self.customFunctions.append(None)
			# ... and append page specific function.
			self.customFunctions.append(fcn)
		# If the function is placed in an existing list item...
		elif page <= listIndexMax and page < self.get_n_pages():
			# ... simply drop it there.
			self.customFunctions[page] = fcn

	# Get current page.
	def getCurrentPage(self):
		return self.get_current_page()
	
	# Set current page.
	def setCurrentPage(self, page):
		self.set_current_page(page)
		
	# Define tab change actions.
	# Tab change event. The actual tab change will commence at the end of this function.
	# Callback takes four mysterious arguments (parent, notebook, page, page index?).
	# Last argument is the current tab index.
	def callbackPageSwitch(self, notebook, page, pageIndex, customFunc):
		# Handle tab sensitivity.
		# If the switch was made to an insensitive tab (the requested pageIndex)...
		if self.is_tab_sensitivte(pageIndex)==False:
			# ... change to previously selected tab.
			pageIndex = self.get_current_page() # Current page still points to the old page.
			# Stop the event handling to stay on current page.
			self.stop_emission("switch-page")
		# Run the custom function corresponding to the current page index.
		if len(self.customFunctions) > pageIndex and self.customFunctions[pageIndex] != None:
			self.customFunctions[pageIndex]()






# Slider that takes image which has to be update externally.
class imageSlider(gtk.VBox):
	def __init__(self, modelCollection, programSettings, console=None, customFunctions=None):
		# Call super class init function.
		gtk.VBox.__init__(self)
		
		# Internalise parameters.
		self.modelCollection = modelCollection
		self.console = console
		self.customFunctions = customFunctions
		
		# Reference to image.
#		self.image = self.modelCollection.sliceImage
		
		# Get parent width and set height according to projector aspect ratio.
		aspect = float(programSettings['Projector size Y'].value) / float(programSettings['Projector size X'].value)
		self.width = 250
		self.height = int(self.width * aspect)
		
		
		# Create image view.
		self.imageView = gtk.Image()
		# Create black dummy image.
		self.imageBlack = numpy.zeros((self.height, self.width, 3), numpy.uint8)
		# Create pixbuf from numpy.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageBlack, gtk.gdk.COLORSPACE_RGB, 8)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)
		self.pack_start(self.imageView, expand=True, fill=True)
		self.imageView.show()
		
		# Create slider.
		self.slider = gtk.HScrollbar()
		self.pack_start(self.slider, expand=True, fill=True)
		self.slider.set_range(1,100)
		self.slider.set_value(1)
		self.slider.set_round_digits(0)
		self.slider.show()
		# Connect event handler. We only want to update if the button was released.
		self.slider.connect("value-changed", self.callbackScroll)
#		self.slider.connect("button-release-event", self.callbackScroll)

		# Create current slice label.
		self.labelBox = gtk.HBox()
		self.pack_start(self.labelBox, expand=True, fill=True)
		self.labelBox.show()
		# Create labels.
		self.minLabel = gtk.Label('1')
		self.labelBox.pack_start(self.minLabel, expand=False)
		self.minLabel.show()
		self.currentLabel = gtk.Label('1')
		self.labelBox.pack_start(self.currentLabel, expand=True, fill=True)
		self.currentLabel.show()
		self.maxLabel = gtk.Label('1')
		self.labelBox.pack_start(self.maxLabel, expand=False)
		self.maxLabel.show()
		

	# Update image if the slider is at the given position in the stack.
	def updateImage(self):
		# Call function to update the image.
		img = self.modelCollection.updateSliceImage(self.slider.get_value()-1)
		# Get the image from the slice buffer and convert it to 3 channels.
		img = imageHandling.convertSingle2RGB(img)
		# Write image to pixbuf.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(img, gtk.gdk.COLORSPACE_RGB, 8)
		# Resize the image.
		self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_NEAREST)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)


	# Handle the scroll event by displaying the respective imageArray
	# from the image stack.
	def callbackScroll(self, widget=None, event=None):
		# Call function to update the image.
		img = self.modelCollection.updateSliceImage(self.slider.get_value()-1)
		# Get the image from the slice buffer and convert it to 3 channels.
		img = imageHandling.convertSingle2RGB(img)
		# Write image to pixbuf.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(img, gtk.gdk.COLORSPACE_RGB, 8)
		# Resize the pixbuf.
		self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)#INTERP_NEAREST)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)	
		# Set current page label.
		self.currentLabel.set_text(str(int(self.slider.get_value())))	
		# Call custom functions if specified.
		if self.customFunctions != None:
			for function in self.customFunctions:
				# Check if function wants sliceNumber argument.
				val = None
				for arg in inspect.getargspec(function)[0]:
					if arg == 'sliceNumber':
						val = self.slider.get_value()
				# Run function.
				if val != None: function(val)
				else: function()
		
	# Change the slider range according to input.
	def updateSlider(self):
		height = self.modelCollection.getNumberOfSlices()
		if self.console != None:
			self.console.addLine('Resizing layer slider to ' + str(height) + ' slices.')
		# Change slider value to fit inside new range.
		if self.slider.get_value() > height:
			self.slider.set_value(height)
		# Resize slider.
		if height > 0:
			self.slider.set_range(1,height)
		self.maxLabel.set_text(str(height))







# A text entry including a label on the left. #################################
# Will call a function passed to it on input. Label, default value and
# callback function are taken from the settings object.

class entry(gtk.HBox):
	# Override init function.
#	def __init__(self, string, settings, function=None):
	def __init__(self, string, settings=None, modelCollection=None, customFunctions=None, width=None):
		# Call super class init function.
		gtk.HBox.__init__(self)
		self.show()
		
		self.string = string
#		self.settings = settings
		self.modelCollection = modelCollection
		# Get settings of default model which is the only model during GUI creation.
		if self.modelCollection != None:
			self.settings = modelCollection.getCurrentModel().settings
		# If settings are provided instead of a model collection this is a
		# printer settings entry.
		elif settings != None:
			self.settings = settings
			
		self.customFunctions = customFunctions
		
		# Make label.
		self.label = gtk.Label(string+self.settings[string].unit)
		self.label.set_justify(gtk.JUSTIFY_LEFT)
		self.pack_start(self.label, expand=True, fill=True)
		self.label.show()
		
		# Make text entry.
		self.entry = gtk.Entry()
		self.pack_start(self.entry, expand=False, fill=False)
		self.entry.show()
		if width == None:
			self.entry.set_width_chars(7)
		else:
			self.entry.set_width_chars(width)
		
		# Set entry text.
		self.entry.set_text(str(self.settings[string].value))
		
		# A bool to track if focus change was invoked by Tab key.
		self.tabKeyPressed = False
			
		# Set callback connected to Enter key and focus leave.
		#self.entry.connect("activate", self.entryCallback, entry)
		self.entry.connect("key-press-event", self.entryCallback, entry)
		self.entry.connect("focus_out_event", self.entryCallback, entry)
	
	
		
	def entryCallback(self, widget, event, entry):
		# Callback provides the following behaviour:
		# Return key sets the value and calls the function.
		# Tab key sets the value and calls the function.
		# Focus-out resets the value if the focus change was not invoked by Tab key.
		# Note: Tab will first emit a key press event, then a focus out event.
#		if event.type.value_name == "GDK_FOCUS_CHANGE" and self.entry.has_focus()==False:
#			print 'foo'
#		elif event.type.value_name == "GDK_KEY_PRESS" and event.keyval == gtk.keysyms.Return:
#			print 'bar'
		# GDK_FOCUS_CHANGE is emitted on focus in or out, so make sure the focus is gone.
		# If Tab key was pressed, set tabKeyPressed and leave.
		if event.type.value_name == "GDK_KEY_PRESS" and event.keyval == gtk.keysyms.Tab:
			self.tabKeyPressed = True
			return
		# If focus was lost and tab key was pressed or if return key was pressed, set the value.
		if (event.type.value_name == "GDK_FOCUS_CHANGE" and self.entry.has_focus()==False and self.tabKeyPressed) or (event.type.value_name == "GDK_KEY_PRESS" and event.keyval == gtk.keysyms.Return):
			# Set value.
			# In case a model collection was provided...
			if self.modelCollection != None:
				# ... set the new value in the current model's settings.
				self.modelCollection.getCurrentModel().settings[self.string].setValue(self.entry.get_text())
				# Call the models update function. This might change the settings value again.
#				# Call the custom functions specified for the setting.
#				if self.customFunctions != None:
#					for function in self.customFunctions:
#						function()
				# Set the entrys text field as it might have changed during the previous function call.
				self.entry.set_text(str(self.modelCollection.getCurrentModel().settings[self.string].value))
			# If this is not a model setting but a printer setting...
			elif self.settings != None:
				# ... write the value to the settings.
				self.settings[self.string].setValue(self.entry.get_text())
				# Set the entry text in case the setting was changed by settings object.
				self.entry.set_text(str(self.settings[self.string].value))
			# Call the custom functions specified for the setting.
			if self.customFunctions != None:
				for function in self.customFunctions:
					function()
			# Reset tab pressed bool.
			self.tabKeyPressed = False
			return
		# If focus was lost without tab key press, reset the value.
		elif event.type.value_name == "GDK_FOCUS_CHANGE" and self.entry.has_focus()==False:
			#Reset value.
			if self.modelCollection != None:
				self.entry.set_text(str(self.modelCollection.getCurrentModel().settings[self.string].value))
			elif self.settings != None:
				self.entry.set_text(str(self.settings[self.string].value))
			return

		
	# Update the value in the text field if current model has changed.	
	def update(self):
		# If this is a model setting...
		if self.modelCollection != None:
			self.entry.set_text(str(self.modelCollection.getCurrentModel().settings[self.string].value))
		else:
			self.entry.set_text(str(self.settings[self.string].value))
			
		
'''		
# Slider that takes image stack.
class imageSlider2(gtk.VBox):
	def __init__(self, imageStack, programSettings, console=None, customFunctions=None):
		# Call super class init function.
		gtk.VBox.__init__(self)
		
		# Internalise parameters.
		self.imageStack = imageStack
		self.console = console
		self.customFunctions = customFunctions
		
		# Get parent width and set height according to projector aspect ratio.
		aspect = float(programSettings['Projector size Y'].value) / float(programSettings['Projector size X'].value)
		print aspect
		self.width = 240
		self.height = int(self.width * aspect)
		print self.height
		
		
		# Create image view.
		self.imageView = gtk.Image()
		# Create random noise image.
		self.imageRandom = numpy.random.rand(self.height, self.width, 3) * 255
		self.imageRandom = numpy.uint8(self.imageRandom)
		# Create black dummy image.
		self.imageBlack = numpy.zeros((self.height, self.width, 3), numpy.uint8)
		# Create pixbuf from numpy.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageRandom, gtk.gdk.COLORSPACE_RGB, 8)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)
		self.pack_start(self.imageView, expand=True, fill=True)
		self.imageView.show()
		
		# Create slider.
		self.slider = gtk.HScrollbar()
		self.pack_start(self.slider, expand=True, fill=True)
		self.slider.set_range(1,100)
		self.slider.set_value(1)
		self.slider.set_round_digits(0)
		self.slider.show()
		# Connect event handler. We only want to update if the button was released.
		self.slider.connect("value-changed", self.callbackScroll)
#		self.slider.connect("button-release-event", self.callbackScroll)

		# Create current slice label.
		self.labelBox = gtk.HBox()
		self.pack_start(self.labelBox, expand=True, fill=True)
		self.labelBox.show()
		# Create labels.
		self.minLabel = gtk.Label('1')
		self.labelBox.pack_start(self.minLabel, expand=False)
		self.minLabel.show()
		self.currentLabel = gtk.Label('1')
		self.labelBox.pack_start(self.currentLabel, expand=True, fill=True)
		self.currentLabel.show()
		self.maxLabel = gtk.Label('1')
		self.labelBox.pack_start(self.maxLabel, expand=False)
		self.maxLabel.show()
		

	# Update image if the slider is at the given position in the stack.
	def updateImage(self, position):
		if position+1 == self.slider.get_value():
			# Get the image from the slice buffer.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageStack.getImage(self.slider.get_value()-1), gtk.gdk.COLORSPACE_RGB, 8)
			# Resize the image.
			self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)#INTERP_NEAREST)
			# Set image to viewer.
			self.imageView.set_from_pixbuf(self.pixbuf)


	# Handle the scroll event by displaying the respective imageArray
	# from the image stack.
	def callbackScroll(self, widget=None, event=None):
		# Get the image from the slice buffer and convert it to 3 channels.
		img = imageHandling.convertSingle2RGB(self.imageStack.getImage(int(self.slider.get_value()-1)))
		# Write image to pixbuf.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(img, gtk.gdk.COLORSPACE_RGB, 8)
		# Resize the pixbuf.
		self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_NEAREST)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)	
		# Set current page label.
		self.currentLabel.set_text(str(int(self.slider.get_value())))	
		# Call custom functions if specified.
		if self.customFunctions != None:
			for function in self.customFunctions:
				# Check if function wants sliceNumber argument.
				val = None
				for arg in inspect.getargspec(function)[0]:
					if arg == 'sliceNumber':
						val = self.slider.get_value()
				# Run function.
				if val != None: function(val)
				else: function()
		
	# Change the slider range according to input.
	def updateSlider(self):
		if self.console != None:
			self.console.addLine('Resizing layer slider to ' + str(self.imageStack.getNumberOfSlices()) + ' slices.')
		# Change slider value to fit inside new range.
		if self.slider.get_value() > self.imageStack.getNumberOfSlices():
			self.slider.set_value(self.imageStack.getNumberOfSlices())
		# Resize slider.
		if self.imageStack.getNumberOfSlices() > 0:
			self.slider.set_range(1,self.imageStack.getNumberOfSlices())
		self.maxLabel.set_text(str(int(self.imageStack.getNumberOfSlices())))
'''





class printProgressBar(gtk.ProgressBar):
	def __init__(self, sliceQueue=None):
		gtk.ProgressBar.__init__(self)
		self.limit = 1.
		self.sliceQueue = sliceQueue
		
	def setLimit(self, limit):
		self.limit = float(limit)
	
	def setText(self, text):
		self.set_text(text)
	
	def updateValue(self, value=None):
		# Get the value from the queue.
		if self.sliceQueue!=None and self.sliceQueue.qsize():
			value = self.sliceQueue.get()
		# Update progress bar if value existant.
		if value != None:
			frac = float(value/self.limit)
			self.set_fraction(frac)






# Output console. ##############################################################
# We define the console view and its text buffer 
# separately. This way we can have multiple views that share
# the same text buffer on different tabs...

class consoleText(gtk.TextBuffer):
	# Override init function.
	def __init__(self, lineLenght = None):
		gtk.TextBuffer.__init__(self)
	# Add text method with auto line break.
	def addLine(self, string):
		self.insert(self.get_end_iter(),"\n"+string)	
	# Add a string without line break.
	def addString(self, string):
		# Get line length.
		# If line end not reached yet (inlcuding new string)...
		#TODO
		# Insert string.
		self.insert(self.get_end_iter(), string)


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
		
		# Pack an empty label as the frame label.
		# Otherwise corners are not round. Strange...
		label = gtk.Label()
		self.set_label_widget(label)
		
		# Create the scrolled window.
		self.scrolledWindow = gtk.ScrolledWindow()
		self.scrolledWindow.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_ALWAYS)
		self.box.pack_start(self.scrolledWindow, expand=True, fill=True)
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


class avrdudeThread(threading.Thread):
	# Override init function.
	def __init__(self, settings, queue):
		# Internalise parameters.
		self.settings = settings
		self.queue = queue
		# Call super class init function.
		super(avrdudeThread, self).__init__()
	
	# Override run function.
	def run(self):
		# Create avrdude commandline string.
		avrdudeCommandList = [	'avrdude',
							'-p', self.settings['MCU'].value,
							'-P', self.settings['Port'].value,
							'-c', self.settings['Programmer'].value,
							'-b', str(self.settings['Baud'].value),
							'-U', 'flash:w:' + self.settings['Firmware path'].value
							]
		# Append additional options.
		optionList = self.settings['Options'].value.split(' ')
		for option in optionList:
			avrdudeCommandList.append(option)
		# Call avrdude and get its output.
		# Redirect error messages to stdout and stdout to PIPE
		avrdudeProcess = subprocess.Popen(avrdudeCommandList, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
		output = avrdudeProcess.communicate()[0]
		# If an error occured...
		if avrdudeProcess.returncode !=0:
			#... write error message to queue.
			message = "Error code: " + str(avrdudeProcess.returncode) + "\n" + "Error message: " + output + "\n" + "Make sure the Arduino is connected correctly."
			self.queue.put(message)
		# In case of success...
		else:
			# ... write success message to queue.
			message = output + "\n" + "Firmware flashed successfully!"
			self.queue.put(message)




class projectorDisplay(gtk.Window):
	def __init__(self, settings):
		gtk.Window.__init__(self)
		
		# Internalise parameters.
		self.settings = settings
		
		# Customise window.
		# No decorations.
		self.set_decorated(False)#gtk.FALSE)
		# Size and position according to settings.
		self.resize(self.settings['Projector size X'].value,self.settings['Projector size Y'].value)
		self.move(self.settings['Projector position X'].value,self.settings['Projector position Y'].value)
		self.show()
		
		# Queue for getting slice images from print process thread.
		self.queueSliceImage = Queue.Queue()
		
		
	
	def stop(self):
		self.destroy()
	
	def updateSlice(self):
		pass
	
		
