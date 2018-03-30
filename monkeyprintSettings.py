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

import os
import sys
import threading

class setting:
	def __init__(self, value, valType, lower=None, upper=None, unit='', default=None, name=None, isConstant=False, noRead=False, output=None):
		self.value = value
		self.valType = valType
		self.upper = upper
		self.lower = lower
		if unit != '':
			self.unit = ' [' + unit + ']'
		else:
			self.unit = unit
		self.default = default
		self.name = name
		self.isConstant = isConstant	# If true, setting cannot be changed. Use for example for version string.
		self.noRead	= noRead			# If true, setting won't be read from file. Use for settings that need a specific init value.
		self.output = output
		# Create mutex to prevent race conditions if multiple threads access the settings object.
		self.mutex = threading.Lock()


	# Set value and control bounds. ************************
	def setValue(self, inVal):
		# Wait for mutex to be released.
		self.mutex.acquire()
		if not self.isConstant:
			# Set value.
			# If it's a number, correct for bounds.
			if self.valType == float or self.valType == int:
				val = self.valType(inVal)
				if self.lower != None:
					val = max(self.lower, val)
				if self.upper != None:
					val = min(self.upper, val)
				self.value = self.valType(val)
			# Cast to bool if "True" or "False"
			elif inVal == "True" or inVal == "False":
				self.value = eval(inVal)
			else:
				self.value = inVal
		else:
			if self.output != None:
				self.output.addLine("Value of setting {n:s} is constant and cannot be changed.".format(n=name))
		# Release mutex.
		self.mutex.release()

	def getValue(self):
		self.mutex.acquire()
		val = self.value
		self.mutex.release()
		return val

	def getType(self):
		# No mutex needed as valType will never change.
		return self.valType

	def getLimits(self):
		# No mutex needed as valType will never change.
		return [self.lower, self.upper]


	# Check if string represents a number. *****************
	def isnumber(self,s):
		try:
			float(s)
		except ValueError:
			return False
		else:
			return True

	'''
	# Set value and control bounds.
	def setValue(self, inVal):
		if not self.isConstant:
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
	'''


class modelSettings(dict):
	# Override init function.
	def __init__(self, output=None):
		# Internalize.
		self.output = output
		# Call super class init function.
		dict.__init__(self)
		# Create objects for all the settings and put them into dictionary.
		self['filename'] = 					setting(value="", 	valType=str, output=self.output)
		self['active'] = 					setting(value=True, valType=str, output=self.output)
		self['scaling'] = 					setting(value=1, 	valType=float,	name='Scaling', lower=0.0000000000001, output=self.output)
		self['rotationX'] = 				setting(value=0,	valType=float,	lower=0,	upper=359,	unit='°',		name='Rotation X', output=self.output)
		self['rotationY'] =					setting(value=0,	valType=float,	lower=0,	upper=359,	unit='°',		name='Rotation Y', output=self.output)
		self['rotationZ'] = 				setting(value=0,	valType=float,	lower=0,	upper=359,	unit='°',		name='Rotation Z', output=self.output)
		self['positionX'] = 				setting(value=50,	valType=float,	lower=0,	upper=100,	unit='%',		name='Position X', output=self.output)
		self['positionY'] = 				setting(value=50,	valType=float,	lower=0,	upper=100,	unit='%',		name='Position Y', output=self.output)
		self['createBottomPlate'] = 		setting(value=True, valType=str,	default=True, name='Create bottom plate', output=self.output)
		self['createSupports'] = 			setting(value=True, valType=str,	default=True, name='Create supports', output=self.output)
		self['bottomPlateThickness'] =	 	setting(value=0.5,	valType=float,	lower=0.1,	upper=1.0,	unit='mm',		name='Bottom plate thickness', output=self.output)
		self['bottomClearance'] = 			setting(value=5,	valType=float,	lower=self['bottomPlateThickness'].lower, unit='mm',		name='Bottom clearance', output=self.output)
		# bottomClearanceMax must be set by model position, rotation and size
		self['overhangAngle'] = 			setting(value=45,	valType=float,	lower=5,	upper=80,	unit='°',		name='Overhang angle', output=self.output)
		self['spacingX'] =					setting(value=5,	valType=float,	lower=0,	upper=10,	unit='mm',		name='Spacing X', output=self.output)
		self['spacingY'] = 					setting(value=5,	valType=float,	lower=0,	upper=10,	unit='mm',		name='Spacing Y', output=self.output)
		self['maximumHeight'] =				setting(value=20,	valType=float,	lower=1,	upper=1000,	unit='mm',		name='Maximum height', output=self.output)
		self['baseDiameter'] =				setting(value=1.5,	valType=float,	lower=0.3,	upper=5.0,	unit='mm',		name='Base diameter', output=self.output)
		self['tipDiameter'] =				setting(value=0.5,	valType=float,	lower=0.1,	upper=0.5,	unit='mm',		name='Tip diameter', output=self.output)
		self['coneHeight'] =				setting(value=2.5,	valType=float,	lower=1.0,	upper=10.0,	unit='mm',		name='Cone height', output=self.output)
	#	self['bottomPlateThickness'] = setting(value=0.5,	lower=0.1,	upper=1.0,	unit='mm',		name='Bottom plate thickness')
		self['printHollow'] =				setting(value=True,	valType=str,	name='Print hollow', output=self.output)
		self['fill'] =						setting(value=True,	valType=str,	name='Use fill', output=self.output)
		self['fillShellWallThickness'] =	setting(value=2.0,	valType=float,	lower=0.5, upper=10.0, unit='mm',		name='Shell thickness', output=self.output)
		self['fillSpacing'] =				setting(value=3.0,	valType=float,	lower=1.0, upper=10.0, unit='mm',		name='Fill spacing', output=self.output)
		self['fillPatternWallThickness'] =	setting(value=0.3,	valType=float,	lower=0.1, upper=0.4,		name='Fill thickness', output=self.output)

