import numpy as np
import math

def _get_rendering_buffer(xpos, ypos, w, h, zfix=0.0):
    return np.asarray([
        xpos,     ypos - h, 0, 0,
        xpos,     ypos,     0, 1,
        xpos + w, ypos,     1, 1,
        xpos,     ypos - h, 0, 0,
        xpos + w, ypos,     1, 1,
        xpos + w, ypos - h, 1, 0
    ], np.float32)

class OptimizerPointerOLD():
	def __init__(self, i1, i2, index, optimizer):
		if type(i1) != type(0): raise ValueError
		if type(i2) != type(0): raise ValueError
		self.pointer = i1
		self.pointer_end = i2
		self.index = index
		self.optimizer = optimizer
		
class MovementList():
	def __init__(self, v_list):
		self.internal = v_list
		self.future = v_list
		self.iterator = iter(self)
		#self.index = 0
		#self.current = self.future[0] if self.future else None
	
	def __getitem__(self, key):
		return self.future[key]
		
	def __setitem__(self, key, value):
		self.future[key] = value
		
	def __add__(self, value):
		return [i + value for i in self.internal]
		
	def __sub__(self, value):
		return [i - value for i in self.internal]
		
	def __mul__(self, value):
		return [i * value for i in self.internal]
		
	def __div__(self, value):
		return [i / value for i in self.internal]
		
	def __iadd__(self, value):
		self.future = [i + value for i in self.future]
		return self
		
	def __isub__(self, value):
		self.future = [i - value for i in self.future]
		return self
		
	def __imul__(self, value):
		self.future = [i * value for i in self.future]
		return self
		
	def __idiv__(self, value):
		self.future = [i / value for i in self.future]
		return self
		
	def refresh(self):
		self.iterator = iter(self)
			
	def __iter__(self):
		self.index = 0
		self.current = self.future[0] if self.future else None
		return self
		
	def ground(self, index):
		normal = self.internal[index]
		modified = self.future[index]
		diff = modified - normal
		new = math.ceil(modified - (2/diff)) if diff != 0 else normal
		if normal > 0:
			new = new if new <= normal else normal
		else:
			new = new if new >= normal else normal
		return new

	def ground_vectors(self):
		self.future = [self.ground(i) for i in range(len(self.internal))]
			
	def now(self):
		if self.future != self.internal: self.ground_vectors()
		self.current = self.future[self.index]
		return self.current
			
	def __next__(self):
		while True:
			if len(self.future) == 0: break
			self.current = self.future[self.index]
			if self.future != self.internal: self.ground_vectors()
			self.index += 1
			if self.index >= len(self.future): self.index = 0
			return self.future[self.index]
		raise StopIteration
		
class GLPoint():
	def __init__(self, x, y):
		self.x = x
		self.y = y
		self.internal = (x, y)
		
	def __getitem__(self, key):
		return self.internal[key]
		
	def __add__(self, other):
		return GLPoint(self.x + other[0], self.y + other[1])
		
	def __iadd__(self, other):
		self.x += other[0]
		self.y += other[1]
		self.internal = (self.x, self.y)
		return self
		
	def __sub__(self, other):
		return GLPoint(self.x - other[0], self.y - other[1])
	
	def __isub__(self, other):
		self.x -= other[0]
		self.y -= other[1]
		self.internal = (self.x, self.y)
		return self
		
	def __mul__(self, other):
		return GLPoint(self.x * other[0], self.y * other[1])
		
	def __imul__(self, other):
		self.x *= other[0]
		self.y *= other[1]
		self.internal = (self.x, self.y)
		return self
		
	def __div__(self, other):
		return GLPoint(self.x / other[0], self.y / other[1])
		
	def __idiv__(self, other):
		self.x /= other[0]
		self.y /= other[1]
		self.internal = (self.x, self.y)
		return self
		
	def __eq__(self, obj):
		return obj.internal == self.internal
		
	def __hash__(self):
		return hash(self.internal)
		
class OptimizerPointer():
	def __init__(self, main_index, instance_index, optimizer):
		self.main = main_index
		self.instance = instance_index
		self.optimizer = optimizer

def rgb_decimal(c1, c2, c3):
	return (c1/255, c2/255, c3/255)

class ModelLoader:
	def __init__(self):
		self.vert_coords = []
		self.text_coords = []
		self.norm_coords = []

		self.vertex_index = []
		self.texture_index = []
		self.normal_index = []

		self.model = []

	def load_model(self, file):
		for line in open(file, 'r'):
			if line.startswith('#'): continue
			values = line.split()
			if not values: continue

			if values[0] == 'v':
				self.vert_coords.append(values[1:4])
			if values[0] == 'vt':
				self.text_coords.append(values[1:3])
			if values[0] == 'vn':
				self.norm_coords.append(values[1:4])

			if values[0] == 'f':
				face_i = []
				text_i = []
				norm_i = []
				for v in values[1:4]:
					w = v.split('/')
					face_i.append(int(w[0])-1)
					text_i.append(int(w[1])-1)
					norm_i.append(int(w[2])-1)
				self.vertex_index.append(face_i)
				self.texture_index.append(text_i)
				self.normal_index.append(norm_i)

		self.vertex_index = [y for x in self.vertex_index for y in x]
		self.texture_index = [y for x in self.texture_index for y in x]
		self.normal_index = [y for x in self.normal_index for y in x]

		for i in self.vertex_index:
			self.model.extend(self.vert_coords[i])

		for i in self.texture_index:
			self.model.extend(self.text_coords[i])

		for i in self.normal_index:
			self.model.extend(self.norm_coords[i])

		self.model = np.array(self.model, dtype='float32')