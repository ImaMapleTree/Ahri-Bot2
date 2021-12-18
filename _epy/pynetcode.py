import signaturequeue as sq
import socket as _socket
import threading
import time
import sys
import os
import traceback
from queue import Empty

class DisconnectError(Exception):
	def __init__(self):
		super().__init__()

class InvalidDecoderError(Exception):
	def __init__(self, input):
		super().__init__(f"{input} (argument 1) is not a valid decoder. Options: (0, 1)")

class NullDataError(Exception):
	def __init__(self):
		super().__init__("Decoder 1 requires compressed data as an argument.")

class InvalidListenerError(Exception):
	def __init__(self, listener):
		self.listener = listener
		super().__init__()
		
	def __str__(self):
		return f"{self.listener} is not a valid listener type."

class NetByte():
	def addressEncoder(self, x: int) -> bytes:
		amount = (x.bit_length() + 7) // 8
		return (amount).to_bytes(1, "big") + x.to_bytes(amount, 'big')
	
	def int_to_bytes(self, bytes):
		if bytes == 0:
			return (b'\x00')
		amount = (bytes.bit_length() + 7) // 8
		return bytes.to_bytes(amount, "big")
	
	@staticmethod
	def int_from_bytes(xbytes: bytes) -> int:
		return int.from_bytes(xbytes, 'big')
	
	def __init__(self, function=None, decoder=0, *args, **kwargs):
		valid_decoders = [0, 1]
		self._function = function
		self._decoder = decoder
		if decoder not in valid_decoders: raise InvalidDecoderError(decoder)
		self._args = args
		self._id = kwargs.get("id")
	
	def address(self, id=None):
		if id == None:
			if self._id != None: id = self._id
			else: id = 0
		return self.addressEncoder(id)
	
	def asByte(self, id=None):
		bytedata = []
		if self._decoder == 0:
			bytedata.append(self.int_to_bytes(0))
			bytedata.append(self.address(id))
			if self._function == None: bytedata.append(0)
			else:
				func = bytes(self._function, "utf-8")
				bytedata.append(self.int_to_bytes(len(func)))
				bytedata.append(b"\n\r")
				bytedata.append(func)
			for arg in self._args:
				if type(arg) == type((1,1)):
					arg = "TUPLE[" + str(arg).replace("(", "").replace(")", "").replace(",", "*") + "]"
				
				bytedata.append(bytes(str(arg), "utf-8"))
				bytedata.append(bytes(",", "utf-8"))
			return b"".join(bytedata)
		
		if self._decoder == 1:
			bytedata.append(self.int_to_bytes(1))
			bytedata.append(self.address(id))
			if self._function == None: bytedata.append(0)
			else:
				func = bytes(self._function, "utf-8")
				bytedata.append(self.int_to_bytes(len(func)))
				bytedata.append(b"\n\r")
				bytedata.append(func)
			c_data = self.args(0)
			if c_data == None: raise NullDataError
			#bytedata.append(self.addressEncoder(len(c_data)))
			bytedata.append(c_data)
		return b"".join(bytedata)
		
	@staticmethod
	def DECODE(data):
		if data == None: return None
		decoder = NetByte.int_from_bytes(data[0:1])
		if decoder == 0: return NetByte.standardDecoder(data)
		if decoder == 1: return NetByte.compressedDecoder(data)
	
	@staticmethod
	def compressedDecoder(data):
		if data == None: return None
		bit_length = NetByte.int_from_bytes(data[1:2]) + 1
		id = NetByte.int_from_bytes(data[1:bit_length])
		func_end = data.find(b"\n\r")
		func_length = NetByte.int_from_bytes(data[bit_length:func_end])
		func_end = func_end + len("\n\r")
		function = data[func_end:func_end+func_length].decode("utf-8")
		c_data = data[func_end+func_length:]
		kwargs = {"id": id}
		return NetByte(function, 1, c_data, **kwargs)
	
	@staticmethod
	def standardDecoder(data):
		if data == None: return None
		bit_length = NetByte.int_from_bytes(data[1:2]) + 1
		id = NetByte.int_from_bytes(data[1:bit_length])
		func_end = data.find(b"\n\r")
		func_length = NetByte.int_from_bytes(data[bit_length+1:func_end])
		func_end = func_end + len("\n\r")
		function = data[func_end:func_end+func_length].decode("utf-8")
		pre_args = data[func_end+func_length:].decode("utf-8").split(",")
		pre_args.pop(len(pre_args)-1)
		kwargs = {"id": id}
		return NetByte(function, 0, *pre_args, **kwargs)
	
	def _argParse(self, arg):
		def bracketArg(arg):
			p1 = arg.find("["); p2 = arg.find("]")
			return arg[p1+1:p2]
		
		if self._decoder != 0: return arg
		if arg.find("TUPLE") != -1: return tuple(map(int, bracketArg(arg).split('* '))) 
		return arg
		#if arg.find("TUPLE[") != -1: arg = tuple(map(int, arg.replace(
	
	def args(self, int=None):
		args = []
		if int == None: 
			if self._decoder != 0: return self._args
			for arg in self._args: args.append(self._argParse(arg))
			return args
		else:
			try: return self._argParse(self._args[int])
			except: return None
		
