import discord
from discord.ext import commands, tasks
import json
import os
from datetime import datetime

# יצירת הבוט
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix='!', intents=intents)

# נתיב לקובץ ה-JSON שיכיל את הנתונים
stats_file = 'stats.json'

# אם הקובץ לא קיים, ניצור אותו
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump({}, f)

# פונקציה לעדכון הסטטיסטיקות ב-JSON
def update_stats():
    with open(stats_file, 'r') as f:
        stats = json.load(f)
    
    # עדכון הסטטיסטיקות
    for guild in bot.guilds:
        if str(guild.id) not in stats:
            stats[str(guild.id)] = {'messages': 0, 'voice_time': 0}
        
    with open(stats_file, 'w') as f:
        json.dump(stats, f)

# פקודת !stats להציג את הסטטיסטיקות
@bot.command(name='stats')
async def stats(ctx):
    # קריאה לסטטיסטיקות מהקובץ
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_stats = stats.get(str(ctx.guild.id), {'messages': 0, 'voice_time': 0})
    
    # יצירת האמבד
    embed = discord.Embed(
        title="סטטיסטיקות של השרת",
        description=f"סטטיסטיקות עבור השרת {ctx.guild.name}",
        color=discord.Color.blue()
    )
    embed.add_field(name="הודעות שנשלחו", value=str(guild_stats['messages']), inline=False)
    embed.add_field(name="זמן ב-voice (בשניות)", value=str(guild_stats['voice_time']), inline=False)

    await ctx.send(embed=embed)

# פקודת !open - פתיחת טיקט
@bot.command(name='open_ticket')
async def open_ticket(ctx):
    # יצירת קטגוריה אם לא קיימת
    category = discord.utils.get(ctx.guild.categories, name='Tickets')
    if not category:
        category = await ctx.guild.create_category('Tickets')

    # יצירת טיקט
    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    channel = await category.create_text_channel(f'ticket-{ctx.author.name}', overwrites=overwrites)
    await channel.send(f"שלום {ctx.author.mention}, הטיקט שלך נפתח. איך אפשר לעזור לך?")

# פקודת !help - הצגת פקודות זמינות
@bot.command(name='show_help')
async def show_help_command(ctx):
    help_message = """
    פקודות זמינות:
    !stats - הצגת סטטיסטיקות הודעות וזמן ב-voice.
    !open_ticket - פתיחת טיקט חדש.
    !ping - בדיקת תגובה.
    !help - הצגת פקודות זמינות.
    """
    await ctx.send(show_help_message)

# פקודת !ping - לבדוק שהבוט פועל
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send(f'פינג: {round(bot.latency * 1000)}ms')

# פונקציה לעקוב אחרי ההודעות שנשלחו
@bot.event
async def on_message(message):
    if message.author.bot:
        return
    # קריאה לסטטיסטיקות מהקובץ
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_stats = stats.get(str(message.guild.id), {'messages': 0, 'voice_time': 0})
    guild_stats['messages'] += 1

    stats[str(message.guild.id)] = guild_stats
    with open(stats_file, 'w') as f:
        json.dump(stats, f)

    await bot.process_commands(message)

# פונקציה לעקוב אחרי זמן ב-voice
@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # קריאה לסטטיסטיקות מהקובץ
    with open(stats_file, 'r') as f:
        stats = json.load(f)

    guild_stats = stats.get(str(member.guild.id), {'messages': 0, 'voice_time': 0})

    # אם חבר נכנס ל-voice channel
    if after.channel and not before.channel:
        guild_stats['voice_time'] -= int(datetime.now().timestamp())

    # אם חבר יצא מ-voice channel
    if not after.channel and before.channel:
        guild_stats['voice_time'] += int(datetime.now().timestamp())

    stats[str(member.guild.id)] = guild_stats
    with open(stats_file, 'w') as f:
        json.dump(stats, f)

# הפעלת הבוט
bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA')
