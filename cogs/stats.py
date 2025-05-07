import discord
from discord.ext import commands
import json
import os

STATS_FILE = 'stats.json'

def load_stats():
    if not os.path.exists(STATS_FILE):
        with open(STATS_FILE, 'w') as f:
            json.dump({}, f)
    with open(STATS_FILE, 'r') as f:
        return json.load(f)

def save_stats(stats):
    with open(STATS_FILE, 'w') as f:
        json.dump(stats, f, indent=4)

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stats(self, ctx):
        stats = load_stats()
        user_stats = stats.get(str(ctx.author.id))
        if user_stats:
            await ctx.send(
                f"📊 **{ctx.author.name}**\n"
                f"Messages sent: `{user_stats['messages_sent']}`\n"
                f"Time in voice: `{user_stats['time_in_voice']} minutes`"
            )
        else:
            await ctx.send("No stats found for you.")

# הפונקציה שנטענת ע"י load_extension
async def setup(bot):
    await bot.add_cog(Stats(bot))
