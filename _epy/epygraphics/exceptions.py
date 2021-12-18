class RunningInstanceError(Exception): #Triggered when a non-multithreaded window is opened twice
	def __init__(self):
		super().__init__("Instance is already running in another thread!")
		
class PackerArgumentError(Exception):
	def __init__(self):
		super().__init__("Packer requires at least one argument (rows, or columns).")
		
class PackableObjectArgumentError(Exception):
	def __init__(self):
		super().__init__("PackableObject requires a width and height")
		
class RectangleArgumentError(Exception):
	def __init__(self):
		super().__init__("Canvas Rectangle requires either a second set of coords, or a width and height.")
		
class InvalidEventError(Exception):
	def __init__(self):
		super().__init__("Specified event does not exist.")