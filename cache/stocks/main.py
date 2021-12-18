import requests
import asyncio
import aiohttp
import time
from bs4 import BeautifulSoup as Soup
import json
from quicktools import JOpen
from os import path
import glob

files = glob.glob("*.json")
for file in files:
	f = open(file, "r+")
	txt = f.read()
	f.close
	txt = txt.replace("ahri_charm_amount", "total_shares")
	
	f = open(file, "w+")
	f.write(txt)
	f.close()
	
	j = JOpen(file, "r+")
	j["history"]["daily_timeline"] = []
	
	if j["patches_since_patched"] < 0: print(j["name"])
	
	JOpen(file, "w+", j)