from multiprocessing.pool import ThreadPool
import threading
import time
import random
from queue import Queue
from _epy.epygraphics.opengl.engine import *
from _epy.epygraphics.opengl.util import *
import numpy as np


class Concrete(PhysicsObject):
	def __init__(self, *args, **kwargs):
		super(Concrete, self).__init__(*args, **kwargs)
		if self.gl_object.color == (1.0, 1.0, 1.0):
			val1 = random.uniform(0.25, 0.5)
			self.gl_object.color = (val1, val1, val1)
		self.type = "Concrete"
		self.density = 100
		self.active = False
		
	def decay_function(self):
		return True
		
class Sand(PhysicsObject):
	def __init__(self, *args, **kwargs):
		super(Sand, self).__init__(*args, **kwargs)
		self.gl_object.color = (random.uniform(0.80, 0.92), 0.70, 0.50)
		self.movement = 1
		self.type = "Sand"
		self.density = 2
		self.last_coords = (0, 0)
		self.no_movement = 0
		
	def force(self, *m):
		existing_pixel = self.global_states.get(self.project(*m))
		if existing_pixel:
			if existing_pixel.density >= 100: return
				
		current_coords = self.coords
		self.translate(*m) #Translates itself downwards
		self.global_states[self.coords] = self #set new location to yourself
		
		if existing_pixel:
			existing_pixel.move_to(current_coords)
			self.global_states[current_coords] = existing_pixel
		else:
			try: self.global_states.pop(current_coords)
			except: pass
			
		return self
	
	def update_function(self, ticks=0):
		if ticks: self.ticks = ticks
		if not self.active: return
		new_coords = (self.x, self.y+self.movement)
		pixel = self.global_states.get(new_coords)
		if not pixel: return self.move_pixel(0, self.movement)
		if self.density > pixel.density: return self.force(0, self.movement)
		
		self.ready = True
		locations = self.inrange([(self.x-1, self.y+1), (self.x+1, self.y+1)])
		[self.find_movement(location) for location in locations if not location or self.density > location.density]
		return self
		
class Water(PhysicsObject):
	def __init__(self, *args, **kwargs):
		super(Water, self).__init__(*args, **kwargs)
		self.gl_object.color = (0.70, random.uniform(0.85, 0.94), 0.96)
		self.movement = 1
		self.since_down = 0
		self.choices = ["left", "right"]
		self.direction = random.choice(self.choices)
		self.type= "Water"
		self.density = 1
		self.last_coords = (0, 0)
		self.no_movement = 0
	
	def force(self, *m):
		existing_pixel = self.global_states.get(self.project(*m))
		if existing_pixel:
			if existing_pixel.density >= 100: return
				
		current_coords = self.coords
		self.translate(*m)
		self.global_states[self.coords] = self

		if existing_pixel:
			existing_pixel.move_to(current_coords)
			self.global_states[current_coords] = existing_pixel
		else:
			try: self.global_states.pop(current_coords)
			except: pass
			
		return self
		
	def update_function(self, ticks=0):
		if self.ticks % 50 == 0: self.direction = random.choice(self.choices)
		if ticks: self.ticks = ticks
		if not self.active: return self
		if self.y < 0: self.remove()
		if self.since_down > 2000: 
			if self.type == "Water": self.setType(Steam)
			else: self.remove()
				
		self.ready = True
		new_coords = (self.x, self.y+self.movement)
		pixel = self.global_states.get(new_coords)
		if not pixel: self.since_down = 0; return self.move_pixel(0, self.movement)
		density = self.density * self.movement
		pd = pixel.density * self.movement if pixel.density < 100 else pixel.density
		if density > pd: return self.force(0, self.movement)
		
		self.since_down += 1
		
		self.ready = True
		if self.direction == "left":
			locations = self.inrange([(self.x-1, self.y), (self.x+1, self.y)])
		else:
			locations = self.inrange([(self.x+1, self.y), (self.x-1, self.y)])
		[self.find_movement(location) for location in locations if not location or density > location.density * self.movement]		
		if self.ready:
			self.since_down -= 1
		return self
		
		
