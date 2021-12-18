import requests
import aiohttp
from _epy import epyconfig
from _epy.epylog import Logger
from _epy.quicktools import TemporaryDict, redict
import json
import threading
import time
import uuid
import asyncio
import inspect
import nest_asyncio
nest_asyncio.apply()

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

async def large_req(sites, headers={}):
	async with aiohttp.ClientSession() as session:
		tasks = []
		for url in sites:
			task = asyncio.ensure_future(get_data(session, url, headers))
			tasks.append(task)
		ret = await asyncio.gather(*tasks, return_exceptions=True)	
		return(ret)
		
class BasicRequestThread(threading.Thread):
	def __init__(self, request_list=[], response_list=TemporaryDict(), *args, **kwargs):
		self.request_list = request_list
		self.response_list = response_list
		super(BasicRequestThread, self).__init__(*args, **kwargs)
		self.terminate = False
		self.running = False
		self.async_loop = asyncio.get_event_loop()
		
	async def _seriesrequest(self, reqs):
		async with aiohttp.ClientSession() as session:
			for req in reqs:
				async with session.get(*req[1], **req[2]) as response:
					self.response_list[req[0]] = await response.json()
		
	def request(self, *args, **kwargs):
		id = uuid.uuid1()
		self.request_list.append([id, args, kwargs])
		self.response_list[id] = None
		return id
		
	def retrieve(self, id, blocking=True):
		response = self.response_list.get(id)
		if blocking:
			while response == None:
				response = self.response_list.get(id)
				time.sleep(0.015)
		return response
		
	def get(self, *args, **kwargs):
		id = self.request(*args, **kwargs)
		return self.retrieve(id)
		
	def run(self):
		self.running = True
		while not self.terminate:
			time.sleep(0.015)
			if self.request_list:
				reqs = list(self.request_list)
				self.response_list.clear()
				asyncio.run(self._seriesrequest(reqs))
		self.running = False
		
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
	
	def squash(self, request, function=None, args=[], kwargs={}):
		function_name = inspect.stack()[1].function
		if hasattr(request, "status"): code = request.status
		else: code = request.status_code
		if function and code != 429: 
			function_name = function.__name__
			if function_name not in self.tries: self.tries[function_name] = 0
			if self.in_recursion:
				self.tries[function_name] += 1
				if self.tries[function_name] > self.max_retries: raise APIError(code)
			else:
				self.tries[function_name] = 0
		if code != 429:
			self.logger.flag(function_name, code, APIError.CODE_BITS[str(code)], APIError.CODE_DETAILS[str(code)])
			if function: self.timeouts[function_name] = self.timeout
		else:
			if function: self.timeouts[function_name] = int(request.headers["Retry-After"])
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
		self.riot_headers = {"X-Riot-Token": RIOT_KEY}
		
class RootIF(RequestInterface):
	def __init__(self, name=None, region="na1", player_data=None):
		super(RootIF, self).__init__()
		if not name and not player_data: raise ValueError
		if player_data: 
			self.level = None
			self.puuid = None
			self.copy_player_data(player_data)
		else:
			self.region = region
			self.name = name
			self.account_data = self.request_account_info(self.region, self.name)
		self.MatchIF = None
	
	def request_account_info(self, region, name):
		response = requests.get(f"https://{region}.api.riotgames.com/lol/summoner/v4/summoners/by-name/{name}", headers=self.riot_headers)
		if response.status_code == 200:
			j = response.json()
			self.id = j["id"]
			self.account_id = j["accountId"]
			self.puuid = j["puuid"]
			self.profile_icon = j["profileIconId"]
			self.revision_date = j["revisionDate"]
			self.level = j["summonerLevel"]
			return j
		else:
			Riot.squasher.squash(response, self.request_account_info, args=[region, name])
			
	def copy_player_data(self, data):
		self.region = data["currentPlatformId"]
		self.account_id = data["currentAccountId"]
		self.id = data["summonerId"]
		self.name = data["summonerName"]
		self.profile_icon = data["profileIcon"]
		
	def createMatchIF(self, **kwargs):
		self.MatchIF = MatchIF(self, **kwargs)
		return self.MatchIF
		
