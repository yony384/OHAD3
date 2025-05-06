import discord
from discord.ext import commands

class HelpCommand(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def help(self, ctx):
        """מציג את כל הפקודות של הבוט"""
        embed = discord.Embed(
            title="Server Protection Commands",
            description="Here are the available commands for this bot:",
            color=discord.Color.blue()
        )

        # סריקה אוטומטית של כל הפקודות
        for command in self.bot.commands:
            command_obj = self.bot.get_command(command)
            # הוספת הפקודה לאמבד
            embed.add_field(
                name=f"!{command}",
                value=command_obj.help or "No description available.",
                inline=False
            )

        await ctx.send(embed=embed)

# רישום ה-Cog בצורה אסינכרונית
async def setup(bot):
    await bot.add_cog(HelpCommand(bot))
