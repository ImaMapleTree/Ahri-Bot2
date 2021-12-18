from multiprocessing.pool import ThreadPool
import threading
import time
import random
from queue import Queue
from _epy.epygraphics.clock import *
from _epy.epygraphics.opengl.canvas import *
import numpy as np
from numba import jit

class Settings():
	def __init__(self, speed):
		self.speed = speed

class EmptyObject():
	def __init__(self, coords, engine):
		self.type = "Empty"
		self.behavior = "Fluid"
		self.coords = coords
		self.engine = engine
		self.global_states = engine.global_info
		self.flamability = 0
		self.density = 100
		self.movement = True
		
	def __bool__(self):
		return False
		
	def update_function(self):
		return self

class PhysicsObject(GLPixel):
	def __init__(self, engine, *args, **kwargs):
		active = True
		if kwargs.get("active"): active = kwargs.pop("active")
		super(PhysicsObject, self).__init__(*args, **kwargs)
		
		self.engine = engine
		self.gravity = engine.gravity
		self.global_states = engine.global_info
		self.ground = engine.ground
		
		self.active = active
		self.movement = True
		self.flamability = 0
		self.ticks = 1
		self.max_ticks = None
		self.decays = False
		self.finalized = False
		self.ready = True
		self.timing = time.time()
		self.time_step = 0
		self.z = 0
		self._vbo = True

	def force(self, *m):
		return self

	def activate(self, target):
		target.movement = True
		
	def update_function(self, ticks=0):
		pass
		
	def decay_function(self):
		self.tick()
		return False
		
	def tick(self):
		self.time_step = int((time.time() - self.timing)*200)
		self.ticks += 1 #+ self.time_step
		self.timing = time.time()
		
	def move_pixel(self, *m):
		old = self.coords
		try: self.global_states.pop(old)
		except: pass
		self.relmove(*m)
		self.global_states[self.coords] = self
		return self
		
	def jump_pixel(self, coords):
		old = self.coords
		try: self.global_states.pop(old)
		except: pass
		self.absmove(*coords)
		self.global_states[coords] = self
		return self
	
	def remove(self, replacement=None):
		if replacement:
			self.__class__ = replacement.__class__
			self.__init__(self.engine, *self.coords)
			self.color = replacement.color
			self.global_states[self.coords] = self
		else:
			self.global_states[self.coords] = None
			self.color = (0.0, 0.0, 0.0)
			self.absmove(-1, -1)
			self.update_function = PhysicsObject.update_function
			self.engine.gpu.recycle(self)
		for thread in self.engine.threads:
			pixels = thread.pixels
			if self in pixels:
				index = pixels.index(self)
				if not replacement: pixels.pop(index)
				else: 
					pixels[index]  = self
					return self
					
	def find_movement(self, location):
		if not self.ready: return
		self.ready = False
		if not location: return self.jump_pixel(location.coords)
		return self.force(location.x - self.x, 0)
		
	def get_movement_attributes(self):
		return [self.update_function, self.decay_function, self.density, self.decays, self.max_ticks, self.movement]
		
	def set_movement_attributes(self, attribute):
		self.consumed_function = attribute[0]
		if attribute[3]:
			self.decay_function = attribute[1]
		self.density = attribute[2]
		if attribute[4]: self.max_ticks = attribute[4]
		self.movement = attribute[5]
		
	def get_state(self, coords):
		p = self.global_states.get(coords)
		if not p: return EmptyObject(coords, self.engine)
		return p
		
	def inrange(self, cs, vector=(1, 0)):
		st = time.time()
		dx = vector[0]
		dy = vector[1]
		return [self.get_state(c) for c in cs]
		
	def get_neighbors(self, cull=True):
		c = [-1, 1]
		neighbors = [self.get_state(self.project(x, 0)) for x in c]
		neighbors += [self.get_state(self.project(0, y)) for y in c]
		if cull: return [neighbor for neighbor in neighbors if neighbor]
		return neighbors
		
	def setType(self, type):
		new = type(self.engine, *self.coords)
		return self.remove(new)

