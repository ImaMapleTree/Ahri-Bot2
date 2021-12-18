from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from _epy.epygraphics.opengl.base import *
import numpy as np
import threading
		
class GLCube(GLObject3D):
	def __init__(self, x, y, z, size, *args, **kwargs):
		verticies, edges= self.generateArray(x, y, z, size)
		super(GLCube, self).__init__(verticies=verticies, edges=edges, *args, **kwargs)
		self.x, self.y, self.z = x, y, z
		self.center = (x, y, z)
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
	def __init__(self, x, y, width=1, height=1, color=(1.0, 1.0, 1.0), *args, **kwargs):
		self.x1, self.y1 = x, y
		self.x2, self.y2 = self.x1+width, self.y1+height
		self.width = width
		self.height = height
		self.color = color
		self.vertex_buffer = None
		self.color_buffer = None
		self.color_points = np.array((self.color, self.color, self.color, self.color), dtype=np.float32).flatten()
		
		self.verticies = ((self.x1, self.y1), (self.x2, self.y1), (self.x2, self.y2), (self.x1, self.y2))
		super(GLPixel, self).__init__(self.verticies, *args, **kwargs)
		self.calculate_geometry()
		self.pointer = None
			
	
	def calculate_geometry(self):
		self.x2, self.y2 = self.x1+self.width, self.y1+self.height
		self.center = ((self.x2+self.x1)/2, (self.y2+self.y1)/2)
		self.coords = (self.x1, self.y1)
		#self.x3, self.y3 = self.x1+(self.width*0.5), self.y1+(self.height*0.5)
		if not self._vbo: self.verticies = ((self.x1, self.y1), (self.x2, self.y1), (self.x2, self.y2), (self.x1, self.y2))
		self.face_verticies = (np.array((self.x1, self.y1, 0,
						self.x1, self.y2, 0,
						self.x2, self.y2, 0,
						self.x2, self.y1, 0), dtype=np.float32))
		if self.vertex_buffer: self.vertex_buffer.set_array(self.face_verticies)
		else: self.vertex_buffer = vbo.VBO(self.face_verticies)
		if self.color_buffer: self.color_buffer.set_array(self.color_points)
		else: self.color_buffer: vbo.VBO(self.color_points)
	
	def setPointer(self, pointer):
		self.pointer = pointer
		
	def translate(self, x, y):
		self.x1 += x
		self.y1 += y
		self.calculate_geometry()
		if self.pointer:
			p1 = self.pointer.pointer*12
			p2 = self.pointer.pointer_end*12
			#self.pointer.array.pixel_array = self.face_verticies.tolist()
			#print(f"BEFORE: {self.pointer.array.pixel_array[p1:p2]}")
			self.pointer.optimizer.updateVertexData(self.pointer.index, self.face_verticies, p1, p2)
			#print(f"AFTER: {self.pointer.array.pixel_array[p1:p2]}")
		
		