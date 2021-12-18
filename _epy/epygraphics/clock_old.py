import time
import threading
from queue import Queue
import asyncio

def delayed_function(function, delay, args, kwargs):
	clock = Clock()
	clock.sleep(delay)
	function(*args, **kwargs)
	
def repeated_function(function, delay, max_iterations, args, kwargs):
	iternum, max = 0, max_iterations
	if not max_iterations: max = 1; iternum = -1;
	while iternum < max:
		time.sleep(delay)
		function(*args, **kwargs)
		if iternum >= 0: iternum += 1

class Clock():
	def __init__(self, delay=0, target_framerate=None, framerate_range=5, init_thread_clock=False):
		self.delay = delay
		self.target_framerate = target_framerate
		self.framerate_range_low = 0
		self.framerate_range_high = framerate_range
		
		self.last_tick = None
		self.current_tick = 0
		
		self.sleeping = {}
		self.mini_tasks = {}
		self._next_id = 0
		self.fps = 0
		
		self.threaded_clock = None
		if init_thread_clock: self.threaded_clock =  self._init_thread_clock()
		
	def _init_thread_clock(self):
		clock = ThreadClock(delay=self.delay, target_framerate=self.target_framerate, framerate_range=self.framerate_range_high, daemon=True)
		return clock
		
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
		
	async def _asyncsleep(self, delay): #Internal function	
		start_time = time.time()
		while time.time() - start_time < delay: await asyncio.sleep(0)
		return
		
	def sleep(self, delay):
		start_time = time.time()
		while time.time() - start_time < delay: time.sleep(0)
		return
		
	def addThread(self, thread, function):
		if not self.threaded_clock: self.threaded_clock = self._init_thread_clock()
		self.threaded_clock.addThread(thread, function)
		
	def removeThread(self, thread):
		self.threaded_clock.removeThread(thread)
		
	def unboundsleep(self, call, delay):
		if not call in self.sleeping.keys(): self.sleeping[call] = [time.time(), delay]
		current = self.sleeping[call]
		if time.time() - current[0] < current[1]: return False
		self.sleeping.pop(call)
		return True
		
	def schedule_once(self, function, delay, *args, **kwargs):
		thread = threading.Thread(target=delayed_function, args=(function, delay, args, kwargs), daemon=True)
		thread.start()
		
	def schedule_interval(self, function, interval, *args, **kwargs):
		max_iterations = kwargs.get("max_iterations")
		mini_clock_thread = threading.Thread(target=repeated_function, args=(function, interval, max_iterations, args, kwargs), daemon=True)
		mini_clock_thread.start()
		self.mini_tasks[self._next_id] = mini_clock_thread
		self._next_id += 1
		return self._next_id - 1
		
	def setFramerate(self, framerate):
		self.target_framerate = framerate
		if self.threaded_clock: self.threaded_clock.setFramerate(framerate)
		
	def setRange(self, rangeHigh):
		self.framerate_range_high = rangeHigh
		if self.threaded_clock: self.threaded_clock.setRange(rangeHigh)
		
	def ping(self, origin, ctime):
		if not self.threaded_clock: return
		self.threaded_clock.ping(origin, ctime)
		
	def terminate(self):
		if self.threaded_clock: self.threaded_clock.terminate()
			
	def run_secondary_clock(self):
		if not self.threaded_clock: self.threaded_clock = self._init_thread_clock()
		self.threaded_clock.start()
		
class ThreadClock(threading.Thread):
	def __init__(self, delay=0, reference="Canvas", target_framerate=None, framerate_range=5, init_thread_clock=False, *args, **kwargs):
		super(ThreadClock, self).__init__(*args, **kwargs)
		self.threads = {}
		self.temp_threads = {}
		self.trashcan = []
		self.root = True
		self.delay = int(delay)
		self.target_framerate = target_framerate
		self.framerate_range_low = 0
		self.framerate_range_high = framerate_range
		
		self.reference = reference
		
		self.last_tick = None
		self.current_tick = 0
		
		self.sleeping = {}
		self.fps = 0
		
	async def _asyncsleep(self, delay): #Internal function	
		start_time = time.time()
		while time.time() - start_time < delay: await asyncio.sleep(0)
		return
		
	def sleep(self, delay):
		asyncio.run(self._asyncsleep(delay))
		return
		
	def ping(self, origin, ctime):
		if origin == self.reference: self.time_queue.put(ctime)
		
	def setFramerate(self, framerate):
		self.target_framerate = framerate
		
	def setRange(self, rangeHigh):
		self.framerate_range_high = rangeHigh
		
	def setDelay(self, delay):
		self.delay = delay
	
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
		if framerate_diff < self.framerate_range_low: self.delay -= 0.0001
		if self.delay < 0: self.delay = 0
		
	def addThread(self, thread, func):
		self.temp_threads[thread] = func
		
	def removeThread(self, thread):
		self.trashcan.append(thread)
		
	def terminate(self):
		self.root = False
		
	def run(self):
		while self.root:
			print("rawr")
			self.tick()
			if self.temp_threads: self.threads = {**self.threads, **self.temp_threads}; self.temp_threads = {}
			trash = list(self.trashcan); self.trashcan = []
			for thread in trash: self.threads.pop(thread); self.trashcan = []
			for thread in self.threads.keys(): self.threads[thread]()