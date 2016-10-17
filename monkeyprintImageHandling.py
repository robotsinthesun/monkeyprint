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


#from matplotlib import pyplot as plot
import numpy
from scipy import ndimage
from PIL import Image
import math

def array2image(a):
    if a.typecode() == Numeric.UnsignedInt8:
        mode = "L"
    elif a.typecode() == Numeric.Float32:
        mode = "F"
    else:
        raise ValueError, "unsupported image mode"
    return Image.fromstring(mode, (a.shape[1], a.shape[0]), a.tostring())

# Create a single channel, noisy image.
def createImageNoisy(width=None, height=None):
	# Swap width and height to retain real life coordinate system.
	imageNoisy = numpy.random.rand(height, width) * 255
	imageNoisy = numpy.uint8(imageNoisy)
	return imageNoisy

# Create single channel image.
def createImageGray(width, height, value):
	# Swap width and height to retain real life coordinate system.
	return numpy.zeros((height, width), numpy.uint8) + value

def createImageRing():
	return numpy.array([	[0,1,1,0],
						[1,0,0,1],
						[1,0,0,1],
						[0,1,1,0]	]) * 255


# Display an image using matplot.
def showImage(img):
	plot.imshow(img, interpolation='nearest')
	plot.show()

# Convert to single channel BW.
def convertGrayscaleSingle(img):
	img = img.mean(-1)
	img = numpy.uint8(img)
	return img


# Insert smaller image.
def insert(img, imgIns, pos):
	bounds = [	pos[1],
				pos[1]+imgIns.shape[0],
				pos[0],
				pos[0]+imgIns.shape[1]	]
	img[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] = imgIns
	return img

def imgMultiply(img1, img2, pos):
	bounds = [	int(pos[1]),
				int(pos[1]+img2.shape[0]),
				int(pos[0]), 
				int(pos[0]+img2.shape[1])	]
	# Convert to uint32, otherwise multiply will wrap inside 255.
	img1 = numpy.uint32(img1)
	img2 = numpy.uint32(img2)
	img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] = (img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] * img2) / 255
	numpy.clip(img1, 0, 255, out=img1)
	img1 = numpy.uint8(img1)
	return img1

def imgAdd(img1, img2, pos):
	bounds = [	int(pos[1]),
				int(pos[1]+img2.shape[0]),
				int(pos[0]), 
				int(pos[0]+img2.shape[1])	]
	# Convert to uint32, otherwise multiply will wrap inside 255.
	img1 = numpy.uint32(img1)
	img2 = numpy.uint32(img2)
	img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] = (img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] + img2)
	numpy.clip(img1, 0, 255, out=img1)
	img1 = numpy.uint8(img1)
	return img1

def imgSubtract(img1, img2, pos):
	bounds = [	pos[1],
				pos[1]+img2.shape[0],
				pos[0], 
				pos[0]+img2.shape[1]	]
	# Convert to uint32, otherwise multiply will wrap inside 255.
	img1 = numpy.uint32(img1)
	img2 = numpy.uint32(img2)
	img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] = img1[bounds[0]:bounds[1] , bounds[2]:bounds[3] ] - img2
	numpy.clip(img1, 0, 255, out=img1)
	img1 = numpy.uint8(img1)
	return img1


def imgBinarise(img):
	img = img / 255
	return img

def imgInvert(img):
	img = numpy.invert(img, dtype='uint8')
	return img

