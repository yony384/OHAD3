import discord
from discord.ext import commands, tasks
import json
import os
import aiofiles
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

stats_file = "stats.json"  # שם הקובץ שיכיל את הנתונים
log_channel_id = None  # איידי של ערוץ הלוגים (יוכל להתעדכן בהגדרות)

# פוקנציה לקרוא את הנתונים מהקובץ בצורה אסינכרונית
async def load_stats():
    if not os.path.exists(stats_file):
        return {}  # אם הקובץ לא קיים נחזיר מילון ריק
    async with aiofiles.open(stats_file, "r") as file:
        stats_data = await file.read()
        return json.loads(stats_data)

# פונקציה לשמור את הנתונים לקובץ בצורה אסינכרונית
async def save_stats(data):
    async with aiofiles.open(stats_file, "w") as file:
        await file.write(json.dumps(data, indent=4))

# פקודת !stats להצגת הסטטיסטיקות
@bot.command()
async def stats(ctx):
    stats_data = await load_stats()
    
    # יצירת אמבד (Embed) להצגת הנתונים
    embed = discord.Embed(title="Server Stats", color=discord.Color.blue())
    
    embed.add_field(name="Total Messages", value=str(stats_data.get("messages", 0)), inline=False)
    embed.add_field(name="Total Time in Voice", value=str(stats_data.get("voice_time", 0)), inline=False)
    
    await ctx.send(embed=embed)

# פקודת !open לפתיחת טיקט
@bot.command()
async def open(ctx):
    # יצירת קטגוריה אם לא קיימת
    guild = ctx.guild
    category = discord.utils.get(guild.categories, name="ticket")
    if not category:
        category = await guild.create_category("ticket")

    # יצירת תת-ערוץ עם כפתור לפתיחת טיקט
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(read_messages=False),
        ctx.author: discord.PermissionOverwrite(read_messages=True)
    }
    ticket_channel = await guild.create_text_channel(f"ticket-{ctx.author.name}", category=category, overwrites=overwrites)
    await ticket_channel.send(f"שלום {ctx.author.mention}, איך נוכל לעזור לך?")
    await ctx.send(f"טיקט נפתח בהצלחה: {ticket_channel.mention}")

# פקודת !enable ו-!disable להפעיל או לכבות הגנה מניוקים וריידים
@bot.command()
async def enable(ctx):
    global log_channel_id
    if log_channel_id is None:
        log_channel = await ctx.guild.create_text_channel("logs")
        log_channel_id = log_channel.id
    await ctx.send("הגנה נגד ניוקים וריידים הופעלה.")

@bot.command()
async def disable(ctx):
    global log_channel_id
    if log_channel_id:
        log_channel = ctx.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.delete()
    log_channel_id = None
    await ctx.send("הגנה נגד ניוקים וריידים כובתה.")

# פונקציה להוסיף הודעות לסטטיסטיקות
async def update_message_stats(user_id):
    stats_data = await load_stats()
    if user_id not in stats_data:
        stats_data[user_id] = {"messages": 0, "voice_time": 0}
    stats_data[user_id]["messages"] += 1
    await save_stats(stats_data)

# פונקציה לניהול ניוקים וריידים
@bot.event
async def on_member_join(member):
    if log_channel_id:
        log_channel = member.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"User {member} joined the server.")

@bot.event
async def on_member_remove(member):
    if log_channel_id:
        log_channel = member.guild.get_channel(log_channel_id)
        if log_channel:
            await log_channel.send(f"User {member} left the server.")

# התחברות לבוט
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# התחלת הבוט
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
