import time
import threading
import asyncio

THREAD_CLOCKS = []
CLOCKS_ENABLED = True

class ScheduledFunction(threading.Thread):
	def __init__(self, function, interval, max_iterations=None, *args, **kwargs):
		super(ScheduledFunction, self).__init__(daemon=True)
		self.wrapper = function
		self.interval = interval
		self.args = args
		self.kwargs = kwargs
		self.max_iterations = max_iterations
		self.iterations = 0
		if not max_iterations: self.max_iterations = 1; self.iterations = -1
		self.clock = Clock()
		self.running = False

	def terminate(self):
		self.max_iterations = -1

	def run(self):
		self.running = True
		while self.iterations < self.max_iterations:
			self.clock.sleep(self.interval)
			if CLOCKS_ENABLED: self.wrapper(*self.args, **self.kwargs)
			else: break
			if self.iterations >= 0: self.iterations += 1
		self.running = False

class ThreadClock(threading.Thread):
	def __init__(self, interval=0, target_fps=None, *args, **kwargs):
		super(ThreadClock, self).__init__(*args, **kwargs)
		self.delay = interval
		self.target_fps = target_fps
		self.running = False
		
		try: 
			self._loop = asyncio.get_running_loop()
		except: 
			self._loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self._loop)
		
		self._TEMP_DEPS = {}
		self._dependents = {}
		self._FOR_REM = []
		self._ABORT = False
		
		self._LOCKED = False
		self._HINGE = False
		
		self.last_tick = time.time()
		self.this_tick = time.time()
		self.last_fps = 1024
		
		self.ticks = 0
		
	def tick(self, delay=0):
		self._tick()
		self._update_memory()
		for dependent in self._dependents.keys():
			self._dependents[dependent]()
		self.ticks += 1
		
	def _tick(self, delay=0):
		self._sleep(self.delay+delay)
		self.this_tick = time.time()
		try: self.fps = 1/(self.this_tick-self.last_tick)
		except: self.fps = self.last_fps
		self.last_fps = self.fps
		self.last_tick = time.time()
		
		if not self.target_fps: return
		framerate_diff = self.fps-self.target_fps
		if framerate_diff > 3: self.delay += 0.0001
		if framerate_diff < 0: self.delay -= 0.0001
		if self.delay < 0: self.delay = 0
		
	async def _asyncsleep(self, delay): #Internal function	
		start_time = time.time()
		while time.time() - start_time < delay: print(" ", end="\r")
		return
		
	def _sleep(self, delay):
		#while self._loop.is_running: pass
		self._loop.run_until_complete(self._asyncsleep(delay))
		return
		
	def sleep(self, delay):
		asyncio.run(self._asyncsleep(delay))
		return
		
	def hinge(self):
		self._HINGE = True
		
	def lock(self, bool):
		self._LOCKED = bool

	def add_to_cycle(self, dependent, func):
		self._TEMP_DEPS[dependent] = func

	def remove_from_cycle(self, dependent):
		self._FOR_REM.append(dependent)

	def terminate(self):
		self._ABORT = True
		self.running = False
		
	def _update_memory(self):
		if self._TEMP_DEPS:
			self._dependents = {**self._dependents, **self._TEMP_DEPS}
			self._TEMP_DEPS = {}
		if self._FOR_REM:
			removal = list(self._FOR_REM)
			for item in removal:
				try: self._dependents.pop(item)
				except: pass
			self._FOR_REM = []

	def run(self):
		THREAD_CLOCKS.append(self)
		self.running = True
		while not self._ABORT:
			if not self._LOCKED: self.tick()
			else:
				print(" ", end="\r")
				if self._HINGE: self.tick()
				self._HINGE = False
			

class Clock():
	def __init__(self, interval=0, target_fps=None, ITC=False, RTC=False):
		self.delay = interval
		self.target_fps = target_fps
		
		self.tasks = {}
		self._nextTID = 0
		try: 
			self._loop = asyncio.get_running_loop()
		except: 
			self._loop = asyncio.new_event_loop()
			asyncio.set_event_loop(self._loop)
			
		self._TCLOCK = None
		if ITC: self._TCLOCK = self.getTC(interval, target_fps)
		if RTC: self._TCLOCK = self.getTC(); self._TCLOCK.start()
		
		self.fps = 0
		self.last_fps = 0
		self.last_tick = time.time()
			
	def tick(self, delay=0):
		self.sleep(self.delay+delay)
		self.this_tick = time.time()
		tick_time = self.this_tick - self.last_tick
		try: self.fps = 1/(tick_time)
		except: self.fps = self.last_fps
		self.last_fps = self.fps
		self.last_tick = time.time()
		
		if not self.target_fps: return
		framerate_diff = self.fps-self.target_fps
		if framerate_diff > 3: self.delay += 0.0001
		if framerate_diff < 0: self.delay -= 0.0001
		if self.delay < 0: self.delay = 0		
			
	async def _asyncsleep(self, delay): #Internal function
		start_time = time.time()
		while time.time() - start_time < delay: await asyncio.sleep(0)
		return
		
	def sleep(self, delay):
		self._loop.run_until_complete(self._asyncsleep(delay))
		return
		
	def accurate_sleep(self, delay):
		start_time = time.time()
		while time.time() - start_time < delay: time.sleep(0)
		return
		
	def getTC(self, *args, **kwargs):
		if self._TCLOCK: return self._TCLOCK
		kwargs["daemon"] = True
		return ThreadClock(*args, **kwargs)
		
	def add_to_cycle(self, dependent, func):
		if not self._TCLOCK: raise NotImplementedError
		self._TCLOCK.add_to_cycle(dependent, func)
	
	def remove_from_cycle(self, dependent):
		if not self._TCLOCK: raise NotImplementedError
		self._TCLOCK.remove_from_cycle(dependent)
		
	def schedule_once(self, function, delay, *args, **kwargs):
		thread = ScheduledFunction(function, delay, 1, *args, **kwargs)
		thread.start()
		
	def schedule_interval(self, function, interval, *args, **kwargs):
		max_iterations = kwargs.get("max_iterations")
		scheduled_task = ScheduledFunction(function, interval, max_iterations, *args, **kwargs)
		scheduled_task.start()
		self.tasks[self._nextTID] = scheduled_task
		self._nextTID += 1
		return self._nextTID - 1
		
	def terminate(self):
		TC = self.getTC()
		if TC.running: TC.terminate()
		
	def startTC(self):
		TC = self.getTC()
		if not TC.running: TC.start()