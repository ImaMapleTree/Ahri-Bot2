import requests
import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup as Soup
import json
from quicktools import JOpen
from os import path

def chunker(seq, size):
	return (seq[pos:pos + size] for pos in range(0, len(seq), size))

async def get_data(session, url, headers={}):
	async with session.get(url, headers=headers, max_redirects=1000000) as response:
		response = await session.get(url, headers=headers)
		data = await response.text()
		return(data)

async def large_req(sites, headers={}):
	async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(20)) as session:
		tasks = []
		for url in sites:
			task = asyncio.ensure_future(get_data(session, url, headers))
			tasks.append(task)
		ret = await asyncio.gather(*tasks, return_exceptions=True)	
		return(ret)
		
async def wait_site(url):
	session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(20))
	async with session.get(url) as site:
		res = await site.read()
	return res

url = "http://ddragon.leagueoflegends.com/cdn/11.13.1/data/en_US/champion.json"

req = requests.get(url)
champs = req.json()
wiki_urls = []
opgg_urls = []

for key in champs["data"]:
	champ = champs["data"][key]
	name = champ["name"].replace(" ", "_")
	ref = champ["id"].replace(".", "").replace(" ", "").replace("'", "")
	wiki_urls.append(f"https://leagueoflegends.fandom.com/wiki/{name}/LoL")
	opgg_urls.append(f"https://na.op.gg/champion/{ref}/statistics/")
	
st = time.time()
wiki_sites = []
opgg_sites = []
i = 1
chunks = list(chunker(wiki_urls, 60))
for group in chunks:
	wiki_sites += (asyncio.run(large_req(group)))
	print(f"Finished chunk ({i} of {len(chunks)}) - Elapsed time: {time.time()-st}")
	i += 1

i = 1
chunks = list(chunker(opgg_urls, 10))
for group in chunks:
	opgg_sites += (asyncio.run(large_req(group)))
	print(f"Finished chunk ({i} of {len(chunks)}) - Elapsed time: {time.time()-st}")
	time.sleep(2)
	i += 1
	
champ_data = {}
for site in wiki_sites:
	try:
		soup = Soup(site, "html.parser")
		t = soup.title.text
		p1 = t.find(" (")
		name = t[:p1]
		
		candidates = soup.find_all("div", "pi-data-value")
		last_changed = None
		for candidate in candidates:
			a = candidate.a
			if a:
				if a.text.find("V") != -1:
					last_changed = a.text.replace("V", "")
					break
		
		since_last_change = 14 - int(last_changed.replace("11.", "").replace("10.", "").replace("9.", "").replace("8.", "").replace("7.", ""))
		champ_data[name] = {"name": name, "ahri_charm_amount": 10000000, "stock_price": 1, "stock_demand": 1, "history": {"price_timeline": [], "patch_winrate": {}, "last_patched": last_changed}, "patches_since_patched": since_last_change}
	except:
		pass

for site in opgg_sites:
	try: 
		soup = Soup(site, "html.parser")
		t = soup.find("div", "champion-stats-header-info")
		name = t.h1.text
		timeline = {}
		
		o = soup.find("div", "l-champion-statistics-content__side")
		s = o.div.contents[3].script.contents[0]
		spl = s.split(", ")
		js = spl[4]
		obj = json.loads(js)
		for point in obj:
			timeline[point["patchIndex"]] = point["y"]
		champ_data[name]["history"]["patch_winrate"] = timeline
	except:
		pass
	
for key in champ_data:
	p = path.join("dumps", key) + ".json"
	JOpen(p, "w+", champ_data[key])
