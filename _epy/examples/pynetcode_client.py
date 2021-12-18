import numpy as np
import cv2
from mss import mss
from PIL import Image
import time
import threading
from zlib import compress
from _epy import PyNetcode

class ScreenShare(threading.Thread):
	def __init__(self, sender, *args, **kwargs):
		super(ScreenShare, self).__init__()
		self._sender = sender
		self._sct = mss()
		
	def run(self):
		times = 0
		start_time = time.time()
		while True:
			time.sleep(0.025)
			sct_img = self._sct.grab(self._sender._bbox).bgra
			compressed = compress(sct_img, 9)
			self._sender.client.sendData(PyNetcode.NetByte("Screenshare", 1, compressed))

class ScreenSender():
	def onConnect(self, _):
		test = PyNetcode.NetByte("WinSize", 0, self._width, self._height)
		self.client.sendData(test)
	
	def __init__(self, width=960, height=560):
		self.client = PyNetcode.ClientConnection(ip="107.217.234.59", daemon=True)
		self.client.start()
		self.client.registerListener("connect", self.onConnect)
		self._width = width
		self._height = height
		self._bbox = {'top': 0, 'left': 0, 'width': width, 'height': height}
		
		
		
		
		
		
		

test = ScreenSender()
time.sleep(5)
print("Starting share thread!")
thread = ScreenShare(test, daemon=True)
thread.start()