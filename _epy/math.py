import math
import random

class MagnitudeError(Exception):
	def __init__(self, limit):
		super().__init__("Total iterations cannot be greater than 10^8")


class Matherators():
	def flat(result=1):
		yield result
	
	def linear(k=0, limit=999999):
		for i in range(limit):
			yield k
			k += 1
			
	def quadratic(k=0, power=2, limit=999999):
		for i in range(limit):
			yield k**power
			k += 1
			
	def exponential(a=1, k=0, limit=999999):
		for i in range(limit):
			yield a**k
			k += 1

class Summation(Matherators):
	def __init__(self, number=0, xGen=None, limit=99999999):
		super().__init__()
		if limit > 99999999: raise MagnitudeError(limit)
		self.xGen = xGen
		if xGen == None: self.xGen = self.flat()
		self.number = number
		self.execution_limit = limit
	
	def add(self, value):
		self.number += value
		
	def series(self, expression, xGen=None, limit=None, keep=False):
		if not keep: self.number = 0
		if xGen == None: xGen = self.xGen
		if limit == None: limit = self.execution_limit
		expression = expression.replace("^", "**")
		for i in range(limit):
			try: 
				subbed_expression = expression.replace("x", str(next(xGen)))
				self.number += eval(subbed_expression)
			except StopIteration: break
		return self.number



			