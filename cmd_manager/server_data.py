import pickle
from typing import Callable
from discord import Guild

class ServerSettings:
    """
    Stores the settings used by this bot for a single discord server
    """
    def __init__(self, server_id: int, prefix: str="-", possible_prefixes: list[str] = []):
        self.id: int = server_id
        self.prefix: str = prefix
        self.prefixes: list[str] = possible_prefixes
        
    def set_prefix(self, prefix: str):
        if prefix and prefix in self.prefixes:
            self.prefix = prefix
            if hasattr(self, 'on_update'): self.on_update()
            return True
        return False
    
    def _set_on_update(self, on_update: Callable):
        self.on_update = on_update

class ServerData:
    """
    Stores all the ServerSettings used by this bot
    """
    def __init__(self, prefixes: list[str], load_file: str | None = None):
        self.prefixes: list[str] = prefixes
        self.file_loc: str | None = load_file
        self.servers: dict[int, ServerSettings] = {}
        if load_file != None: self.load_servers_from_file(load_file)
        
    def __getitem__(self, key: int | str | Guild) -> ServerSettings:
        """Get saved server info using the server's id (int or str), or by discord.Guild

        If a server is not found, then will add the server using default settings before returning the result
        
        Args:
            key (int | str | Guild): Identifier for which server information we want. 

        Returns:
            ServerSettings: Class containing the saved server information
        """
        server_id: int = key if type(key)==int else key.id if type(key) == Guild else int(key)
        return self.add_server(server_id)
    
    def add_server(self, server_id: int, prefix: str = '-') -> ServerSettings:
        settings: ServerSettings | None = self.servers.get(server_id)
        if settings: return settings
        
        settings = ServerSettings(server_id, prefix, self.prefixes)
        if self.file_loc: settings._set_on_update(lambda: self.save_server_data(self.file_loc))
        self.servers[server_id] = settings
        return settings
    
    # 'server_data/data.pkl'
    def load_servers_from_file(self, file: str) -> dict[int, ServerSettings]:
        with open(file, 'rb') as f:
            saved_prefix_data: dict[int, str] = pickle.load(f)
            for server_id, prefix in saved_prefix_data.items():
                if not prefix in self.prefixes:
                    print(f"Error with server: {server_id}")
                else:
                    self.add_server(server_id, prefix)

            print("Loaded server data")
                    
    def save_server_data(self, file: str | None):
        if file==None:
            return
        prefix_data: dict[int, str]
        for server_id, server_data in self.servers.items():
            prefix_data[server_id] = server_data.prefix
        with open(file, 'wb') as f:
            pickle.dump(prefix_data, f, pickle.HIGHEST_PROTOCOL)
            print("Saved server data")