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

    @commands.hybrid_group(name = 'pokemon', help="get a picture and pokedex entry of a pokemon")
    async def pokemon(self, ctx:commands.Context, search:str):
        
        message = await ctx.defer()
        request = requests.get("https://pokeapi.co/api/v2/pokedex/1")
        if request.status_code != 200:
            logging.error(f"status code {request.status_code} received on pokedex request")
            return
        
        search = '-'.join(search.split())
        entry = next((dct for dct in request.json()["pokemon_entries"] if dct["pokemon_species"]["name"] == search.lower() or str(dct["entry_number"]) == search), None)
        
        if entry is None:
            logging.error(f"{ctx.author.name} unsuccessfully searched the pokemon: {search}")
            
        else:
            pokemon_species_request = requests.get(entry["pokemon_species"]["url"])
            if pokemon_species_request.status_code != 200:
                logging.error(f"status code {pokemon_species_request.status_code} received on pokemon species request: : {pokemon_species_request.request.url}")
                return
            pokemon_species_json = pokemon_species_request.json()
            pokedex_entry = ("The pokedex entry for this pokemon has not been updated." if not pokemon_species_json["flavor_text_entries"] else 
                             random.choice([dct["flavor_text"] for dct in pokemon_species_json["flavor_text_entries"] if dct["language"]["name"] == "en"]) )
            
            pokemon_data_request = requests.get(f"https://pokeapi.co/api/v2/pokemon/{entry['pokemon_species']['name']}")
            if pokemon_data_request.status_code  != 200:
                logging.error(f"status code {pokemon_data_request.status_code} received on pokemon data request: {pokemon_data_request.request.url}")
                return
            pokedex_picture = pokemon_data_request.json()["sprites"]["other"]["official-artwork"]["front_default"]
            
            logging.info(f"{ctx.author.name} successfully requested pokemon: {search}")
            
            embed = discord.Embed(description=pokedex_entry)
            embed.set_image(url = pokedex_picture)
            
            await ctx.send(embed = embed)