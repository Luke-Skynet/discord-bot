import json
import os
import discord

from dbhandler import DBhandle

from discord.ext import commands

info = json.load(open("dbfolder/info.json"))
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!',intents=intents)

# bot commands

@bot.command(name='bonk', help='bonk a person being indecorous')
async def bonk(ctx, *args):
    handle = DBhandle()
    handle.open()
    handle.update(args[0], handle.get(args[0]) + 1)
    await ctx.send(str(args[0]) + " has been bonked " + str(handle.get(args[0]) + 1) + " times.")

bot.run(info["key"])

