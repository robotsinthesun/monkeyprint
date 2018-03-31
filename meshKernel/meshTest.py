import pyximport; pyximport.install()
import monkeyprintMesh
import numpy as np

from mpl_toolkits import mplot3d
from matplotlib import pyplot

if __name__ == "__main__":

	mesh = monkeyprintMesh.mesh()
	mesh.readStl("../models/monkey.stl", 10)
	mesh.scale(2, np.array((0,0,0)))
	mesh.rotate(np.array((0,0,1)), 3.1415/2.)
	mesh.detectOverhangs(45.)
	mesh.createSliceContours(0.1)

	figure = pyplot.figure()
	axes = mplot3d.Axes3D(figure)
	faces = np.asarray(mesh.points)[np.asarray(mesh.indicesFaceToPoint)]
	axes.add_collection3d(mplot3d.art3d.Poly3DCollection(faces))
	axes.set_xlim(-10, 10)
	axes.set_ylim(-10, 10)
	axes.set_zlim(-10, 10)
	pyplot.show()

