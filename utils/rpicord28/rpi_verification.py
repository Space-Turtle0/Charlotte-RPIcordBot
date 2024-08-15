import discord
from discord import app_commands
from discord.components import SelectOption
from discord.ext import commands

from core import database

MAJOR_SHORT_NAMES = {
    "Architecture": "Arch",
    "Building Sciences": "BuildSci",
    "Aeronautical Engineering": "AeroE",
    "Aerospace": "SpaceE",
    "Biomedical Engineering": "BME",
    "Chemical Engineering": "ChemE",
    "Civil Engineering": "CivE",
    "Computer and Systems Engineering": "CSE",
    "Electrical Engineering": "EE",
    "Engineering Science": "EngSci",
    "Environmental Engineering": "EnvE",
    "Industrial and Management Engineering": "IME",
    "Materials Engineering": "MatE",
    "Mechanical Engineering": "MechE",
    "Nuclear Engineering": "NucE",
    "Biotechnology and Health Economics": "Biotech",
    "Cognitive Science": "CogSci",
    "Communication, Media, and Design": "CMD",
    "Design, Innovation, and Society": "DIS",
    "Economics": "Econ",
    "Electronic Arts": "EA",
    "Electronic Media, Arts, and Communication": "EMAC",
    "Games and Simulation Arts and Sciences": "GSAS",
    "Music": "Music",
    "Philosophy": "Phil",
    "Psychological Science": "PsychSci",
    "Science, Technology, and Society": "STS",
    "Sustainability Studies": "Sustain",
    "Business Analytics": "BA",
    "Business and Management": "BM",
    "Applied Physics": "AppPhys",
    "Biology": "Bio",
    "Biochemistry and Biophysics": "BioChem",
    "Biological Neuroscience": "Neuro",
    "Chemistry": "Chem",
    "Computational Biology": "CompBio",
    "Computer Science": "CS",
    "Environmental Science": "EnvSci",
    "Geology": "Geo",
    "Hydrogeology": "Hydro",
    "Interdisciplinary Science": "IDSci",
    "Mathematics": "Math",
    "Physics": "Phys",
    "Information Technology and Web Science": "ITWS",
    "Other": "Other"
}

BS_MAJORS = [
    "Architecture", "Building Sciences", "Aeronautical Engineering", "Biomedical Engineering", "Chemical Engineering",
    "Civil Engineering", "Computer and Systems Engineering", "Electrical Engineering", "Engineering Science",
    "Environmental Engineering", "Industrial and Management Engineering", "Materials Engineering", "Mechanical Engineering",
    "Nuclear Engineering", "Biotechnology and Health Economics", "Cognitive Science", "Communication, Media, and Design",
    "Design, Innovation, and Society", "Economics", "Electronic Arts", "Electronic Media, Arts, and Communication",
    "Games and Simulation Arts and Sciences", "Music", "Philosophy", "Psychological Science", "Science, Technology, and Society",
    "Sustainability Studies", "Business Analytics", "Business and Management", "Applied Physics", "Biology",
    "Biochemistry and Biophysics", "Biological Neuroscience", "Chemistry", "Computational Biology", "Computer Science",
    "Environmental Science", "Geology", "Hydrogeology", "Interdisciplinary Science", "Mathematics", "Physics",
    "Information Technology and Web Science", "Other"
]

def split_majors(majors, chunk_size):
    for i in range(0, len(majors), chunk_size):
        yield majors[i:i + chunk_size]

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
    @app_commands.describe(
        code="Enter the verification code sent to your RPI email.",
        first_name="Enter your first name."
    )
    async def verify_code(self, interaction: discord.Interaction, code: str, first_name: str):
        if any(role.id in [self.co28_role, self.upperclassman_role] for role in interaction.user.roles):
            await interaction.response.send_message("You are already verified.", ephemeral=True)
            return

        first_name = first_name.capitalize()
        codes = []
        class_year = 0
        email = ""

        expected_code = database.EmailVerification.select().where(database.EmailVerification.discord_id == interaction.user.id)
        if expected_code.exists():
            for record in expected_code:
                codes.append(record.verification_code)
                class_year = record.class_year
                email = record.email
                record.delete_instance()

        check = database.FinalizedEmailVerification.select().where(database.FinalizedEmailVerification.email == email)
        if check.exists():
            for record in check:
                if record.discord_id != interaction.user.id:
                    await interaction.response.send_message("This email has already been used for verification. Please use a different email.", ephemeral=True)
                    return

        if code in codes:
            await interaction.response.send_message("Verification successful! Please select your major from the dropdown.", ephemeral=True)
            await self.ask_major(interaction, first_name, class_year, email)
            return

        await interaction.response.send_message("Invalid verification code. Please try again.", ephemeral=True)

    async def ask_major(self, interaction: discord.Interaction, first_name: str, class_year: int, email: str):
        class MajorSelect(discord.ui.Select):
            def __init__(self, options, placeholder='Select your major...'):
                super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options)
                self.upperclassman_role = 1161340460242063557
                self.co28_role = 1161340010822385694

            async def callback(self, interaction: discord.Interaction):
                short_major = self.values[0]
                major = MAJOR_SHORT_NAMES.get(short_major, short_major)
                nickname = f"{first_name} ({major}, '{str(class_year)[-2:]})"
                await interaction.user.edit(nick=nickname)
                await interaction.response.send_message(f"Your nickname has been updated to: {nickname}", ephemeral=True)

                if class_year == "2028":
                    role = interaction.guild.get_role(self.co28_role)
                    await interaction.user.add_roles(role, reason=f"{interaction.user.name} verified as a student")
                else:
                    role = interaction.guild.get_role(self.upperclassman_role)
                    await interaction.user.add_roles(role, reason=f"{interaction.user.name} verified as a student")

                if major == "Other":
                    await interaction.followup.send("Looks like we don't have your major yet.\n> **Please ping an admin to manually add your major!**", ephemeral=True)

                finalized: database.FinalizedEmailVerification = database.FinalizedEmailVerification.create(
                    discord_id=interaction.user.id, email=email, class_year=class_year)
                finalized.save()

        class MajorSelectView(discord.ui.View):
            def __init__(self):
                super().__init__()
                for chunk in split_majors(list(MAJOR_SHORT_NAMES.keys()), 25):
                    options = [SelectOption(label=major, value=major) for major in chunk]
                    self.add_item(MajorSelect(options))

        await interaction.followup.send("Select your primary major. *You may have to go through the 2nd dropdown if you don't find it in the first!*\n\n> **Click OTHER in the 2nd dropdown if you don't see your major, then ping an Admin to help with your nickname request**", view=MajorSelectView(), ephemeral=True)

async def setup(bot):
    await bot.add_cog(EmailVerificationCog(bot))