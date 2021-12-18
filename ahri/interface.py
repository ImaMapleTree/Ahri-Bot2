from ahri import errors, data_manager, embeds
from discord_slash.utils.manage_components import create_button, create_actionrow, create_select_option, create_select
from discord_slash.model import ButtonStyle
from _epy.quicktools import SplitFind
from ahri import utils, stocks

def create_option(opt_dict):
	label = opt_dict.get("label") if opt_dict.get("label") else ""
	if opt_dict.get("embed"): value = "switch_embed(" + str(opt_dict.get("embed")) + ")"
	elif opt_dict.get("value"): value = opt_dict.get("value")
	else: value = ""
	emoji = opt_dict.get("emoji")
	description = opt_dict.get("description")
	default = opt_dict.get("default") if opt_dict.get("default") != None else False
	return create_select_option(label, value, emoji, description, default)

def create_interface(raw_dict, id=None):
	styles = {"blue": ButtonStyle.blue, "blurple": ButtonStyle.blurple, "grey": ButtonStyle.grey, "gray": ButtonStyle.grey, "green": ButtonStyle.green, "red": ButtonStyle.red, "URL": ButtonStyle.URL, "primary": ButtonStyle.primary, "secondary": ButtonStyle.secondary, "success": ButtonStyle.success, "danger": ButtonStyle.danger}
	components = []
	i = 0
	for row_name in raw_dict:
		arc = []; has_button = False; has_select = False
		row = raw_dict[row_name]
		for comp in row:
			if len(arc) >= 5: raise errors.PackedRowError
			if comp["type"] == 1:
				if has_select: raise errors.InvalidButtonError(True)
				has_button = True
				style = styles[comp.get("style")] if type(comp.get("style")) == type("") else comp.get("style")
				if not style: style = ButtonStyle.primary
				label = comp.get("label") if comp.get("label") else ""
				#if comp.get("embed"): value = "switch_embed(" + comp.get("embed") + ")"
				#elif comp.get("value"): value = comp.get("value")
				#else: value = ""
				if id: custom_id = id
				else: custom_id = comp.get("custom_id")
				emoji = comp.get("emoji")
				if emoji: emoji = utils.get_emoji(emoji)
				url = comp.get("url")
				disabled = comp.get("disabled") if comp.get("disabled") != None else False
				if custom_id: custom_id = str(custom_id) + "-" + str(i)
				button = create_button(style, label, emoji, custom_id, url, disabled)
				arc.append(button)
				i += 1
				
			if comp["type"] == 2:
				if has_select or has_button: raise errors.InvalidButtonError(True)
				has_select = True; has_button = True
				options = [create_option(opt) for opt in comp["options"]]
				if id: custom_id = id
				else: custom_id = comp.get("custom_id")
				label = comp.get("label") if comp.get("label") else comp.get("placeholder")
				min = comp.get("min") if comp.get("min") else comp.get("min_values")
				max = comp.get("max") if comp.get("max") else comp.get("max_values")
				disabled = comp.get("disabled") if comp.get("disabled") != None else False
				if custom_id: custom_id = str(custom_id)
				button = create_select(options, custom_id, label, min, max, disabled)
				arc.append(button)
		components.append(create_actionrow(*arc))
	return components
				

class ContextManager():
	def __init__(self):
		self.sessions = {}
		self.DM = data_manager.DataManager()
		self.embed_loader = embeds.EmbedLoader(self)
		self.embed_loader.load_all("ahri/default_embeds")
		self.DM.register_embeds(self.embed_loader.embeds)

	def create_session(self, id=None, data={}):
		if not id: id = utils.UUID().uuid
		self.sessions[str(id)] = data
		return id

	def _cmd_split(self, txt):
		txt = txt.replace(", ", ",")
		p1 = txt.find("(")
		cmd = txt[:p1]
		unsplit, _, _ = SplitFind(txt, "(", ")")
		args = unsplit.split(",")
		return cmd, args
		
	async def handle_context(self, ctx):
		if utils.find(ctx.custom_id, "-"):
			s = ctx.custom_id.split("-")
			custom_id = s[0]; opt = s[1]
			cmd = self.sessions.get(str(custom_id))["command"]
			if cmd == "accept_stock_agreement": await self.accept_stock_agreement(opt, ctx, custom_id)
			if cmd == "purchase_stock":
				await self.purchase_stock(opt, ctx, custom_id)
			
		else:
			for value in ctx.values:
				cmd, args = self._cmd_split(value)
				if cmd == "switch_embed": await self.switch_embed(args[0], ctx)
		
	async def switch_embed(self, id, ctx):
		embed = self.DM.get_embed(id)
		if not embed: return
		data_id = ctx.custom_id
		gen = embed.generate(**self.sessions.get(str(data_id), {}))
		await gen.edit_ctx(ctx) #ctx.edit_origin(embed=gen)
	
	async def purchase_stock(self, opt, ctx, id):
		if opt == "1": await ctx.edit_origin(content=":x: **Purchase Cancelled**", embed=None, components=[])
		else:
			sd = self.sessions.get(str(id))
			await ctx.edit_origin(content=stocks.purchase(sd["user"], sd["stock"], sd["amount"], sd["cost"], sd["cost_per_stock"]), embed=None, components=[])
		
	async def accept_stock_agreement(self, opt, ctx, id):
		if opt == "0":
			stocks.agreement(self.sessions.get(str(id))["user"])
			await ctx.edit_origin(content=":white_check_mark: **Agreement Accepted**", embed=None, components=[])
		else:
			await ctx.edit_origin(content=":x: **Agreement Denied**", embed=None, components=[])
		