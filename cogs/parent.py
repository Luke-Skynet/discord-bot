import asyncio
import logging
import re

import discord
from discord.ext import commands

from db_handler import DBhandle


class ParentCog(commands.Cog):
    
    def __init__(self, bot, db_handler):
        
        self.bot:commands.Bot = bot
        self.db_handler:DBhandle = db_handler
    
    def get_mentioned_member(cls, mention:str, ctx:commands.Context) -> discord.Member:
        if mention is not None and re.match("<@\d+>", mention):
            return ctx.guild.get_member(int(mention.strip("<@>")))
        elif mention is None:
            asyncio.run_coroutine_threadsafe(ctx.send("No @person entered"), ctx.bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send(f"{mention} is not a member"), ctx.bot.loop)
        return None