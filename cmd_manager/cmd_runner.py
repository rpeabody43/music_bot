from typing import Any, Callable, Awaitable
from .server_data import ServerData
from discord import Message, Client, Guild

type CmdResult = CmdResult

# Rust has had an irreparable impact on my code
class CmdResult:
    def __init__(self, success: bool, result_value: Any):
        self.success: bool = success
        self.__val: Exception | str | Any = result_value
    
    def ok(val: Any) -> CmdResult:
        return CmdResult(True, val)
    
    def err(err_msg: Exception | str) -> CmdResult:
        return CmdResult(False, err_msg)
    
    def is_ok(self) -> bool:
        return self.success
    
    def is_err(self) -> bool:
        return not self.success
    
    def unwrap(self) -> Any:
        return self.__val if self.success else Exception("Attempted to unwrap an Err Result")
    
    def err_msg(self) -> str | None:
        return None if self.success else f"{self.__val}" + (f" on line {self.__val.__traceback__.tb_lineno}\n{self.__val.__traceback__.tb_frame}" if type(self.__val)==Exception or isinstance(self.__val, BaseException) else "")
    
    def __str__(self) -> str:
        return f"CmdResult::{"Ok" if self.success else "Err"}({str(self.__val)})"

class CmdContext:
    """
    Context given to any 'command' function that the bot may run.
    Includes the bot client, message that initiated the command, and the message content following the command name
    """
    def __init__(self, client: Client, message: Message, arg: str | None):
        self.client: Client = client
        self.message: Message = message
        self.guild: Guild = message.guild
        self.arg: str = arg

class CmdRunner:
    """
    Outlines a discord bot which responds to specific 'commands' sent as a message in a channel the bot has access to
    """
    def __init__(self, client: Client, server_data: ServerData, 
                 on_success: Callable[[CmdContext], Awaitable[None]] | None = None, 
                 on_fail: Callable[[CmdContext], Awaitable[None]] | None = None):
        self.client: Client = client
        self.server_data: ServerData = server_data
        self.commands: dict[str, Callable[[CmdContext], Awaitable[Any]]] = {}
        self.on_success: Callable[[CmdContext], Awaitable[None]] = on_success
        self.on_fail: Callable[[CmdContext], Awaitable[None]] = on_fail
        
    async def _prefix_command(self, ctx: CmdContext) -> CmdResult:
        if self.server_data[ctx.guild].set_prefix(ctx.arg):
            await ctx.message.channel.send(f"Updated prefix to {ctx.arg}")
            return CmdResult.ok(None)
        else:
            return CmdResult.err("Invalid prefix")
        
    def __setitem__(self, key: str | list[str], value: Callable[[CmdContext], Awaitable[Any]]):
        """
        Define a command that this bot will respond to in some way

        Args:
            key (str | list): The string or list of strings which this bot will respond to with the given Callable function
            value (async Callable): The async function that gets run whenever the command string is matched. 
            Note that this function must include an argument of type CmdContext
        """
        if type(key)==list:
            for k in key:
                self.commands[k] = value
        else: self.commands[key] = value        
    
    async def on_message(self, message: Message) -> None | CmdResult:
        """
        Run this whenever a message gets sent to try to run one of the defined commands
        
        If the message has text after the [prefix][command], ie if the message follows the format [prefix][command] [arg],
        then the arg will get passed to the provided command callable

        Args:
            message (discord.Message): The message that was just sent, possibly containing a command

        Returns:
            None | CommandResult: None if not a command, otherwise the result of running the command
        """
        if message.author == self.client.user or message.author.bot:
            return None
        if not message.guild or len(message.content)==0:
            return None
        if message.content==None or message.content[0]!=self.server_data[message.guild].prefix:
            return None
        
        # Get the command and argument
        temp: list = message.content[1::].split(None, 1)
        cmd: str = temp[0]
        arg: str | None = temp[1] if len(temp) > 1 else None
        
        # Fetch the corresponding command, or return none if it isn't defined.
        cmd_func: Callable | None = self.commands.get(cmd)
        if cmd_func==None: return None
        
        try:
            # Run the function and get the result
            async with message.channel.typing():
                res = await cmd_func(CmdContext(self.client, message, arg))
            
            # Context used for on_success and on_fail callbacks
            ctx: CmdContext = CmdContext(self.client, message, cmd)
            
            # If the result is of type CmdResult, run on_success or on_fail callbacks, then return the result
            if type(res)==CmdResult:
                if self.on_success and res.is_ok(): await self.on_success(ctx)
                elif self.on_fail and res.is_err(): await self.on_fail(ctx)
                return res
            
            # Otherwise, assume the command ran successfully and return CmdResult.ok()
            if self.on_success: await self.on_success(ctx)
            
            return CmdResult.ok(res)
        
        # If there was an error while running the command, catch the error and return the exception
        except Exception as e:
            if self.on_fail: await self.on_fail(CmdContext(self.client, message, cmd))
            return CmdResult.err(e)