class NetThread(threading.Thread):
	def __init__(self, *args, **kwargs):
		super(NetThread, self).__init__(*args, **kwargs)
		self._thread = threading.current_thread()
		self._condition = threading.Condition()
		
	def int_from_bytes(self, xbytes: bytes) -> int:
		return int.from_bytes(xbytes, 'big')

	def recvall(self, socket, artificial_timeout=0.00001):
		fragments = []
		start_time = time.time()
		while True:
			try:
				chunk = socket.recv(self._byte_limit)
				fragments.append(chunk)
			except _socket.timeout: #Actual timeout is 0.01
				if time.time() - start_time >= artificial_timeout:
					chunk = False
				else: chunk = True
			except ConnectionResetError: raise DisconnectError
			except ConnectionAbortedError: raise DisconnectError
			if not chunk: break
			data = b"".join(fragments)
			if data == b"": return None
			return data

	def DataDecoder(self, data):
		if data == None: return None
		bit_length = self.int_from_bytes(data[0:1]) + 1
		sid = self.int_from_bytes(data[1:bit_length])
		real_data = data[bit_length:]
		if len(real_data) >= 10000:
			return (sid, real_data)
		return (sid, real_data.decode("utf-8"))
		
	def addressEncoder(self, x: int) -> bytes:
		amount = (x.bit_length() + 7) // 8
		return (amount).to_bytes(1, "big") + x.to_bytes(amount, 'big')

	def EventWrapper(self, wrappers, *args):
		for wrapper in wrappers:
			try: wrapper(self, *args)
			except Exception as e:
				traceback.print_exc()

class ConnectionBridge(NetThread):
	def __init__(self, client, id, client_queue, listener_queue, end_queue, byte_limit=4096, data_timeout=0.01, client_timeout=30, *args, **kwargs):
		super(ConnectionBridge, self).__init__(*args, **kwargs)
		
		self.socket = client
		self._id = id
		self._client_queue = client_queue
		
		
		self._listener_queue = listener_queue
		self._end_queue = end_queue
		
		
		self._byte_limit = byte_limit
		self._client_timeout = client_timeout
		self._data_timeout = data_timeout
		
		self._begin_timeout = False
		self._timeoutTime = 0
		self._timeout = False
		
		self.check = 0
		
		
	def run(self):
		start_time = time.time()
		attempts = 0
		error_attempts = 0
		self.socket.settimeout(self._data_timeout)
		self._client_queue.assign(self._id)
		
		while self._timeout == False:
			try:
				outbound = self._client_queue.get_nowait()
				try: self.socket.send(outbound.asByte())
				except: traceback.print_exc()
			except Empty: pass
			except Exception as e: print(e)
			try: 
				data = NetByte.DECODE(self.socket.recv(self._byte_limit))
				if data != None: self._listener_queue.put(data)
				self._begin_timeout = False
			except _socket.timeout: pass
			except (ConnectionResetError, ConnectionAbortedError):
				if self._client_timeout != None:
					if not self._begin_timeout: self._begin_timeout = time.time()
					if time.time() - self._begin_timeout >= self._client_timeout: self._timeout = True
			except Exception as e: 
				traceback.print_exc()
				error_attempts += 1
		
		self.socket.close()
		self._end_queue.put(self._id)

