def lazylist(item):
	try:
		iter(item)
		return list(item)
	except: return [item]
		
def softtype(object):
	if type(object) == type(()): return "tuple"
	if type(object) == type(0): return "int"
	if type(object) == type([]): return "list"
	if type(object) == type({}): return "dict"
	if type(object) == type("hi"): return "string"
	if type(object) == type(0.0): return "float"
	return type(object)