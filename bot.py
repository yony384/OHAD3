import discord
from discord.ext import commands, tasks
from discord.ui import Button, View
import json
import asyncio
import os
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

stats_file = "stats.json"
protection_enabled = {}

# ---------- כלים ----------

def load_json(path):
    if not os.path.exists(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ---------- ניטור הודעות ו-voice ----------

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = load_json(stats_file)
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats.setdefault(guild_id, {}).setdefault(user_id, {"messages": 0, "voice_time": 0, "last_voice": None})
    stats[guild_id][user_id]["messages"] += 1

    save_json(stats_file, stats)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    stats = load_json(stats_file)
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    stats.setdefault(guild_id, {}).setdefault(user_id, {"messages": 0, "voice_time": 0, "last_voice": None})

    now = datetime.utcnow().timestamp()

    if before.channel is None and after.channel is not None:
        stats[guild_id][user_id]["last_voice"] = now

    elif before.channel is not None and after.channel is None:
        last = stats[guild_id][user_id]["last_voice"]
        if last:
            stats[guild_id][user_id]["voice_time"] += int(now - last)
        stats[guild_id][user_id]["last_voice"] = None

    save_json(stats_file, stats)

# ---------- פקודות ----------

@bot.command()
async def stats(ctx):
    stats = load_json(stats_file)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats.get(guild_id, {}).get(user_id)

    if not user_stats:
        await ctx.send("אין נתונים עליך עדיין.")
        return

    minutes = user_stats["voice_time"] // 60
    embed = discord.Embed(title=f"סטטיסטיקה של {ctx.author.display_name}", color=discord.Color.blue())
    embed.add_field(name="הודעות", value=str(user_stats["messages"]))
    embed.add_field(name="דקות ב-Voice", value=str(minutes))

    await ctx.send(embed=embed)

@bot.command()
async def open(ctx):
    async def button_callback(interaction: discord.Interaction):
        category = discord.utils.get(ctx.guild.categories, name="ticket")
        if category is None:
            category = await ctx.guild.create_category("ticket")

        channel = await ctx.guild.create_text_channel(f"ticket-{interaction.user.name}", category=category)
        await channel.set_permissions(interaction.user, read_messages=True, send_messages=True)
        await channel.send(f"{interaction.user.mention} ברוך הבא לטיקט שלך!")
        await interaction.response.send_message(f"נפתח טיקט: {channel.mention}", ephemeral=True)

    button = Button(label="פתח טיקט", style=discord.ButtonStyle.green)
    button.callback = button_callback
    view = View()
    view.add_item(button)

    embed = discord.Embed(title="מערכת טיקטים", description="לחץ על הכפתור כדי לפתוח טיקט.", color=discord.Color.green())
    await ctx.send(embed=embed, view=view)

@bot.command()
async def enable(ctx):
    protection_enabled[str(ctx.guild.id)] = True
    await ctx.send("🔒 ההגנה הופעלה.")

@bot.command()
async def disable(ctx):
    protection_enabled[str(ctx.guild.id)] = False
    await ctx.send("🔓 ההגנה בוטלה.")

# ---------- מערכת אנטי ניוק ----------

@bot.event
async def on_guild_channel_create(channel):
    await check_raid(channel.guild, f"נוצר ערוץ: {channel.name}")

@bot.event
async def on_guild_channel_delete(channel):
    await check_raid(channel.guild, f"נמחק ערוץ: {channel.name}")

@bot.event
async def on_member_join(member):
    await check_raid(member.guild, f"חבר חדש נכנס: {member.name}")

async def check_raid(guild, message):
    if not protection_enabled.get(str(guild.id), False):
        return

    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel is None:
        log_channel = await guild.create_text_channel("logs")

    await log_channel.send(f"[הגנה] {message}")

# ---------- הפעלה ----------

bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
