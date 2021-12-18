from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
from OpenGL.arrays import vbo
from _epy.epygraphics.opengl.util import *
from _epy.epygraphics.opengl.optimizers import *
from _epy.epygraphics.opengl.camera import *
from _epy.epygraphics.opengl.base import *
from _epy.epygraphics.opengl.canvas import *
from _epy.epygraphics.opengl.window import *
from _epy.epygraphics.opengl.shaders import *
from _epy.epygraphics.clock import *
import numpy as np
import time
import math
import multiprocessing.dummy
from pyrr import matrix44, Vector3
import random

class GLTKFrame(GLTKWindow):
	FRAME_2D = "2D"
	FRAME_3D = "3D"
	FRAME_MODES = [FRAME_2D, FRAME_3D]
	
	def __init__(self, *args, **kwargs):
		mode = kwargs.get("mode")
		if mode: kwargs.pop("mode")
		super(GLTKFrame, self).__init__(*args, **kwargs)
		self.mode = mode if mode else "2D"
		
		if self.mode == "3D": self.camera = Camera3D(self, z=5)
		elif self.mode == "2D": self.camera = Camera2D(self)
			
		self.rendering_changes = []
		self.texts = []
		self.objects = []
		self.need_register = []
		self.bound_types = {}
		
		self.vao_index = 0
		self.vao = 0
		self.total_objects_created = 0
		self.max_vao_size = 12000
		self.diagnosis = False
		self.lag = {"GPU-Adding": [], "GPU-Rendering": []}
		
		self.optimizer = VBO_Optimizer(self.max_vao_size)
		self.fully_initialized = False
		
	def tkMakeCurrent(self):
		if self.master.window: super().tkMakeCurrent()
			
	def tkSwapBuffers(self):
		if self.master.window: super().tkSwapBuffers()
		
	def initgl(self):
		glClearColor(*rgb_decimal(153, 147, 130), 1.0)
		glViewport(0, 0, self.width, self.height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		self.camera.update_view(self.width, self.height)
		glMatrixMode (GL_MODELVIEW)
		glLoadIdentity()
		self.camera.sync_scene()
		
		glEnable(GL_PROGRAM_POINT_SIZE);
		vs, fs = load_shader()
		self.shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vs, GL_VERTEX_SHADER), OpenGL.GL.shaders.compileShader(fs, GL_FRAGMENT_SHADER))
		vs, fs = load_shader("text")
		self.text_shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vs, GL_VERTEX_SHADER), OpenGL.GL.shaders.compileShader(fs, GL_FRAGMENT_SHADER))
		
		
		glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
	
		self.text_vao = glGenVertexArrays(1)
		self.text_vbo = glGenBuffers(1)
		face = freetype.Face(r'C:\Windows\Fonts\arial.ttf')
		face.set_char_size( 48*64 )
		load_ascii(self.text_vao, self.text_vbo, face)
	
		glUseProgram(self.text_shader)
		shader_projection = glGetUniformLocation(self.text_shader, "projection")
		projection = glm.ortho(0, self.width, self.height, 0)
		glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))
	
	
		glUseProgram(self.shader)
		
	
	def redraw(self):
		glClear(GL_DEPTH_BUFFER_BIT)
		glClear(GL_COLOR_BUFFER_BIT);
		glClearDepthf(1.0)
		
		time1 = time.time()
		
		CURRENT_CHANGES = list(self.rendering_changes)
		for change in CURRENT_CHANGES:
			change[0](*change[1])
			self.rendering_changes.pop(0)
		
		need_register = list(self.need_register)
		[self.bind_object(waiting) for waiting in need_register]
		if self.diagnosis: self.lag["GPU-Adding"].append(time.time()-time1)
		
		if self.objects:
			for object in self.objects:
				object.render()
			
		st = time.time()
		texts = list(self.texts)
		if self.texts:
			for text in texts:
				text.render()
			if not text.static: self.texts.pop(self.texts.index(text))
			
		self.optimizer.draw_all()
		if self.diagnosis: self.lag["GPU-Rendering"].append(time.time()-st)
			
	def recycle(self, object):
		if not object.main_pointer: return
		name = object.__class__.__name__
		if not name in self.bound_types.keys(): return
		self.bound_types[name]["recycled"].append([object.main_pointer, object.instance_pointer])
			
	def bind_object(self, object):
		self.total_objects_created += 1
		if not object._vbo: self.objects.append(object)
		name = object.__class__.__name__
		if not name in self.bound_types.keys(): self.bound_types[name] = {"index": 0, "amount": 0, "ia": 0, "vaos": [], "recycled": []}; self.bound_types[name]["vaos"].append(self.generate_vao_type(object))
		ref = self.bound_types[name]
		if ref["ia"] >= self.max_vao_size: ref["vaos"].append(self.generate_vao_type(object)); ref["index"] += 1; ref["ia"] = 0
		if ref["recycled"]:
			repair = ref["recycled"][0]
			main_index = repair[0]
			instance_index = repair[1]
			self.optimizer.updateOffsetInstance(main_index, instance_index, object.coords)
			self.optimizer.updateColorInstance(main_index, instance_index, object.color)
			ref["recycled"].pop(0)
		else:
			vaos = ref["vaos"]
			main_index = vaos[ref["index"]]
			instance_index = self.optimizer.addOffsetInstance(main_index, object.coords)
			self.optimizer.addColorInstance(main_index, object.color)
			object.setPointers(main_index, instance_index)
			ref["amount"] += 1; ref["ia"] += 1
		object.setPointers(main_index, instance_index)
		self.need_register.pop(0)
		
	def generate_vao_type(self, object):
		self.vao_index += 1
		print("Created vao", self.total_objects_created)
		return self.optimizer.addType(np.array((0, 0, 0, 1, 1, 1, 1, 0), dtype=np.float32)) #will eventually be stored in object's default code, so that if the object is generated the vao will know what to put in place
		
			
	def printout(self, text, x, y, *args, **kwargs):
		self.texts.append(GLText(self, x, y, text, *args, **kwargs))
		
	def clearprint(self):
		self.texts = []
			
	def mode(self, m):
		if m not in GLFrame.FRAME_MODES: raise NotImplementedError
		self.mode = m
		self.rendering_changes.append([Camera.from_old_camera, self.camera])
			
	def addObject(self, object):
		if isinstance(object, GLPixel): self.need_register.append(object)
		else: self.objects.append(object)
		
	def apply_camera_movement(self, *args):
		self.rendering_changes.append([glTranslatef, args])
	
	def apply_camera_rotation(self, *args):
		self.rendering_changes.append([glLoadIdentity, []])
		self.rendering_changes.append([gluLookAt, args])
		
	def gpu_function(self, *args):
		self.rendering_changes.append([*args])

