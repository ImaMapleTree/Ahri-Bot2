from epyriot import base

class MostPlayedObject():
	def __init__(self, champion, games):
		self.forbidden = []
		self.name = champion.name
		self.champion = champion
		self.games = games
		self.image_url = champion.get_image_url()
		
class FriendObject():
	def __init__(self, name, games):
		self.forbidden = []
		self.name = name
		self.games = games
		
class MasteryObject():
	def __init__(self, data):
		self.forbidden = []
		self.champion_id = data["championId"]
		self.champion = base.Champion.from_ref(self.champion_id)
		self.level = data["championLevel"]
		self.points = data["championPoints"]
		self.pretty_points = '{:20,.2f}'.format(self.points).replace(".00", "")
		self.last_played = data["lastPlayTime"]
		self.points_since_levelup = data["championPointsSinceLastLevel"]
		self.points_until_levelup = data["championPointsUntilNextLevel"]
		self.chest_available = not data["chestGranted"]
		self.tokens_earned = data["tokensEarned"]