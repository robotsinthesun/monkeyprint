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

import pygtk
pygtk.require('2.0')
import gtk, gobject
import cairo
from math import pi

import PyQt4
from PyQt4 import QtGui, QtCore
from PyQt4.QtCore import Qt

import sys
import time
import os.path
import shutil
import numpy
import random
from PIL import Image
import inspect	# Provides methdos to check arguments of a function.
import monkeyprintImageHandling as imageHandling
import monkeyprintPrintProcess
import Queue, threading, subprocess



# Button convenience class.
class button(QtGui.QPushButton):
	def __init__(self, label, callback):
		# Call super class init function.
		QtGui.QPushButton.__init__(self, label)
		# Internalise values.
		self.callback = callback
		self.label = label
		# Set label.
		self.setText(label)
		# Set callback.
		QtCore.QObject.connect(self, QtCore.SIGNAL("clicked()"), self.callback)

# Check button convenience class.
class checkbox(QtGui.QCheckBox):
	def __init__(self, label, callback, initialState=False):
		# Call super class init function.
		QtGui.QCheckBox.__init__(self, label)
		# Internalise values.
		self.callback = callback
		# Set label.
		self.setText(label)
		# Set state.
		self.setChecked(initialState)
		# Set callback.
		self.stateChanged.connect(self.callbackInternal)
		#QtCore.QObject.connect(self, QtCore.SIGNAL("clicked()"), functools.partial(self.callback, self))

	def callbackInternal(self):
		self.callback(self.isChecked())


# A text entry including a label on the left. ##################################
# Will call a function passed to it on input. Label, default value and
# callback function are taken from the settings object.

class entry(QtGui.QHBoxLayout):
	# Override init function.
#	def __init__(self, string, settings, function=None):
	def __init__(self, string, settings=None, modelCollection=None, customFunctions=None, width=None, displayString=None):
		# Call super class init function.
		QtGui.QHBoxLayout.__init__(self)
		
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
		
		
		# Create the label string.
		if displayString != None:
			self.labelString = displayString+self.settings[string].unit
		elif self.settings[self.string].name != None:
			self.labelString = self.settings[self.string].name + self.settings[string].unit
		else:
			self.labelString = string+self.settings[string].unit

		
		# Make label.
		self.label = QtGui.QLabel(self.labelString)
	#	if displayString != None:
	#		self.label = gtk.Label(displayString+self.settings[string].unit)
	#	else:
	#		self.label = gtk.Label(string+self.settings[string].unit)
	#	self.label.set_alignment(xalign=0, yalign=0.5)
		self.addWidget(self.label)#, expand=True, fill=True, padding=5)
	#	self.label.show()
		self.addStretch(1)
		
		# Make text entry.
		self.entry = QtGui.QLineEdit()
		self.addWidget(self.entry)
	#	self.pack_start(self.entry, expand=False, fill=False, padding=5)
		#self.entry.show()
		if width == None:
			self.entry.setFixedWidth(50)
		else:
			self.entry.setFixedWidth(width)
		
		# Set entry text.
		# TODO
		self.entry.setText(str(self.settings[string].value))
		
		# TODO
		# A bool to track if focus change was invoked by Tab key.
	#	self.tabKeyPressed = False
			
		# Set callback connected to Enter key and focus leave.
		#self.entry.connect("activate", self.entryCallback, entry)
	#	self.entry.connect("key-press-event", self.entryCallback, entry)
	#	self.entry.connect("focus_out_event", self.entryCallback, entry)
	
		'''
		
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
		if (event.type.value_name == "GDK_FOCUS_CHANGE" and self.entry.has_focus()==False and self.tabKeyPressed) or (event.type.value_name == "GDK_KEY_PRESS" and (event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter)):
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
				# Set model changed flag in model collection. Needed to decide if slicer should be started again.
				self.modelCollection.getCurrentModel().setChanged()
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
		'''
		
	# Update the value in the text field if current model has changed.	
	def update(self):
		# If this is a model setting...
		if self.modelCollection != None:
			self.entry.setText(str(self.modelCollection.getCurrentModel().settings[self.string].value))
		else:
			self.entry.setText(str(self.settings[self.string].value))






#*******************************************************************************
# String class that emits a signal on content changes. *************************
#*******************************************************************************
class consoleText(QtCore.QObject):
	changed = QtCore.pyqtSignal()
	# Init function.
	def __init__(self):
		QtCore.QObject.__init__(self)
		self.text = QtCore.QString()
		
	# Add text method with auto line break.
	def addLine(self, string):
		self.text += "\n"+string
		self.changed.emit()
		
	# Add a string without line break.
	def addString(self, string):
		self.text += string
		self.changed.emit()
		




