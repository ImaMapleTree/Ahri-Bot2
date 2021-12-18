import tkinter as tk
from tkinter import messagebox
import multiprocessing
import threading
import time
import sys
from numba import jit

def delayed_function(delay, function, args, kwargs):
	clock = Clock()
	clock.sleep(delay)
	function(*args, **kwargs)

class ThreadClock(threading.Thread):
	def __init__(self, delay=0, *args, **kwargs):
		super(ThreadClock, self).__init__()
		self.threads = {}
		self.delay = delay
		
	def sleep(self, delay):
		sleep_start = time.time()
		while time.time() - sleep_start < delay: time.sleep(0)
		return
		
	def addThread(self, thread, function):
		self.threads[thread] = function
		
	def run(self):
		while True:
			self.sleep(self.delay)
			for thread in self.threads.keys():
				self.threads[thread]()

class Clock():
	def __init__(self, delay=0, target_framerate=None, framerate_range=5):
		self.delay = delay
		self.target_framerate = target_framerate
		self.framerate_range_low = target_framerate
		self.framerate_range_high = framerate_range
		
		self.last_tick = None
		self.current_tick = 0
		
		self.sleeping = {}
		self.fps = 0
		
	def tick(self, delay=0):
		if not self.last_tick: self.last_tick = time.time()
		self.sleep(self.delay+delay)
		self.current_tick = time.time()
		try: self.fps = 1/(self.current_tick-self.last_tick)
		except: self.fps = 1024
		self.last_tick = time.time()
		
		if not self.target_framerate: return
		framerate_diff = self.fps-self.target_framerate
		if framerate_diff > self.framerate_range_high: self.delay += 0.0001
		elif framerate_diff < self.framerate_range_low: self.delay -= 0.0001
		if self.delay < 0: self.delay = 0
		
	def sleep(self, delay):
		sleep_start = time.time()
		while time.time() - sleep_start < delay: time.sleep(0)
		return
		
	def unboundsleep(self, call, delay):
		if not call in self.sleeping.keys(): self.sleeping[call] = [time.time(), delay]
		current = self.sleeping[call]
		if time.time() - current[0] < current[1]: return False
		self.sleeping.pop(call)
		return True
		
	def schedule(self, delay, function, *args, **kwargs):
		thread = threading.Thread(target=delayed_function, args=(delay, function, args, kwargs), daemon=True)
		thread.start()
		
	def setFramerate(self, framerate):
		self.target_framerate = framerate
		self.framerate_range_low = framerate

class RunningInstanceError(Exception):
	def __init__(self):
		super().__init__("Instance is already running in another thread!")

def WinWait(window):
	while not window._initialized: pass
	time.sleep(0.005)
	return True

class Point2D():
	def __init__(self, x, y):
		self.LPOINT = [x, y]
		self.x = x
		self.y = y
		
	def __repr__(self):
		return f"Point2D(x={round(self.x, 2)}, y={round(self.y, 2)})"
	
	def __getitem__(self, key):
		return self.LPOINT[key]
	
	def __setitem__(self, key, value):
		nkey = 0
		skey = key.lower()
		if skey == "x": nkey = 0; self.x = value
		elif skey == "y": nkey = 1; self.y = value
		else: raise ValueError
		self.LPOINT[nkey] = value
		
	def moveX(self, x):
		self.x += x
		self.LPOINT[0] += x
		
	def moveY(self, y):
		self.y += y
		self.LPOINT[1] += y
		
	def moveXY(self, x, y):
		self.moveX(x)
		self.moveY(y)
		
	def npX(self, x):
		return Point2D(self[0] + x, self.y)
	
	def npY(self, y):
		return Point2D(self.x, self[1] + y)
	
	def npXY(self, x, y):
		return Point2D(self[0] + x, self[1] + y)
		
class CanvasText():
	pass
		
class Circle(tk.Frame):	
	def __init__(self, master, r, allow_collision=False, collisionEvent=None, *args, **kwargs):
		super(Circle, self).__init__(master)
		self.args, self.kwargs = args, kwargs
		self.radius = r
		self.allow_collision = allow_collision
		self.collisions = []
		self.collisionEvent = collisionEvent
		self.tags = {}
		
	def get_collisions(self, x1, y1, x2, y2):
		all_collisions = list(self.canvas.find_overlapping(self.corner1.x, self.corner1.y, self.corner2.x, self.corner2.y))
		if len(all_collisions) == 1: return []
		try: all_collisions.pop(all_collisions.index(self._circle))
		except: pass
		return all_collisions
		
	def move(self, x, y, _=None):
		self.center.moveXY(x, y)
		self.corner1.moveXY(x, y)
		self.corner2.moveXY(x, y)
		self.x, self.y = self.center.x, self.center.y
		if self.canvas._freezelock: return
		if self.allow_collision: self.collisions = self.get_collisions(self.corner1.x, self.corner1.y, self.corner2.x, self.corner2.y); self._collide()
		self.canvas.move(self._circle, x, y)
		
	def place(self, x, y):
		self.canvas = self.master.canvas
		self.center = Point2D(x, y)
		self.x, self.y = x, y
		self._circle = self.draw(self.args, self.kwargs)
		
	def draw(self, args, kwargs):
		x,y,r = self.x,self.y,self.radius
		x0, y0, x1, y1 = x-r, y-r, x+r, y+r
		self.corner1 = Point2D(x0, y0)
		self.corner2 = Point2D(x1, y1)
		circle = self.canvas.create_oval(x0, y0, x1, y1, *args, **kwargs)
		self.canvas.register_object(circle, self)
		return circle
		
	def color(self, color):
		self.canvas.itemconfig(self._circle, fill=color)
		self.tags["color"] = color
		
	def inWindow(self, x, y):
		nC = self.corner1.npXY(x, y)
		if not 0 < nC.x < self.master["width"]: return False
		if not 0 < nC.y < self.master["height"]: return False
		nC = self.corner2.npXY(x, y)
		if not 0 < nC.x < self.master["width"]: return False
		if not 0 < nC.y < self.master["height"]: return False
		return True
		
	def _collide(self):
		if self.collisions == []: return
		if self.collisionEvent: self.collisionEvent(self, self.canvas.identify(self.collisions))