class ConnectionListener(NetThread):
	def __init__(self, ip="localhost", port=25565, timeout=0.01, max_connections=10, byte_limit=4096, connection_key=None, client_data_timeout=0.01, client_timeout=300, *args, **kwargs):
		super(ConnectionListener, self).__init__(*args, **kwargs)
		
		self._connections = {}
		self._threads = []
		
		self._client_queue = sq.Queue("listener")
		self._listener_queue = sq.Queue("listener")
		self._end_queue = sq.Queue("listener")
		
		self._wrappers = {"onConnect": [], "onDisconnect": [], "onServerbound": []}
		
		print("Starting Connection Listener")
		self._start_time = time.time()
		self._ip = ip
		self._port = port
		self._max_connections = max_connections
		self._timeout = timeout
		self._byte_limit = byte_limit
		self._connection_key = connection_key
		self._client_data_timeout = client_data_timeout
		self._client_timeout = client_timeout
		
		
		self.socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
		self.socket.bind((ip, port))
		self.socket.listen(max_connections)
		self.socket.settimeout(timeout)
		
		print(f"Listener successfully started in: {str(time.time() - self._start_time)[0:7]} seconds.")
		print(f"Currently listening to: (IP: {self._ip}) | (Port: {self._port})")
		print("------------------------------------------------------")
		
	def registerListener(self, type, function):
		if type == "connect": self._wrappers["onConnect"].append(function)
		elif type == "disconnect": self._wrappers["onDisconnect"].append(function)
		elif type == "serverbound": self._wrappers["onServerbound"].append(function)
		elif type == "data": self._wrappers["onServerbound"].append(function)
		else:
			if type not in self._wrappers: self._wrappers[type] = []
			self._wrappers[type].append(function)
	
	def send(self, data=None, id=None):
		self._client_queue.put(data, id)
	
	def sendToAll(self, data=None):
		for id in self._connections:
			if self._connections[id] == None: continue
			self._client_queue.put(data, id)
	
	def run(self):
		while True:
			try: 
				terminator = self._end_queue.get_nowait(True)
				old_connection = self._connections[terminator]
				self._connections[terminator] = None
				self._threads[terminator]._stop()
				self._threads[terminator] = None
				self.EventWrapper(self._wrappers["onDisconnect"], old_connection)
				print(f"Terminated connection with: (ID: {terminator}) {old_connection}")
			except Empty: pass
			except Exception as e: print(e)
			try:
				serverbound = self._listener_queue.get_nowait(True)
				if serverbound._function != None:
					if serverbound._function in self._wrappers: self.EventWrapper(self._wrappers[serverbound._function], serverbound)
					self.EventWrapper(self._wrappers["onServerbound"], serverbound)
				else: self.EventWrapper(self._wrappers["onServerbound"], serverbound)
			except Empty: pass
			except Exception as e:
				print("Error in listener thread! (Serverbound Data)")
				traceback.print_exc()
			try: 
				new_socket, address = self.socket.accept()
				print(f"Incoming connection from: {address[0]}")
				new_socket.settimeout(self._timeout)
				try: 
					try: 
						if self._connection_key != None:
							data = new_socket.recv(self._byte_limit).decode("utf-8")
							if data[1] != self._connection_key:
								new_socket.close()
								print(f"Connection failed with {address[0]}. Reason: Invalid Key")
						id = len(self._connections)
						self.EventWrapper(self._wrappers["onConnect"], (address[0], address[1], id)) #OnConnect wrapper
						self._connections[id] = address[0]
						new_socket.send(bytes(list(self.addressEncoder(id))))
						new_thread = ConnectionBridge(new_socket, id, self._client_queue, self._listener_queue, self._end_queue, self._byte_limit, self._client_data_timeout, self._client_timeout, daemon=True)
						new_thread.start()
						self._threads.append(new_thread)
						print(f"Handshake completed with: {address[0]} (ID: {id})")
					except Exception as e:
						new_socket.close()
						print(f"Connection failed with {address[0]}. Reason: {e}")
						traceback.print_exc()
				except _socket.timeout: pass
			except _socket.timeout: pass
				
