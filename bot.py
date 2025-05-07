import discord
from discord.ext import commands, tasks
from discord.ext.commands import has_permissions
import json
import os
from datetime import datetime

intents = discord.Intents.all()
bot = commands.Bot(command_prefix='!', intents=intents)

stats_file = "stats.json"
rooms_file = "rooms.json"
protected_guilds = []

# יצירת קובץ אם לא קיים
def ensure_file(file, default):
    if not os.path.exists(file):
        with open(file, "w", encoding='utf-8') as f:
            json.dump(default, f, indent=4, ensure_ascii=False)

ensure_file(stats_file, {})
ensure_file(rooms_file, {})

# טעינת קבצים
def load_json(file):
    with open(file, "r", encoding='utf-8') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, "w", encoding='utf-8') as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# לוג
async def log(guild, message):
    logs = discord.utils.get(guild.text_channels, name="logs")
    if not logs:
        logs = await guild.create_text_channel("logs")
    await logs.send(message)

# מנטר הודעות
@bot.event
async def on_message(message):
    if message.author.bot:
        return

    stats = load_json(stats_file)
    guild_id = str(message.guild.id)
    user_id = str(message.author.id)

    stats.setdefault(guild_id, {}).setdefault(user_id, {"messages": 0, "voice_seconds": 0})
    stats[guild_id][user_id]["messages"] += 1

    save_json(stats_file, stats)
    await bot.process_commands(message)

# מנטר Voice
voice_start_times = {}

@bot.event
async def on_voice_state_update(member, before, after):
    uid = str(member.id)
    gid = str(member.guild.id)

    stats = load_json(stats_file)

    if after.channel and not before.channel:
        voice_start_times[(gid, uid)] = datetime.utcnow()
    elif before.channel and not after.channel:
        start = voice_start_times.pop((gid, uid), None)
        if start:
            duration = (datetime.utcnow() - start).total_seconds()
            stats.setdefault(gid, {}).setdefault(uid, {"messages": 0, "voice_seconds": 0})
            stats[gid][uid]["voice_seconds"] += int(duration)
            save_json(stats_file, stats)

# פקודת !stats
@bot.command()
async def stats(ctx):
    gid = str(ctx.guild.id)
    uid = str(ctx.author.id)

    stats = load_json(stats_file)
    user_stats = stats.get(gid, {}).get(uid, {"messages": 0, "voice_seconds": 0})

    embed = discord.Embed(title="📊 הסטטיסטיקות שלך השבוע", color=discord.Color.green())
    embed.add_field(name="הודעות", value=user_stats["messages"])
    hours = user_stats["voice_seconds"] // 3600
    minutes = (user_stats["voice_seconds"] % 3600) // 60
    embed.add_field(name="זמן ב־Voice", value=f"{int(hours)} שעות ו־{int(minutes)} דקות")
    await ctx.send(embed=embed)

# פקודת !enable
@bot.command()
@has_permissions(administrator=True)
async def enable(ctx):
    guild = ctx.guild
    gid = str(guild.id)
    rooms = {}

    for channel in guild.channels:
        perms = {}
        for role in channel.changed_roles:
            perms[str(role.id)] = {
                "read_messages": channel.permissions_for(role).read_messages,
                "send_messages": channel.permissions_for(role).send_messages
            }
        rooms[str(channel.id)] = {
            "name": channel.name,
            "type": str(channel.type),
            "permissions": perms
        }

    all_data = load_json(rooms_file)
    all_data[gid] = rooms
    save_json(rooms_file, all_data)
    protected_guilds.append(gid)

    await ctx.send("✅ הגנה הופעלה ונשמרו הגדרות החדרים.")
    await log(guild, f"🛡️ ההגנה הופעלה על ידי {ctx.author.mention}.")

# אנטי ניוק ורייד
@bot.event
async def on_guild_channel_delete(channel):
    gid = str(channel.guild.id)
    if gid in protected_guilds:
        await log(channel.guild, f"🚨 ערוץ {channel.name} נמחק!")

@bot.event
async def on_member_join(member):
    gid = str(member.guild.id)
    if gid in protected_guilds:
        await log(member.guild, f"⚠️ {member.mention} הצטרף לשרת.")

# מערכת טיקטים
class TicketView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📩 פתח טיקט", style=discord.ButtonStyle.green)
    async def open_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        user = interaction.user
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="ticket")

        if not category:
            category = await guild.create_category("ticket")

        existing = discord.utils.get(guild.text_channels, name=f"ticket-{user.name}")
        if existing:
            await interaction.response.send_message(f"כבר יש לך טיקט פתוח: {existing.mention}", ephemeral=True)
            return

        ticket_channel = await guild.create_text_channel(
            f"ticket-{user.name}",
            category=category,
            overwrites={
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                user: discord.PermissionOverwrite(read_messages=True)
            }
        )
        await ticket_channel.send(f"{user.mention} פתחת טיקט. אנא פרט את הבעיה.")
        await interaction.response.send_message(f"הטיקט נפתח: {ticket_channel.mention}", ephemeral=True)
        await log(guild, f"🎫 טיקט נפתח על ידי {user.mention}.")

# פקודת !open
@bot.command()
async def open(ctx):
    embed = discord.Embed(title="🎫 פתיחת טיקט", description="לחץ על הכפתור למטה כדי לפתוח טיקט.", color=discord.Color.blue())
    await ctx.send(embed=embed, view=TicketView())

# הרצת הבוט
bot.run("MTM2ODQ5NDk5MTM0MDczMjQ2Nw.GhIkkz.PTGoaidqLNiSapgFwFaFveKMy0819uZDgdxUAA")
