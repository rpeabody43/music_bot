import discord
import asyncio
from urllib import request
import json
from typing import Callable, Awaitable, Coroutine, SupportsIndex, Any
import yt_dlp

type QueuedSong = QueuedSong
type QueuedPlaylist = tuple[str, list[QueuedSong]]
type MusicBotClient = MusicBotClient

HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

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

FFMPEG_OPTIONS = {'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5 -http_persistent 0','options': '-vn -filter:a "volume=0.25"'}

YTDL = yt_dlp.YoutubeDL(YTDL_FORMAT_OPTIONS)

class QueuedSong:
    """
    Represents a song in the queue. Contains the URL, name, duration, and thumbnail of the queued video. 
    
    Additionally, has functions for searching for videos using youtube's search bar.
    """
    def __init__(self, url: str | None, name: str, dur: str, thumbnail: str, player: str | None = None):
        self.name: str = name
        self.url: str | None = url
        self.duration: str = dur
        self.thumbnail: str = thumbnail
        self.player: str | None = player
        self.generating_player: bool = False
    
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
    
    def has_player(self) -> bool:
        return self.player != None
    
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
    
    async def add_player(self) -> bool:
        self.generating_player = True
        data: dict[str, Any] | Exception | None = await QueuedSong.get_video(self.url)
        self.player = data.get('url')
        return True if self.player else False
    
    async def get_playlist(playlist_url: str) -> QueuedPlaylist | Exception | None:
        """Get a list of QueuedSong from a playlist
        
        Note that the queued songs will not come with video players

        Args:
            playlist_url (str): _description_

        Returns:
            QueuedPlaylist | Exception | None: _description_
        """
        if not "www.youtube.com/playlist?list=" in playlist_url: return None
        try:
            results: QueuedPlaylist = await asyncio.get_event_loop().run_in_executor(None, lambda: QueuedSong._playlist_query_result(playlist_url))
            return results
        except Exception as e:
            return e
    
    def _find_closing_brace(string: str, open_brace: str, close_brace: str) -> int:
        """Given open and closing brace characters to search for, finds the index of the respective closing brace

        Args:
            string (str): string to search in
            open_brace (str): open brace character to match
            close_brace (str): close brace character to match

        Returns:
            int: index of the closing brace matching to the first found open brace. 
        """
        start: int = string.index(open_brace)+1
        counter: int = 1
        for i,c in enumerate(string[start:]):
            if c==open_brace:
                counter+=1
            elif c==close_brace:
                counter-=1
            if counter==0:
                return start+i
        return len(string)
    
    def _playlist_query_result(url: str) -> QueuedPlaylist:
        """Searches for videos using a given youtube playlist URL

        Args:
            url (str): URL to search videos for

        Returns:
            dict[str, dict[str, dict]]: Dictionary containing some of the video's information. 
        """
        req: request.Request = request.Request(url, headers=HEADER)
        page: str = request.urlopen(req).read().decode("utf-8")
        
        playlist_info_start: int = page.index("\"pageHeaderRenderer\"")
        playlist_info_end: int = QueuedSong._find_closing_brace(page[playlist_info_start:], "{", "}")
        playlist_info: dict[str, str | dict] = json.loads(page[playlist_info_start+21:playlist_info_start+playlist_info_end+1])
        playlist_title: str = playlist_info.get('pageTitle', "Playlist")
        
        start: int = page.index("\"contents\":[{\"playlistVideoRenderer\":{\"")
        end: int = start + QueuedSong._find_closing_brace(page[start:], "[", "]")
        
        video_info: list[dict[str, Any]] = [video['playlistVideoRenderer'] for video in json.loads(page[start+11:end+1])]
        return playlist_title, [QueuedSong(f"https://www.youtube.com/watch?v={info['videoId']}", 
                    info['title']['runs'][0]['text'], 
                    info['lengthText']['simpleText'], 
                    info['thumbnail']['thumbnails'][0]['url']) 
                for info in video_info]
            
    

