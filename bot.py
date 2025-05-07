import discord
from discord.ext import commands, tasks
import json
import asyncio
import datetime
from collections import defaultdict

intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.guilds = True
intents.voice_states = True
intents.guild_messages = True
intents.guild_reactions = True

client = commands.Bot(command_prefix="!", intents=intents)

# Load or initialize stats data
def load_stats():
    try:
        with open("stats.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_stats(data):
    with open("stats.json", "w") as f:
        json.dump(data, f, indent=4)

# Load or initialize rooms data
def load_rooms():
    try:
        with open("rooms.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_rooms(data):
    with open("rooms.json", "w") as f:
        json.dump(data, f, indent=4)

# Initialize stats and rooms data
stats = load_stats()
rooms = load_rooms()

# Dictionary to store user voice time and other details
voice_times = defaultdict(lambda: defaultdict(int))  # server_id -> user_id -> time_in_voice
deletion_logs = defaultdict(list)  # server_id -> list of deletion logs

@client.event
async def on_ready():
    print(f"Logged in as {client.user}")

# Command to open a ticket
@client.command()
async def open(ctx):
    channel = ctx.channel
    category = discord.utils.get(ctx.guild.categories, name="tickets")

    if not category:
        category = await ctx.guild.create_category("tickets")

    # Create the ticket channel under the 'tickets' category
    ticket_channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", category=category)

    await ticket_channel.send(f"Ticket opened by {ctx.author.mention}")
    await ctx.send(f"Ticket opened: {ticket_channel.mention}")

# Track voice time
@tasks.loop(minutes=1)
async def track_voice():
    for guild in client.guilds:
        for member in guild.members:
            if member.voice:
                voice_time = voice_times[guild.id][member.id]
                voice_times[guild.id][member.id] = voice_time + 1  # Add 1 minute to the voice time

# Command to get stats
@client.command()
async def stats(ctx):
    user_id = ctx.author.id
    server_id = ctx.guild.id

    # Get the stats from the voice_times dictionary
    voice_time = voice_times[server_id].get(user_id, 0)
    minutes = voice_time
    hours = minutes // 60
    minutes = minutes % 60

    await ctx.send(f"{ctx.author.mention}, you've spent {hours} hours and {minutes} minutes in voice channels.")

# Command to enable protection and save all rooms with permissions
@client.command()
async def enable(ctx):
    server_id = ctx.guild.id

    # Save all channel names and permissions in rooms.json
    rooms_data = {}
    for channel in ctx.guild.channels:
        if isinstance(channel, discord.TextChannel):
            permissions = {}
            for role in ctx.guild.roles:
                permissions[role.name] = {
                    "read_messages": channel.permissions_for(role).read_messages,
                    "send_messages": channel.permissions_for(role).send_messages,
                    "manage_messages": channel.permissions_for(role).manage_messages,
                }
            rooms_data[channel.id] = {
                "name": channel.name,
                "type": "text",
                "created_at": channel.created_at.isoformat(),
                "permissions": permissions
            }
        elif isinstance(channel, discord.VoiceChannel):
            permissions = {}
            for role in ctx.guild.roles:
                permissions[role.name] = {
                    "connect": channel.permissions_for(role).connect,
                    "speak": channel.permissions_for(role).speak,
                    "mute_members": channel.permissions_for(role).mute_members,
                }
            rooms_data[channel.id] = {
                "name": channel.name,
                "type": "voice",
                "created_at": channel.created_at.isoformat(),
                "permissions": permissions
            }

    rooms[server_id] = rooms_data
    save_rooms(rooms)
    await ctx.send(f"Protection enabled. All rooms and their permissions saved for server {ctx.guild.name}.")

# Command to disable protection
@client.command()
async def disable(ctx):
    server_id = ctx.guild.id
    if server_id in rooms:
        rooms[server_id]['protection_enabled'] = False
        save_rooms(rooms)
        await ctx.send("Protection has been disabled.")

# Protection event for deletion of channels
@client.event
async def on_guild_channel_delete(channel):
    server_id = channel.guild.id

    if server_id in rooms and rooms.get(server_id, {}).get('protection_enabled', False):
        deletion_logs[server_id].append({
            "channel": channel.name,
            "time": datetime.datetime.utcnow().isoformat(),
            "deleted_by": str(channel.guild.owner)
        })

        # If there were multiple deletions within a short time, take action
        if len(deletion_logs[server_id]) >= 6:  # More than 6 deletions within the last minute
            time_threshold = datetime.datetime.utcnow() - datetime.timedelta(minutes=1)
            deletions_recent = [log for log in deletion_logs[server_id] if datetime.datetime.fromisoformat(log['time']) > time_threshold]

            if len(deletions_recent) >= 6:
                # Create a logs channel if not exists
                logs_channel = discord.utils.get(channel.guild.text_channels, name="logs")
                if not logs_channel:
                    logs_channel = await channel.guild.create_text_channel("logs")

                await logs_channel.send(f"Suspicious deletion activity detected: {len(deletions_recent)} channels deleted within 1 minute.")
                
                # Kick the user performing suspicious activity (if possible)
                user = channel.guild.owner  # This should be replaced by actual user performing deletions
                try:
                    await user.kick(reason="Multiple channel deletions detected. Possible raid or nuke attempt.")
                    await logs_channel.send(f"{user.mention} has been kicked for suspicious activity (multiple channel deletions).")
                except Exception as e:
                    print(f"Error kicking user: {e}")

        save_rooms(rooms)

# Update voice time when user leaves or joins a voice channel
@client.event
async def on_voice_state_update(member, before, after):
    server_id = member.guild.id
    if before.channel and not after.channel:  # User leaves a voice channel
        voice_time = voice_times[server_id].get(member.id, 0)
        voice_times[server_id][member.id] = voice_time + 1  # Add the time when they leave

    if after.channel:  # User joins a voice channel
        voice_times[server_id][member.id] = 0  # Reset the timer for new session

# Start voice tracking task
track_voice.start()

client.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