# Job settings are used to transfer job specific settings to the printer.
# This way, different jobs can have different settings on the printer.
class jobSettings(dict):
	# Override init function.
	def __init__(self, programSettings, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		# Load defaults from program settings to get settings saved from last session.
		self['layerHeight'] = setting(value=0.1, valType=float,	lower=.01, upper=0.3, unit='mm', output=self.output)
		self['projectPath'] = programSettings['currentFolder']#setting(value="")
		self['exposureTimeBase'] = programSettings['exposureTimeBase']#setting(value=14.0, lower=1.0, upper=15.0)
		self['numberOfBaseLayers'] = programSettings['numberOfBaseLayers']
		self['exposureTime'] = programSettings['exposureTime']#setting(value=9.0, lower=1.0, upper=15.0)

	'''
	def setProgramSettings(self, programSettings):
		for setting in self:
			programSettings[setting] = self[setting]

	def getProgramSettings(self, programSettings):
		for setting in self:
			self[setting] = programSettings[setting]
	'''

class programSettings(dict):
	# Override init function.
	def __init__(self, console=None, output=None):
		# Internalize.
		self.output = output
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		self['currentFolder'] =				setting(value='./models',			valType=str, 	output=self.output)
		self['tmpDir'] = 					setting(value=self.getInstallDir()+'/tmp', 	valType=str,	isConstant=True, output=self.output)
		self['installDir'] = 				setting(value=self.getInstallDir(),			valType=str,	isConstant=True, output=self.output)
		self['versionMajor'] =				setting(value=0, 					valType=int, 	noRead=True,	isConstant=True,	output=self.output)
		self['versionMinor'] =				setting(value=14, 					valType=int, 	noRead=True,	isConstant=True,	output=self.output)
		self['revision'] =					setting(value=1, 					valType=int, 	noRead=True,	isConstant=True,	output=self.output)
		self['projectorSizeX'] =			setting(value=1024, 				valType=int,	default=1024,	name='Projector size X', output=self.output)
		self['projectorSizeY'] =			setting(value=768, 					valType=int,	default=768,	name='Projector size Y', output=self.output)
		self['projectorPositionX'] =		setting(value=1920, 				valType=int,	default=1920,	name='Projector position X', output=self.output)
		self['projectorPositionY'] =		setting(value=0, 					valType=int,	default=0,		name='Projector position Y', output=self.output)
		self['buildSizeX'] =				setting(value=102.4, 				valType=float,	default=102.4,	lower=0.0,	upper=100000.0,	unit='mm',		name='Build size X', output=self.output)
		self['buildSizeY'] =				setting(value=76.8, 				valType=float,	default=76.8,	lower=0.0,	upper=100000.0,	unit='mm',		name='Build size Y', output=self.output)
		self['buildSizeZ'] =				setting(value=150.0, 				valType=float,	default=150.0,	lower=0.0,	upper=100000.0,	unit='mm',		name='Build size Z', output=self.output)
		self['pxPerMmX'] =  				setting(value=self['projectorSizeX'].value / self['buildSizeX'].value,		valType=float, output=self.output)
		self['pxPerMmY'] =  				setting(value=self['projectorSizeY'].value / self['buildSizeY'].value,		valType=float, output=self.output)
		self['port'] = 						setting(value='/dev/ttyACM0',		valType=str, 	default='/dev/ttyACM0',		name='Port', output=self.output)
		self['baudrate'] = 					setting(value=115200, 				valType=int, 	default=115200,		name='Baud rate', output=self.output)

		self['avrdudeMcu'] = 				setting(value='atmega32u4', 		valType=str, default='atmega32u4',		name='MCU', output=self.output)
		self['avrdudeMcuGCode'] = 			setting(value='atmega2560', 		valType=str, default='atmega2560',		name='MCU', output=self.output)
		self['avrdudeProgrammer'] = 		setting(value='avr109', 			valType=str, default='avr109',		name='Programmer', output=self.output)
		self['avrdudeProgrammerGCode'] =	setting(value='stk500v2', 			valType=str, default='stk500v2',		name='Programmer', output=self.output)
		self['avrdudePort'] = 				setting(value='/dev/ttyACM0', 		valType=str, default='/dev/ttyACM0',		name='Port', output=self.output)
		self['avrdudePortGCode'] = 			setting(value='/dev/ttyACM0', 		valType=str, default='/dev/ttyACM0',		name='Port', output=self.output)
		self['avrdudeBaudrate'] = 			setting(value=57600, 				valType=int, default=57600,		name='Baud rate', output=self.output)
		self['avrdudeBaudrateGCode'] =		setting(value=115200, 				valType=int, default=115200,		name='Baud rate', output=self.output)
		self['avrdudeOptions'] =			setting(value='-D -V', 				valType=str, default='-D -V',		name='Options', output=self.output)
		self['avrdudeOptionsGCode'] =		setting(value='-D -V', 				valType=str, default='-D -V',		name='Options', output=self.output)
		self['avrdudeFirmwarePath'] =		setting(value='./firmware/main.hex', 		valType=str, default='./firmware/main.hex',		name='Firmware path', output=self.output)
		self['avrdudeFirmwarePathGCode'] =	setting(value='./firmware/marlin/marlinForMonkeyprint.hex', 		valType=str, default='./firmware/marlin/marlinForMonkeyprint.hex',		name='Firmware path', output=self.output)

	#	self['avrdudeSettings'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'], default=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
	#	self['avrdudeSettingsGCode'] = setting(value=['atmega2560', 'stk500v2', '/dev/ttyACM0', '115200', '-D -V -U', './firmware/marlin/marlinForMonkeyprint.hex'])
	#	self['avrdudeSettingsDefault'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['portRaspi'] = 				setting(value='/dev/ttyAMA0', 	valType=str, 	default='/dev/ttyAMA0',		name='Port', output=self.output)
		self['baudrateRaspi'] =				setting(value=9600, 			valType=int, 	default=9600,		name='Baud rate', output=self.output)
		self['ipAddressRaspi'] =			setting(value='192.168.2.111', 	valType=str, 	default='192.168.2.111',		name='IP address', output=self.output)
		self['networkPortRaspi'] =			setting(value=5553, 			valType=int, 	default=5553,		name='Control port', output=self.output)
		self['fileTransmissionPortRaspi'] =	setting(value=6000,				valType=int, 	default='6000',		name='File transmission port', output=self.output)
	#	self['SSH user name'] = setting(value='pi', default='pi')
	#	self['SSH password'] = setting(value='raspberry', default='raspberry')
		self['projectorPort'] =				setting(value='/dev/ttyUSB0', 	valType=str, 	default='/dev/ttyUSB0',		name='Port', output=self.output)
		self['projectorBaudrate'] =			setting(value=9600, 			valType=int,	default=9600,		name='Baud rate', output=self.output)
		self['projectorControl'] =			setting(value=False, 			valType=str, 	default=False,		name='Projector control', output=self.output)
		self['projectorOnCommand'] =		setting(value='* 0 IR 001', 	valType=str, 	default='* 0 IR 001',		name='Projector ON command', output=self.output)
		self['projectorOffCommand'] =		setting(value='* 0 IR 002', 	valType=str,	default='* 0 IR 002',		name='Projector OFF command', output=self.output)
		self['showFill'] =					setting(value=True, 			valType=str,	name='Show fill', output=self.output)
		self['layerHeight'] =				setting(value=0.1, 				valType=float, 	lower=.05, upper=0.3, unit='mm',		name='Layer height', output=self.output)
		self['modelSafetyDistance'] =		setting(value=1.0, 				valType=float, 	unit='mm', output=self.output)
		self['debug'] =						setting(value=False, 			valType=str,	name='Debug', output=self.output)
		self['exposureTimeBase'] =			setting(value=14.0, 			valType=float, 	default=14.0,	lower=0.1, 	upper=15.0,	name='Exposure time base', output=self.output)
		self['exposureTime'] =				setting(value=9.0, 				valType=float,	default=9.0,	lower=0.1,	upper=15.0, name='Exposure time', output=self.output)
		self['numberOfBaseLayers'] = 		setting(value=1, 				valType=int,	default=1, 		lower=0, 	upper=20, 	name='Number of base layers', output=self.output)
		self['calibrationImagePath'] =		setting(value="./calibrationImage", valType=str,default="./calibrationImage", output=self.output)
		self['calibrationImage'] =			setting(value=False, 			valType=str,	default=False, output=self.output)
		self['showVtkErrors'] =				setting(value=True, 			valType=str,	default=False, output=self.output)
		self['runningOnRaspberry'] =		setting(value=False, 			valType=str,	default=False, output=self.output)
		self['printOnRaspberry'] =			setting(value=False, 			valType=str,	default=False, output=self.output)
		self['localMkpPath'] =				setting(value='./currentPrint.mkp', valType=str,default='./currentPrint.mkp', output=self.output)
		self['monkeyprintBoard'] =			setting(value=False, 			valType=str,	default=False, output=self.output)

#		self['Tilt GCode']	 = setting(value='G1 X{$tiltDist*$tiltDir} F10 G1 X{-$tiltDist*$tiltDir} F10', default = 'G1 X{$tiltDist*$tiltDir} F10 G1 X{-$tiltDist*$tiltDir} F10')
#		self['Build platform GCode'] = setting(value='G1 Z{$layerHeight*$buildDir} F10', default='G1 Z{$layerHeight*$buildDir} F10')
#		self['Shutter open GCode'] = setting(value='M280 P0 S{$shutterPosOpen}', default='M280 P0 S{$shutterPosOpen}')
#		self['Shutter close GCode'] = setting(value='M280 P0 S{$shutterPosClosed}', default='M280 P0 S{$shutterPosClosed}')
#		self['Start commands GCode'] = setting(value='G21 G91 M17', default='G21 G91 M17')
#		self['End commands GCode'] = setting(value='M18', default='M18')
#		self['Home GCode'] = setting(value='G28', default='G28')
#		self['Top GCode'] = setting(value='G28 Z0', default='G28 Z0')
		# Modules for print process. Values are: Display name, Value, Unit, Type, Editable, Active.
		self['printModulesGCode'] =			setting(value='Wait,1.0,,internal,True,True;Initialise printer,G21 G91 M17,,serialGCode,True,True;Build platform layer up,G1 Z{$layerHeight} F100,,serialGCode,True,True;Build platform to home,G28 X Z,,serialGCode,True,True;Build platform to top,G162 Z F100,,serialGCode,True,True;Tilt down,G1 X20 F1000,,serialGCode,True,True;Tilt up,G1 X-20 F1000,,serialGCode,True,True;Shutter open,M280 P0 S500,,serialGCode,True,True;Shutter close,M280 P0 S2500,,serialGCode,True,True;Expose,,,internal,False,True;Projector on,,,internal,False,True;Projector off,,,internal,False,True;Start loop,,,internal,False,True;End loop,,,internal,False,True;Shut down printer,M18,,serialGCode,True,True;Set steps per unit,M92 X 20.8 Z 10.2,,serialGCode,True,True;Emergency stop,M112,,serialGCode,True,True;Beep,M300 S440 P500,,serialGCode,True,True;Custom G-Code,G91,,serialGCode,True,True', 		valType=str, output=self.output)
		self['printProcessGCode'] =			setting(value='Initialise printer,G21 G91 M17,,serialGCode,True,True;Projector on,---,,internal,False,True;Build platform to home,G28 X Z,,serialGCode,True,True;Start loop,---,,internal,False,True;Shutter open,M280 P0 S500,,serialGCode,True,True;Expose,---,,internal,False,True;Shutter close,M280 P0 S2500,,serialGCode,True,True;Tilt down,G1 X20 F1000,,serialGCode,True,True;Build platform layer up,G1 Z{$layerHeight} F100,,serialGCode,True,True;Tilt up,G1 X-20 F1000,,serialGCode,True,True;Wait,1.0,,internal,True,True;End loop,---,,internal,False,True;Build platform to top,G162 F100,,serialGCode,True,True;Shut down printer,M18,,serialGCode,True,True', 		valType=str, output=self.output)
		#self['calibrationImageFile'] = setting(value="calibrationImage.jpg", default="calibrationImage.jpg")
		self['polylineClosingThreshold'] = 	setting(value=0.1, 		valType=float,	default=0.1, lower=0.0, upper=1.0, output=self.output)
		self['sliceStackMemory'] = 			setting(value=50, 		valType=int,	default=500, lower=100, unit='MB', name='Slicer memory', output=self.output)
		self['previewSlicesMax'] = 			setting(value=300, 		valType=int,	default=300, lower=100, upper=1000, name='Max. preview slices', output=self.output)
		self['previewSliceWidth'] = 		setting(value=200, 		valType=int,	default=200, output=self.output)
		self['sliceBorderWidth'] = 			setting(value=10, 		valType=int, output=self.output)
		self['multiBodySlicing'] = 			setting(value=False, 	valType=bool,	default=False, name='Multi body slicing', output=self.output)

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
		string = setting + ":" + str(self[setting].getValue()) + "\n"
		return string

	# Convert a string reading "setting name:value" to a setting.
	def string2Setting(self, string):
		if string.strip() != '':
			string = string.strip()
			strSplit = string.split(':')
			try:
				# Only read if permitted.
				if not self[strSplit[0]].noRead:
					self[strSplit[0]].setValue(strSplit[1])
			except KeyError:
				if self.output != None:
					self.output.addLine("Setting " + strSplit[0] + " found in settings file but not in settings object. Skipping.")



	# Save program settings to file. ***********************
	def saveFile(self, path):
		# Set file path.
		if path[-1] != '/':
			path += '/'
#		print "Writing settings file."
		# Open file.
		with open(path + 'settings', 'w') as f:
			# Loop through settings.
			for setting in self:
				# Convert to string and write to file.
				f.write(self.setting2String(setting))


	# Read program settings from file. *********************
	def readFile(self, path, filename=None):
		# Format path.
		if filename==None:
			filename = 'settings'
		if path[-1] != '/':
			path += '/'
		filename = path + filename
		# Open file.
		try:
			# Open file.
			with open(filename, 'r') as f:
				# Loop through lines.
				for line in f:
					if line != "":
						self.string2Setting(line)
				if self.output != None:
					self.output.addLine("Settings loaded from file.")
		except IOError:
			if self.output != None:
				self.output.addLine("No settings file found. Using defaults.")



	def getModuleList(self):
		if self['monkeyprintBoard'].value == True:
			moduleList = self['printModulesMonkeyprint'].value.split(';')
			for i in range(len(moduleList)):
				moduleList[i] = moduleList[i].split(',')
				moduleList[i][-1] = eval(moduleList[i][-1])
			return moduleList
		else:
			moduleList = self['printModulesGCode'].value.split(';')
			for i in range(len(moduleList)):
				moduleList[i] = moduleList[i].split(',')
				# Turn True/False string into boolean.
				moduleList[i][-1] = eval(moduleList[i][-1])
				moduleList[i][-2] = eval(moduleList[i][-2])
			return moduleList

	def setModuleList(self, moduleList):
		settingString = ''
		for row in range(len(moduleList)):
			settingString += str(moduleList[row])
			if row < len(moduleList)-1:
				settingString += ';'
		if self['monkeyprintBoard'].value == True:
			self['printModulesMonkeyprint'].value = moduleList
		else:
			self['printModulesGCode'].value = settingString

	def getPrintProcessList(self):
		printProcessList = self['printProcessGCode'].value.split(';')
		for i in range(len(printProcessList)):
			# Split comma separated string for each command.
			printProcessList[i] = printProcessList[i].split(',')
			# Turn True/False string into boolean.
			printProcessList[i][-1] = eval(printProcessList[i][-1])
			printProcessList[i][-2] = eval(printProcessList[i][-2])
		return printProcessList


	def setPrintProcessList(self, moduleList):
		settingString = ''
		for row in range(len(moduleList)):
			for item in range(len(moduleList[row])):
				settingString += str(moduleList[row][item])
				if item < len(moduleList[row])-1:
					settingString += ','
			if row < len(moduleList)-1:
				settingString += ';'
		if self['monkeyprintBoard'].value == True:
			self['printProcessMonkeyprint'].value = settingString
		else:
			self['printProcessGCode'].value = settingString


	# Get install dir for running from packaged exe or script.
	# https://stackoverflow.com/questions/7674790/bundling-data-files-with-pyinstaller-onefile
	def getInstallDir(self):
		try:
			# PyInstaller creates a temp folder and stores path in _MEIPASS
			base_path = sys._MEIPASS
		except AttributeError:
			base_path = os.path.abspath(".")
		return base_path
