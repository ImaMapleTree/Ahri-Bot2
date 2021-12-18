from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from _epy.epygraphics.model import ModelLoader
import numpy as np
import time
import math
import multiprocessing.dummy

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
		#self.vertex_buffer = vbo.VBO(np.array(self.verticies, dtype=np.float32), GL_STATIC_DRAW, GL_ARRAY_BUFFER)
	
	def _vbo_render(self, vao=0):
		glEnableClientState(GL_VERTEX_ARRAY)
		self.vertex_buffer.bind()
		glVertexPointer(3, GL_FLOAT, 0, self.vertex_buffer)
		glDrawArrays(GL_TRIANGLES, 0, 6)
		glDisableClientState(GL_VERTEX_ARRAY)
	
	def _normal_render(self):
		glBegin(GL_POLYGON)
		for vertex in self.verticies:
			glVertex2f(vertex[0], vertex[1])
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

from _epy.epygraphics.opengl_canvas import *

class Camera():
	def __init__(self, scene, x=0, y=0, z=0, focal_distance=1):
		self.scene = scene
		self.x, self.y, self.z = x, y, z
		self.focal_distance = focal_distance
		self.type = Camera
	
	def sync_scene(self):
		if self.type == Camera2D: print("oop"); return()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.x, self.y, self.z-self.focal_distance, 0, 1, 0)
	
	def zoom(self, distance):
		self.z += distance
		self.scene.apply_camera_movement(0, 0, distance)
		
	def update_view(self, width, height):
		if self.type == Camera2D:
			glOrtho(0, width, height, 0, -1, 1)
		elif self.type == Camera3D:
			gluPerspective(45, (width/height), 0.1, 50.0)
	
	@staticmethod
	def from_old_camera(cam):
		if isinstance(cam, Camera3D): return Camera2D(cam.scene, cam.x, cam.y, cam.z, cam.focal_distance)
		elif isinstance(cam, Camera2D): return Camera3D(cam.scene, cam.x, cam.y, focal_distance=cam.focal_distance)
		else: raise NotImplementedError
		
class Camera2D(Camera):
	def __init__(self, scene, *args, **kwargs):
		super(Camera2D, self).__init__(scene, *args, **kwargs)
		self.type = Camera2D

class Camera3D(Camera):
	def __init__(self, scene, x=0, y=0, z=0, pitch=0, yaw=0, roll=0):
		super(Camera3D, self).__init__(scene, x, y, z)
		self.fpX, self.fpY, self.fpZ = 0, 0, 0
		self.pitch = pitch
		self.yaw = yaw
		self.roll = roll
		self.type = Camera3D
		
	def translateForward(self, speed):
		radYaw = (self.yaw * math.pi) / 180
		x = math.sin(radYaw)
		z = -1 * math.cos(radYaw)
		self.translateX(x*speed)
		self.translateZ(z*speed)
		
	def translateLeft(self, speed):
		radYaw = (self.yaw * math.pi) / 180
		x = -1 * math.cos(radYaw)
		z = -1 * math.sin(radYaw)
		self.translateX(x*speed)
		self.translateZ(z*speed)
		
	def translateRight(self, speed):
		radYaw = (self.yaw * math.pi) / 180
		x =  math.cos(radYaw)
		z = math.sin(radYaw)
		self.translateX(x*speed)
		self.translateZ(z*speed)
	
	def translateBack(self, speed):
		radYaw = (self.yaw * math.pi) / 180
		x = -1 * math.sin(radYaw)
		z = math.cos(radYaw)
		self.translateX(x*speed)
		self.translateZ(z*speed)
		
	def get_focal_point(self):
		radYaw = (self.yaw * math.pi) / 180
		self.fpX = self.x + math.sin(radYaw)
		self.fpZ = self.z + (-1 * math.cos(radYaw))
		
	def translateX(self, x):
		self.x += x
		self.get_focal_point()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.fpX, self.fpY, self.fpZ, 0, 1, 0)
		
	def translateY(self, y):
		self.y += y
		self.get_focal_point()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.fpX, self.fpY, self.fpZ, 0, 1, 0)
		
	def translateZ(self, z):
		self.z += z
		self.get_focal_point()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.fpX, self.fpY, self.fpZ, 0, 1, 0)
		
	def rotateX(self, x):
		self.pitch += x
		self.fpY -= x
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.fpX, self.fpY, self.fpZ, 0, 1, 0)
		
	def rotateY(self, y):
		self.yaw += y
		self.get_focal_point()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.fpX, self.fpY, self.fpZ, 0, 1, 0)
		
	def rotateZ(self, z):
		self.roll = z1
		self.scene.apply_camera_movement(self.roll, 0.0, 0.0, 1.0)

