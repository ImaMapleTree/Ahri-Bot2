from _epy.epygraphics.clock import *
from _epy.epygraphics.canvas import *
from _epy.epygraphics.base import *
from _epy.epygraphics.exceptions import *
from _epy.epygraphics.events import *
from _epy.epygraphics.opengl import *
import tkinter as tk
from tkinter.ttk import Progressbar
import threading
import time

def WaitUntilInitialized(window):
	while not window._initialized: time.sleep(0.01)
	return True
		
class Fodder():
	pass

class FutureWidget(Fodder):
	def __init__(self, master, *args, **kwargs):
		self.args, self.kwargs = args, kwargs
		self.future_calls = []
		self.master = master
	
	def place(self, *args, **kwargs):
		self.future_calls.append([self.place, args, kwargs])
		
	def pack(self, *args, **kwargs):
		self.future_calls.append([self.pack, args, kwargs])
		
	def grid(self, *args, **kwargs):
		self.future_calls.append([self.grid, args, kwargs])
	
	def bind(self, *args, **kwargs):
		self.future_calls.append([self.bind, args, kwargs])
	
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
	def __init__(self, window, *args, **kwargs):
		super(WindowFrame, self).__init__(*args, **kwargs)
		self.canvas = None
		self.window = window
	
	def attachCanvas(self, *args, **kwargs):
		self.canvas = Canvas(self, *args, **kwargs)
		self.canvas.pack()
		return self.canvas
		
	def attachClock(self, clock):
		self.clock = clock
		
	def get_bbox(self):
		x1, y1 = self.winfo_x(), self.winfo_y()
		x2, y2 = x1+self["width"], y1+self["height"]
		return (x1, y1, x2, y2)
		
	#def bind(self, event, func):
		#self.master.event_manager.register_event(self, event, func)

class WindowThread(threading.Thread):
	def __init__(self, window=None, *args, **kwargs):
		self.window = window
		super(WindowThread, self).__init__(*args, **kwargs)
		if not window: self.window = Window(delay_loop=True)
	
	def run(self):
		if self.window._initialized: raise RunningInstanceError
		self.window.initialize()
		
class Window():
	def __init__(self, width=50, height=50, SML = True, canvas=True, delay_loop=True, auto_start=True, init_thread_clock=True):
		self.width = width
		self.height = height
		self._initialized = False
		self._future_constructs = {}
		self.canvas = canvas
		self.clock = Clock(ITC=init_thread_clock)
		self.running = False
		self.looping = False
		self.auto_start = auto_start
		self.SML = SML
		if not delay_loop: self.initialize()
	
	def initialize(self):
		self.root = tk.Tk()
		self.mainframe = WindowFrame(self, master=self.root, width=self.width, height=self.height)
		self.mainframe["width"] = self.width
		self.mainframe["height"] = self.height
		self.mainframe.pack()
		
		if self.canvas: self.mainframe.attachCanvas(width=self.width, height=self.height)
		self.mainframe.attachClock(self.clock)
		
		self.event_manager = EventManager(self)
		
		self._initialized = True
		self._unpackConstructs()
		
		self.root.protocol("WM_DELETE_WINDOW", self._exit)
		if self.auto_start: self.clock.startTC()
			
		if self.SML:
			self.looping = True
			self.running = True
			self.root.mainloop()
		
	def __bool__(self):
		if self.looping:
			return self.running
		return True
		
	def _exit(self):
		self.clock.schedule_once(self.root.destroy, 0.001)
		time.sleep(0.1)
		CLOCKS_ENABLED = False
		for clock in THREAD_CLOCKS:
			clock.terminate()
		try:
			if self.mainframe.canvas: self.mainframe.canvas.prevent_freeze()
		except: pass
		self.clock.terminate()
		self.running = False
		
	def _packConstruct(self, func, master, args, kwargs):
		future_widget = FutureWidget(master, *args, **kwargs)
		self._future_constructs[future_widget] = [func, args, kwargs, master]
		return future_widget
		
	def _unpackConstructs(self):
		identified_constructs = []
		for construct in self._future_constructs.keys():
			construct_list = self._future_constructs.get(construct)
			identified_constructs.append([construct, construct_list[0](construct_list[3], *construct_list[1], **construct_list[2])])
			
		for alive in identified_constructs: alive[0].identify(alive[1])
		
	def createButton(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createButton, master, args, kwargs)
		parent = master if master else self.mainframe
		return tk.Button(parent, *args, **kwargs)
		
	def createScale(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createScale, master, args, kwargs)
		parent = master if master else self.mainframe
		return tk.Scale(parent, *args, **kwargs)
		
	def createCanvas(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createCanvas, master, args, kwargs)
		parent = master if master else self.mainframe
		return tk.Canvas(parent, *args, **kwargs)
		
	def createCircle(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createCircle, master, args, kwargs)
		parent = master if master else self.mainframe
		return Circle(parent, *args, **kwargs)
		
	def createRectangle(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createRectangle, master, args, kwargs)
		parent = master if master else self.mainframe
		return Rectangle(parent, *args, **kwargs)
		
	def createText(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createText, master, args, kwargs)
		parent = master if master else self.mainframe
		return CanvasText(parent, *args, **kwargs)
		
	def createLabel(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createLabel, master, args, kwargs)
		parent = master if master else self.mainframe
		if kwargs.get("canvas"): kwargs.pop("canvas"); return self.createCLabel(*args, **kwargs)
		return tk.Label(parent, *args, **kwargs)
		
	def createCLabel(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createCLabel, master, args, kwargs)
		parent = master if master else self.mainframe
		return CanvasLabel(parent, *args, **kwargs)
		
	def createFrame(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createFrame, master, args, kwargs)
		parent = master if master else self.mainframe
		if kwargs.get("OpenGL"): kwargs.pop("OpenGL"); return GLTKFrame(parent, *args, **kwargs)
		return tk.Frame(parent, *args, **kwargs)
		
	def createProgressbar(self, *args, **kwargs):
		master = kwargs.get("master")
		if master: kwargs.pop("master")
		if not self._initialized: return self._packConstruct(self.createProgressbar, master, args, kwargs)
		parent = master if master else self.mainframe
		return ProgressBar(parent, *args, **kwargs)
		
	def getCanvas(self):
		return self.mainframe.canvas
		
	def get_bbox(self):
		return (0, 0, self.width, self.height)
		
	def bind(self, event, func):
		self.root.bind(event, func)
		
	def register_event(self, event, func):
		#self.root.bind(event, func)
		self.event_manager.register_event(event, self.root, func)	
		
	def wait(self):
		while self.running: time.sleep(1)
			
	def Events(self):
		return self.event_manager
			
	def mainloop(self):
		if self.running: return
		self.running = True
		#self.event_manager.calculate_offset()
		self.root.mainloop()