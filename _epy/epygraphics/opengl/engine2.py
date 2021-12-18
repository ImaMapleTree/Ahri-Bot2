from multiprocessing.pool import ThreadPool
import threading
import time
import random
from queue import Queue
from _epy.epygraphics.opengl.canvas import *
from _epy.epygraphics.opengl.util import *
from _epy.epygraphics.base import *
import numpy as np
from numba import jit

def requeue(L):
	L.append(L.pop(0))

class PixelObject():
	def __init__(self, engine, gl_object, coords=None, type="Empt", x_movement=MovementList([0]), y_movement=MovementList([0]), color=(0, 0, 0), static=False):
		
		self.x_movement = x_movement
		self.y_movement = y_movement
		
		#self.CXM = self.x_movement.vectors()
		#self.CYM = self.y_movement.vectors()
		self.gl_object = gl_object
		if gl_object:
			self.coords = gl_object.coords
			self.pointer = gl_object.pointer
		
		self.set_color(color)
		self.density = 1
		self.type = type
		self.static = static
		self.ticks = 0
		
		if coords: self.coords = Point2D(coords)
		self.engine = engine
		self.exists = False
	
	def behavior_function(self):
		self.behavior_function = None
		
	def set_color(self, rgb255):
		self.color = rgb255
		decimal_color = rgb_decimal(*rgb255)
		self.gl_object.color = decimal_color
		if self.pointer.optimizer:
			self.pointer.optimizer.updateColorInstance(self.pointer.main, self.pointer.instance, decimal_color)
		
	def translateX(self, x):
		if self.pointer.optimizer:
			self.pointer.optimizer.updateXOffsetInstance(self.pointer.main, self.pointer.instance, self.coords[0])
		
	def translateY(self, y):
		if self.pointer.optimizer:
			self.pointer.optimizer.updateYOffsetInstance(self.pointer.main, self.pointer.instance, self.coords[1])
		
	def translate(self, x, y):
		self.coords += (x, y)
		self.gl_object.coords = self.coords
		if x: self.translateX(x)
		if y: self.translateY(y)
			
	def relocateX(self, x):
		if self.pointer.optimizer:
			self.pointer.optimizer.updateXOffsetInstance(self.pointer.main, self.pointer.instance, self.coords[0])
		
	def relocateY(self, y):
		if self.pointer.optimizer:
			self.pointer.optimizer.updateYOffsetInstance(self.pointer.main, self.pointer.instance, self.coords[1])
		
	def relocate(self, x, y):
		self.coords = GLPoint(x, y)
		self.gl_object.coords = self.coords
		if x: self.relocateX(x)
		if y: self.relocateY(y)
			
	def refresh_movement(self):
		self.x_movement.refresh()
		self.y_movement.refresh()
		
	def __bool__(self):
		return self.exists

class PixelEngine():
	def __init__(self, window, gpu):
		self.window = window
		self.gpu = gpu
		self.xy_data = {}
		self.pixel_data = {}
		self.util_list = [-1, 1]
		self.pixel_count = 0
		
		self.threads = []
		self.thread_amount = 16
		self.running_diagnosis = False
		for i in range(self.thread_amount):
			amount = len(self.threads)
			t = PET(self.window, self.pixel_data, self.xy_data, amount/self.thread_amount, (amount+1)/self.thread_amount, daemon=True)
			self.threads.append(t)
			t.start()
	
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
	
		else:
			print("Starting Diagnosis")
			for t in self.threads:
				t.lag_pixels = {str(t.ident):[]}
				t.diagnosis = True
			self.gpu.diagnosis = True
			self.gpu.lag = {"GPU-Adding": [], "GPU-Rendering": []}
			self.running_diagnosis = time.time()
		
	def create_pixel(self, type, coords, check=False):
		if check:
			if self.xy_data.get(GLPoint(*coords)): return
		pixel = GLPixel(coords[0], coords[1], VBO=True)
		self.gpu.addObject(pixel)
		alive = type(self, pixel)
		alive.exists = True
		self.pixel_data[alive] = alive.coords
		self.set_coord(alive.coords, alive)
		self.pixel_count += 1
		#print(self.pixel_count)
		
	def set_coord(self, coord, data):
		old = self.xy_data.get(coord)
		if old: self.recycle(old)
		self.xy_data[coord] = data
		
	def get_individual(self, coord, cull=True):
		i = self.xy_data.get(coords)
		if not i: 
			if cull: return None
			return PixelObject(self, coords=coords)
		return i
		
	def get_adjacent(self, coords, cull=True):
		adjacent = [self.get_individual(coords.npX(x). cull) for x in self.util_list]
		adjacent += [self.get_individual(coords.npY(y), cull) for y in self.util_list]
		if cull: return [adj for adj in adjacent if adj]
		return adjacent
		
	def recycle(self, old):
		old.exists = False
		old.movement = 0
		old.set_color((0, 0, 0))
		old.relocate(-1, -1)
		self.gpu.recycle(old.gl_object)
		self.pixel_data.pop(old)
		try:
			self.xy_data.pop(old.coords)
		except:
			pass
			
	def _update(self, pixel):
		pixel.ticks += 1
		if pixel.behavior_function: 
			if pixel.behavior_function(): return
		if pixel.static: return

		self.xy_data[pixel.coords] = None
		CX, CY = pixel.x_movement.current, pixel.y_movement.now()
		point = pixel.coords + (CX, CY)
		state = self.xy_data.get(point)
		if not state:
			pixel.translate(CX, CY)
			pixel.refresh_movement()
		
		elif pixel.density * CY > state.density * CY and state.density != 100:
			state.translate(0, CY*-1)
			self.xy_data[state.coords] = state
			pixel.translate(CX, CY)
			pixel.refresh_movement()
		
		else: next(pixel.x_movement); next(pixel.y_movement)
		self.xy_data[pixel.coords] = pixel
		return
			
	def UPDATE(self):
		st = time.time()
		[self._update(pixel) for pixel in list(self.pixel_data.keys())]


