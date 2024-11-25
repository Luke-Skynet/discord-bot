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
        
        self.data: dict = data
        self.title: str = data.get('title')

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
        
        self.ytdl_format_options: dict = {
            'format': 'bestaudio/best',
            'noplaylist': True,
            'default_search': 'auto'
        }
        
        self.ffmpeg_options: dict = {
            'options': '-vn',
            "before_options": "-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5",
        }
                

    @commands.hybrid_command(name='join', help="add bot to your current channel")
    async def join(self, ctx:commands.Context):
        
        if ctx.author.voice is not None and ctx.voice_client and \
           ctx.author.voice.channel.id == ctx.voice_client.channel.id:
               
            await ctx.send(f"I am already in <#{ctx.voice_client.channel.id}>")
            
        else:
            await self._join_if_not_connected(ctx)

    
    @commands.hybrid_command(name='leave', help="disconnect bot from your current channel")
    async def leave(self, ctx:commands.Context):
        
        if not self._bot_in_user_channel(ctx):
            await ctx.send("You are not in the voice channel")
            
        elif ctx.voice_client:
            
            if self.currently_playing is not None:
                self._stop(ctx)
                
            await ctx.send(f"Leaving <#{ctx.voice_client.channel.id}>")
            await ctx.voice_client.disconnect()
            
        else:
            await ctx.send("I am not in a voice channel")
        

    @commands.hybrid_command(name="play", help="play a new song or resume a paused song")
    async def play(self, ctx:commands.Context,
                   song: str = commands.parameter(description="- link or youtube search. Leave blank to resume current song.",
                                                  default=None, displayed_default=None)):
        
        await self._join_if_not_connected(ctx)
        if not self._bot_in_user_channel(ctx):
            return
        
        if song is not None:
            
            if self.currently_playing is not None:
                self._stop(ctx)
                
            message = await ctx.send("Working on it")
            
            player = YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options)
            self._play(ctx, player)
            
            await message.edit(content = f'Now playing: {player.title}')
            
        elif ctx.voice_client.is_paused():
            
            ctx.voice_client.resume()
            await ctx.send(f"Resuming: {self.currently_playing.title}")
            
        elif self.music_queue:
            
            player = self.music_queue.popleft()
            self._play(ctx, player)
            
            await ctx.send(f'Now playing: {player.title}')
            
        else:
            await ctx.send("There is nothing to play")
            
            
    @commands.hybrid_command(name="pause", help="pause the currently playing song")
    async def pause(self, ctx:commands.Context):
        
        if not self._bot_in_user_channel(ctx):
            await ctx.send("You are not in the voice channel")
        
        elif ctx.voice_client.is_playing():
            ctx.voice_client.pause()
            await ctx.send(f"Pausing: {self.currently_playing.title}")
            
        else:
            await ctx.send("No song is currently playing")
            

    @commands.hybrid_command(name="skip", help="play the next song in the music queue, if there is one")
    async def skip(self, ctx:commands.Context):
        
        if not self._bot_in_user_channel(ctx):
            await ctx.send("You are not in the voice channel")
            
        elif ctx.voice_client and self.currently_playing is not None:
            await ctx.send(f"Skipping: {self.currently_playing.title}")
            ctx.voice_client.stop()
            
        else:
            await ctx.send("No song is currently playing")


    @commands.hybrid_command(name="queue", help="add a song to the music queue")
    async def queue(self, ctx:commands.Context,
                    song: str = commands.parameter(description="- link or youtube search",
                                                   default=None, displayed_default=None)):
        if not self._bot_in_user_channel(ctx):
            await ctx.send("You are not in the voice channel")
            
        elif song is not None:
            
            message = await ctx.send("Working on it")
            
            player = YTDLSource.from_url(song, self.ytdl_format_options, self.ffmpeg_options)
            self.music_queue.append(player)
            
            await message.edit(content = f"Queued: {player.title}")
            
        else:
            await ctx.send("No song was specified")


    @commands.hybrid_command(name="clear", help="remove all songs from the music queue")
    async def clear(self, ctx:commands.Context):
        
        if not self._bot_in_user_channel(ctx):
            await ctx.send("You are not in the voice channel")
            return
        
        self.music_queue = deque()
        
        await ctx.send("Music queue cleared")


    async def _join_if_not_connected(self, ctx:commands.Context):
        
        if ctx.author.voice is None:
            await ctx.send("You are not connected to a voice channel")
        else:
            
            user_channel = ctx.author.voice.channel
            bot_channel  = ctx.voice_client.channel if ctx.voice_client else None
                
            if bot_channel and (bot_channel.id != user_channel.id) and ctx.voice_client.is_playing():
                await ctx.send(f"I am already playing music in <#{bot_channel.id}>")
                
            elif bot_channel and (bot_channel.id != user_channel.id):
                await ctx.voice_client.move_to(user_channel)
                await ctx.send(f"Joining <#{user_channel.id}>")
                
            elif bot_channel is None:
                await user_channel.connect()
                await ctx.send(f"Joining <#{user_channel.id}>")
            
    
    def _bot_in_user_channel(self, ctx:commands.Context) -> bool:
        return ctx.author.voice is not None and ctx.voice_client is not None and \
               ctx.author.voice.channel.id  ==  ctx.voice_client.channel.id


    def _play(self, ctx, player: YTDLSource):
        ctx.voice_client.play(player, after = lambda e: self._after(ctx, e))
        self.currently_playing = player


    def _stop(self, ctx):  
        ctx.voice_client.pause()
        self.currently_playing.cleanup()
        self.currently_playing = None


    def _after(self, ctx: commands.Context, e):
    
        if self.currently_playing is not None:
            self._stop(ctx)
            
        if ctx.voice_client.is_connected() and len(self.music_queue) > 0:
            
            next_player = self.music_queue.popleft()
            self._play(ctx, next_player)
            
            asyncio.run_coroutine_threadsafe(ctx.send(f"Up next: {next_player.title}"), self.bot.loop)
            
        elif ctx.voice_client is not None and ctx.voice_client.is_connected():
            asyncio.run_coroutine_threadsafe(ctx.send("No more songs in queue."), self.bot.loop)