class Wire(Concrete):
	def __init__(self, *args, **kwargs):
		super(Wire, self).__init__(*args, **kwargs)
		val1 = random.randint(0, 20)
		self.gl_object.color = rgb_decimal(212, 123-val1, 83-val1)
		self.off_color = self.gl_object.color
		val1 = random.randint(0, 20)
		self.on_color = rgb_decimal(190+val1, 255, 255)
		self.type = "Wire"
		self.component = "Wire"
		self.energized = False
		self.energy_decay = 0
		self.targeter1 = None
		self.cap = False
		self.lockout = 0
	
	def decay_function(self):
		self.tick()
		if self.ticks % 3 <= self.time_step: return False
		return True

	def update_state(self, origin):
		if self.ticks < self.lockout: return
		if origin.energized != self.energized:
			self.energized = origin.energized
			self.lockout = self.ticks + 300
			if self.targeter1: self.targeter1.update_state(self)
			self.targeter1 = origin
			
	def set_decay(self, origin):
		self.energy_decay = self.ticks + 200
			
	def set_visual(self, state):
		if state:
			self.gl_object.change_color(self.on_color)
		else:
			self.gl_object.change_color(self.off_color)		
				
	def set_state(self, target):
		target.update_state(self)

	def update_function(self):
		self.set_visual(self.energized)
		r = random.randint(1, 2)
		if r == 1:
			neighbors = self.get_neighbors()
			if neighbors:
				n = random.choice(neighbors)
				if hasattr(n, "energized"): n.update_state(self)
		
		#if self.energized: self.trigger = 3
		#else: self.trigger = 15
		#if self.ticks > self.energy_decay:
			#self.energized = False
			#self.energy_decay = self.ticks + random.randint(1500, 5000)
		
		if self.cap:
			if self.energized:
				flash = random.randint(0, 50)
				if flash == 1: self.toggle_visual()
			if self.visual:
				flash = random.randint(0, 7)
				if flash == 1: self.toggle_visual()
		
class Lamp(Wire):
	def __init__(self, *args, **kwargs):
		super(Lamp, self).__init__(*args, **kwargs)
		self.off_color = rgb_decimal(43, 43, 43)
		self.gl_object.color = self.off_color
		val1 = random.randint(0, 50)
		self.on_color = rgb_decimal(255, 225+(val1*0.2), val1)
		self.type = "Lamp"
		self.component = "Lamp"
			
	def decay_function(self):
		self.tick()
		if self.ticks % 42 <= self.time_step: return False
		return True
		
	def update_function(self):
		self.set_visual(self.energized)
		
class Inverter(Wire):
	def __init__(self, *args, **kwargs):
		super(Inverter, self).__init__(*args, **kwargs)
		self.off_color = rgb_decimal(71, 0, 59)
		self.gl_object.color = self.off_color
		self.on_color = rgb_decimal(196, 0, 163)
		self.type = "Component"
		self.component = "Inverter"
		
	def decay_function(self):
		self.tick()
		if self.ticks % 30 <= self.time_step: return False
		return True
		
	def update_state(self, origin):
		if self.ticks < self.lockout: return
		energy = origin.energized if origin.component == "Inverter" else not origin.energized
			
		if energy != self.energized:
			self.lockout = self.ticks + 1000
			self.energized = energy
			if self.targeter1: self.targeter1.update_state(self)
			self.targeter1 = origin
	
	def update_function(self):
		self.set_visual(self.energized)
		r = random.randint(1, 2)
		if r == 1:
			neighbors = self.get_neighbors()
			if neighbors:
				n = random.choice(neighbors)
				if hasattr(n, "energized"):
					if n.type == "Component": n.update_state(self)
						
