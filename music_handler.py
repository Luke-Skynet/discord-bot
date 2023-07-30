import discord
import yt_dlp

from collections import deque

class MusicHandle:
    def __init__(self):

        self.play_queue:deque = deque()

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
    
    def load_settings(self, opus_directory:str):
        discord.opus.load_opus(opus_directory)
        yt_dlp.utils.bug_reports_message = lambda: ''
    
    def prepare_audio(self, url:str):
        return YTDLSource.from_url(url, self.ytdl_format_options, self.ffmpeg_options)
    
    def songs_in_queue(self):
        return bool(self.play_queue)

    def load_from_queue(self):
        return self.prepare_audio(self.play_queue.popleft())

    def add_to_queue(self, song:str):
        self.play_queue.append(song)



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
