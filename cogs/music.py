import asyncio
import json
import logging
import yt_dlp
from collections import deque
from typing import Optional

import discord
from discord.ext import commands


from parent import ParentCog


class Music(ParentCog):
    
    def __init__(self, bot, db_handler):
        
        super().__init__(bot, db_handler)
        self.play_queue: deque[YTDLSource] = deque()
        self.currently_playing: Optional[YTDLSource] = None

        with open("config.json") as handle:
            discord.opus.load_opus(json.load(handle)["opus-dir"])
        yt_dlp.utils.bug_reports_message = lambda: ''
        
        self.ytdl_format_options = {
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
        
        self.ffmpeg_options = {
            'options': '-vn',
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        }

    @commands.command(name='join', help="add bot to your current channel", aliases = ("come", "j"))
    async def join(self, ctx:commands.Context):
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel")
        else:
            channel = ctx.author.voice.channel
            if ctx.voice_client is not None:
                await ctx.voice_client.move_to(channel)
            else:
                await channel.connect()
            await ctx.send(f"Joining channel: <#{channel.id}>")

    @commands.command(name='leave', help="disconnect bot from current channel", aliases = ("quit","go", "exit", "l"))
    async def leave(self, ctx:commands.Context):
        if ctx.voice_client:
            channel_id = ctx.voice_client.channel.id
            await ctx.voice_client.disconnect()
            await ctx.send(f"Leaving channel: <#{channel_id}>")
            
    @commands.command(name="play", help="play a new song or resume a paused song", aliases = ("resume", "p"))
    async def play(self, ctx:commands.Context,
                *, song: str = commands.parameter(description="- link or youtube search. Leave blank to resume current song.", default=None, displayed_default=None)):
        if not ctx.voice_client:
            await self.join(ctx)
            if not ctx.author.voice:
                return
        if song is not None:
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                self.currently_playing.cleanup()
            message = await ctx.send("Working on it")
            player = YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options)
            ctx.voice_client.play(player, after = lambda e: self._after(ctx, e))
            self.currently_playing = player
            await message.edit(content = f'Now playing: {player.title}')
        else:
            if ctx.voice_client and ctx.voice_client.is_paused():
                ctx.voice_client.resume()
                await ctx.send("Resume Confirmed")

    def _after(self, ctx: commands.Context, e):
        self.currently_playing.cleanup()
        if self.play_queue:
            next_player = self.play_queue.popleft()
            ctx.voice_client.play(next_player, after = lambda e: self._after(ctx, e))
            self.currently_playing = next_player
            asyncio.run_coroutine_threadsafe(ctx.send(f"Up next: {next_player.title}"), self.bot.loop)
        else:
            asyncio.run_coroutine_threadsafe(ctx.send("No more songs in queue."), self.bot.loop)
            self.currently_playing = None


    @commands.command(name="pause", help="pause the currently playing song", aliases = ("stop","s"))
    async def pause(self, ctx:commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send("Pause Confirmed")

    @commands.hybrid_group(name="queue", help="add a song to the music queue", aliases = ("que","q"))
    async def queue(self, ctx:commands.Context,
                    *, song: str = commands.parameter(description="- link or youtube search.", default=None, displayed_default=None)):
        if song is not None:
            message = await ctx.send("Working on it")
            self.play_queue.append(YTDLSource.from_url(song), self.ytdl_format_options, self.ffmpeg_options)
            await message.edit(content = f"Queued: {self.play_queue[-1].title}")

    @queue.command(name="view", help="- show the current music queue list", aliases = ("list",))
    async def display_queue(self, ctx:commands.Context):
        embed=discord.Embed(title="Music Queue", color=discord.Colour.og_blurple())
        if not self.play_queue:
            embed.add_field(value =  "Empty", name = '')
        else:
            for i, song in enumerate([*self.play_queue]):
                embed.add_field(value = f"{i + 1}: {song.title}", name = '', inline = False)
        await ctx.send(embed = embed)

    @queue.command(name="insert", help="- add song at to a specific spot in music queue", aliases =("add",))
    async def insert(self, ctx:commands.Context,
                    song: str = commands.parameter(description="- link or youtube search (use parentheses).", default=None, displayed_default=None),
                    place: str = commands.parameter(description="- where to add the song. Leave blank to queue normally.", default=None, displayed_default=None)):
        if song is not None and ( place.isdigit() or place is None ):
            message = await ctx.send("Working on it")
            queue_pos = max(1, min(place, len(self.play_queue)))
            if place is None or place > len(self.play_queue):
                self.play_queue.append(YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options))
                queue_pos = len(self.play_queue)
            else:
                self.play_queue.insert(queue_pos - 1, YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options))
            await message.edit(content = f"Queued '{self.play_queue[queue_pos].title}' into place: {queue_pos}")

    @queue.command(name="delete", help="- remove song at to a specific spot in music queue", aliases =("remove",))
    async def delete(self, ctx:commands.Context,
                    place: str = commands.parameter(description="- place of the song to remove.", default=None, displayed_default=None)):
        if place is not None and ( place.isdigit() or place is None ):
            if 1 <= place <= len(self.play_queue):
                title_result = self.play_queue[place - 1].title
                del self.play_queue[place - 1]
                await ctx.send(f"Deleted from music queue: {title_result}")

    @queue.command(name="clear", help="- remove all songs from the music queue")
    async def clear(self, ctx:commands.Context):
        if len(ctx.message.content.split()) == 2:
            if self.play_queue:
                self.play_queue = deque()
            await ctx.send("Cleared music queue")
        else:
            await self.queue(ctx, song = ' '.join(ctx.message.content.split()[1:]))

    @commands.command(name="skip", help="play the next song in the music queue, if there is one", aliases = ("next","n"))
    async def skip(self, ctx:commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            await ctx.send(f"Skipping {ctx.voice_client.source.title}")
            ctx.voice_client.stop()
            
    @commands.command(name="start", help="start playing songs from the music queue", aliases = ("startq", "begin", "beginq"))
    async def start(self, ctx:commands.Context):
        if self.play_queue:
            if not ctx.voice_client:
                await self.join(ctx)
                if not ctx.author.voice:
                    return
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                self.currently_playing.cleanup()
            player = self.play_queue.popleft()
            ctx.voice_client.play(player, after = lambda e: self._after(ctx, e))
            self.currently_playing = player
            await ctx.send(f'Now playing: {player.title}')

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=1):

        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    def from_url(cls, url, ytdl_format_options, ffmpeg_options):
        data =  yt_dlp.YoutubeDL(ytdl_format_options).extract_info(url, download=False)

        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url']

        ffmpeg_options_instance = dict(ffmpeg_options)
        if data.get('is_live'):
            ffmpeg_options_instance["before_options"] = "-http_persistent 0 -reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5"

        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options_instance), data=data)
