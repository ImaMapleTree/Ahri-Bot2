import requests
import aiohttp
from _epy import epyconfig
from _epy.epylog import Logger
from _epy.quicktools import TemporaryDict, redict, JOpen
from epyriot import utils, nio
import json
import threading
import time
import uuid
import asyncio
import inspect
import operator
import nest_asyncio
nest_asyncio.apply()

def sort_players(players, attr, reverse=False):
	return sorted(players, key=operator.attrgetter(attr), reverse=reverse)
	
def list_find(list, key, itemattr=None):
	for item in list:
		if itemattr:
			try:
				if key == getattr(item, itemattr): return item
			except AttributeError: pass
		else:
			if key == item: return item
	
def tally(players, attr):
	result = None
	for player in players: 
		if result == None: result = getattr(player, attr)
		else: result += getattr(player, attr)
	return result
	
def count(players, attr, hashattr=None, sort=False):
	results = {}
	reverse = True
	for player in players:
		result = getattr(player, attr)
		if hashattr: result = getattr(result, hashattr)
		if result not in results: results[result] = 0
		results[result] += 1
	if not sort: return results
	if sort == "reverse": reverse = False #backwards I know, but when sorting will return from lowest to highest instead of highest to lowest
	return {k: v for k, v in sorted(results.items(), key=lambda item: item[1], reverse=reverse)}

class APIError(Exception):
	CODE_BITS = {"400": "Bad Request", "401": "Unauthorized", "403": "Forbidden", "404": "Not Found", "415": "Unsupported Media Type", "429": "Rate Limit Exceeded", "500": "Internal Server Error", "503": "Service Unavailable"}
	CODE_DETAILS = {"400": "Check parameters", "401": "Request lacked API Key", "403": "Invalid API key or forbidden endpoint", "404": "Resource doesn't exist", "415": "Content-type header not set appropriately", "429": "Too many API calls.", "500": "Glitch", "503": "Riot Service Down"}
	def __init__(self, code):
		super(APIError, self).__init__(f"Riot API Error ({code} : {APIError.CODE_BITS[str(code)]})")
		

async def get_data(session, url, headers={}):
	async with session.get(url, headers=headers) as response:
		response = await session.get(url, headers=headers)
		if response.status != 200:
			return Riot.squasher.squash(response, get_data, args=[session, url, headers])
		if isinstance(response, asyncio.Task): await response; response = response.result(); print(response)
		data = await response.json()
		return(data)
		
async def FTN_get_data(session, url, headers={}):
	async with session.get(url, headers=headers) as response:
		response = await session.get(url, headers=headers)
		while response.status == 429:
				await asyncio.sleep(int(response.headers.get("Retry-After")))
				response = await session.get(url, headers=headers)
		if response.status != 200:
			return Riot.squasher.squash(response, get_data, args=[session, url, headers])
		if isinstance(response, asyncio.Task): await response; response = response.result(); print(response)
		data = await response.json()
		return(data)

async def large_req(sites, headers={}, FTN=False):
	async with aiohttp.ClientSession() as session:
		tasks = []
		for url in sites:
			if not FTN: task = asyncio.ensure_future(get_data(session, url, headers))
			else: task = asyncio.ensure_future(FTN_get_data(session, url, headers))
			tasks.append(task)
		ret = await asyncio.gather(*tasks, return_exceptions=True)	
		return(ret)
		
