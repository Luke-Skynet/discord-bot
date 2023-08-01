import json
from dotenv import load_dotenv
import os
import sys
import re
import asyncio
import time
import logging

import discord
from discord.ext import commands
from discord.utils import get

from db_handler import DBhandle
from music_handler import MusicHandle

# load main references

load_dotenv() # guild id and bot oauth key
config = json.load(open("config.json"))

bot = commands.Bot(
    command_prefix = commands.when_mentioned_or("!"), 
    case_insensitive = True,
    intents = discord.Intents.all(),
    help_command = commands.DefaultHelpCommand(no_category="Commands") 
)

guild:discord.Guild = None
discord.utils.setup_logging(level=logging.INFO, root=True)

db_handle = DBhandle(in_docker = config["docker"])
db_handle.set_db(config["database"])
try:
    db_handle.client.server_info()
    logging.info("connected to database")
except:
    logging.error("database connection not established")
    sys.exit(1)

music_handle = MusicHandle()
music_handle.load_settings(config["opus-dir"])

# events and helpers

def get_mentioned_member(mention:str, ctx:commands.Context) -> discord.Member:
    if mention is not None and re.match("<@\d+>", mention):
        return ctx.guild.get_member(int(mention.strip("<@>")))
    elif mention is None:
        asyncio.run_coroutine_threadsafe(ctx.send(f"No @person entered"), bot.loop)
    else:
        asyncio.run_coroutine_threadsafe(ctx.send(f"{mention} is not a member"), bot.loop)
    return None

@bot.event
async def on_ready():
    logging.info("connected to Discord")
    guild = bot.get_guild(int(os.getenv("guild")))
    if guild:
        logging.info(f"registered guild: {str(guild)}")
    else:
        logging.error("guild not found")
        sys.exit(1)

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
    logging.info("member database refreshed")

@bot.event
async def on_member_join(member):
    if not db_handle.db["members"].find({"member_id":member.id}):
        new_member = json.load(open("db_member_template.json"))
        new_member["member_id"] = member.id
        db_handle.db["members"].insert_one(new_member)

@bot.event
async def on_message(message:str):
    if message.author.id == bot.user.id:
        return
    if message.channel.id == config["commands-channel-id"]:
        await bot.process_commands(message)
        
# bonking

@bot.command(name = "bonk", help="bonk a person being indecorous", aliases = ("b",))
async def bonk(ctx:commands.Context,
               person: str = commands.parameter(description=" - the @person you want to bonk.", default=None, displayed_default=None),
               *, reason: str = commands.parameter(description=" - why they deserve to be bonked.", default="no reason")):

    bonk_time = round(time.time())
    bonk_reason = reason
    
    if person == bot.user.mention:
        await ctx.send(f"{ctx.message.author.mention} tried to bonk the bot!")
        return
    
    member = get_mentioned_member(person, ctx)
    if member is None:
        return

    db_handle.db["members"].update_one(
        {"member_id": ctx.message.author.id},
        {"$inc": {"bonks_given": 1},
         "$set": {"last_bonk_given": member.id,
                  "last_bonk_given_time": bonk_time,
                  "last_bonk_given_reason": bonk_reason}
        }
    )
    bonked_result = db_handle.db["members"].find_one_and_update(
        {"member_id": member.id},
        {"$inc": {"bonks_received": 1},
         "$set": {"last_bonked_by": ctx.message.author.id,
                  "last_bonked_by_time": bonk_time,
                  "last_bonked_by_reason": bonk_reason},
         "$push":{"bonk_reasons": bonk_reason}
        }
    )

    bonks = bonked_result["bonks_received"] + 1
    await ctx.send(f"{member.mention} has been bonked {str(bonks)} time{'s' if bonks != 1 else ''}!")

@bot.command(name = "bonkinfo", help="view a person's bonk statistics (last bonk and reason)")
async def bonkinfo(ctx:commands.Context,
                   person: str = commands.parameter(description=" - the @person you want to look up. Leave blank to look up yourself.", default=None, displayed_default=None)):
    
    member_id = ctx.author.id
    if person is not None: 
        if person == bot.user.mention:
            await ctx.send("I cannot be bonked")
            return
        else:
            member = get_mentioned_member(person, ctx)
            if member is None:
                return
            member_id = member.id

    doc = db_handle.db["members"].find_one({"member_id":member_id})

    string = f"Bonk statistics for <@{member_id}>: \n" + \
             f"\t They have been bonked {doc['bonks_received']} time{'s' if doc['bonks_received'] != 1 else ''}\n"
    if doc['last_bonked_by']:
        string = string + f"\t They were last bonked by <@{doc['last_bonked_by']}> on {time.ctime(doc['last_bonked_by_time'])}\n"
        string = string + f"\t This was because: \"{doc['last_bonked_by_reason']}\"\n"
    
    await ctx.send(string)

