import logging
import requests
import json
import random

import discord
from discord.ext import commands

from cogs.parent import ParentCog

class Web(ParentCog):
    
    def __init__(self, bot, db_handler):
        super().__init__(bot, db_handler)
        self.animals = ["cat","dog","bird","panda","redpanda","koala",
                        "fox","dolphin","kangaroo","bunny","lion","bear",
                        "frog","duck","penguin","axolotl","capybara"]


    @commands.hybrid_group(name = "animal", help="show a random picture and fact about an animal")
    async def animal(self, ctx:commands.Context,
                     search:str = commands.parameter(description= "- the specific animal you want (cat, dog, etc.)",
                                                     default=None, displayed_default=None)):
        
        request = requests.get(f"https://api.animality.xyz/all/{search or random.choice(self.animals)}")
        if request.status_code != 200:
            return
        
        dct = request.json()
        embed = discord.Embed(description=dct["fact"])
        embed.set_image(url = dct["link"])
        
        logging.info(f"{ctx.author.name} successfully requested animal: {search}")
        await ctx.send(embed = embed)
     
     
    @animal.command(name = "list", help="- show list of animals that that can be called", aliases = ("help",))
    async def which_animals(self, ctx:commands.Context):
        
        logging.info(f"{ctx.author.name} successfully requested animal list")
        await ctx.send(f"Here is the list of animals you can ask for:\n {self.animals}")
    
    
    @commands.hybrid_group(name = "pokemon", help="get a picture and pokedex entry of a pokemon", aliases=("pokedex",))
    async def pokemon(self, ctx:commands.Context,
                      search:str = commands.parameter(description= "- name or pokedex number",
                                                      default=None, displayed_default=None)):
        
        request = requests.get("https://pokeapi.co/api/v2/pokedex/1")
        if request.status_code != 200:
            logging.error(f"status code {request.status_code} received on pokedex request")
            return
        
        entry = next((dct for dct in request.json()["pokemon_entries"] if dct["pokemon_species"]["name"] == search.lower() or str(dct["entry_number"]) == search), None)
        
        if entry is not None:
            
            pokemon_species_request = requests.get(entry["pokemon_species"]["url"])
            if pokemon_species_request.status_code != 200:
                logging.error(f"status code {pokemon_species_request.status_code} received on pokemon species request")
                return
            pokedex_entry = random.choice([dct["flavor_text"] for dct in pokemon_species_request.json()["flavor_text_entries"] if dct["language"]["name"] == "en"])
            
            pokemon_data_request = requests.get(f"https://pokeapi.co/api/v2/pokemon/{entry['pokemon_species']['name']}")
            if pokemon_data_request.status_code  != 200:
                logging.error(f"status code {pokemon_data_request.status_code} received on pokemon data request")
                return
            pokedex_picture = pokemon_data_request.json()["sprites"]["other"]["official-artwork"]["front_default"]
            
            embed = discord.Embed(description=pokedex_entry)
            embed.set_image(url = pokedex_picture)
            
            logging.info(f"{ctx.author.name} successfully requested pokemon: {search}")
            await ctx.send(embed = embed)