class Fodder():
	pass

class FutureWidget(Fodder):
	def __init__(self, *args, **kwargs):
		self.args, self.kwargs = args, kwargs
		self.future_calls = []
	
	def place(self, *args, **kwargs):
		self.future_calls.append([self.place, args, kwargs])
		
	def pack(self, *args, **kwargs):
		self.future_calls.append([self.pack, args, kwargs])
		
	def grid(self, *args, **kwargs):
		self.future_calls.append([self.grid, args, kwargs])
	
	def identify(self, widget):
		need_executions = self.future_calls
		args = self.args
		kwargs = self.kwargs
		self.__class__.__bases__ = (tk.Frame,)
		self.__class__ = widget.__class__
		self._w = widget._w
		self.__init__(widget.master, *self.args, **self.kwargs)
		for executable in need_executions: executable[0](*executable[1], **executable[2])

class WindowFrame(tk.Frame):
	def __init__(self, *args, **kwargs):
		super(WindowFrame, self).__init__(*args, **kwargs)
	
	def attachCanvas(self, *args, **kwargs):
		self.canvas = Canvas(self, *args, **kwargs)
		self.canvas.pack()
		
	def attachClock(self, clock):
		self.clock = clock



class Canvas(tk.Canvas):
	def __init__(self, *args, **kwargs):
		super(Canvas, self).__init__(*args, **kwargs)
		self._freezelock = None
		self.objects = {}
	
	def identify(self, ids):
		if type(ids) == type(int): return self.objects.get(ids)
		live_list = []
		for id in ids: live_list.append(self.objects.get(id))
		return live_list
	
	def register_object(self, id, object):
		self.objects[id] = object
	
	def prevent_freeze(self):
		self._freezelock = True
		
	def move(self, *args, **kwargs):
		super().move(*args, **kwargs)

class WindowThread(threading.Thread):
	def __init__(self, window=None, *args, **kwargs):
		self.window = window
		super(WindowThread, self).__init__(*args, **kwargs)
		if not window: self.window = Window(delay_loop=True)
	
	def run(self):
		if self.window._initialized: raise RunningInstanceError
		self.window.initialize()
		
class Window():
	def __init__(self, width=50, height=50, delay_loop=True):
		self.width = width
		self.height = height
		self._initialized = False
		self._future_constructs = {}
		if not delay_loop: self._initialize()
		self.clock = Clock()
			
	def initialize(self):
		self.root = tk.Tk()
		self.mainframe = WindowFrame(master=self.root, width=self.width, height=self.height)
		self.mainframe["width"] = self.width
		self.mainframe["height"] = self.height
		self.mainframe.pack()
		
		self.mainframe.attachCanvas(width=self.width, height=self.height)
		self.mainframe.attachClock(self.clock)
		
		self._initialized = True
		self._unpackConstructs()
		
		self.root.protocol("WM_DELETE_WINDOW", self._exit)
		self.root.mainloop()
		
	def _exit(self):
		self.mainframe.canvas.prevent_freeze()
		self.clock.schedule(0.01, self.root.destroy)
		
	def _packConstruct(self, func, args, kwargs):
		future_widget = FutureWidget(*args, **kwargs)
		self._future_constructs[future_widget] = [func, args, kwargs]
		return future_widget
		
	def _unpackConstructs(self):
		identified_constructs = []
		for construct in self._future_constructs.keys():
			construct_list = self._future_constructs.get(construct)
			identified_constructs.append([construct, construct_list[0](*construct_list[1], **construct_list[2])])
			
		for alive in identified_constructs: alive[0].identify(alive[1])
		
	def createButton(self, *args, **kwargs):
		if not self._initialized: return self._packConstruct(self.createButton, args, kwargs)
		return tk.Button(self.mainframe, *args, **kwargs)
		
	def createCanvas(self, *args, **kwargs):
		if not self._initialized: return self._packConstruct(self.createCanvas, args, kwargs)
		return tk.Canvas(self.mainframe, *args, **kwargs)
		
	def createCircle(self, *args, **kwargs):
		if not self._initialized: return self._packConstruct(self.createCircle, args, kwargs)
		return Circle(self.mainframe, *args, **kwargs)
		
	def createText(self, *args, **kwargs):
		if not self._initialized: return self._packConstruct(self.createText, args, kwargs)
		return CanvasText(self.mainframe, *args, **kwargs)