class ErrorSquasher():
	BLOCKING_ERRORS = [429, 500, 503]
	NON_BLOCKING_ERRORS = [400, 401, 403, 404, 415]
	def __init__(self, logger=True, timestamps=True, timeout=0.5, max_retries=10):
		self.timeouts = {}
		self.tries = {}
		self.logger = False
		self.timeout = timeout
		self.max_retries = max_retries
		self.in_recursion = False
		if logger:
			self.logger = Logger(dir="epyriot", module_mode="include", modules=["main.py"], filename="RAPI.txt", timestamps=timestamps, silent=True)
			self.logger.log()
	
	def squash(self, request, function=None, args=[], kwargs={}, retries=None):
		if retries == None: retries = self.max_retries
		function_name = inspect.stack()[1].function
		if hasattr(request, "status"): code = request.status
		else: code = request.status_code
		if function and code != 429: 
			function_name = function.__name__
			if function_name not in self.tries: self.tries[function_name] = 0
			if self.in_recursion:
				self.tries[function_name] += 1
				if self.tries[function_name] > retries: raise APIError(code)
			else:
				self.tries[function_name] = 0
		if code != 429:
			self.logger.flag(function_name, code, APIError.CODE_BITS[str(code)], APIError.CODE_DETAILS[str(code)])
			if function: self.timeouts[function_name] = self.timeout
		else:
			if function: self.timeouts[function_name] = int(request.headers.get("Retry-After"))
			else: raise APIError(code)
			
		if function: 
			lock_time = time.time()
			while time.time() - lock_time < self.timeouts[function_name]: time.sleep(0.015)
			self.in_recursion = True
			if inspect.iscoroutinefunction(function): final = asyncio.get_running_loop().run_until_complete(function(*args, **kwargs))
			else: final = function(*args, **kwargs)
			self.in_recursion = False
			return final
		
class RequestInterface():
	def __init__(self):
		self.riot_headers = utils.secret_dict()
		self.riot_headers["X-Riot-Token"] = RIOT_KEY
		
	def request(self, url, **params):
		response = requests.get(url, headers=self.riot_headers, params=params)
		return response.json()
		
