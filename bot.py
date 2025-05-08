import discord
from discord.ext import commands, tasks
from discord.ui import View, Button
import json
import datetime
from collections import defaultdict
import os
import time
from dotenv import load_dotenv

load_dotenv()

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

deleted_channels = defaultdict(list)
protection_data = {}

stats_file = "stats.json"
sessions_file = "voice_sessions.json"

# שליחת לוג עם יצירת הערוץ אם לא קיים
async def send_log(guild, message):
    log_channel = discord.utils.get(guild.text_channels, name='logs')
    if not log_channel:
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False)
        }
        log_channel = await guild.create_text_channel('logs', overwrites=overwrites)
    embed = discord.Embed(description=message, color=discord.Color.orange())
    await log_channel.send(embed=embed)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.event
async def on_guild_channel_delete(channel):
    guild_id = str(channel.guild.id)
    now = datetime.datetime.utcnow()

    # שמירת פרטי החדר שנמחק
    channel_data = {
        "name": channel.name,
        "type": str(channel.type),
        "category": channel.category.name if channel.category else None,
        "overwrites": [
            {
                "id": target.id,
                "type": "role" if isinstance(target, discord.Role) else "member",
                "allow": overwrite.pair()[0].value,
                "deny": overwrite.pair()[1].value
            }
            for target, overwrite in channel.overwrites.items()
        ]
    }
    deleted_channels[guild_id].append((now, channel_data))
    deleted_channels[guild_id] = [
        (timestamp, data) for timestamp, data in deleted_channels[guild_id]
        if (now - timestamp).total_seconds() < 120
    ]

    if len(deleted_channels[guild_id]) >= 6:
        try:
            async for entry in channel.guild.audit_logs(limit=1, action=discord.AuditLogAction.channel_delete):
                await channel.guild.kick(entry.user, reason="נמחקו יותר מ-6 חדרים תוך 2 דקות")
                await send_log(channel.guild, f"{entry.user.mention} קיבל קיק על מחיקת 6 חדרים תוך 2 דקות")
        except discord.Forbidden:
            await send_log(channel.guild, "❌ אין הרשאות לבצע קיק.")
        except Exception as e:
            await send_log(channel.guild, f"שגיאה בעת ניסיון לקיק: {e}")

    await send_log(channel.guild, f"🗑️ ערוץ {channel.name} נמחק.")

