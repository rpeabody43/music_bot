import asyncio
import json
from urllib import request

type QueuedSong = QueuedSong

HEADER = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
       'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
       'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
       'Accept-Encoding': 'none',
       'Accept-Language': 'en-US,en;q=0.8',
       'Connection': 'keep-alive'}

class QueuedSong:
    """
    Represents a song in the queue. Contains the URL, name, duration, and thumbnail of the queued video. 
    
    Additionally, has functions for searching for videos using youtube's search bar.
    """
    def __init__(self, url: str | None, name: str, dur: str, thumbnail: str):
        self.name: str = name
        self.url: str | None = url
        self.duration: str = dur
        self.thumbnail: str = thumbnail
    
    async def create(query: str) -> QueuedSong:
        """Creates a QueuedSong, searching for video data if necessary. 

        Args:
            query (str): A video name or url

        Returns:
            QueuedSong: Instance of a QueuedSong containing video information
        """
        name: str = "Unknown"
        url: str = "Unknown"
        duration: str = "??:??:??"
        thumbnail: str = "https://redthread.uoregon.edu/files/original/affd16fd5264cab9197da4cd1a996f820e601ee4.png"
        use_query: bool = True
        if query.startswith("http"):
            if "youtube.com/watch?v=" in query:
                query = query.split('watch?v=')[1]
            else:
                url = query
                use_query = False
        
        if use_query:
            data: dict[str, dict[str, dict]] = QueuedSong.first_query_result(f"https://www.youtube.com/results?search_query={QueuedSong.parse_url_query(query)}")
            name, url, duration, thumbnail = data['title']['runs'][0]['text'], f"https://www.youtube.com/watch?v={data['videoId']}", data['lengthText']['simpleText'], data['thumbnail']['thumbnails'][0]['url']
        
        return QueuedSong(url, name, duration, thumbnail)
        
    def parse_url_query(query: str) -> str:
        """Converts a query (as normal characters) to the format used by youtube search urls (alpha numeric characters or `%ascii hex` otherwise)

        Args:
            query (str): Query in the format of normal ascii characters

        Returns:
            str: The query as it would be seen in a youtube search query url
        """
        return ''.join([c if c.isalnum() else "+" if c==' ' else f"%{hex(ord(c))[2:].upper()}" for c in ' '.join(query.split())])
    
    def find_closing_brace(string: str, open_brace: str, close_brace: str) -> int:
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
    
    async def first_query_result(url: str) -> dict[str, dict[str, dict]]:
        """Searches for a video using a given URL in the format youtube.com/results?search_query= ...

        Args:
            url (str): URL to search videos for

        Returns:
            dict[str, dict[str, dict]]: Dictionary containing some of the video's information. 
        """
        req: request.Request = request.Request(url, headers=HEADER)
        page: str = await asyncio.get_running_loop().run_in_executor(None, lambda: request.urlopen(req).read(750000).decode("utf-8"))
        
        start: int = page.index("\"contents\":[{\"videoRenderer\":{\"")
        end: int = start + QueuedSong.find_closing_brace(page[start:], "{", "}")
        
        video_info: dict[str, dict[str, dict]] = await asyncio.get_running_loop().run_in_executor(None, lambda: json.loads(page[start+12:end+1])['videoRenderer'])
        return video_info