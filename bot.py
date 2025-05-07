import discord
from discord.ext import commands
import json
import os
import asyncio

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix='!', intents=intents)

STATS_FILE = 'stats.json'
PROTECTION_FILE = 'protection.json'

# וודא שיש קובץ עם נתונים ברגע התחלת הבוט
def load_stats():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {}

def load_protection():
    if os.path.exists(PROTECTION_FILE):
        with open(PROTECTION_FILE, 'r') as f:
            return json.load(f)
    return {}

stats = load_stats()
protection = load_protection()

# פונקציה לשמירת נתוני השעה וההודעות
async def save_stats():
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

async def save_protection():
    with open(PROTECTION_FILE, 'w') as f:
        json.dump(protection, f, indent=4)

# פקודת !stats
@bot.command()
async def stats(ctx):
    user = ctx.author
    if str(user.id) in stats:
        total_messages = stats[str(user.id)].get('messages', 0)
        total_time = stats[str(user.id)].get('time_in_voice', 0)
        await ctx.send(f"Messages: {total_messages} | Time in voice: {total_time} seconds")
    else:
        await ctx.send("No data found for you.")

# פקודת !enable להפעיל הגנת שרת
@bot.command()
async def enable(ctx):
    protection['enabled'] = True
    await save_protection()
    await ctx.send("Protection has been enabled.")

# פקודת !disable לכיבוי הגנת שרת
@bot.command()
async def disable(ctx):
    protection['enabled'] = False
    await save_protection()
    await ctx.send("Protection has been disabled.")

# פקודת !open לפתיחת טיקט
@bot.command()
async def open(ctx):
    await ctx.send("Ticket has been opened.")

# מערכת עדכון שעות ונתונים בזמן אמת
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    # עדכון הודעות
    if str(message.author.id) not in stats:
        stats[str(message.author.id)] = {'messages': 0, 'time_in_voice': 0}

    stats[str(message.author.id)]['messages'] += 1

    # שמירת נתונים
    await save_stats()

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # מעקב אחרי זמן שהות ב-voice
    if before.channel is None and after.channel is not None:  # הצטרפות לערוץ
        stats[str(member.id)]['join_time'] = asyncio.get_event_loop().time()
    elif before.channel is not None and after.channel is None:  # יציאה מערוץ
        if 'join_time' in stats[str(member.id)]:
            total_time = stats[str(member.id)].get('time_in_voice', 0)
            time_spent = asyncio.get_event_loop().time() - stats[str(member.id)]['join_time']
            stats[str(member.id)]['time_in_voice'] = total_time + time_spent
            await save_stats()

bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA')
