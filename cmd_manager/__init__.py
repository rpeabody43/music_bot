from .cmd_runner import CmdResult, CmdContext, CmdRunner
from . import server_data

def setup_runner(client: cmd_runner.Client, *, 
                 saved_servers_file: str | None = None, prefixes: list[str] = ["!","-","/",":","~",",",".","#","$","%","^","&","*","+","=","_",";"], 
                 on_success: cmd_runner.Callable[[CmdContext], cmd_runner.Any] | None = None, 
                 on_fail: cmd_runner.Callable[[CmdContext], cmd_runner.Any] | None = None) -> CmdRunner:
    """Sets up a command runner, which can be used to assign functions to specific "command" keywords sent in a discord text channel
    
    Args:
        client (Client): The bot's discord client
        saved_servers_file (str | None, optional): File location where server data should be saved. Defaults to None.
        prefixes (_type_, optional): Valid prefixes that a server may use to run commands. Defaults to ["!","-","/",":","~",",",".","#","$","%","^","&","*","+","=","_",";"].
        on_success (Callable[[CmdContext], Any] | None, optional): A function that gets called every time a command runs successfully. Defaults to None.
        on_fail (Callable[[CmdContext], Any] | None, optional): A function that gets called every time a command fails. Defaults to None.

    Returns:
        CmdRunner: Command runner used to run commands. Make sure to call CmdRunner.on_message inside of a @client.event on_message() function!
    """
    return CmdRunner(client, server_data.ServerData(prefixes, saved_servers_file), on_success, on_fail)
