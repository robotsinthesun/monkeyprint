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


class setting:
	def __init__(self, value, lower=None, upper=None, unit='', default=None, valType=None):
		self.value = value
		self.upper = upper
		self.lower = lower
		if unit != '':
			self.unit = ' [' + unit + ']'
		else:
			self.unit = unit
		self.default = default

	# Set value and control bounds.
	def setValue(self, inVal):
		self.value = inVal
		# Type cast to float or int if number.
		if type(inVal) == str and self.isnumber(inVal):
#			print inVal.isdigit()
			if inVal.isdigit():
				self.value = int(inVal)
#				print "Int: " + inVal
			else:
				self.value = float(inVal)
#				print "Float: " + inVal
		# Cast to bool if "True" or "False"
		elif inVal == "True" or inVal == "False":
			self.value = eval(inVal)
#			print "String: " + inVal
		# Correct for upper bound.
		if self.upper != None:
			if self.value > self.upper:
				self.value = self.upper
		# Correct for lower bound.
		if self.lower != None:
			if self.value < self.lower:
				self.value = self.lower

	def isnumber(self,s):
		try:
			float(s)      
		except ValueError:
			return False
		else:
			return True


class modelSettings(dict):
	# Override init function.
	def __init__(self):
		# Call super class init function.
		dict.__init__(self)
		# Create objects for all the settings and put them into dictionary.
		self['filename'] = setting(value="")
		self['Active'] = setting(value=True)
		self['Scaling'] = setting(value=1)
		self['Rotation X'] = setting(value=0,	lower=0,	upper=359,	unit='°')
		self['Rotation Y'] = setting(value=0,	lower=0,	upper=359,	unit='°')
		self['Rotation Z'] = setting(value=0,	lower=0,	upper=359,	unit='°')
		self['Position X'] = setting(value=50,	lower=0,	upper=100,	unit='%')
		self['Position Y'] = setting(value=50,	lower=0,	upper=100,	unit='%')
		self['Bottom plate thickness'] = setting(value=0.5,	lower=0.1,	upper=1.0,	unit='mm')
		self['Bottom clearance'] = setting(value=5,	lower=self['Bottom plate thickness'].lower, unit='mm')
		# bottomClearanceMax must be set by model position, rotation and size
		self['Overhang angle'] = setting(value=45,	lower=5,	upper=80,	unit='°')
		self['Spacing X'] = setting(value=5,	lower=0,	upper=10,	unit='mm')
		self['Spacing Y'] = setting(value=5,	lower=0,	upper=10,	unit='mm')
		self['Maximum height'] = setting(value=20,	lower=1,	upper=1000,	unit='mm')
		self['Base diameter'] = setting(value=1.5,	lower=0.3,	upper=5.0,	unit='mm')
		self['Tip diameter'] = setting(value=0.5,	lower=0.1,	upper=0.5,	unit='mm')
		self['Cone height'] = setting(value=2.5,	lower=1.0,	upper=10.0,	unit='mm')
		self['Bottom plate thickness'] = setting(value=0.5,	lower=0.1,	upper=1.0,	unit='mm')
		self['Print hollow'] = setting(value=True)
		self['Fill'] = setting(value=True)
		self['Shell wall thickness'] = setting(value=2.0, lower=0.5, upper=10.0, unit='mm')
		self['Fill spacing'] = setting(value=3.0, lower=1.0, upper=10.0, unit='mm')
		self['Fill wall thickness'] = setting(value=0.3, lower=0.1, upper=0.4)

