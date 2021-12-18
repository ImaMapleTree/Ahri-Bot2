from playsound import playsound
import threading
from queue import Queue
import time
import os
from soundfile import SoundFile
import pyaudio
import wave

def sound_base_path(path):
	sounds._setpath(path)
	
class AmbiguousDeviceError(Exception):
	def __init__(self, term, devices):
		self.devices = devices
		super(AmbiguousDeviceError, self).__init__(f"More than one device found for <{term}> | Devices: {[device.name for device in devices]}")
		
class NoDeviceError(Exception):
	def __init__(self, term):
		super(NoDeviceError, self).__init__(f"No devices found for <{term}>")

class AudioDevice():
	def __init__(self, device):
		self._PAI = pyaudio.PyAudio()
		self._base = device
		self.name = device["name"]
		self.index = device["index"]
		self.structVersion = device["structVersion"]
		self.host_api = self._PAI.get_host_api_info_by_index(device["hostApi"])["name"]
		c = device.get("maxInputChannels")
		self.channels = device["maxInputChannels"] if (device["maxOutputChannels"] < device["maxInputChannels"]) else device["maxOutputChannels"]
		self.input_latency = (device["defaultLowInputLatency"], device["defaultHighInputLatency"])
		self.output_latency = (device["defaultLowOutputLatency"], device["defaultHighOutputLatency"])
		self.samplerate = int(device["defaultSampleRate"])
		self.type = "output"
		if device["maxInputChannels"] > device["maxOutputChannels"]: self.type = "input"
			
	def __repr__(self):
		return str(self._base)
		
class AudioRecorder():
	def _audio_thread(self):
		while self.recording:
			self.audio_buffer.append(self.stream.read(self.frames_per_buffer))
	
	def __init__(self, device="microphone", frames_per_buffer=512, audio_buffer=[]):
		self._PAI = pyaudio.PyAudio()
		self.device_count = self._PAI.get_device_count()
		self.devices = self.get_devices()
		if device == "microphone" or device == "mic" or device == "input" or device == "in":
			self.device = AudioDevice(self._PAI.get_default_input_device_info())
		elif device == "output" or device == "out":
			self.device = AudioDevice(self._PAI.get_default_output_device_info())
		elif type(device) == type(int):
			self.device = AudioDevice(self._PAI.get_device_info_by_index(device))
		elif type(device) == AudioDevice:
			self.device = device
		else:
			found = [d for d in self.devices if device in d.name]
			if len(found) > 1: raise AmbiguousDeviceError(device, found)
			if len(found) == 0:
				found = [d for d in self.devices if device in d.host_api]
				if len(found) > 1: raise AmbiguousDeviceError(device, found)
				if len(found) == 0: raise NoDeviceError(device)
			self.device = found[0]
		self.frames_per_buffer = frames_per_buffer
		self.stream = None
		self.audio_buffer = audio_buffer
		self.stream_thread = None
		self.recording = False
		
	def get_devices(self):
		devices = []
		for i in range(self.device_count):
			devices.append(AudioDevice(self._PAI.get_device_info_by_index(i)))
		return devices
		
	def set_buffer(self, buffer):
		self.audio_buffer = buffer
		
	def record(self, format=pyaudio.paInt16):
		self.recording = True
		try:
			self.audio_buffer.clear()
		except:
			self.audio_buffer = []
		self.stream = self._PAI.open(format = pyaudio.paInt16, channels = self.device.channels, rate = self.device.samplerate, input = True, frames_per_buffer = self.frames_per_buffer, input_device_index = self.device.index, as_loopback = (self.device.type == "output"))
		self.stream_thread = threading.Thread(target=self._audio_thread, args=(), daemon=True)
		self.stream_thread.start()

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

def cut_audio_channels(source, channels=2):
	cb = 0
	newbyte = b""
	for i in range(len(source)): #Probably 8192
		if cb < 2:
			newbyte += source[i*2:(i+1)*2]
		cb = cb +1 if cb < 7 else 0
	return newbyte