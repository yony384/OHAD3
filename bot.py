import discord
from discord.ext import commands
import json
import os
from datetime import datetime
import threading
import socket

# יצירת הבוט
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.voice_states = True
bot = commands.Bot(command_prefix='!', intents=intents)

# נתיב לקובץ ה-JSON
stats_file = 'stats.json'

# יצירת הקובץ אם לא קיים
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump({}, f)

# פקודת !stats
@bot.command(name='stats')
async def stats(ctx):
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats.get(guild_id, {}).get(user_id, {'messages': 0, 'voice_time': 0})

    # המרה לפורמט קריא
    total_seconds = user_stats['voice_time']
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    seconds = total_seconds % 60
    formatted_time = f"{hours} שעות, {minutes} דקות, {seconds} שניות"

    embed = discord.Embed(
        title="הסטטיסטיקות שלך",
        description=f"סטטיסטיקות עבור {ctx.author.display_name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="הודעות שנשלחו", value=str(user_stats['messages']), inline=False)
    embed.add_field(name="זמן ב-voice", value=formatted_time, inline=False)

    await ctx.send(embed=embed)

# פקודת !open_ticket
@bot.command(name='open_ticket')
async def open_ticket(ctx):
    category = discord.utils.get(ctx.guild.categories, name='Tickets')
    if not category:
        category = await ctx.guild.create_category('Tickets')

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await category.create_text_channel(f'ticket-{ctx.author.name}', overwrites=overwrites)
    await channel.send(f"שלום {ctx.author.mention}, הטיקט שלך נפתח. איך אפשר לעזור לך?")

# פקודת !help
@bot.command(name='show_help')
async def show_help_command(ctx):
    show_help_message = """
    פקודות זמינות:
    !stats - הצגת סטטיסטיקות הודעות וזמן ב-voice.
    !open_ticket - פתיחת טיקט חדש.
    !ping - בדיקת תגובה.
    !help - הצגת פקודות זמינות.
    """
    await ctx.send(show_help_message)

# פקודת !ping
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'פינג: {round(bot.latency * 1000)}ms')

# מעקב אחרי הודעות
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    if guild_id not in stats:
        stats[guild_id] = {}

    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {'messages': 0, 'voice_time': 0, 'joined_at': None}

    stats[guild_id][user_id]['messages'] += 1

    with open(stats_file, 'w') as f:
        json.dump(stats, f)

    await bot.process_commands(message)

# מעקב אחרי זמן ב-voice
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_id = str(member.guild.id)
    user_id = str(member.id)

    if guild_id not in stats:
        stats[guild_id] = {}

    if user_id not in stats[guild_id]:
        stats[guild_id][user_id] = {'messages': 0, 'voice_time': 0, 'joined_at': None}

    user_stats = stats[guild_id][user_id]

    # נכנס לערוץ
    if after.channel and not before.channel:
        user_stats['joined_at'] = datetime.now().timestamp()

    # יצא מהערוץ
    if not after.channel and before.channel and user_stats.get('joined_at'):
        join_time = user_stats['joined_at']
        session_duration = int(datetime.now().timestamp() - join_time)
        user_stats['voice_time'] += session_duration
        user_stats['joined_at'] = None

    stats[guild_id][user_id] = user_stats

    with open(stats_file, 'w') as f:
        json.dump(stats, f)

# פתיחת פורט ל-Render
def keep_port_open():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.bind(('0.0.0.0', 8080))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        conn.close()

threading.Thread(target=keep_port_open, daemon=True).start()

# הפעלת הבוט (שנה את הטוקן שלך פה אם צריך)
bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA')
