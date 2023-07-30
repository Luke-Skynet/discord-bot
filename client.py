import json
from dotenv import load_dotenv
import os
import re
import asyncio
import time

import discord
from discord.ext import commands
from discord.utils import get

from db_handler import DBhandle
from music_handler import MusicHandle

# load main references

load_dotenv() # guild id and bot oauth key
config = json.load(open("config.json"))

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), case_insensitive=True, intents=discord.Intents.all())
guild:discord.Guild = None

music_handle = MusicHandle()
music_handle.load_settings(config["opus-dir"])

db_handle = DBhandle(in_docker = bool(config["docker"]))
db_handle.set_db(config["database"])

# commands

@bot.event
async def on_ready():
    print(f'Update: {bot.user} has connected to Discord!')
    guild = bot.get_guild(int(os.getenv("guild")))
    if not guild:
        print("Error: guild not found")
        exit()
    else:
        print(f"Update: {bot.user} registered guild: {str(guild)}")

    query = list(db_handle.db["members"].find({}, {"member_id"}))
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
        db_handle.db["members"].insert_many(new_members)
    print("Update: member database refreshed")

@bot.event
async def on_member_join(member):
    if not db_handle.db["members"].find({"member_id":member.id}):
        new_member = json.load(open("db_member_template.json"))
        new_member["member_id"] = member.id
        db_handle.db["members"].insert_one(new_member)

@bot.event
async def on_message(message:str):
    if message.author == bot.user:
        return
    author = "<@" + str(message.author.id) + ">"
    swears = count_swears(message.content)
    if swears:
        await message.channel.send(author + " has said the following swear words: " + str(swears))

    if message.channel.id == config["commands-channel-id"]:
        await bot.process_commands(message)

def count_swears(string:str):
    swear_words = ("fuck", "shit", "uwu")
    counts = (string.lower().count(s) for s in swear_words)
    ret = {}
    for swear, count in list(zip(swear_words, counts)):
        if count > 0:
            ret[swear] = count
    return ret

@bot.command(name = "bonk", help="bonk a person being indecorous", aliases = ("b",))
async def bonk(ctx:commands.Context,
               member: str = commands.parameter(description=" - the person you want to bonk.", default=None, displayed_default=None),
               *, reason: list = commands.parameter(description=" - why they deserve to be bonked.", default="no reason")):
    
    if not member:
        return
    bonk_time = round(time.time())
    bonk_reason = ''.join(reason)
    
    if member == "<@" + str(bot.user.id) + ">":
        author = "<@" + str(ctx.message.author.id) + ">"
        await ctx.send(f"{author} tried to bonk the bot!")
        return
    
    if not re.match("<@\d+>", member) or not ctx.guild.get_member(int(member.strip("<@>"))):
        await ctx.send(f"{member} is not a member.")
        return
    
    member_id = int(member.strip("<@>"))

    db_handle.db["members"].update_one(
        {"member_id": ctx.message.author.id},
        {"$inc": {"bonks_given": 1},
         "$set": {"last_bonk_given": member_id,
                  "last_bonk_given_time": bonk_time,
                  "last_bonk_given_reason": bonk_reason}
        }
    )
    bonked_result = db_handle.db["members"].find_one_and_update(
        {"member_id": member_id},
        {"$inc": {"bonks_received": 1},
         "$set": {"last_bonked_by": ctx.message.author.id,
                  "last_bonked_by_time": bonk_time,
                  "last_bonked_by_reason": bonk_reason},
         "$push":{"bonk_reasons": bonk_reason}
        }
    )

    bonks = bonked_result["bonks_received"] + 1
    await ctx.send(f"{member} has been bonked {str(bonks)} time{'s' if bonks != 1 else ''}!")

