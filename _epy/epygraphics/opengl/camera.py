from OpenGL.GL import *
from OpenGL.GLUT import *
from OpenGL.GLU import *
import math

class Camera():
	def __init__(self, scene, x=0, y=0, z=0, focal_distance=1):
		self.scene = scene
		self.x, self.y, self.z = x, y, z
		self.focal_distance = focal_distance
		self.type = Camera
		self.zoom = 1
	
	def sync_scene(self):
		if self.type == Camera2D: return()
		self.scene.apply_camera_rotation(self.x, self.y, self.z, self.x, self.y, self.z-self.focal_distance, 0, 1, 0)
	
	def zoom(self, distance):
		self.z += distance
		self.scene.apply_camera_movement(0, 0, distance)
		
	def update_view(self, width, height):
		self.scene.gpu_function(glLoadIdentity, ())
		if self.type == Camera2D:
			self.scene.gpu_function(glOrtho, (0, width, height, 0, -1, 1))
		elif self.type == Camera3D:
			self.scene.gpu_function(gluPerspective, (45, (width/height), 0.1, 50))
	
	@staticmethod
	def from_old_camera(cam):
		if isinstance(cam, Camera3D): return Camera2D(cam.scene, cam.x, cam.y, cam.z, cam.focal_distance)
		elif isinstance(cam, Camera2D): return Camera3D(cam.scene, cam.x, cam.y, focal_distance=cam.focal_distance)
		else: raise NotImplementedError
		
class Camera2D(Camera):
	def __init__(self, scene, *args, **kwargs):
		super(Camera2D, self).__init__(scene, *args, **kwargs)
		self.type = Camera2D
		
	def scale(self, integer):
		self.zoom = integer
		adj_width = self.scene.width / integer
		adj_height = self.scene.height / integer
		self.update_view(adj_width, adj_height)

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