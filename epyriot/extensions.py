from epyriot import base
from epyriot import data_objects
from epyriot import utils
from epyriot import noimport_objects as nio
import datetime
import dateutil.relativedelta

def list_add(list1, list2):
	list1 += list2

def convert_players(player_list):
	return [FullPlayer(player) for player in player_list]
		
class LegacyFullMatch(base.Match):
	def __init__(self, match):
		super(FullMatch, self).__init__(None, match.interface)
		self.__dict__ = match.__dict__
		self.forbidden = ["game_id"]
		self.searched_player = FullPlayer(self.searched_player)
		self.time_since_creation = utils.current_epoch_difference(self.creation_date/1000)
		self.match_type = data_objects.QueueObject(base.Riot.queues[self.queue_id])
		self.map = base.Riot.maps[self.map_id]["name"]
		self.season = base.Riot.seasons[self.season_id]
		self.mode_info = base.Riot.modes[self.mode]
		self.gametype_info = base.Riot.gametypes[self.type]
		
class FullPlayer(base.Player):
	def __init__(self, player):
		super(FullPlayer, self).__init__(None, player.player_data, player.match)
		self.__dict__ = player.__dict__
		self.forbidden = player.forbidden + []
		self.friends = []
		friends = self.get_friends()
		for friend in friends: self.friends.append(data_objects.FriendObject(friend, friends[friend]))
		self.root = self.interface.root
		most_played = [nio.MostPlayedObject(mp[0], mp[1], self.interface) for mp in self.get_most_played(all=True)[:5]]
		self.region_short = self.root.region.replace("1", "").upper()
		self.mastery = [data_objects.MasteryObject(data) for data in self.root.mastery_data]
		self.most_played = nio.MostPlayedListObject(most_played)
		
		
		self.icon_url = self.root.icon_url
		self.ranked = self.root.get_division()
		
		self.last_game_as_player = self.interface.searched_player[0]
		self.time = self.last_game_as_player.match.time
		self.last_result = "Win" if self.last_game_as_player.win else "Loss"
		
		self.stats_string = f"{self.kills}/{self.deaths}/{self.assists}"
		self.kda = round((self.kills+self.assists)/self.deaths, 2) if self.deaths != 0 else "Perfect"
		self.cs = self.creep_score
		
		self.total_kills = base.tally(self.interface.searched_player, "kills")
		self.total_deaths = base.tally(self.interface.searched_player, "deaths")
		self.total_assists = base.tally(self.interface.searched_player, "assists")
		self.total_kda = round((self.total_kills+self.total_assists)/self.total_deaths, 2) if self.total_deaths != 0 else "Perfect"
		
		self.win_loss = base.count(self.interface.searched_player, "win")
		self.wins = self.win_loss.get(True); self.losses = self.win_loss.get(False)
		self.winrate = round((self.wins/(self.wins+self.losses)*100))

		self.win_streak = 0;
		latest = self.interface.searched_player[0].win
		while latest == True:
			latest = self.interface.searched_player[self.win_streak+1].win
			self.win_streak += 1
		
		self.loss_streak = 0;
		latest = self.interface.searched_player[0].win
		while latest == False:
			latest = self.interface.searched_player[self.loss_streak+1].win
			self.loss_streak += 1
			
		
		
	def get_friends(self):
		friends = []
		[list_add(friends, player.get_teammates()) for player in self.interface.searched_player]
		return base.count(friends, "name", sort=True)
		
	def __repr__(self):
		return f"<FullPlayer({self.name}, {self.champion.name}, {self.color}) at {hex(id(self))}>"