import traceback
import os
import time
from datetime import date, datetime
import sys

def shorten_source(source):
	i = source.rfind("\\")
	if i == -1: return source
	return source[i+1:]
	
def get_timestamp():
	return datetime.now().strftime("%I:%M.%S")
	
class Logger():
	_MODES = ["include", "exclude", "silent"]
	
	def __init__(self, dir="logs", filename=None, function_mode="exclude", module_mode="exclude", functions=[], modules=[], trace_func=None, silent=False, timestamps=False):
		self.started = False
		if function_mode not in Logger._MODES: raise AssertionError
		self.function_mode = function_mode
		
		if module_mode not in Logger._MODES: raise AssertionError
		self.module_mode = module_mode
		
		if silent: function_mode = "silent"; module_mode = "silent"
		if trace_func: self.trace_func=trace_func
		self.functions = ["flag"] + functions if function_mode == "include" else ["write", "output"] + functions
		self.modules = modules
		self.trackers = []
		try: os.mkdir(dir)
		except: pass
		self.dir = dir
		self.filename = filename
		self.outpath = None
		self.outfile = None
		if self.filename:
			self.outpath = os.path.join(self.dir, self.filename)
			self.outfile = open(self.outpath, "w+")
		self.timestamps = timestamps
		self.out_functions = [self.output, self.no_module_output, self.no_function_output]
		
	def add_filter(self, type="function", name=None):
		if lower(type) == "function": self.functions.append(name)
		elif lower(type) == "module": self.modules.append(name)
	
	def trace_func(self, frame, event, arg):
		if not self.started:
			self.started = True
			if not self.filename:
				today = date.today()
				name = today.strftime("%Y-%m-%d"); i = 1
				while os.path.isfile(os.path.join(self.dir, f"{name}-{i}.txt")): i += 1
				self.filename = f"{name}-{i}.txt"
			self.outpath = os.path.join(self.dir, self.filename)
			self.outfile = open(self.outpath, "w+")
		
		for tracker in self.trackers:
			if time.time() - tracker[2] > tracker[1]:
				var = tracker[0] if not callable(tracker[0]) else tracker[0](*tracker[3])
				print(f"[TRACKER]\n{var}\n[TRACKER]", file=self.outfile)
				tracker[2] = time.time()
			
		if self.module_mode == "silent" and self.function_mode == "silent": return
		if event != 'call': return
		co = frame.f_code
		func_name = co.co_name
		if self.function_mode == "exclude":
			if func_name in self.functions: return
		else:
			if func_name not in self.functions: return
		func_line_no = frame.f_lineno
		func_filename = shorten_source(co.co_filename)
		
		caller = frame.f_back
		if not caller: return
		caller_line_no = caller.f_lineno
		caller_filename = shorten_source(caller.f_code.co_filename)
		if self.module_mode == "exclude":
			if func_filename in self.modules: return
		else:
			if func_filename not in self.modules: return
		if self.module_mode == "silent":
			self.out_functions[1](func_name, func_line_no, func_filename, caller_line_no, caller_filename)
		elif self.function_mode == "silent":
			self.out_functions[2](func_name, func_line_no, func_filename, caller_line_no, caller_filename)
		else:
			self.out_functions[0](func_name, func_line_no, func_filename, caller_line_no, caller_filename)
		return
		
	def track(self, object, interval=0.1, *args):
		self.trackers.append([object, interval, time.time(), args])
		
	def flag(self, *info):
		tss = ""
		if self.timestamps: tss = f"[{get_timestamp()}] "
		info_string = ' | '.join([str(obj) for obj in info])
		if self.module_mode == "silent" and self.function_mode == "silent":
			print(f"{tss}{info_string}", file=self.outfile)
		else:
			print(f"[FLAG INFO]\n{tss}{info_string}\n[FLAG INFO]\n", file=self.outfile)
		
	def output(self, *args):
		tss = ""
		if self.timestamps: tss = f"[{get_timestamp()}] "
		print(f"{tss}Call to {args[0]} on line {args[1]} of {args[2]} from line {args[3]} of {args[4]}", file=self.outfile)
		
	def no_module_output(self, *args):
		tss = ""
		if self.timestamps: tss = f"[{get_timestamp()}] "
		print(f"{tss}Call to {args[0]} on line {args[1]}", file=self.outfile)
	
	def no_function_output(self, *args):
		tss = ""
		if self.timestamps: tss = f"[{get_timestamp()}] "
		print(f"{tss}Call to {args[2]} from {args[4]}", file=self.outfile)
		
	def log(self):
		sys.setprofile(self.trace_func)