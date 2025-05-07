import discord
from discord.ext import commands, tasks
import json
import asyncio
import datetime

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# הגדרת קובץ rooms.json לשמירת חדרים
rooms_file = "rooms.json"
logs_channel_id = None  # נמלא את זה לפי הצורך בהגדרת הערוץ logs

# מבנה לדוגמה של rooms.json
# {
#     "guild_id": {
#         "rooms": ["room_id_1", "room_id_2"],
#         "enabled": true
#     }
# }

# טוען את קובץ ה-rooms.json אם קיים
def load_rooms():
    try:
        with open(rooms_file, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

# שומר את חדרים ל-rooms.json
def save_rooms(rooms_data):
    with open(rooms_file, "w") as file:
        json.dump(rooms_data, file, indent=4)

# בודק אם צריך להפעיל או לכבות את ההגנה
@bot.command()
async def enable(ctx):
    rooms_data = load_rooms()
    guild_id = str(ctx.guild.id)

    if guild_id not in rooms_data:
        rooms_data[guild_id] = {
            "rooms": [],
            "enabled": True
        }

    rooms_data[guild_id]["enabled"] = True
    save_rooms(rooms_data)
    await ctx.send("הגנה על החדרים הופעלה!")

@bot.command()
async def disable(ctx):
    rooms_data = load_rooms()
    guild_id = str(ctx.guild.id)

    if guild_id in rooms_data:
        rooms_data[guild_id]["enabled"] = False
        save_rooms(rooms_data)
        await ctx.send("הגנה על החדרים כובתה!")

@bot.command()
async def stats(ctx):
    # שמירת זמן שהות בחדרי Voice
    stats_data = load_stats_data()
    user_id = str(ctx.author.id)
    guild_id = str(ctx.guild.id)
    
    if guild_id not in stats_data:
        stats_data[guild_id] = {}

    if user_id not in stats_data[guild_id]:
        stats_data[guild_id][user_id] = {
            "messages": 0,
            "voice_time": 0
        }

    stats = stats_data[guild_id][user_id]
    await ctx.send(f"סטטיסטיקות שלך:\nהודעות: {stats['messages']}\nזמן ב-voice: {stats['voice_time']} שניות")

    # שמירת הנתונים בקובץ
    save_stats_data(stats_data)

@bot.event
async def on_message(message):
    if not message.author.bot:
        stats_data = load_stats_data()
        user_id = str(message.author.id)
        guild_id = str(message.guild.id)

        if guild_id not in stats_data:
            stats_data[guild_id] = {}

        if user_id not in stats_data[guild_id]:
            stats_data[guild_id][user_id] = {
                "messages": 0,
                "voice_time": 0
            }

        stats_data[guild_id][user_id]["messages"] += 1
        save_stats_data(stats_data)
    
    await bot.process_commands(message)

# פונקציה לניהול סטטיסטיקות
def load_stats_data():
    try:
        with open("stats.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        return {}

def save_stats_data(stats_data):
    with open("stats.json", "w") as file:
        json.dump(stats_data, file, indent=4)

# טיפול בהגנה מניוקים וריידים
@bot.event
async def on_bulk_message_delete(messages):
    rooms_data = load_rooms()
    guild_id = str(messages[0].guild.id)
    
    if guild_id in rooms_data and rooms_data[guild_id]["enabled"]:
        deleted_rooms = len(messages)
        
        # אם נמחקו יותר מ-6 חדרים בזמן קצר
        if deleted_rooms >= 6:
            logs_channel = discord.utils.get(messages[0].guild.text_channels, name='logs')
            if not logs_channel:
                logs_channel = await messages[0].guild.create_text_channel('logs')

            # רישום פעולת מחיקה בלוגים
            await logs_channel.send(f"נמחקו {deleted_rooms} חדרים בתוך פחות מדקה. מבוצע קיק.")

            # קיק למי שביצע את המחיקה
            author = messages[0].author
            if author:
                await author.kick(reason="ניסיון לבצע רייד או ניוק")

# יצירת טיקט
@bot.command()
async def open(ctx):
    # יצירת טיקט עם כפתור
    await ctx.send("הטיקט נפתח!")

# יצירת הערוץ logs במידה ואין
@bot.event
async def on_guild_channel_delete(channel):
    if channel.name == 'logs':
        guild = channel.guild
        await guild.create_text_channel('logs')

# הגדרת תחילת הריצה של הבוט
@bot.event
async def on_ready():
    print(f"{bot.user} connected to the server.")
    rooms_data = load_rooms()
    # טוען חדרים וסטטיסטיקות אם לא קיימים
    if not rooms_data:
        save_rooms(rooms_data)

# ריצה של הבוט
if __name__ == "__main__":
    asyncio.run(bot.start("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA"))
