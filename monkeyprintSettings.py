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

class setting:
	def __init__(self, value, lower=None, upper=None, unit='', default=None, valType=None, name=None, isConstant=False):
		self.value = value
		self.upper = upper
		self.lower = lower
		if unit != '':
			self.unit = ' [' + unit + ']'
		else:
			self.unit = unit
		self.default = default
		self.name = name
		self.isConstant = isConstant


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


class modelSettings(dict):
	# Override init function.
	def __init__(self):
		# Call super class init function.
		dict.__init__(self)
		# Create objects for all the settings and put them into dictionary.
		self['filename'] = setting(value="")
	#	self['id'] = setting(value="")
		self['active'] = setting(value=True)
		self['scaling'] = setting(value=1, name='Scaling', lower=0.0000000000001)
		self['rotationX'] = setting(value=0,	lower=0,	upper=359,	unit='°',		name='Rotation X')
		self['rotationY'] = setting(value=0,	lower=0,	upper=359,	unit='°',		name='Rotation Y')
		self['rotationZ'] = setting(value=0,	lower=0,	upper=359,	unit='°',		name='Rotation Z')
		self['positionX'] = setting(value=50,	lower=0,	upper=100,	unit='%',		name='Position X')
		self['positionY'] = setting(value=50,	lower=0,	upper=100,	unit='%',		name='Position Y')
		self['createBottomPlate'] = setting(value=True, default=True, name='Create bottom plate')
		self['createSupports'] = setting(value=True, default=True, name='Create supports')
		self['bottomPlateThickness'] = setting(value=0.5,	lower=0.1,	upper=1.0,	unit='mm',		name='Bottom plate thickness')
		self['bottomClearance'] = setting(value=5,	lower=self['bottomPlateThickness'].lower, unit='mm',		name='Bottom clearance')
		# bottomClearanceMax must be set by model position, rotation and size
		self['overhangAngle'] = setting(value=45,	lower=5,	upper=80,	unit='°',		name='Overhang angle')
		self['spacingX'] = setting(value=5,	lower=0,	upper=10,	unit='mm',		name='Spacing X')
		self['spacingY'] = setting(value=5,	lower=0,	upper=10,	unit='mm',		name='Spacing Y')
		self['maximumHeight'] = setting(value=20,	lower=1,	upper=1000,	unit='mm',		name='Maximum height')
		self['baseDiameter'] = setting(value=1.5,	lower=0.3,	upper=5.0,	unit='mm',		name='Base diameter')
		self['tipDiameter'] = setting(value=0.5,	lower=0.1,	upper=0.5,	unit='mm',		name='Tip diameter')
		self['coneHeight'] = setting(value=2.5,	lower=1.0,	upper=10.0,	unit='mm',		name='Cone height')
	#	self['bottomPlateThickness'] = setting(value=0.5,	lower=0.1,	upper=1.0,	unit='mm',		name='Bottom plate thickness')
		self['printHollow'] = setting(value=True,		name='Print hollow')
		self['fill'] = setting(value=True,		name='Use fill')
		self['fillShellWallThickness'] = setting(value=2.0, lower=0.5, upper=10.0, unit='mm',		name='Shell thickness')
		self['fillSpacing'] = setting(value=3.0, lower=1.0, upper=10.0, unit='mm',		name='Fill spacing')
		self['fillPatternWallThickness'] = setting(value=0.3, lower=0.1, upper=0.4,		name='Fill thickness')

