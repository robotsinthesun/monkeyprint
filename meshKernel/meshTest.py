import pyximport; pyximport.install()
import monkeyprintMesh
import numpy as np

if __name__ == "__main__":

	mesh = monkeyprintMesh.mesh()
	mesh.readStl("../models/monkey.stl", 10)
	mesh.scale(2, np.array((0,0,0)))
	mesh.rotate(np.array((0,0,1)), 3.1415/2.)
	mesh.detectOverhangs(45.)
	mesh.createSliceContours(0.1)

