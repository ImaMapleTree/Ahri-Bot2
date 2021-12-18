class InvalidButtonError(Exception):
	def __init__(self, select_overflow=False):
		if select_overflow: super().__init__("Row must have only one select component and nothing else")
			
class PackedRowError(Exception):
	def __init__(self):
		super().__init__("Cannot have more than 5 buttons per row.")
		
class ParseError(Exception):
	CODES = {"1": "Invalid Shell Name", "2": "Invalid Key in Shell", "3": "Attribute is forbidden", "4": "Evaluated non conditional", "5": "Field value must be < 1024 characters long"}
	
	def __init__(self, code, mistake=None, line=None):
		if code == 6: super().__init__(f"ParseError - Domain (**{mistake}**) has no attribute (**{line}**)")
		elif code == 7: super().__init__(f"ParseError - Index (**{line}**) out of range of Domain (**{mistake}**)")
		elif code == 8: super().__init__(f"ParseError - Domain (**{mistake}**) is not subsciptable (Example: player.name[0] gives an error)")
		elif code == 9: super().__init__(f"ParseError - Domains can only be extended with up to 10 attributes (**{mistake}**) has (**{line}**)")
		else:
			line = f"at line: (**{line}**)" if line else ""
			super().__init__(f"ParseError - {ParseError.CODES[str(code)]}: (**{mistake}**) {line}")
			
class MaxEmbedError(Exception):
	def __init__(self):
		super().__init__("Users are only able to create a maximum of 30 embeds.")
		
class InvalidStockError(Exception):
	def __init__(self):
		super().__init__("Requested stock does not exist.")