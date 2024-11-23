import asyncio
import json
import logging
import yt_dlp

from collections import deque
from typing import Optional

import discord
from discord.ext import commands

from cogs.parent import ParentCog


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


class Music(ParentCog):
    
    def __init__(self, bot, db_handler):
        
        super().__init__(bot, db_handler)
        
        self.music_queue: deque[YTDLSource] = deque()
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


    @commands.hybrid_command(name='join', help="add bot to your current channel")
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


    @commands.hybrid_command(name='leave', help="disconnect bot from current channel")
    async def leave(self, ctx:commands.Context):
        if ctx.voice_client:
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                self.currently_playing.cleanup()
                self.currently_playing = None
            await ctx.send(f"Leaving channel: <#{ctx.voice_client.channel.id}>")
            await ctx.voice_client.disconnect()
        

    @commands.hybrid_command(name="play", help="play a new song or resume a paused song")
    async def play(self, ctx:commands.Context,
                   song: str = commands.parameter(description="- link or youtube search. Leave blank to resume current song.",
                                                  default=None, displayed_default=None)):
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
                await ctx.send(f"Resuming: {self.currently_playing.title}")
            

    @commands.hybrid_command(name="pause", help="pause the currently playing song")
    async def pause(self, ctx:commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(f"Pausing: {self.currently_playing.title}")
            

    @commands.hybrid_command(name="skip", help="play the next song in the music queue, if there is one")
    async def skip(self, ctx:commands.Context):
        if ctx.voice_client and ctx.voice_client.is_playing():
            title = self.currently_playing.title
            ctx.voice_client.stop()
            await ctx.send(f"Skipping: {title}")


    @commands.hybrid_command(name="queue", help="add a song to the music queue")
    async def queue(self, ctx:commands.Context,
                    song: str = commands.parameter(description="- link or youtube search.",
                                                   default=None, displayed_default=None)):
        if song is not None:
            message = await ctx.send("Working on it")
            player = YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options)
            self.music_queue.append(player)
            await message.edit(content = f"Queued: {player.title}")


    @commands.hybrid_command(name="clear", help="remove all songs from the music queue")
    async def clear(self, ctx:commands.Context):
        self.music_queue = deque()
        await ctx.send("Music queue cleared.")

            
    @commands.hybrid_command(name="start", help="start playing songs from the music queue")
    async def start(self, ctx:commands.Context):
        if self.music_queue:
            if not ctx.voice_client:
                await self.join(ctx)
                if not ctx.author.voice:
                    return
            if ctx.voice_client.is_playing():
                ctx.voice_client.pause()
                self.currently_playing.cleanup()
            player = self.music_queue.popleft()
            ctx.voice_client.play(player, after = lambda e: self._after(ctx, e))
            self.currently_playing = player
            await ctx.send(f'Now playing: {player.title}')


    def _after(self, ctx: commands.Context, e):
        self.currently_playing.cleanup()
        self.currently_playing = None
        if self.music_queue and ctx.voice_client is not None:
            next_player = self.music_queue.popleft()
            ctx.voice_client.play(next_player, after = lambda e: self._after(ctx, e))
            self.currently_playing = next_player
            asyncio.run_coroutine_threadsafe(ctx.send(f"Up next: {next_player.title}"), self.bot.loop)
        elif ctx.voice_client is not None:
            asyncio.run_coroutine_threadsafe(ctx.send("No more songs in queue."), self.bot.loop)