class Gatherer(Wire):
	def __init__(self, *args, **kwargs):
		super(Gatherer, self).__init__(*args, **kwargs)
		self.off_color = rgb_decimal(81, 56, 128)
		self.gl_object.color = self.off_color
		self.on_color = rgb_decimal(155, 125, 212)
		self.type = "Component"
		self.component = "Gatherer"
		
	def update_state(self, origin):
		if self.ticks < self.lockout: return
		if origin.type != "Component": return
			
		if origin.energized != self.energized:
			self.lockout = self.ticks + 300
			self.energized = origin.energized
			if self.targeter1: self.targeter1.update_state(self)
			self.targeter1 = origin
			
	def decay_function(self):
		self.tick()
		if self.ticks % 40 <= self.time_step: return False
		return True		
			
	def update_function(self):
		self.set_visual(self.energized)
		r = random.randint(1, 2)
		if r == 1:
			neighbors = self.get_neighbors()
			if neighbors:
				n = random.choice(neighbors)
				if hasattr(n, "energized"):
					if n.type != "Component":
						n.update_state(self)
					elif n.component == "Gatherer":  n.update_state(self)
		
class Connector(Wire):
	def __init__(self, *args, **kwargs):
		super(Connector, self).__init__(*args, **kwargs)
		self.type = "Component"
		self.component = "Connector"
		self.change_attempts = 0
		self.off_color = rgb_decimal(128, 67, 62)
		self.on_color = rgb_decimal(173, 77, 69)

	def update_state(self, origin):
		if self.ticks < self.lockout: return
		if origin.type != "Component": return
			
		if origin.energized != self.energized:
			self.change_attempts += 1
			if self.change_attempts > 3:
				self.lockout = self.ticks + 300
				self.energized = origin.energized
				if self.targeter1: self.targeter1.update_state(self)
				self.targeter1 = origin
				self.change_attempts = 0
			
	def decay_function(self):
		self.tick()
		if self.ticks % 40 <= self.time_step: return False
		return True		
			
	def update_function(self):
		self.set_visual(self.energized)
		r = random.randint(1, 2)
		if r == 1:
			neighbors = self.get_neighbors()
			if neighbors:
				n = random.choice(neighbors)
				if hasattr(n, "energized"):
					if n.type != "Component":
						n.update_state(self)
					elif n.component == "Connector":  n.update_state(self)
						
		
class Chargestone(Concrete):
	def __init__(self, *args, **kwargs):
		super(Chargestone, self).__init__(*args, **kwargs)
		self.active = True
		yellow = random.randint(0, 12)
		if yellow == 1:
			val1 = random.randint(0, 30)
			self.gl_object.color = rgb_decimal(205-(val1*0.3), 255, 135-val1)  #191, 252, 106
		else:
			val1 = random.randint(0, 40)
			self.gl_object.color = rgb_decimal(144-val1, 255-(val1*0.3), 140-val1) #144, 255, 140 #108, 240, 104
			
	def decay_function(self):
		self.tick()
		if self.ticks % 10 <= self.time_step: return False
		return True
		
	def change_state(self, target, state):
		target.energized = state
		
	def update_function(self):
		neighbors = self.get_neighbors()
		[self.change_state(neighbor, self.engine.energy) for neighbor in neighbors if hasattr(neighbor, "energized")]
		
		
	

class Dirt(Sand):
	def __init__(self, *args, **kwargs):
		super(Dirt, self).__init__(*args, **kwargs)
		grey = random.randint(0, 10)
		if grey == 1:
			val1 = random.uniform(0.0, 0.2)
			self.gl_object.color = (0.46-val1, 0.38-val1, 0.30-val1)
		else:
			val1 = random.uniform(0.0, 0.1)
			self.gl_object.color = (0.61-val1, 0.46-val1, 0.33)
		self.type = "Dirt"
		
class Smoke(Water):
	def __init__(self,  *args, **kwargs):
		super(Smoke, self).__init__(*args, **kwargs)
		val1 = random.uniform(0.0, 0.22)
		self.gl_object.color = (0.25-val1, 0.25-val1, 0.25-val1)
		self.max_ticks = random.randint(600, 2000)
		self.decays = True
		self.type = "Smoke"
		self.movement = -1
		self.density = 0.3
	
	def decay_function(self):
		self.tick()
		if self.ticks > self.max_ticks: self.remove(); return True
		if self.ticks % 10 <= self.time_step: return False
		return True

