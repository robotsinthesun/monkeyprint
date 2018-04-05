# dependencies:
# - python-qt4-gl
import pyximport; pyximport.install()
import monkeyprintMesh

import sys
from PyQt4 import QtCore
from PyQt4 import QtGui
from PyQt4 import QtOpenGL
from OpenGL import GLU
import OpenGL
import OpenGL.GL.shaders
from OpenGL import GL
from OpenGL.GL import *
from OpenGL.arrays import vbo

from OpenGL.GLUT import *

import numpy as np
import time
import monkeyprintMesh

# Define shaders.
vertex_shader = """
#version 120
void main() {
gl_Position = gl_ModelViewProjectionMatrix * gl_Vertex;
}
"""

fragment_shader = """
#version 120
uniform ivec4 color;
// Define pick color as integer. This way we can save some memory.
uniform ivec3 colorPick;
uniform int flagPick;
void main(){
    // Check if we are picking or not.
    //if(flagPick == 0)
    //{
    //    gl_FragColor = color;
    //}
    // If picking we need to transfer the integer pick color to float between 0.0 and 1.0.
    //else
    //{
        gl_FragColor = vec4(color[0]/255.0, color[1]/255.0, color[2]/255.0, 1.0);
   // }


}
"""




class GLWidget(QtOpenGL.QGLWidget):
    def __init__(self, parent=None):
        self.parent = parent
        QtOpenGL.QGLWidget.__init__(self, parent)

        # Define initial camera position.
        self.cameraRotationX = 35.0
        self.cameraRotationZ = 45.0
        self.cameraDistanceInitial = 20.
        self.cameraDistance = self.cameraDistanceInitial

        self.setMouseTracking(True)
        self.mouseRotate = False
        self.mousePan = False
        self.mousePositionOld = QtCore.QPoint(0, 0)

        self.colorBackground = (0.4, 0.4, 0.5)
        self.colorModelDefault = [int(n*255) for n in (0.7, 0.7, 0.0)]
        self.colorModelHover = [int(n*255) for n in (0.5, 0.5, 0.0)]
        self.colorModelSelected = [int(n*255) for n in (0.8, 0.5, 0.0)]

        self.indexHover = 0
        self.indexSelected = 0


        self.rot1 = 0.0
        self.rot2 = 0.0


        self.objects = {}
        self.vbos = {}


    def mousePressEvent(self, event):

        mods = event.modifiers()

        # Check button.
        # Right click.
        if event.buttons() == QtCore.Qt.RightButton:
            if mods == QtCore.Qt.ControlModifier:
                self.mousePan == True
            else:
                self.mouseRotate = True
            #self.mousePan = True
        # Middle click. --> Does not work on thinkpad?
        #elif event.buttons() == QtCore.Qt.MiddleButton:
            #offset = event.globalPos() - self.mousePositionOld
            #self.mousePositionOld = event.globalPos()
            #self.viewZoom(np.sqrt(offset.x()**2 + offset.y()**2))
        elif event.buttons() == QtCore.Qt.LeftButton:
            if self.indexHover > 0:
                if self.indexSelected != self.indexHover:
                    self.indexSelected = self.indexHover
                    self.updateGL()
            elif self.indexSelected != self.indexHover:
                self.indexSelected = 0
                self.updateGL()
        # Save current mouse position to track movement.
        self.mousePositionOld = event.globalPos()
        super(GLWidget, self).mousePressEvent(event)

    def mouseDoubleClickEvent(self, event):
        super(GLWidget, self).mouseDoubleClickEvent(event)
        #print self.colorPick(event.pos().x(), event.pos().y())
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
        # Check which object the cursor is on.
        #if objectPicked != None:

        # Rotate or pan if mouse is pressed without an object picked.
        if self.mouseRotate:
            offset = event.globalPos() - self.mousePositionOld
            self.mousePositionOld = event.globalPos()
            self.viewRotate(offset.x(), offset.y())
        elif self.mousePan:
            pass
        else:
            i = self.getPixelColor(event.pos().x(), event.pos().y())
            if self.indexHover != i:
                self.indexHover = i
                self.updateGL()




    def initializeGL(self):
        width = 500
        height = 700
        # Create a texture and a frame buffer object for picking.
        # Texture.
        texturePick = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, texturePick)
        # Framebuffer.
        self.framebufferPick = glGenFramebuffers(1)
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebufferPick)
        # Set texture to framebuffer.
        # TODO: Check if resizing works.
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGB, width, height, 0, GL_RGB, GL_FLOAT, None)
        glFramebufferTexture2D(GL_FRAMEBUFFER, GL_COLOR_ATTACHMENT0, GL_TEXTURE_2D, texturePick, 0)

        # Create render buffer. This is needed to make depth testing work for the frame buffer.
        renderBufferPick = glGenRenderbuffers(1)
        glBindRenderbuffer(GL_RENDERBUFFER, renderBufferPick)
        glRenderbufferStorage(GL_RENDERBUFFER, GL_DEPTH_COMPONENT, width, height)
        glFramebufferRenderbuffer(GL_FRAMEBUFFER, GL_DEPTH_ATTACHMENT, GL_RENDERBUFFER, renderBufferPick)

        # Unbind the picking framebuffer and texture.
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        glBindTexture(GL_TEXTURE_2D, 0)
        glBindRenderbuffer(GL_RENDERBUFFER, 0)

        # Compile the shader program and activate it.
        self.shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vertex_shader, GL.GL_VERTEX_SHADER), OpenGL.GL.shaders.compileShader(fragment_shader, GL.GL_FRAGMENT_SHADER))
        shaders.glUseProgram(self.shader)

        # Set up uniforms. Get the locations in memory for the uniforms used in the shader program.
        self.locationGlColor =  glGetUniformLocation(self.shader, "color")
        self.locationGlColorPick =  glGetUniformLocation(self.shader, "colorPick")
        self.locationGlFlagPick =  glGetUniformLocation(self.shader, "flagPick")

        # Enable depth testing for overlapping objects.
        glEnable(GL_DEPTH_TEST)
        #glShadeModel(GL_SMOOTH);
        #glEnable(GL_MULTISAMPLE);



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
        # Set background color.
        glClearColor(self.colorBackground[0], self.colorBackground[1], self.colorBackground[2], 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
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
        # Loop through all objects.
        for i in self.objects:

            if self.objects[i].visible:
                glPushMatrix()

                # Transform according to the object data.
                glTranslate(self.objects[i].position[0], self.objects[i].position[1], self.objects[i].position[2])
                glRotate(self.rot1, 0,0,1)
                glScale(self.objects[i].scale, self.objects[i].scale, self.objects[i].scale)

                # Render the object.

                # Set pick colors. This has to happen after activating the shader program
                # OpenGL expects colors to be in [0,1], so divide by 255.
                if i > 0 and i == self.indexSelected:
                    c = self.colorModelSelected
                elif i > 0 and i == self.indexHover:
                    c = self.colorModelHover
                else:
                    if self.objects[i].color is not None:
                        c = self.objects[i].color
                    else:
                        c = self.colorModelDefault
                if self.objects[i].enabled:
                    t = 255
                else:
                    t = int(0.3*255)
                glUniform4i(self.locationGlColor, c[0], c[1], c[2], t)
                #c = self.objects[i].colorPick
                #glUniform4i(self.locationGlColor, c[0], c[1], c[2], 255)

                try:
                    self.vbos[i].bind()
                    try:
                        glEnableClientState(GL_VERTEX_ARRAY)
                        glVertexPointerf( self.vbos[i] )
                        glDrawArrays(GL_TRIANGLES, 0, self.objects[i].faces.shape[0] * 3)
                    finally:
                        self.vbos[i].unbind()
                        glDisableClientState(GL_VERTEX_ARRAY)
                finally:
                    pass

                glPopMatrix()

        # Draw to the picking frame buffer.
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebufferPick)
        glClearColor(0.0, 0.0, 0.0, 1.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        #glUniform1i(self.locationGlFlagPick, 1)
        for i in self.objects:

            if self.objects[i].visible:
                glPushMatrix()

                # Transform according to the object data.
                glTranslate(self.objects[i].position[0], self.objects[i].position[1], self.objects[i].position[2])
                glRotate(self.rot1, 0,0,1)
                glScale(self.objects[i].scale, self.objects[i].scale, self.objects[i].scale)

                # Render the object.

                # Set pick colors.
                c = self.objects[i].colorPick
                glUniform4i(self.locationGlColor, c[0], c[1], c[2], 255)

                try:
                    self.vbos[i].bind()
                    try:
                        glEnableClientState(GL_VERTEX_ARRAY)
                        glVertexPointerf( self.vbos[i] )
                        glDrawArrays(GL_TRIANGLES, 0, self.objects[i].faces.shape[0] * 3)
                    finally:
                        self.vbos[i].unbind()
                        glDisableClientState(GL_VERTEX_ARRAY)
                finally:
                    pass

                glPopMatrix()
        glBindFramebuffer(GL_FRAMEBUFFER, 0)

        '''
        glPushMatrix()

        # Draw axes.
        # This is the legacy version.
        glLineWidth(2)
        glColor(1.0, 0.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(15, 0, 0)
        glEnd()
        glColor(0.0, 1.0, 0.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 15, 0)
        glEnd()
        glColor(0.0, 0.0, 1.0, 0.0)
        glBegin(GL_LINES)
        glVertex3f(0, 0, 0)
        glVertex3f(0, 0, 15)
        glEnd()

        # Once again, go back to world-to-view matrix.
        glPopMatrix()
        '''
    def getPixelColor(self, x, y):
        # Set picking frame buffer.
        glBindFramebuffer(GL_FRAMEBUFFER, self.framebufferPick)
        # Sample the pixel under the mouse.
        # Swap the y direction using the viewport size.
        # Also it appears that gl pixel count starts at 0 while qt count starts at 1.
        # Map to 8-bit color range.
        color = glReadPixels(x - 1, glGetIntegerv(GL_VIEWPORT)[3] - y + 1, 1, 1, GL_RGB, GL_FLOAT)[0][0]
        i = self.colorToId([int(c*255) for c in color])
        if i > 0:
            self.parent.statusBar().showMessage('Object id %i' % i)
        else:
            self.parent.statusBar().clear()
        # Reset default frame buffer.
        glBindFramebuffer(GL_FRAMEBUFFER, 0)
        return i



    def colorToId(self, color):
        return color[0] + color[1]*256 + color[2]*256*256

    def idToColor(self, i):
        return [i%256, (i/256)%256, (i/(256*256))%256]

    #def initGeometry(self):

        '''
        mesh = monkeyprintMesh.mesh()
        mesh.readStl("../models/monkey.stl", 10)
        vertices = np.asarray(mesh.points).astype(np.float32)
        faces = np.asarray(mesh.indicesFaceToPoint)
        self.vertices = vertices[faces].reshape(-1, 3)
        '''

        '''
        self.vertices = np.array( [
            [0.0, 0.0, 0.7],
            [0.3, -0.3, -0.3],
            [0.0, 0.7, -0.3],
            [0.0, 0.0, 0.7],
            [0.0, 0.7, -0.3],
            [-0.3, -0.3, -0.3],
            [0.0, 0.0, 0.7],
            [-0.3, -0.3, -0.3],
            [0.3, -0.3, -0.3],
            [0.3, -0.3, -0.3],
            [-0.3, -0.3, -0.3],
            [0.0, 0.7, -0.3]
             ], 'f') * 10. + np.array((5, 5, 3), 'f')

        self.vbo = vbo.VBO(self.vertices)
        '''

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
        self.updateGL()

    def spinCubes(self):
        self.rot1 += 1
        self.rot2 += 2
        self.updateGL()

    def addObject(self, obj):
        # Search for the smallest free id.
        # There are 2^24 ids in the RGB space.
        # Start at 1 because the canvas is black and
        # id 0 will have black color.
        i = 1
        while i < 256*256*256:
            if not i in self.objects.keys():
                self.objects[i] = obj
                # Set vertices.
                self.vbos[i] = vbo.VBO(obj.vertices[obj.faces])
                # Set pick color.
                #
                obj.colorPick = self.idToColor(i)
                return i
            i += 1









class renderObject:

    def __init__(self):

        self.vertices = np.array( [
            [0.0, 0.0, 0.7],
            [0.3, -0.3, -0.3],
            [0.0, 0.7, -0.3],
            [-0.3, -0.3, -0.3]
             ], 'f')

        self.faces = np.array([[0,1,2], [0,2,3], [0,3,1], [3,2,1]])

        self.position = [np.random.rand()*10-5, np.random.rand()*10-5, np.random.rand()*10-5]
        self.scale = np.random.rand()*3
        self.quaternion = [np.random.rand(), np.random.rand(), np.random.rand(), np.random.rand()*np.pi]
        self.visible = True
        self.enabled = bool(np.random.rand())#True
        self.selected = False
        self.color = np.random.randint(low=0, high=255, size=(3,1))
        self.colorPick = None

    def getRotationX(self):
        pass












class MainWindow(QtGui.QMainWindow):

    def __init__(self):
        QtGui.QMainWindow.__init__(self)

        self.resize(500, 700)
        self.setWindowTitle('GL Cube Test')

        self.initActions()
        self.initMenus()
        self.statusBar()

        glWidget = GLWidget(self)
        self.setCentralWidget(glWidget)

        for i in range(300):
            glWidget.addObject(renderObject())


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
