# role_management.py
import traceback

import discord
from discord.ext import commands
from discord.ui import View, Modal, TextInput, Button
import random
from core import database  # Make sure database.py is in the same directory or update the import path accordingly

insults = ["Dingus", "Buffoon", "Clown", "Muppet", "Nincompoop"]


class RoleColorModal(Modal):
    hex_code = TextInput(label="Hex Code", placeholder="Enter a hex code (e.g., #123abc)", max_length=7)

    async def on_submit(self, interaction: discord.Interaction):
        hex_code = self.hex_code.value

        if not (hex_code.startswith('#') and len(hex_code) == 7):
            await interaction.response.send_message("Invalid hex code. Please use the format #123abc.", ephemeral=True)
            return

        user_record = database.ColorUser.select().where(database.ColorUser.user_id == interaction.user.id)

        if user_record.exists():
            role = interaction.guild.get_role(user_record.get().role_id)
            if role:
                await role.edit(colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}")
                await interaction.response.send_message(f"Role {role.name} edited.", ephemeral=True)
            else:
                role_name = interaction.user.name + f"'s Role ({hex_code})"
                role = await interaction.guild.create_role(name=role_name, colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}")
                database.update_user_role(interaction.user.id, role.id)
                await interaction.response.send_message(f"Role {role.name} assigned.", ephemeral=True)
        else:
            role_name = interaction.user.name + f"'s Role ({hex_code})"
            role = await interaction.guild.create_role(name=role_name, colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}")
            query = database.ColorUser.create(user_id=interaction.user.id, role_id=role.id)
            query.save()
            database.update_user_role(interaction.user.id, role.id)
            await interaction.response.send_message(f"Role {role.name} given!", ephemeral=True)

        await interaction.user.add_roles(role, reason=f"{interaction.user.name} requested color change to {hex_code}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Contact rohit if this keeps happening :(.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class RoleNameModal(Modal):
    role_name = TextInput(label="Role Name", placeholder="Enter a Role Name", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        role_name = self.role_name.value

        user_record = database.ColorUser.select().where(database.ColorUser.user_id == interaction.user.id)

        if user_record.exists():
            role = interaction.guild.get_role(user_record.get().role_id)
            if role:
                await role.edit(name=role_name, reason=f"{interaction.user.name} requested name change to {role_name}")
                await interaction.response.send_message(f"Role {role.name} edited.", ephemeral=True)
            else:
                random_hex_code = discord.Color.random()
                role_name = interaction.user.name + f"'s Role ({random_hex_code.value})"
                role = await interaction.guild.create_role(name=role_name, colour=random_hex_code, reason=f"{interaction.user.name} requested name change to {role_name}")
                database.update_user_role(interaction.user.id, role.id)
                await interaction.response.send_message(f"Role {role.name} assigned.", ephemeral=True)
        else:
            random_hex_code = discord.Color.random()
            role_name = interaction.user.name + f"'s Role ({random_hex_code.value})"
            role = await interaction.guild.create_role(name=role_name, colour=random_hex_code, reason=f"{interaction.user.name} requested name change to {role_name}")

            query = database.ColorUser.create(user_id=interaction.user.id, role_id=role.id)
            query.save()
            database.update_user_role(interaction.user.id, role.id)
            await interaction.response.send_message(f"Role {role.name} given!", ephemeral=True)

        await interaction.user.add_roles(role, reason=f"{interaction.user.name} requested name change to {role_name}")

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Contact rohit if this keeps happening :(.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class CustomizeView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view

    @discord.ui.button(label="Customize Role Color", style=discord.ButtonStyle.primary, custom_id="customize_role_color")
    async def customize_button_color(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoleColorModal(title="Customize Your Role Color")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Customize Role Name", style=discord.ButtonStyle.gray, custom_id="customize_role_name")
    async def customize_button_name(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = RoleNameModal(title="Customize Your Role Name")
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Get Roblox Role", style=discord.ButtonStyle.danger, custom_id="get_roblox_role")
    async def get_roblox_role(self, interaction: discord.Interaction, button: discord.ui.Button):
        roblox_role = discord.utils.get(interaction.guild.roles, id=1239657271143698564)
        if roblox_role in interaction.user.roles:
            await interaction.user.remove_roles(roblox_role, reason="User requested to remove Roblox role")
            await interaction.response.send_message("Roblox role removed!", ephemeral=True)
        else:
            await interaction.user.add_roles(roblox_role, reason="User requested to add Roblox role")
            await interaction.response.send_message("Roblox role added!", ephemeral=True)

