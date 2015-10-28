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
	def __init__(self, value, lower=None, upper=None, unit='', default=None):
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
		# Type cast to float.
		if type(inVal) == str:
			self.value = float(inVal)
		# Correct for upper bound.
		if self.upper != None:
			if self.value > self.upper:
				self.value = self.upper
		# Correct for lower bound.
		if self.lower != None:
			if self.value < self.lower:
				self.value = self.lower



class modelSettings(dict):
	# Override init function.
	def __init__(self):
		# Call super class init function.
		dict.__init__(self)
		# Create objects for all the settings and put them into dictionary.
		self['filename'] = setting(value="")
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
		


class programSettings(dict):	
	# Override init function.
	def __init__(self):
		# Call super class init function.
		dict.__init__(self)
		# Create objects for all the settings and put them into dictionary.
		self['currentFolder'] = setting(value='./models')
		self['versionMajor'] = setting(value=0)
		self['versionMinor'] = setting(value=9)	
		self['revision'] = setting(value=0)
		self['Projector size X'] = setting(value=1024, default=1024)
		self['Projector size Y'] = setting(value=768, default=768)
		self['Projector position X'] = setting(value=1920, default=1920)
		self['Projector position Y'] = setting(value=0, default=0)
		self['Build size X'] = setting(value=102, default=102)
		self['Build size Y'] = setting(value=79, default=79)
		self['Build size Z'] = setting(value=150, default=150)
		self['projectorSizeXY'] = setting(value=[1024,768])
		self['projectorPositionXY'] = setting(value=[1280,0])
		self['buildSizeXYZ'] = setting(value=[102,79,150])
		self['pxPerMm'] =  setting(value=self['projectorSizeXY'].value[0] / self['buildSizeXYZ'].value[0])
		self['avrdudeMCU'] = setting(value='atmega32u4')
		self['avrdudeProgrammer'] = setting(value='avr109')
		self['avrdudePort'] = setting(value='/dev/ttyACM0')
		self['avrdudeBaud'] = setting(value='57600')
		self['avrdudeOptions'] = setting(value='-D -V')
		self['avrdudePath'] = setting(value='./firmware/main.hex')
		self['avrdudeSettings'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['avrdudeSettingsDefault'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['Port'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM')
		self['Baud rate'] = setting(value='9600', default='9600')
		self['Tilt steps / °'] = setting(value='100', default='100')
		self['Tilt angle'] = setting(value='14', default='14')
		self['Tilt speed'] = setting(value='10', default='10')
		self['Build steps / mm'] = setting(value='100', default='100')
		self['Ramp slope'] = setting(value='15', default='15')
		self['Build platform speed'] = setting(value='10', default='10')
		
	# Load default settings.
	def loadDefaults(self):
		# Loop through all settings.
		for setting in self:
			# If default value is available...
			if self[setting].default:
				#... restore it.
				self[setting].value = self[setting].default
		
