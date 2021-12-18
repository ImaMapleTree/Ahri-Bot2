from playsound import playsound
import threading
from queue import Queue
import time
import os

def sound_base_path(path):
	sounds._setpath(path)

class SoundManager():
	def __init__(self):
		self.queue = Queue()
		self.soundthread = SoundThread(self.queue, daemon=True)
		self.soundthread.start()
		self.soundroot = ''
		
	def _setpath(self, path):
		self.soundroot = path
		
	def play(self, source):
		self.queue.put(source)

class SoundThread(threading.Thread):
	def __init__(self, queue=Queue(), *args, **kwargs):
		super(SoundThread, self).__init__(*args, **kwargs)
		self._thread = threading.current_thread()
		self._condition = threading.Condition()
		self.queue = queue
		
	def run(self):
		while True:
			time.sleep(0.01)
			try:
				sound = self.queue.get_nowait()
				if sound != None: playsound(sound)
			except: pass
				
				
def qsound(source):
	global sounds
	sounds.play(os.path.join(sounds.soundroot, source))
	
global sounds
sounds = SoundManager()