class PhysicsEngine():
	def __init__(self, window, gpu, pixels=[]):
		self.ground = 150
		self.gravity = 1
		
		self.settings = Settings(speed=0)
		self.decaying = {}
		
		self.pixels = pixels
		self.window = window
		self.gpu = gpu
		self.threads = []
		self.t_amount = 16	
		
		self.y_spaces = 400
		self.p = 0
		
		self.pixel_index = 0
		
		self.to_move = []
		self.running_diagnosis = False
		
		self.energy = True
		
		self.global_info = {}
		self.object_amount = len(self.pixels)
		
	
		n = int(len(self.pixels)/self.t_amount)
		
		for pixel in self.pixels:
			self.global_info[pixel.coords] = pixel
		
		for i in range(self.t_amount):
			t = PhysicsThread(self.window, self.gpu, self.settings, [], self.to_move, self.global_info, daemon=True)
			t.start()
			self.threads.append(t)
			
	def cheat_toggle(self):
		self.energy = not self.energy
			
	def change_speed(self, dS):
		self.settings.speed = self.settings.speed + dS if self.settings.speed + dS > 0 else 0
		print(f"Delay changed to: {self.settings.speed} seconds.")
		
	def create_pixel(self, type, coords):
		st = time.time()
		if self.global_info.get(coords): return
		alive = type(self, coords[0], coords[1])
		self.gpu.addObject(alive)
		self.global_info[alive.coords] = alive
		self.threads[self.pixel_index].pixels.append(alive)
		self.pixel_index = self.pixel_index + 1 if self.pixel_index + 1 < self.t_amount else 0
		self.p += 1
		return alive
		
	def merge(self, obj1, obj2):
		obj3 = {}
		for key in obj1.keys():
			if key not in obj3.keys(): obj3[key] = obj1[key]
			else: obj3[key] += obj1[key]
		for key in obj2.keys():
			if key not in obj3.keys(): obj3[key] = obj2[key]
			else: obj3[key] += obj2[key]
		return obj3
		
	def diagnosis(self):
		if self.running_diagnosis:
			all_pixels = {}
			DATA = {}
			filtered_data = {"Total": {"entry_name": "Total", "entries": 0, "total": [], "average": 0}}
			filtered_data_keys = []
			showed_thread = False
			for t in self.threads:
				DATA = self.merge(DATA, t.lag_pixels)
				t.diagnosis = False
				
			DATA = self.merge(DATA, self.gpu.lag)
			self.gpu.diagnosis = False
			running_time = time.time()-self.running_diagnosis
			print(f"Diagnosis finished after: {running_time} seconds.")
			print(self.p)
			print("----------------------------------------------------------------------------")
			
			for key in DATA.keys():
				total = DATA[key]
				total_lag = sum(total)
				entries = len(DATA[key])
				average = total_lag/entries
				filtered_data[total_lag] = {"entry_name": key,  "entries": entries,  "total": total, "average": average}
				filtered_data_keys.append(total_lag)
				
				try: int(key); this_key = "Threads"
				except:
					if key == "GPU-Adding" or key == "GPU-Rendering": this_key = "GPU"
					else: this_key = "Pixels"
				if not filtered_data.get(this_key): filtered_data[this_key] = {"entry_name": this_key, "entries": 0, "total": [], "average": 0}
				for cheatkey in [this_key, "Total"]:
					if this_key == "Threads" and cheatkey == "Total" and showed_thread == True: continue
					#print(this_key, cheatkey, showed_thread, key)
					nested = filtered_data[cheatkey]
					nested["entries"] += entries
					nested["total"].extend(total)
					nested["average"] = sum(nested["total"])/nested["entries"]
					if this_key == "Threads" and cheatkey == "Total": showed_thread = True
			
			showed_thread = False
			filtered_data_keys.sort(reverse=True)
			filtered_data_keys.append("GPU")
			filtered_data_keys.append("Threads")
			if filtered_data.get("Pixels"): filtered_data_keys.append("Pixels")
			filtered_data_keys.append("Total")
			string = ""
			for key in filtered_data_keys:
				nested = filtered_data[key]
				try: 
					int(nested['entry_name'])
					if showed_thread: continue
					showed_thread = True
				except: pass
				text = f"{nested['entry_name']} | Total Entries: {nested['entries']} | Total Lag: {sum(nested['total'])} | Average Lag: {nested['average']}"
				string = string + "\n" + text if string else text
				print(text)
			print(f"Time Spent Lagging: {round(((sum(nested['total'])/running_time)*100), 2)}%")
			self.running_diagnosis = False
			#self.gpu.clearprint()
			#self.gpu.printout(string, 20, 30, scale=0.25, static=True)
			
			
		else:
			print("Starting Diagnosis")
			for t in self.threads:
				t.lag_pixels = {str(t.ident):[]}
				t.diagnosis = True
			self.gpu.diagnosis = True
			self.gpu.lag = {"GPU-Adding": [], "GPU-Rendering": []}
			self.running_diagnosis = time.time()
			
			
class PhysicsThread(threading.Thread):
	def __init__(self, window, gpu, settings, pixels, to_move, global_info, *args, **kwargs):
		super(PhysicsThread, self).__init__(*args, **kwargs)
		self.ground = 800 #fix later
		self.settings = settings
		self.pixels = pixels #should be objects, fix laters
		self.gpu = gpu

		self.to_move = to_move
		self.global_info = global_info
		
		self.window = window
		self.diagnosis = False
		self.lag_pixels = {str(self.ident):[]}
		
		
		self.gravity = 3
		
		
		self.ticks = 0
		
		self.st = time.time()
		self.et = 0
		
	def update_coords(self, pixel, old_coords, new_coords):
		self.global_info[new_coords] = pixel
		try: self.global_info.pop(old_coords)
		except: pass
		return pixel
		
	def update_pixel(self, pixel):
		st = time.time()
		pixel.update_function()
		t = time.time() - st
		if t > 0:
			if pixel.type not in self.lag_pixels.keys():
				self.lag_pixels[pixel.type] = []
			self.lag_pixels[pixel.type].append(t)
		
	def run(self):
		self.s_ident = str(self.ident)
		while self.window:
			time.sleep(self.settings.speed)
			[self.update_pixel(pixel) for pixel in self.pixels if not pixel.decay_function() and pixel.movement]
			self.et = time.time() - self.st
			if self.diagnosis: self.lag_pixels[self.s_ident].append(self.et)
			time.sleep(0.0001)
			#print(" ", end="\r")
			#print(self.et)
			self.st = time.time()
				
				
				
		