class RootIF(RequestInterface):
	#regions = {"NA1": "americas", "LA1": "americas", "LA2": "americas", "EUW1": "europe", "EUN1": "europe", "TR1": "europe", "OC1": "americas", "BR1": "americas", "RU1": "europe", "JP1": "asia", "KR", "asia"}
	
	def __init__(self, name=None, region="na1", player_data=None, bypass=False):
		super(RootIF, self).__init__()
		self.session = requests.Session()
		self.game_ranks = None
		self.bypass = bypass
		self.region = region
		self.name = name
		self.forbidden = ["session", "mastery_data", "account_data", "id", "account_id", "puuid", "revision_date", "riot_headers"]
		if not name and not player_data: 
			if not bypass: raise ValueError
		else:
			if player_data: 
				self.level = None
				self.puuid = None
				self.copy_player_data(player_data)
			else:
				self.account_data = utils.secret_dict(self.request_account_info(self.region, self.name))
				qdatas = asyncio.run(large_req([f"https://{self.region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/{self.id}", f"https://{self.region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{self.id}"], headers=self.riot_headers, FTN=True))
				self.set_mastery_info(qdatas[0]) #I'm not a fan of this code but it should slightly optimize lookup speeds by saving these 2 requests for the request pool
				self.set_ranked_info(qdatas[1])
		self.MatchIF = None
		#self.routing_region = RootIF.regions.get(self.region)
	
	def request_account_info(self, region, name):
		response = self.session.get(f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}", headers=self.riot_headers)
		if response.status_code == 200:
			return self.set_account_info(response)
		else:
			Riot.squasher.squash(response, self.request_account_info, args=[region, name])
		
	def request_mastery_info(self, region, id):
		response = self.session.get(f"https://{region}.api.riotgames.com/lol/champion-mastery/v4/champion-masteries/by-summoner/{id}, headers=self.riot_headers")
		if response.status_code == 200:
			return self.set_mastery_info(response)
		else:
			Riot.squasher.squash(response, self.request_mastery_info, args=[region, id])
			
	def request_ranked_info(self, region, id):
		response = self.session.get(f"https://{region}.api.riotgames.com/lol/league/v4/entries/by-summoner/{id}, headers=self.riot_headers")
		if response.status_code == 200:
			return self.set_ranked_info(response)
		else:
			Riot.squasher.squash(response, self.request_ranked_info, args=[region, id])		
			
	@staticmethod
	def all_from_json(root_json, match_json):
		root = RootIF(bypass=True)
		if root_json.get("account_data"): root.set_account_info(root_json.get("account_data"))
		if root_json.get("mastery_data"): root.set_mastery_info(root_json.get("mastery_data"))
		if root_json.get("ranked_data"): root.set_ranked_info(root_json.get("ranked_data"))
		interface = root.cif()
		interface._matches_from_json(root, match_json)
		return interface
		
	def dump_info(self, name):
		info = {}
		if hasattr(self, "account_data"): info["account_data"] = self.account_data.to_JSON()
		if hasattr(self, "mastery_data"): info["mastery_data"] = self.mastery_data
		if hasattr(self, "ranked_data"): info["ranked_data"] = self.ranked_data
		JOpen(name, "w+", info)
			
	def set_account_info(self, response):
		j = response if isinstance(response, dict) else response.json()
		self.id = j["id"]
		self.account_id = j["accountId"]
		self.puuid = j["puuid"]
		self.icon = j["profileIconId"]
		self.icon_url = f'http://ddragon.leagueoflegends.com/cdn/{Riot.version}/img/profileicon/{self.icon}.png'
		self.revision_date = j["revisionDate"]
		self.level = j["summonerLevel"]
		self.name = j.get("name")
		if self.region: j["region"] = self.region
		else: self.region = j.get("region")
		return j
			
	def set_mastery_info(self, response):
		if isinstance(response, list): self.mastery_data = response
		else: self.mastery_data = response.json()
		return self.mastery_data		
			
	def set_ranked_info(self, response):
		self.game_ranks = []
		j = response if isinstance(response, list) else response.json()
		self.ranked_data = j
		[self.game_ranks.append(Division(data)) for data in j]
		return self.game_ranks
		
	def get_division(self):
		if self.game_ranks == None: self.game_ranks = self.request_ranked_info(self.region, self.id)
		if self.game_ranks == []:
			division = Division(None)
			self.game_ranks.append(division)
			return division
		return nio.RankedObject(self.game_ranks)
	
	def copy_player_data(self, data):
		self.region = data.get("currentPlatformId")
		self.account_id = data.get("currentAccountId")
		self.id = data.get("summonerId")
		self.name = data.get("summonerName")
		self.icon = data.get("profileIcon")
		
	def createInterface(self, **kwargs):
		self.MatchIF = MatchIF(self, **kwargs)
		return self.MatchIF
		
	def cif(self, **kwargs):
		return self.createInterface(**kwargs)
		
