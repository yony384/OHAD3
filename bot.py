import discord
from discord.ext import commands, tasks
from discord.utils import get
from discord import app_commands, Intents, Interaction, ButtonStyle
import json
import os
from datetime import datetime
import asyncio

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

stats_file = "stats.json"
protection_enabled = {}

# Load stats
if os.path.exists(stats_file):
    with open(stats_file, "r") as f:
        stats = json.load(f)
else:
    stats = {}

# Save stats
def save_stats():
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=4)

# Logs setup
async def log_action(guild, content):
    log_channel = discord.utils.get(guild.text_channels, name="logs")
    if not log_channel:
        log_channel = await guild.create_text_channel("logs")
    await log_channel.send(content)

# When bot ready
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    track_voice.start()

# Track messages
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    gid = str(message.guild.id)
    uid = str(message.author.id)

    if gid not in stats:
        stats[gid] = {}
    if uid not in stats[gid]:
        stats[gid][uid] = {"messages": 0, "voice_seconds": 0, "last_join": None}

    stats[gid][uid]["messages"] += 1
    save_stats()

    await bot.process_commands(message)

# Track voice join time
@bot.event
async def on_voice_state_update(member, before, after):
    gid = str(member.guild.id)
    uid = str(member.id)

    if gid not in stats:
        stats[gid] = {}
    if uid not in stats[gid]:
        stats[gid][uid] = {"messages": 0, "voice_seconds": 0, "last_join": None}

    if after.channel and not before.channel:
        stats[gid][uid]["last_join"] = datetime.utcnow().timestamp()
    elif before.channel and not after.channel:
        last_join = stats[gid][uid].get("last_join")
        if last_join:
            duration = int(datetime.utcnow().timestamp() - last_join)
            stats[gid][uid]["voice_seconds"] += duration
            stats[gid][uid]["last_join"] = None
            save_stats()

# Background task: update voice time every 60 sec
@tasks.loop(seconds=60)
async def track_voice():
    for guild in bot.guilds:
        for vc in guild.voice_channels:
            for member in vc.members:
                if member.bot:
                    continue
                gid = str(guild.id)
                uid = str(member.id)
                if gid not in stats:
                    stats[gid] = {}
                if uid not in stats[gid]:
                    stats[gid][uid] = {"messages": 0, "voice_seconds": 0, "last_join": None}
                stats[gid][uid]["voice_seconds"] += 60
    save_stats()

# !stats command
@bot.command()
async def stats(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    user_stats = stats.get(gid, {}).get(uid, {"messages": 0, "voice_seconds": 0})
    minutes = user_stats["voice_seconds"] // 60

    embed = discord.Embed(title="📊 סטטיסטיקות שבועיות", color=discord.Color.blue())
    embed.add_field(name="הודעות 💬", value=str(user_stats["messages"]), inline=False)
    embed.add_field(name="זמן ב־Voice 🕓", value=f"{minutes} דקות", inline=False)
    await ctx.send(embed=embed)

# !open ticket
@bot.command()
async def open(ctx):
    class OpenButton(discord.ui.View):
        @discord.ui.button(label="פתח טיקט", style=discord.ButtonStyle.green)
        async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            category = discord.utils.get(ctx.guild.categories, name="ticket")
            if not category:
                category = await ctx.guild.create_category("ticket")

            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                interaction.user: discord.PermissionOverwrite(view_channel=True),
                ctx.guild.me: discord.PermissionOverwrite(view_channel=True),
            }

            channel = await ctx.guild.create_text_channel(
                name=f"ticket-{interaction.user.name}",
                category=category,
                overwrites=overwrites
            )
            await interaction.response.send_message(f"טיקט נפתח: {channel.mention}", ephemeral=True)

    embed = discord.Embed(title="🎟️ מערכת טיקטים", description="לחץ על הכפתור כדי לפתוח טיקט", color=discord.Color.green())
    await ctx.send(embed=embed, view=OpenButton())

# !enable protection
@bot.command()
@commands.has_permissions(administrator=True)
async def enable(ctx):
    protection_enabled[str(ctx.guild.id)] = True
    await ctx.send("🛡️ הגנה הופעלה.")

# !disable protection
@bot.command()
@commands.has_permissions(administrator=True)
async def disable(ctx):
    protection_enabled[str(ctx.guild.id)] = False
    await ctx.send("🛡️ הגנה בוטלה.")

# Guild protection (logs role creation, channel deletion, etc.)
@bot.event
async def on_guild_channel_delete(channel):
    gid = str(channel.guild.id)
    if protection_enabled.get(gid):
        await log_action(channel.guild, f"⚠️ נמחק ערוץ: {channel.name}")

@bot.event
async def on_guild_channel_create(channel):
    gid = str(channel.guild.id)
    if protection_enabled.get(gid):
        await log_action(channel.guild, f"⚠️ נוצר ערוץ חדש: {channel.name}")

@bot.event
async def on_member_ban(guild, user):
    gid = str(guild.id)
    if protection_enabled.get(gid):
        await log_action(guild, f"⚠️ המשתמש {user} קיבל באן")

@bot.event
async def on_member_remove(member):
    gid = str(member.guild.id)
    if protection_enabled.get(gid):
        await log_action(member.guild, f"⚠️ {member} עזב את השרת או הוסר")

# Run bot
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