class PET(threading.Thread):
	def __init__(self, window, pixel_data, xy_data, per1, per2, *args, **kwargs):
		super(PET, self).__init__(*args, **kwargs)
		self.window = window
		self.pixel_data = pixel_data
		self.xy_data = xy_data
		self.per1 = per1
		self.per2 = per2
		self.diagnosis = False
		self.lag_pixels = {str(self.ident):[]}
		
	def _update(self, pixel):
		st = time.time()
		pixel.ticks += 1
		if pixel.behavior_function: 
			if pixel.behavior_function(): return

		CX, CY = pixel.x_movement.current, pixel.y_movement.now()
		point = pixel.coords + (CX, CY)
		state = self.xy_data.get(point)
		if not state:
			self.xy_data[pixel.coords] = None
			pixel.translate(CX, CY)
			pixel.refresh_movement()
			self.xy_data[pixel.coords] = pixel
		
		elif pixel.density * CY > state.density * CY and state.density != 100:
			self.xy_data[pixel.coords] = None
			state.translate(0, CY*-1)
			self.xy_data[state.coords] = state
			pixel.translate(CX, CY)
			pixel.refresh_movement()
			self.xy_data[pixel.coords] = pixel
		
		else: next(pixel.x_movement); next(pixel.y_movement)
		t = time.time() - st
		if t > 0:
			if pixel.type not in self.lag_pixels.keys():
				self.lag_pixels[pixel.type] = []
			self.lag_pixels[pixel.type].append(t)
		return
			
	def run(self):
		self.s_ident = str(self.ident)
		while self.window:
			st = time.time()
			CL = list(self.pixel_data.keys())
			length = len(CL) - 1
			CL = CL[math.ceil(length*self.per1):math.ceil(length*self.per2)]
			
			[self._update(pixel) for pixel in CL if not pixel.static]
			if self.diagnosis: self.lag_pixels[self.s_ident].append(time.time()-st)
			print(" ", end="\r")



'''
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
		
	def __bool__(self):
		return False
		
	def update_function(self):
		return self

class PhysicsObject():
	def __init__(self, gl_object, engine, active=True):
		self.gl_object = gl_object
		self.coords = self.gl_object.coords
		
		self.engine = engine
		self.gravity = engine.gravity
		self.global_states = engine.global_info
		self.ground = engine.ground
		
		self.active = active
		self.pointer =  gl_object.pointer
		self.flamability = 0
		self.ticks = 1
		self.max_ticks = None
		self.decays = False
		self.finalized = False
		self.ready = True
		self.timing = time.time()
		self.time_step = 0
			
		if len(self.gl_object.coords) == 3:
			self.x, self.y, self.z = self.coords[0], self.coords[1], self.coords[2]
		else: self.x, self.y, self.z = self.coords[0], self.coords[1], 0

	def force(self, *m):
		return self

	def translate(self, x, y, z=None):
		if z != None: self.gl_object.translate(x, y, z)
		else: self.gl_object.translate(x, y); z = 0
		self.x += x; self.y += y; self.z += z
		self.coords = self.gl_object.coords
		
	def move_to(self, coords):
		self.gl_object.move_to(coords[0], coords[1])
		self.coords = self.gl_object.coords
		self.x = self.coords[0]
		self.y = self.coords[1]
		
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
		self.translate(*m)
		self.global_states[self.coords] = self
		return self
		
	def jump_pixel(self, coords):
		old = self.coords
		try: self.global_states.pop(old)
		except: pass
		self.move_to(coords)
		self.global_states[coords] = self
		return self
		
	def project(self, x, y):
		return (self.coords[0] + x, self.coords[1] + y)
	
	def remove(self, replacement=None):
		if replacement:
			self.__class__ = replacement.__class__
			self.__init__(self.gl_object, self.engine)
			self.gl_object.change_color(replacement.gl_object.color)
			self.global_states[self.coords] = self
		else:
			self.global_states[self.coords] = None
			self.gl_object.change_color((0.0, 0.0, 0.0))
			self.gl_object.move_to(-1, -1)
			self.coords = self.gl_object.coords
			self.update_function = PhysicsObject.update_function
			self.engine.gpu.recycle(self.gl_object)
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
		return [self.update_function, self.decay_function, self.density, self.decays, self.max_ticks]
		
	def set_movement_attributes(self, attribute):
		self.consumed_function = attribute[0]
		if attribute[3]:
			self.decay_function = attribute[1]
		self.density = attribute[2]
		if attribute[4]: self.max_ticks = attribute[4]
		
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
		new = type(self.gl_object, self.engine)
		return self.remove(new)

class PhysicsEngine():
	def __init__(self, window, gpu, pixels):
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
		pixel = GLPixel(coords[0], coords[1], VBO=True)
		self.gpu.addObject(pixel)
		alive = type(pixel, self)
		self.global_info[alive.coords] = alive
		
		self.threads[self.pixel_index].pixels.append(alive)
		self.pixel_index = self.pixel_index + 1 if self.pixel_index + 1 < self.t_amount else 0
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
			[self.update_pixel(pixel) for pixel in self.pixels if not pixel.decay_function()]
			self.et = time.time() - self.st
			if self.diagnosis: self.lag_pixels[self.s_ident].append(self.et)
			print(" ", end="\r")
			#print(self.et)
			self.st = time.time()
'''
				
				
		