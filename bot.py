import discord
from discord.ext import commands, tasks
from discord import app_commands
import os
import json
from datetime import datetime
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True
intents.voice_states = True

bot = commands.Bot(command_prefix="!", intents=intents)
stats_file = "stats.json"
protection_enabled = {}

def load_stats():
    if not os.path.exists(stats_file):
        with open(stats_file, "w") as f:
            json.dump({}, f)
    with open(stats_file, "r") as f:
        return json.load(f)

def save_stats(stats):
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=4)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    track_voice.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = load_stats()
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats.setdefault(guild_id, {})
    stats[guild_id].setdefault(user_id, {"messages": 0, "voice_time": 0, "last_join": None})
    stats[guild_id][user_id]["messages"] += 1

    save_stats(stats)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    stats = load_stats()
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    stats.setdefault(guild_id, {})
    stats[guild_id].setdefault(user_id, {"messages": 0, "voice_time": 0, "last_join": None})

    if before.channel is None and after.channel is not None:
        # נכנס ל־voice
        stats[guild_id][user_id]["last_join"] = datetime.utcnow().timestamp()

    elif before.channel is not None and after.channel is None:
        # יצא מה־voice
        join_time = stats[guild_id][user_id].get("last_join")
        if join_time:
            duration = datetime.utcnow().timestamp() - join_time
            stats[guild_id][user_id]["voice_time"] += int(duration)
            stats[guild_id][user_id]["last_join"] = None

    save_stats(stats)

@bot.command()
async def stats(ctx):
    stats = load_stats()
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats.get(guild_id, {}).get(user_id, {"messages": 0, "voice_time": 0})
    voice_minutes = user_stats["voice_time"] // 60

    embed = discord.Embed(title="📊 הסטטיסטיקה שלך לשבוע הזה:", color=discord.Color.blue())
    embed.add_field(name="הודעות 📩", value=str(user_stats["messages"]))
    embed.add_field(name="זמן ב־Voice 🗣️", value=f"{voice_minutes} דקות")
    await ctx.send(embed=embed)

# טיקטים
@bot.command()
async def open(ctx):
    embed = discord.Embed(title="לחץ על הכפתור כדי לפתוח טיקט 🎫", color=discord.Color.green())
    button = discord.ui.Button(label="פתח טיקט", style=discord.ButtonStyle.primary)

    async def button_callback(interaction):
        guild = ctx.guild
        category = discord.utils.get(guild.categories, name="ticket")
        if category is None:
            category = await guild.create_category("ticket")

        channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.send(f"{interaction.user.mention} טיקט נפתח בהצלחה.")
        await interaction.response.send_message("הטיקט נפתח!", ephemeral=True)

    button.callback = button_callback
    view = discord.ui.View()
    view.add_item(button)
    await ctx.send(embed=embed, view=view)

# הגנה
@bot.command()
async def enable(ctx):
    protection_enabled[str(ctx.guild.id)] = True
    await ctx.send("🛡️ ההגנה הופעלה בהצלחה.")

@bot.command()
async def disable(ctx):
    protection_enabled[str(ctx.guild.id)] = False
    await ctx.send("⚠️ ההגנה בוטלה.")

@bot.event
async def on_guild_channel_create(channel):
    guild_id = str(channel.guild.id)
    if protection_enabled.get(guild_id, False):
        logs_channel = discord.utils.get(channel.guild.text_channels, name="logs")
        if logs_channel is None:
            logs_channel = await channel.guild.create_text_channel("logs")

        await logs_channel.send(f"⚠️ התראה: נוצר ערוץ חדש: {channel.name}")

@bot.event
async def on_member_join(member):
    guild_id = str(member.guild.id)
    if protection_enabled.get(guild_id, False):
        logs_channel = discord.utils.get(member.guild.text_channels, name="logs")
        if logs_channel is None:
            logs_channel = await member.guild.create_text_channel("logs")

        await logs_channel.send(f"👥 משתמש חדש הצטרף: {member.name}")

# משימה רקע לחישוב זמן ב־Voice כל 60 שניות
@tasks.loop(seconds=60)
async def track_voice():
    stats = load_stats()
    for guild in bot.guilds:
        for member in guild.members:
            if member.bot:
                continue
            if member.voice and member.voice.channel:
                guild_id = str(guild.id)
                user_id = str(member.id)

                stats.setdefault(guild_id, {})
                stats[guild_id].setdefault(user_id, {"messages": 0, "voice_time": 0, "last_join": None})
                stats[guild_id][user_id]["voice_time"] += 60
    save_stats(stats)

# הפעלת הבוט
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
