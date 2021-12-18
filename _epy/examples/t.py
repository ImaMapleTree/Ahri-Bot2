import _epy.epygraphics as graphics
from _epy.epygraphics import Window, WindowThread, WinWait, Clock, ThreadClock, Colors, LiveData
from epysim import Agent, RandomMove
import threading
import multiprocessing
import random
import math
import time

global cdict
total = LiveData(default_key="total")
last_peeps = []

def updateCount(colorDict):
	for key in cdict.keys():
		pair = cdict[key]
		pair[0].setText(key + " " +str(pair[1]))
	
def getInfection(host, victims):
	if not host.tags.get("infected"): return
	global cdict
	global last_peeps
	color = host["color"]
	for victim in victims:
		if victim["infected"] and victim["color"] != color:
			if random.randint(0, 10) > 5: victim.remove(); cdict[victim["color"]][1] -= 1
		if victim["color"] != color:
			if victim.tags.get("color"): cdict[victim["color"]][1] -= 1
			victim["infected"] = True
			victim.color(color)
			cdict[color][1] += 1
			
class MovingThread(threading.Thread):
	def __init__(self, agents, clock, *args, **kwargs):
		super(MovingThread, self).__init__(*args, **kwargs)
		self.agents = agents
		self.clock = clock
		self.clock.add_to_cycle(self, self.tick)
		
	def tick(self):
		#self.clock.delay = 0
		active_list = list(self.agents)
		for agent in active_list:
			if agent.body._ref == None: self.agents.pop(self.agents.index(agent))
			agent.auto_move()
		if len(self.agents) == 0: self.clock.remove_from_cycle(self)

def createAgents(window, n, r=4, infected=random.randint(1,8)):
	rm = RandomMove(random.randint(4,10))
	agents = []
	used_colors = {}
	for i in range(n):
		c = window.createCircle(r, fill="black", width=0, allow_collisions=True, collision_wrapper=getInfection)
		c.place(x=random.uniform(0, window.width), y=random.uniform(0, window.height))
		if i < infected: 
			color = random.choice(Colors.MAIN_COLORS);
			if not color in used_colors.keys(): used_colors[color] = 0
			used_colors[color] += 1; 
			c.color(color); 
			c["infected"] = True
		agent = Agent(c, rm)
		agents.append(agent)
	return agents, used_colors
	
def createThreads(n, apt, agents, clock, target=None):
	threads = []
	for i in range(n):
		#t = threading.Thread(target=target, args=(agents[apt*i:(apt+1)*i],clock), daemon=True)
		t = MovingThread(agents[apt*i:(i+1)*apt], clock, daemon=True)
		t.start()
		threads.append(t)
	return threads
		
window = Window(800, 800, auto_start=False)
windowthread = WindowThread(window, daemon=True)
windowthread.start()

WinWait(window)

agents, colors = createAgents(window, 1000, 4)
threads = createThreads(1000, 1, agents, window.clock.getTC())
label = window.createLabel(text="Alive Status", size=15, font="Times", bg="black", fill="white")
label.place(x=60, y=20)

h = 0
cdict = {}
for color in colors.keys():
	clabel = window.createLabel(text=color + " " + str(colors[color]), size=15, font="Times", bg="white", fill=color, border_width=2, padx=4, pady=4)
	clabel.place(x=60, y=50+(h*30))
	h+= 1
	cdict[color] = [clabel, colors[color]]

window.clock.schedule_interval(updateCount, 0.1, cdict)
window.clock.getTC().target_fps = 60
window.clock.startTC()

window.wait()