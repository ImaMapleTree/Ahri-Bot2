from _epy.epygraphics.exceptions import *
from _epy.epygraphics.epyinput import *
from _epy.epygraphics.base import *
from _epy.epygraphics.canvas import *
from _epy.epygraphics.clock import *
import _epy.epygraphics.canvas as CV
from pynput.mouse import Listener, Button
import threading
	
class BaseEvent():
	def __init__(self, source):
		self.timestamp = Timestamp()
		self.source = source
		
class KeyboardReleaseEvent(BaseEvent):		
	def __init__(self, source, key):
		super(KeyboardReleaseEvent, self).__init__(source)
		self.key = key
		
	def getKey(self):
		return self.key	
		
class KeyboardPressEvent(BaseEvent):
	def __init__(self, source, key):
		super(KeyboardPressEvent, self).__init__(source)
		self.key = key
		
	def getKey(self):
		return self.key
		
class MouseEvent(BaseEvent):
	def __init__(self, source, x, y, x2, y2):
		super(MouseEvent, self).__init__(source)
		self.screen_pos = (x, y)
		self.screen_x = x
		self.screen_y = y
		self.window_x = x2
		self.window_y = y2
		self.window_pos = (x2, y2)
		if source:
			bbox = source.get_bbox()
			x3, y3 = bbox[0], bbox[1]
		else:
			x3, y3 = 0, 0
		self.x = x2 - x3
		self.y = y2 - y3
		self.pos = (self.x, self.y)
	
	def getPos(self):
		return self.pos
		
class MouseLeftEvent(MouseEvent):
	def __init__(self, source, x, y, x2, y2):
		super(MouseLeftEvent, self).__init__(source, x, y, x2, y2)
		self.button = Button.left
		
class MouseRightEvent(MouseEvent):
	def __init__(self, source, x, y, x2, y2):
		super(MouseRightEvent, self).__init__(source, x, y, x2, y2)
		self.button = Button.left
		
class MouseMoveEvent(MouseEvent):
	def __init__(self, source, x, y, x2, y2):
		super(MouseMoveEvent, self).__init__(source, x, y, x2, y2)
	
class MouseDragEvent(MouseEvent):
	def __init__(self, source, x, y, x2, y2):
		super(MouseDragEvent, self).__init__(source, x, y, x2, y2)
			
		
class EventManager():
	def __init__(self, window=None, active_limit=None):
		self.window = window
		#self._event_registry = {Events.KEYBOARD_PRESS:[], Events.KEYBOARD_RELEASE:[], Events.MOUSE_LEFT_CLICK:[], Events.MOUSE_RIGHT_CLICK:[], Events.MOUSE_MOVE:[], Events.MOUSE_DRAG:[]}
		self.bindings = {Events.MOUSE_LEFT_CLICK: ["<Button-1>", self.MOUSE_LEFT_CLICK], Events.MOUSE_MOVE: ["<Motion>", self.MOUSE_MOVE], Events.MOUSE_DRAG: ["<B1-Motion>", self.MOUSE_DRAG], Events.KEYBOARD_PRESS: ["<Key>", self.KEYBOARD_PRESS]}
		self._event_registry = {}
		self.MOUSE_PRESSED = False
		
	def call_events(self, func, event):
		func(event)
		
	def register_event(self, event, w, func):
		if w not in self._event_registry.keys(): self._event_registry[event] = []
		self._event_registry[event].append(func)
		w.bind(self.bindings[event][0], self.bindings[event][1])
	
	def MOUSE_LEFT_CLICK(self, event):
		self.MOUSE_PRESSED = True
		[self.call_events(func, event) for func in self._event_registry[Events.MOUSE_LEFT_CLICK]]
		
	def MOUSE_MOVE(self, event):
		[self.call_events(func, event) for func in self._event_registry[Events.MOUSE_MOVE]]
		
	def MOUSE_DRAG(self, event):
		self.MOUSE_PRESSED = True
		[self.call_events(func, event) for func in self._event_registry[Events.MOUSE_DRAG]]
	
	def KEYBOARD_PRESS(self, event):
		[self.call_events(func, event) for func in self._event_registry[Events.KEYBOARD_PRESS]]
			
class Events:
	KEYBOARD_PRESS = KeyboardPressEvent
	KEYBOARD_RELEASE = KeyboardPressEvent
	MOUSE_LEFT_CLICK = MouseLeftEvent
	MOUSE_RIGHT_CLICK = MouseRightEvent
	MOUSE_MOVE = MouseMoveEvent
	MOUSE_DRAG = MouseDragEvent
	ALL = [KEYBOARD_PRESS, KEYBOARD_RELEASE, MOUSE_LEFT_CLICK, MOUSE_RIGHT_CLICK, MOUSE_MOVE, MOUSE_DRAG]