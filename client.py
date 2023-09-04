import asyncio
import json
from dotenv import load_dotenv
import os
import sys
import logging

import discord
from discord.ext import commands

from db_handler import DatabaseHandle

from cogs.bonk import Bonk
from cogs.messaging import Messaging
from cogs.music import Music
from cogs.web import Web

# load main references

load_dotenv() # guild id, channel id, bot oauth key
config = json.load(open("config.json")) # database configs and opus sound dir location

bot = commands.Bot(command_prefix = commands.when_mentioned_or("!"),
                   case_insensitive = True,
                   intents = discord.Intents.all(),
                   help_command = commands.DefaultHelpCommand(no_category="Commands"))

discord.utils.setup_logging(level=logging.INFO, root=True)

db_handler = DatabaseHandle(mongo_host = config["mongo-host"], mongo_port = config["mongo-port"])
db_handler.set_db(config["database"])
try:
    db_handler.client.server_info()
    logging.info("connected to database")
except:
    logging.error("database connection not established")
    sys.exit(1)

# events and helpers

@bot.event # load guild info, refresh member db, load commands (cogs)
async def on_ready():
    logging.info("connected to Discord")
    guild = bot.get_guild(int(os.getenv("guild_id")))
    if guild:
        logging.info(f"registered guild: {str(guild)}")
    else:
        logging.error("guild not found")
        sys.exit(1)

    db_members = list(db_handler.db["members"].find({}, {"member_id"}))
    db_members_ids = set(dct["member_id"] for dct in db_members)

    current_members_ids = [mem.id for mem in guild.members]

    new_member_template = json.load(open("db_member_template.json"))
    new_members = []
    
    for mem_id in current_members_ids:
        if mem_id not in db_members_ids:
            new_member = dict(new_member_template)
            new_member["member_id"] = mem_id
            new_members.append(new_member)
    if new_members:
        db_handler.db["members"].insert_many(new_members)
    logging.info("member database refreshed")
    
    await bot.add_cog(Bonk(bot, db_handler))
    await bot.add_cog(Music(bot, db_handler))
    await bot.add_cog(Messaging(bot, db_handler))
    await bot.add_cog(Web(bot, db_handler))
    logging.info("cogs loaded")


@bot.event # add member to db on join
async def on_member_join(member):
    if not db_handler.db["members"].find({"member_id":member.id}):
        new_member = json.load(open("db_member_template.json"))
        new_member["member_id"] = member.id
        db_handler.db["members"].insert_one(new_member)


@bot.event # process command if command message in correct channel
async def on_message(message:str):
    if message.author.id == bot.user.id:
        return
    if message.channel.id == int(os.getenv("commands_channel_id")):
        await bot.process_commands(message)


@bot.event # disconnect music player after everyone leaves and music is finished
async def on_voice_state_update(member, before, after):
    
    if member.guild.voice_client and before.channel and after.channel is None and \
       member.guild.voice_client.channel.id == before.channel.id:
           
        while member.guild.voice_client.is_playing() and len(member.guild.voice_client.channel.members) - 1 == 0:
            await asyncio.sleep(1)
        if not member.guild.voice_client.is_playing() and len(member.guild.voice_client.channel.members) - 1 == 0:
            commands_channel = bot.get_channel(int(os.getenv("commands_channel_id")))
            await member.guild.voice_client.disconnect()
            await commands_channel.send(f"Leaving channel: <#{commands_channel.id}>")
     

bot.run(os.getenv("bot_key"), log_handler=None)