class MatchIF(RequestInterface):
	def __init__(self, root, **kwargs):
		super(MatchIF, self).__init__()
		self.forbidden = ["session", "match_list_data"]
		self.root = root
		self.region = root.region
		self.session = root.session
		self._operators = {'>': operator.gt, '<': operator.lt, '>=': operator.ge, '<=': operator.le, '==': operator.eq}
		self.players = []
		self.all_players = []
		self.searched_player = []
		if not root.bypass:
			self.match_list_data = self.request_match_list(root.region, root.account_id, **kwargs)
			
	def get_match_url(self, match):
		return f"https://{self.region}.api.riotgames.com/lol/match/v4/matches/{match['gameId']}"
		#return f"https://{self.routing_value}.api.riotgames.com/lol/match/v5/matches/{match}"
		
	def request_match_list(self, region, id, **params):
		if "champion" in params:
			if isinstance(params["champion"], Champion): params["champion"] = params["champion"].id
		#response = self.session.get(f"https://{routing}.api.riotgames.com/lol/match/v5/matches/by-puuid/{puuid}/ids"}
		response = self.session.get(f"https://{region}.api.riotgames.com/lol/match/v4/matchlists/by-account/{id}", headers=self.riot_headers, params=params)
		if response.status_code == 200:
			j = response.json()
			#print(j)
			self.match_list = j["matches"]
			#self.match_list = j
			self._match_list = self.match_list
			return j
		else:
			Riot.squasher.squash(response, self.request_match_list, args=[region, id], kwargs=params)
			
	def request_matches(self, match_list=None, max=0):
		if not match_list: match_list = self._match_list
		if max: match_list = match_list[0:max]
		urls = [self.get_match_url(match) for match in match_list]
		st = time.time()
		self.match_list = asyncio.run(large_req(urls, headers=self.riot_headers, FTN=True))
		self.matches = []
		self.all_players = []
		for match in self.match_list:
			new_match = Match(match, self)
			self.matches.append(new_match)
			self.all_players += new_match.players
		self.searched_player = self.filter_players("name", self.root.name)
		return self.matches
		
	def _matches_from_json(self, root, json):
		self.root = root
		self.matches = []
		self.all_players = []
		for match in json:
			new_match = Match(match, self)
			self.matches.append(new_match)
			self.all_players += new_match.players
		self.searched_player = self.filter_players("name", self.root.name)
		return self.matches
		
	def dump_info(self, name):
		JOpen(name, "w+", self.match_list)
		
	def filter_players(self, attr, value, relate="==", player_list=None, matches=None, save=True):
		op = self._operators[relate]
		if not matches: matches = self.matches
		if not player_list: player_list = self.all_players
		players = []
		[players.append(player) for player in player_list if self._filter(attr, value, player, op)]
		if save: self.players = players
		return players
	
	def _filter(self, attr, context, player, op=operator.eq):
		try: value = getattr(player, attr)
		except AttributeError: return False
		return op(value, context)
		
	def get_player(self, player_name):
		return list_find(self.all_players, player_name, "name")
		
	def get_most_played(self, player_name, all=False):
		player = self.get_player(player_name)
		if not player: return None
		return player.get_most_played(all)
		
	def tally(self, attr=None, iterable=None):
		if iterable == None: iterable = self.players
		if not attr: return None
		return tally(iterable, attr)
		
	def count(self, attr=None, sort=False, iterable=None):
		if iterable == None: iterable = self.players
		if not attr: return None
		return count(iterable, attr, sort)
			
class Division():
	def __init__(self, data):
		if data == None: self.create_unranked_divison()
		else:
			self.data = utils.secret_dict(data)
			self.type = data["queueType"]
			self.league_id = data["leagueId"]
			self.tier = data["tier"].capitalize()
			self.rank = data["rank"]
			self.lp = data["leaguePoints"]
			self.wins = data["wins"]
			self.losses = data["losses"]
			self.winrate = round((self.wins/(self.wins+self.losses)*100))
			self.veteran = data["veteran"]
			self.inactive = data["inactive"]
			self.new = data["freshBlood"]
			self.hot_streak = data["hotStreak"]
			
	def create_unranked_divison(self):
		self.type = "RANKED_FLEX_SR"
		self.league_id = None
		self.tier = "Unranked"
		self.rank = ""
		self.lp = 0
		self.wins = 0
		self.losses = 0
		self.winrate = 0
		self.veteran = False
		self.inactive = False
		self.new = False
		self.hot_streak = False

	def __eq__(self, obj):
		if id(obj) == id(self): return True
		if obj.league_id == self.league_id: return True
		return False
	
	def __repr__(self):
		return f"<Division({self.type}, {self.tier} {self.rank}) at {hex(id(self))}>"
			
