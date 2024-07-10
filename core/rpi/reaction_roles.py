import traceback
import discord
from discord.ext import commands
from discord.ui import View, Select, Modal, TextInput
from core import database  # Make sure database.py is in the same directory or update the import path accordingly

# Define dorm and class year roles with emojis and descriptions
DORM_ROLES = {
    "Bray": (1260475859664633957, "🏠 Bray, good luck lol"),
    "Nugent": (1260475861811859458, "🌟 Nugent, ngl i thought this was mcdonalds nuggets"),
    "Warren": (1260475864165122071, "🛏️ Warren, coolest dorm name"),
    "Nason": (1260475866652348446, "🔔 Nason, good luck x2"),
    "Barton": (1260475869563060307, "🏀 Barton, congrats on a good dorm hall"),
    "Barh": (1260475871978983465, "🍕 Barh, best dining hall"),
    "Remove Roles": (0, "❌ Remove all housing roles that you have"),
}

CLASS_YEAR_ROLES = {
    "Class of 2024": (1260117771799363614, "🎓 Class of 2024, almost done"),
    "Class of 2025": (1260117772302680146, "📚 Class of 2025, wannabe seniors"),
    "Class of 2026": (1260117772755796068, "🧑‍💻 Class of 2026, fresh and stressed"),
    "Class of 2027": (1260117773355454525, "🛡️ Class of 2027, idk what i can even say to you guys"),
    "Class of 2028": (1260117774059962450, "🚀 Class of 2028, this is probably you"),
    "Class of 2029": (1260117774059962450, "🥁 Class of 2029, archie majors assemble!"),
}

# Role management functions
async def update_role(interaction, role_id, role_type):
    user_roles = interaction.user.roles

    # Check if the selected role is to remove all roles
    if role_id == 0:
        # Remove all dorm-related roles
        for user_role in user_roles:
            if user_role.id in (role_info[0] for role_info in DORM_ROLES.values() if role_info[0] != 0):
                await interaction.user.remove_roles(user_role, reason=f"{interaction.user.name} requested to remove all {role_type} roles")
        await interaction.response.send_message("All housing roles have been removed.", ephemeral=True)
    else:
        role = interaction.guild.get_role(role_id)

        # Remove any existing roles of the same type
        for user_role in user_roles:
            if user_role.id in (role_info[0] for role_info in DORM_ROLES.values() if role_info[0] != 0):
                await interaction.user.remove_roles(user_role, reason=f"{interaction.user.name} changed {role_type} role")

        # Add the new role
        await interaction.user.add_roles(role, reason=f"{interaction.user.name} requested {role_type} role {role.name}")
        await interaction.response.send_message(f"Hall Role: `{role.name}` assigned.", ephemeral=True)

# Views and dropdowns
class DormRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

        dorm_options = [discord.SelectOption(label=dorm, value=str(role_id), description=desc) for dorm, (role_id, desc) in DORM_ROLES.items()]
        self.add_item(DormDropdown(placeholder="Select your dorm", options=dorm_options))

class DormDropdown(Select):
    def __init__(self, placeholder, options):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id="dorm_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])
        await update_role(interaction, selected_role_id, 'dorm')

class ClassYearRoleView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

        class_year_options = [discord.SelectOption(label=year, value=str(role_id), description=desc) for year, (role_id, desc) in CLASS_YEAR_ROLES.items()]
        self.add_item(ClassYearDropdown(placeholder="Select your class year", options=class_year_options))

class ClassYearDropdown(Select):
    def __init__(self, placeholder, options):
        super().__init__(placeholder=placeholder, min_values=1, max_values=1, options=options, custom_id="class_year_dropdown")

    async def callback(self, interaction: discord.Interaction):
        selected_role_id = int(self.values[0])
        await update_role(interaction, selected_role_id, 'class year')

# Add views to bot
class RoleBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        super().__init__(command_prefix=command_prefix, intents=intents)

    async def on_ready(self):
        self.add_view(DormRoleView())
        self.add_view(ClassYearRoleView())
        print(f'Logged in as {self.user}')