class MusicBotClient(discord.VoiceClient):
    def __init__(self, client: discord.Client, channel: discord.abc.Connectable):
        # song queue
        self.queue: list[QueuedSong] = []
        self.next_in_queue: int = 0
        
        self.loop_queue: bool = False
        self._active: bool = False
        self._timeout_task: asyncio.Task | None = None
        self._bg_tasks: set[asyncio.Task | asyncio.Future] = set()
        
        # Event that checks whether a song is currently being queried or not
        self._wait_query_event: asyncio.Event = asyncio.Event()
        self._wait_query_event.set()
        
        # Used to force only one song to be queried at a time
        self._query_task: asyncio.Task[QueuedSong | Exception | None] | None = None
        
        # Provides provide priority to a certain query
        self._priority_query_event: asyncio.Event = asyncio.Event()
        self._priority_query_event.set()
        
        self._disconnecting: bool = False
        
        # Acts as a callback for errors
        async def default_err(c: MusicBotClient, e: Exception):
            print(e)
        self._on_err: Callable[[MusicBotClient, Exception], Awaitable[None]] = default_err
        
        super().__init__(client, channel)
        self.msg_channel: discord.abc.Messageable = self.channel
        self._set_inactive()
    
    async def enqueue(self, query: str | QueuedSong, blocking: bool = True) -> QueuedSong | Exception | None:
        """Adds a song(s) to the queue

        Args:
            query (str | QueuedSong): A query or QueuedSong
            blocking (bool): Whether the enqueue function should block until the song is actually queued. 
            If blocking is set to false, then this function will always return None

        Returns:
            QueuedSong | Exception | None: Song that was enqueued, Exception if the query failed, or None if the queued song is no longer available
            (would likely be caused by the client being closed before enqueue could complete)
        """
        if not blocking:
            self._run_task(self.enqueue(query, True))
            return None
            
        # Create an event that will be set once this enqueue request completes
        my_event: asyncio.Event = await self._wait_query()
        
        # If after waiting for previous queries we got disconnected, cancel the enqueue and bubble the wait events
        if self._disconnecting:
            my_event.set()
            return None
        
        # Search using the query and queue the song
        song: QueuedSong | QueuedPlaylist | Exception | None
        if type(query)==str:
            self._query_task = self.loop.create_task(QueuedSong.create(query) if not "www.youtube.com/playlist?list=" in query else QueuedSong.get_playlist(query))
            try:
                song = await self._query_task
            except asyncio.CancelledError:
                my_event.set()
                return Exception("Query was cancelled")
        else:
            song = query
        
        # If while querying our song we got disconnected, bubble up the wait list and cancel all enqueues
        if self._disconnecting: 
            my_event.set()
            return None
        
        # Add the song if it was found
        if song and type(song)==tuple:
            if len(song[1]) > 0:
                self.queue.extend(song[1])
                song = QueuedSong(query, song[0], '??:??', song[1][0].thumbnail)
            else:
                song = Exception("Invalid Playlist")
        elif song and type(song)==QueuedSong: self.queue.append(song)
        
        # Limit queue size to 32
        if len(self.queue) > 32: 
            self.queue.pop(0)
            self.next_in_queue-=1
            
        my_event.set()
        
        if hasattr(self, '_on_queue') and type(song)==QueuedSong: self._run_task(self._on_queue(song, self))
            
        return song        
    
    async def _wait_query(self, prioritize: bool = False) -> asyncio.Event:
        """Block until the previously queried song gets queued, 
        and sets up the query event bubble so that the next queried song waits

        Returns:
            asyncio.Event: handle for setting when our current query completes
        """
        if prioritize and not self._priority_query_event.is_set():                 
            self._priority_query_event.clear()
            await self._query_task
            return self._priority_query_event

        # Create an event that will be set once our current query completes
        my_event: asyncio.Event = asyncio.Event()

        # Wait for previous query to run
        last_event: asyncio.Event = self._wait_query_event
        self._wait_query_event = my_event
        await last_event.wait()
        await self._priority_query_event.wait()
        return my_event
    
    def cancel_enqueue(self):
        """Stop the last queried song from being queued if it hasn't been queued yet
        """
        if self._query_task: self._query_task.cancel()
    
    def peek_queue(self) -> QueuedSong | None:
        return self.queue[self.next_in_queue] if self.next_in_queue < len(self.queue) else None
              
    def incr_queue(self) -> QueuedSong | None:
        """Increments the queue and returns the new current QueuedSong

        Returns:
            QueuedSong | None: _description_
        """
        song: QueuedSong | None = self.peek_queue()
        if song: self.next_in_queue += 1
        if self.loop_queue and self.next_in_queue >= len(self.queue):
            self.next_in_queue = 0
        return song
    
    def pop_queue(self, index: SupportsIndex = -1) -> QueuedSong | Exception:
        """Remove a song from the queue, decrementing 'next_in_queue' as needed. 

        Args:
            index (SupportsIndex, optional): Index of song in queue to remove. Defaults to -1.

        Returns:
            QueuedSong | Exception: The song that got removed; if pop() fails then returns an exception
        """
        if index < 0 or index >= len(self.queue): return Exception("Index out of bounds")
        elif not isinstance(index, SupportsIndex): return Exception("Index for removing song must be a number")
        
        res: QueuedSong = self.queue.pop(index)
        # Change next_in_queue only if self.queue.pop does not raise an error
        if self.next_in_queue > index and self.next_in_queue > 0: self.next_in_queue -= 1
        return res
    
    def clear_queue(self):
        """Clears the current queue of songs
        """
        self.queue.clear()
        self.next_in_queue = 0
    
    def curr_song(self) -> tuple[QueuedSong | None, int]:
        """Returns the current QueuedSong and the song's index in the queue

        Returns:
            tuple[QueuedSong | None, int]: Currently playing QueuedSong and its index in the queue
        """
        return (self.queue[self.next_in_queue-1], self.next_in_queue - 1) if self._active else (None, -1)
    
    def play_next(self, error: Exception | None = None):
        """Plays the next song in the queue, stopping the currently playing song if necessary. 

        Args:
            error (Exception | None, optional): Argument passed by VoiceClient.play. Defaults to None.
        """
        if self._disconnecting: return
        if error: self._run_task_threadsafe(self._on_err(self, error))
        
        # if we're playing a song already, then stop playing it and return
        # the 'after' closure we passed into self.play() should queue the next song for us
        if self.is_playing() or super().is_paused():
            super().stop()
            return
        
        # get the next song in the queue
        next_song: QueuedSong | None = self.incr_queue()
        
        # then play it
        self._play_song(next_song)
        
    def _play_song(self, song: QueuedSong, check_player: bool = True):
        # if we're at the end of the queue, return because there is nothing to play.
        if song==None:
            self._set_inactive()
            return
        # Otherwise, if the next song doesn't have a player, create one then play. 
        elif check_player and not song.has_player():
            self._run_task_threadsafe(self._add_player_and_play(song))
            return
        
        # play the song
        super().play(discord.FFmpegOpusAudio(song.player, **FFMPEG_OPTIONS), after = self.play_next)
        self._set_active()
        if hasattr(self, '_on_play'): self._run_task_threadsafe(self._on_play(song, self))
        
        # setup the next song if it has no player
        after_song: QueuedSong | None = self.peek_queue()
        if after_song and not after_song.has_player(): self._run_task_threadsafe(self._add_player_to_song(after_song))
    
    async def _add_player_to_song(self, song: QueuedSong, prioritize: bool = False) -> bool:        
        my_event: asyncio.Event = await self._wait_query(prioritize)
        if self._disconnecting:
            my_event.set()
            return False
        self._query_task = self.loop.create_task(song.add_player())
        res: bool = True
        try:
            await self._query_task
        except asyncio.CancelledError: res = False
        except Exception as e: res = False
        if self._disconnecting: res = False
        
        my_event.set()
        return res and song.has_player()
    
    async def _add_player_and_play(self, song: QueuedSong):
        if song.has_player():
            self._play_song(song, False)
        
        elif song.generating_player:            
            iters: int = 0
            while not song.has_player() and iters<10:
                await asyncio.sleep(1)
                iters+=1
                
            if song.has_player():
                self._play_song(song, False)
            else:
                self.play_next(Exception(f"Failed to play {song.name}"))
                
        elif await self._add_player_to_song(song, True):
            self._play_song(song, False)
            
        else:
            self.play_next(Exception(f"Failed to play {song.name}"))
    
    def _set_active(self):
        self._active = True
        if self._timeout_task: self._timeout_task.cancel()
    
    def _set_inactive(self):
        self._active = False
        if self._timeout_task and not self._timeout_task.done(): self._timeout_task.cancel()
        self._timeout_task = self.loop.create_task(self.inactivity_timeout())
    
    async def inactivity_timeout(self):
        await asyncio.sleep(300)
        await self.disconnect(reason = "Timed out", force = False, cancel_timeout = False)
        
    async def disconnect(self, *, force: bool = False, cancel_timeout: bool = True, reason: str | None = None):
        """Disconnects the bot from its voice channel

        Args:
            force (bool, optional): Force the disconnect even if the bot is not connected. Defaults to False.
        """
        self._disconnecting = True
        
        self.stop()
        await self._connection.disconnect(force=force, wait=True, cleanup = False)
        self.cleanup(cancel_timeout = cancel_timeout, reason = reason)
            
    def cleanup(self, *, cancel_timeout: bool = True, reason: str | None = None):
        self._disconnecting = True
        self.cancel_enqueue()
        
        if self.source and self.is_playing():
            self.source.cleanup()
        if cancel_timeout and self._timeout_task:
            self._timeout_task.cancel()
            
        super().cleanup()
                    
        if hasattr(self, '_on_disconnect') and not self.is_connected():
            self._run_task(self._on_disconnect(self, reason))

    def get_queue(self) -> tuple[int, list[QueuedSong]]:
        """Get the queue and the current song index

        Returns:
            tuple[int, list[QueuedSong]]: (current song index, full song queue)
        """
        return self.next_in_queue-1, self.queue
    
    def toggle_loop(self) -> bool:
        """Toggles whether the queue should loop back to the beginning

        Returns:
            bool: what the loop was set to 
        """
        self.loop_queue = not self.loop_queue
        return self.loop_queue
        
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
    
    def set_on_disconnect(self, func: Callable[[MusicBotClient, str | None], Awaitable[None]]) -> None:
        """Set a function which gets called right after the bot disconnects from voice
        
        Note that it is possible that the bot fails to disconnect, but the disconnect function will get called anyways. 

        Args:
            func (Callable[[MusicBotClient], None]): Function that gets called when this MusicBotClient instance disconnects
        """
        self._on_disconnect: Callable[[MusicBotClient, str | None], Awaitable[None]] = func
        
    def _run_task(self, coro: Coroutine[Any, Any, Any], *, name: str | None = None, context: Any | None = None):
        task: asyncio.Task = self.loop.create_task(coro, name=name, context=context)
        self._bg_tasks.add(task)
        task.add_done_callback(self._bg_tasks.discard)
        
    def _run_task_threadsafe(self, coro: Coroutine[Any, Any, Any]):
        future: asyncio.Future = asyncio.run_coroutine_threadsafe(coro, self.loop)
        self._bg_tasks.add(future)
        future.add_done_callback(self._bg_tasks.discard)
        
        
