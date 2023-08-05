import logging
import requests
import json
import random

import discord
from discord.ext import commands

from cogs.parent import ParentCog

class API(ParentCog):
    
    def __init__(self, bot, db_handler):
        super().__init__(bot, db_handler)
        self.animals = ["cat","dog","bird","panda","redpanda","koala",
                        "fox","dolphin","kangaroo","bunny","lion","bear",
                        "frog","duck","penguin","axolotl","capybara"]

    @commands.hybrid_group(name = "animal", help="show a random picture and fact about an animal")
    async def animal(self, ctx:commands.Context,
                     animal:str = commands.parameter(description= "- the specific animal you want (cat, dog, etc.)",
                                                     default=None, displayed_default=None)):
        
        request = requests.get(f"https://api.animality.xyz/all/{animal or random.choice(self.animals)}")
        if request.status_code != 200:
            return
        
        dct = json.loads(request._content.decode('utf-8'))
        
        embed = discord.Embed(description=dct["fact"])
        embed.set_image(url = dct["link"])
        
        await ctx.send(embed = embed)
     
    @animal.command(name = "list", help="- show list of animals that that can be called", aliases = ("help",))
    async def which_animals(self, ctx:commands.Context):
        await ctx.send(f"Here is the list of animals you can ask for:\n {self.animals}")