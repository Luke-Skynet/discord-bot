import json

from dbhandler import DBhandle

import discord
from discord.ext import commands

info = json.load(open("info.json"))
config = json.load(open("dbfolder/config.json"))

intents = discord.Intents.all()

bot = commands.Bot(command_prefix='!', intents=intents)

guild:discord.Guild = None
commmand_channel:int = config["commands-channel-id"]

@bot.event
async def on_ready():
    print(f'Update: {bot.user} has connected to Discord!')
    guild = bot.get_guild(int(info["guild"]))
    if not guild:
        print("Error: guild not found")
        exit()
    else:
        print(f"Update: {bot.user} connected to guild: {str(guild)}")

@bot.event
async def on_message(message:str):
    if message.author == bot.user:
        return
    author = "<@" + str(message.author.id) + ">"
    swears = count_swears(message.content)
    if swears:
        await message.channel.send(author + " has said the following swear words: " + str(swears))
    
    await bot.process_commands(message)

def count_swears(string:str):
    swear_words = ("fuck", "shit", "uwu")
    counts = (string.lower().count(s) for s in swear_words)
    ret = {}
    for swear, count in list(zip(swear_words, counts)):
        if count > 0:
            ret[swear] = count
    return ret

@bot.command(name = "bonk", help='bonk a person being indecorous')
async def bonk(ctx:commands.Context, *arg:str):
    if ctx.channel.id != commmand_channel:
        await ctx.send(f"Please direct commands to the <#{commmand_channel}> channel")
        return
    
    for user in arg:
        if user == "<@" + str(bot.user.id) + ">":
            author = "<@" + str(ctx.message.author.id) + ">"
            await ctx.send(f"{author} tried to bonk the bot!")
            continue
        elif not user.strip("<@>").isnumeric() or not ctx.guild.get_member(int(user.strip("<@>"))):
            print(str(user) + " is not a member.")
            continue
        
        handle = DBhandle()
        handle.open()
        bonks = handle.get(user, default = 0) + 1
        handle.update(user, bonks)
        handle.close()
        await ctx.send(f"{user} has been bonked {str(bonks)} time{'s' if bonks > 1 else ''}!")

bot.run(info["key"])