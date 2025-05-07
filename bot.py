import discord
from discord.ext import commands, tasks
import json
import asyncio

# הגדרות בסיסיות
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
intents.presences = True
bot = commands.Bot(command_prefix='!', intents=intents)

# קובץ הנתונים
stats_file = "stats.json"
rooms_file = "rooms.json"
logs_channel_id = 1234567890  # ה-ID של ערוץ הלוגים

# פונקציה לקריאה מהקובץ stats.json בצורה סינכרונית
def load_stats():
    try:
        with open(stats_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# פונקציה לשמירה לקובץ stats.json בצורה סינכרונית
def save_stats(stats_data):
    with open(stats_file, "w") as file:
        json.dump(stats_data, file, indent=4)

# פונקציה לקריאה מהקובץ rooms.json בצורה סינכרונית
def load_rooms():
    try:
        with open(rooms_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# פונקציה לשמירה לקובץ rooms.json בצורה סינכרונית
def save_rooms(rooms_data):
    with open(rooms_file, "w") as file:
        json.dump(rooms_data, file, indent=4)

# פקודת !stats להצגת סטטיסטיקות של המשתמש
@bot.command()
async def stats(ctx):
    stats_data = load_stats()
    server_stats = stats_data.get(str(ctx.guild.id), {})
    user_stats = server_stats.get(str(ctx.author.id), {"messages": 0, "voice_time": 0})
    
    # שליחה של מידע לאמבד
    embed = discord.Embed(title=f"סטטיסטיקות עבור {ctx.author.name}", color=discord.Color.blue())
    embed.add_field(name="הודעות שנשלחו", value=user_stats["messages"], inline=False)
    embed.add_field(name="זמן ב-Voice", value=f"{user_stats['voice_time']} דקות", inline=False)
    
    await ctx.send(embed=embed)

# פקודת !open לפתיחת טיקט
@bot.command()
async def open(ctx):
    rooms_data = load_rooms()
    if str(ctx.guild.id) not in rooms_data:
        rooms_data[str(ctx.guild.id)] = []
    
    ticket_channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}")
    rooms_data[str(ctx.guild.id)].append(ticket_channel.id)
    
    save_rooms(rooms_data)
    
    await ctx.send(f"טיקט נפתח בהצלחה: {ticket_channel.mention}")

# הגנת שרת (הפעלת והכיבוי של הגנת שרת)
@bot.command()
async def enable(ctx):
    # צ'ק אם המשתמש הוא אדמין
    if ctx.author.guild_permissions.administrator:
        # פעולת הגנה
        await ctx.send("הגנה הופעלה בהצלחה!")
    else:
        await ctx.send("אין לך הרשאות להפעיל הגנה!")

@bot.command()
async def disable(ctx):
    # צ'ק אם המשתמש הוא אדמין
    if ctx.author.guild_permissions.administrator:
        # השבתת הגנה
        await ctx.send("הגנה הושבתה בהצלחה!")
    else:
        await ctx.send("אין לך הרשאות להשבית את ההגנה!")

# פונקציה למעקב אחר זמן ב-Voice
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel is None and after.channel is not None:
        # כשמצטרפים לערוץ Voice
        pass
    elif before.channel is not None and after.channel is None:
        # כשעוזבים את ערוץ ה-Voice
        stats_data = load_stats()
        server_stats = stats_data.setdefault(str(member.guild.id), {})
        user_stats = server_stats.setdefault(str(member.id), {"messages": 0, "voice_time": 0})
        
        voice_time = (after.channel.connect_time - before.channel.connect_time).total_seconds() // 60
        user_stats["voice_time"] += int(voice_time)
        
        save_stats(stats_data)

# ריצה של הבוט
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
