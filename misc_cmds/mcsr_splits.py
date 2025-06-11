import json, math
import discord
from dataclasses import dataclass

from cmd_manager import CmdContext, CmdResult

SECOND_MS = 1000
MIN_MS = 60 * SECOND_MS
HOUR_MS = 60 * MIN_MS

@dataclass
class Segment:
    # "Bastion", "Blind Travel", etc.
    name: str
    # How long the segment took 
    segment_ms: int
    # Time the segment was completed at in the run
    split_ms: int

segment_names = {
    "enter_nether": "Enter Nether",
    "enter_bastion": "Start Bastion",
    "enter_fortress": "Start Fortress",
    "nether_travel": "Blind Travel",
    "enter_stronghold": "Stronghold",
    "enter_end": "Enter End",
}

def _parse_json (run_json: bytes) -> dict:
    run: dict = json.loads(run_json)
    segments = []
    last_split_ms = 0
    for segment in run['timelines']:
        name = segment['name']
        if name in segment_names:
            time = segment['igt']
            segments.append(Segment(
                segment_names[name],
                time - last_split_ms,
                time,
            ))
            last_split_ms = time

    segments.append(Segment(
        "Final",
        run['retimed_igt'] - last_split_ms,
        run['retimed_igt'],
    )) 

    return {
        'segments': segments,
        'world_name': run['world_name'],
        'version': run['mc_version'],
        'type': run['run_type'],
        'category': run['category']
    }


async def show_splits(ctx: CmdContext) -> CmdResult:
    """
        Have the bot parse through a Minecraft speedrun timer record, 
        and display the segments of the run.

        Args:
            ctx (CmdContext): Context given to this command

        Returns:
            CmdResult: Result of running the splits command
    """
    if len(ctx.message.attachments) == 0:
        await ctx.message.reply("Please attach a splits json file")
    attachment = ctx.message.attachments[0]
    file_bytes = await attachment.read()
    try:
        run_dict = _parse_json(file_bytes)
        if run_dict['category'] != "ANY" or run_dict['version'] != '1.16.1':
            await ctx.message.channel.send("This tool is focused on 1.16.1 Any%, other versions / categories may produce unpredictable results")
        segments: list[Segment] = run_dict['segments']
        
        category_str = "Any%" if run_dict['category'] == "ANY" else run_dict['category']
        
        seeded_str = "Random Seed" if run_dict['type'] == "random_seed" else "Set Seed"
        if run_dict['type'] == 'old_world':
            seeded_str = ""

        title = run_dict['world_name']
        footer_str = f"{run_dict['version']} {category_str} {seeded_str}"
        embed = discord.Embed(title=title)
        embed.set_footer(text=footer_str)

        segment_names = []
        segment_times_f = []
        split_times_f = []
        for segment in segments:
            segment_names.append(f"**{segment.name}**")
            segment_times_f.append(_format_time(segment.segment_ms))
            split_times_f.append(_format_time(segment.split_ms))

        # Segment name
        embed.add_field(name="---", value="\n".join(segment_names))
        embed.add_field(name="Segment", value="\n".join(segment_times_f))
        embed.add_field(name="Split", value="\n".join(split_times_f))

        await ctx.message.reply(embed=embed)
        return CmdResult.ok(None)

    except json.JSONDecodeError:
        return CmdResult.err("Unable to decode json")
    except Exception as e: 
        return CmdResult.err(f"Parse error: {e}")

def _format_time (ms: int) -> str:
    hours = math.floor(ms / HOUR_MS)
    mins = math.floor(ms / MIN_MS) % 60
    seconds = math.floor(ms / SECOND_MS) % 60
    centiseconds = math.floor(ms / 10) % 100

    hour_str = ""
    min_str = ""
    second_str = f"{seconds}."
    centisecond_str = str(centiseconds).ljust(2, "0")

    if mins:
        min_str = f"{mins}:"
        second_str = second_str.rjust(3, "0")
    if hours:
        hour_str = f"{hours}:"
        min_str = min_str.rjust(3, "0")

    return f"{hour_str}{min_str}{second_str}{centisecond_str}"