#*******************************************************************************
# Creates a view for the model list including add and remove buttons.
#*******************************************************************************		
class modelTableView(QtGui.QWidget):

	def __init__(self):
		#Init the base class
		#QtGui.QWidget.__init__(self)
		super(modelTableView, self).__init__()
		
		self.box = QtGui.QVBoxLayout()
		self.setLayout(self.box)
		
		self.tableView = QtGui.QTableView()
		# Select whole rows instead of individual cells.
		self.tableView.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
		# Hide the cell grid.
		self.tableView.setShowGrid(False)
		# Hide the vertical headers.
		self.tableView.verticalHeader().hide()
		# Set the row height.
		self.tableView.verticalHeader().setDefaultSectionSize(20)
		# Hide the grey dottet line of the item in focus.
		# This will disable focussing, so no keyboard events can be processed.
		self.tableView.setFocusPolicy(QtCore.Qt.NoFocus)
		# Prevent the header font from being made bold if a row is selected.
		self.tableView.horizontalHeader().setHighlightSections(False)
		
		self.box.addWidget(self.tableView)
		self.boxButtons = QtGui.QHBoxLayout()
		self.box.addLayout(self.boxButtons)
		self.buttonAdd = QtGui.QPushButton("Add")
		self.buttonAdd.clicked.connect(self.callbackButtonAdd)
		self.boxButtons.addWidget(self.buttonAdd)
		self.buttonRemove = QtGui.QPushButton("Remove")
		self.buttonRemove.clicked.connect(self.callbackButtonRemove)
		self.boxButtons.addWidget(self.buttonRemove)

		
		self.slicerStatus = 0
 
		data = [["foo", 100, "hoo", True], ["bar", 50, "har", False]]
		self.model = tableModel(data, 2)#QtGui.QStandardItemModel()
		#self.model.setHorizontalHeaderLabels(['Model', 'Active'])
		self.tableView.setModel(self.model)
		
		self.model.updateSlicerStatus(85,1)

		#self.listView.setUniformRowHeights(True)
		#self.model = QtGui.QFileSystemModel()
		#self.model.setRootPath( QtCore.QDir.currentPath() )

		#self.listView.selectionModel().selectionChanged.connect(self.selectionChanged)
	#	QtCore.QObject.connect(self.tableView.selectionModel(), QtCore.SIGNAL('selectionChanged(QItemSelection, QItemSelection)'), self.test)

		self.timer = QtCore.QTimer()
		self.timer.timeout.connect(self.updateSlicerStatus)
		self.timer.start(10)


	'''
	@QtCore.pyqtSlot("QItemSelection, QItemSelection")
	def test(self, selected, deselected):
		print("Selection changed.")
		print self.tableView.selectedIndexes()
		if len(self.tableView.selectedIndexes()) < 1:
			
			print "Nothing selected."
		#	self.tableView.selectionModel().select(self.listView.indexAt(0), QtGui.QItemSelectionModel.Select | QtGui.QItemSelectionModel.Rows)
		#print(deselected)
	'''
	# Method to add a new model.
	# Create a 
	def callbackButtonAdd(self):
		print "Adding model."
		self.model.insertRows(["hoo", 5, "har", False], position=len(self.model.tableData), rows=1)
		'''
		item = QtGui.QStandardItem('Model name'.format(0))
		self.model.appendRow(['foo'])
		'''
		'''
		item.setCheckable(True)
		self.model.appendRow(item)
		# Get new item's index.
		index = self.model.indexFromItem(item)
		# Select new row.
		self.tableView.clearSelection()
		self.tableView.selectionModel().select(index, QtGui.QItemSelectionModel.Select | QtGui.QItemSelectionModel.Rows)
		self.tableView.scrollToBottom()
		'''
		
	def callbackButtonRemove(self):
		print "remove"
		# TODO: remove the selected row.
		self.model.removeRow(0)
		# TODO: select the next row or the last one remaining.
		'''
		if len(self.tableView.selectedIndexes()) > 0:
			index = self.tableView.selectedIndexes()[0]
			item = index.model().itemFromIndex(index)
			self.model.removeRow(item.row())
		'''

	def removeAll(self):	
		self.model.clear()

	def on_item_changed(self, item):
		print "Item " + str(item.row()) + " changed into: " + item.text() +  "."
		# print "foo"
		# If the changed item is not checked, don't bother checking others
		if not item.checkState():
			return

	def updateSlicerStatus(self):
		if self.slicerStatus == 100:
			self.slicerStatus = 0
		else:
			self.slicerStatus += 1
		self.model.updateSlicerStatus(self.slicerStatus,0)
		
		
		
		
		
