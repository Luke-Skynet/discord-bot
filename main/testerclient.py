import json
import asyncio
import yt_dlp

from dbhandler import DBhandle

import discord
from discord.ext import commands


info = json.load(open("/root/discord-bot/jsons/info.json"))
config = json.load(open("/root/discord-bot/jsons/config.json"))

bot = commands.Bot(command_prefix=commands.when_mentioned_or("!"), case_insensitive=True, intents=discord.Intents.all())

guild:discord.Guild = None
commmand_channel:int = config["commands-channel-id"]


'''stream stuff'''

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
    async def from_url(cls, url, *, loop=None, stream=False):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))

        if 'entries' in data:
            # take first item from a playlist
            data = data['entries'][0]

        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

'''Commands'''

@bot.event
async def on_ready():
    print(f'Update: {bot.user} has connected to Discord!')
    guild = bot.get_guild(int(info["guild"]))
    if not guild:
        print("Error: guild not found")
        exit()
    else:
        print(f"Update: {bot.user} registered guild: {str(guild)}")

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

'''Voice Commands'''

@bot.command(name='join', help="add bot to user's current channel", aliases = ("start", "j"))
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

@bot.command(name='leave', help="disconnect bot from current channel", aliases = ("quit", "l"))
async def leave(ctx:commands.Context):
    if ctx.voice_client:
        await ctx.send(f"Leaving channel: <#{ctx.voice_client.channel.id}>")
        await ctx.voice_client.disconnect()

@bot.command(name="play", help="play a new song or resume a paused song", aliases = ("resume", "p"))
async def play(ctx:commands.Context, *args):
    if len(args) > 0:
        async with ctx.typing():
            player = await YTDLSource.from_url(args[0], loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Player error: {e}') if e else None)
        await ctx.send(f'Now playing: {player.title}')
    else:
        if ctx.voice_client and ctx.voice_client.is_paused():
            ctx.voice_client.resume()
            await ctx.send("Resume Confirmed")

@bot.command(name="pause", help="pause the current playing song", aliases = ("stop","s"))
async def pause(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.pause()
        await ctx.send("Pause Confirmed")

bot.run(info["key"])
