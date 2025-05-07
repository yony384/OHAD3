import discord
from discord.ext import commands, tasks
import asyncio
import os
import json
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix="!", intents=intents)

stats_file = "stats.json"
protection_file = "protection.json"

# ========== עזר ==========
def load_json(path):
    if not os.path.exists(path):
        with open(path, "w", encoding="utf-8") as f:
            json.dump({}, f)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ========== אירועים ==========
@bot.event
async def on_ready():
    print(f"{bot.user} מחובר!")
    reset_stats.start()

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = load_json(stats_file)
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats.setdefault(guild_id, {})
    stats[guild_id].setdefault(user_id, {"messages": 0, "voice_time": 0, "joined_at": None})
    stats[guild_id][user_id]["messages"] += 1
    save_json(stats_file, stats)

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    stats = load_json(stats_file)
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    stats.setdefault(guild_id, {})
    stats[guild_id].setdefault(user_id, {"messages": 0, "voice_time": 0, "joined_at": None})

    if not before.channel and after.channel:
        stats[guild_id][user_id]["joined_at"] = datetime.utcnow().timestamp()
    elif before.channel and not after.channel and stats[guild_id][user_id]["joined_at"]:
        joined_at = stats[guild_id][user_id]["joined_at"]
        stats[guild_id][user_id]["voice_time"] += int(datetime.utcnow().timestamp() - joined_at)
        stats[guild_id][user_id]["joined_at"] = None

    save_json(stats_file, stats)

# ========== פקודות ==========
@bot.command()
async def stats(ctx):
    stats = load_json(stats_file)
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats.get(guild_id, {}).get(user_id, {"messages": 0, "voice_time": 0})
    embed = discord.Embed(title="📊 הסטטיסטיקה שלך השבוע", color=discord.Color.blue())
    embed.add_field(name="הודעות", value=str(user_stats["messages"]))
    embed.add_field(name="זמן ב-Voice", value=f'{user_stats["voice_time"] // 60} דקות')
    await ctx.send(embed=embed)

@tasks.loop(hours=1)
async def reset_stats():
    if datetime.utcnow().weekday() == 6 and datetime.utcnow().hour == 0:
        save_json(stats_file, {})
        print("✅ סטטיסטיקות אופסו")

@bot.command()
async def open(ctx):
    embed = discord.Embed(title="🎫 פתיחת טיקט", description="לחץ על הכפתור כדי לפתוח טיקט", color=discord.Color.green())
    view = discord.ui.View()
    view.add_item(discord.ui.Button(label="פתח טיקט", style=discord.ButtonStyle.green, custom_id="open_ticket"))
    await ctx.send(embed=embed, view=view)

@bot.event
async def on_interaction(interaction):
    if interaction.type == discord.InteractionType.component and interaction.data["custom_id"] == "open_ticket":
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="ticket")
        if category is None:
            category = await guild.create_category(name="ticket")
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
        }
        channel = await guild.create_text_channel(name=f"ticket-{interaction.user.name}", overwrites=overwrites, category=category)
        await channel.send(f"{interaction.user.mention}, טיקט נפתח.")
        await interaction.response.send_message("✅ הטיקט נפתח", ephemeral=True)

# ========== הגנה ==========
@bot.command()
async def enable(ctx):
    protections = load_json(protection_file)
    protections[str(ctx.guild.id)] = True
    save_json(protection_file, protections)
    await ctx.send("🛡️ ההגנה הופעלה.")

@bot.command()
async def disable(ctx):
    protections = load_json(protection_file)
    protections[str(ctx.guild.id)] = False
    save_json(protection_file, protections)
    await ctx.send("⚠️ ההגנה בוטלה.")

async def log_action(guild, content):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if log_channel is None:
        log_channel = await guild.create_text_channel("logs")
    await log_channel.send(content)

@bot.event
async def on_guild_channel_delete(channel):
    protections = load_json(protection_file)
    if protections.get(str(channel.guild.id), False):
        await log_action(channel.guild, f"🚨 ערוץ נמחק: {channel.name}")

@bot.event
async def on_guild_channel_create(channel):
    protections = load_json(protection_file)
    if protections.get(str(channel.guild.id), False):
        await log_action(channel.guild, f"⚠️ ערוץ נוצר: {channel.name}")

@bot.event
async def on_guild_role_create(role):
    protections = load_json(protection_file)
    if protections.get(str(role.guild.id), False):
        await log_action(role.guild, f"⚠️ רול נוצר: {role.name}")

@bot.event
async def on_guild_role_delete(role):
    protections = load_json(protection_file)
    if protections.get(str(role.guild.id), False):
        await log_action(role.guild, f"🚨 רול נמחק: {role.name}")

# ========== הפעלה ==========
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
