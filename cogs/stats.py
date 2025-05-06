import discord
from discord.ext import commands

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stats(self, ctx):
        guild_data = self.bot.message_stats.get(ctx.guild.id, {})
        stats_text = f"Server Statistics for {ctx.guild.name}:\n"
        
        for member_id, data in guild_data.items():
            member = ctx.guild.get_member(member_id)
            if member:
                messages = data["messages"]
                voice_time = data["voice_time"] // 3600  # שינוי לשעות
                stats_text += f"{member.name}: {messages} messages, {voice_time} hours in voice\n"
        
        await ctx.send(stats_text)

# רישום ה-Cog
def setup(bot):
    bot.add_cog(Stats(bot))
