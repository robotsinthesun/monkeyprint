# dependencies:
# - python-qt4-gl
import pyximport; pyximport.install()
import monkeyprintMesh

import sys
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtOpenGL
from OpenGL import GLU
from OpenGL.GL import *
import numpy as np

import monkeyprintMesh


class GLWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        self.parent = parent
        QtOpenGL.QGLWidget.__init__(self, parent)

        # Define initial camera position.
        self.cameraRotationX = 35.0
        self.cameraRotationZ = 45.0
        self.cameraDistanceInitial = 5.
        self.cameraDistance = self.cameraDistanceInitial

        self.setMouseTracking(True)
        self.mouseRotate = False
        self.mousePan = False
        self.mousePositionOld = QtCore.QPoint(0, 0)
        self.backgroundColor = (0.4, 0.4, 0.5)

        self.rot1 = 0.0
        self.rot2 = 0.0

    def mousePressEvent(self, event):

        print event.modifiers()
        # Check button.
        # Right click.
        if event.buttons() == QtCore.Qt.RightButton:
            self.mousePan = True
        # Middle click. --> Does not work on thinkpad?
        #elif event.buttons() == QtCore.Qt.MiddleButton:
            #offset = event.globalPos() - self.mousePositionOld
            #self.mousePositionOld = event.globalPos()
            #self.viewZoom(np.sqrt(offset.x()**2 + offset.y()**2))
        elif event.buttons() == QtCore.Qt.LeftButton:
            self.mouseRotate = True
        # Save current mouse position to track movement.
        self.mousePositionOld = event.globalPos()
        super(GLWidget, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        super(GLWidget, self).mouseDoubleClickEvent(event)
        print "Double click"
        # TODO: select model.

    def mouseReleaseEvent(self, event):
        super(GLWidget, self).mouseReleaseEvent(event)
        self.mouseRotate = False
        self.mousePan = False

    def wheelEvent(self, event):
        super(GLWidget, self).wheelEvent(event)
        self.viewZoom(event.delta()*0.01)


    def mouseMoveEvent(self, event):
        super(GLWidget, self).mouseMoveEvent(event)
        if self.mouseRotate:
            offset = event.globalPos() - self.mousePositionOld
            self.mousePositionOld = event.globalPos()
            self.viewRotate(offset.x(), offset.y())

        elif self.mousePan:
            pass

    def initializeGL(self):
        self.initGeometry()
        glEnable(GL_DEPTH_TEST)

    def resizeGL(self, width, height):
        if height == 0: height = 1

        glViewport(0, 0, width, height)

        # Switch into projection matrix mode.
        # This is the matrix that controls how the
        # 3d world is translated into a 2d view.
        glMatrixMode(GL_PROJECTION)
        # Reset projection matrix.
        glLoadIdentity()
        # Get widget aspect ration.
        aspect = width / float(height)
        # Set camera
        # Angle: 45 degrees
        # Aspect: widget aspect
        # Near plane: 1
        # Far plane: 1000
        GLU.gluPerspective(45.0, aspect, 0.01, 1000.0)
        # Switch back into model view matrix mode.
        # This is where the model-to-world and world-to-view matrices
        # are modified.
        glMatrixMode(GL_MODELVIEW)

    # This get's called on self.updateGL()
    def paintGL(self):
        # Clear buffers.
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        # Set background color.
        glClearColor(self.backgroundColor[0], self.backgroundColor[1], self.backgroundColor[2], 0)

        # Set up the view and model matrices.
        # Basically, we're setting up a stack of transformation matrices.
        # In GL_MODELVIEW mode we have at least 32 matrices in that stack that we
        # can use.
        # The first maps from the world to the view (the camera, which is static).
        # The others map from the world to the individual models in the scene.
        # So first, set the world-to-view matrix. The key part here is that
        # we move the world, not the camera.

        # First, reset current view matrix. Now, the coordinate systems of world
        # and view are equal.
        glLoadIdentity()

        # Now, use the camera info to move the world in order to achieve the desired
        # view. glScale, glRotate and glTranslate will modify the current matrix in the background.
        # The camera is always positioned at (0, 0, 0) and the world is as well.
        #gluLookAt(camera.position.x, camera.position.y, camera.position.z, camera.lookat.x, camera.lookat.y, camera.lookat.z, 0, 1, 0)
        # First, move away the world so that the camera looks at the origin from a distance.
        glTranslate(0.0, 0.0, -self.cameraDistance)
        # Then, rotate the world around that new origin.
        glRotate(-self.cameraRotationX, 1, 0, 0)
        glRotate(-self.cameraRotationZ, 0, 0, 1)

        # Now, let's draw some objects.
        # For this, we'll advance to the next matrix on the stack.
        # glPushMatrix() also copies the previous matrix to the now current one.
        # This means that our world-to-view transform will stay the same.
        glPushMatrix()

        # Transform according to the object data.
        glTranslate(0.5, 0.5, 0.5)
        glRotate(self.rot1, 0,0,1)
        glScale(0.5, 0.5, 0.5)

        # Draw the object.
        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(self.cubeVtxArray)
        glColorPointerf(self.cubeClrArray)
        glDrawElementsui(GL_QUADS, self.cubeIdxArray)

        # glPopMatrix() restores the previous matrix, which is the world-to-view matrix.
        # This means we leave the previous objects transform behind and start over new.
        glPopMatrix()
        glPushMatrix()


        # Transform according to the object data.
        glTranslate(-0.75, -0.75, 0.5)
        glRotate(self.rot2, 0,0,1)
       # glScale(0.5, 0.5, 0.5)

        glEnableClientState(GL_VERTEX_ARRAY)
        glEnableClientState(GL_COLOR_ARRAY)
        glVertexPointerf(self.cubeVtxArray)
        glColorPointerf(self.cubeClrArray)
        glDrawElementsui(GL_QUADS, self.cubeIdxArray)

        glPopMatrix()
        glPushMatrix()

        glBegin(GL_TRIANGLES)
        for face in self.stlFaces:
            #glNormal3f(tri.normal.x,tri.normal.y,tri.normal.z)
            glVertex3f(self.stlVertices[face[0]][0], self.stlVertices[face[0]][1], self.stlVertices[face[0]][2])
            glVertex3f(self.stlVertices[face[1]][0], self.stlVertices[face[1]][1], self.stlVertices[face[1]][2])
            glVertex3f(self.stlVertices[face[2]][0], self.stlVertices[face[2]][1], self.stlVertices[face[2]][2])
        glEnd()

        glPopMatrix()
        glPushMatrix()

        # Draw axes.
        glLineWidth(2)
        glColor(1.0, 0.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(1, 0, 0)
        glEnd()
        glColor(0.0, 1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 1, 0)
        glEnd()
        glColor(0.0, 0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 1)
        glEnd()

        # Once again, go back to world-to-view matrix.
        glPopMatrix()


    def initGeometry(self):

        mesh = monkeyprintMesh.mesh()
        mesh.readStl("../models/monkey.stl", 10)
        mesh.scale(0.2)
        self.stlVertices = np.asarray(mesh.points)
        self.stlFaces = np.asarray(mesh.indicesFaceToPoint).tolist()
        self.stlColors = [[1,1,1] for i in range(len(self.stlFaces))]


        self.cubeVtxArray = np.array(
                [[-0.5, -0.5, -0.5],
                 [0.5, -0.5, -0.5],
                 [0.5, 0.5, -0.5],
                 [-0.5, 0.5, -0.5],
                 [-0.5, -0.5, 0.5],
                 [0.5, -0.5, 0.5],
                 [0.5, 0.5, 0.5],
                 [-0.5, 0.5, 0.5]])
        self.cubeIdxArray = [
                0, 1, 2, 3,
                3, 2, 6, 7,
                1, 0, 4, 5,
                2, 1, 5, 6,
                0, 3, 7, 4,
                7, 6, 5, 4 ]
        self.cubeClrArray = [
                [0.0, 0.0, 0.0],
                [1.0, 0.0, 0.0],
                [1.0, 1.0, 0.0],
                [0.0, 1.0, 0.0],
                [0.0, 0.0, 1.0],
                [1.0, 0.0, 1.0],
                [1.0, 1.0, 1.0],
                [0.0, 1.0, 1.0 ]]


    # Process x and y mouse movements from the screen.
    # x maps to rotation around the VIEW's x coordinate.
    # y maps to rotation around the VIEW's z coordinate.
    def viewRotate(self, y, x):
        self.cameraRotationX = (self.cameraRotationX  - x) % 360.0
        self.cameraRotationZ = (self.cameraRotationZ  - y) % 360.0
        self.parent.statusBar().showMessage('rotation %f' % self.cameraRotationZ)
        self.updateGL()

    def viewZoom(self, deltaZ):
        # Let
        self.cameraDistance = max(0.011, self.cameraDistance + deltaZ*(self.cameraDistance/20))
        print self.cameraDistance
        self.updateGL()

    def spinCubes(self):
        self.rot1 += 1
        self.rot2 += 2
        self.updateGL()

class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.resize(300, 300)
        self.setWindowTitle('GL Cube Test')

        self.initActions()
        self.initMenus()
        self.statusBar()

        glWidget = GLWidget(self)
        self.setCentralWidget(glWidget)

        timer = QtCore.QTimer(self)
        timer.setInterval(20)
        QtCore.QObject.connect(timer, QtCore.SIGNAL('timeout()'), glWidget.spinCubes)
        #timer.start()


    def initActions(self):
        self.exitAction = QtGui.QAction('Quit', self)
        self.exitAction.setShortcut('Ctrl+Q')
        self.exitAction.setStatusTip('Exit application')
        self.connect(self.exitAction, QtCore.SIGNAL('triggered()'), self.close)

    def initMenus(self):
        menuBar = self.menuBar()
        fileMenu = menuBar.addMenu('&File')
        fileMenu.addAction(self.exitAction)

    def close(self):
        QtGui.qApp.quit()

app = QtGui.QApplication(sys.argv)

win = MainWindow()
win.show()

sys.exit(app.exec_())
