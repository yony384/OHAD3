import discord
from discord.ext import commands
from discord.ui import Button, View

class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command()
    async def create_ticket(self, ctx):
        # יצירת כפתור
        button = Button(label="Open Ticket", style=discord.ButtonStyle.green)

        async def button_callback(interaction):
            # יצירת הערוץ עבור הטיקט
            overwrites = {
                ctx.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True)
            }
            ticket_channel = await ctx.guild.create_text_channel(f"ticket-{interaction.user.name}", overwrites=overwrites)
            await ticket_channel.send(f"Hello {interaction.user.mention}, your ticket has been created!")
            await interaction.response.send_message(f"Your ticket has been created: {ticket_channel.mention}", ephemeral=True)

        # חיבור הפונקציה לכפתור
        button.callback = button_callback

        # יצירת ה-View
        view = View()
        view.add_item(button)

        # שליחת ההודעה עם הכפתור
        await ctx.send("Click the button to create a ticket:", view=view)

# רישום ה-Cog
def setup(bot):
    bot.add_cog(Tickets(bot))
