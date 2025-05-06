import discord
from discord.ext import commands, tasks
import json
import datetime
import os
from asyncio import sleep

intents = discord.Intents.all()
client = commands.Bot(command_prefix="!", help_command=None, intents=intents)

# נתונים כלליים
client.message_stats = {}
client.voice_stats = {}

# פונקציה לעדכון נתונים ב-JSON
def update_guild_data():
    with open("stats.json", "w") as f:
        json.dump({"guilds": client.message_stats}, f)

# פונקציה לקרוא את הנתונים מקובץ
def load_guild_data():
    try:
        with open("stats.json", "r") as f:
            return json.load(f).get("guilds", {})
    except FileNotFoundError:
        return {}

# עדכון נתונים בזמן אמת כל 10 שניות
@tasks.loop(seconds=10)
async def update_stats():
    await client.wait_until_ready()
    
    for guild in client.guilds:
        if guild.id not in client.message_stats:
            client.message_stats[guild.id] = {"messages": 0, "voice_time": 0}

        for member in guild.members:
            if not member.bot:
                # עדכון כמות הודעות
                if member.id not in client.message_stats[guild.id]:
                    client.message_stats[guild.id][member.id] = {"messages": 0, "voice_time": 0}
                
                # כל פעם שמישהו שולח הודעה
                @client.event
                async def on_message(message):
                    if message.author.bot:
                        return
                    if message.guild.id == guild.id:
                        client.message_stats[guild.id][message.author.id]["messages"] += 1
                    update_guild_data()

                # עדכון זמן שהייה ב-voice
                @client.event
                async def on_voice_state_update(member, before, after):
                    if not member.bot and member.guild.id == guild.id:
                        # אם נכנס לחדר קול
                        if after.channel is not None and before.channel is None:
                            client.voice_stats[guild.id][member.id] = datetime.datetime.now()
                        # אם יצא מחדר קול
                        if after.channel is None and before.channel is not None:
                            entry_time = client.voice_stats[guild.id].get(member.id)
                            if entry_time:
                                delta = datetime.datetime.now() - entry_time
                                client.message_stats[guild.id][member.id]["voice_time"] += delta.total_seconds()
                            del client.voice_stats[guild.id][member.id]
                        update_guild_data()

# איפוס ביום שבת בחצות
@tasks.loop(hours=24)
async def reset_weekly_stats():
    now = datetime.datetime.now()
    # אם היום הוא שבת בשעה 00:00
    if now.weekday() == 5 and now.hour == 0 and now.minute == 0:
        client.message_stats = {}  # איפוס נתונים
        update_guild_data()
        print("Stats reset to start a new week.")
    await sleep(60)  # נמתין 60 שניות כדי לבדוק כל 60 שניות

# הפעלת הבוט
@client.event
async def on_ready():
    update_stats.start()
    reset_weekly_stats.start()

# טוען את כל ה-cogs מהתיקייה
for filename in os.listdir('./cogs'):
    if filename.endswith('.py'):
        client.load_extension(f'cogs.{filename[:-3]}')

# הפעלת הבוט
client.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GyYtye.g-4PNwaC4Cpkq8wuDFCueWL-5n081x_3GX-BUw")
