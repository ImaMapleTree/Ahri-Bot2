from _epy.epygraphics.util import *
from _epy.epygraphics.base import *
from _epy.epygraphics.exceptions import *
from _epy.epygraphics.events import *
import tkinter as tk
import time

def in_bbox(bbox, point):
	if not bbox[0] < point[0] < bbox[2]: return False
	if not bbox[1] < point[1] < bbox[3]: return False
	return True

class Canvas(tk.Canvas):
	def __init__(self, *args, **kwargs):
		super(Canvas, self).__init__(*args, **kwargs)
		self._freezelock = None
		self.objects = {}
		self._updated = False
	
	def identify(self, ids):
		if type(ids) == type(int): return self.objects.get(ids)
		live_list = []
		for id in ids: 
			obj = self.objects.get(id)
			if obj["allow_collisions"]: live_list.append(self.objects.get(id))
		return live_list
	
	def register_object(self, id, object):
		self.objects[id] = object
	
	def prevent_freeze(self):
		self._freezelock = True
		
	def move(self, *args, **kwargs):
		super().move(*args, **kwargs)
		
	def setCorner1(self, point):
		self.corner1 = point
		
	def setCorner2(self, point):
		self.corner2 = point
		
	def get_bbox(self):
		if not self._updated: self.master.master.update(); self._updated = True
		x1, y1 = self.winfo_x(), self.winfo_y()
		x2, y2 = x1+self.winfo_width(), y1+self.winfo_height()
		return (x1, y1, x2, y2)
		
	def bind(self, event, func):
		self.master.master.event_manager.register_event(self, event, func)
		
class CanvasObject(tk.Frame):
	def __init__(self, master, canvas=None, *args, **kwargs):
		super(CanvasObject, self).__init__(master)
		self.canvas = self.master.canvas if not canvas else canvas
		self.args, self.kwargs = args, kwargs
		self._event_wrappers = {}
		self._ref = None
		self.tags = {}
		
	def __getitem__(self, key):
		return self.tags.get(key)
	
	def __setitem__(self, key, value):
		self.tags[key] = value
		
	def place(self, x, y, canvas=None):
		if canvas: self.canvas = canvas
		self.center = Point2D(x, y)
		self.x, self.y = x, y
		self._ref = self.draw(self.args, self.kwargs)
		
	def draw(self, *args, **kwargs):
		raise NotImplementedError
		
	def bind(self, ref, func):
		if ref in Events.ALL: self.canvas.master.window.event_manager.register_event(self, ref, func)
		else: self._event_wrappers[ref] = func
		
	def remove(self):
		self.canvas.delete(self._ref)
		self._ref = None
		
	def get_collisions(self, x1, y1, x2, y2):
		all_collisions = list(self.canvas.find_overlapping(self.corner1.x, self.corner1.y, self.corner2.x, self.corner2.y))
		if len(all_collisions) == 1: return []
		try: all_collisions.pop(all_collisions.index(self._ref))
		except: pass
		return self.canvas.identify(all_collisions)
	
	def get_bbox(self):
		return self.canvas.bbox(self._ref)
		
	def inWindow(self, x, y):
		nC = self.corner1.npXY(x, y)
		if not 0 < nC.x < self.master["width"]: return False
		if not 0 < nC.y < self.master["height"]: return False
		nC = self.corner2.npXY(x, y)
		if not 0 < nC.x < self.master["width"]: return False
		if not 0 < nC.y < self.master["height"]: return False
		return True
		
class PackableObject(CanvasObject):
	def __init__(self, master, w=None, h=None, *args, **kwargs):
		super(PackableObject, self).__init__(master, *args, **kwargs)
		self.packed = False
		if not master.canvas: self.canvas = Canvas(width=w, height=h)
		else: self.canvas = master.canvas; self.packed = True
		if not w or not h: raise PackableObjectArgumentError
		self.w = w
		self.h = h
		
	def pack(self):
		if not self.packed: self.canvas.pack(); self.packed = True
		self._ref = self.draw(self.args, self.kwargs)
	
class CollidableObject(CanvasObject):
	def __init__(self, master, allow_collisions=False, collision_wrapper=None, *args, **kwargs):
		super(CollidableObject, self).__init__(master, *args, **kwargs)
		self.collisions = []
		self.tags["allow_collisions"] = allow_collisions
		self._event_wrappers["collision_wrapper"] = lazylist(collision_wrapper)
		
	def color(self, color):
		self.canvas.itemconfig(self._ref, fill=color)
		self.tags["color"] = color	
		
	def _collide(self):
		if not self.collisions: return
		collision_wrapper = self._event_wrappers.get("collision_wrapper")
		if collision_wrapper:
			for wrapper in collision_wrapper: wrapper(self, self.collisions)
		
