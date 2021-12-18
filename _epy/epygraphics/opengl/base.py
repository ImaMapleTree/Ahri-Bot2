from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
import ctypes

class GLObject():
	def __init__(self, VBO=False):
		self._vbo = VBO
		self.tags = {}
	
	def _vbo_render(self, vao=0):
		raise NotImplementedError
		
	def _normal_render(self):
		raise NotImplementedError
	
	def render(self, vao=0):
		if self._vbo: return self._vbo_render(vao)
		self._normal_render()
		
class GLObject2D(GLObject):
	def __init__(self, verticies, color=(1.0,1.0,1.0), VBO=False):
		super(GLObject2D, self).__init__(VBO)
		self.verticies = verticies
		self.color = color
	
	def _vbo_render(self, vao=0):
		glEnableClientState(GL_VERTEX_ARRAY)
		glEnableClientState(GL_COLOR_ARRAY)
		self.vertex_buffer.bind()
		glVertexPointer(3, GL_FLOAT, 0, self.vertex_buffer)
		self.color_buffer.bind()
		glColorPointer(3, GL_FLOAT, 0, self.color_buffer)
		glDrawArrays(GL_TRIANGLES, 0, 6)
		glDisableClientState(GL_VERTEX_ARRAY)
		glDisableClientState(GL_COLOR_ARRAY)
	
	def _normal_render(self):
		glBegin(GL_LINES)
		for vertex in self.verticies:
			glColor3f(self.color[0], self.color[1], self.color[2])
			glVertex3f(vertex[0], vertex[1], 0)
		glEnd()
			
	@property
	def VBO(self):
		return self._vbo	
		
class GLObject3D(GLObject):
	def __init__(self, verticies, edges, vx_array=(), color_array=(), color=(1.0,1.0,1.0), VBO=False):
		super(GLObject3D, self).__init__(VBO)
		self.verticies = verticies
		self.edges = edges
		self.color=color
		self.color_array = color_array
		self.rendered = False
		self.vx_array = vx_array
		self.vao = None
		
	def init_VBO(self):	
		if self._vbo:
			if self.rendered: return
			self.vertex_buffer = vbo.VBO(np.array(self.verticies, dtype=np.float32), GL_STATIC_DRAW, GL_ARRAY_BUFFER)
			self.color_buffer = vbo.VBO(np.array(self.color_array, dtype=np.float32), GL_STATIC_DRAW, GL_ARRAY_BUFFER)
			self.vx_array = vbo.VBO(np.array(
					[0, 1, 2, 3,
					 3, 2, 6, 7,
					 1, 0, 4, 5,
					 2, 1, 5, 6,
					 0, 3, 7, 4,
					 7, 6, 5, 4 ], dtype=np.float32), GL_STATIC_DRAW, GL_ELEMENT_ARRAY_BUFFER)
			self.rendered = True
			
	def register(self):
		glEnableClientState(GL_VERTEX_ARRAY)
		glEnableClientState(GL_COLOR_ARRAY)
		
		vao = glGenVertexArrays(1)
		glBindVertexArray(vao)
		
		self.init_VBO()
		
		self.vertex_buffer.bind()
		glVertexPointer(4, GL_FLOAT, 0, None)
		self.vertex_buffer.unbind()
		
		self.color_buffer.bind()
		glColorPointer(4, GL_FLOAT, 0, self.vertex_buffer)
		self.color_buffer.unbind()
		
		self.vx_array.bind()
		glIndexPointer(GL_FLOAT, 0, self.vertex_buffer)
		self.vx_array.unbind()
		
		glDisableClientState(GL_VERTEX_ARRAY)
		glDisableClientState(GL_COLOR_ARRAY)
		
		glBindVertexArray(0)
		return vao
		
		
	def _vbo_render(self, vao):
		self.vao = vao
		self.init_VBO()
		glBindVertexArray(vao)
		
		self.vertex_buffer.bind()
		glVertexPointer(3, GL_FLOAT, 12, self.vertex_buffer)
		glNormalPointer(GL_FLOAT, 12, self.vertex_buffer)
		self.vertex_buffer.unbind()
		
		self.color_buffer.bind()
		glColorPointer(3, GL_FLOAT, 0, self.vertex_buffer)
		self.color_buffer.unbind()
		
		self.vx_array.bind()
		glIndexPointer(GL_FLOAT, 0, self.vertex_buffer)
		self.vx_array.unbind()
		
		glDisableClientState(GL_VERTEX_ARRAY)
		glDisableClientState(GL_COLOR_ARRAY)
		
		glBindVertexArray(0)
		
		
	def _normal_render(self):
		glColor3f(self.color[0], self.color[1], self.color[2])
		glBegin(GL_LINES)
		for edge in self.edges:
			for vertex in edge:
				glVertex3fv(self.verticies[vertex])
		glEnd()