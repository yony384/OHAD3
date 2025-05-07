import discord
from discord.ext import commands, tasks
import socket
import json
import os

# הגדרות הבוט
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

# נתיב לקובץ סטטיסטיקות
stats_file = 'stats.json'

# נתיב לקובץ טיקטים
tickets_file = 'tickets.json'

# אתחול משתנים
if not os.path.exists(stats_file):
    with open(stats_file, 'w') as f:
        json.dump({}, f)

if not os.path.exists(tickets_file):
    with open(tickets_file, 'w') as f:
        json.dump({}, f)

# פקודת !stats - הצגת סטטיסטיקות
@bot.command(name='stats')
async def stats(ctx):
    user_id = str(ctx.author.id)
    
    # קריאה לסטטיסטיקות מהקובץ
    with open(stats_file, 'r') as f:
        stats_data = json.load(f)

    user_stats = stats_data.get(user_id, {"messages": 0, "voice": 0})

    await ctx.send(f"סטטיסטיקות עבור {ctx.author.name}:\n"
                   f"הודעות: {user_stats['messages']}\n"
                   f"זמן ב-voice: {user_stats['voice']} דקות.")

# פקודת !open_ticket - יצירת טיקט חדש
@bot.command(name='open_ticket')
async def open_ticket(ctx):
    category_name = 'Tickets'
    channel_name = f'ticket-{ctx.author.name}'

    # קבלת קטגוריית הטיקטים
    category = discord.utils.get(ctx.guild.categories, name=category_name)
    if not category:
        category = await ctx.guild.create_category(category_name)

    # יצירת ערוץ טיקט חדש
    ticket_channel = await ctx.guild.create_text_channel(channel_name, category=category)

    # שמירת הטיקט בקובץ
    with open(tickets_file, 'r') as f:
        tickets_data = json.load(f)

    tickets_data[channel_name] = {"user": str(ctx.author.id), "channel_id": str(ticket_channel.id)}

    with open(tickets_file, 'w') as f:
        json.dump(tickets_data, f)

    # שליחה למשתמש על פתיחת הטיקט
    await ticket_channel.send(f"{ctx.author.mention} הטיקט שלך נפתח! תוכל להוסיף שאלות או בקשות כאן.")

    await ctx.send(f"נפתח טיקט חדש עבורך: {ticket_channel.mention}")

# פקודת !ping - בדיקת תגובה
@bot.command(name='ping')
async def ping(ctx):
    await ctx.send('Pong!')

# פקודת !help - הצגת מידע על הפקודות
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

# פונקציה לבדיקת פורטים פתוחים
def check_ports():
    ports_to_check = [80, 443, 8080]  # לדוגמה, פותחים את הפורטים 80, 443 ו-8080
    open_ports = []

    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)  # זמן המתנה לבדיקת כל פורט
        result = sock.connect_ex(('localhost', port))  # מנסה להתחבר לפורט המקומי
        if result == 0:
            open_ports.append(port)
        sock.close()

    if open_ports:
        print(f"פורטים פתוחים: {', '.join(map(str, open_ports))}")
    else:
        print("לא נמצאו פורטים פתוחים.")

# משימה לריצה כל 5 דקות לבדוק פורטים
@tasks.loop(minutes=5)
async def periodic_port_check():
    check_ports()

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')
    periodic_port_check.start()  # הפעלת המשימה לבדוק פורטים כל 5 דקות

# הפעלת הבוט
bot.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.Grw03o.kBReOzSQTOfNVNdWIOC5CCv-1ZtzSRZfXN38bM')  # הכנס את טוקן הבוט שלך כאן
