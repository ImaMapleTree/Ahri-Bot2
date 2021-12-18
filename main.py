import nest_asyncio
nest_asyncio.apply()
import builtins
import discord
from discord_slash import SlashCommand
from discord_slash.utils.manage_commands import create_option, create_choice
from epyriot import base, extensions
builtins.CLIENT_LOADED = False #Unpythonic but allows me to reload underlying modules without re-initalizing the bot
from ahri import utils, interface, embeds

root_json = utils.JOpen("ahri/debuggers/root.json", "r")
interface_json = utils.JOpen("ahri/debuggers/matches.json", "r")
inter = base.RootIF.all_from_json(root_json, interface_json)
embeds.preload("root", inter.root, "interface", inter, "player", extensions.FullPlayer(inter.get_player(inter.root.name)), "matches", inter.matches, "partial_games", inter.searched_player)

builtins.CM = interface.ContextManager()
from ahri import command_front as cf
from _epy import epylog
import importlib	

def reload_front():
	print("Reloading CF")
	importlib.reload(cf)

cf.pass_module(interface)
cf.allow_self_reload(True, reload_front)

@client.event
async def on_component(ctx):
	await CM.handle_context(ctx)

@client.event
async def on_ready():
	print("Ready!")
	guild_ids = [guild.id for guild in client.guilds]
	utils.get_emoji_list(client)
	print(len(guild_ids))

builtins.CLIENT_LOADED = True
client.run('NjU5OTg3MTMyOTg2ODE4NTYw.XmgipA.thhPhuhmZ0WQzIBYAVSGlVwdAr0')