#*******************************************************************************
# Creates a view for the model list including add and remove buttons.
#*******************************************************************************
# Custom table model.
# Data carries the following columns:
# Stl name, slicer status, internal stl name, stl path, model acitve flag.
class tableModel(QtCore.QAbstractTableModel):
	
	def __init__(self, tableData, numDispCols, parent = None, *args):
		QtCore.QAbstractTableModel.__init__(self, parent, *args)
		
		self.tableData = tableData
		self.numDispCols = numDispCols
	
	# This will be called by the view to determine the number of rows to show.
	def rowCount(self, parent):
		return len(self.tableData)
		
	# This will be called by the view to determine the number of columns to show.
	# We only want to show a certain number of columns, starting from 0 and
	# ending at numDispCols
	def columnCount(self, parent):
		if len(self.tableData) > 0:
			if self.numDispCols <= len(self.tableData[0]):
				return self.numDispCols
			else:
				return len(self.tableData[0])
		else:
			return 0

	# This gets called by the view to get the data at the given index.
	# Based on the row and column number retrieved from the index, we
	# assign different roles the the returned data. This predicts how the data
	# is shown. The view will request all roles and if the requested one matches
	# the one we want to show for the given index, we'll return it.
	# DisplayRole will show the data, all other roles will modify the display.
	def data(self, index, role):
		# Return nothing if index is invalid.
		if not index.isValid():
			return QtCore.QVariant()
		# Get row and column.
		row = index.row()
		column = index.column()
		
		# Return the data.
		if role == Qt.DisplayRole:
			if column == 0:
				return QtCore.QVariant(self.tableData[index.row()][index.column()])
			elif column == 1:
				return QtCore.QVariant(str(self.tableData[index.row()][index.column()]) + " %")
		
		# If user starts editing the cell by double clicking it, also return the data.
		# Otherwise cell will be empty once editing is started.
		if role == Qt.EditRole:
			return QtCore.QVariant(self.tableData[index.row()][index.column()])

		# Return the picture for slicer status bar if the view asks for a 
		# decoration role.
		elif role == Qt.DecorationRole:
			if column == 1:
				# Bar size.
				barWidth = 50
				barHeight =10
				# Set the color depending on the slicer status.
				# Small: red, medium: yellow, high: green.
				if self.tableData[row][1] < barWidth * (100./barWidth) * 0.1:
					color = 0xFF0000
				elif self.tableData[row][1] > barWidth * (100./barWidth) * 0.95:
					color = 0x64FF00
				else:
					color = 0xFFC800
				# Create image.
				img = QtGui.QImage(barWidth, barHeight, QtGui.QImage.Format_RGB888)
				img.fill(0xFFFFFF)

				for h in range(barHeight):
					for w in range(barWidth):
						if w*(100./barWidth) < self.tableData[row][1]:
							img.setPixel(w,h,color)
				
				'''
				# DOES NOT WORK.
				# That's because the bardata array
				# will be deleted after the data() method has returned.
				# The memory of the img will be overwritten and result in
				# noise.
				barWidth = 50
				barHeight =6
				# Create a numpy array of 100 x 1 pixels.
				barData = numpy.ones((barHeight,barWidth,3), dtype = numpy.uint8)*255
				
				# Set the color depending on the slicer status.
				# Small: red, medium: yellow, high: green.
				if self.tableData[row][1] < barWidth * (100./barWidth) * 0.1:
					color = [255,255,0]#0xFFFF00
				elif self.tableData[row][1] > barWidth * (100./barWidth) * 0.95:
					color = [100,255,0]#0x80FF00
				else:
					color = [255,200,0]#0x00D0FF
				# Loop through image columns and set pixel color.
				barData = numpy.swapaxes(barData,0,1)
				for i in range(barData.shape[0]):
					if i*(100./barWidth) < self.tableData[row][1]:
						barData[i] = color
				barData = numpy.swapaxes(barData,0,1)
				
				print barData
				
				# Convert to image.
				img = QtGui.QImage(barData.DeepCopy(), barData.shape[1], barData.shape[0], barData.strides[0], QtGui.QImage.Format_RGB888)
				'''
				return img
		
		# Add a check box to all rows in column 1.
		# Set the checkbox state depending on the data in column 3.
		elif role == Qt.CheckStateRole:
			if column == 0:
				#print self.tableData[row][3]
				if self.tableData[row][3]:
					return Qt.Checked
				else:
					return Qt.Unchecked
		
		# Return tooltip.
		elif role == Qt.ToolTipRole:
			if column == 0:
				return "Use the check box to enable or disable this model.\nDouble click to rename."
			else:
				return "Current slicer status."
		
		# Return alignment.
		elif role == Qt.TextAlignmentRole:
			#print column
			if column == 1:
				return Qt.AlignRight + Qt.AlignVCenter
			else:
				return Qt.AlignLeft + Qt.AlignVCenter
		'''
		# Return background color.
		elif role == Qt.BackgroundRole:
			if column == 1:
				red = QtGui.QBrush(Qt.red);
				return red;
		'''
		# If none of the conditions is met, return nothing.
		return QtCore.QVariant()
	
	# Provide header strings for the horizontal headers.
	# Vertical headers are empty.
	# Role works the same as in data().
	def headerData(self, section, orientation, role):
		if role == Qt.DisplayRole:
			if orientation == Qt.Horizontal:
				if section == 0:
					return QtCore.QString("Model")
				elif section == 1:
					return QtCore.QString("Slicer status")
	
	# This is called once user editing of a cell has been completed.
	# The value is the new data that has to be manually set to the
	# tableData within the setData method.
	def setData(self, index, value, role=Qt.EditRole):
		row = index.row()
		column = index.column()
		if role == Qt.EditRole:
			self.tableData[row][column] = value
		elif role == Qt.CheckStateRole:
			if value == Qt.Checked:
				self.tableData[row][3] = Qt.Checked
			elif value == Qt.Unchecked:
				self.tableData[row][3] = Qt.Unchecked
		# Emit the data changed signal to let possible other views that
		# didn't do the editing know about the changed data.
		self.dataChanged.emit(index, index)
		return True
	
	# This will be called by the view to determine if the cell that
	# has been clicked is enabled, editable, checkable, selectable and so on.
	def flags(self, index):
		# Get row and column.
		row = index.row()
		column = index.column()
		
		if column < 1:
			return Qt.ItemIsSelectable |  Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsUserCheckable ;
		else:
			return Qt.ItemIsEnabled | Qt.ItemIsSelectable
	
	# This is called for inserting a row.
	# Position: where to insert, rows: how many to insert,
	# parent: who will be parent in a tree view?
	# beginInsertRows(index, first, last) tells the views where data is inserted.
	# index is for hierarchical data, so we pass an empty QModelIndex, that
	# points to the root index.
	def insertRows(self, data, position, rows, parent=QtCore.QModelIndex()):
		self.beginInsertRows(parent, position, position+rows-1)
		for i in range(rows):
			if len(data) == 4:
				self.tableData.insert(position, data)
		self.endInsertRows()
		return True
	
	# This is called for removing a row.
	# Position: where to insert, rows: how many to insert,
	# parent: who will be parent in a tree view?
	def removeRows(self, position, rows, parent=QtCore.QModelIndex()):
		self.beginRemoveRows(parent, position, position+rows-1)
		for i in range(rows):
			# Remove method takes a value, not and index.
			# So get the value first...
			value = self.tableData[position]
			#... and remove it.
			self.tableData.remove(value)
			
		self.endRemoveRows()
		return True
	
	# Delete all the data.
	#TODO: leave "default" model in table data upon clearing?
	#def clearData(self):
	#	if len(self.tableData) != 0:
	#		self.beginRemoveRows(QModelIndex(), 0, len(self.tableData) - 1)
	#		self.tableData = []
	#		self.endRemoveRows()

	
		
	# Provide a new value for the slicer status of a given row.
	# Slicer status is in column 1.
	def updateSlicerStatus(self, percentage, row):
		# Set the data.
		self.tableData[row][1] = percentage
		# Create index for the changed cell.
		index = self.createIndex(row, 1)
		# Emit data changed signal to update all views since we changed the data manually.
		self.dataChanged.emit(index, index)