class Steam(Smoke):
	def __init__(self, *args, **kwargs):
		super(Steam, self).__init__(*args, **kwargs)
		self.type = "Steam"
		self.density = 0.2
		val1 = random.uniform(0, 20)
		self.gl_object.color = rgb_decimal(222-val1, 222-val1, 222-val1)

class Wood(Concrete):
	def __init__(self, *args, **kwargs):
		super(Wood, self).__init__(*args, **kwargs)
		val1 = random.uniform(0.0, 0.04)
		self.gl_object.color = (0.2-val1, 0.13-val1, 0.06-val1)
		self.type = "Wood"
		self.flamability = 7
		
class Biomatter(Concrete):
	def __init__(self, *args, **kwargs):
		super(Biomatter, self).__init__(*args, **kwargs)
		color = random.randint(1, 3)
		val1 = random.uniform(0, 20)
		val2 = random.uniform(0, 10)
		
		if color == 1:
			self.gl_object.color = rgb_decimal(88-val1, 127-val1, 95-val1)
		elif color == 2:
			self.gl_object.color = rgb_decimal(52-(val1*0.5), 60-(val1*0.35), 53-(val1*0.5))
		else:
			self.gl_object.color = rgb_decimal(55, 48-val2, 35-(val2*0.5))
			
		self.type = "Biomatter"
		self.flamability = 28
		self.max_ticks = random.randint(600, 1600)
		
	def decay_function(self):
		self.tick()
		if self.ticks % 2 <= self.time_step: return False
		return True
		
class Fire(PhysicsObject):
	def __init__(self, *args, **kwargs):
		super(Fire, self).__init__(*args, **kwargs)
		val1 = random.uniform(0.0, 0.7)
		val2 = val1+0.94 if val1+0.94 < 1.0 else 1.0
		self.gl_object.color = (val2, 0.9-val1, random.uniform(0, 0.11))
		self.gl_object.change_color(self.gl_object.color)
		self.max_ticks = random.randint(800, 1800)
		self.decays = True
		self.density = 3
		self.type = "Fire"
		self.ticks = 0
		
	def burn(self, pixel):
		chance = random.randint(1, 30)
		if chance > pixel.flamability: return pixel
		attributes = pixel.get_movement_attributes()
		pixel.setType(Fire)
		pixel.set_movement_attributes(attributes)
		return pixel
		
	def consumed_function(self, ticks=None):
		return
		
	def decay_function(self):
		self.tick()
		if self.ticks % 8 <= self.time_step: return False
		return True
		
	def water_death(self, neighbor):
		n = neighbor.coords
		s = self.coords
		neighbor.remove()
		self.remove()
		self.engine.create_pixel(Steam, n)
		return self.create_smoke(s, 1)
		
	def create_smoke(self, coords, max=2):
		chance = random.randint(1, max)
		if chance == 2: return
		return self.engine.create_pixel(Smoke, coords)
		
	def create_ember(self, coords):
		chance = random.randint(1, 20)
		if chance != 1: return
		self.engine.create_pixel(Ember, coords)
		
	def update_function(self):
		if self.ticks > self.max_ticks: self.setType(Smoke); return True
		ticks = self.ticks
		self.consumed_function(ticks)
		self.ticks = ticks
		
		neighbors = self.get_neighbors(False)
		[self.water_death(neighbor) for neighbor in neighbors if neighbor.type == "Water"]
		ember_chance = random.randint(1, 20)
		if ember_chance == 1:
			[self.create_ember(neighbor.coords) for neighbor in neighbors if neighbor.type == "Empty"]
			
		if ember_chance in range(2, 4):
			[self.burn(neighbor) for neighbor in neighbors if neighbor.flamability]
			
		if ember_chance == 5:
			[self.create_smoke(neighbor.coords) for neighbor in neighbors if neighbor.type == "Empty"]

class Oil(Water):
	def __init__(self, *args, **kwargs):
		super(Oil, self).__init__(*args, **kwargs)
		val1 = random.randint(0, 20)
		self.max_ticks = random.randint(1200, 2200)
		self.gl_object.color = rgb_decimal(20-val1, 12-(val1*0.5), 0)
		self.type = "Oil"
		self.flamability = 15
		self.density = 0.9
	
	def decay_function(self):
		self.tick()
		if self.ticks % 12 <= self.time_step: return False
		return True
		
