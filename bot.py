import discord
from discord.ext import commands, tasks
from discord import app_commands
import json
import os
from datetime import datetime
import asyncio

intents = discord.Intents.default()
intents.messages = True
intents.guilds = True
intents.members = True
intents.message_content = True
intents.voice_states = True

bot = commands.Bot(command_prefix='!', intents=intents)
stats_file = "stats.json"
protection_enabled = {}

# === סטטיסטיקות ===

if not os.path.exists(stats_file):
    with open(stats_file, "w") as f:
        json.dump({}, f)

def load_stats():
    with open(stats_file, "r") as f:
        return json.load(f)

def save_stats(data):
    with open(stats_file, "w") as f:
        json.dump(data, f, indent=4)

user_voice_joins = {}

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}!')
    track_voice.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = load_stats()
    gid = str(message.guild.id)
    uid = str(message.author.id)
    stats.setdefault(gid, {}).setdefault(uid, {"messages": 0, "voice_minutes": 0})
    stats[gid][uid]["messages"] += 1
    save_stats(stats)

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    gid = str(member.guild.id)

    if after.channel is not None and before.channel is None:
        user_voice_joins[(gid, uid)] = datetime.utcnow()
    elif after.channel is None and before.channel is not None:
        join_time = user_voice_joins.pop((gid, uid), None)
        if join_time:
            minutes = int((datetime.utcnow() - join_time).total_seconds() / 60)
            stats = load_stats()
            stats.setdefault(gid, {}).setdefault(uid, {"messages": 0, "voice_minutes": 0})
            stats[gid][uid]["voice_minutes"] += minutes
            save_stats(stats)

@tasks.loop(minutes=1)
async def track_voice():
    now = datetime.utcnow()
    stats = load_stats()
    for (gid, uid), join_time in user_voice_joins.items():
        minutes = int((now - join_time).total_seconds() / 60)
        stats.setdefault(gid, {}).setdefault(uid, {"messages": 0, "voice_minutes": 0})
        stats[gid][uid]["voice_minutes"] += minutes
        user_voice_joins[(gid, uid)] = now
    save_stats(stats)

@bot.command()
async def stats(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)
    stats = load_stats()
    user_stats = stats.get(gid, {}).get(uid)

    if not user_stats:
        await ctx.send("לא נמצאו נתונים.")
        return

    embed = discord.Embed(title="הסטטיסטיקות שלך", color=discord.Color.green())
    embed.add_field(name="הודעות", value=str(user_stats["messages"]), inline=False)
    embed.add_field(name="זמן ב-Voice (בדקות)", value=str(user_stats["voice_minutes"]), inline=False)
    await ctx.send(embed=embed)

# === מערכת טיקטים ===

@bot.command()
async def open(ctx):
    embed = discord.Embed(title="תמיכה", description="לחץ על הכפתור כדי לפתוח טיקט", color=discord.Color.blurple())
    view = discord.ui.View()
    
    class OpenTicket(discord.ui.Button):
        def __init__(self):
            super().__init__(label="פתח טיקט", style=discord.ButtonStyle.green)

        async def callback(self, interaction):
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name="tickets")
            if category is None:
                category = await guild.create_category("tickets")

            ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
            await ticket_channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
            await ticket_channel.send(f"{interaction.user.mention}, הנה הטיקט שלך!")

            await interaction.response.send_message("טיקט נפתח!", ephemeral=True)

    view.add_item(OpenTicket())
    await ctx.send(embed=embed, view=view)

# === הגנה מניוקים וריידים ===

@bot.command()
async def enable(ctx):
    protection_enabled[ctx.guild.id] = True
    await ctx.send("הגנה הופעלה.")

@bot.command()
async def disable(ctx):
    protection_enabled[ctx.guild.id] = False
    await ctx.send("הגנה בוטלה.")

@bot.event
async def on_guild_channel_create(channel):
    if protection_enabled.get(channel.guild.id):
        log_channel = discord.utils.get(channel.guild.text_channels, name="logs")
        if not log_channel:
            log_channel = await channel.guild.create_text_channel("logs")
        await log_channel.send(f"ערוץ חדש נוצר: {channel.name}")

@bot.event
async def on_member_join(member):
    if protection_enabled.get(member.guild.id):
        log_channel = discord.utils.get(member.guild.text_channels, name="logs")
        if not log_channel:
            log_channel = await member.guild.create_text_channel("logs")
        await log_channel.send(f"חבר חדש הצטרף: {member.name}")

# === הפעלת הבוט ===
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
