import discord
from discord.ext import commands
import json

class Protection(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def get_protection_status(self, guild_id):
        """מייבא את מצב ההגנה מהקובץ JSON"""
        try:
            with open("protection_status.json", "r") as f:
                data = json.load(f)
                return data.get(str(guild_id), {"enabled": False})["enabled"]
        except FileNotFoundError:
            return False

    def set_protection_status(self, guild_id, status):
        """מעדכן את מצב ההגנה בקובץ JSON"""
        try:
            with open("protection_status.json", "r") as f:
                data = json.load(f)
        except FileNotFoundError:
            data = {}
        
        data[str(guild_id)] = {"enabled": status}

        with open("protection_status.json", "w") as f:
            json.dump(data, f)

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def enable(self, ctx):
        """מפעיל את הגנת השרת"""
        self.set_protection_status(ctx.guild.id, True)
        await ctx.send("Protection enabled ✅")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def disable(self, ctx):
        """כיבוי הגנת השרת"""
        self.set_protection_status(ctx.guild.id, False)
        await ctx.send("Protection disabled ❌")

    @commands.command()
    async def protection_status(self, ctx):
        """מציג את מצב ההגנה הנוכחי"""
        is_enabled = self.get_protection_status(ctx.guild.id)
        status = "enabled" if is_enabled else "disabled"
        await ctx.send(f"The server protection is currently {status}.")

# רישום ה-Cog (אסינכרוני!)
async def setup(bot):
    await bot.add_cog(Protection(bot))
