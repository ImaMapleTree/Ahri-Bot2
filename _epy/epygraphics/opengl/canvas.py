from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import glm
from _epy.epygraphics.opengl.base import *
from _epy.epygraphics.opengl.util import *
from _epy.epygraphics.opengl.util import _get_rendering_buffer
from _epy.epygraphics.opengl.shaders import *
from _epy.epygraphics.opengl.window import *
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
			
class GLText():
	def __init__(self, gpu, x, y, text, color=(255, 255, 255), scale=1, static=False):
		self.characters = getCharacters()
		if not self.characters: raise NotImplementedError
		self.gpu = gpu
		self.vao = gpu.text_vao
		self.vbo = gpu.text_vbo
		self.x, self.y = x, y
		self.text = text
		self.text = self.text.replace("\n", "$")
		self.color = color
		self.scale = scale
		self.static = static
		self.funky = ["y", "p", "g"]
		
	def draw(self, c):
		if c == "$": self.cx = self.x; self.cy += 45*self.scale; return
		self.ch = self.characters[c]
		w, h = self.ch.textureSize
		w = w*self.scale
		h = h*self.scale
		if c in self.funky:
			vertices = _get_rendering_buffer(self.cx,self.cy+(11*self.scale),w,h)
		else: vertices = _get_rendering_buffer(self.cx,self.cy,w,h)

		#render glyph texture over quad
		glBindTexture(GL_TEXTURE_2D, self.ch.texture)
		#update content of VBO memory
		glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
		glBufferSubData(GL_ARRAY_BUFFER, 0, vertices.nbytes, vertices)

		glBindBuffer(GL_ARRAY_BUFFER, 0)
		#render quad
		glDrawArrays(GL_TRIANGLES, 0, 6)
		#now advance cursors for next glyph (note that advance is number of 1/64 pixels)
		self.cx += (self.ch.advance>>6)*self.scale
	
	def render(self):
		glUseProgram(self.gpu.text_shader)
		#projection = glOrtho(0, 640, 640, 0, -1, 1)
		#shader_projection = glGetUniformLocation(self.gpu.text_shader, "projection")
		#glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))
		face = freetype.Face(r'C:\Windows\Fonts\arial.ttf')
		face.set_char_size(48*64)
		glUniform3f(glGetUniformLocation(self.gpu.text_shader, "textColor"),
					self.color[0]/255,self.color[1]/255,self.color[2]/255)
				   
		glActiveTexture(GL_TEXTURE0)
		
		glEnable(GL_BLEND)
		glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

		glBindVertexArray(self.vao)
		self.cx, self.cy = self.x, self.y
		
		[self.draw(c) for c in self.text]
			

		glBindVertexArray(0)
		glBindTexture(GL_TEXTURE_2D, 0)
		glUseProgram(self.gpu.shader)
		
class GLPixel():
	def __init__(self, x, y, width=1, height=1, color=(1.0, 1.0, 1.0), main_pointer=None, instance_pointer=None):
		self.x, self.y = x, y
		self.x2, self.y2 = x+width, y+height
		self.coords = (self.x, self.y)
		self._color = color
		self.main_pointer = main_pointer
		self.instance_pointer = instance_pointer
		self.gl_instance = GLInstance()
		self.updater = self.gl_instance.optimizer
		
	def setPointers(self, mp, ip):
		self.main_pointer = mp
		self.instance_pointer = ip
		
	def project(self, x, y):
		return (self.x + x, self.y + y)
		
	def relmove(self, x, y):
		self.x += x; self.y += y
		self.coords = (self.x, self.y)
		if self.main_pointer: self.updater.updateOffsetInstance(self.main_pointer, self.instance_pointer, self.coords)
			
	def absmove(self, x, y):
		self.x = x; self.y = y;
		self.coords = (x, y)
		if self.main_pointer: self.updater.updateOffsetInstance(self.main_pointer, self.instance_pointer, self.coords)
		
	@property
	def color(self):
		return self._color
		
	@color.setter
	def color(self, rgb):
		try:
			if max(rgb) > 1: self._color = (rgb[0]/255, rgb[1]/255, rgb[2]/255)
			self._color = rgb
		except: raise AttributeError
		if self.main_pointer: self.updater.updateColorInstance(self.main_pointer, self.instance_pointer, self._color)

'''
class GLPixel(GLObject2D):
	def __init__(self, x, y, width=1, height=1, color=(1.0, 1.0, 1.0), *args, **kwargs):
		self.x1, self.y1 = x, y
		self.x2, self.y2 = self.x1+width, self.y1+height
		self.width = width
		self.height = height
		self.color = color
		self.vertex_buffer = None
		self.color_buffer = None
		self.verticies = ((self.x1, self.y1), (self.x2, self.y1), (self.x2, self.y2), (self.x1, self.y2))
		super(GLPixel, self).__init__(self.verticies, *args, **kwargs)
		self.calculate_geometry()
		self.main = None
		self.instance = None
	
	def calculate_geometry(self):
		self.x2, self.y2 = self.x1+self.width, self.y1+self.height
		self.coords = (self.x1, self.y1)
	
	def setPointer(self, main, instance=None):
		self.main = main
		self.instance = instance
		
	def change_color(self, color):
		self.color = color
		if self.main:
			self.pointer.optimizer.updateColorInstance(self.pointer.main, self.pointer.instance, self.color)
		
	def project(self, x, y):
		return (self.coords[0] + x, self.coords[1] + y)
		
	def move_to(self, x, y):
		self.x1 = x
		self.y1 = y
		self.calculate_geometry()
		if self.main:
			GLInstance().optimizerupdateOffsetInstance(self.main, self.instance, self.coords)
		
	def translate(self, x, y):
		if x: 
			self.x1 += x
			if self.pointer:
				self.pointer.optimizer.updateXOffsetInstance(self.pointer.main, self.pointer.instance, self.x1)
		if y:
			self.y1 += y
			if self.pointer:
				self.pointer.optimizer.updateYOffsetInstance(self.pointer.main, self.pointer.instance, self.y1)
				
		self.calculate_geometry()
'''