class Champion():
	def __init__(self, data):
		self.data = data
		self.reference = data["id"]
		self.name = data["name"]
		self.id = int(data["key"])
		self.title = data["title"]
		self.lore = data["blurb"]
		self.info = data["info"]
		self.image = data["image"]["full"]
		self.tags = data["tags"]
		self.bartype = data["partype"]
		self.stats = data["stats"]
		
	@classmethod
	def from_ref(cls, ref):
		for c in Riot.champions:
			if c == ref: return c
		
	def get_image_url(self):
		return f'http://ddragon.leagueoflegends.com/cdn/{Riot.version}/img/champion/{self.image}'
		
	def __eq__(self, obj):
		if id(obj) == id(self): return True
		if obj == self.name: return True
		if obj == self.id: return True
		if obj == self.reference: return True
		return False
	
	def __hash__(self):
		return hash(self.name)
		
	def __str__(self):
		return self.name
		
	def __repr__(self):
		return f"<Champion({self.name}, {self.id}) at {hex(id(self))}>"
			
class Team():
	def remove_pickTurn(self, ban):
		return ban["championId"]
	
	def __init__(self, data, players=None):
		self.correct_roles = ["Top", "Jungle", "Middle", "Bot Carry", "Support"]
		self.data = utils.secret_dict(data)
		self.forbidden = ["data"]
		self.team_id = data["teamId"]
		self.color = "blue" if self.team_id == 100 else "red"
		self.win = True if data["win"] == "Win" else False
		self.outcome = nio.GameResultObject(self.win)
		self.result = self.outcome
		self.first_blood = data["firstBlood"]
		self.first_tower = data["firstTower"]
		self.first_inhibitor = data["firstInhibitor"]
		self.first_baron = data["firstBaron"]
		self.first_dragon = data["firstDragon"]
		self.first_rift_herald = data["firstRiftHerald"]
		self.tower_kills = data["towerKills"]
		self.inhibitor_kills = data["inhibitorKills"]
		self.baron_kills = data["baronKills"]
		self.dragon_kills = data["dragonKills"]
		self.rift_herald_kills = data["riftHeraldKills"]
		self.bans = [self.remove_pickTurn(ban) for ban in data["bans"]]
		self.players = players
		
	def __repr__(self):
		return f"<Team({self.color}, {self.win}) at {hex(id(self))}>"
	
