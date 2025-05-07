import discord
from discord.ext import commands, tasks
import json
import os
import asyncio
from datetime import datetime
import socket

# יצירת אובייקט של הבוט עם פריפיקס
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# נתיב לקובץ JSON לאחסון המידע
DATA_FILE = 'data.json'

# פונקציה שתטען את המידע מקובץ JSON
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r') as f:
            return json.load(f)
    return {}

# פונקציה שתשמור את המידע לקובץ JSON
def save_data(data):
    with open(DATA_FILE, 'w') as f:
        json.dump(data, f, indent=4)

# פונקציה שמעדכנת את הסטטיסטיקות של המשתמש
def update_user_stats(user_id, message_count=0, voice_time=0):
    data = load_data()
    user_stats = data.get('users', {})
    
    if user_id not in user_stats:
        user_stats[user_id] = {'messages': 0, 'voice_time': 0}

    user_stats[user_id]['messages'] += message_count
    user_stats[user_id]['voice_time'] += voice_time
    
    data['users'] = user_stats
    save_data(data)

# פונקציה שמעדכנת את שמות החדרים וההגדרות שלהם
def update_channel_settings(channel_id, name, category):
    data = load_data()
    channels = data.get('channels', {})
    
    channels[channel_id] = {'name': name, 'category': category}
    
    data['channels'] = channels
    save_data(data)

# פקודת סטטיסטיקות שמציגה את כמות ההודעות והזמן ב-voice של המשתמש
@bot.command(name='stats')
async def stats(ctx):
    data = load_data()
    user_stats = data.get('users', {}).get(str(ctx.author.id), {'messages': 0, 'voice_time': 0})
    await ctx.send(f"**{ctx.author.name}**: {user_stats['messages']} הודעות, {user_stats['voice_time']} שניות ב-voice")

# פקודת פתיחת טיקט
@bot.command(name='open')
async def open_ticket(ctx):
    category_name = 'ticket'
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    
    if not category:
        category = await ctx.guild.create_category(category_name)

    overwrites = {
        ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }

    ticket_channel = await ctx.guild.create_text_channel(f'ticket-{ctx.author.name}', category=category, overwrites=overwrites)
    await ticket_channel.send(f"שלום {ctx.author.mention}, איך אני יכול לעזור לך היום?")
    update_channel_settings(ticket_channel.id, ticket_channel.name, category.name)

# פונקציה שמבצע עדכון על הודעות שנשלחו
@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    
    update_user_stats(message.author.id, message_count=1)
    await bot.process_commands(message)

# פונקציה שמבצע עדכון על זמן ב-voice
@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        return
    
    # אם הצטרף לערוץ, נתחיל למדוד את הזמן
    if after.channel:
        start_time = datetime.now()
        while member.voice and member.voice.channel == after.channel:
            await asyncio.sleep(5)
        
        end_time = datetime.now()
        duration = (end_time - start_time).seconds
        update_user_stats(member.id, voice_time=duration)

# טעינת הפקודות והקוגים
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')
    await bot.change_presence(activity=discord.Game(name="Managing your server"))
    print(f'Bot is ready!')

# הפונקציה שתוודא שהבוט מאזין לפורטים פתוחים
def check_open_ports(host='127.0.0.1', port=80):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex((host, port))
    if result == 0:
        print(f"פורט {port} פתוח.")
    else:
        print(f"פורט {port} סגור.")
    sock.close()

# בדיקת פורטים כל 10 שניות (כדוגמה)
@tasks.loop(seconds=10)
async def check_ports():
    print("בודק פורטים...")
    check_open_ports(host='127.0.0.1', port=80)  # בדיקה אם הפורט 80 פתוח
    check_open_ports(host='127.0.0.1', port=443) # בדיקה אם הפורט 443 פתוח

# הפעלת הבוט
check_ports.start()  # הפעלת הבדיקה על הפורטים ברקע
bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.Grw03o.kBReOzSQTOfNVNdWIOC5CCv-1ZtzSRZfXN38bM')
