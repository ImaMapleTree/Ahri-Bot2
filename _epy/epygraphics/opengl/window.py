from pyopengltk import OpenGLFrame
from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import os
import threading

global _GLWINDOW
_GLWINDOW = None
def GLInstance():
	global _GLWINDOW
	return _GLWINDOW

class INTERNAL_INIT(type):
	def __call__(cls, *args, **kwargs):
		obj = type.__call__(cls, *args, **kwargs)
		obj._INTERNAL_INIT_()
		return obj
		
class GLTKWindow(OpenGLFrame):
	def __init__(self, *args, **kwargs):
		super(GLTKWindow, self).__init__(*args, **kwargs)
		global _GLWINDOW
		_GLWINDOW = self

class GLWindow(object, metaclass=INTERNAL_INIT):
	def __init__(self, width=0, height=0, initgl=None, redraw=None, click_function=None, drag_function=None, keyboard_function=None, window_x=0, window_y=0, glut_color=GLUT_RGBA, name=f"OpenGL Window - {os.getpid()}"):
		self.width = width
		self.height = height
		self.window_x = window_x #X Pos of window
		self.window_y = window_y #Y Pos of window
		self.init_wrapper = initgl if initgl else self.initgl #Wrapper for init
		self.render_wrapper = redraw if redraw else self.redraw #Wrapper for rendering
		self.click_wrapper = click_function if click_function else None
		self.keyboard_wrapper = keyboard_function if keyboard_function else None
		self.drag_wrapper = drag_function if drag_function else None
		
		
		self.glut_color = glut_color
		self.window_name = name
		self.window = True
		
		global _GLWINDOW
		_GLWINDOW = self
		
		#self.second_init = False
		
	def _INTERNAL_INIT_(self):
		self._window_()
		self.init_wrapper()
		
	def _window_(self):
		glutInit()
		glutInitDisplayMode(self.glut_color)
		glutInitWindowSize(self.width, self.height)
		glutInitWindowPosition(self.window_x, self.window_y)
		self.window = glutCreateWindow(self.window_name)
			
	def _render_(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		#glViewport(0, 0, self.width, self.height)
		#glLoadIdentity()
		self.render_wrapper()
		glutSwapBuffers()
			
	def initgl(self):
		pass
		
	def redraw(self):
		pass
		
	def _start(self):	
		glutDisplayFunc(self._render_)
		glutIdleFunc(self._render_)
		if self.click_wrapper: glutMouseFunc(self.click_wrapper)
		if self.drag_wrapper: glutMotionFunc(self.drag_wrapper)
		if self.keyboard_wrapper: glutKeyboardFunc(self.keyboard_wrapper); glutSpecialFunc(self.keyboard_wrapper)
		glutMainLoop()
		
	def start(self):
		self._start()
		
	def __bool__(self):
		return bool(self.window)
		

class GLWindowThread(threading.Thread, object, metaclass=INTERNAL_INIT):
	def __init__(self, width=0, height=0, initgl=None, redraw=None, click_function=None, drag_function=None, keyboard_function=None, window_x=0, window_y=0, glut_color=GLUT_RGBA, name=f"OpenGL Window - {os.getpid()}", *args, **kwargs):
		super(GLWindowThread, self).__init__(*args, **kwargs)
		self.width = width
		self.height = height
		self.window_x = window_x #X Pos of window
		self.window_y = window_y #Y Pos of window
		self.init_wrapper = initgl if initgl else self.initgl #Wrapper for init
		self.render_wrapper = redraw if redraw else self.redraw #Wrapper for rendering
		self.click_wrapper = click_function if click_function else None
		self.keyboard_wrapper = keyboard_function if keyboard_function else None
		self.drag_wrapper = drag_function if drag_function else None
		
		
		self.glut_color = glut_color
		self.window_name = name
		self.window = True
		
		global _GLWINDOW
		_GLWINDOW = self
		print("threading")
		print(_GLWINDOW)
		
		#self.second_init = False
		
	def _INTERNAL_INIT_(self):
		self._window_()
		self.init_wrapper()
		
	def _window_(self):
		glutInit()
		glutInitDisplayMode(self.glut_color)
		glutInitWindowSize(self.width, self.height)
		glutInitWindowPosition(self.window_x, self.window_y)
		self.window = glutCreateWindow(self.window_name)
			
	def _render_(self):
		glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
		#glViewport(0, 0, self.width, self.height)
		#glLoadIdentity()
		self.render_wrapper()
		glutSwapBuffers()
			
	def initgl(self):
		pass
		
	def redraw(self):
		pass
		
	def _start(self):	
		glutDisplayFunc(self._render_)
		glutIdleFunc(self._render_)
		if self.click_wrapper: glutMouseFunc(self.click_wrapper)
		if self.drag_wrapper: glutMotionFunc(self.drag_wrapper)
		if self.keyboard_wrapper: glutKeyboardFunc(self.keyboard_wrapper); glutSpecialFunc(self.keyboard_wrapper)
		glutMainLoop()
		
	def start(self):
		self._start()
		
	def __bool__(self):
		return bool(self.window)