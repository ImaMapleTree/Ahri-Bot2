from ahri import data_manager, errors, utils
import matplotlib.pyplot as plt
import time
import threading
import os
import discord

class StockCompounder(threading.Thread):
	def __init__(self, *args, **kwargs):
		kwargs["daemon"] = True
		super(StockCompounder, self).__init__(*args, **kwargs)
		self.next_run = 0
		self.manager = data_manager.DataManager()
		self.stock_data = self.manager.stock_data
		self.catch_weight = 1.5
		
	def run(self):
		while True:
			if time.time() > self.next_run:
				st = time.time()
				for stock in self.stock_data:
					stock_info = self.stock_data[stock]
					CP5 = self.manager.ST5.get("cp5")
					if self.manager.ST5["tp5"] != 0:
						cDemand = stock_info["stock_demand"]
						cPrice = stock_info["stock_price"]
						MVR = CP5 / 1000000 #1,000,000
						MVR = MVR if MVR <= 1 else 1
						sCP5 = self.manager.ST5.get(stock, 0)
						self.manager.ST5[stock] = 0
						nDemand = cDemand + ((sCP5/CP5)*MVR) - (0.1*MVR*(cDemand/(cDemand*self.catch_weight)))
						nPrice = cPrice - (cPrice*(1-nDemand)*MVR)
						stock_info["stock_demand"] = nDemand
						stock_info["stock_price"] = nPrice
					dt =  stock_info["history"]["daily_timeline"]
					dt.append(stock_info["stock_price"])
					if len(dt) > 144: dt.pop(0)
					sp = os.path.join(self.manager.stock_path, stock_info["name"]) + ".json"
					utils.JOpen(sp, "w+", stock_info)
				self.manager.ST5["tp5"] = 0
				self.manager.ST5["cp5"] = 0
				self.next_run = time.time() + (60*5)
			else:
				time.sleep(5)
			
global compounder

def start_stock_compounder():
	global compounder
	compounder = StockCompounder(daemon=True)
	compounder.start()
	print(compounder)

def agreement(author):
	data_manager.DataManager().create_stock_entry(author)
	
def calculate_stock_cost(stock, total):
	price = get_price(stock)
	return total * price

def get_details(stock):
	stock_data = data_manager.DataManager().stock_data.get(stock.lower())
	if not stock_data: raise errors.InvalidStockError
	return stock_data

def get_price(stock):
	stock_data = data_manager.DataManager().stock_data.get(stock.lower())
	if not stock_data: raise errors.InvalidStockError
	return stock_data["stock_price"]
	
def graph(stock, graph_type):
	data = get_details(stock)["history"][graph_type]
	x_axis = []; x_label = None
	if graph_type == "price_timeline":
		name = "Weekly Price"
		[x_axis.append(i+1) for i in range(len(data))]
		x_label = "Week"; y_label = "Price (Charms)"
	elif graph_type == "daily_timeline":
		name = "Daily Price"
		[x_axis.append(((i+1)*5)/60) for i in range(len(data))]
		x_label = "Hourly (Hours passed)"; y_label = "Price (Charms)"
	#x_axis.reverse()
	plt.plot(x_axis, data)
	plt.xlabel(x_label)
	plt.ylabel(y_label)
	#plt.rcParams['axes.formatter.useoffset'] = False
	bot, top = plt.ylim()
	plt.ylim(0, top+5)
	plt.title(name)
	plt.savefig("cache/tempgraph.png")
	plt.clf()
	return discord.File("cache/tempgraph.png")
	
	
def purchase(user, stock, amount, cost, cps):
	manager = data_manager.DataManager()
	user_sd = manager.stock_ud.get(str(user.id))
	if user_sd["charms"] < cost: return f"**:x: Not enough charms to buy requested stock.** (Need {cost-user_sd['charms']} more)"
	stock_holdings = user_sd["stocks"].get(stock)
	if not stock_holdings: stock_holdings = {"amount": 0, "value": 0, "last_purchased": time.time()}
	stock_holdings["amount"] += amount
	stock_holdings["value"] = stock_holdings["amount"] * cps
	stock_holdings["last_purchased"] = time.time()
	user_sd["charms"] -= cost
	user_sd["stocks"][stock] = stock_holdings
	manager.ST5["cp5"] += cost
	manager.ST5["tp5"] += 1
	if stock not in manager.ST5: manager.ST5[stock.lower()] = 0
	manager.ST5[stock.lower()] += cost
	
	return f":white_check_mark: Successfully bought **{amount} {stock}** stocks for **{cost}** charms."