class ClientConnection(NetThread):
	def __init__(self, ip="localhost", port=25565, initial_timeout = 10, timeout=0.5, byte_limit=4096, connection_key=None, *args, **kwargs):
		super(ClientConnection, self).__init__()
		self._ip = ip
		self._port = port
		self._byte_limit = byte_limit
		self._connection_key = connection_key
		self._initial_timeout = initial_timeout
		self._timeout = timeout
		
		self.socket = _socket.socket(_socket.AF_INET, _socket.SOCK_STREAM)
		self.socket.settimeout(self._initial_timeout)
		
		self._client_queue = sq.Queue("client")
		
		self._wrappers = {"onConnect": [], "onDisconnect": [], "onClient": [], "onPing": []}
		
		self._id = None
		self._connected = False
		self._pings = 0
		
	def registerListener(self, type, function):
		if type == "connect": self._wrappers["onConnect"].append(function)
		elif type == "disconnect": self._wrappers["onDisconnect"].append(function)
		elif type == "client": self._wrappers["onClient"].append(function)
		elif type == "data": self._wrappers["onClient"].append(function)
		elif type == "ping": self._wrappers["onPing"].append(function)
		else:
			if type not in self._wrappers: self._wrappers[type] = []
			self._wrappers[type].append(function)
	
	def sendData(self, data=None):
		self._client_queue.put(data)
	
	def run(self):
		print(f"Attempting connection with {self._ip}:{self._port}")
		try:
			self.socket.connect((self._ip, self._port))
			if self._connection_key != None: self.socket.send(NetByte(self._connection_key).asByte())
			try: 
				self._id = self.DataDecoder(self.socket.recv(self._byte_limit))[0]
				self._connected = True
				print(f"Successfully connected to {self._ip}:{self._port} (Unique ID: {self._id})")
				print("------------------------------------------------------")
				self.EventWrapper(self._wrappers["onConnect"])
			except Exception as e: 
				print(f"Failed to assign ID to client.")
				traceback.print_exc()
		except _socket.timeout:
			print("Error: Timed Out")
		self.socket.settimeout(self._timeout)
		while self._connected:
			try:
				outbound = self._client_queue.get_nowait(True)
				self.socket.send(outbound.asByte(self._id))
			except Empty: pass
			except Exception as e:
				print("Error in client thread!")
				traceback.print_exc()
			except _socket.timeout:
				self._client_queue.put(outbound, self._id)
			try:
				data = NetByte.DECODE(self.socket.recv(self._byte_limit))
				if data == "ping":
					self._pings += 1
					self.socket.send(NetByte("pong").asByte(self._id))
					self.EventWrapper(self._wrappers["onPing"], self._pings)
				else:
					if data._function != None:
						if data._function in self._wrappers: self.EventWrapper(self._wrappers[data._function], data)
						self.EventWrapper(self._wrappers["onClient"], data)
					else: self.EventWrapper(self._wrappers["onClient"], data)
			except _socket.timeout: pass
			except Exception as e:
				print("Crtical error in client thread!")
				traceback.print_exc()
				print(e)
				self._connected = False
		self.socket.close()
		self.EventWrapper(self._wrappers["onDisconnect"])