import pynput
from pynput.keyboard import Key as PPK
from _epy.quicktools import redict
import time
from enum import Enum

global EPYINPUT_KEY_DICTIONARY
global EPYINPUT_SHIFTED_KEYS
EPYINPUT_KEY_DICTIONARY = redict({PPK.alt: 18, PPK.alt_l: 18, PPK.alt_r: 18, PPK.alt_gr: 18, PPK.backspace: 8, PPK.caps_lock: 20, PPK.cmd: 91, PPK.cmd_l: 91, PPK.cmd_r: 91, PPK.ctrl: 17, PPK.ctrl_l: 17, PPK.ctrl_r: 17, PPK.delete: 46, PPK.down: 40, PPK.end: 35, PPK.enter: 13, PPK.esc: 27, PPK.f1: 112, PPK.f2: 113, PPK.f3: 114, PPK.f4: 115, PPK.f5: 116, PPK.f6: 117, PPK.f7: 118, PPK.f8: 119, PPK.f9: 120, PPK.f10: 121, PPK.f11: 122, PPK.f12: 123, PPK.home: 36, PPK.left: 37, PPK.page_down: 34, PPK.page_up: 33, PPK.right: 39, PPK.shift: 16, PPK.shift_l: 16, PPK.shift_r: 16, PPK.space: 32, PPK.tab: 9, PPK.up: 38, PPK.insert: 45, PPK.menu: 93, PPK.num_lock: 144, PPK.pause: 19, PPK.scroll_lock: 145})
EPYINPUT_SHIFTED_KEYS = ["!", "@", "#", "$", "%", "^", "&", "*", "(", ")", "~", "_", "+", "{", "}", "\\", "|", ":", '"', "<", ">", "?"]

class Key(PPK, Enum):
	pass

class ComboKey():
	def __init__(self, key):
		global EPYINPUT_KEY_DICTIONARY
		global EPYINPUT_SHIFTED_KEYS
		self._KEY_DICTIONARY = EPYINPUT_KEY_DICTIONARY
		self._SHIFTED_KEYS = EPYINPUT_SHIFTED_KEYS
		self.nested = key
		self.char = None
		self._assign(key)
		
	def getChar(self, noneType=None):
		if not self.char: return noneType
		return self.char
		
	def _assign(self, key):
		self.keys = []
		try: 
			self.keycode = key.vk
			self.char = key.char
			if self.char in self._SHIFTED_KEYS: self.keys.append(16)
			elif self.char.isupper(): self.keys.append(16)
		except: self.keycode = self._KEY_DICTIONARY.get(key)
		if key == PPK.space: self.char = " "
		self.keys.append(self.keycode)
		self.name = (str(self.nested).replace("Key.", "").replace("'", "")).lower()
			
	def __repr__(self):
		return self.name
		
class Manager(pynput.keyboard.Listener):
	def __init__(self, *args, **kwargs):
		global EPYINPUT_KEY_DICTIONARY
		self._KEY_DICTIONARY = EPYINPUT_KEY_DICTIONARY
		self._ONPRESS_WRAPPER = kwargs.get("on_press")
		self._ONRELEASE_WRAPPER = kwargs.get("on_release")
		kwargs["on_press"] = self._ONPRESS
		kwargs["on_release"] = self._ONRELEASE
		
		self._Controller = pynput.keyboard.Controller()
		self._BLOCKED = False
		super(Manager, self).__init__(*args, **kwargs)
	
	def _ONPRESS(self, key):
		if self._BLOCKED: return
		if self._ONPRESS_WRAPPER: self._ONPRESS_WRAPPER(ComboKey(key))
		
	def _ONRELEASE(self, key):
		self._UNBLOCK()
		if self._BLOCKED: return
		if self._ONRELEASE_WRAPPER: self._ONRELEASE_WRAPPER(ComboKey(key))
		
	def _UNBLOCK(self):
		if time.time() - self._BLOCKED > 0.05: self._BLOCKED = False
		
	def type(self, string, blocking=True):
		if blocking: self._BLOCKED = time.time()
		self._Controller.type(string)
		
	def tap(self, key, blocking=True):
		if blocking: self._BLOCKED = time.time()
		if type(key) == type(PPK.backspace) or type(key) == type(""): self._Controller.tap(key)
		elif type(key) == type(0):
			real_key = self._KEY_DICTIONARY.getKey(key)
			if not real_key: real_key = PPK.from_vk(key)
			self._Controller.tap(real_key)
		
	def press(self, key, blocking=True):
		if blocking: self._BLOCKED = time.time()
		if type(key) == type(PPK.backspace) or type(key) == type(""): self._Controller.press(key)
		elif type(key) == type(0):
			real_key = self._KEY_DICTIONARY.getKey(key)
			if not real_key: real_key = PPK.from_vk(key)
			self._Controller.press(real_key)
	
	def release(self, key, blocking=True):
		if blocking: self._BLOCKED = time.time()
		if type(key) == type(PPK.backspace) or type(key) == type(""): self._Controller.release(key)
		elif type(key) == type(0):
			real_key = self._KEY_DICTIONARY.getKey(key)
			if not real_key: real_key = PPK.from_vk(key)
			self._Controller.release(real_key)