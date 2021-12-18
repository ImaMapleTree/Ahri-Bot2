import glob
from os import path
from _epy.quicktools import SplitFind, redict
from _epy import epyconfig
import epyriot
import discord
from ahri import utils, interface, errors
import codecs
import re
import builtins

global PRELOADED_DATA
PRELOADED_DATA = {}
def preload(*args):
	for i in range(int(len(args)/2)):
		PRELOADED_DATA[args[i*2]] = args[(i*2)+1]
	
class NoData():
	def __init__(self):
		pass
	
	def __str__(self):
		return "$NODATA"

class Prebuilt():
	def __init__(self):
		self.dot = "•"
		self.arrows = "《》"

class EmptyField(discord.embeds._EmptyEmbed):
	def __init__(self):
		super().__init__()
		
	@staticmethod
	def format(*args, **kwargs):
		return discord.embeds._EmptyEmbed()

def read_raw(source):
	with codecs.open(source, 'r', "utf-8") as f:
		txt = f.read().replace(" = ", "=").replace(" >= ", ">=").replace(" <= ", "<=").replace(" == ", "==").replace(" != ", "!=").replace("\r", "")
	return txt
	
def split_bracket(string):
	loc = string.find("[")
	if loc == -1: return string
	split, _, _ = SplitFind(string, "[", "]")
	return split
	
def find(string, term):
	found = True if string.find(term) != -1 else False
	return found
	
def shorten_source(source):
	i = source.rfind("\\")
	if i == -1: return source
	return source[i+1:].replace(".embed", "")
	
def split_conditional(string):
	conditionals = [">", "==", "<", ">=", "<=", "!="]
	for condition in conditionals:
		loc = string.find(condition)
		if loc != -1: return string[:loc]
	
def eval_condition(condition, marker, data, conditionals=None):
	domain = split_conditional(condition)
	domain_data = marker.eval_domain(data, domain, conditionals)
	if isinstance(domain_data, str): domain_data = '"' + domain_data + '"'
	condition = condition.replace("==", " == ").replace(">=", " >= ").replace("<=", " <= ").replace("!=", " != ")
	re_condition = re.sub(rf'\b{domain}\b', str(domain_data), condition)
	if re_condition == condition: re_condition = condition.replace(domain, str(domain_data))
	return re_condition
	