class MatchIF(RequestInterface):
	def __init__(self, root, **kwargs):
		super(MatchIF, self).__init__()
		self.region = root.region
		self.match_list_data = self.request_match_list(self.region, root.account_id, **kwargs)
		
	def get_match_url(self, match):
		return f"https://{self.region}.api.riotgames.com/lol/match/v4/matches/{match['gameId']}"
		
	def request_match_list(self, region, id, **params):
		if "champion" in params:
			if isinstance(params["champion"], Champion): params["champion"] = params["champion"].id
		response = requests.get(f"https://{region}.api.riotgames.com/lol/match/v4/matchlists/by-account/{id}", headers=self.riot_headers, params=params)
		if response.status_code == 200:
			j = response.json()
			self.match_list = j["matches"]
			self._match_list = self.match_list
			return j
		else:
			Riot.squasher.squash(response, self.request_match_list, args=[region, id], kwargs=params)
			
	def request_matches(self, match_list=None, max=0):
		if not match_list: match_list = self._match_list
		if max: match_list = match_list[0:max]
		urls = [self.get_match_url(match) for match in match_list]
		st = time.time()
		self.match_list = asyncio.run(large_req(urls, headers=self.riot_headers))
		self.matches = []
		for match in self.match_list:
			self.matches.append(Match(match))
		return self.matches
			
	def filter_players(self, attr, value, match_list=None):
		if not match_list: match_list = self.match_list
		players = []
		for match in match_list:
			players += [player for player in players if _filter(player)]
	
	def _filter(self, attr, context, player):
		try: value = getattr(player, attr)
		except AttributeError: return False
		return context == value		
			
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
		
	def __eq__(self, obj):
		if id(obj) == id(self): return True
		if obj == self.name: return True
		if obj == self.id: return True
		if obj == self.reference: return True
		return False
		
	def __repr__(self):
		return f"<Champion({self.name}, {self.id}) at {hex(id(self))}>"
			
class Team():
	def remove_pickTurn(self, ban):
		return ban["championId"]
	
	def __init__(self, data, players=None):
		self.data = data
		self.team_id = data["teamId"]
		self.color = "blue" if self.team_id == 100 else "red"
		self.win = True if data["win"] == "Win" else False
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
	def __init__(self, data, player_data, match_interface = None):
		super(Player, self).__init__(player_data=player_data)
		self.data = data
		self.match_interface = match_interface
		self.player_id = data["participantId"]
		self.team_id = data["teamId"]
		self.team = self.get_team(self.team_id)
		self.color = "blue" if self.team_id == 100 else "red"
		self.champion_id = data["championId"]
		self.champion = Champion.from_ref(self.champion_id)
		self.summoner_spell1 = data["spell1Id"]
		self.summoner_spell2 = data["spell2Id"]
		s = data["stats"]
		self.win = s["win"]
		self.items = [s["item0"], s["item1"], s["item2"], s["item3"], s["item4"], s["item5"], s["item6"]]
		self.kills = s["kills"]
		self.deaths = s["deaths"]
		self.assists = s["assists"]
		self.largest_killing_spree = s["largestKillingSpree"]
		self.largest_multikill = s["largestMultiKill"]
		self.killing_sprees = s["killingSprees"]
		self.longest_time_alive = s["longestTimeSpentLiving"]
		self.double_kills = s["doubleKills"]
		self.triple_kills = s["tripleKills"]
		self.quadra_kills = s["quadraKills"]
		self.penta_kills = s["pentaKills"]
		self.total_damages = {"total": s["totalDamageDealt"], "magic": s["magicDamageDealt"], "physical": s["physicalDamageDealt"], "true": s["trueDamageDealt"]}
		self.champion_damages = {"total": s["totalDamageDealtToChampions"], "magic": s["magicDamageDealtToChampions"], "physical": s["physicalDamageDealtToChampions"], "true": s["trueDamageDealtToChampions"]}
		self.objective_damage = s["damageDealtToObjectives"]
		self.turret_damage = s["damageDealtToTurrets"]
		self.healing = s["totalHeal"]
		self.mitigated_damage = s["damageSelfMitigated"]
		self.largest_crit = s["largestCriticalStrike"]
		self.vision_score = s["visionScore"]
		self.cc_score = s["timeCCingOthers"]
		self.damage_taken = {"total": s["totalDamageTaken"], "magical": s["magicalDamageTaken"], "physical": s["physicalDamageTaken"], "true": s["trueDamageTaken"]}
		self.gold_earned = s["goldEarned"]
		self.gold_spent = s["goldSpent"]
		self.turret_kills = s["turretKills"]
		self.inhibitor_kills = s["inhibitorKills"]
		self.total_minions_killed = s["totalMinionsKilled"]
		self.neutral_minions_killed =  s["neutralMinionsKilled"]
		self.creep_score = self.total_minions_killed + self.neutral_minions_killed
		self.total_cc_time = s["totalTimeCrowdControlDealt"]
		self.champion_level = s["champLevel"]
		self.vision_wards_bought = s["visionWardsBoughtInGame"]
		self.sight_wards_bought = s["sightWardsBoughtInGame"]
		self.wards_placed = s["wardsPlaced"]
		self.wards_killed = s["wardsKilled"]
		self.first_blood_kill = s["firstBloodKill"]
		self.first_blood_assist = s["firstBloodAssist"]
		self.first_tower_kill = s["firstTowerKill"]
		self.first_tower_assist = s["firstTowerAssist"]
		self.runes = [s["perk0"], s["perk1"], s["perk2"], s["perk3"], s["perk4"], s["perk5"]]
		self.rune_primary = s["perkPrimaryStyle"]
		self.rune_secondary = s["perkSubStyle"]
		self.rune_stats = {self.runes[0]: [s["perk0Var1"], s["perk0Var2"], s["perk0Var3"]], self.runes[1]: [s["perk1Var1"], s["perk1Var2"], s["perk1Var3"]], self.runes[2]: [s["perk2Var1"], s["perk2Var2"], s["perk2Var3"]], self.runes[3]: [s["perk3Var1"], s["perk3Var2"], s["perk3Var3"]], self.runes[4]: [s["perk4Var1"], s["perk4Var2"], s["perk4Var3"]], self.runes[5]: [s["perk5Var1"], s["perk5Var2"], s["perk5Var3"]]}
		self.timeline = data["timeline"]
	
	def get_team(self, id):
		if not self.match_interface: return None
		if self.match_interface.teams[0].id == id: return self.match_interface.teams[0]
		return self.match_interface.teams[1]
		
	def __repr__(self):
		return f"<Player({self.name}, {self.champion.name}, {self.color}) at {hex(id(self))}>"
		
