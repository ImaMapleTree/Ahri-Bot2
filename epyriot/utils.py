import datetime
import dateutil.relativedelta
from collections.abc import MutableMapping
import time
import random

def timestamp_readable(epoch):
	return time.strftime("%Mm %Ss", time.gmtime(epoch))	
	
def date_readable(epoch):
	return datetime.datetime.fromtimestamp(epoch/1000).strftime("%m/%d/%Y")

def current_epoch_difference(epoch):
	return epoch_difference(epoch, datetime.datetime.now().timestamp())

def epoch_difference(epoch1, epoch2):
	dt1 = datetime.datetime.fromtimestamp(epoch1) # 1973-11-29 22:33:09
	dt2 = datetime.datetime.fromtimestamp(epoch2)
	rd = dateutil.relativedelta.relativedelta(dt2, dt1)
	if rd.years > 1: difference = "1+ Years"
	elif rd.years == 1: difference = "1 Year" 
	elif rd.months > 2: difference = f'{rd.months} Months {rd.days} Days'
	elif rd.months == 1: difference = f'{rd.months} Month {rd.days} Days'
	elif rd.days == 1: difference = f'{rd.days} Day {rd.hours} Hours'
	elif rd.days > 1: difference = f'{rd.days} Days {rd.hours} Hours'
	elif rd.hours != 1: difference = f'{rd.hours} Hours'
	else: difference = f'{rd.hours} Hour'
	return difference
	
class secret_dict(MutableMapping):
	def __init__(self, dict_like=None, *args, **kwargs):
		self.__store = dict_like if dict_like else dict()
		self.forbidden = ["__store", "_secret_dict__store"]
		
	def to_JSON(self):
		return self.__store

	def __getitem__(self, key):
		return self.__store[self._keytransform(key)]

	def __setitem__(self, key, value):
		self.__store[self._keytransform(key)] = value

	def __delitem__(self, key):
		del self.__store[self._keytransform(key)]

	def __iter__(self):
		return iter(self.__store)
	
	def __len__(self):
		return len(self.__store)

	def _keytransform(self, key):
		return key
		
	def __repr__(self):
		return f"<SecretDict at {hex(id(self))}>"
		
	def __str__(self):
		return f"<SecretDict at {hex(id(self))}>"