class DataMarker():
	def __init__(self):
		self.markers = 0
		self.data = {}
		self.old_data = {}
		self.variables = {}
		self.conditionals = {}
		self.emoji_markers = []
		self.functions = {"prettify": self.prettify, "remove_string_markers": self.remove_string_markers, "null_func": self.null_func, "eval": self.eval, "repr": self.repr, "space": self.space, "tally": self.tally}
	
	def add_marker(self, key, emoji=False):
		id = self.markers
		self.data["ID" + str(id)] = key
		self.markers += 1
		if emoji: self.emoji_markers.append("ID" + str(id))
		return "ID" + str(id)
		
	def set_variables(self, variables):
		self.variables= variables
		
	def set_conditionals(self, conditionals):
		self.conditionals=conditionals
		
	def freturn(self, function, ret, *args):
		if function: return self.functions[function](ret, *args)
		return ret
		
	def eval_domain(self, data, domain, variables=None, conditionals=None, function=None):
		if variables == None and self.variables == None: raise AttributeError
		if conditionals == None and self.conditionals == None: raise AttributeError
		if variables == None: variables = self.variables
		if conditionals == None: conditionals = self.conditionals
		args = ()
		def bracket_sub(attr):
			bracket = attr.find("[")
			if bracket == -1: return attr, None, False
			split = split_bracket(attr)
			attr = attr[:bracket]
			if not (split.find("'") == -1) or not (split.find('"') == -1): num = split.replace('"', "").replace("'", "")
			else: num = int(split)
			return attr, num, True
			
		if domain.find("(") != -1:
			pos1 = domain.find("(")
			function = domain[:pos1]
			domain = domain[pos1:].replace("(", "").replace(")", "").replace(", ", ",")
			if find(domain, ","):
				args = domain.split(",")
				domain = args[0]
				args = args[1:]
				if function == "eval":
					args.append(data)
					domain = self.functions["eval"](domain, *args)
					function = None
			

		if domain.find(".") == -1:
			if domain in variables.keys(): 
				renamed = variables[domain]
				if renamed.find(".") == -1:
					if renamed.startswith('"') and renamed.endswith('"'): return self.freturn(function, renamed.replace('"', ''), *args)
					elif renamed.startswith("'") and renamed.endswith("'"): return self.freturn(function, renamed.replace("'", ""), *args)
					return self.freturn(function, data[renamed])
			elif domain in conditionals:
				conditional = conditionals[domain]
				condition = conditional[0]
				condition = eval_condition(condition, self, data)
				if eval(condition): return self.eval_domain(data, conditional[1])
				return self.eval_domain(data, conditional[2])
				
			else:
				try: return self.freturn(function, data[domain], *args)
				except: return self.freturn(function, domain, *args)
		ext_count = domain.count(".")
		if ext_count > 10: raise errors.ParseError(9, domain, ext_count)
		attrs = domain.split(".")
		if attrs[0] in variables:
			attrs[0] = variables[attrs[0]]
			if attrs[0].find(".") != -1: attrs = attrs[0].split(".") + attrs[1:]
		checked_attr, num, isSub = bracket_sub(attrs[0])
		if isSub: 
			try: object = data[checked_attr][num]
			except: 
				try: object = self.eval_domain(data, checked_attr)[num];
				except IndexError: return NoData()
		else: object = data[checked_attr]
		for attr in attrs[1:]:
			checked, num, isSub = bracket_sub(attr)
			try:
				if checked == "forbidden": raise errors.ParseError(3, checked)
				if checked in object.forbidden: raise errors.ParseError(3, checked)
			except AttributeError: pass
			if isSub:
				try: object = getattr(object, checked)[num] #Add catch here
				except IndexError: raise errors.ParseError(7, f"{domain}.{checked}", num)
				except TypeError: raise erros.ParseError(8, f"{domain}.{checked}")
				except AttributeError: raise errors.ParseError(6, domain, checked)
			else:
				if not hasattr(object, checked): raise errors.ParseError(6, domain, checked)
				object = getattr(object, checked)
		return self.freturn(function, object, *args)
	
	def identify(self, data, variables=None, conditionals=None):
		if variables: self.set_variables(variables)
		if conditionals: self.set_conditionals(conditionals)
		if self.old_data == {}: self.old_data = self.data.copy()
		else: self.data = self.old_data.copy()
		for key in self.old_data:
			object = self.eval_domain(data, self.data[key])
			if key in self.emoji_markers:
				self.data[key] = utils.get_emoji(object)
			else: self.data[key] = object
				
	def prettify(self, data, *args):
		if args:
			if self.remove_string_markers(args[0]) == "time":
				return utils.timestamp_readable2(data)
		return '{:,}'.format(data)
		
	def remove_string_markers(self, string, *args):
		if string.startswith('"'): return string.replace('"', '')
		return string.replace("'", "")
		
	def eval(self, data, *args):
		if data not in self.conditionals: raise errors.ParseError(4, data)
		if eval(eval_condition(self.conditionals[data][0].replace("~", args[0]), self, args[1])): return self.conditionals[data][1]
		return self.conditionals[data][2]
		
	def space(self, data, spacer=" ."):
		spaces = []
		[spaces.append(spacer) for i in range(len(str(data)))]
		return "".join(spaces)
		
	def null_func(self, data, *args):
		return data
		
	def repr(self, data):
		return repr(data)
		
	def tally(self, object_list, attr):
		return epyriot.base.tally(object_list, attr)	

