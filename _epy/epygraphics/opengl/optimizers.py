from OpenGL.arrays import vbo
from OpenGL.GL import *
from _epy.epygraphics.opengl.util import *
import numpy as np
import time
import ctypes
import numba

class VBO_Optimizer():	
	def __init__(self, max_vao_size=1000):
		self.vaos = []
		self.xoffsets = []
		self.yoffsets = []
		self.colors = []
		self.index = 0
		self.mvs = max_vao_size
		
		self.updates = []
		
	def _UPDATE_COLORS(self, index):
		indexed_list = self.colors[index]
		color_array = np.array(indexed_list[1], np.float32)
		glBindBuffer(GL_ARRAY_BUFFER, color_buffer);
		glBufferData(GL_ARRAY_BUFFER, color_array.itemsize*len(color_array), color_array, GL_STATIC_DRAW);
		glEnableVertexAttribArray(1);
		glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0,  ctypes.c_void_p(0));
		glVertexAttribDivisor(1, 1);
		
	def _UPDATE_OFFSETS(self, index):	
		indexed_list = self.offsets[index]
		offset_array = np.array(indexed_list[1], np.float32)
		glBindBuffer(GL_ARRAY_BUFFER, offset_buffer);
		glBufferData(GL_ARRAY_BUFFER, offset_array.itemsize*len(offset_array), offset_array, GL_STATIC_DRAW);
		#glBindBuffer(GL_ARRAY_BUFFER, 0);
		
		glEnableVertexAttribArray(2);
		glBindBuffer(GL_ARRAY_BUFFER, offset_buffer);
		glVertexAttribPointer(2, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0));
		glBindBuffer(GL_ARRAY_BUFFER, 0);
		glVertexAttribDivisor(2, 1);
		
		
	def addType(self, data):
		quadVAO = glGenVertexArrays(1);
		quadVBO = glGenBuffers(1);
		glBindVertexArray(quadVAO);
		glBindBuffer(GL_ARRAY_BUFFER, quadVBO);
		glBufferData(GL_ARRAY_BUFFER, data.itemsize*len(data), data, GL_STATIC_DRAW);
		glEnableVertexAttribArray(0);
		glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0));
		
		color_buffer = glGenBuffers(1)
		
		pregen_colors = []
		for i in range(self.mvs):
			pregen_colors.append(rgb_decimal(153, 147, 130))
		color_array = np.array(pregen_colors, np.float32).flatten()
		
		self.colors.append([color_buffer, color_array, 0])
		
		indexed_list = self.colors[self.index]
		glBindBuffer(GL_ARRAY_BUFFER, color_buffer);
		glBufferData(GL_ARRAY_BUFFER, color_array.itemsize*len(color_array), color_array, GL_STATIC_DRAW);
		glEnableVertexAttribArray(1);
		glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, 0,  ctypes.c_void_p(0));
		glVertexAttribDivisor(1, 1);
		
		offset_x_buffer = glGenBuffers(1);
		
		pregen_x_offsets = np.zeros(self.mvs, np.float32)
		pregen_y_offsets = np.zeros(self.mvs, np.float32)
			
		self.xoffsets.append([offset_x_buffer, pregen_x_offsets, 0])
		indexed_list = self.xoffsets[self.index]
		offset_array = np.array(indexed_list[1], np.float32).flatten()
		glBindBuffer(GL_ARRAY_BUFFER, offset_x_buffer);
		glBufferData(GL_ARRAY_BUFFER, offset_array.itemsize*len(offset_array), offset_array, GL_STATIC_DRAW);
		
		glEnableVertexAttribArray(2);
		glBindBuffer(GL_ARRAY_BUFFER, offset_x_buffer);
		glVertexAttribPointer(2, 1, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0));
		glBindBuffer(GL_ARRAY_BUFFER, 0);
		glVertexAttribDivisor(2, 1);
		
		offset_y_buffer = glGenBuffers(1);
		
		self.yoffsets.append([offset_y_buffer, pregen_y_offsets, 0])
		indexed_list = self.yoffsets[self.index]
		offset_array = np.array(indexed_list[1], np.float32).flatten()
		glBindBuffer(GL_ARRAY_BUFFER, offset_y_buffer);
		glBufferData(GL_ARRAY_BUFFER, offset_array.itemsize*len(offset_array), offset_array, GL_STATIC_DRAW);
		
		glEnableVertexAttribArray(3);
		glBindBuffer(GL_ARRAY_BUFFER, offset_y_buffer);
		glVertexAttribPointer(3, 1, GL_FLOAT, GL_FALSE, 0, ctypes.c_void_p(0));
		glBindBuffer(GL_ARRAY_BUFFER, 0);
		glVertexAttribDivisor(3, 1);
		
		glBindVertexArray(0);
		
		self.vaos.append(quadVAO)
		
		self.index_index = 0
		
		self.index += 1
		return self.index - 1
		
	def addOffsetInstance(self, index, data):
		triple_list = self.xoffsets[index]
		pregen_data = triple_list[1]
		index_index = triple_list[2]
		pregen_data[index_index] = data[0]
		triple_list[2] += 1
		
		triple_list = self.yoffsets[index]
		pregen_data = triple_list[1]
		index_index = triple_list[2]
		pregen_data[index_index] = data[1]
		triple_list[2] += 1
		if not index in self.updates: self.updates.append(index)
		return index_index
		
	def addColorInstance(self, index, data):
		triple_list = self.colors[index]
		pregen_data = triple_list[1]
		index_index = triple_list[2]
		
		pregen_data[index_index] = data[0]
		pregen_data[index_index+1] = data[1]
		pregen_data[index_index+2] = data[2]
		if not index in self.updates: self.updates.append(index)
		triple_list[2] += 3
		return index_index
		
	def updateXOffsetInstance(self, MI, II, x):
		self.xoffsets[MI][1][II] = x
		if not MI in self.updates: self.updates.append(MI)
		return
		
	def updateYOffsetInstance(self, MI, II, y):
		self.yoffsets[MI][1][II] = y
		if not MI in self.updates: self.updates.append(MI)
		return
		
	def updateOffsetInstance(self, MI, II, coords):
		self.xoffsets[MI][1][II] = coords[0]
		self.yoffsets[MI][1][II] = coords[1]
		if not MI in self.updates: self.updates.append(MI)
		return
		
	def updateColorInstance(self, MI, II, data):
		colors = self.colors[MI][1]
		m3 = II*3
		colors[m3] = data[0]
		colors[m3+1] = data[1]
		colors[m3+2] = data[2]
		if not MI in self.updates: self.updates.append(MI)
		return
		
	def draw(self, i):
		vao = self.vaos[i]
		if vao == None: return
		amount = self.xoffsets[i][2]
		glBindVertexArray(vao)
		glDrawArraysInstanced(GL_QUADS, 0, 4, amount)
		
	def draw_all(self):
		if len(self.updates) >= 1:
			ST = time.time()
			for index in self.updates:
				indexed_list = self.xoffsets[index]
				buffer = indexed_list[0]
				glBindBuffer(GL_ARRAY_BUFFER, buffer)
				glBufferSubData(GL_ARRAY_BUFFER, 0, indexed_list[1])
				
				indexed_list = self.yoffsets[index]
				buffer = indexed_list[0]
				glBindBuffer(GL_ARRAY_BUFFER, buffer)
				glBufferSubData(GL_ARRAY_BUFFER, 0, indexed_list[1])
				
				indexed_list = self.colors[index]
				buffer = indexed_list[0]
				glBindBuffer(GL_ARRAY_BUFFER, buffer)
				glBufferSubData(GL_ARRAY_BUFFER, 0, indexed_list[1])
			self.updates = []
	
		[self.draw(i) for i in range(len(self.vaos))]
		return
		
	def __iter__(self):
		self.n = 0
		return self
		
	def __next__(self):
		if self.n < self.total:
			res = self.vbos[self.n]
			self.n += 1
			return res
		else:
			raise StopIteration