@bot.command(name = "bonkinfo", help="view a person's bonk statistics (last bonk and reason)")
async def bonkinfo(ctx:commands.Context,
                   member: str = commands.parameter(description=" - the person you want to look up. Leave blank to look up yourself.", default=None, displayed_default=None)):
    
    member_id = ctx.author.id
    if member: 
        if member == "<@" + str(bot.user.id) + ">":
            await ctx.send("I cannot be bonked.")
            return
        elif not re.match("<@\d+>", member) or not ctx.guild.get_member(int(member.strip("<@>"))):
            await ctx.send(f"{member} is not a member.")
            return
        else:
            member_id = int(member.strip("<@>"))

    doc = db_handle.db["members"].find_one({"member_id":member_id})

    string = f"Bonk statistics for <@{member_id}>: \n" + \
             f"\t They have been bonked {doc['bonks_received']} time{'s' if doc['bonks_received'] != 1 else ''}.\n"
    if doc['last_bonked_by']:
        string = string + f"\t They were last bonked by <@{doc['last_bonked_by']}> on {time.ctime(doc['last_bonked_by_time'])}.\n"
        string = string + f"\t This was because: \"{doc['last_bonked_by_reason']}\".\n"
    
    await ctx.send(string)

# music commands

@bot.command(name='join', help="add bot to your current channel", aliases = ("come", "j"))
async def join(ctx:commands.Context):
    if ctx.author.voice is None:
        await ctx.send("You are not connected to a voice channel.")
    else:
        channel = ctx.author.voice.channel
        if ctx.voice_client is not None:
            await ctx.voice_client.move_to(channel)
        else:
            await channel.connect()
        await ctx.send(f"Joining channel: <#{channel.id}>")

@bot.command(name='leave', help="disconnect bot from current channel", aliases = ("quit","go", "l"))
async def leave(ctx:commands.Context):
    if ctx.voice_client:
        channel_id = ctx.voice_client.channel.id
        await ctx.voice_client.disconnect()
        await ctx.send(f"Leaving channel: <#{channel_id}>")
        
@bot.command(name="play", help="play a new song or resume a paused song", aliases = ("resume", "p"))
async def play(ctx:commands.Context,
               *, song: list = commands.parameter(description=" - link or youtube search. Leave blank to resume current song.", default=None, displayed_default=None)):
    if not ctx.voice_client:
        await join(ctx)
        if not ctx.author.voice:
            return
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
    if song:
        player = music_handle.prepare_audio(''.join(song))
        ctx.voice_client.play(player, after = lambda e: _after(ctx, e))
        await ctx.send(f'Now playing: {player.title}')
    else:
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resume Confirmed")

def _after(ctx: commands.Context, e):
    if music_handle.songs_in_queue():
        next_player = music_handle.load_from_queue()
        ctx.voice_client.play(next_player, after = lambda e: _after(ctx, e))
        asyncio.run_coroutine_threadsafe(ctx.send(f"Up next: {next_player.title}"), bot.loop)
    else:
        asyncio.run_coroutine_threadsafe(ctx.send("No more songs in queue."), bot.loop)


@bot.command(name="pause", help="pause the current playing song", aliases = ("stop","s"))
async def pause(ctx:commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Pause Confirmed")

@bot.command(name="queue", help="add a song the the play queue", aliases = ("que","q"))
async def queue(ctx:commands.Context,
                *, song: list = commands.parameter(description=" - link or youtube search.", default=None, displayed_default=None)):
    if song:
        music_handle.add_to_queue(''.join(song))
        await ctx.send(f"Queueing: {''.join(song)}")
    

@bot.command(name="skip", help="play the next song in the play queue, if there is one", aliases = ("next","n"))
async def skip(ctx:commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send(f"Skipping {ctx.voice_client.source.title}")
        ctx.voice_client.stop()
        

@bot.command(name="start", help="start playing songs from the playlist", aliases = ("begin",))
async def start(ctx:commands.Context):
    if music_handle.songs_in_queue():
        await play(ctx, song=music_handle.play_queue.popleft())

bot.run(os.getenv("bot_key"))