class EmbedLoader():
	def __init__(self, context_manager):
		self.embeds = redict()
		self.valid_shells = ["variables", "init", "inline-field", "field", "conditionals", "interface"]
		self.variable_shells = ["variables", "conditionals", "interface"]
		self.libraries = ["matches", "prebuilt", "player", "interface", "root"]
		self.CM = context_manager
	
	def _chop_equal(self, line):
		split = line.split("=")
		if len(split) == 1: return None, None
		conditional_first = False; conditional_second=False
		if len(split) == 2:
			return split[0], split[1]
		if find(split[0], ">") or find(split[0], "<") or find(split[0], "!"): conditional_first = True;
		elif split[1] == '': conditional_first = True;
		elif find(split[1], "if"): conditional_second = True
		if conditional_first:
			pos1 = line.find(split[2])-1
			ep = line.find("=", pos1)
		elif conditional_second:
			ep = line.find("=")
		else:
			ep = -1
		if ep == -1: return None, None
		return line[:ep], line[ep+1:]
		
	def _get_shell(self, line):
		shell, m1, m2 = SplitFind(line, "[[", "]]", bump=2)
		if m1 == -1 or m2 == -1: return None
		return shell.replace("[", "")
		
	def register_parsed(self, name, loaded, dir=""):
		pass
	
	def load(self, name, dir=""):
		source = path.join(dir, name)
		if not path.exists(source): open(source, "w+").write("")
		embed = self.text_parse(read_raw(source))
		embed.set_loader(self)
		embed.set_path(source)
		self.embeds[embed.identifier.name_path] = embed
		return embed
		
	def load_all(self, dir=""):
		slashes = ["/", "\\"]
		if dir != "":
			if dir[len(dir)-1] not in slashes: dir += "/"
		dir += "*.embed"
		load_list = glob.glob(dir)
		embeds_dict = {}
		for embed in load_list:
			embeds_dict[shorten_source(embed)] = self.load(embed)
		return embeds_dict
		
	def text_parse(self, text):
		embed = LoadedEmbed(text)
		shell_objects = {"init": EmbedInit, "inline-field": InlineField, "field": Field}
		shell_object = None
		shell = None
		lines = [line for line in text.split("\n") if line != ""]
		count = 0
		SKIP_TEST = False
		for line in lines:
			if len(line) == 1: continue
			if find(line, "534b49505f54455354"): SKIP_TEST = True; continue
			count += 1
			key, value = self._chop_equal(line)
			if shell == "interface":
				new_shell = self._get_shell(line)
				if not new_shell: 
					embed.interface_shell.add_line(line)
					continue
			if not key: #We know it's a shell
				new_shell = self._get_shell(line)
				if new_shell not in self.valid_shells: raise errors.ParseError(1, new_shell, count)
				if new_shell == shell: shell = None #marks the end of a shell
				elif new_shell not in self.variable_shells: shell=new_shell; shell_object = shell_objects[new_shell](); embed.shells.append(shell_object)
				else: shell = new_shell
				continue
			if shell not in self.variable_shells:
				try: shell_object.add_key(key, value)
				except errors.ParseError: raise errors.ParseError(2, key, count)
			elif shell == "conditionals":
				value = value.replace(" if ", "if").replace(" else ", "else")
				split1 = value.split("if")
				split2 = split1[1].split("else")
				condition = [split2[0], split1[0], split2[1]]; i = 0
				for item in list(condition):
					for var in reversed(embed.variables.keys()):
						if item.startswith(var + "["): item = item.replace(var, embed.variables.get(var)); break
						if item.startswith(var + "."): item = item.replace(var, embed.variables.get(var)); break
						condition[i] = item
						i += 1
				embed.conditionals[key] = condition
			else:
				if key == "color" or key == "colour": value = int(value)
				for var in reversed(embed.variables.keys()):
					if value.startswith(var + "["): value = value.replace(var, embed.variables.get(var)); break
					if value.startswith(var + "."): value = value.replace(var, embed.variables.get(var)); break
				embed.variables[key] = value
		if SKIP_TEST: return embed
		return self.test(embed)
		
	def test(self, embed, return_alive=False):
		self.embeds["TEST"] = embed
		gen = self.generate("TEST", **PRELOADED_DATA)
		if return_alive: return gen
		return embed
		
	def field_code(self, shell, data):	
		lines = []
		for line in shell.lines:
			if line[0].find("conditional_line") != -1:
				condition = split_bracket(line[0])
				condition = eval_condition(condition, shell.marker, data)
				if eval(condition): lines.append(line[1].format(**shell.marker.data))
			else: 
				txt = line[1].format(**shell.marker.data)
				if not find(txt, "$NODATA"): lines.append(txt);
		return lines
							
	def generate(self, key, **data):
		data.update({"prebuilt": Prebuilt()})
		embed = self.embeds[key]
		id = self.CM.create_session(data=data)
		real_embed = None
		fields = []
		for shell in embed.shells:
			shell.marker.identify(data, embed.variables, embed.conditionals)
			if shell.type == "init":
				title = shell.title.format(**shell.marker.data)
				desc = shell.description.format(**shell.marker.data)
				color = shell.color.format(**shell.marker.data)
				color = color if isinstance(color, discord.embeds._EmptyEmbed) else int(color, 16)
				real_embed = AliveEmbed(title=title, description=desc, color=color)
				if shell.author and not shell.author_icon: real_embed.set_author(name=shell.author.format(**shell.marker.data))
				if not shell.author and shell.author_icon: real_embed.set_author(name="No Author", icon_url=shell.author_icon.format(**shell.marker.data))
				if shell.author and shell.author_icon: real_embed.set_author(name=shell.author.format(**shell.marker.data), icon_url=shell.author_icon.format(**shell.marker.data))
				if shell.thumbnail: real_embed.set_thumbnail(url=shell.thumbnail.format(**shell.marker.data))
			if shell.type == "field":
				lines = self.field_code(shell, data)
				fields.append([shell.name.format(**shell.marker.data), lines, False])
			if shell.type == "inline":
				lines = self.field_code(shell, data)
				fields.append([shell.name.format(**shell.marker.data), lines, True])
		if not real_embed: raise ValueError
		for field in fields:
			txt = "\n".join(field[1])
			if len(txt) > 1024: raise errors.ParseError(5, len(txt))
			real_embed.add_field(name=field[0], value=txt, inline=field[2])
		real_embed.interface = embed.build_interface(id, data)
		return real_embed

