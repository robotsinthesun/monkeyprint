import pyximport; pyximport.install()
import monkeyprintMesh
import numpy as np

if __name__ == "__main__":

	mesh = monkeyprintMesh.mesh()
	mesh.readStl("../models/monkey.stl", 10)
	mesh.translate(np.array((0,1,1)))
	mesh.rotate(np.array((0,0,1)), 3.1415/2.)
	mesh.createSliceContours(0.1)

