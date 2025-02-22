import discord
import asyncio
from typing import Callable, Awaitable, Coroutine, Any
import yt_dlp

type QueuedSong = QueuedSong
type MusicBotClient = MusicBotClient

# HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
#        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
#        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
#        'Accept-Encoding': 'none',
#        'Accept-Language': 'en-US,en;q=0.8',
#        'Connection': 'keep-alive'}

YTDL_FORMAT_OPTIONS = {
    'format': 'bestaudio',
    'outtmpl': '%(extractor)s-%(id)s-%(title)s.%(ext)s',
    'skip_download': True,
    'restrictfilenames': True,
    'default_search': 'auto',
    'noplaylist': True,
    'nocheckcertificate': True,
    'ignoreerrors': True,
    'logtostderr': False, 
    'quiet': True, # update
    'no_warnings': True,
    'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '140',
    }],
    "simulate": True,
    "forceurl": True,
}

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5','options': '-vn -filter:a "volume=0.25"'}

YTDL = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

class QueuedSong:
    """
    Represents a song in the queue. Contains the URL, name, duration, and thumbnail of the queued video. 
    
    Additionally, has functions for searching for videos using youtube's search bar.
    """
    def __init__(self, url: str | None, name: str, dur: str, thumbnail: str, player: str):
        self.name: str = name
        self.url: str | None = url
        self.duration: str = dur
        self.thumbnail: str = thumbnail
        self.player: str | None = player
    
    async def create(query: str) -> QueuedSong | Exception | None:
        """Creates a QueuedSong, searching for video data if necessary. 

        Args:
            query (str): A video name or url

        Returns:
            None | QueuedSong: Instance of a QueuedSong containing video information
            If the video failed to be found, then returns None. 
        """
        data: dict[str, Any] | None = await QueuedSong.get_video(query)
        if data == None or type(data) == Exception: return data
        
        name: str = data.get('title', query)
        url: str = data.get('webpage_url', query)
        duration: str = data.get('duration_string', "??:??")
        thumbnail: str = data.get('thumbnail', "https://redthread.uoregon.edu/files/original/affd16fd5264cab9197da4cd1a996f820e601ee4.png")
        player: str | None = data.get('url')
        
        return QueuedSong(url, name, duration, thumbnail, player)
    
    def get_video_info(query: str) -> dict[str, Any] | Exception | None:
        try:
            return YTDL.extract_info(query, download=False)
        except Exception as e:
            return e
    
    async def get_video(query: str) -> dict[str, Any] | Exception | None:
        """Searches for a video given a URL or query

        Args:
            url (str): URL or query to search for

        Returns:
            dict | list[dict]: Dictionary containing some of the video's information. 
            If the query was a playlist, then this will contain a list of dictionaries with each video's information. 
        """
        # Get the video info
        data: dict[str, Any] | Exception | None = await asyncio.get_event_loop().run_in_executor(None, lambda: QueuedSong.get_video_info(query))
        
        # Playlist urls or youtube searches may return multiple results, in which case we just want the top result
        if data and type(data) == dict and 'entries' in data:
            if len(data['entries'])==0: return None
            data = data['entries'][0]
            
        return data

class MusicBotClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        self.queue: list[QueuedSong] = []
        self.next_in_queue: int = 0
        self.loop_queue: bool = False
        self._active: bool = False
        self._timeout_task: asyncio.Task | None = None
        self._bg_tasks: set[asyncio.Task] = set()
        
        # Acts as a callback for errors
        async def default_err(c: MusicBotClient, e: Exception):
            print(e)
        self._on_err: Callable[[MusicBotClient, Exception], Awaitable[None]] = default_err
        
        super().__init__(client, channel)
        self.msg_channel: discord.abc.Messageable = self.channel
    
    async def enqueue(self, query: str | QueuedSong) -> QueuedSong | None:
        """Adds a song to the queue

        Args:
            query (str | QueuedSong): A query or QueuedSong

        Returns:
            QueuedSong | None: Song that was enqueued, or None if the query failed to be found.
        """
        song: QueuedSong | Exception | None = await QueuedSong.create(query) if type(query)==str else query
        
        # If song could not be found, run the error function
        if song == None or type(song) == Exception: self._run_task(self._on_err(self, song if song else Exception(f"Could not queue song {query}")))
        # Otherwise, add the song
        else: self.queue.append(song)
        
        # Limit queue size to 32
        if len(self.queue) > 32: 
            self.queue.pop(0)
            self.next_in_queue-=1
            
        if hasattr(self, '_on_queue') and type(song)==QueuedSong: self._run_task(self._on_queue(song, self))
            
        return None if type(song)==Exception else song
          
    def peek_queue(self) -> QueuedSong | None:
        return self.queue[self.next_in_queue] if self.next_in_queue < len(self.queue) else None
              
    def incr_queue(self) -> QueuedSong | None:
        """Increments the queue and returns the new current QueuedSong

        Returns:
            QueuedSong | None: _description_
        """
        song: QueuedSong | None = self.peek_queue()
        self.next_in_queue += 1
        if self.loop_queue and self.next_in_queue >= len(self.queue):
            self.next_in_queue = 0
        return song
    
    def play_next(self, error: Exception | None = None):
        """Plays the next song in the queue, stopping the currently playing song if necessary. 

        Args:
            error (Exception | None, optional): Argument passed by VoiceClient.play. Defaults to None.
        """
        if error: self._run_task(self._on_err(self, error))
        
        # if we're playing a song already, then stop playing it and return
        # the 'after' closure we passed into self.play() should queue the next song for us
        if self.is_playing() or super().is_paused():
            super().stop()
            return
        
        # get the next song in the queue
        next_song: QueuedSong | None = self.incr_queue()
        # if we're at the end of the queue, return because there is nothing to play.
        if next_song==None:
            self._set_inactive()
            return
        
        super().play(discord.FFmpegOpusAudio(next_song.player, **FFMPEG_OPTIONS), after = self.play_next)
        self._set_active()
        if hasattr(self, '_on_play'): self._run_task(self._on_play(next_song, self))
    
    def _set_active(self):
        self._active = True
        if self._timeout_task: self._timeout_task.cancel()
    
    def _set_inactive(self):
        self._active = False
        self._timeout_task = self.loop.create_task(self.timeout())
    
    async def timeout(self):
        await asyncio.sleep(300)
        await self.disconnect()
        
    async def disconnect(self, force: bool = False):
        """Disconnects the bot from its voice channel

        Args:
            force (bool, optional): Force the disconnect even if the bot is not connected. Defaults to False.
        """
        if self._active:
            self.source.cleanup()
            
        if hasattr(self, '_on_disconnect'): self._run_task(self._on_disconnect(self))
        await super().disconnect(force = force)
        
    def get_queue(self) -> tuple[int, list[QueuedSong]]:
        """Get the queue and the current song index

        Returns:
            tuple[int, list[QueuedSong]]: (current song index, full song queue)
        """
        return self.next_in_queue-1, self.queue
        
    def is_active(self) -> bool:
        """Indicates if the bot is playing music or if there are songs still left in the queue

        Returns:
            bool: Whether the bot is current playing a song or has songs left in the queue to play
        """
        return self._active
    
    def set_msg_channel(self, channel: discord.abc.Messageable):
        """Set the channel which this bot will send play and queue updates to

        Args:
            channel (discord.MusicBotClient): The channel the bot should send messages to
        """
        self.msg_channel: discord.abc.Messageable = channel
    
    def set_on_play(self, func: Callable[[QueuedSong, MusicBotClient], Awaitable[None]]):
        """Set a function which gets called when the bot begins playing a new song

        Args:
            func (Callable[[QueuedSong, MusicBotClient], None]): Function that gets called
        """
        self._on_play: Callable[[QueuedSong, MusicBotClient], Awaitable[None]] = func
        
    def set_on_queue(self, func: Callable[[QueuedSong, MusicBotClient], Awaitable[None]]):
        """Set a function which gets called when the bot begins playing a new song

        Args:
            func (Callable[[QueuedSong, MusicBotClient], None]): Function that gets called
        """
        self._on_queue: Callable[[QueuedSong, MusicBotClient], Awaitable[None]] = func
        
    def set_on_err(self, func: Callable[[MusicBotClient, Exception], Awaitable[None]]):
        """Set a function which gets called when an exception occurs in this voice client

        Args:
            func (Callable[[MusicBotClient, Exception], None]): Function that gets called
        """
        self._on_err: Callable[[MusicBotClient, Exception], Awaitable[None]] = func
    
    def set_on_disconnect(self, func: Callable[[MusicBotClient], Awaitable[None]]) -> None:
        """Set a function which gets called right before the bot disconnects from voice
        
        Note that it is possible that the bot fails to disconnect, but the disconnect function will get called anyways. 

        Args:
            func (Callable[[MusicBotClient], None]): Function that gets called when this MusicBotClient instance disconnects
        """
        self._on_disconnect: Callable[[MusicBotClient], Awaitable[None]] = func
        
    def _run_task(self, coro: Coroutine[Any, Any, Any], *, name: str | None = None, context: Any | None = None):
        task: asyncio.Task = self.loop.create_task(coro, name=name, context=context)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        
        