import os
from _epy.quicktools import redict
import uuid
from ahri import utils, embeds, errors
import glob
import codecs
import time
import json
import threading

global _manager
_manager = None

class ThreadWriter(threading.Thread):
	def __init__(self, data, path, type="json", timeout=5, *args, **kwargs):
		kwargs["daemon"] = True
		super(ThreadWriter, self).__init__(*args, **kwargs)
		self.running = False
		self.data = data
		self.path = path
		self.type = type
		self.terminate = False
		self.timeout = timeout
		
	def run(self):
		self.running = True
		while not self.terminate:
			time.sleep(self.timeout)
			#if self.type == "json": json.dump(self.data, self.file, indent=3)
			if self.type == "json": utils.JOpen(self.path, "w+", self.data)
			
		

class DataManagerMeta(type):
	_instances = {}
	def __call__(cls, *args, **kwargs):
		if cls not in cls._instances:
			cls._instances[cls] = super(DataManagerMeta, cls).__call__(*args, **kwargs)
		return cls._instances[cls]

class DataManager(metaclass=DataManagerMeta):
	def __init__(self, ud_path="cache/user_data", stock_path="cache/stocks"):
		self.cfg = utils.CONFIG
		self.max_embeds = self.cfg["max_embeds"]
		self.ud_path = ud_path
		self.embed_udp = os.path.join(self.ud_path, "embeds/embed_user_data.json")
		self.embed_ud = redict(utils.JOpen(self.embed_udp, "r+"))
		self.embeds = {}
		
		self.stock_path = stock_path
		self.stock_data = self.open_all(stock_path, ext="*.json", lower=True)
		self.stock_udp = os.path.join(self.ud_path, "stock_user_data.json")
		self.stock_ud = redict(utils.JOpen(self.stock_udp, "r+"))
		self.stock_writer = ThreadWriter(self.stock_ud, self.stock_udp)
		self.stock_writer.start()
		
		self.ST5 = {"cp5": 0, "tp5": 0}
		
		
		self.id = utils.UUID()
		
	def open_all(self, dir="", ext="*", type="json", lower=False):
		open_dict = {}
		slashes = ["/", "\\"]
		if dir[len(dir)-1] not in slashes: dir += "/"
		dir += ext
		
		locations = glob.glob(dir)

		for loc in locations:
			if type == "json":
				if lower: open_dict[utils.shorten_source(loc).lower()] = utils.JOpen(loc, "r")
				else: open_dict[utils.shorten_source(loc)] = utils.JOpen(loc, "r")
		return open_dict
		
			
	def register_embeds(self, embeds):
		embeds = embeds if isinstance(embeds, list) or isinstance(embeds, dict) else {"name": embeds}
		for name in embeds:
			embed = embeds[name]
			if not embed.identifier in self.embed_ud.values():
				uuid = utils.UUID().uuid
				self.embed_ud[uuid] = embed.identifier
			else:
				uuid = self.embed_ud.getKey(embed.identifier)
			self.embeds[uuid] = embed
		utils.JOpen(self.embed_udp, "w+", self.embed_ud)
		return uuid
		
	def get_embed(self, id):
		return self.embeds.get(str(id))
		
	def embed_by_string(self, string):
		id = None
		for value in self.embed_ud.values():
			if value["name"] == string: id = self.embed_ud.getKey(value)
		return self.embeds.get(id)
		
	def write_embed(self, name, embed, dir=""):
		print(embed.raw)
		if not os.path.exists(dir): os.mkdir(dir)
		slashes = ["/", "\\"]
		temp_dir = dir
		if dir[len(dir)-1] not in slashes: temp_dir += "/"
		temp_dir += "*.embed"
		if len(glob.glob(temp_dir)) >= self.max_embeds: raise MaxEmbedsError
		p = os.path.join(dir, name + ".embed")
		f = codecs.open(p, 'w+', encoding='utf-8')
		f.write(embed.raw)
		f.close()
		embed.set_path(p)
		return self.register_embeds(embed)
		
	def create_stock_entry(self, user):
		self.stock_ud[str(user.id)] = {"name": user.name, "charms": 1000, "stocks": {}, "booster_cooldown": time.time()+86400}
		
		