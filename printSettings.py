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


class printSettings:
	def __init__(self):
	
		self.debug = True
	
		self.buildVolumeSize = [192, 108, 300]	# [mm]
		
		self.projectorSizeXYDebug = [500,300]			# [px]
		self.projectorPositionXYDebug = [1500,600]
		self.projectorSizeXY = [1920, 1080]			# [px]
		self.projectorPositionXY = [1280, 0]

		
		self.pxPerMm = self.projectorSizeXY[0] / self.buildVolumeSize[0]
		
		self.filename = ""
		
		self.scaling = 1						# []
		self.scalingMin = 0.000001
		# scalingMax must be set by model position, rotation and size

		self.rotationXYZ = [0, 0, 0]			# [°]
		self.rotationXYZMin = [0, 0, 0]
		self.rotationXYZMax = [359, 359, 359]

		self.positionXYRel = [50, 50]			# [%]
		self.positionXYRelMin = [0, 0]
		self.positionXYRelMax = [100, 100]

		self.bottomPlateThickness = 0.5		# [mm]
		self.bottomPlateThicknessMin = 0.1
		self.bottomPlateThicknessMax = 1.0

		self.bottomClearance = 5				# [mm]
		self.bottomClearanceMin = self.bottomPlateThicknessMin
		# bottomClearanceMax must be set by model position, rotation and size
				
		self.overhangAngle = 40				# [°]
		self.overhangAngleMin = 5	
		self.overhangAngleMax = 80
		
		self.supportBaseDiameter = 1.5		# [mm]
		self.supportBaseDiameterMin = 0.3	
		self.supportBaseDiameterMax = 5.0	
		
		self.supportTipDiameter = .5			# [mm]
		self.supportTipDiameterMin = .1
		self.supportTipDiameterMax = .5
		
		self.supportTipHeight = 2.5			# [mm]
		self.supportTipHeightMin = 1.0
		self.supportTipHeightMax = 10.0
		
		self.supportSpacingXY = [5.0, 5.0]		# [mm]
		self.supportSpacingXYMin = [self.supportBaseDiameter*2.0, self.supportBaseDiameter*2.0]
		self.supportSpacingXYMax = [10.0, 10.0]		
		# TODO: max should be depending on model size

		self.supportMaxHeight = 20.0		# [mm]

		self.layerHeight = 0.1				# [mm]
		self.layerHeightMax = 0.3
		self.layerHeightMin = 0.1
		
		self.hollow = True
		self.fill = True
		self.fillShow = True
		self.shellThickness = 2.0		# [mm]
		self.fillSpacing = 3.0		# [mm]
		self.fillWallThickness = 0.3	# [mm]
		
		self.baseLayerHeight = 0.2				# [mm]
		self.baseLayerHeightMax = 0.3
		self.baseLayerHeightMin = 0.1
		
		self.exposureTime = 9.0				# [s]
		self.exposureTimeBase = 14.0			# [s]
		self.settleTime = 3.0
		
		self.tiltAngle = 14
		self.tiltSpeedSlow = 8
		self.tiltSpeedFast = 11
		
		self.stepsPerMm = 100


	# Build volume size ##################################
	def setBuildVolumeSize(self, buildVolumeSize):
		self.buildVolumeSize = buildVolumeSize
	
	def getBuildVolumeSize(self):
		return self.buildVolumeSize
		

	# Projector size #####################################
	def setProjectorSizeXY(self, projectorSizeXY):
		for i in range(2):
			self.projectorSizeXY[i] = projectorSizeXY[i]
	
	def getProjectorSizeXY(self):
		return self.projectorSizeXY
	
	def getProjectorSizeXYDebug(self):
		return self.projectorSizeXYDebug

	# Projector position #################################
	def getProjectorPositionXY(self):
		return self.projectorPositionXY

	def getProjectorPositionXYDebug(self):
		return self.projectorPositionXYDebug	
	
	# File name ##########################################
	def setFilename(self, filename):
		self.filename = filename
		
	def getFilename(self):
		return self.filename
	
	
	# Scaling ############################################
	def setScaling(self, scaling):
		self.scaling = scaling
	
	def getScaling(self):
		return self.scaling
	
	
	# Rotation ###########################################
	def setRotationXYZ(self, rotationXYZ):
		for i in range(3):
			self.rotationXYZ[i] = rotationXYZ[i]
	
	def getRotationXYZ(self):
		return self.rotationXYZ
	
	
	# Position XY ########################################
	def setPositionXYRel(self, positionXYRel):
		for i in range(2):
			self.positionXYRel[i] = positionXYRel[i]
	
	def getPositionXYRel(self):
		return self.positionXYRel
		
		
	# Position Z (bottom clearance) ######################
	def setBottomClearance(self, bottomClearance):
		self.bottomClearance = bottomClearance
	
	def getBottomClearance(self):
		return self.bottomClearance		
		
		
	# Overhang angle #####################################
	def setOverhangAngle(self, overhangAngle):
		self.overhangAngle = overhangAngle
		
	def getOverhangAngle(self):
		return self.overhangAngle	

	# Bottom plate thickness. ############################
	def setBottomPlateThickness(self, bottomPlateThickness):
		if bottomPlateThickness < 0:
			self.bottomPlateThickness = 0
		elif bottomPlateThickness > self.bottomClearance:
			self.bottomPlateThickness = self.bottomClearance
		else:
			self.bottomPlateThickness = bottomPlateThickness
	
	def getBottomPlateThickness(self):
		return self.bottomPlateThickness

	# Support base diameter ##############################
	def setSupportBaseDiameter(self, supportBaseDiameter):
		self.supportBaseDiameter = supportBaseDiameter
	
	def getSupportBaseDiameter(self):
		return self.supportBaseDiameter	
	
	# Support tip diameter ###############################
	def setSupportTipDiameter(self, supportTipDiameter):
		self.supportTipDiameter = supportTipDiameter

	def getSupportTipDiameter(self):
		return self.supportTipDiameter	
	
	# Support tip height #################################
	def setSupportTipHeight(self, supportTipHeight):
		self.supportTipHeight = supportTipHeight
	
	def getSupportTipHeight(self):
		return self.supportTipHeight

	# Support maximum height #############################
	def setSupportMaxHeight(self, supportMaxHeight):
		if supportMaxHeight < self.bottomClearance:
			self.supportMaxHeight = self.bottomClearance
		elif supportMaxHeight > self.buildVolumeSize[2]:
			self.supportMaxHeight = self.buildVolumeSize[2]
		else:
			self.supportMaxHeight = supportMaxHeight
	
	def getSupportMaxHeight(self):
		return self.supportMaxHeight

	
	# Support spacing ####################################
	def setSupportSpacingXY(self, supportSpacingXY):
		for i in range(2):
			self.supportSpacingXY[i] = supportSpacingXY[i]
	
	def getSupportSpacingXY(self):
		return self.supportSpacingXY
		
		
	# Fill switch ########################################
	def setHollow(self, hollow):
		self.hollow = hollow
	
	def getHollow(self):
		return self.hollow
		
	# Fill switch ########################################
	def setFill(self, fill):
		self.fill = fill
	
	def getFill(self):
		return self.fill
	
	# Fill show switch ###################################
	def setFillShow(self, fillShow):
		self.fillShow = fillShow
	
	def getFillShow(self):
		return self.fillShow

	# Shell thickness ################################
	def setShellThickness(self, shellThickness):
		self.shellThickness = shellThickness
	
	def getShellThickness(self):
		return self.shellThickness
	
	# Fill spacing #######################################
	def setFillSpacing(self, fillSpacing):
		self.fillSpacing = fillSpacing
	
	def getFillSpacing(self):
		return self.fillSpacing

	# Fill wall thickness ################################
	def setFillWallThickness(self, fillWallThickness):
		self.fillWallThickness = fillWallThickness
	
	def getFillWallThickness(self):
		return self.fillWallThickness
		
	# Layer height #######################################
	def setLayerHeight(self, layerHeight):
		self.layerHeight = layerHeight
	
	def getLayerHeight(self):
		return self.layerHeight

	# Base layer height ##################################
	def setBaseLayerHeight(self, baseLayerHeight):
		self.baseLayerHeight = baseLayerHeight
	
	def getBaseLayerHeight(self):
		return self.baseLayerHeight

	# Build speed ########################################
	def setBuildSpeed(self, buildSpeed):
		if buildSpeed > 4:
			self.buildSpeed = 4
		elif buildSpeed < 1:
			self.buildSpeed = 1
		else:
			self.buildSpeed = buildSpeed
	
	def getBuildSpeed(self):
		return self.buildSpeed

	# Tilt speed slow ###################################
	def setTiltSpeedSlow(self, tiltSpeedSlow):
		if tiltSpeedSlow > 12:
			self.tiltSpeedSlow = 12
		elif tiltSpeedSlow < 1:
			self.tiltSpeedSlow = 1
		else:
			self.tiltSpeedSlow = tiltSpeedSlow
	
	def getTiltSpeedSlow(self):
		return self.tiltSpeedSlow

	# Tilt speed fast ###################################
	def setTiltSpeedFast(self, tiltSpeedFast):
		if tiltSpeedFast > 12:
			self.tiltSpeedFast = 12
		elif tiltSpeedFast < 1:
			self.tiltSpeedFast = 1
		else:
			self.tiltSpeedFast = tiltSpeedFast
	
	def getTiltSpeedFast(self):
		return self.tiltSpeedFast

	# Tilt angle ########################################
	def setTiltAngle(self, tiltAngle):
		if tiltAngle > 18:
			self.tiltAngle = 18
		elif tiltAngle < 5:
			self.tiltAngle = 5
		else:
			self.tiltAngle = tiltAngle
	
	def getTiltAngle(self):
		return self.tiltAngle
	
	# Exposure time ######################################
	def setExposureTime(self, exposureTime):
		if exposureTime < 1:
			self.exposureTime = 1.0
		else:
			self.exposureTime = exposureTime
	
	def getExposureTime(self):
		return self.exposureTime
	
	# Exposure time base #################################
	def setExposureTimeBase(self, exposureTimeBase):
		if exposureTimeBase < 1:
			self.exposureTimeBase = 1.0
		else:
			self.exposureTimeBase = exposureTimeBase
	
	def getExposureTimeBase(self):
		return self.exposureTimeBase
	
	# Resin settle time ##################################
	def setSettleTime(self, settleTime):
		if settleTime < 0:
			self.settleTime = 0
		else:
			self.settleTime = settleTime
	
	def getSettleTime(self):
		return self.settleTime
	
	# Stepper steps per mm. ##############################
	def getStepsPerMm(self):
		return self.stepsPerMm
	
	# All model settings. ################################
	def setModelSettings(self, modelSettings):
		self.scaling = modelSettings[0]
		self.rotationXYZ = modelSettings[1, 2, 3]
		self.positionXYRel = modelSettings[4, 5]
		self.bottomClearance = modelSettings[6]
	
	def getModelSettings(self, modelSettings):
		return [ self.scaling, self.rotationXYZ[0], self.rotationXYZ[1], self.rotationXYZ[2], self.positionXYRel[0], self.positionXYRel[1], self.bottomClearance ]
	
	def getPxPerMm(self):
		return self.pxPerMm
	
	def getDebugStatus(self):
		return self.debug
	
	def resetModelSettings(self):
		print "foo"
		self.scaling = 1
		self.rotationXYZ = [0, 0, 0]
		self.positionXYRel = [50, 50]
		self.bottomClearance = 5
	
	# Print behaviour.
	def __str__(self):
		return "Scaling: " + str(self.scaling) + "\n" + "Rotation X: " + str(self.rotationXYZ[0]) + "\n" + "Rotation Y: " + str(self.rotationXYZ[1]) + "\n" + "Rotation Z: " + str(self.rotationXYZ[2]) + "\n" + "PositionXRel: " + str(self.positionXYRel[0]) + "\n" + "PositionYRel: " + str(self.positionXYRel[1]) + "\n" + "Bottom clearance: " + str(self.bottomClearance)
		
