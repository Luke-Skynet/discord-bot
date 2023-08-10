import json
from dotenv import load_dotenv
import os
import sys
import logging

import discord
from discord.ext import commands
from discord.utils import get

from db_handler import DatabaseHandle

from cogs.bonk import Bonk
from cogs.messaging import Messaging
from cogs.music import Music
from cogs.web import Web

# load main references

load_dotenv() # guild id, channel id, bot oauth key
config: dict
with open("config.json") as handle:
    config = json.load(handle)

bot = commands.Bot(command_prefix = commands.when_mentioned_or("!"),
                   case_insensitive = True,
                   intents = discord.Intents.all(),
                   help_command = commands.DefaultHelpCommand(no_category="Commands"))
commands_channel_id = int(os.getenv("commands_channel_id"))

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

@bot.event
async def on_ready():
    logging.info("connected to Discord")
    guild = bot.get_guild(int(os.getenv("guild_id")))
    if guild:
        logging.info(f"registered guild: {str(guild)}")
    else:
        logging.error("guild not found")
        sys.exit(1)

    query = list(db_handler.db["members"].find({}, {"member_id"}))
    db_members_ids = set(dct["member_id"] for dct in query)

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

@bot.event
async def on_member_join(member):
    if not db_handler.db["members"].find({"member_id":member.id}):
        new_member = json.load(open("db_member_template.json"))
        new_member["member_id"] = member.id
        db_handler.db["members"].insert_one(new_member)

@bot.event
async def on_message(message:str):
    if message.author.id == bot.user.id:
        return
    if message.channel.id == commands_channel_id:
        await bot.process_commands(message)
        
bot.run(os.getenv("bot_key"), log_handler=None)