class jobSettings(dict):
	# Override init function.
	def __init__(self, programSettings, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		# Load defaults from program settings to get settings saved from last session.
		self['layerHeight'] = programSettings['layerHeight']#setting(value=0.1, lower=.01, upper=0.3, unit='mm', name='Layer height')
		self['currentFolder'] = programSettings['currentFolder']#setting(value="")
		self['exposureTimeBase'] = programSettings['exposureTimeBase']#setting(value=14.0, lower=1.0, upper=15.0)
		self['exposureTime'] = programSettings['exposureTime']#setting(value=9.0, lower=1.0, upper=15.0)

	def setProgramSettings(self, programSettings):
		for setting in self:
			programSettings[setting] = self[setting]

	def getProgramSettings(self, programSettings):
		for setting in self:
			self[setting] = programSettings[setting]

class programSettings(dict):
	# Override init function.
	def __init__(self, console=None):
		# Call super class init function.
		dict.__init__(self)
		# Internalise console.
		self.console = console
		# Create objects for all the settings and put them into dictionary.
		self['currentFolder'] = setting(value='./models')
		self['tmpDir'] = setting(value=os.getcwd()+'/tmp', isConstant=True)
		self['versionMajor'] = setting(value=0, isConstant=True)
		self['versionMinor'] = setting(value=11, isConstant=True)
		self['revision'] = setting(value=3, isConstant=True)
		self['projectorSizeX'] = setting(value=1024, default=1024,		name='Projector size X')
		self['projectorSizeY'] = setting(value=768, default=768,		name='Projector size Y')
		self['projectorPositionX'] = setting(value=1920, default=1920,		name='Projector position X')
		self['projectorPositionY'] = setting(value=0, default=0,		name='Projector position Y')
		self['buildSizeX'] = setting(value=102.4, default=102.4, unit='mm',		name='Build size X')
		self['buildSizeY'] = setting(value=76.8, default=76.8, unit='mm',		name='Build size Y')
		self['buildSizeZ'] = setting(value=150.0, default=150.0, unit='mm',		name='Build size Z')
		self['previewSlicesMax'] = setting(value=500, default=500, name='Number of preview slices')
#		self['projectorSizeXY'] = setting(value=[1024,768])
#		self['projectorPositionXY'] = setting(value=[1280,0])
#		self['buildSizeXYZ'] = setting(value=[102.4,76.8,150.0])

		self['pxPerMm'] =  setting(value=self['projectorSizeX'].value / self['buildSizeX'].value)

		self['port'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM0',		name='Port')
		self['baudrate'] = setting(value='57600', default=57600,		name='Baud rate')
		self['baudrateGCode'] = setting(value='115200', default=115200,		name='Baud rate')

		self['avrdudeMcu'] = setting(value='atmega32u4', default='atmega32u4',		name='MCU')
		self['avrdudeMcuGCode'] = setting(value='atmega2560', default='atmega2560',		name='MCU')
		self['avrdudeProgrammer'] = setting(value='avr109', default='avr109',		name='Programmer')
		self['avrdudeProgrammerGCode'] = setting(value='stk500v2', default='stk500v2',		name='Programmer')
		self['avrdudePort'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM0',		name='Port')
		self['avrdudePortGCode'] = setting(value='/dev/ttyACM0', default='/dev/ttyACM0',		name='Port')
		self['avrdudeBaudrate'] = setting(value='57600', default=57600,		name='Baud rate')
		self['avrdudeBaudrateGCode'] = setting(value='115200', default=115200,		name='Baud rate')
		self['avrdudeOptions'] = setting(value='-D -V', default='-D -V',		name='Options')
		self['avrdudeOptionsGCode'] = setting(value='-D -V', default='-D -V',		name='Options')
		self['avrdudeFirmwarePath'] = setting(value='./firmware/main.hex', default='./firmware/main.hex',		name='Firmware path')
		self['avrdudeFirmwarePathGCode'] = setting(value='./firmware/marlin/marlinForMonkeyprint.hex', default='./firmware/marlin/marlinForMonkeyprint.hex',		name='Firmware path')
	#	self['avrdudeSettings'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'], default=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
	#	self['avrdudeSettingsGCode'] = setting(value=['atmega2560', 'stk500v2', '/dev/ttyACM0', '115200', '-D -V -U', './firmware/marlin/marlinForMonkeyprint.hex'])
	#	self['avrdudeSettingsDefault'] = setting(value=['atmega32u4', 'avr109', '/dev/ttyACM0', '57600', '-D -V', './firmware/main.hex'])
		self['portRaspi'] = setting(value='/dev/ttyAMA0', default='/dev/ttyAMA0',		name='Port')
		self['baudrateRaspi'] = setting(value='9600', default='9600',		name='Baud rate')
		self['ipAddressRaspi'] = setting(value='192.168.2.111', default='192.168.2.111',		name='IP address')
		self['networkPortRaspi'] = setting(value='5553', default='5553',		name='Control port')
		self['fileTransmissionPortRaspi'] = setting(value='6000', default='6000',		name='File transmission port')
	#	self['SSH user name'] = setting(value='pi', default='pi')
	#	self['SSH password'] = setting(value='raspberry', default='raspberry')
		self['projectorPort'] = setting(value='/dev/ttyUSB0', default='/dev/ttyUSB0',		name='Port')
		self['projectorBaudrate'] = setting(value='9600', default='9600',		name='Baud rate')
		self['projectorControl'] = setting(value=False, default=False,		name='Projector control')
		self['projectorOnCommand'] = setting(value='* 0 IR 001', default='* 0 IR 001',		name='Projector ON command')
		self['projectorOffCommand'] = setting(value='* 0 IR 002', default='* 0 IR 002',		name='Projector OFF command')
		self['tiltStepAngle'] = setting(value=1.8, default=1.8, upper=3.6, lower=0.9, unit="°",		name='Step angle')
		self['tiltMicroStepsPerStep'] = setting(value=4, default=4, lower=1, upper=32,		name='Micro steps per step')
		self['tiltAngle'] = setting(value='130', default='130',		name='Angle')
#		self['Tilt distance GCode'] = setting(value='10', default='10', unit='mm')
		self['tiltSpeed'] = setting(value='10', default='10',		name='Speed')
		self['tiltSpeedSlow'] = setting(value='4', default='4',		name='Speed slow')
		self['tiltEnable'] = setting(value=True, default=True,		name='Enable')
		self['tiltReverse'] = setting(value=False, default=False,		name='Reverse tilt direction')
		self['buildStepAngle'] = setting(value=1.8, default=1.8, unit="°",		name='Step angle')
		self['buildMicroStepsPerStep'] = setting(value=16, default=16, lower=1, upper=32,		name='Micro steps per step')
		self['buildMmPerTurn'] = setting(value=1.0, default=1.0, unit="mm",		name='Distance per turn')
		self['buildMinimumMove'] = setting(value=0.01, default=0.01, unit="mm",		name='Minimum move')
		self['buildRampSlope'] = setting(value=15, default=15,		name='Ramp slope')
		self['buildPlatformSpeed'] = setting(value='10', default='10', unit='mm/s',		name='Speed')
		self['reverseBuild'] = setting(value=False, default=False,		name='Reverse build direction')
		self['showFill'] = setting(value=True,		name='Show fill')
		self['layerHeight'] = setting(value=0.1, lower=.05, upper=0.3, unit='mm',		name='Layer height')
		self['modelSafetyDistance'] = setting(value=1.0, unit='mm')
		self['debug'] = setting(value=False,		name='Debug')
		self['exposureTimeBase'] = setting(value=14.0, lower=0.1, upper=15.0)
		self['exposureTime'] = setting(value=9.0, lower=0.1, upper=15.0)
#		self['Resin settle time'] = setting(value=1.0, lower=0.0, upper=5.0)
		self['camTriggerWithExposure'] = setting(value=False, default=False)
		self['camTriggerAfterExposure'] = setting(value=False, default=False)
		self['calibrationImagePath'] = setting(value="./calibrationImage", default="./calibrationImage")
		self['calibrationImage'] = setting(value=False, default=False)
		self['showVtkErrors'] = setting(value=True, default=False)
		self['runningOnRaspberry'] = setting(value=False, default=False)
		self['printOnRaspberry'] = setting(value=False, default=False)
		self['shutterPositionOpen'] = setting(value=4, default=4, lower=0, upper=10, 		name='Shutter position closed')
		self['shutterPositionClosed'] = setting(value=6, default=6, lower=0, upper=10, 		name='Shutter position closed')
#		self['Shutter position open GCode'] = setting(value=550, default=550, lower=500, upper=2500)
#		self['Shutter position closed GCode'] = setting(value=2450, default=2450, lower=500, upper=2500)
		self['enableShutterServo'] = setting(value=False, default=False, 	name='Enable shutter servo')
		self['localMkpPath'] = setting(value='./currentPrint.mkp', default='./currentPrint.mkp')
		self['monkeyprintBoard'] = setting(value=True, default=True)
#		self['Tilt GCode']	 = setting(value='G1 X{$tiltDist*$tiltDir} F10 G1 X{-$tiltDist*$tiltDir} F10', default = 'G1 X{$tiltDist*$tiltDir} F10 G1 X{-$tiltDist*$tiltDir} F10')
#		self['Build platform GCode'] = setting(value='G1 Z{$layerHeight*$buildDir} F10', default='G1 Z{$layerHeight*$buildDir} F10')
#		self['Shutter open GCode'] = setting(value='M280 P0 S{$shutterPosOpen}', default='M280 P0 S{$shutterPosOpen}')
#		self['Shutter close GCode'] = setting(value='M280 P0 S{$shutterPosClosed}', default='M280 P0 S{$shutterPosClosed}')
#		self['Start commands GCode'] = setting(value='G21 G91 M17', default='G21 G91 M17')
#		self['End commands GCode'] = setting(value='M18', default='M18')
#		self['Home GCode'] = setting(value='G28', default='G28')
#		self['Top GCode'] = setting(value='G28 Z0', default='G28 Z0')
		# Modules for print process. Values are: Type, Display name, Value, Unit, Editable.
		self['printModulesMonkeyprint'] = setting(value=	'Initialise printer,,,internal,False;Wait,1.0,,internal,True;Build platform layer up,,buildUp,serialMonkeyprint,False;Build platform to home,,buildHome,serialMonkeyprint,False;Build platform to top,,buildTop,serialMonkeyprint,False;Tilt,,tilt,serialMonkeyprint,False;Shutter open,,shutterOpen,serialMonkeyprint,False;Shutter close,,shutterClose,serialMonkeyprint,False;Expose,,,internal,False;Projector on,,projectorOn,serialMonkeyprint,False;Projector off,,projectorOff,serialMonkeyprint,False;Start loop,,,internal,False;End loop,,,internal,False')
		self['printModulesGCode'] = setting(value='Wait,1.0,,internal,True;Initialise printer,G21 G91 M17,,serialGCode,True;Build platform layer up,G1 Z{$layerHeight} F100,,serialGCode,True;Build platform to home,G28 X Z,,serialGCode,True;Build platform to top,G162 Z F100,,serialGCode,True;Tilt down,G1 X20 F1000,,serialGCode,True;Tilt up,G1 X-20 F1000,,serialGCode,True;Shutter open,M280 P0 S500,,serialGCode,True;Shutter close,M280 P0 S2500,,serialGCode,True;Expose,,,internal,False;Projector on,,,internal,False;Projector off,,,internal,False;Start loop,,,internal,False;End loop,,,internal,False;Shut down printer,M18,,serialGCode,True;Set steps per unit,M92 X 20.8 Z 10.2,,serialGCode,True;Emergency stop,M112,,serialGCode,True;Beep,M300 S440 P500,,serialGCode,True;Custom G-Code,G91,,serialGCode,True')
		self['printProcessMonkeyprint'] = setting(value='Initialise printer,,,internal,False;Projector on,,projectorOn,serialMonkeyprint,False;Build platform to home,,buildHome,serialMonkeyprint,False;Start loop,,,internal,False;Shutter open,,shutterOpen,serialMonkeyprint,False;Expose,,,internal,False;Shutter close,,shutterClose,serialMonkeyprint,False;Tilt,,tilt,serialMonkeyprint,False;Wait,1.0,,internal,True;End loop,,,internal,False;Build platform to top,,buildTop,serialMonkeyprint,False')
		self['printProcessGCode'] = setting(value='Initialise printer,G21 G91 M17,,serialGCode,True;Projector on,---,,internal,False;Build platform to home,G28 X Z,,serialGCode,True;Start loop,---,,internal,False;Shutter open,M280 P0 S500,,serialGCode,True;Expose,---,,internal,False;Shutter close,M280 P0 S2500,,serialGCode,True;Tilt down,G1 X20 F1000,,serialGCode,True;Build platform layer up,G1 Z{$layerHeight} F100,,serialGCode,True;Tilt up,G1 X-20 F1000,,serialGCode,True;Wait,1.0,,internal,True;End loop,---,,internal,False;Build platform to top,G162 F100,,serialGCode,True;Shut down printer,M18,,serialGCode,True')
		#self['calibrationImageFile'] = setting(value="calibrationImage.jpg", default="calibrationImage.jpg")
		self['polylineClosingThreshold'] = setting(value=0.1, default=0.1, lower=0.0, upper=1.0)
		self['sliceStackMemory'] = setting(value=50, default=500, lower=100, unit='MB', name='Slicer memory')

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
	def readFile(self, filename=None):
		if filename==None:
			filename = 'programSettings.txt'
		try:
			# Open file.
			with open(filename, 'r') as f:
				# Loop through lines.
				for line in f:
					if line != "":
						self.string2Setting(line)
				if self.console != None:
					self.console.addLine("Settings loaded from file.")
		except IOError:
			if self.console != None:
				self.console.addLine("No settings file found. Using defaults.")


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
				moduleList[i][-1] = eval(moduleList[i][-1])
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
		if self['monkeyprintBoard'].value == True:
			printProcessList = self['printProcessMonkeyprint'].value.split(';')
			for i in range(len(printProcessList)):
				# Split comma separated string for each command.
				printProcessList[i] = printProcessList[i].split(',')
				# Turn True/False string into boolean.
				printProcessList[i][-1] = eval(printProcessList[i][-1])
			return printProcessList
		else:
			printProcessList = self['printProcessGCode'].value.split(';')
			for i in range(len(printProcessList)):
				# Split comma separated string for each command.
				printProcessList[i] = printProcessList[i].split(',')
				# Turn True/False string into boolean.
				printProcessList[i][-1] = eval(printProcessList[i][-1])
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
