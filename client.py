import json
import re
import asyncio
import yt_dlp

from collections import deque

import discord
from discord.ext import commands
from discord.utils import get

from db_handler import DBhandle

# load main references

info = json.load(open("jsons/info.json"))
config = json.load(open("jsons/config.json"))

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), case_insensitive=True, intents=discord.Intents.all())

guild:discord.Guild = None
commmand_channel:int = config["commands-channel-id"]


# stream configs

play_queue = deque()

discord.opus.load_opus(config["opus-dir"])

yt_dlp.utils.bug_reports_message = lambda: ''

ytdl_format_options = {
    'format': 'bestaudio/best',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'restrictfilenames': True,
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': False,
    'logtostderr': False,
    'quiet': True,
    'no_warnings': True,
    'default_search': 'auto',
    'source_address': '0.0.0.0',  # bind to ipv4 since ipv6 addresses cause issues sometimes
}

ffmpeg_options = {
    'options': '-vn',
    "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):

        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def from_url(cls, url):
        data = ytdl.extract_info(url, download=False)
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url']
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

#initialize database

handle = DBhandle()
handle.set_db("bot")

#commands

@bot.event
async def on_ready():
    print(f'Update: {bot.user} has connected to Discord!')
    guild = bot.get_guild(int(info["guild"]))
    if not guild:
        print("Error: guild not found")
        exit()
    else:
        print(f"Update: {bot.user} registered guild: {str(guild)}")

    query = list(handle.db["members"].find({}, {"member_id"}))
    print(query)
    db_members_ids = set(dct["member_id"] for dct in query)

    current_members_ids = [mem.id for mem in guild.members]

    new_member_template = json.load(open("db_member_template.json"))
    new_members = []
    for mem_id in current_members_ids:
        if mem_id not in db_members_ids:
            new_member = dict(new_member_template)
            new_member["member_id"] = mem_id
            new_members.append(new_member)
    handle.db["members"].insert_many(new_members)
    print("Update: member database refreshed")

@bot.event
async def on_member_join(member):
    if not handle.db["members"].find({"member_id":member.id}):
        new_member = json.load(open("db_member_template.json"))
        new_member["member_id"] = mem_id
        handle.db["members"].insert_one(new_member)

@bot.event
async def on_message(message:str):
    if message.author == bot.user:
        return
    author = "<@" + str(message.author.id) + ">"
    swears = count_swears(message.content)
    if swears:
        await message.channel.send(author + " has said the following swear words: " + str(swears))

    if message.channel.id == commmand_channel:
        await bot.process_commands(message)

def count_swears(string:str):
    swear_words = ("fuck", "shit", "uwu")
    counts = (string.lower().count(s) for s in swear_words)
    ret = {}
    for swear, count in list(zip(swear_words, counts)):
        if count > 0:
            ret[swear] = count
    return ret

@bot.command(name = "bonk", help='bonk a person being indecorous', aliases = ("b",))
async def bonk(ctx:commands.Context, *arg:str):
    for user in arg:
        if not re.match("<@\d+>", str(user)) or ctx.guild.get_member(int(user.strip("<@>"))):
            print(str(user) + " is not a member.")

        if user == "<@" + str(bot.user.id) + ">":
            author = "<@" + str(ctx.message.author.id) + ">"
            await ctx.send(f"{author} tried to bonk the bot!")
            continue

        user_id = int(user.strip("<@>"))

        handle.db["members"].update_one(
            {"member_id":ctx.message.author.id},
            {"$inc": {"bonks_given": 1},
             "$set":{"last_bonk_given":user_id}})
        bonked_result = handle.db["members"].find_one_and_update(
            {"member_id":user_id},
            {"$inc": {"bonks_received": 1},
             "$set":{"last_bonk_received":ctx.message.author.id}})

        bonks = bonked_result["bonks_received"] + 1
        await ctx.send(f"{user} has been bonked {str(bonks)} time{'s' if bonks > 1 else ''}!")

'''Voice Commands'''

@bot.command(name='join', help="add bot to user's current channel", aliases = ("come", "j"))
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
        await ctx.voice_client.disconnect()
        await ctx.send(f"Leaving channel: <#{ctx.voice_client.channel.id}>")
        

@bot.command(name="play", help="play a new song or resume a paused song", aliases = ("resume", "p"))
async def play(ctx:commands.Context, *args):
    if not ctx.voice_client:
        await join(ctx)
        if not ctx.author.voice:
            return
    if ctx.voice_client.is_playing():
        ctx.voice_client.pause()
    if len(args) > 0:
        player = YTDLSource.from_url(' '.join(args))
        ctx.voice_client.play(player, after = lambda e: _after(ctx, e))
        await ctx.send(f'Now playing: {player.title}')
    else:
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resume Confirmed")

def _after(ctx: commands.Context, e):
    if play_queue:
        next_player = YTDLSource.from_url(play_queue.popleft())
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
async def queue(ctx:commands.Context, *args):
    play_queue.append(' '.join(args))
    await ctx.send(f"Queueing: {' '.join(args)}")

@bot.command(name="skip", help="play the next song in the play queue, if there is one", aliases = ("next","n"))
async def skip(ctx:commands.Context, *args):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send(f"Skipping {ctx.voice_client.source.title}")

@bot.command(name="start", help="start playing songs from the playlist", aliases = ("begin",))
async def start(ctx:commands.Context, *args):
    if play_queue:
        await play(ctx, play_queue.popleft())

bot.run(info["key"])
