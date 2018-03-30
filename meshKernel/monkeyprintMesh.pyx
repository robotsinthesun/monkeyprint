import numpy as np
import math
import struct
import time


# Mesh class.
cdef class mesh:

	cdef public double[:,:] bounds
	cdef public double[:,:] points
	cdef public unsigned int[:,:] faces
	cdef public double[:,:] normals
	cdef public double[:,:] axes

	def __init__(self):
		# Set bounds min to double maxvalue, bounds max to double minvalue.
		self.bounds = np.vstack((np.repeat(np.finfo(np.float64).max,3),np.repeat(np.finfo(np.float64).min,3)))
		self.points = np.empty((0,3), dtype=np.float64)
		self.faces = np.empty((0,3), dtype=np.uint32)
		self.normals = np.empty((0,3), dtype=np.float64)
		self.axes = np.array([[1,0,0], [0,1,0], [0,0,1]], dtype=np.float64)

	cpdef readStl(self, filepath):
		tStart = time.time()
		cdef unsigned int i = 0
		cdef unsigned int j = 0
		cdef unsigned int counterPoint = 0
		cdef unsigned int nFaces
		# Check if ascii or binary file.
		with open(filepath) as f:
			start = f.read(6)
			if start == "solid":
				pass
			else:
				# Read the rest of the header.
				header = start + f.read(74)
				#print header
				# Read number of faces. This is uint32 --> read for bytes.
				nFaces = struct.unpack('<i', f.read(4))[0]
				# Pre-assign arrays.
				self.points = np.empty((nFaces*3,3), dtype=np.float64)
				self.faces = np.empty((nFaces,3), dtype=np.uint32)
				self.normals = np.empty((nFaces,3), dtype=np.float64)
				pointsTmp = []
				facesTmp = []
				# Read faces.
				for i in range(nFaces):
					# Read normal.
					self.normals[i][0] = struct.unpack('<f4', f.read(4))[0]
					self.normals[i][1] = struct.unpack('<f4', f.read(4))[0]
					self.normals[i][2] = struct.unpack('<f4', f.read(4))[0]
					# Read points.
					for j in range(3):
						# Add point.
						#print struct.unpack('<i', f.read(4))[0]
						self.points[counterPoint][0] = struct.unpack('<f4', f.read(4))[0]
						self.points[counterPoint][1] = struct.unpack('<f4', f.read(4))[0]
						self.points[counterPoint][2] = struct.unpack('<f4', f.read(4))[0]
						# Extend bounds.
						self.faces[i][j] = counterPoint
						counterPoint += 1
					# Read the face attribute. Discard...
					f.read(2)
			# Move model bottom to build platform.
			self.bounds = np.vstack((np.min(self.points, axis=0), np.max(self.points, axis=0)))
			self.translate(-np.asarray(self.bounds)[0,2])
		print "Read stl in " + str(time.time()-tStart) + " seconds."
		print "   Bounds: " + str(np.asarray(self.bounds))












	  ##### ##     ###### ####   #####    ####   ####  ##  ## ###### ####  ##  ## #####
	 ##     ##       ##  ##  ## ##       ##  ## ##  ## ### ##   ##  ##  ## ##  ## ##  ##
	  ####  ##       ##  ##     ####     ##     ##  ## ######   ##  ##  ## ##  ## ##  ##
	     ## ##       ##  ##     ##       ##     ##  ## ## ###   ##  ##  ## ##  ## #####
	     ## ##       ##  ##  ## ##       ##  ## ##  ## ##  ##   ##  ##  ## ##  ## ## ##
	 #####  ###### ###### ####   #####    ####   ####  ##  ##   ##   ####   ####  ##  ##





	# Caution: point Z values must be all positive.
	cpdef createSliceContours(self, double layerHeight):
		#timePrepSum = 0
		#timeSliceSum = 0
		timeStart = time.time()
		sliceContours = {}
		cdef double[3][3] points
		cdef double[3][3] pointsSorted
		cdef double[2][2] segment
		#cdef double[:,:] points
		#cdef double pointsC[] = [1,2]
		cdef unsigned int i = 0
		cdef unsigned int j = 0
		cdef unsigned long sliceStart
		cdef unsigned long sliceEnd
		cdef double z
		#cdef unsigned int[:] slicePositionsZ
		cdef bint intersectionFound
		for i in range(self.faces.shape[0]):


			# Get points.
			# Can't get the slicing to work properly so we'll get each
			# coordinate individually.
			points[0][0] = self.points[self.faces[i,0],0]
			points[0][1] = self.points[self.faces[i,0],1]
			points[0][2] = self.points[self.faces[i,0],2]
			points[1][0] = self.points[self.faces[i,1],0]
			points[1][1] = self.points[self.faces[i,1],1]
			points[1][2] = self.points[self.faces[i,1],2]
			points[2][0] = self.points[self.faces[i,2],0]
			points[2][1] = self.points[self.faces[i,2],1]
			points[2][2] = self.points[self.faces[i,2],2]

			# Sort points.
			#print "--------------------------------------------------------------------"
			# A B C or A C B or B C A
			if points[0][2] < points[1][2]:
				if points[1][2] < points[2][2]:
					#print "A B C"
					pointsSorted = points
				# A C B
				else:
					if points[0][2] < points[2][2]:
						#print "A C B"
						pointsSorted[0][0] = points[0][0]
						pointsSorted[0][1] = points[0][1]
						pointsSorted[0][2] = points[0][2]
						pointsSorted[1][0] = points[2][0]
						pointsSorted[1][1] = points[2][1]
						pointsSorted[1][2] = points[2][2]
						pointsSorted[2][0] = points[1][0]
						pointsSorted[2][1] = points[1][1]
						pointsSorted[2][2] = points[1][2]
					# B C A
					else:
						#print "B C A"
						pointsSorted[0][0] = points[2][0]
						pointsSorted[0][1] = points[2][1]
						pointsSorted[0][2] = points[2][2]
						pointsSorted[1][0] = points[0][0]
						pointsSorted[1][1] = points[0][1]
						pointsSorted[1][2] = points[0][2]
						pointsSorted[2][0] = points[1][0]
						pointsSorted[2][1] = points[1][1]
						pointsSorted[2][2] = points[1][2]

			# B A C or C B A or C A B
			else:
				# C B A
				if points[1][2] > points[2][2]:
					#print "C B A"
					pointsSorted[0][0] = points[2][0]
					pointsSorted[0][1] = points[2][1]
					pointsSorted[0][2] = points[2][2]
					pointsSorted[1][0] = points[1][0]
					pointsSorted[1][1] = points[1][1]
					pointsSorted[1][2] = points[1][2]
					pointsSorted[2][0] = points[0][0]
					pointsSorted[2][1] = points[0][1]
					pointsSorted[2][2] = points[0][2]
				# C A B or B A C
				else:
					# C A B
					if points[0][2] > points[2][2]:
						#print "C A B"
						pointsSorted[0][0] = points[1][0]
						pointsSorted[0][1] = points[1][1]
						pointsSorted[0][2] = points[1][2]
						pointsSorted[1][0] = points[2][0]
						pointsSorted[1][1] = points[2][1]
						pointsSorted[1][2] = points[2][2]
						pointsSorted[2][0] = points[0][0]
						pointsSorted[2][1] = points[0][1]
						pointsSorted[2][2] = points[0][2]
					# B A C
					else:
						#print "B A C"
						pointsSorted[0][0] = points[1][0]
						pointsSorted[0][1] = points[1][1]
						pointsSorted[0][2] = points[1][2]
						pointsSorted[1][0] = points[0][0]
						pointsSorted[1][1] = points[0][1]
						pointsSorted[1][2] = points[0][2]
						pointsSorted[2][0] = points[2][0]
						pointsSorted[2][1] = points[2][1]
						pointsSorted[2][2] = points[2][2]


			#print points[0][2], points[1][2], points[2][2]
			#print pointsSorted[0][2], pointsSorted[1][2], pointsSorted[2][2]
			#if pointsSorted[0][2] > pointsSorted[1][2]:
			#	print "A > B"
			#if pointsSorted[1][2] > pointsSorted[2][2]:
			#	print "B > C"
			#if pointsSorted[0][2] > pointsSorted[2][2]:
			#	print "A > C"



			# Get relevant slice positions, i.e. those within the triangle z bounds.
			sliceStart = int(math.ceil(pointsSorted[0][2] / layerHeight))
			sliceEnd = int(math.floor(pointsSorted[2][2] / layerHeight))
			slicePositionsZ = range(sliceStart, sliceEnd + 1)
			'''

			# Create lines.
			# Order: bottom to mid, bottom to top, mid to top.
			#line0 = points[0:2]
			#line1 = points[[0,2]]
			#line2 = points[1:3]
			'''

			for j in slicePositionsZ:

				z = j * layerHeight
				#print "   " + str(z)
				intersectionFound = False
				# Walk through lines and check for intersections.
				# Ignore top and bottom point intersections as they do not
				# result in a line segment.
				# Top and mid point.
				# Can only happen for last slice.
				if j != slicePositionsZ[-1] and z == pointsSorted[2][2] and z == pointsSorted[1][2]:
					#segment = [ pointsSorted[1,0:2], pointsSorted[1,0:2]]
					segment[0][0] = pointsSorted[1][0]
					segment[0][1] = pointsSorted[1][1]
					segment[1][0] = pointsSorted[2][0]
					segment[1][1] = pointsSorted[2][1]
					intersectionFound = True

				# Bottom and mid point.
				# Can only happen for first slice.
				elif not j == slicePositionsZ[0] and z == pointsSorted[0][2] and z == pointsSorted[1][2]:
					#segment = [ pointsSorted[0,0:2], pointsSorted[1,0:2]]
					segment[0][0] = pointsSorted[0][0]
					segment[0][1] = pointsSorted[0][1]
					segment[1][0] = pointsSorted[1][0]
					segment[1][1] = pointsSorted[1][1]
					intersectionFound = True

				# Mid point
				elif z == pointsSorted[1][2]:
					# There must be an intersection in the second line.
					#intersectionXY = intersectLineZ(line1, z)
					#segment = [ pointsSorted[1,0:2], self.intersectLineZ(pointsSorted[[0,2]], z)]
					segment[0][0] = pointsSorted[1][0]
					segment[0][1] = pointsSorted[1][1]
					self.intersectLineZ(pointsSorted[0], pointsSorted[2], segment[1], z)
					intersectionFound = True
				# Intersection below mid point.
				elif z < pointsSorted[1][2]:
					# There must be an intersection in first and seconds line.
					#segment = [ self.intersectLineZ(pointsSorted[0:2], z), self.intersectLineZ(pointsSorted[[0,2]], z) ]
					self.intersectLineZ(pointsSorted[0], pointsSorted[1], segment[0], z)
					self.intersectLineZ(pointsSorted[0], pointsSorted[2], segment[1], z)
					intersectionFound = True
				elif z < pointsSorted[2][2]:
					# There must be an intersection in second and third line.
					#segment = [ self.intersectLineZ(pointsSorted[[0,2]], z), self.intersectLineZ(pointsSorted[1:3], z) ]
					self.intersectLineZ(pointsSorted[0], pointsSorted[2], segment[0], z)
					self.intersectLineZ(pointsSorted[1], pointsSorted[2], segment[1], z)
					intersectionFound = True
				else:
					print "CAUTION: Slice plane does not intersect face."

				# Append to slice contours.
				#TODO: OPTIMIZE
				#WE KNOW THE NUMBER OF SLICES BEFOREHAND, WE SHOULD USE THIS
				#IN ORDER TO APPEND SEGMENTS TO AN ARRAY INSTEAD OF A DICT.
				#BUT WE DON'T KNOW NUMBER OF SEGMENTS, SO ARRAY MIGHT NOT WORK.
				if intersectionFound:
					try:
						sliceContours[j].append(segment)
					except KeyError:
						sliceContours[j] = [segment]


		print(len(sliceContours))
		print("Sliced in " + str(time.time() - timeStart) + " seconds.")

		'''
		# Now we have an array that contains slice contour segments
		# We'll loop over these arrays and try to combine stray lines into closed polylines.
		# Start timer.
		timeStart = time.time()
		polylinesClosedAll = []
		polylinesCorruptedAll = []

		for i in range(len(pointsInputAll)):
			# Get current points.
			points = pointsInputAll[i]
			# Remove Z dimension.
			points = points[:,0:2]
			# Scale to fit the image (convert from mm to px).
			points[:,0] *= self.pxPerMmX
			points[:,1] *= self.pxPerMmX
			# Move points to center of image.
			points[:,0] -= self.position[0]
			points[:,1] -= self.position[1]
			# Flip points y-wise because image coordinates start at top.
			points[:,1] = abs(points[:,1] - self.size[1])

			# Get current lines.
			# Lines contain point indices in the right order for each polyline.
			# However, there might be polyline segments that are not connected.
			# We need to connect all polyline segments.
			lines = linesInputAll[i]
			numberOfPolylines = numberOfPolylinesInputAll[i]

			polylineIndicesClosed = []
			polylineIndicesOpen = []
			startIndex = 0

			# Check if there are connecting polylines.
			# This is necessary because some polylines from the stripper output may still be segmented.
			# Two polylines are connected if the start or end point indices are equal.
			# Test for start/start, end/end, start/end, end/start.
			# NOTE: The lines array contains point indices for all polylines.
			# It consists of multiple blocks, each block starting with the
			# number of points, followed by the point indices. Then, the next block starts with the
			# next number of points, followed by the point indices and so on...
			for polyline in range(numberOfPolylines):
				#print "Polyline " + str(polyline) + ". ****************"
				numberOfPoints = lines[startIndex]
				#print "   Start point: " + str(points[lines[startIndex+1]]) + "."
				#print "   End point: " + str(points[lines[startIndex+numberOfPoints]]) + "." # -1
				# Get the indices starting just behind the start index.
				polylineInd = lines[startIndex+1:startIndex+1+numberOfPoints]

				# Check if polyline is closed. If yes, append to closed list.
				if polylineInd[0] == polylineInd[-1]:
					#print "   Found closed polyline."
					polylineIndicesClosed.append(polylineInd)
				# If not, check if this is the first open one. If yes, append.
				else:# len(polylineIndicesOpen) == 0:
					#print "   Found open polyline."
					polylineIndicesOpen.append(polylineInd)

				# Set start index to next polyline.
				startIndex += numberOfPoints+1


			# Get closed polyline points according to indices.
			polylinesClosed = []
			for polyline in polylineIndicesClosed:
				polylinePoints = points[polyline]
				polylinesClosed.append(polylinePoints)


			# Get open polyline points according to indices.
			polylinesOpen = []
			for polyline in polylineIndicesOpen:
				polylinePoints = points[polyline]
				polylinesOpen.append(polylinePoints)

			#print "   Found " + str(len(polylinesClosed)) + " closed segments."
			#print "   Found " + str(len(polylinesOpen)) + " open segments."

			# Loop over open polyline parts and pick the ones that connect.
			# Do this until everything is connected.
			#print "Trying to connect open segments."
			polylinesCorrupted = []
			# Create list of flags for matched segments.
			matched = [False for i in range(len(polylinesOpen))]
			# Loop through open segments.
			for i in range(len(polylinesOpen)):
				#print "Testing open segment " + str(i) + ". ********************************"

				# Get a segment and try to match it to any other segment.
				# Only do this if the segment has not been matched before.
				if matched[i] == True:
					pass
					#print "   Segment was matched before. Skipping."
				else:
					segmentA = polylinesOpen[i]

					#print (segmentA[0] == segmentA[0]).all()

					# Flag that signals if any of the other segments was a match.
					runAgain = True # Set true to start first loop.
					while runAgain == True:
						# Set false to stop loop if no match is found.
						runAgain = False
						isClosed = False
						# Loop through all other segments check for matches.
						for j in range(len(polylinesOpen)):
							# Only if this is not segmentA and if it still unmatched.
							if j != i and matched[j] == False:

								# Get next piece to match to current piece.
								segmentB = polylinesOpen[j]

								# Compare current piece and next piece start and end points.
								# If a match is found, add next piece to current piece.
								# Loop over next pieces until no match is found or the piece is closed.
								# Start points equal: flip new array and prepend.
								if (segmentB[0] == segmentA[0]).all():
									#print "   Start-start match with segment " + str(j) + "."
									segmentA = numpy.insert(segmentA, 0, numpy.flipud(segmentB[1:]), axis=0)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now is closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True


								elif (segmentB[0] == segmentA[-1]).all():
									#print "   Start-end match with segment " + str(j) + "."
									segmentA = numpy.append(segmentA, segmentB[1:])
									segmentA = segmentA.reshape(-1,2)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

								elif (segmentB[-1] == segmentA[0]).all():
									#print "   End-start match with segment " + str(j) + "."
									segmentA = numpy.insert(segmentA, 0, segmentB[:-1], axis=0)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

								elif (segmentB[-1] == segmentA[-1]).all():
									#print "   End-end match with segment " + str(j) + "."
									segmentA = numpy.append(segmentA, numpy.flipud(segmentB[:-1]), axis=0)
									segmentA = segmentA.reshape(-1,2)
									matched[j] = True
									# Check if this closes the line.
									if (segmentA[0] == segmentA[-1]).all():
										#print "      Polyline now closed."
										polylinesClosed.append(segmentA)
										isClosed = True
										runAgain = False
										break
									else:
										runAgain = True

						# If no match was found and segmentA is still open,
						# copy it to defective segments array.
						if runAgain == False and isClosed == False:
							endPointDistance = math.sqrt( pow((segmentA[0][0] -segmentA[-1][0])/self.pxPerMmX, 2) + pow((segmentA[0][1] -segmentA[-1][1])/self.pxPerMmY, 2) )
							if endPointDistance < (self.polylineClosingThreshold):
								#print "      End point distance below threshold. Closing manually."
								polylinesClosed.append(segmentA)
							else:
								#print "      Giving up on this one..."
								polylinesCorrupted.append(segmentA)
						elif runAgain == False and isClosed == True:
							pass
							#print "   Segment is closed. Advancing to next open segment."
						else:
							pass
							#print "   Matches were found. Restarting loop to find more..."

			polylinesClosedAll.append(polylinesClosed)

			if len(polylinesCorrupted) != 0:
				polylinesCorruptedAll.append(polylinesCorrupted)

		# End timer.
		if self.debug:
			interval = time.time() - interval
			print "Polyline point sort time: " + str(interval) + " s."
		'''














	# Only works if Z plane is within Z bounds of line.
	cdef intersectLineZ(self, double[3] point0, double[3] point1, double[:] pointOut, double z):
		# This is simply a linear interpolation.
		# First, get relative position t of intersection on line.
		cdef double[3] delta
		delta[0] = point1[0] - point0[0]
		delta[1] = point1[1] - point0[1]
		delta[2] = point1[2] - point0[2]
		cdef double t
		t = (z - point0[2]) / delta[2]
		if t > 1:
			print "CAUTION: Sliceplane does not intersect edge."
		# Now, scale X and Y with relative position, add start point offset and return.
		pointOut[0] = delta[0] * t + point0[0]
		pointOut[1] = delta[1] * t + point0[1]

		'''
		# This is simply a linear interpolation.
		# First, get relative position of intersection on line.
		delta = line[1] - line[0]
		t = (Z - line[0,2]) / delta[2]
		# Now, scale X and Y with relative position, add start point offset and return.
		return delta[0:2] * t + line[0,0:2]
		'''


	def translate(self, vector):
		tStart = time.time()
		self.points += vector
		#self.bounds = np.vstack((np.min(self.points, axis=0), np.max(self.points, axis=0)))
		self.bounds += vector
		#print "Translated in " + str(time.time()-tStart) + " seconds."
		#print "   Bounds: " + str(np.asarray(self.bounds))


	def rotate(self, axis, theta, center=None):
		tStart = time.time()
		if center == None:
			center = (np.asarray(self.bounds)[0,:] + np.asarray(self.bounds)[1,:]) / 2.0
		# Rotate axes to keep track of orientation.
		self.axes = np.dot(self.axes, self.rotation_matrix(axis, theta).T)
		# Rotate points.
		self.translate(-center)
		self.points = np.dot(self.points, self.rotation_matrix(axis, theta).T)
		self.translate(center)
		# Recompute bounds.
		self.bounds = np.vstack((np.min(self.points, axis=0), np.max(self.points, axis=0)))
		#print "Rotated in " + str(time.time()-tStart) + " seconds."
		#print "   Bounds: " + str(np.asarray(self.bounds))


	def rotation_matrix(self, axis, theta):
		"""
		Return the rotation matrix associated with counterclockwise rotation about
		the given axis by theta radians.
		"""
		axis = np.asarray(axis)
		axis = axis/math.sqrt(np.dot(axis, axis))
		a = math.cos(theta/2.0)
		b, c, d = -axis*math.sin(theta/2.0)
		aa, bb, cc, dd = a*a, b*b, c*c, d*d
		bc, ad, ac, ab, bd, cd = b*c, a*d, a*c, a*b, b*d, c*d
		return np.array([[aa+bb-cc-dd, 2*(bc+ad), 2*(bd-ac)],
		                 [2*(bc-ad), aa+cc-bb-dd, 2*(cd+ab)],
		                 [2*(bd+ac), 2*(cd-ab), aa+dd-bb-cc]])






