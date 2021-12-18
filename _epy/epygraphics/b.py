from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from _epy.epygraphics.opengl import *
import numpy as np
import threading

class TestThread(threading.Thread):
	def __init__(self, obj, *args, **kwargs):
		super(TestThread, self).__init__(*args, **kwargs)
		self.obj = obj
	
	def run(self):
		while True:
			self.obj.render()
		

class GLCube(GLObject3D):
	def __init__(self, x, y, z, size, *args, **kwargs):
		verticies, edges= self.generateArray(x, y, z, size)
		super(GLCube, self).__init__(verticies=verticies, edges=edges, *args, **kwargs)
		self.x, self.y, self.z = x, y, z
		self.size = size
		self.color_array = verticies
		
	@staticmethod
	def generateArray(x, y, z, size):
		sh = size/2
		verticies = ((x-sh, y-sh, z-sh), (x+sh, y-sh, z-sh), (x-sh, y+sh, z-sh), (x+sh, y+sh, z-sh), 
			(x-sh, y-sh, z+sh), (x+sh, y-sh, z+sh), (x-sh, y+sh, z+sh), (x+sh, y+sh, z+sh))
		edges = ((0, 1), (2, 3), (1, 3), (5, 7), (4, 5), (6, 7), (0, 2), (4, 6), (0, 4), (1, 5), (2, 6), (3, 7))
		return verticies, edges
			
			
class GLPixel(GLObject2D):
	def __init__(self, x, y, width=1, height=1, *args, **kwargs):
		self.x1, self.y1 = x, y
		self.x2, self.y2 = x+width, y+height
		self.x3, self.y3 = x+(width*0.5), y+(height*0.5)
		self.width = width
		self.height = height
		self.verticies = ((self.x1, self.y1), (self.x2, self.y1), (self.x2, self.y2), (self.x1, self.y2))
		super(GLPixel, self).__init__(self.verticies, *args, **kwargs)
		if self._vbo:
			self.face_verticies = (np.array((self.x1, self.y1, 0, 
						self.x1, self.y2, 0, 
						self.x2, self.y1, 0, 
						self.x1, self.y2, 0,
						self.x2, self.y1, 0,
						self.x2, self.y2, 0), dtype=np.float32))
			self.vertex_buffer = vbo.VBO(self.face_verticies)

		