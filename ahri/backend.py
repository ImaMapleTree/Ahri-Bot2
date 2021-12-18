import nest_asyncio
nest_asyncio.apply()
from epyriot import base, extensions
import traceback
import psutil
from ahri import utils, embeds, data_manager, errors, stocks
import sys
import os
import time
from discord_slash.utils.manage_components import create_button, create_actionrow
from discord_slash.model import ButtonStyle

import importlib

global client
global data_manager
global modules
global context_manager

manager = data_manager.DataManager()
stocks.start_stock_compounder()

def pass_client(c):
	global client
	client = c
	
def pass_context_manager(c):
	global context_manager
	context_manager = c
	
async def debug(ctx):
	await manager.embed_by_string("debug3").generate().send(ctx)
	return

def get_modules():
	modules = {}
	module_names = [key for key in globals().keys() if isinstance(globals()[key], type(sys)) and not key.startswith('__')]
	hooked_modules = [embeds]
	for module in hooked_modules:
		for mod in dir(module):
			if type(getattr(module, mod)) == type(sys):
				modules[mod] = getattr(module, mod)
	for name in module_names:
		modules[name] = globals()[name]
	return modules

modules = get_modules()

async def reload(module):
	global embed_loader
	modules = get_modules()
	if module == "all": [importlib.reload(modules[name]) for name in modules.keys()]
	elif module == "embeds": importlib.reload(modules[module]); context_manager.embed_loader=embeds.EmbedLoader(context_manager); context_manager.embed_loader.load_all("ahri/default_embeds")
	else: importlib.reload(modules[module])
	print(f"Reloaded: {module}")
	
def restart_program():
	try:
		p = psutil.Process(os.getpid())
		for pid in p.children(recursive=True):
			pid.terminate()
	except:
		traceback.print_exc()
	python = sys.executable
	os.execl(python, python, *sys.argv)
	
	
async def register_embed(name, embed_text, author):
	try: parsed = context_manager.embed_loader.text_parse(embed_text)
	except Exception as e: return str(e).replace("ParseError", "[Parser]")
	try: id = manager.write_embed(name, parsed, os.path.join("ahri/user_data", str(author.id)))
	except errors.MaxEmbedError as e: return str(e)
	return f"Successfully registered embed (**{name}**) with ID (**{id}**)"
		
async def test_embed(embed_text, author):
	try: parsed = context_manager.embed_loader.text_parse(embed_text)
	except Exception as e: print("EXCEPTION!", e); return str(e).replace("ParseError", "[Parser]")
	return context_manager.embed_loader.test(parsed, return_alive=True)
	
async def confirm_stock_purchase(author, stock, amount):
	if str(author.id) not in manager.stock_ud: return ":x: **In order to participate in the stock game you must read the disclaimer. Use __/stock signup__ for more info**"
	cost_per_stock = stocks.get_price(stock)
	total_cost = stocks.calculate_stock_cost(stock, amount)
	return manager.embed_by_string("stock_purchase_confirm").generate(**{"user": author, "stock": stock, "amount": amount, "cost": total_cost, "cost_per_stock": cost_per_stock, "command": "purchase_stock"})
	
async def show_stock_details(stock):
	data = stocks.get_details(stock)
	return manager.embed_by_string("stock_details").generate(**{"stock": stock, "cost": data["stock_price"], "last_change": data["history"]["last_patched"], "price_timeline": data["history"]["price_timeline"], "patches_since_change": data["patches_since_patched"]})
	
async def prepose_stock_agreement(author):
	if str(author.id) in manager.stock_ud: return ":x: **You've already agreed to this agreement, use /stock userdata for information on how to delete your data.**"
	return manager.embed_by_string("stock_agreement").generate(**{"user": author, "command": "accept_stock_agreement"})

async def stock_quantify(stock, cost):
	return cost/(stocks.get_price(stock))
	
async def stock_graph(stock, graph_type):
	return stocks.graph(stock, graph_type)
	

async def player_lookup(name, region="NA1", champion=None, games=50):
	params = {}
	st = time.time()
	if champion: params["champion"] = base.Champion.from_ref(champion)
	root = base.RootIF(name=name, region=region.lower())
	interface = root.createInterface(**params)
	matches = interface.request_matches()
	print("Interntal time:", time.time()-st)
	data = {"interface": interface, "player": extensions.FullPlayer(interface.get_player(name)), "root": root, "matches": matches, "partial_games": interface.searched_player}
	print("Calculation time:", time.time()-st)
	embed = manager.embed_by_string("player_summary").generate(**data)
	return embed