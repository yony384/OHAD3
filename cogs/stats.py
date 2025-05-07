import discord
from discord.ext import commands

class Stats(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def stats(self, ctx):
        guild_data = self.bot.message_stats.get(ctx.guild.id, {})
        
        # יצירת האמבד
        embed = discord.Embed(title=f"Server Statistics for {ctx.guild.name}", color=discord.Color.blue())
        
        for member_id, data in guild_data.items():
            member = ctx.guild.get_member(member_id)
            if member:
                messages = data["messages"]
                voice_time = data["voice_time"] // 3600  # המרת שניות לשעות
                embed.add_field(
                    name=member.name,
                    value=f"Messages: {messages}\nVoice Time: {voice_time} hours",
                    inline=False
                )
        
        await ctx.send(embed=embed)

# רישום ה-Cog
async def setup(bot):
    await bot.add_cog(Stats(bot))