class CanvasText(CanvasObject):
	def __init__(self, master, text="", font="TkDefaultFont", size=9, italics=False, bold=False, *args, **kwargs):
		kwargs["text"] = text
		if italics: font += " italic"
		if bold: font += " bold"
		font += " " + str(size)
		kwargs["font"] = font
		
		super(CanvasText, self).__init__(master, *args, **kwargs)
		self.tags["text"] = text
		
		self.text = text
		self.italics = italics
		self.bold = bold
		self.size = size
		
	def draw(self, args, kwargs):
		x,y = self.x,self.y
		ref = self.canvas.create_text(x, y, *args, **kwargs)
		self.canvas.register_object(ref, self)
		return ref
		
	def setText(self, string):
		self.canvas.itemconfig(self._ref, text=string)	
		self.tags["text"] = string
		self.canvas.update()
		
class CanvasLabel(CanvasText):
	def __init__(self, master, border_width=0, padx=0, pady=0, *args, **kwargs):
		bg = kwargs.get("bg")
		if bg: kwargs.pop("bg")
		super(CanvasLabel, self).__init__(master, *args, **kwargs)
		self.bg = bg
		self.border_width=border_width
		self.padx = padx
		self.pady = pady
		
	def draw(self, args, kwargs):
		x,y = self.x,self.y
		ref = self.canvas.create_text(x, y, *args, **kwargs)
		if self.bg != "": 
			cbox = self.canvas.bbox(ref)
			bbox = (cbox[0]-self.padx, cbox[1]-self.pady, cbox[2]+self.padx, cbox[3]+self.pady)
			self.rect = Rectangle(self.master, *bbox, fill=self.bg, width=self.border_width);
		self.canvas.tag_raise(self.rect._ref, 'all')
		self.canvas.tag_raise(ref, 'all')
		self.canvas.register_object(ref, self)
		return ref
		
	def color(self, color):
		self.rect.color(color)
		
	def move(self, x, y):
		if self._ref == None: return
		self.x += x
		self.y += y
		self.rect.move(x, y)
		self.canvas.move(self._ref, x, y)
		
	def move_to(self, x, y):
		distX = x - self.x
		distY = y - self.y
		self.x = x
		self.y = y
		self.rect.move_to(x, y)
		self.canvas.move(self._ref, distX, distY)
		
	def setText(self, string):
		super().setText(string)
		cbox = self.canvas.bbox(self._ref)
		bbox = (cbox[0]-self.padx, cbox[1]-self.pady, cbox[2]+self.padx, cbox[3]+self.pady)
		new_rect = Rectangle(self.master, *bbox, fill=self.bg, width=self.border_width);
		self.canvas.delete(self.rect._ref)
		self.rect = new_rect
		#self.canvas.tag_raise(self.rect._ref, 'all')
		self.canvas.tag_raise(self._ref, 'all')
		