class EmbedIdentity(dict):
	def __init__(self, name, name_path):
		super(EmbedIdentity, self).__init__()
		self.name = name
		self.name_path = name_path.replace("default_embeds.", "")
		self["name"] = name
		self["name_path"] = self.name_path
	
	def __hash__(self):
		return id(self.name) + id(self.name_path)
	
	def __eq__(self, obj):
		if not isinstance(obj, dict): return False
		if obj.get("name") == self.name and obj.get("name_path") == self.name_path: return True
		if id(obj) == id(self): return True
		return False
		
	def __repr__(self):
		return super().__repr__()

class LoadedEmbed():
	def __init__(self, txt):
		self.variables = redict()
		self.conditionals = redict()
		self.shells = []
		self.data_markers = []
		self.interface_shell = InterfaceShell()
		self.path = None
		self.loader = None
		self.raw = txt
	
	def set_loader(self, loader):
		self.loader = loader
	
	def set_path(self, path):
		self.path = path
		self.name_path = self.path[path.rfind("/")+1:].replace("\\", ".").replace(".embed", "")
		self.identifier = EmbedIdentity(shorten_source(self.path), self.name_path)
		
	def build_interface(self, id, data):
		if not self.interface_shell: return
		self.interface_shell.marker.identify(data, self.variables, self.conditionals)
		raw = "\n".join(self.interface_shell.lines).format(**self.interface_shell.marker.data)
		formatted_raw = raw.replace("&^", "{").replace("^&", "}")
		self.interface_cabinet = epyconfig.cabinet.from_string(formatted_raw)
		self.interface_raw = self.interface_cabinet.rank()
		self.interface = interface.create_interface(self.interface_raw, id)
		return self.interface
		
	def generate(self, **data):
		return self.loader.generate(self.identifier.name_path, **data)

