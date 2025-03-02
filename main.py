# Discord music bot
# irawizza 
# 2/2025 rewrite

# -*- coding: utf-8 -*-
"""
Created on Sun Sep 19 17:22:34 2021

@author: irawi
""" 
import discord
import asyncio
import os

from cmd_manager import setup_runner, CmdRunner, CmdContext, CmdResult
from music_bot import MusicBot, MusicBotClient, QueuedSong
import song_logger


intents: discord.Intents = discord.Intents.all()
client: discord.Client = discord.Client(intents=intents)

bot: CmdRunner = setup_runner(client, on_success = lambda ctx: ctx.message.add_reaction("👍"), on_fail = lambda ctx: ctx.message.add_reaction("👎"))

music_bot: MusicBot = MusicBot(bot)

def split_any(string: str, delims: list[str], start: int = 0) -> tuple[str, str]:
    """
    Split a string once any of the characters in delims is matched
    """
    for i in range(start, len(string)):
        if string[i] in delims:
            return string[:i], string[i:]
    return (string)

# Added functionality for my (friends) server's music bot to show currently playing song as the bot's status
async def on_play(song: QueuedSong, music_client: MusicBotClient):
    await music_bot._default_on_play(song, music_client)
    
    if type(music_client.msg_channel)==discord.TextChannel and music_client.guild.id==462469935436922880:
        song_details = split_any(song.name, [':', '-', '|', '.', '(', '/', '\\', ';'], 4)
        await client.change_presence(
            activity = discord.Game(song_details[0], details = song_details[1]),
            status = discord.Status.online)
        await music_client.loop.run_in_executor(None, song_logger.incr_music_counter, song.url, song.name)

# Reset the status of the bot once it stops playing music
async def on_disconnect(music_client: MusicBotClient, reason: str | None):
    await music_bot._default_on_dc(music_client, reason)
    
    if music_client.guild.id==462469935436922880:
        await client.change_presence(status=discord.Status.idle)

music_bot.set_on_play(on_play)
music_bot.set_on_disconnect(on_disconnect)

# Added functionality for my (friends) server's music bot to save number of times a song is played
async def send_music_counts(ctx: CmdContext):
    data: list[tuple[str, int, str]] = await ctx.client.loop.run_in_executor(None, song_logger.get_music_counts, 20)
    await ctx.message.channel.send('```'+'\n'.join([f"{name}: {count}" for _, name, count in data])+'```')
bot["rewind"] = send_music_counts

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
        if cmd_result.is_err() and len(cmd_result.err_msg()) > 0:
            await message.channel.send(cmd_result.err_msg())
        return
    
    if client.user in message.mentions:
        await message.channel.send(message.author)
        
@client.event
async def on_voice_state_update(member: discord.Member, before: discord.VoiceState, after: discord.VoiceState):
    # Disconnect the bot if it gets moved to the afk channel
    if member==client.user:
        if after.channel==member.guild.afk_channel:
            await music_bot[member.guild].disconnect(reason="Moved to afk channel")
    
    # Disconnect the bot if the vc it's in is empty
    elif after.channel==None and before.channel!=None and len(before.channel.members)==1 and client.user in before.channel.members:
        await music_bot[member.guild].disconnect(reason="Voice channel is empty")
            
client.run(os.getenv("BOT_TOKEN"))