class Player(RootIF):
	def __init__(self, data, player_data, match = None):
		super(Player, self).__init__(player_data=player_data)
		if data != None:
			self.data = utils.secret_dict(data)
			self.player_data = utils.secret_dict(player_data)
			self.match = match
			self.interface = None if not self.match else self.match.interface
			self.forbidden = self.interface.root.forbidden + ["data", "player_data", "account_id", "id"]
			self.player_id = data["participantId"]
			self.team_id = data["teamId"]
			self.team = self.get_team(self.team_id)
			self.color = "blue" if self.team_id == 100 else "red"
			self.champion_id = data["championId"]
			self.champion = Champion.from_ref(self.champion_id)
			self.summoner_spell1 = nio.SummonerSpell(data["spell1Id"])
			self.summoner_spell2 = nio.SummonerSpell(data["spell2Id"])
			s = data["stats"]
			self.win = s.get("win")
			self.outcome = nio.GameResultObject(self.win)
			self.result = self.outcome
			self.items = [s.get("item0"), s.get("item1"), s.get("item2"), s.get("item3"), s.get("item4"), s.get("item5"), s.get("item6")]
			self.kills = s.get("kills")
			self.deaths = s.get("deaths")
			self.assists = s.get("assists")
			try:
				self.kda = f"{round((self.kills+self.assists)/self.deaths, 2):.2f}"
			except:
				self.kda = "Perfect"
			self.kda_slashes = f'{self.kills}/{self.deaths}/{self.assists}'
			self.largest_killing_spree = s.get("largestKillingSpree")
			self.largest_multikill = s.get("largestMultiKill")
			self.killing_sprees = s.get("killingSprees")
			self.longest_time_alive = s.get("longestTimeSpentLiving")
			self.double_kills = s.get("doubleKills")
			self.triple_kills = s.get("tripleKills")
			self.quadra_kills = s.get("quadraKills")
			self.penta_kills = s.get("pentaKills")
			self.total_damages = {"total": s.get("totalDamageDealt"), "magic": s.get("magicDamageDealt"), "physical": s.get("physicalDamageDealt"), "true": s.get("trueDamageDealt"), "pretty_total": '{:,}'.format(s.get("totalDamageDealt")), "pretty_ magic": '{:,}'.format(s.get("magicDamageDealt")), "pretty_physical": '{:,}'.format(s.get("physicalDamageDealt")), "pretty_true": '{:,}'.format(s.get("trueDamageDealt"))}
			self.champion_damages = {"total": s.get("totalDamageDealtToChampions"), "magic": s.get("magicDamageDealtToChampions"), "physical": s.get("physicalDamageDealtToChampions"), "true": s.get("trueDamageDealtToChampions"), "pretty_total": '{:,}'.format(s.get("totalDamageDealtToChampions")), "pretty_magic": '{:,}'.format(s.get("magicDamageDealtToChampions")), "pretty_physical": '{:,}'.format(s.get("physicalDamageDealtToChampions")), "pretty_true": '{:,}'.format(s.get("trueDamageDealtToChampions"))}
			self.objective_damage = s.get("damageDealtToObjectives")
			self.turret_damage = s.get("damageDealtToTurrets")
			self.healing = s.get("totalHeal")
			self.mitigated_damage = s.get("damageSelfMitigated")
			self.largest_crit = s.get("largestCriticalStrike")
			self.vision_score = s.get("visionScore")
			self.cc_score = s.get("timeCCingOthers")
			self.damage_taken = {"total": s.get("totalDamageTaken"), "magical": s.get("magicalDamageTaken"), "physical": s.get("physicalDamageTaken"), "true": s.get("trueDamageTaken"), "pretty_total": '{:,}'.format(s.get("totalDamageTaken")), "pretty_magical": '{:,}'.format(s.get("magicalDamageTaken")), "pretty_physical": '{:,}'.format(s.get("physicalDamageTaken")), "pretty_true": '{:,}'.format(s.get("trueDamageTaken"))}
			self.gold_earned = s.get("goldEarned")
			self.pretty_gold_earned = '{:,}'.format(self.gold_earned)
			self.gold_spent = s.get("goldSpent")
			self.pretty_gold_spent = '{:,}'.format(self.gold_spent)
			self.turret_kills = s.get("turretKills")
			self.inhibitor_kills = s.get("inhibitorKills")
			self.total_minions_killed = s.get("totalMinionsKilled")
			self.neutral_minions_killed =  s.get("neutralMinionsKilled")
			self.creep_score = self.total_minions_killed + self.neutral_minions_killed
			self.total_cc_time = s.get("totalTimeCrowdControlDealt")
			self.champion_level = s.get("champLevel")
			self.vision_wards_bought = s.get("visionWardsBoughtInGame")
			self.sight_wards_bought = s.get("sightWardsBoughtInGame")
			self.wards_placed = s.get("wardsPlaced")
			self.wards_killed = s.get("wardsKilled")
			self.first_blood_kill = s.get("firstBloodKill")
			self.first_blood_assist = s.get("firstBloodAssist")
			self.first_tower_kill = s.get("firstTowerKill")
			self.first_tower_assist = s.get("firstTowerAssist")
			self.runes = [s.get("perk0"), s.get("perk1"), s.get("perk2"), s.get("perk3"), s.get("perk4"), s.get("perk5")]
			self.rune_primary = s.get("perkPrimaryStyle")
			self.rune_secondary = s.get("perkSubStyle")
			self.rune_stats = {self.runes[0]: [s.get("perk0Var1"), s.get("perk0Var2"), s.get("perk0Var3")], self.runes[1]: [s.get("perk1Var1"), s.get("perk1Var2"), s.get("perk1Var3")], self.runes[2]: [s.get("perk2Var1"), s.get("perk2Var2"), s.get("perk2Var3")], self.runes[3]: [s.get("perk3Var1"), s.get("perk3Var2"), s.get("perk3Var3")], self.runes[4]: [s.get("perk4Var1"), s.get("perk4Var2"), s.get("perk4Var3")], self.runes[5]: [s.get("perk5Var1"), s.get("perk5Var2"), s.get("perk5Var3")]}
			self.timeline = data["timeline"]
			self.lane = None if self.timeline["lane"] == "BOTTOM" or self.timeline["lane"] == "NONE" else self.timeline["lane"].capitalize()
			if not self.lane:
				if self.timeline["role"] == "DUO" or self.timeline["role"] == "DUO_CARRY": self.lane = "Bot Carry"
				elif self.timeline["role"] == "SOLO" or self.timeline["role"] == "DUO_SUPPORT": self.lane = "Support"
				else: self.lane = "Unknown"
	
	def get_team(self, id):
		if not self.match: return None
		if self.match.teams[0].team_id == id: return self.match.teams[0]
		return self.match.teams[1]
		
	def get_teammates(self):
		return [player for player in self.team.players if player.name != self.name]
	
	def get_most_played(self, index=0, all=False):
		if not self.interface: return None
		players = self.interface.filter_players("name", self.name, save=False)
		champions = count(players, "champion", sort=True)
		if all: return [[k, v] for k, v in champions.items()]
		return list(champions.items())[index]
	
	def __hash__(self):
		return hash(self.name)
		
	def __repr__(self):
		return f"<Player({self.name}, {self.champion.name}, {self.color}) at {hex(id(self))}>"
		
