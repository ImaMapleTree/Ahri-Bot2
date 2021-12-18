import datetime
import dateutil
import time

def list_find(list, key, itemattr=None):
	for item in list:
		if itemattr:
			try:
				if key == getattr(item, itemattr): return item
			except AttributeError: pass
		else:
			if key == item: return item

class MostPlayedObject():
	def __init__(self, champion, games, interface=None):
		self.forbidden = []
		self.name = champion.name
		self.champion = champion
		self.games = games
		self.image_url = champion.get_image_url()
		if not interface:
			self.kills = None
			self.deaths = None
			self.assists = None
			self.kda = None
			self.kda_slashes = None
			self.wins = None
			self.losses = None
			self.winrate = None
		else:
			games = interface.filter_players("champion", self.champion, player_list=interface.searched_player)
			self.kills = interface.tally("kills", iterable=games)
			self.deaths = interface.tally("deaths", iterable=games)
			self.assists = interface.tally("assists", iterable=games)
			self.kda = round((self.kills+self.assists)/self.deaths, 2) if self.deaths != 0 else "Perfect"
			self.kda_slashes = f'{self.kills}/{self.deaths}/{self.assists}'
			if self.kda >= 4: self.kda_emoji = "gold_small_square"
			elif self.kda >= 2.5: self.kda_emoji = "blue_small_square"
			else: self.kda_emoji = ":white_small_square:"
			self.win_loss = interface.count("win", iterable=games)
			self.wins = self.win_loss.get(True, 0); self.losses = self.win_loss.get(False, 0)
			self.winrate = round((self.wins/(self.wins+self.losses)*100))
		
	def __str__(self):
		return str(self.champion)
		
class MostPlayedListObject():
	def __init__(self, champ_list):
		self.__dict__ = dict(champ_list[0].__dict__)
		self.champ_list = champ_list
		
	def __getitem__(self, num):
		return self.champ_list[num]
		
	def __len__(self):
		return len(self.champ_list)
		
	def __str__(self):
		return str(self.champ_list[0])

class QueueObject():
	mapping = {"Clash games": ["Clash", "Clash"], "5v5 Ranked Solo games": ["Ranked (Solo/Duo)", "Solo"], "5v5 Ranked Flex games": ["Ranked (Flex)", "Flex"], "5v5 Draft Pick games": ["Normal Draft", "Normals"],
		"Co-op vs. AI Intermediate Bot games": ["Co-op vs AI (INT)", "Bots"], "5v5 Blind Pick games": ["Blind Pick", "Blind"], "Co-op vs. AI Beginner Bot games": ["Co-op vs AI (BGNR)", "Bots"], "URF games": ["URF", "URF"], "5v5 ARAM games": ["ARAM", "ARAM"]}
	
	def __init__(self, data):
		self.forbidden = []
		self.map = data["map"]
		self.description = data["description"]
		map = QueueObject.mapping.get(self.description)
		self.type = self.description if not map else map[0]
		self.tiny = self.description if not map else map[1]
		self.notes = data["notes"]
		
	def __str__(self):
		return self.type
		
class GameResultObject():
	def __init__(self, outcome):
		self.text = "Win" if outcome else "Loss"
		self.color_emoji = ":small_blue_diamond:" if outcome else "small_red_diamond"
		self.boolean = outcome
		self.bool = outcome
		
	def __str__(self):
		return self.text
		
	def __bool__(self):
		return self.bool
		
class SummonerSpell():
	id_dict = {"21": "Barrier", "1": "Cleanse", "35": "DisabledSummoner", "36": "DisabledSummoner", "14": "Ignite", "3": "Exhaust", "4": "Flash", "6": "Ghost", "7": "Heal", "13": "Clarity", "30": "PoroRecall", "31": "PoroThrow", "33": "NexusSiege", "34": "NexusSiege", "11": "Smite", "32": "Snowball", "12": "Teleport"}
	def __init__(self, id):
		self.id = id
		self.text = SummonerSpell.id_dict.get(str(self.id), "Barrier")
		
	def __str__(self):
		return self.text
	
class RankedObject():
	def __init__(self, divisions):
		solo = list_find(divisions, "RANKED_SOLO_5x5", "type")
		self.add_nulls()
		if solo: 
			self.__dict__ = solo.__dict__
		flex = list_find(divisions, "RANKED_FLEX_SR", "type")
		if not solo:
			if flex: 
				self.__dict__ = flex.__dict__
			else:
				self.__dict__ = divisions[0].__dict__
		self.solo = solo if solo else EmptyObject(divisions[0])
		self.flex = flex if flex else EmptyObject(divisions[0])
	
	def add_nulls(self):
		self.data = None
		self.type = None
		self.league_id = None
		self.tier = None
		self.rank = None
		self.lp = None
		self.wins = None
		self.losses = None
		self.winrate = None
		self.veteran = False
		self.inactive = False
		self.new = False
		self.hot_streak = False
		
class EmptyObject():
	def __init__(self, copy):
		for item in copy.__dict__:
			self.__dict__[item] = ""
	
	def __str__(self):
		return ""

class TimeObject():
	def __init__(self, time1, time2=None):
		self.creation_date = time1
		self.duration = time2
		self.digital_duration = self.duration_format(self.duration)
		self.analog_duration = self.duration_format(self.duration, "%Mm %Ss")
		self.date = self.date_readable(self.creation_date)
		self.elapsed_time = self.current_epoch_difference(self.creation_date/1000)
		self.short_elapsed = self.current_epoch_difference(self.creation_date/1000, rounding=True)
		self.aduration = self.analog_duration
		self.dduration = self.digital_duration
		
	def duration_format(self, epoch, time_string="%M:%S"):
		return time.strftime(time_string, time.gmtime(epoch))	
	
	def date_readable(self, epoch):
		return datetime.datetime.fromtimestamp(epoch/1000).strftime("%m/%d/%Y")

	def current_epoch_difference(self, epoch, rounding=False):
		return self.epoch_difference(epoch, datetime.datetime.now().timestamp(), rounding)

	def epoch_difference(self, epoch1, epoch2, rounding=False):
		dt1 = datetime.datetime.fromtimestamp(epoch1) # 1973-11-29 22:33:09
		dt2 = datetime.datetime.fromtimestamp(epoch2)
		rd = dateutil.relativedelta.relativedelta(dt2, dt1)
		if rd.years > 1: 
			difference = "1+ years";
			if rounding: return difference
		elif rd.years == 1: 
			difference = "1 year"
			if rounding: return difference
		elif rd.months > 2: 
			difference = f'{rd.months} months'
			if rounding: return difference
			difference += f" {rd.days} days"
		elif rd.months == 1: 
			difference = f'{rd.months} month'
			if rounding: return difference
			difference += f" {rd.days} days"
		elif rd.days == 1: 
			difference = f'{rd.days} day'
			if rounding: return difference
			difference += f" {rd.hours} hours"
		elif rd.days > 1: 
			difference = f'{rd.days} days'
			if rounding: return difference
			difference += f" {rd.hours} hours"
		elif rd.hours > 1: 
			difference = f'{rd.hours} hours'
			if rounding: return difference
		elif rd.hours == 1: 
			difference = f'{rd.hours} hour'
			if rounding: return difference
		else:
			difference = f'{rd.minutes} mins'
		return difference
		
	def __str__(self):
		return self.elapsed_time