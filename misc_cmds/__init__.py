from cmd_manager import CmdRunner
from .mcsr_splits import show_splits

def add_misc_cmds (bot: CmdRunner):
    bot['splits'] = show_splits