# music commands

@bot.command(name='join', help="add bot to your current channel", aliases = ("come", "j"))
async def join(ctx:commands.Context):
    if ctx.author.voice is None:
        await ctx.send("You are not connected to a voice channel")
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
               *, song: str = commands.parameter(description=" - link or youtube search. Leave blank to resume current song.", default=None, displayed_default=None)):
    if not ctx.voice_client:
        await join(ctx)
        if not ctx.author.voice:
            return
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
    if song is not None:
        player = music_handle.prepare_audio(song)
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

@bot.command(name="pause", help="pause the currently playing song", aliases = ("stop","s"))
async def pause(ctx:commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Pause Confirmed")

@bot.command(name="queue", help="add a song the the play queue", aliases = ("que","q"))
async def queue(ctx:commands.Context,
                *, song: str = commands.parameter(description=" - link or youtube search.", default=None, displayed_default=None)):
    if song is not None:
        music_handle.add_to_queue(song)
        await ctx.send(f"Queueing: {music_handle.play_queue[-1].title}")

@bot.command(name="skip", help="play the next song in the play queue, if there is one", aliases = ("next","n"))
async def skip(ctx:commands.Context):
    if ctx.voice_client and ctx.voice_client.is_playing():
        await ctx.send(f"Skipping {ctx.voice_client.source.title}")
        ctx.voice_client.stop()
        
@bot.command(name="start", help="start playing songs from the queue", aliases = ("startq", "begin","beginq"))
async def start(ctx:commands.Context):
    if music_handle.songs_in_queue():
        if not ctx.voice_client:
            await join(ctx)
            if not ctx.author.voice:
                return
        if ctx.voice_client.is_playing():
            ctx.voice_client.pause()
        player = music_handle.load_from_queue()
        ctx.voice_client.play(player, after = lambda e: _after(ctx, e))
        await ctx.send(f'Now playing: {player.title}')

@bot.command(name="viewq", help="show the current play queue list", aliases = ("viewqueue","qlist","queuelist","listq","listqueue"))
async def display_queue(ctx:commands.Context):
    embed=discord.Embed(title="Music Queue", color=discord.Colour.og_blurple())
    if not music_handle.songs_in_queue():
        embed.add_field(value =  "Empty", name = '')
    else:
        for i, song in enumerate([*music_handle.play_queue]):
            embed.add_field(value = f"{i + 1}: {song.title}", name = '', inline = False)
    await ctx.send(embed = embed)

# quote and comment

@bot.command(name="quote", help="record and frame the last thing a member said in a channel")
async def quote(ctx:commands.Context, 
                person: str = commands.parameter(description= " - the @person you want to quote.", default=None, displayed_default=None),
                channel: str = commands.parameter(description= " - the #channel to update their quote from. Leave blank to just recall.", default=None, displayed_default=None)):
    
    member = get_mentioned_member(person, ctx)
    if member is None:
        return
    
    quote_message = None

    if channel is not None:
        text_channel = ctx.guild.get_channel(int(channel.strip("<#>"))) if re.match("<#\d+>", channel) else None
        if text_channel is None:
            await ctx.send(f"{channel} is not a text channel")
            return
            
        history = [message async for message in text_channel.history(limit=50)]

        messages= []

        for msg in history:
            if msg.author.id == member.id:
                messages.append(msg.content)
            elif messages:
                break
        if not messages:
            return
        
        quote_message = '\n'.join(reversed(messages))
        db_handle.db["members"].update_one({"member_id": member.id},
                                           {"$set": {f"quotes.{ctx.author.id}": quote_message}})

    else:
        query = db_handle.db["members"].find_one({"member_id": member.id}, {f"quotes.{ctx.author.id}"})
        if query:
            quote_message = query.get("quotes").get(str(ctx.author.id))
        else:
            return


    embed = discord.Embed(title=member.display_name, color=member.accent_color)
    embed.add_field(name = '', value = f"\"{quote_message}\"")
    await ctx.send(embed = embed)
    
bot.run(os.getenv("bot_key"), log_handler=None)