class ProgressBar(PackableObject):
	def __init__(self, master, bg='', fill='', border_width=0, offset_x=3, offset_y=3, inner_width=0, progress=100, speed=0, *args, **kwargs):
		super(ProgressBar, self).__init__(master, *args, **kwargs)
		self.x = 0
		self.y = 0
		self.inner_width = inner_width
		self.bg = bg
		self.border_width = border_width
		self.fill = fill
		self.offset_x = offset_x
		self.offset_y = offset_y
		self.tags["progress"] = progress
		self.speed = speed

	def draw(self, args, kwargs):
		self.borderRect = Rectangle(self.master, self.x, self.y, w=self.w, h=self.h, canvas=self.canvas, width=self.border_width, fill=self.bg)
		self.innerRect = Rectangle(self.master, self.x-1+(self.offset_x/2), self.y-1+(self.offset_y/2), w=self.w+2-self.offset_x, h=self.h+2-self.offset_y, canvas=self.canvas, width=self.inner_width+2, fill=self.bg)
		self.aliveRect = Rectangle(self.master, self.x+(self.offset_x/2), self.y+(self.offset_y/2), w=((self.w-self.offset_x)*(self["progress"]/100)), h=self.h-self.offset_y, canvas=self.canvas, width=self.inner_width, fill=self.fill)
		self.canvas.tag_raise(self.borderRect._ref, 'all')
		self.canvas.tag_raise(self.innerRect._ref, 'all')
		self.canvas.tag_raise(self.aliveRect._ref, 'all')
		self.canvas.register_object(self.borderRect._ref, self)
		return self.borderRect._ref
		
	def smoothen(self, old_progress, progress):
		delta = progress - old_progress
		spd = (1/self.speed)*1000
		old_width = self.aliveRect.width
		for i in range(int(spd)):
			p = old_progress + delta*(i/spd)
			new_rect = Rectangle(self.master, self.x+(self.offset_x/2), self.y+(self.offset_y/2), w=((self.w-self.offset_x)*(p/100)), h=self.h-self.offset_y, canvas=self.canvas, width=self.inner_width, fill=self.fill)
			self.canvas.delete(self.aliveRect._ref)
			self.aliveRect = new_rect
		
	def setProgress(self, progress):
		old_progress = self["progress"]
		self.tags["progress"] = progress
		if self.speed:
			self.smoothen(old_progress, progress)
		else:
			new_rect = Rectangle(self.master, self.x+(self.offset_x/2), self.y+(self.offset_y/2), w=((self.w-self.offset_x)*(self["progress"]/100)), h=self.h-self.offset_y, canvas=self.canvas, width=self.inner_width, fill=self.fill)
			self.canvas.delete(self.aliveRect._ref)
			self.aliveRect = new_rect
		
	def __setitem__(self, key, value):
		if key == "progress": self.setProgress(value)
		else: super().__setitem__(key, value)
		
class Rectangle(CollidableObject):
	def __init__(self, master, x1, y1, x2=None, y2=None, w=None, h=None, *args, **kwargs):
		super(Rectangle, self).__init__(master, *args, **kwargs)
		if "canvas" in kwargs.keys(): kwargs.pop("canvas")
		if not x2 and not w: 
			if w != 0: raise RectangleArgumentError
		if not y2 and not h: 
			if h != 0: raise RectangleArgumentError
		if w != None: self.width = w; self.x2 = x1+w
		if h != None: self.height = h; self.y2 = y1+h
		if x2: self.x2 = x2; self.width = x2-x1
		if y2: self.y2 = y2; self.height = y2-y1
		self.x1 = x1
		self.y1 = y1
		self._ref = self.draw(args, kwargs)
	
	def draw(self, args, kwargs):
		ref = self.canvas.create_rectangle(self.x1, self.y1, self.x2, self.y2, *args, **kwargs)
		self.canvas.register_object(ref, self)
		return ref
		
	def move(self, x, y):
		if self._ref == None: return
		self.x1 += x; self.x2 += x; self.y1 += y; self.y2 += y
		if self.canvas._freezelock: return
		if self.tags["allow_collisions"]: self.collisions = self.get_collisions(self.x1, self.y1, self.x2, self.y2)
		self.canvas.move(self._ref, x, y)
		
	def move_to(self, x, y):
		distX = x - self.x1
		distY = y - self.y1
		self.move(distX, distY)
	
		
class Circle(CollidableObject):	
	def __init__(self, master, r, *args, **kwargs):
		super(Circle, self).__init__(master, *args, **kwargs)
		self.tags["color"] = kwargs.get("color")
		self.radius = r
	
	def move(self, x, y):
		if self._ref == None: return
		self.center.moveXY(x, y)
		self.corner1.moveXY(x, y)
		self.corner2.moveXY(x, y)
		self.x, self.y = self.center.x, self.center.y
		if self.canvas._freezelock: return
		if self.tags["allow_collisions"]: self.collisions = self.get_collisions(self.corner1.x, self.corner1.y, self.corner2.x, self.corner2.y); self._collide()
		self.canvas.move(self._ref, x, y)
		
	def move_to(self, x, y):
		distX = x - self.x
		distY = y - self.y
		self.move(distX, distY)
		
	def draw(self, args, kwargs):
		x,y,r = self.x,self.y,self.radius
		x0, y0, x1, y1 = x-r, y-r, x+r, y+r
		self.corner1 = Point2D(x0, y0)
		self.corner2 = Point2D(x1, y1)
		ref = self.canvas.create_oval(x0, y0, x1, y1, *args, **kwargs)
		self.canvas.register_object(ref, self)
		return ref