#*******************************************************************************
# Creates a text viewer that automatically updates if the referenced string is
# emitting a changed signal.
#*******************************************************************************
class consoleView(QtGui.QVBoxLayout):
	# Override init function.
	def __init__(self, textBuffer):
		QtGui.QVBoxLayout.__init__(self)
		# Internalise.
		self.textBuffer = textBuffer
		
		# Connect to text buffers changed signal.
		# First, make a slot function.
		@QtCore.pyqtSlot()
		def textChanged():
			self.update()
		# Then, we connect the slot to the changed signal of the text buffer.
		self.textBuffer.changed.connect(textChanged)
		
		# Create box for content.
		self.frame = QtGui.QGroupBox("Output log")
		self.addWidget(self.frame)

		self.box = QtGui.QVBoxLayout()
		self.frame.setLayout(self.box)
		
		self.textBrowser = QtGui.QTextBrowser()
		self.box.addWidget(self.textBrowser)
		
		self.update()
	
	def update(self):
		self.textBrowser.clear()
		self.textBrowser.append(self.textBuffer.text)
		




#*******************************************************************************
# Creates a notebook for the settings tabs.
#*******************************************************************************
class notebook(QtGui.QTabWidget):
	def __init__(self, customFunctions=None):
		# Call super class init function.
		QtGui.QTabWidget.__init__(self)
		
		# Create custom function list to add to.
		self.customFunctions = [None]
		
		# Connect the page switch signal to a custom event handler.
		# Tab sensitivity checking is done there.
		self.connect(self, QtCore.SIGNAL("currentChanged(int)"), self.callbackPageSwitch)

	#	self.box = QtGui.QVBoxLayout()
	#	self.setLayout(self.box)
		'''
	def add(self, custo)

		self.tabWidget.addTab(QtGui.QWidget(),'Tab_01')
        self.tabWidget.addTab(QtGui.QWidget(),'Tab_02')
        self.tabWidget.addTab(QtGui.QWidget(),'Tab_03')          



	def tabSelected(self, arg=None):
		print '\n\t tabSelected():', arg

	def whatTab(self):
		print '\n\t current Tab:', '?'
        
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
		'''
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
		'''
	# Get current page.
	def getCurrentPage(self):
		return self.get_current_page()
	
	# Set current page.
	def setCurrentPage(self, page):
		self.set_current_page(page)
	'''	
	# Define tab change actions.
	# Tab change event. The actual tab change will commence at the end of this function.
	# Callback takes four mysterious arguments (parent, notebook, page, page index?).
	# Last argument is the current tab index.
	def callbackPageSwitch(self, data):
		# Handle tab sensitivity.
		print data
		
		'''
		# If the switch was made to an insensitive tab (the requested pageIndex)...
		if self.is_tab_sensitivte(pageIndex)==False:
			# ... change to previously selected tab.
			pageIndex = self.get_current_page() # Current page still points to the old page.
			# Stop the event handling to stay on current page.
			self.stop_emission("switch-page")
		# Run the custom function corresponding to the current page index.
		if len(self.customFunctions) > pageIndex and self.customFunctions[pageIndex] != None:
			self.customFunctions[pageIndex]()
		'''
		'''
		'''