class GLFrame(GLWindowThread):
	FRAME_2D = "2D"
	FRAME_3D = "3D"
	FRAME_MODES = [FRAME_2D, FRAME_3D]
	
	def __init__(self, *args, **kwargs):
		mode = kwargs.get("mode")
		if mode: kwargs.pop("mode")
		super(GLFrame, self).__init__(*args, **kwargs)
		self.mode = mode if mode else "2D"
		
		if self.mode == "3D": self.camera = Camera3D(self, z=5)
		elif self.mode == "2D": self.camera = Camera2D(self)
			
		self.rendering_changes = []
		self.texts = []
		self.objects = []
		self.need_register = []
		self.bound_types = {}
		
		self.vao_index = 0
		self.vao = 0
		self.total_objects_created = 0
		self.max_vao_size = 12000
		self.diagnosis = False
		self.lag = {"GPU-Adding": [], "GPU-Rendering": []}
		
		self.optimizer = VBO_Optimizer(self.max_vao_size)
		self.fully_initialized = False
		
	def tkMakeCurrent(self):
		if self.master.window: super().tkMakeCurrent()
			
	def tkSwapBuffers(self):
		if self.master.window: super().tkSwapBuffers()
		
	def initgl(self):
		glClearColor(*rgb_decimal(153, 147, 130), 1.0)
		glViewport(0, 0, self.width, self.height)
		glMatrixMode(GL_PROJECTION)
		glLoadIdentity()
		self.camera.update_view(self.width, self.height)
		glMatrixMode (GL_MODELVIEW)
		glLoadIdentity()
		self.camera.sync_scene()
		
		glEnable(GL_PROGRAM_POINT_SIZE);
		vs, fs = load_shader()
		self.shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vs, GL_VERTEX_SHADER), OpenGL.GL.shaders.compileShader(fs, GL_FRAGMENT_SHADER))
		vs, fs = load_shader("text")
		self.text_shader = OpenGL.GL.shaders.compileProgram(OpenGL.GL.shaders.compileShader(vs, GL_VERTEX_SHADER), OpenGL.GL.shaders.compileShader(fs, GL_FRAGMENT_SHADER))
		
		
		glPixelStorei(GL_UNPACK_ALIGNMENT, 1)
	
		self.text_vao = glGenVertexArrays(1)
		self.text_vbo = glGenBuffers(1)
		face = freetype.Face(r'C:\Windows\Fonts\arial.ttf')
		face.set_char_size( 48*64 )
		load_ascii(self.text_vao, self.text_vbo, face)
	
		glUseProgram(self.text_shader)
		shader_projection = glGetUniformLocation(self.text_shader, "projection")
		projection = glm.ortho(0, self.width, self.height, 0)
		glUniformMatrix4fv(shader_projection, 1, GL_FALSE, glm.value_ptr(projection))
	
	
		glUseProgram(self.shader)
		
	
	def redraw(self):
		glClear(GL_DEPTH_BUFFER_BIT)
		glClear(GL_COLOR_BUFFER_BIT);
		glClearDepthf(1.0)
		
		time1 = time.time()
		
		CURRENT_CHANGES = list(self.rendering_changes)
		for change in CURRENT_CHANGES:
			change[0](*change[1])
			self.rendering_changes.pop(0)
		
		need_register = list(self.need_register)
		[self.bind_object(waiting) for waiting in need_register]
		if self.diagnosis: self.lag["GPU-Adding"].append(time.time()-time1)
		
		if self.objects:
			for object in self.objects:
				object.render()
			
		st = time.time()
		texts = list(self.texts)
		if self.texts:
			for text in texts:
				text.render()
			if not text.static: self.texts.pop(self.texts.index(text))
			
		self.optimizer.draw_all()
		if self.diagnosis: self.lag["GPU-Rendering"].append(time.time()-st)
			
	def recycle(self, object):
		if not object.main_pointer: return
		name = object.__class__.__name__
		if not name in self.bound_types.keys(): return
		self.bound_types[name]["recycled"].append([object.main_pointer, object.instance_pointer])
			
	def bind_object(self, object):
		self.total_objects_created += 1
		if not object._vbo: self.objects.append(object)
		name = object.__class__.__name__
		if not name in self.bound_types.keys(): self.bound_types[name] = {"index": 0, "amount": 0, "ia": 0, "vaos": [], "recycled": []}; self.bound_types[name]["vaos"].append(self.generate_vao_type(object))
		ref = self.bound_types[name]
		if ref["ia"] >= self.max_vao_size: ref["vaos"].append(self.generate_vao_type(object)); ref["index"] += 1; ref["ia"] = 0
		if ref["recycled"]:
			repair = ref["recycled"][0]
			main_index = repair[0]
			instance_index = repair[1]
			self.optimizer.updateOffsetInstance(main_index, instance_index, object.coords)
			self.optimizer.updateColorInstance(main_index, instance_index, object.color)
			ref["recycled"].pop(0)
		else:
			vaos = ref["vaos"]
			main_index = vaos[ref["index"]]
			instance_index = self.optimizer.addOffsetInstance(main_index, object.coords)
			self.optimizer.addColorInstance(main_index, object.color)
			object.setPointers(main_index, instance_index)
			ref["amount"] += 1; ref["ia"] += 1
		object.setPointers(main_index, instance_index)
		self.need_register.pop(0)
		
	def generate_vao_type(self, object):
		self.vao_index += 1
		print("Created vao", self.total_objects_created)
		return self.optimizer.addType(np.array((0, 0, 0, 1, 1, 1, 1, 0), dtype=np.float32)) #will eventually be stored in object's default code, so that if the object is generated the vao will know what to put in place
		
			
	def printout(self, text, x, y, *args, **kwargs):
		self.texts.append(GLText(self, x, y, text, *args, **kwargs))
		
	def clearprint(self):
		self.texts = []
			
	def mode(self, m):
		if m not in GLFrame.FRAME_MODES: raise NotImplementedError
		self.mode = m
		self.rendering_changes.append([Camera.from_old_camera, self.camera])
			
	def addObject(self, object):
		if isinstance(object, GLPixel): self.need_register.append(object)
		else: self.objects.append(object)
		
	def apply_camera_movement(self, *args):
		self.rendering_changes.append([glTranslatef, args])
	
	def apply_camera_rotation(self, *args):
		self.rendering_changes.append([glLoadIdentity, []])
		self.rendering_changes.append([gluLookAt, args])
		
	def gpu_function(self, *args):
		self.rendering_changes.append([*args])