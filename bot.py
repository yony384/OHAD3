import discord
from discord.ext import commands, tasks
import json
import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import time

# יצירת אינסטנציה של הבוט
intents = discord.Intents.default()
intents.message_content = True
intents.members = True  # נדרש כדי לעקוב אחרי חברים ב-voice
bot = commands.Bot(command_prefix="!", intents=intents)

# הגדרת קובץ הסטטיסטיקות
stats_file = "stats.json"

# טוען את הסטטיסטיקות מקובץ JSON
def load_stats():
    if os.path.exists(stats_file):
        with open(stats_file, "r") as f:
            return json.load(f)
    return {}

# שומר את הסטטיסטיקות לקובץ JSON
def save_stats(stats):
    with open(stats_file, "w") as f:
        json.dump(stats, f, indent=4)

# הגדרת המערך הגנתי
protection_enabled = False
logs_channel_id = None

# יצירת חדר logs אם לא קיים
async def create_logs_channel(guild):
    global logs_channel_id
    logs_channel = discord.utils.get(guild.text_channels, name="logs")
    if not logs_channel:
        logs_channel = await guild.create_text_channel("logs")
    logs_channel_id = logs_channel.id

# הגדרת פונקציה לשליחת הודעות לחדר "logs"
async def log_activity(guild, message):
    if logs_channel_id:
        logs_channel = guild.get_channel(logs_channel_id)
        if logs_channel:
            await logs_channel.send(message)

# עדכון הסטטיסטיקות של זמן ב-voice
def update_stats(user_id, server_id, voice_time):
    stats = load_stats()
    if server_id not in stats:
        stats[server_id] = {}
    if user_id not in stats[server_id]:
        stats[server_id][user_id] = {"messages": 0, "voice_time": 0}
    stats[server_id][user_id]["voice_time"] += voice_time
    save_stats(stats)

# משתנים למעקב אחרי הזמן ב-voice
user_voice_start_time = {}

# עדכון הזמן ב-voice על כל כניסת משתמש
@bot.event
async def on_voice_state_update(member, before, after):
    global user_voice_start_time
    server_id = str(member.guild.id)
    user_id = str(member.id)

    # אם המשתמש נכנס ל-voice
    if after.channel is not None and before.channel is None:
        user_voice_start_time[user_id] = time.time()
    
    # אם המשתמש יצא מ-voice
    elif after.channel is None and before.channel is not None:
        if user_id in user_voice_start_time:
            voice_time = int(time.time() - user_voice_start_time[user_id]) // 60  # זמן ב-voice בדקות
            update_stats(user_id, server_id, voice_time)
            del user_voice_start_time[user_id]

# עדכון הזמן ב-voice בזמן קריאת הפקודה !stats
@bot.command(name="stats")
async def stats(ctx):
    stats = load_stats()
    server_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)
    
    if user_id in user_voice_start_time:  # אם המשתמש עדיין ב-voice
        voice_time = int(time.time() - user_voice_start_time[user_id]) // 60
        update_stats(user_id, server_id, voice_time)
        del user_voice_start_time[user_id]

    if server_id in stats and user_id in stats[server_id]:
        messages = stats[server_id][user_id].get("messages", 0)
        voice_time = stats[server_id][user_id].get("voice_time", 0)
        await ctx.send(f"Messages: {messages}, Voice Time: {voice_time} minutes")
    else:
        await ctx.send("No stats found for you!")

# פקודת !open שמייצרת טיקט
@bot.command(name="open")
async def open_ticket(ctx):
    category_name = "ticket"
    category = discord.utils.get(ctx.guild.categories, name=category_name)

    if category is None:
        category = await ctx.guild.create_category(category_name)

    ticket_channel = await ctx.guild.create_text_channel(f"ticket-{ctx.author.name}", category=category)
    await ticket_channel.send(f"Hello {ctx.author.mention}, your ticket has been created!")

# הפעלת הגנת שרת
@bot.command(name="enable")
async def enable_protection(ctx):
    global protection_enabled
    protection_enabled = True
    await ctx.send("Server protection enabled.")

# כיבוי הגנת שרת
@bot.command(name="disable")
async def disable_protection(ctx):
    global protection_enabled
    protection_enabled = False
    await ctx.send("Server protection disabled.")

# הגדרת Web Service מזויף
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b'OK')

def run_fake_server():
    port = int(os.environ.get("PORT", 10000))  # Render דורש להשתמש ב-PROCESS-BOUND PORT
    server = HTTPServer(('0.0.0.0', port), SimpleHandler)
    server.serve_forever()

# הרץ את השרת המזויף בת'רד נפרד
threading.Thread(target=run_fake_server, daemon=True).start()

# הפעלת פקודת עדכון זמן ב-voice
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await create_logs_channel(bot.guilds[0])  # יצירת חדר logs בשרת הראשון
    print("Logs channel created!")
    
# הפעלת הבוט
bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA')