class Match():
	def __init__(self, data, interface=None):
		if data != None:
			self.forbidden = ["data", "game_id"]
			self.data = utils.secret_dict(data)
			self.interface = interface
			self.game_id = data["gameId"]
			self.platform_id = data["platformId"]
			self.creation_epoch = data["gameCreation"]
			self.duration = data["gameDuration"]
			self.time = nio.TimeObject(self.creation_epoch, self.duration)
			self.queue_id = data["queueId"]
			self.map_id = data["mapId"]
			self.season_id = data["seasonId"]
			self.version = data["gameVersion"]
			self.mode = data["gameMode"]
			self.type = data["gameType"]
			i = 0; self.players = []; self.teams = []
			self.teams = [Team(t) for t in data["teams"]]
			for p in data["participants"]:
				new_player = Player(p, data["participantIdentities"][i]["player"], self)
				self.players.append(new_player); i += 1
				if new_player.name == self.interface.root.name: self.player = new_player
			self.teams[0].players = self.organize_players(self.players[0:5])
			self.teams[1].players = self.organize_players(self.players[5:10])
			self.teams[0].gold = tally(self.teams[0].players, "gold_earned")
			self.teams[1].gold = tally(self.teams[1].players, "gold_earned")
			self.teams[0].pretty_gold = '{:,}'.format(self.teams[0].gold)
			self.teams[1].pretty_gold = '{:,}'.format(self.teams[1].gold)
			#self.time_since_creation = utils.current_epoch_difference(self.creation_date/1000)
			#self.pretty_duration = utils.timestamp_readable(self.duration)
			#self.pretty_date = utils.date_readable(self.creation_date)
			self.match_type = nio.QueueObject(Riot.queues[self.queue_id])
			self.map = Riot.maps[self.map_id]["name"]
			self.season = Riot.seasons[self.season_id]
			self.mode_info = Riot.modes[self.mode]
			self.gametype_info = Riot.gametypes[self.type]
	
	def organize_players(self, players):
		final = []
		players = list(players)
		def change(players, index, player):
			players[index:index] = player
			
		roles = ["Top", "Jungle", "Middle", "Bot Carry", "Support"]; i = 0
		for role in roles:
			[final.append(players.pop(players.index(player))) for player in players if player.lane == role]
		final += players
		return final
		