class Match():
	def __init__(self, data):
		self.data = data
		self.game_id = data["gameId"]
		self.platform_id = data["platformId"]
		self.creation_date = data["gameCreation"]
		self.duration = data["gameDuration"]
		self.queue_id = data["queueId"]
		self.map_id = data["mapId"]
		self.season_id = data["seasonId"]
		self.version = data["gameVersion"]
		self.mode = data["gameMode"]
		self.type = data["gameType"]
		i = 0; self.players = []; self.teams = []
		self.teams = [Team(t) for t in data["teams"]]
		for p in data["participants"]:
			self.players.append(Player(p, data["participantIdentities"][i]["player"])); i += 1
		self.teams[0].players = self.players[0:4]
		self.teams[1].players = self.players[5:10]
	
class RiotIF(RequestInterface):
	def __init__(self, logger=True):
		super(RiotIF, self).__init__()
		self.squasher = ErrorSquasher(logger)
		self.version_data = self.get_live_version()
		self.champion_rotation_data = self.get_champion_rotation()
		self.champion_data = self.get_champions()
		
	def get_champion_rotation(self):
		r = requests.get("https://na1.api.riotgames.com/lol/platform/v3/champion-rotations", headers=self.riot_headers)
		if r.status_code == 200:
			j = r.json()
			self.champion_rotation = j["freeChampionIds"]
		else:
			return self.squasher.squash(r, self.get_champion_rotation)
		j = None
		time.sleep(0.00001)
		return j
		
	def get_live_version(self):
		r = requests.get("https://ddragon.leagueoflegends.com/realms/na.json")
		j = r.json()
		self.version = j["v"]
		self.language = j["l"]
		self.cdn = j["cdn"]
		return j
	
	def get_champions(self):
		if not hasattr(self, "version"): self.get_live_version()
		r = requests.get(f"{self.cdn}/{self.version}/data/{self.language}/champion.json")
		j = r.json()["data"]
		self.champions = []
		for name in j:
			self.champions.append(Champion(j[name]))
			
		
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
match = matches[0]
player0 = match.players[0]
print(player0.name, player0.champion, player0.champion_level, player0.champion_damages)
print(match.players[5:10])
print(len(matches))
'''

		