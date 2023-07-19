import json
import os

import discord
from discord.ext import commands

info = json.load(open("dbfolder/info.json"))
intents = discord.Intents.default()
intents.message_content = True


client = discord.Client(intents=intents)

@client.event
async def on_ready():
    print(f'{client.user} has connected to Discord!')

@client.event
async def on_message(message):
    if message.author == client.user:
        return
    await message.channel.send("hi " + str(message.author))
client.run(info["key"])