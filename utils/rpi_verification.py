import discord
from discord.ext import commands
from discord import app_commands

from core import database


class EmailVerificationCog(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.upperclassman_role = 1161340460242063557
        self.co28_role = 1161340010822385694

    """@app_commands.command(name='verify')
    async def verify(self, ctx):
        modal = EmailVerificationModal(self.bot, title="Email Verification")
        await ctx.send_modal(modal)"""

    VR = app_commands.Group(
        name="verification",
        description="Commands for verifying your student status.",
        guild_ids=[1216429016760717322, 1161339749487870062]
    )

    @VR.command(name='verify_code', description="Step 2 of the verification process.")
    @app_commands.describe(code="Enter the verification code sent to your RPI email.")
    async def verify_code(self, interaction: discord.Interaction, code: str):
        if any(role.id in [self.co28_role, self.upperclassman_role] for role in interaction.user.roles):
            await interaction.response.send_message("You are already verified.", ephemeral=True)
            return
        codes = []
        class_year = 0

        expected_code = database.EmailVerification.select().where(database.EmailVerification.discord_id == interaction.user.id)
        if expected_code.exists():
            for record in expected_code:
                codes.append(record.verification_code)
                class_year = record.class_year

        if code in codes:
            await interaction.response.send_message("Verification successful! You are now verified.", ephemeral=True)
            if class_year == "2028":
                role = interaction.guild.get_role(self.co28_role)
                await interaction.user.add_roles(role, reason=f"{interaction.user.name} verified as a student")
            else:
                role = interaction.guild.get_role(self.upperclassman_role)
                await interaction.user.add_roles(role, reason=f"{interaction.user.name} verified as a student")
            return
        await interaction.response.send_message("Invalid verification code. Please try again.", ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmailVerificationCog(bot))