'''

# A simple GTK splash window that destroys itself after a given period.
class splashWindow:
	def __init__(self, imageFile, duration=1, infoString=None):
		
		
		# Create pixbuf from file.
		self.pixbuf = gtk.gdk.pixbuf_new_from_file(imageFile)
		self.size = (self.pixbuf.get_width(), self.pixbuf.get_height())
		
		# Create window.
		self.splashWindow = gtk.Window()
		self.splashWindow.set_decorated(False)
		self.splashWindow.resize(self.size[0], self.size[1])
		self.splashWindow.show()
		self.splashWindow.set_position(gtk.WIN_POS_CENTER_ALWAYS)
		
		# Create a horizontal and a vertical box.
		self.splashBoxH = gtk.HBox()
		self.splashWindow.add(self.splashBoxH)
		self.splashBoxH.show()
		
		self.splashBox = gtk.VBox()
		self.splashBoxH.pack_start(self.splashBox, fill=True, expand=True, padding=5)
		self.splashBox.show()
		
		# Create image container and set pixbuf.
		self.splashImage = gtk.Image()
		self.splashImage.set_from_pixbuf(self.pixbuf)
		self.splashBox.pack_start(self.splashImage, expand=True, fill=True, padding=5)
		self.splashImage.show()
		
		# Create info string label.
		if infoString != None:
			self.info = gtk.Label(infoString)
			self.splashBox.pack_start(self.info, expand=True, fill=True, padding=5)
			self.info.show()
			self.info.set_justify(gtk.JUSTIFY_LEFT)
		
		# Register a gtk timeout function that terminates the splash screen.	
		splashWindowTimer = gobject.timeout_add(duration*1000, self.destroy)
		
		# Start gtk main loop.
		gtk.main()
			
	
	# Timeout callback to terminate the splash screen.
	def destroy(self):
		gtk.mainquit()
		self.splashWindow.destroy()






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


# Pix buf for calibration image display.
class imageFromFile(gtk.VBox):
	def __init__(self, programSettings, width = 100):
		# Init super class.
		gtk.VBox.__init__(self)
		
		# Internalise data.
		self.programSettings = programSettings
		self.width = width
		
		# Get projector width and set height according to projector aspect ratio.
		aspect = float(self.programSettings['projectorSizeY'].value) / float(self.programSettings['projectorSizeX'].value)
		self.height = int(width * aspect)
		
		# Create image view.
		self.imageView = gtk.Image()
		self.imgSpacingBox = gtk.HBox();
		self.imgSpacingBox.pack_start(self.imageView, expand=True, fill=True, padding=5)
		self.imgSpacingBox.show()
		self.pack_start(self.imgSpacingBox, expand=True, fill=True, padding=5)
		self.imageView.show()
		
		# Load and delete button.
		self.buttonBox = gtk.HBox()
		self.pack_start(self.buttonBox, expand=True, fill=True, padding=5)
		self.buttonBox.show()
		self.buttonLoad = gtk.Button(label='Load')
		self.buttonBox.pack_start(self.buttonLoad, expand=True, fill=True, padding=5)
		self.buttonLoad.connect("clicked", self.callbackLoad)
		self.buttonLoad.show()
		self.buttonRemove = gtk.Button(label='Remove')
		self.buttonBox.pack_start(self.buttonRemove, expand=True, fill=True, padding=5)
		self.buttonRemove.connect("clicked", self.callbackRemove)
		self.buttonRemove.set_sensitive(self.programSettings['calibrationImage'].value)
		self.buttonRemove.show()
		
		# Load the image.
		self.updateImage()
		
		
	def updateImage(self):
		# Load calibration image into pixbuf if present.
		if (self.programSettings['calibrationImage'].value == True):
			# Load image from file.
			if (os.path.isfile('./calibrationImage.jpg')):
				# Write image to pixbuf.
				self.pixbuf = gtk.gdk.pixbuf_new_from_file('./calibrationImage.jpg')
				# Resize the image.
				self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)
			elif (os.path.isfile('./calibrationImage.png')):
				# Write image to pixbuf.
				self.pixbuf = gtk.gdk.pixbuf_new_from_file('./calibrationImage.png')
				# Resize the image.
				self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)
			else:
				self.programSettings['calibrationImage'].value = False
				
		# If no image present, create white dummy image.
		if (self.programSettings['calibrationImage'].value == False):
			# Create white dummy image.
			self.imageWhite = numpy.ones((self.height, self.width, 3), numpy.uint8) * 255
			# Create pixbuf from dummy image.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageWhite, gtk.gdk.COLORSPACE_RGB, 8)		
		
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)
		
	def callbackLoad(self, data=None):
		# Open file chooser dialog."
		filepath = ""
		# File open dialog to retrive file name and file path.
		dialog = gtk.FileChooserDialog("Load calibration image", None, gtk.FILE_CHOOSER_ACTION_OPEN, (gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
		dialog.set_modal(True)
		dialog.set_default_response(gtk.RESPONSE_OK)
		dialog.set_current_folder(self.programSettings['currentFolder'].value)
		# File filter for the dialog.
		fileFilter = gtk.FileFilter()
		fileFilter.set_name("Image file")
		fileFilter.add_pattern("*.jpg")
		fileFilter.add_pattern("*.png")
		#fileFilter.add_pattern("*.png")
		dialog.add_filter(fileFilter)
		# Run the dialog and return the file path.
		response = dialog.run()
		# Check the response.
		# If OK was pressed...
		if response == gtk.RESPONSE_OK:
			filepath = dialog.get_filename()
			filename = filepath.split('/')[-1]
			fileExtension = filepath.lower()[-4:]	
			# Check if file is an image. If not...
			if (fileExtension == ".jpg" or fileExtension == ".png"):
				# Copy image file to program path.
				try:
					shutil.copy(filepath, './calibrationImage' + fileExtension)
				except shutil.Error:
					print "File copy error, maybe you have chosen the calibration image?"
				# Set button sensitivities.
				self.buttonRemove.set_sensitive(True)
				self.programSettings['calibrationImage'].value = True
				# Update the image.
				self.updateImage()
				
			# Close dialog.
			dialog.destroy()
		# If cancel was pressed...
		elif response == gtk.RESPONSE_CANCEL:
			#... do nothing.
			dialog.destroy()
	
	def callbackRemove(self, data=None):
		# Delete the current file.
	#	try:
	#		os.remove('./calibrationImage.jpg')
	#	except (OSError, IOError):
	#		pass
	#	try:
	#		os.remove('./calibrationImage.png')
	#	except (OSError, IOError):
	#		pass
		self.programSettings['calibrationImage'].value = False	
		# Set button sensitivities.
		self.buttonRemove.set_sensitive(False)
		# Update the image.
		self.updateImage()
			
	def deleteImageFile(self):
		# Delete the current file.
		try:
			os.remove('./calibrationImage.jpg')
		except (OSError, IOError):
			pass
		try:
			os.remove('./calibrationImage.png')
		except (OSError, IOError):
			pass
		




# Slider that takes image which has to be update externally.
class imageSlider(gtk.VBox):
	def __init__(self, modelCollection, programSettings, width=250, console=None, customFunctions=None):
		# Call super class init function.
		gtk.VBox.__init__(self)
		
		# Internalise parameters.
		self.modelCollection = modelCollection
		self.console = console
		self.customFunctions = customFunctions
		
		# Reference to image.
#		self.image = self.modelCollection.sliceImage
		
		# Get parent width and set height according to projector aspect ratio.
		aspect = float(programSettings['projectorSizeY'].value) / float(programSettings['projectorSizeX'].value)
		self.width = width#250
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
		self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)
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




# A toggle button class with a label on the left. ##############################
# Will call custom functions passed as input. Label and default value are 
# taken from settings object.
# There are two possibilities: if a model collection is supplied, this is a 
# toggle button for a model specific setting. If no model collection has been
# supplied, this is a general setting.

class toggleButton(gtk.CheckButton):
	# Override init function.
	def __init__(self, string, settings=None, modelCollection=None, customFunctions=None, displayString=None):
	
		# Internalise model collection.
		self.modelCollection = modelCollection
		self.string = string
		
		# Get settings object if model collection was supplied.
		if self.modelCollection != None:
			self.settings = self.modelCollection.getCurrentModel().settings
		# If no model collection was supplied, this is a general setting.
		elif settings != None:
			self.settings = settings
		
		# Internalise custom functions.
		self.customFunctions = customFunctions
		
		# Create the label string.
		if displayString != None:
			self.labelString = displayString+self.settings[string].unit
		elif self.settings[self.string].name != None:
			self.labelString = self.settings[self.string].name + self.settings[string].unit
		else:
			self.labelString = string+self.settings[string].unit
		
		# Create toggle button.
		# Call super class init funtion.
		gtk.CheckButton.__init__(self, self.labelString)
		self.show()
		# Set toggle state according to setting.
		self.set_active(self.settings[string].value)
		# Connect to callback function.
		self.connect("toggled", self.callbackToggleChanged)
	

	def callbackToggleChanged(self, data=None):
		# Set value.
		# In case a model collection was provided...
		if self.modelCollection != None:
			# ... set the new value in the current model's settings.
			self.modelCollection.getCurrentModel().settings[self.string].setValue(self.get_active())
			# Set model changed flag in model collection. Needed to decide if slicer should be started again.
			self.modelCollection.getCurrentModel().setChanged()
		# If this is not a model setting but a printer setting...
		elif self.settings != None:
			# ... write the value to the settings.
			self.settings[self.string].setValue(self.get_active())
		# Call the custom functions specified for the setting.
		if self.customFunctions != None:
			for function in self.customFunctions:
				function()		
		
	# Update the toggle state if current model has changed.	
	def update(self):
		# If this is a model setting...
		if self.modelCollection != None:
			self.set_active(self.modelCollection.getCurrentModel().settings[self.string].value)
		else:
			self.set_active(self.settings[self.string].value)		



# A text entry including a label on the left. ##################################
# Will call a function passed to it on input. Label, default value and
# callback function are taken from the settings object.

class entry(gtk.HBox):
	# Override init function.
#	def __init__(self, string, settings, function=None):
	def __init__(self, string, settings=None, modelCollection=None, customFunctions=None, width=None, displayString=None):
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
		
		
		# Create the label string.
		if displayString != None:
			self.labelString = displayString+self.settings[string].unit
		elif self.settings[self.string].name != None:
			self.labelString = self.settings[self.string].name + self.settings[string].unit
		else:
			self.labelString = string+self.settings[string].unit

		
		# Make label.
		self.label = gtk.Label(self.labelString)
	#	if displayString != None:
	#		self.label = gtk.Label(displayString+self.settings[string].unit)
	#	else:
	#		self.label = gtk.Label(string+self.settings[string].unit)
		self.label.set_alignment(xalign=0, yalign=0.5)
		self.pack_start(self.label, expand=True, fill=True, padding=5)
		self.label.show()
		
		
		# Make text entry.
		self.entry = gtk.Entry()
		self.pack_start(self.entry, expand=False, fill=False, padding=5)
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
		if (event.type.value_name == "GDK_FOCUS_CHANGE" and self.entry.has_focus()==False and self.tabKeyPressed) or (event.type.value_name == "GDK_KEY_PRESS" and (event.keyval == gtk.keysyms.Return or event.keyval == gtk.keysyms.KP_Enter)):
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
				# Set model changed flag in model collection. Needed to decide if slicer should be started again.
				self.modelCollection.getCurrentModel().setChanged()
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
			
		
class printProgressBar(gtk.ProgressBar):
	def __init__(self, sliceQueue=None):
		gtk.ProgressBar.__init__(self)
		self.limit = 1.
		self.sliceQueue = sliceQueue
		self.queueStatus = Queue.Queue()
		
	def setLimit(self, limit):
		self.limit = float(limit)
	#	print "Limit: ", limit
	
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

#	def listener(self):
#		if self.sliceQueue.qsize():
#			self.updateValue(self.sliceQueue.get())
#		if self.queueStatus.qsize():
#			self.setText(self.queueStatus.get())






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
		
		# If G-Code board is used append GCode to settings strings.
		if self.settings['monkeyprintBoard'].value:
			self.postfix = ""
		else:
			self.postfix = "GCode"
	
	# Override run function.
	def run(self):
		# Create avrdude commandline string.
		avrdudeCommandList = [	'avrdude',
							'-p', self.settings['avrdudeMcu'+self.postfix].value,
							'-P', self.settings['avrdudePort'+self.postfix].value,
							'-c', self.settings['avrdudeProgrammer'+self.postfix].value,
							'-b', str(self.settings['avrdudeBaudrate'+self.postfix].value),
							'-U', 'flash:w:' + self.settings['avrdudeFirmwarePath'+self.postfix].value
							]
		# Append additional options.
		optionList = self.settings['avrdudeOptions'+self.postfix].value.split(' ')
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



class imageView(gtk.Image):
	def __init__(self, settings, modelCollection, width=None):
		gtk.Image.__init__(self)
		
		# Internalise parameters.
		self.settings = settings
		self.modelCollection = modelCollection
		
		self.resizeFlag = False
		# If no width is given...
		if width == None:
			# ... take the projector size from the settings.
			self.width = self.settings['projectorSizeX'].value
			self.height = self.settings['projectorSizeY'].value
		# If a width is given...
		else:
			# ... set corresponding height using projector aspect ratio.
			self.width = width
			# Get parent width and set height according to projector aspect ratio.
			aspect = float(self.settings['projectorSizeY'].value) / float(self.settings['projectorSizeX'].value)
			self.height = int(self.width * aspect)
			self.resizeFlag = True

		# Create black dummy image.
		self.imageBlack = numpy.zeros((self.height, self.width, 3), numpy.uint8)
		# Create pixbuf from numpy.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageBlack, gtk.gdk.COLORSPACE_RGB, 8)
		# Set image to viewer.
		self.set_from_pixbuf(self.pixbuf)
	
	# Check if a new slice number is in the queue.
	def updateImage(self, sliceNumber):
		if sliceNumber != -1:
			image = self.modelCollection.updateSliceImage(sliceNumber)
			# Get the image from the slice buffer and convert it to 3 channels.
			image = imageHandling.convertSingle2RGB(image)
			# Write image to pixbuf.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(image, gtk.gdk.COLORSPACE_RGB, 8)
			# Resize the image if in debug mode.
			#if self.settings['debug'].value:
			if self.resizeFlag:
				self.pixbuf = self.pixbuf.scale_simple(self.width, self.height, gtk.gdk.INTERP_BILINEAR)
		else:
			# Create pixbuf from numpy.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageBlack, gtk.gdk.COLORSPACE_RGB, 8)
		# Set pixbuf.
		self.set_from_pixbuf(self.pixbuf)


class projectorDisplay(gtk.Window):
	def __init__(self, settings, modelCollection):
		gtk.Window.__init__(self)
		
		# TODO: Check out screen setting methods
		# self.set_screen(parent.get_screen())
		
		# Internalise parameters.
		self.settings = settings
		self.modelCollection = modelCollection
		
		debugWidth = 200
		
		self.debug = self.settings['debug'].value
		self.printOnPi = self.settings['printOnRaspberry'].value
		
		# Customise window.
		# No decorations.
		self.set_decorated(False)#gtk.FALSE)
		# Call resize before showing the window.
		if self.debug and not self.printOnPi:
			aspect = float(self.settings['projectorSizeY'].value) / float(self.settings['projectorSizeX'].value)
			self.resize(debugWidth, int(debugWidth*aspect))
		else:
			self.resize(self.settings['projectorSizeX'].value, self.settings['projectorSizeY'].value)
		# Show the window.
		self.show()
		# Set position after showing the window.
		if self.debug and not self.printOnPi:
			self.move(200,100)
		elif self.printOnPi:
			self.move(0,0)
		else:
			self.move(self.settings['projectorPositionX'].value, self.settings['projectorPositionY'].value)

		# Create image view.
		if self.debug:
			self.imageView = imageView(self.settings, self.modelCollection, width = debugWidth)
		else:
			self.imageView = imageView(self.settings, self.modelCollection)
			
		# Create black dummy image.
		self.imageBlack = numpy.zeros((self.get_size()[1], self.get_size()[0], 3), numpy.uint8)
		# Create pixbuf from numpy.
		self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageBlack, gtk.gdk.COLORSPACE_RGB, 8)
		# Set image to viewer.
		self.imageView.set_from_pixbuf(self.pixbuf)
		self.add(self.imageView)
		self.imageView.show()
		
	
	# Check if a new slice number is in the queue.
	def updateImage(self, sliceNumber):
#		print "3: Started image update at " + str(time.time()) + "."
		if sliceNumber != -1:
			image = self.modelCollection.updateSliceImage(sliceNumber)
			# Get the image from the slice buffer and convert it to 3 channels.
			image = imageHandling.convertSingle2RGB(image)
			# Write image to pixbuf.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(image, gtk.gdk.COLORSPACE_RGB, 8)
			# Resize the image if in debug mode.
			if self.debug:
				self.pixbuf = self.pixbuf.scale_simple(self.get_size()[0], self.get_size()[1], gtk.gdk.INTERP_BILINEAR)
		else:
			# Create pixbuf from numpy.
			self.pixbuf = gtk.gdk.pixbuf_new_from_array(self.imageBlack, gtk.gdk.COLORSPACE_RGB, 8)
		# Set pixbuf.
		self.imageView.set_from_pixbuf(self.pixbuf)
#		print "4: Finished image update at " + str(time.time()) + "."
'''
