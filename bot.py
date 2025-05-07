import discord
from discord.ext import commands
import json
from datetime import datetime
import os

# הגדרת הבוט וההגדרות
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.guild_messages = True
intents.guild_members = True
intents.message_content = True
client = commands.Bot(command_prefix='!', intents=intents)

# משתנים עיקריים
protection = {}  # מערך הגנה לכל שרת
data = {}  # נתוני סטטיסטיקות לכל המשתמשים

# קובץ שמכיל את הנתונים
STATS_FILE = 'stats.json'
PROTECTION_FILE = 'protection.json'
LOGS_FILE = 'logs.json'

# קריאת נתוני המשתמשים
def load_data():
    if os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'r') as f:
            return json.load(f)
    return {}

# שמירת נתוני המשתמשים
def save_data():
    with open(STATS_FILE, 'w') as f:
        json.dump(data, f, indent=2)

# קריאת נתוני הגנת שרת
def load_protection():
    if os.path.exists(PROTECTION_FILE):
        with open(PROTECTION_FILE, 'r') as f:
            return json.load(f)
    return {}

# שמירת הגנת שרת
def save_protection():
    with open(PROTECTION_FILE, 'w') as f:
        json.dump(protection, f, indent=2)

# פונקציה שמבצעת גיבוי של מבנה השרת
def backup_server(guild):
    backup = {
        'channels': []
    }
    for channel in guild.channels:
        backup['channels'].append({
            'name': channel.name,
            'type': channel.type,
            'parent': channel.category_id,
            'permission_overwrites': [{
                'id': perm.id,
                'allow': perm.allow.value,
                'deny': perm.deny.value
            } for perm in channel.permission_overwrites]
        })
    with open(f'backups/{guild.id}.json', 'w') as f:
        json.dump(backup, f, indent=2)

# יצירת חדר "logs" אם לא קיים
async def ensure_log_channel(guild):
    log_channel = discord.utils.get(guild.text_channels, name='logs')
    if not log_channel:
        log_channel = await guild.create_text_channel('logs')
    return log_channel

# רישום פעולות בלוג
async def log_event(guild, content):
    log_channel = await ensure_log_channel(guild)
    await log_channel.send(content)

# הפעלת הגנה
@client.command()
async def enable(ctx):
    protection[ctx.guild.id] = {"protectionEnabled": True}
    save_protection()
    await ctx.send("🛡️ ההגנה הופעלה.")

# כיבוי הגנה
@client.command()
async def disable(ctx):
    protection[ctx.guild.id] = {"protectionEnabled": False}
    save_protection()
    await ctx.send("🛑 ההגנה כובתה.")

# פקודת סטטיסטיקות
@client.command()
async def stats(ctx):
    user_id = str(ctx.author.id)
    if user_id not in data:
        await ctx.send("אין נתונים למשתמש זה.")
        return
    
    user_data = data[user_id]
    voice_time = 0
    if 'voiceJoinTime' in user_data:
        current_time = datetime.now().timestamp()
        voice_time = int(current_time - user_data['voiceJoinTime']) // 60  # בדקות
    
    total_messages = user_data.get('messages', 0)
    await ctx.send(f"{ctx.author.mention} - מספר הודעות: {total_messages}, זמן ב-voice: {voice_time} דקות")

# פקודת פתיחת טיקט
@client.command()
async def open(ctx):
    embed = discord.Embed(title="פתיחת טיקט", description="לחץ על הכפתור למטה כדי לפתוח טיקט", color=discord.Color.blue())
    button = discord.ui.Button(label="📩 פתח טיקט", style=discord.ButtonStyle.primary, custom_id="create_ticket")
    view = discord.ui.View(timeout=None)
    view.add_item(button)
    await ctx.send(embed=embed, view=view)

# לוגיקה של כפתור פתיחת טיקט
@client.event
async def on_interaction(interaction):
    if interaction.custom_id == 'create_ticket':
        # יצירת טיקט חדש (הוספת הודעה או יצירת חדר חדש)
        ticket_channel = await interaction.guild.create_text_channel(f"ticket-{interaction.user.name}")
        await ticket_channel.send(f"טיקט נפתח עבור {interaction.user.mention}")
        await interaction.response.send_message(f"טיקט נפתח בהצלחה: {ticket_channel.mention}", ephemeral=True)

# זיהוי ניוק
@client.event
async def on_guild_channel_create(channel):
    if protection.get(channel.guild.id, {}).get("protectionEnabled"):
        await log_event(channel.guild, f"🎯 נוצר חדר: {channel.name}")

@client.event
async def on_guild_channel_delete(channel):
    if protection.get(channel.guild.id, {}).get("protectionEnabled"):
        await log_event(channel.guild, f"⚠️ נמחק חדר: {channel.name}")

@client.event
async def on_member_ban(guild, user):
    if protection.get(guild.id, {}).get("protectionEnabled"):
        await log_event(guild, f"👤 {user} הושעה.")

@client.event
async def on_member_unban(guild, user):
    if protection.get(guild.id, {}).get("protectionEnabled"):
        await log_event(guild, f"👤 {user} הוסר מההרשעה.")

# הפעלת הבוט
client.run('MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA')