class RiotIF(RequestInterface):
	def __init__(self, logger=True):
		super(RiotIF, self).__init__()
		self.session = requests.Session()
		self.squasher = ErrorSquasher(logger)
		self.version_data = self.get_live_version()
		self.champion_rotation_data = self.get_champion_rotation()
		self.champion_data = self.get_champions()
		self.get_seasons(); self.get_queues(); self.get_maps(); self.get_modes(); self.get_gametypes();
		
	def get_champion_rotation(self):
		r = self.session.get("https://na1.api.riotgames.com/lol/platform/v3/champion-rotations", headers=self.riot_headers)
		if r.status_code == 200:
			j = r.json()
			self.champion_rotation = j["freeChampionIds"]
		else:
			return self.squasher.squash(r, self.get_champion_rotation, retries=2)
		return j
		
	def get_live_version(self):
		r = self.session.get("https://ddragon.leagueoflegends.com/realms/na.json")
		j = r.json()
		self.version = j["v"]
		self.language = j["l"]
		self.cdn = j["cdn"]
		return j
	
	def get_champions(self):
		if not hasattr(self, "version"): self.get_live_version()
		r = self.session.get(f"{self.cdn}/{self.version}/data/{self.language}/champion.json")
		if r.status_code == 200:
			j = r.json()["data"]
			self.champions = []
			for name in j:
				self.champions.append(Champion(j[name]))
		else:
			return self.squasher.squash(r, self.get_champions, retries=2)
		return self.champions
			
	def get_seasons(self):
		r = self.session.get("https://static.developer.riotgames.com/docs/lol/seasons.json")
		if r.status_code == 200:
			j = r.json()
			self.seasons = {}
			[self.seasons.update({season["id"]: season["season"]}) for season in j]
			return self.seasons
		else:
			self.squasher.squash(r, self.get_seasons, retries=2)
			
	def get_queues(self):
		r = self.session.get("https://static.developer.riotgames.com/docs/lol/queues.json")
		j = r.json()
		if r.status_code == 200:
			self.queues = {}
			for queue in j:
				id = queue["queueId"]; map = queue["map"]; desc = queue["description"]; notes = queue["notes"]
				if id == 0: desc = "Custom games"
				self.queues[id] = {"map": map, "description": desc, "notes": notes}
			return self.queues
		else:
			self.squasher.squash(r, self.get_queues, retries=2)
		
	def get_maps(self):
		r = self.session.get("https://static.developer.riotgames.com/docs/lol/maps.json")
		j = r.json()
		if r.status_code == 200:
			self.maps = {}
			for map in j:
				id = map["mapId"]; name = map["mapName"]; notes = map["notes"]
				self.maps[id] = {"name": name, "notes": notes}
			return self.maps
		else:
			self.squasher.squash(r, self.get_maps, retries=2)
		
	def get_modes(self):
		r = self.session.get("https://static.developer.riotgames.com/docs/lol/gameModes.json")
		j = r.json()
		if r.status_code == 200:
			self.modes = {}
			[self.modes.update({mode["gameMode"]: mode["description"]}) for mode in j]
			return self.modes
		else:
			self.squasher.squash(r, self.get_modes, retries=2)
			
	def get_gametypes(self):
		r = self.session.get("https://static.developer.riotgames.com/docs/lol/gameTypes.json")
		j = r.json()
		if r.status_code == 200:
			self.gametypes = {}
			[self.gametypes.update({gametype["gametype"]: gametype["description"]}) for gametype in j]
			return self.gametypes
		else:
			self.squasher.squash(r, self.get_gametypes, retries=2)
		
#======================================================

global RIOT_KEY
global Riot
global BRT

cfg = epyconfig.load()
RIOT_KEY = cfg["riot_key"]

Riot = RiotIF()

'''
root = RootIF("Tealeaf")
interface = root.createMatchIF()
matches = interface.request_matches(max=20)
match = matches.get(0]
player0 = match.players.get(0]
print(player0.name, player0.champion, player0.champion_level, player0.champion_damages)
print(match.players.get(5:10])
print(len(matches))
'''

		