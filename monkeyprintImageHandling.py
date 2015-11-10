#!/usr/bin/python

from matplotlib import pyplot as plot
import numpy
import Image
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