class AliveEmbed(discord.Embed):
	def __init__(self, *args, **kwargs):
		super(AliveEmbed, self).__init__(*args, **kwargs)
		self.interface = None
		
	def set_interface(self, interface):
		self.interface = interface
		
	async def send(self, ctx, *args, **kwargs):
		await ctx.send(embed=self, components=self.interface, *args, **kwargs)
		
	async def edit_ctx(self, ctx, *args, **kwargs):
		await ctx.edit_origin(embed=self, components=self.interface, *args, **kwargs)
		
class EmbedPage():
	def __init__(self, pages=[]):
		self.pages = pages
		self.current_page = pages[0] if pages else None

class Shell():
	def __init__(self):
		self.marker = DataMarker()
	
	def _add_markers(self, line):
		old_line = line
		if old_line.find("{{") == -1: return []
		marker_name, pos1, pos2 = SplitFind(line, "{{", "}}", bump=2)
		old_line = old_line.replace("{"+marker_name+"}", self.marker.add_marker(marker_name))
		line = line[pos2:]
		while pos1 != 1:
			marker_name, pos1, pos2 = SplitFind(line, "{{", "}}", bump=2)
			if pos1 == 1: break
			old_line = old_line.replace("{"+marker_name+"}", self.marker.add_marker(marker_name))
			line = line[pos2:]
		return old_line
		
	def _add_marker_emojis(self, line):
		old_line = line
		if old_line.find("<<") == -1: return []
		marker_name, pos1, pos2 = SplitFind(line, "<<", ">>", bump=2)
		old_line = old_line.replace("<<"+marker_name+">>", "{"+self.marker.add_marker(marker_name, True)+"}")
		line = line[pos2:]
		while pos1 != 1:
			marker_name, pos1, pos2 = SplitFind(line, "<<", ">>", bump=2)
			if pos1 == 1: break
			old_line = old_line.replace("<<"+marker_name+">>", "{" +self.marker.add_marker(marker_name, True) + "}")
			line = line[pos2:]
		return old_line
		
	def add_key(self, key, value):
		if value.find("{{") != -1: value = self._add_markers(value)
		if value.find("<<") != -1: value = self._add_marker_emojis(value)
		if not hasattr(self, key): raise errors.ParseError(2, key)
		setattr(self, key, value)
		
class InterfaceShell(Shell):
	def __init__(self):
		super(InterfaceShell, self).__init__()
		self.lines = []
		
	def add_line(self, line):
		if line.find("{{") != -1: line = self._add_markers(line)
		if line.find("<<") != -1: line = self._add_marker_emojis(line)
		self.lines.append(line.replace("{", "&^").replace("}", "^&"))
			
	def __bool__(self):
		return bool(self.lines)

class EmbedInit(Shell):
	def __init__(self):
		super().__init__()
		self.type = "init"
		self.title = EmptyField()
		self.author = None
		self.description = EmptyField()
		self.color= EmptyField()
		self.author_icon= None
		self.thumbnail= None

class Field(Shell):
	def __init__(self):
		super().__init__()
		self.type = "field"
		self.name = None
		self.lines = []
		
	def add_key(self, key, value):
		if value.find("{{") != -1: value = self._add_markers(value)
		if value.find("<<") != -1: value = self._add_marker_emojis(value)
		if key.find("line") == -1: 
			if not hasattr(self, key): raise errors.ParseError(2, key)
			super().add_key(key, value)
		else: self.lines.append([key, value])
			
class InlineField(Field):
	def __init__(self):
		super().__init__()
		self.type = "inline"