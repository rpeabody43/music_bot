# Discord music bot
# irawizza 
# 2/2025 rewrite

# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 17:22:34 2021

@author: irawi
""" 
import discord
from datetime import datetime
import os

from cmd_manager import setup_runner, CmdRunner, CmdContext, CmdResult
from music_bot import MusicBot, MusicBotClient, QueuedSong


intents: discord.Intents = discord.Intents.all()
client: discord.Client = discord.Client(intents=intents)

bot: CmdRunner = setup_runner(client, on_success = lambda ctx: ctx.message.add_reaction("👍"), on_fail = lambda ctx: ctx.message.add_reaction("👎"))

music_bot: MusicBot = MusicBot(bot)

def before_any(string: str, delims: list[str], start: int = 0) -> str:
    """
    Get the start of a string up until any delimiter is found
    """
    for i in range(start, len(string)):
        if string[i] in delims:
            return string[:i]
    return string
    

async def on_play(song: QueuedSong, music_client: MusicBotClient):
    await music_bot._default_on_play(song, music_client)
    
    if type(music_client.msg_channel)==discord.TextChannel and music_client.guild.id==462469935436922880:
        await client.change_presence(
            activity=discord.Game(before_any(song.name, [':', '-', '|', '.', '(', '/', '\\'], 4), 
                                  assets = {'small_image': song.thumbnail}, 
                                  start=datetime.now()), 
            status=discord.Status.online)
    
async def on_disconnect(music_client: MusicBotClient):
    await music_bot._default_on_dc(music_client)
    
    if music_client.guild.id==462469935436922880:
        await client.change_presence(status=discord.Status.idle)

music_bot.set_on_play(on_play)
music_bot.set_on_disconnect(on_disconnect)

@client.event
async def on_ready():
    # global prev_plant
    print('We have logged in as {0.user}'.format(client))
    await client.change_presence(activity=discord.Game("RIP groovy and rythmn :sob:"))
    
    # try:
    #     prev_plant = await load_time()
    #     print("loaded plant time as: "+str(prev_plant))
    # except:
    #     print("could not load plant")
    #     prev_plant=0
        
@client.event
async def on_message(message: discord.Message):
    # Runner for Bot commands
    cmd_result: CmdResult | None = await bot.on_message(message)
    
    # Check the result and send an error message if the command failed
    if cmd_result:
        if cmd_result.is_err():
            await message.channel.send(cmd_result.err_msg())
        return
    
    if client.user in message.mentions:
        await message.channel.send(message.author)
        
@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Disconnect the bot if it gets moved to the afk channel
    if member==client.user:
        if after.channel==member.guild.afk_channel:
            await music_bot.disconnect(CmdContext(client, after.channel, None))
    
    # Disconnect the bot if the vc it's in is empty
    elif after.channel==None and before.channel!=None and len(before.channel.members)==1 and client.user in before.channel.members:
        await music_bot.disconnect(CmdContext(client, before.channel, None))
            
client.run(os.getenv('BOT_TOKEN'))
