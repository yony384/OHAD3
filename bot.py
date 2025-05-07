import discord
import os
import socket
import json
from discord.ext import commands, tasks
import asyncio
from datetime import datetime

# הגדרת intents
intents = discord.Intents.default()
intents.message_content = True  # לוודא שהכוונה זו פעילה
intents.members = True  # מאפשר ניטור פעילות של חברים

# יצירת אובייקט הבוט
client = commands.Bot(command_prefix='!', intents=intents)

# הגדרת קובץ ה-JSON שבו נשמור את הסטטיסטיקות
STATS_FILE = 'stats.json'

# פונקציה לבדוק פורטים פתוחים על השרת
def check_open_ports():
    open_ports = []
    # פורטים לבדוק
    ports = [80, 443, 8080, 5000]
    
    for port in ports:
        try:
            # מנסה ליצור חיבור לפורט על כתובת ה-IP המקומית
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)  # זמן חיבור מוגבל
                result = s.connect_ex(('127.0.0.1', port))  # בודק אם הפורט פתוח
                if result == 0:
                    open_ports.append(port)
        except socket.error:
            pass  # אם קרתה שגיאה, מתעלמים ממנה

    return open_ports

# פונקציה לעדכון סטטיסטיקות משתמשים
def update_user_stats():
    # אם קובץ הסטטיסטיקות לא קיים, ניצור אותו
    if not os.path.exists(STATS_FILE):
        stats = {}
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)

    # טוען את הנתונים הנוכחיים
    with open(STATS_FILE, 'r') as f:
        stats = json.load(f)

    # עדכון סטטיסטיקות לכל משתמש
    for guild in client.guilds:
        for member in guild.members:
            if member.bot:
                continue  # לא מעדכן סטטיסטיקות של בוטים

            # אם המשתמש לא קיים בסטטיסטיקות, ניצור לו ערכים חדשים
            if str(member.id) not in stats:
                stats[str(member.id)] = {
                    'messages_sent': 0,
                    'time_in_voice': 0
                }

    # שמירת הנתונים מחדש בקובץ
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f)

# פונקציה לאיתור והפעלת כל ה-cogs
async def load_cogs():
    for filename in os.listdir('./cogs'):
        if filename.endswith('.py'):
            # טוען את כל ה-cogs בתיקיית cogs
            await client.load_extension(f'cogs.{filename[:-3]}')

# אירוע כשבוט מתחבר
@client.event
async def on_ready():
    print(f'Logged in as {client.user}')
    
    # טעינת ה-cogs
    await load_cogs()

    # בדיקה אם יש פורטים פתוחים
    open_ports = check_open_ports()
    
    # הדפסת הפורטים הפתוחים
    if open_ports:
        print(f"Open ports: {', '.join(map(str, open_ports))}")
    else:
        print("No open ports detected.")

    # הפעלת משימה (למשל עדכון סטטיסטיקות כל שבוע)
    update_stats.start()

# טסק שמריץ כל שבוע
@tasks.loop(hours=168)  # כל שבוע
async def update_stats():
    # עדכון סטטיסטיקות
    update_user_stats()
    print("Updated user stats...")

# פקודה להציג את הסטטיסטיקות של המשתמש
@client.command()
async def stats(ctx):
    # טוען את הנתונים
    with open(STATS_FILE, 'r') as f:
        stats = json.load(f)

    # אם המשתמש קיים בסטטיסטיקות
    user_stats = stats.get(str(ctx.author.id))
    if user_stats:
        messages_sent = user_stats['messages_sent']
        time_in_voice = user_stats['time_in_voice']
        await ctx.send(f"**{ctx.author.name}** sent {messages_sent} messages and spent {time_in_voice} minutes in voice channels.")
    else:
        await ctx.send(f"No stats found for {ctx.author.name}.")

# אירוע שמעדכן את הסטטיסטיקות של הודעות שנשלחו
@client.event
async def on_message(message):
    # אם זה לא הודעה של בוט, נעדכן את הסטטיסטיקות
    if not message.author.bot:
        # טוען את הנתונים הנוכחיים
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)

        # אם המשתמש לא קיים בסטטיסטיקות, ניצור לו ערכים חדשים
        if str(message.author.id) not in stats:
            stats[str(message.author.id)] = {
                'messages_sent': 0,
                'time_in_voice': 0
            }

        # עדכון מספר ההודעות
        stats[str(message.author.id)]['messages_sent'] += 1

        # שמירת הנתונים מחדש בקובץ
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)

    # ממשיך לעבד את ההודעות
    await client.process_commands(message)

# אירוע כשמשתמש נכנס לערוץ קול
@client.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    # אם נכנס לערוץ קול חדש או יצא ממנו
    if after.channel and not before.channel:  # נכנס לערוץ קול
        # טוען את הנתונים הנוכחיים
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)

        # אם המשתמש לא קיים בסטטיסטיקות, ניצור לו ערכים חדשים
        if str(member.id) not in stats:
            stats[str(member.id)] = {
                'messages_sent': 0,
                'time_in_voice': 0
            }

        # מתחילים לעקוב אחרי הזמן בערוץ
        stats[str(member.id)]['time_in_voice'] = 0  # מתחילים עם אפס זמן

        # שמירת הנתונים מחדש בקובץ
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)

    elif not after.channel and before.channel:  # יצא מערוץ קול
        # טוען את הנתונים הנוכחיים
        with open(STATS_FILE, 'r') as f:
            stats = json.load(f)

        # שמירת הזמן שבילה בערוץ
        if str(member.id) in stats:
            stats[str(member.id)]['time_in_voice'] += 1  # נניח שנשאר דקה אחת

        # שמירת הנתונים מחדש בקובץ
        with open(STATS_FILE, 'w') as f:
            json.dump(stats, f)

# הרצת הבוט עם ה-token שלך
TOKEN = 'MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GyYtye.g-4PNwaC4Cpkq8wuDFCueWL-5n081x_3GX-BUw'

# הפעלת הבוט
client.run(TOKEN)