class Salt(Sand):
	def __init__(self, *args, **kwargs):
		super(Salt, self).__init__(*args, **kwargs)
		val1 = random.randint(0, 9)
		val2 = random.randint(0, 65)
		self.gl_object.color = rgb_decimal(255-val1, 215-(0.6*val2), 205-val2)
		self.type = "Salt"
		self.density = 100
		self.active = False
		
	def dissolve(self):
		chance = random.randint(0, 200)
		if chance <= 3:
			self.active = True
			self.density = 2
		if chance == 4:
			self.remove()
		
	def decay_function(self):
		self.tick()
		if self.ticks % 4 <= self.time_step: return False
		return True
	
	def update_function(self):
		super().update_function()
		neighbors = self.get_neighbors()
		[self.dissolve() for neighbor in neighbors if neighbor.type == "Water"]
	
class Methane(Water):
	def __init__(self, *args, **kwargs):
		super(Methane, self).__init__(*args, **kwargs)
		self.max_ticks = random.randint(50, 800)
		val1 = random.randint(0, 20)
		self.gl_object.color = rgb_decimal(247-val1, 255-(val1*0.5), 217-val1)
		self.type = "Methane"
		self.flamability = 25
		self.density = 0.1
		self.movement = -1
		
	def decay_function(self):
		self.tick()
		if self.ticks % 10<= self.time_step: return False
		return True

class Charcoal(Sand):
	def __init__(self, *args, **kwargs):
		super(Charcoal, self).__init__(*args, **kwargs)
		light = random.randint(0, 5)
		if light == 1:
			val1 = random.randint(0, 10)
			self.gl_object.color = rgb_decimal(80-val1, 80-val1, 80-val1)
		else:
			val1 = random.randint(0, 20)
			self.gl_object.color = rgb_decimal(50-val1, 50-val1, 50-val1)
		self.type = "Charcoal"
		self.flamability = 5
		self.density = 2
		self.max_ticks = random.randint(3000, 6000)
	
	def decay_function(self):
		self.tick()
		if self.ticks % 4 <= self.time_step: return False
		return True

class Ember(Sand):
	def __init__(self, *args, **kwargs):
		super(Ember, self).__init__(*args, **kwargs)
		val1 = random.randint(0, 50)
		val2 = random.randint(0, 20)
		self.gl_object.color = rgb_decimal(120+val1, 60-val2, 0)
		self.type = "Ember"
		self.max_ticks = random.randint(500, 1000)
		self.gl_object.change_color(self.gl_object.color)
		self.density = 0.5
		self.decays = True
		
	def burn(self, pixel):
		chance = random.randint(1, 30)
		if chance > pixel.flamability: return pixel
		attributes = pixel.get_movement_attributes()
		pixel.setType(Fire)
		pixel.set_movement_attributes(attributes)
		return pixel
			
	def decay_function(self):
		self.tick()
		if self.ticks > self.max_ticks: self.remove(); return True
		if self.ticks % 10 <= self.time_step: return False
		return True
			
	def update_function(self):
		super().update_function()
		
		movement = random.randint(1, 8)
		distance = random.choice([-1, -1, -1, -2, -2, -3])
		
		neighbors = self.get_neighbors()
		[self.remove()  for neighbor in neighbors if neighbor.type == "Water"]
		
		if movement == 1:
			new_coords = (self.x-1, self.y+distance)
			pixel = self.global_states.get(new_coords)
			if not pixel: return self.move_pixel(-1, distance)
				
		if movement == 2:
			new_coords = (self.x, self.y+distance)
			pixel = self.global_states.get(new_coords)
			if not pixel: return self.move_pixel(0, distance)
		
		if movement == 3:
			new_coords = (self.x+1, self.y+distance)
			pixel = self.global_states.get(new_coords)
			if not pixel: return self.move_pixel(1, distance)
		
		if movement == 4:
			[self.burn(pixel) for pixel in neighbors if pixel.flamability]
		return self
		
		
