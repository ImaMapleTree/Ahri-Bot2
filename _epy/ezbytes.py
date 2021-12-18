class NoDataError(Exception):
	def __init__(self):
		super(NoDataError, self).__init__()

class StringByte():
	def __init__(self, bytes):
		self._bytes = bytes
		
	def __iter__(self):
		self._index = 0
		return self
		
	def __next__(self):
		while self._index < len(self._bytes):
			byte = self._bytes[self._index:self._index+1]
			self._index += 1
			return byte
		raise StopIteration
		
	def __getitem__(self, key):
		if key >= len(self._bytes): raise IndexError
		byte = self._bytes[key:key+1]
		return byte

def ByteRead(filename):
	with open(filename, "rb") as bytefile:
		data = bytefile.read()
		bytefile.close()
	return data
		
def ByteWrite(filename, data):
	with open(filename, "wb") as bytefile:
		bytefile.write(data)
		bytefile.close()
	return
	
def ByteWriteSection(filename, data, index):
	with open(filename, "r+b") as bytefile:
		bytefile.seek(index)
		bytefile.write(data)
		bytefile.close()
	return

class ByteManager():
	def __init__(self, main_data=None):
		self._bytesources = {}
		self._maindata = main_data
		
	def setMain(self, data):
		self._maindata = data
	
	def addSource(self, key, source):
		self._bytesources[key] = source
		
	def SourceFromFile(self, key, filename):
		self._bytesources[key] = ByteRead(filename)
		
	def save(self, filename):
		pass
		
	def load(self, filename):
		pass
		
	def findIndex(self, key, data=None, index_length=25):
		if data == None: data = self._maindata
		if data == None: raise NoDataError
		key_header = self.getHeader(key, index_length)
		return data.find(key_header)
		
	def compare(self, key, data=None):
		if data == None: data = self._maindata
		if data == None: raise NoDataError
		return rawcompare(self._bytesources[key], data)
		
	def rawcompare(self, data1, data2):
		index = 0
		differences = []
		data2 = StringByte(data2)
		for byte in StringByte(data1):
			if index >= len(data2)
			if byte != data2[index]: differences.append([byte, data2[index]])
			index += 1
		return differences
		
	def getSection(self, key, data=None):
		if data == None: data = self._maindata
		if data == None: raise NoDataError
		index = self.findIndex(key, data)
		return data[index:index+self.getLength(key)]
		
	def getSource(self, key):
		return self._bytesources[key]
		
	def getLength(self, key):
		return len(self._bytesources[key])
		
	def getHeader(self, key, index_length=25):
		return self._bytesources[key][0:index_length]
		
	def writeMain(self, filename):
		if self._maindata == None: raise NoDataError
		ByteWrite(filename, self._maindata)
		
	def writeSection(self, filename, section, index):
		ByteWriteSection(filename, section, index)
		
	def __iter__(self):
		self._step = 0
		return self
		
	def __next__(self):
		while self._step < len(self._bytesources.keys()):
			key = self._bytesources.keys()[self._step]
			source = self._bytesources[key]
			self._step += 1
			return [key, source]
		raise StopIteration