class GLFrame(OpenGLFrame):
	FRAME_2D = "2D"
	FRAME_3D = "3D"
	FRAME_MODES = [FRAME_2D, FRAME_3D]
	
	def __init__(self, *args, **kwargs):
		mode = kwargs.get("mode")
		if mode: kwargs.pop("mode")
		super(OpenGLFrame, self).__init__(*args, **kwargs)
		self.objects = []
		self.rendering_changes = []
		self.need_register = []
		self.pixels = []
		self.pixel_array = []
		self.vaos = []
		self.mode = mode if mode else "2D"
		
		if self.mode == "3D": self.camera = Camera3D(self, z=5)
		elif self.mode == "2D": self.camera = Camera2D(self)
			
		self.start = time.time()
		self.nframes = 0
		self.fps = 0
		self._PF = False
		self.test = True
		self.bigVBO = vbo.VBO(np.array(self.pixel_array, dtype=np.float32))
		
	def initgl(self):
		glViewport(0, 0, self.width, self.height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		self.camera.update_view(self.width, self.height)
		glMatrixMode (GL_MODELVIEW)
		glLoadIdentity()
		self.camera.sync_scene()
		
		#gluLookAt(0, 0, 5, 0, 0, 4, 0, 1, 0)
		
	def redraw(self):
		glClear(GL_DEPTH_BUFFER_BIT)
		glClear(GL_COLOR_BUFFER_BIT);
		glClearDepthf(1.0)
		
		c = False
		pixels = list(self.pixels)
		for pixel in self.pixels:
			if pixel._vbo: self.pixelself.pixel_array.extend(pixel.face_verticies)
			else: self.objects.append(pixel)
			self.pixels.pop(0)
			c = True
		if c: self.bigVBO.set_array(np.array(self.pixel_array, dtype=np.float32))
		
		CURRENT_CHANGES = list(self.rendering_changes)
		for change in CURRENT_CHANGES:
			change[0](*change[1])
			self.rendering_changes.pop(0)
			
		need_register = list(self.need_register)
		for object in need_register:
			self.vaos.append(object.register())
			self.need_register.pop(0) #Prevents the list from dying if it's writting from another thread
		self.need_register = []
		
		for object in self.objects:
			object.render()
		
		glEnableClientState(GL_VERTEX_ARRAY)
		
		self.bigVBO.bind()
		glVertexPointer(3, GL_FLOAT, 0, self.bigVBO)
		glDrawArrays(GL_TRIANGLES, 0, self.bigVBO.size)
		
		glDisableClientState(GL_VERTEX_ARRAY)
		
		tm = time.time() - self.start
		self.nframes += 1
		tm = tm if tm else 0.00001
		self.fps = self.nframes / tm
		if self._PF: print("fps",self.fps, end="\r" )
			
	def mode(self, m):
		if m not in GLFrame.FRAME_MODES: raise NotImplementedError
		self.mode = m
		self.rendering_changes.append([Camera.from_old_camera, self.camera])
			
	def addObject(self, object):
		if isinstance(object, GLPixel): self.pixels.append(object)
		#if object._vbo: self.need_register.append(object)
		else: self.objects.append(object)
		
	def apply_camera_movement(self, *args):
		self.rendering_changes.append([glTranslatef, args])
	
	def apply_camera_rotation(self, *args):
		self.rendering_changes.append([glLoadIdentity, []])
		self.rendering_changes.append([gluLookAt, args])
		
		
		