class jobSettings(dict):
	# Override init function.
	def __init__(self, programSettings, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		# Load defaults from program settings to get settings saved from last session.
		self['Layer height'] = setting(value=0.1, lower=.01, upper=0.3, unit='mm')
		self['projectPath'] = programSettings['currentFolder']#setting(value="")		
		self['Exposure time base'] = programSettings['Exposure time base']#setting(value=14.0, lower=1.0, upper=15.0)
		self['Exposure time'] = programSettings['Exposure time']#setting(value=9.0, lower=1.0, upper=15.0)
		self['Resin settle time'] = programSettings['Resin settle time']#setting(value=1.0, lower=0.1, upper=3.0)
		
		
class programSettings(dict):	
	# Override init function.
	def __init__(self, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		self['currentFolder'] = setting(value='./models')
		self['versionMajor'] = setting(value=0)
		self['versionMinor'] = setting(value=10)	
		self['revision'] = setting(value=3)
		self['Projector size X'] = setting(value=1024, default=1024)
		self['Projector size Y'] = setting(value=768, default=768)
		self['Projector position X'] = setting(value=1920, default=1920)
		self['Projector position Y'] = setting(value=0, default=0)
		self['Build size X'] = setting(value=102.4, default=102.4)
		self['Build size Y'] = setting(value=76.8, default=76.8)
		self['Build size Z'] = setting(value=150.0, default=150.0)
		self['projectorSizeXY'] = setting(value=[1024,768])
		self['projectorPositionXY'] = setting(value=[1280,0])
		self['buildSizeXYZ'] = setting(value=[102.4,76.8,150.0])
		self['pxPerMm'] =  setting(value=self['projectorSizeXY'].value[0] / self['buildSizeXYZ'].value[0])
		self['MCU'] = setting(value='atmega32u4', default='atmega32u4')
		self['Programmer'] = setting(value='avr109', default='avr109')
		self['Port'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM0')
		self['Baud rate'] = setting(value='57600', default=57600)
		self['Options'] = setting(value='-D -V', default='-D -V')
		self['Firmware path'] = setting(value='./firmware/main.hex', default='./firmware/main.hex')
		self['avrdudeSettings'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['avrdudeSettingsDefault'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['Port RasPi'] = setting(value='/dev/ttyS0', default='/dev/ttyS0')
		self['Baud rate RasPi'] = setting(value='57600', default='57600')
		self['IP RasPi'] = setting(value='192.168.2.111', default='192.168.2.111')
		self['SSH user name'] = setting(value='pi', default='pi')
		self['SSH password'] = setting(value='raspberry', default='raspberry')
		self['Projector port'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM0')
		self['Projector baud rate'] = setting(value='9600', default='9600')
		self['Projector control'] = setting(value=False, default=False)
		self['Tilt step angle'] = setting(value=1.8, default=1.8, upper=3.6, lower=0.9, unit="°")
		self['Tilt microsteps per step'] = setting(value=4, default=4, lower=1, upper=32)
		self['Tilt angle'] = setting(value='14', default='14')
		self['Tilt speed'] = setting(value='10', default='10')
		self['Tilt speed slow'] = setting(value='4', default='4')
		self['Enable tilt'] = setting(value=True, default=True)
		self['Build step angle'] = setting(value=1.8, default=1.8, unit="°")
		self['Build microsteps per step'] = setting(value=16, default=16, lower=1, upper=32)
		self['Build mm per turn'] = setting(value=1.0, default=1.0, unit="mm")
		self['Build minimum move'] = setting(value=0.01, default=0.01, unit="mm")
		self['Build ramp slope'] = setting(value=15, default=15)
		self['Build platform speed'] = setting(value='10', default='10', unit='mm/s')
		self['Show fill'] = setting(value=True)
		self['Layer height'] = setting(value=0.1, lower=.05, upper=0.3, unit='mm')
		self['Model safety distance'] = setting(value=1.0, unit='mm')
		self['Debug'] = setting(value=False)
		self['Exposure time base'] = setting(value=14.0, lower=1.0, upper=15.0)
		self['Exposure time'] = setting(value=9.0, lower=1.0, upper=15.0)
		self['Resin settle time'] = setting(value=1.0, lower=0.0, upper=5.0)
		self['camTriggerWithExposure'] = setting(value=False, default=False)
		self['camTriggerAfterExposure'] = setting(value=False, default=False)
		self['calibrationImagePath'] = setting(value="./calibrationImage", default="./calibrationImage")
		self['calibrationImage'] = setting(value=False, default=False)
		self['showVtkErrors'] = setting(value=False, default=False)
		self['runOnRaspberry'] = setting(value=False, default=False)
		self['Shutter position open'] = setting(value=4, default=4, lower=0, upper=10)
		self['Shutter position closed'] = setting(value=6, default=6, lower=0, upper=10)
		self['Enable shutter servo'] = setting(value=False, default=False)
		#self['calibrationImageFile'] = setting(value="calibrationImage.jpg", default="calibrationImage.jpg")

	# Load default settings.
	def loadDefaults(self):
		# Loop through all settings.
		for setting in self:
			# If default value is available...
			if self[setting].default:
				#... restore it.
				self[setting].value = self[setting].default

	# Convert one setting to a string reading "setting name:value".
	def setting2String(self,setting):
		string = setting + ":" + str(self[setting].value) + "\n"
		return string
	
	def string2Setting(self, string):
		string = string.strip()
		strSplit = string.split(':')
		self[strSplit[0]].setValue(strSplit[1])	# Use eval to turn string into object.

	# Save program settings to file.
	def saveFile(self):
		# Open file.
		with open('programSettings.txt', 'w') as f:
			# Loop through settings.
			for setting in self:
				# Convert to string and write to file.
				f.write(self.setting2String(setting))
	
	# Read program settings from file.
	def readFile(self):
		try:
			# Open file.
			with open('programSettings.txt', 'r') as f:
				# Loop through lines.
				for line in f:
					if line != "":
						self.string2Setting(line)
				if self.console != None:
					self.console.addLine("Settings loaded from file.")
		except IOError:
			if self.console != None:
				self.console.addLine("No settings file found. Using defaults.")
