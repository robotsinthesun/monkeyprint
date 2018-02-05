import numpy
import time
from stl import mesh




class basicMesh:

	def __init__(self):
		self.points = []
		self.faces = []
		self.normals = []



	def loadFromStl(self, path):
		timeStart = time.time()
		tolerance = 0.0001
		self.your_mesh = mesh.Mesh.from_file(path)
		# Remove duplicate points.
		points = []
		faces = []
		# Walk through faces.
		for i in range(self.your_mesh.points.shape[0]):
			face = []
			for j in range(3):
				point = self.your_mesh.points[i, 0+3*j:3+3*j]
				#print ("   Current point: ({i:g}) [{p0:g}, {p1:g}, {p2:g}]".format(i=i,p0=point[0], p1=point[1], p2=point[2]))
				if len(points) > 0:
					for k in range(len(points)):
						if numpy.linalg.norm(point - points[k]) < tolerance:
							#print("     Found duplicate.")
							face.append(k)
							break
					if len(face) == j:
						#print("     New point.")
						points.append(point)
						face.append(len(points)-1)
				else:
					#print("     First point.")
					points.append(point)
					face.append(0)
				# Check if they exist already.
				'''
				try:
					k = points.index(point)
				except ValueError:
					print("foo")
					points.append(point)
					face.append(len(points)-1)
				else:
					face.append(k)
				'''
			faces.append(face)
		print("Loaded stl in {n:g} seconds.".format(n=time.time()-timeStart))

		print ("Number of points: {n:g}".format(n=len(points)))
		print ("Number of faces: {n:g}".format(n=len(faces)))
		print (self.your_mesh.points.shape[0])





	def saveAsStl(self, path):
		pass

class face:

	vertices = []
	normal = []



if __name__ == "__main__":
	m = basicMesh()
	m.loadFromStl('./models/monkey.stl')
	print(m.your_mesh.points.shape)
	print(m.your_mesh.normals.shape)
