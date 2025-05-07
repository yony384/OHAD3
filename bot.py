import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

stats_file = "stats.json"
protection_file = "protection.json"

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

stats = load_json(stats_file)
protection_data = load_json(protection_file)
voice_times = {}  # זמני התחלה למשתמשים ב-voice

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    track_voice_time.start()

@bot.command()
async def stats(ctx):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    if guild_id in stats and user_id in stats[guild_id]:
        user_stats = stats[guild_id][user_id]
        msg_count = user_stats.get("messages", 0)
        voice_time = user_stats.get("voice_time", 0)

        if user_id in voice_times.get(guild_id, {}):
            start_time = voice_times[guild_id][user_id]
            voice_time += int((datetime.utcnow() - start_time).total_seconds())

        embed = discord.Embed(
            title=f"סטטיסטיקות עבור {ctx.author.name}",
            color=discord.Color.blue()
        )
        embed.add_field(name="הודעות", value=str(msg_count))
        embed.add_field(name="זמן ב-Voice (שניות)", value=str(voice_time))
        await ctx.send(embed=embed)
    else:
        await ctx.send("אין נתונים עליך עדיין.")

@bot.command()
async def enable(ctx):
    guild_id = str(ctx.guild.id)
    protection_data[guild_id] = {
        "enabled": True,
        "protected_channels": [channel.id for channel in ctx.guild.channels],
        "protected_roles": [role.id for role in ctx.guild.roles],
        "protected_emojis": [emoji.id for emoji in ctx.guild.emojis]
    }
    save_json(protection_file, protection_data)
    await ctx.send("🔒 הגנת השרת הופעלה ונשמרה.")

@bot.command()
async def disable(ctx):
    guild_id = str(ctx.guild.id)
    protection_data[guild_id] = {"enabled": False}
    save_json(protection_file, protection_data)
    await ctx.send("🔓 הגנת השרת כובתה.")

@bot.command()
async def load(ctx):
    guild_id = str(ctx.guild.id)
    if guild_id in protection_data:
        enabled = protection_data[guild_id].get("enabled", False)
        embed = discord.Embed(
            title="🔧 סטטוס הגנה",
            description="ההגנה מופעלת ✅" if enabled else "ההגנה כבויה ❌",
            color=discord.Color.green() if enabled else discord.Color.red()
        )
        await ctx.send(embed=embed)
    else:
        await ctx.send("⚠️ אין מידע שמור על הגנת השרת הזה.")

@bot.command()
async def open(ctx):
    button = discord.ui.Button(label="פתח טיקט 🎫", style=discord.ButtonStyle.green)

    async def button_callback(interaction):
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="ticket")
        if not category:
            category = await guild.create_category("ticket")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True)
        }

        ticket_channel = await guild.create_text_channel(f"ticket-{interaction.user.name}", category=category, overwrites=overwrites)
        await interaction.response.send_message(f"טיקט נפתח: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(f"{interaction.user.mention}, ברוך הבא לטיקט שלך.")

    button.callback = button_callback

    view = discord.ui.View()
    view.add_item(button)

    embed = discord.Embed(
        title="מערכת טיקטים",
        description="לחץ על הכפתור כדי לפתוח טיקט.",
        color=discord.Color.blurple()
    )

    await ctx.send(embed=embed, view=view)

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault("messages", 0)
    stats[guild_id][user_id]["messages"] += 1
    save_json(stats_file, stats)

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    voice_times.setdefault(guild_id, {})

    if after.channel and not before.channel:
        voice_times[guild_id][user_id] = datetime.utcnow()
    elif before.channel and not after.channel and user_id in voice_times[guild_id]:
        start_time = voice_times[guild_id].pop(user_id)
        duration = int((datetime.utcnow() - start_time).total_seconds())

        stats.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault("voice_time", 0)
        stats[guild_id][user_id]["voice_time"] += duration
        save_json(stats_file, stats)

@tasks.loop(minutes=1)
async def track_voice_time():
    now = datetime.utcnow()
    for guild_id, users in voice_times.items():
        for user_id, start_time in users.items():
            duration = int((now - start_time).total_seconds())
            stats.setdefault(guild_id, {}).setdefault(user_id, {}).setdefault("voice_time", 0)
            stats[guild_id][user_id]["voice_time"] += duration
            voice_times[guild_id][user_id] = now
    save_json(stats_file, stats)

async def log_action(guild, description):
    logs_channel = discord.utils.get(guild.text_channels, name="logs")
    if not logs_channel:
        logs_channel = await guild.create_text_channel("logs")

    embed = discord.Embed(
        title="📛 פעילות חשודה",
        description=description,
        color=discord.Color.red(),
        timestamp=datetime.utcnow()
    )
    await logs_channel.send(embed=embed)

@bot.event
async def on_guild_channel_delete(channel):
    guild_id = str(channel.guild.id)
    if protection_data.get(guild_id, {}).get("enabled"):
        await log_action(channel.guild, f"🛑 ערוץ נמחק: {channel.name}")

@bot.event
async def on_guild_role_delete(role):
    guild_id = str(role.guild.id)
    if protection_data.get(guild_id, {}).get("enabled"):
        await log_action(role.guild, f"🛑 תפקיד נמחק: {role.name}")

@bot.event
async def on_guild_emojis_update(guild, before, after):
    guild_id = str(guild.id)
    if protection_data.get(guild_id, {}).get("enabled") and len(after) < len(before):
        await log_action(guild, "🛑 אימוג'י נמחק.")

# הכנס את הטוקן שלך כאן
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