@bot.command()
@commands.has_permissions(administrator=True)
async def enable(ctx):
    guild = ctx.guild
    data = {}

    categories_data = []
    uncategorized_channels = []

    for category in guild.categories:
        category_channels = []
        for channel in category.channels:
            overwrites = {}
            for target, perms in channel.overwrites.items():
                perms_data = {}
                for perm in discord.Permissions.VALID_FLAGS:
                    value = getattr(perms, perm)
                    if value is True:
                        perms_data[perm] = 1
                    elif value is False:
                        perms_data[perm] = -1
                if isinstance(target, discord.Role) or isinstance(target, discord.Member):
                    overwrites[str(target.id)] = perms_data

            channel_type = "text" if isinstance(channel, discord.TextChannel) else "voice" if isinstance(channel, discord.VoiceChannel) else None
            if channel_type:
                category_channels.append({
                    "id": channel.id,
                    "name": channel.name,
                    "type": channel_type,
                    "overwrites": overwrites
                })

        categories_data.append({
            "id": category.id,
            "name": category.name,
            "channels": category_channels
        })

    for channel in guild.channels:
        if not channel.category:
            overwrites = {}
            for target, perms in channel.overwrites.items():
                perms_data = {}
                for perm in discord.Permissions.VALID_FLAGS:
                    value = getattr(perms, perm)
                    if value is True:
                        perms_data[perm] = 1
                    elif value is False:
                        perms_data[perm] = -1
                if isinstance(target, discord.Role) or isinstance(target, discord.Member):
                    overwrites[str(target.id)] = perms_data

            channel_type = "text" if isinstance(channel, discord.TextChannel) else "voice" if isinstance(channel, discord.VoiceChannel) else None
            if channel_type:
                uncategorized_channels.append({
                    "id": channel.id,
                    "name": channel.name,
                    "type": channel_type,
                    "overwrites": overwrites
                })

    # קריאת נתונים קיימים מ-protection.json אם יש
    try:
        with open("protection.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        data = {}

    guild_id = str(guild.id)
    data[guild_id] = {
        "categories": categories_data,
        "uncategorized_channels": uncategorized_channels
    }

    with open("protection.json", "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

    embed = discord.Embed(title="הפעלת הגנה", description="המבנה של השרת נשמר בהצלחה.", color=discord.Color.green())
    await ctx.send(embed=embed)


@bot.command()
@commands.has_permissions(administrator=True)
async def sload(ctx):
    guild = ctx.guild
    try:
        with open("protection.json", "r", encoding="utf-8") as f:
            data = json.load(f)
    except FileNotFoundError:
        await ctx.send(embed=discord.Embed(description="לא קיימים נתונים לשחזור.", color=discord.Color.red()))
        return

    guild_id = str(guild.id)
    if guild_id not in data:
        await ctx.send(embed=discord.Embed(description="לא קיימים נתונים עבור השרת הזה.", color=discord.Color.red()))
        return

    restored_count = 0
    restored_channels = []
    existing_channel_ids = [ch.id for ch in guild.channels]

    for category_data in data[guild_id].get("categories", []):
        category_name = category_data["name"]
        category_id = category_data["id"]
        saved_channels = category_data["channels"]

        category = discord.utils.get(guild.categories, id=category_id)
        if category is None:
            category = await guild.create_category(name=category_name)
            restored_count += 1

        for channel in saved_channels:
            original_id = channel["id"]
            channel_name = channel["name"]
            channel_type = channel["type"]
            overwrites_data = channel.get("overwrites", {})

            existing = discord.utils.get(guild.channels, id=original_id)
            if existing:
                if existing.category != category:
                    await existing.edit(category=category)
                continue  # אם החדר קיים, אנחנו מעבירים אותו לקטגוריה ונסיים

            overwrites = {}
            for target_id, perms in overwrites_data.items():
                target = guild.get_role(int(target_id)) or guild.get_member(int(target_id))
                if not target:
                    continue
                allow = discord.Permissions.none()
                deny = discord.Permissions.none()
                for perm, value in perms.items():
                    if value == 1:
                        allow.update(**{perm: True})
                    elif value == -1:
                        deny.update(**{perm: True})
                overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)

            if channel_type == "text":
                new_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
            elif channel_type == "voice":
                new_channel = await guild.create_voice_channel(channel_name, category=category, overwrites=overwrites)
            else:
                continue

            restored_count += 1
            restored_channels.append(new_channel.name)

    for channel in data[guild_id].get("uncategorized_channels", []):
        original_id = channel["id"]
        channel_name = channel["name"]
        channel_type = channel["type"]
        overwrites_data = channel.get("overwrites", {})

        if discord.utils.get(guild.channels, id=original_id):
            continue

        overwrites = {}
        for target_id, perms in overwrites_data.items():
            target = guild.get_role(int(target_id)) or guild.get_member(int(target_id))
            if not target:
                continue
            allow = discord.Permissions.none()
            deny = discord.Permissions.none()
            for perm, value in perms.items():
                if value == 1:
                    allow.update(**{perm: True})
                elif value == -1:
                    deny.update(**{perm: True})
            overwrites[target] = discord.PermissionOverwrite.from_pair(allow, deny)

        if channel_type == "text":
            new_channel = await guild.create_text_channel(channel_name, overwrites=overwrites)
        elif channel_type == "voice":
            new_channel = await guild.create_voice_channel(channel_name, overwrites=overwrites)
        else:
            continue

        restored_count += 1
        restored_channels.append(new_channel.name)

    if restored_count == 0:
        embed = discord.Embed(title="שחזור ערוצים", description="לא היו ערוצים לשחזור.", color=discord.Color.orange())
    else:
        embed = discord.Embed(title="שחזור ערוצים", description=f"שוחזרו {restored_count} ערוצים.", color=discord.Color.green())
        embed.add_field(name="ערוצים ששוחזרו:", value="\n".join(restored_channels), inline=False)

    await ctx.send(embed=embed)


@bot.command()
async def topen(ctx):
    class TicketView(View):
        @discord.ui.button(label="פתח טיקט", style=discord.ButtonStyle.green, custom_id="open_ticket")
        async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
            user = interaction.user
            guild = interaction.guild
            category = discord.utils.get(guild.categories, name="Tickets")
            if not category:
                category = await guild.create_category("Tickets")

            existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.id}")
            if existing:
                await interaction.response.send_message("כבר פתחת טיקט.", ephemeral=True)
                return

            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }
            channel = await guild.create_text_channel(f"ticket-{user.id}", category=category, overwrites=overwrites)
            await channel.send(f"{user.mention} ברוך הבא לטיקט שלך!")
            await interaction.response.send_message("הטיקט נפתח.", ephemeral=True)

    embed = discord.Embed(title="פתיחת טיקט", description="לחץ על הכפתור כדי לפתוח טיקט", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

def load_json(filename):
    if os.path.exists(filename):
        with open(filename, "r") as f:
            return json.load(f)
    return {}

def save_json(filename, data):
    with open(filename, "w") as f:
        json.dump(data, f, indent=4)

stats_data = load_json(stats_file)
voice_sessions = load_json(sessions_file)

# פונקציה לאיפוס הנתונים בסיום השבוע
def reset_weekly_data():
    current_time = datetime.datetime.now()
    if current_time.weekday() == 5 and current_time.hour == 0 and current_time.minute == 0:  # יום שבת ב-00:00
        stats_data.clear()  # איפוס הנתונים
        voice_sessions.clear()  # איפוס זמן ה-Voice
        save_json(stats_file, stats_data)
        save_json(sessions_file, voice_sessions)
        print("הנתונים אופטו מחדש.")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats_data.setdefault(guild_id, {}).setdefault(user_id, {"messages": 0, "voice_seconds": 0})
    stats_data[guild_id][user_id]["messages"] += 1

    save_json(stats_file, stats_data)
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    guild_id = str(member.guild.id)
    user_id = str(member.id)

    voice_sessions.setdefault(guild_id, {})

    if before.channel is None and after.channel is not None:
        voice_sessions[guild_id][user_id] = int(time.time())

    elif before.channel is not None and after.channel is None:
        if user_id in voice_sessions[guild_id]:
            join_time = voice_sessions[guild_id].pop(user_id)
            duration = int(time.time()) - join_time

            stats_data.setdefault(guild_id, {}).setdefault(user_id, {"messages": 0, "voice_seconds": 0})
            stats_data[guild_id][user_id]["voice_seconds"] += duration

            save_json(stats_file, stats_data)
            save_json(sessions_file, voice_sessions)
            return

    save_json(sessions_file, voice_sessions)

@bot.command()
async def stats(ctx):
    guild_id = str(ctx.guild.id)
    user_id = str(ctx.author.id)

    user_stats = stats_data.get(guild_id, {}).get(user_id, {"messages": 0, "voice_seconds": 0})
    voice_seconds = user_stats.get("voice_seconds", 0)

    # אם המשתמש כרגע ב־Voice — נוסיף את הזמן שהוא מחובר עכשיו
    if user_id in voice_sessions.get(guild_id, {}):
        join_time = voice_sessions[guild_id][user_id]
        voice_seconds += int(time.time()) - join_time

    hours, remainder = divmod(voice_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    embed = discord.Embed(title="📊 סטטיסטיקות משתמש", color=discord.Color.blue())
    embed.add_field(name="📝 הודעות", value=str(user_stats.get("messages", 0)), inline=True)
    embed.add_field(name="🔊 זמן ב־Voice", value=f"{hours} שעות, {minutes} דקות, {seconds} שניות", inline=True)

    await ctx.send(embed=embed)

@tasks.loop(hours=1)
async def check_reset():
    now = datetime.datetime.now()
    if now.weekday() == 5 and now.hour == 0:  # שבת ב-00:00
        if os.path.exists("stats.json"):
            with open("stats.json", "r") as f:
                stats = json.load(f)
        else:
            stats = {}

        for guild_id in stats:
            for user_id in stats[guild_id]:
                stats[guild_id][user_id]["messages"] = 0
                stats[guild_id][user_id]["voice_time"] = 0

        with open("stats.json", "w") as f:
            json.dump(stats, f, indent=4)

        print("הנתונים אופסו כי התחילה שבת.")

@bot.event
async def on_ready():
    check_reset.start()
    print(f'{bot.user} התחבר בהצלחה!')

bot.run(os.getenv("DISCORD_BOT_TOKEN"))

