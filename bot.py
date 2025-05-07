import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import asyncio
import aiofiles
import os
from datetime import datetime, timedelta

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

stats_file = 'stats.json'
protection_file = 'protection.json'

async def load_json(path):
    if not os.path.exists(path):
        return {}
    async with aiofiles.open(path, "r", encoding="utf-8") as f:
        contents = await f.read()
        return json.loads(contents)

async def save_json(path, data):
    async with aiofiles.open(path, "w", encoding="utf-8") as f:
        await f.write(json.dumps(data, indent=4))

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    reset_stats.start()

@tasks.loop(hours=1)
async def reset_stats():
    now = datetime.utcnow() + timedelta(hours=3)
    if now.weekday() == 6 and now.hour == 0:
        await save_json(stats_file, {})

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = await load_json(stats_file)
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if guild_id not in stats:
        stats[guild_id] = {}

    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {"messages": 0, "voice_minutes": 0}

    stats[guild_id][user_id]["messages"] += 1
    await save_json(stats_file, stats)

    await bot.process_commands(message)

voice_times = {}

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    if after.channel and not before.channel:
        voice_times[user_id] = datetime.utcnow()
    elif before.channel and not after.channel and user_id in voice_times:
        start_time = voice_times.pop(user_id)
        duration = (datetime.utcnow() - start_time).total_seconds() // 60

        stats = await load_json(stats_file)
        if guild_id not in stats:
            stats[guild_id] = {}

        if user_id not in stats[guild_id]:
            stats[guild_id][user_id] = {"messages": 0, "voice_minutes": 0}

        stats[guild_id][user_id]["voice_minutes"] += int(duration)
        await save_json(stats_file, stats)

@bot.command()
async def stats(ctx):
    stats = await load_json(stats_file)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats.get(guild_id, {}).get(user_id, {"messages": 0, "voice_minutes": 0})

    embed = discord.Embed(title=f"Stats for {ctx.author.display_name}", color=discord.Color.green())
    embed.add_field(name="Messages", value=user_stats["messages"])
    embed.add_field(name="Voice Minutes", value=user_stats["voice_minutes"])
    await ctx.send(embed=embed)

@bot.command()
async def open(ctx):
    embed = discord.Embed(title="Support", description="Click the button to open a ticket.", color=discord.Color.blue())
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="Open Ticket", style=discord.ButtonStyle.green, custom_id="open_ticket"))
    await ctx.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component and interaction.data["custom_id"] == "open_ticket":
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="tickets")
        if not category:
            category = await guild.create_category("tickets")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }

        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await channel.send(f"{interaction.user.mention}, your ticket has been created.")
        await interaction.response.send_message("Ticket created!", ephemeral=True)

@bot.command()
async def enable(ctx):
    guild_id = str(ctx.guild.id)
    protection = await load_json(protection_file)

    protection[guild_id] = {
        "enabled": True,
        "log_channel": ctx.channel.id
    }

    await save_json(protection_file, protection)
    await ctx.send("Anti-raid protection has been enabled. Logging to this channel.")

@bot.command()
async def disable(ctx):
    guild_id = str(ctx.guild.id)
    protection = await load_json(protection_file)

    if guild_id in protection:
        protection[guild_id]["enabled"] = False
        await save_json(protection_file, protection)
        await ctx.send("Anti-raid protection has been disabled.")
    else:
        await ctx.send("Protection was not enabled.")

@bot.event
async def on_member_ban(guild, user):
    await log_action(guild, f"{user} was banned.")

@bot.event
async def on_guild_channel_create(channel):
    await log_action(channel.guild, f"Channel {channel.name} was created.")

@bot.event
async def on_guild_channel_delete(channel):
    await log_action(channel.guild, f"Channel {channel.name} was deleted.")

async def log_action(guild, message):
    protection = await load_json(protection_file)
    guild_id = str(guild.id)

    if guild_id in protection and protection[guild_id]["enabled"]:
        log_channel_id = protection[guild_id]["log_channel"]
        log_channel = guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"🔒 {message}")

bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
