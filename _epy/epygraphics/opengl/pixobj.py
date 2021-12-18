from multiprocessing.pool import ThreadPool
import threading
import time
import random
from queue import Queue
from _epy.epygraphics.opengl.engine2 import *
from _epy.epygraphics.opengl.util import *
import numpy as np

class Concrete(PixelObject):
	def __init__(self, *args, **kwargs):
		color_val = random.uniform(63.75, 127.5)
		color = ((color_val, color_val, color_val))
		super(Concrete, self).__init__(*args, **kwargs, color=color)
		self.type = "Concrete"
		self.active = False
		self.static = True
		self.density = 100
		
	def decay_function(self):
		return True
		
class Sand(PixelObject):
	def __init__(self, *args, **kwargs):
		color = (random.uniform(204, 234.6), 178.5, 122.5)
		super(Sand, self).__init__(*args, **kwargs, type="Sand", color=color, x_movement=MovementList([0, -1, 1]), y_movement=MovementList([1]))
		self.density = 2

class Water(PixelObject):
	def __init__(self, *args, **kwargs):
		val1 = random.uniform(216.75, 239.7)
		color = (178.5, val1, 244.8)
		if val1 > 228.225: movement = [0, -1, 1, -1, 1]
		else: movement = [0, 1, -1, 1, -1]
		
		super(Water, self).__init__(*args, **kwargs, type="Water", color=color, x_movement=MovementList(movement), y_movement=MovementList([1, 1, 1, 0, 0]))
		self.density = 1
		
	def behavior_function(self):
		i = random.randint(0, 100)
		if i == 100:
			self.x_movement = MovementList([0, 1, -1, 1, -1])
		elif i == 99:
			self.x_movement = MovementList([0, -1, 1, -1, 1])