def imgManhattanDistance(img):
	# O(n^2) solution to find the Manhattan distance to "on" pixels in a two dimension array
	# Taken from http://blog.ostermiller.org/dilate-and-erode
	# Find the nearest on pixel.
	# Traverse from top left to bottom right.
	print "manhattan start"
	for i in range(img.shape[0]):			#for (int i=0; i<image.length; i++){
		for j in range(img.shape[1]):			#for (int j=0; j<image[i].length; j++){
			# If the current pixel is on...
			if img[i,j] == 1:					#if (image[i][j] == 1){
				# ... it gets a 0 as the distance to itself is 0.
					img[i,j] = 0
			# If the current pixel is off...
			else:
				# ... its distance to the next on pixel is at most
				# the sum of the lengths of the array...
				img[i,j] = img.shape[0] + img.shape[1]
				# ... or one more than the pixel to the north...
				if i > 0:		#if (i>0) image[i][j] = Math.min(image[i][j], image[i-1][j]+1);
					img[i,j] = min(img[i,j], img[i-1,j]+1)
				# ... or one more than the pixel to the west...
				if j > 0:                # if (j>0) image[i][j] = Math.min(image[i][j], image[i][j-1]+1);
					img[i,j] = min(img[i,j], img[i,j-1]+1)

	print "manhattan 1"
	# Traverse from bottom right to top left.
	for i in range(img.shape[0]-1, -1, -1):
		for j in range(img.shape[1]-1, -1, -1):
			# The distance of the current pixel to the next on pixel
			# is either what we had on the first pass or
			# one more than the pixel to the south...
			if i+1 < img.shape[0]:		#if (i+1<image.length) image[i][j] = Math.min(image[i][j], image[i+1][j]+1);
				img[i,j] = min(img[i,j], img[i+1,j]+1)
			# ... or one more than the pixel to the east.
			if j+1 < img.shape[1]:		#if (j+1<image[i].length) image[i][j] = Math.min(image[i][j], image[i][j+1]+1);
				img[i,j] = min(img[i,j], img[i,j+1]+1)
	
	print "manhattan 2"
	# Distances are set, return the distance map.
	return img;


# Erode. This will shrink white areas in an image by a given radius.
def imgErodeSlow(img, radius=1):
	# First, we need to binarise and invert the image to create the distance map.
	distanceMap = imgManhattanDistance(imgBinarise(imgInvert(img)))
	print "manhattan done"
	# Copy the input image.
	eroded = numpy.zeros_like(img, dtype='uint8')
	print "zeros"
	# Now, all pixels with distance above threshold will get a 0.
	for i in range(eroded.shape[0]):
		for j in range(eroded.shape[1]):
			if distanceMap[i,j] > radius:
				eroded[i,j] = 255
	print "eroded"
	# Return the eroded image as 0..255.
	return eroded

def imgErodeScipy(img, radius=1):
	return ndimage.binary_erosion(img, structure=numpy.ones((radius,radius))).astype(img.dtype)


# Dilate. This will grow white areas in an image by a given radius.
def imgDilate(img, radius=1):
	# First, we need to binarise the image to create the distance map.
	distanceMap = imgManhattanDistance(imgBinarise(img))
	# Copy the input image.
	dilated = numpy.ones_like(img, dtype='uint8') * 255
	# Now, all pixels with distance above threshold will get a 0.
	for i in range(dilated.shape[0]):
		for j in range(dilated.shape[1]):
			if distanceMap[i,j] > radius:
				dilated[i,j] = 0
	# Return the eroded image as 0..255.
	return dilated


# Convert single channel to 3 channel grayscale.
def convertSingle2RGB(img):
	# Expand in 3d dimension.
	img = numpy.expand_dims(img, axis=2)
	img = numpy.repeat(img, 3, axis=2)
	return img

'''
imageInsert = createImageGray(4,2,50)
imageRing= createImageRing()

print imageRing
image = createImageNoisy(20,10)
imageGrayscale1Ch = convertGrayscaleSingle(image)
imageInserted = insert(imageGrayscale1Ch, imageInsert, [3,1])
imageMultiplied = imgMultiply(imageInserted, imageRing, [12,3])
imageSubtracted = imgSubtract(imageInserted, imageRing, [12,3])
print imageSubtracted
imageGrayscale = convertSingle2RGB(imageSubtracted)
showImage(imageGrayscale)
'''
