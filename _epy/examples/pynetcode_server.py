import PyNetcode
import time
import cv2
from mss import mss
from PIL import Image
from zlib import decompress
import numpy as np
from multiprocessing import Queue

class ServerBridge():
	def __init__(self, queue):
		self.clients = {}
		self.listener = PyNetcode.ConnectionListener(ip="192.168.1.74", byte_limit=120000, client_data_timeout=0.000001, daemon=True)
		self.listener.registerListener("WinSize", self.onWinSize)
		self.listener.registerListener("Screenshare", self.onScreenshot)
		self.listener.registerListener("connect", self.onConnect)
		self.queue = queue
	
	def onWinSize(self, _, data):
		self.clients[data._id] = (int(data.args(0)), int(data.args(1)))
			
	def onScreenshot(self, _, data):
		pixels = decompress(data.args(0))
		img =  Image.frombytes("RGB", self.clients[data._id], pixels, "raw", "BGRX")
		cv2.imshow("test", np.array(img))
		if cv2.waitKey(25) & 0xFF == ord('q'):
			cv2.destroyAllWindows()
			
	def onConnect(self, _, data):
		print(data)
	
	def run(self):
		self.listener.start()
		

queue = Queue()
test = ServerBridge(queue)
test.run()
time.sleep(10000)