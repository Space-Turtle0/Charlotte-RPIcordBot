"""
This module provides functionality for customizing Discord role colors and names through interactive modals.

Classes:
    RoleColorModal: A modal for users to input a hex code to change their role color.
    RoleNameModal: A modal for users to input a new name for their role.
    CustomizeView: A persistent view with a dropdown to trigger the role customization modals and manage a specific role.

Only avaliable in the Guild: r(evolution)pi
"""

import traceback

import discord
from discord.ui import View, Modal, TextInput, Select, SelectOption

from core import database


class RoleColorModal(Modal):
    hex_code = TextInput(label="Hex Code", placeholder="Enter a hex code (e.g., #123abc)", max_length=7)

    async def on_submit(self, interaction: discord.Interaction):
        hex_code = self.hex_code.value

        if not (hex_code.startswith('#') and len(hex_code) == 7):
            await interaction.response.send_message("Invalid hex code. Please use the format #123abc.", ephemeral=True)
            return

        user_record = database.ColorUser.select().where(database.ColorUser.user_id == interaction.user.id)
        reference_role = interaction.guild.get_role(1216596310619328642)

        if user_record.exists():
            role = interaction.guild.get_role(user_record.get().role_id)
            if role:
                await role.edit(colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}")
                await interaction.response.send_message(f"Role {role.name} edited.", ephemeral=True)
            else:
                role_name = interaction.user.name + f"'s Role ({hex_code})"
                role = await interaction.guild.create_role(name=role_name, colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}", position=reference_role.position + 1)
                database.update_user_role(interaction.user.id, role.id)
                await interaction.response.send_message(f"Role {role.name} assigned.", ephemeral=True)
        else:
            role_name = interaction.user.name + f"'s Role ({hex_code})"
            role = await interaction.guild.create_role(name=role_name, colour=discord.Colour(int(hex_code[1:], 16)), reason=f"{interaction.user.name} requested color change to {hex_code}", position=reference_role.position + 1)
            query = database.ColorUser.create(user_id=interaction.user.id, role_id=role.id)
            query.save()
            database.update_user_role(interaction.user.id, role.id)
            await interaction.user.add_roles(role, reason=f"{interaction.user.name} requested color change to {hex_code}")
            await interaction.response.send_message(f"Role {role.name} given!", ephemeral=True)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Contact rohit if this keeps happening :(.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class RoleNameModal(Modal):
    role_name = TextInput(label="Role Name", placeholder="Enter a Role Name", max_length=100)

    async def on_submit(self, interaction: discord.Interaction):
        role_name = self.role_name.value

        user_record = database.ColorUser.select().where(database.ColorUser.user_id == interaction.user.id)
        reference_role = interaction.guild.get_role(1216596310619328642)

        if user_record.exists():
            role = interaction.guild.get_role(user_record.get().role_id)
            if role:
                await role.edit(name=role_name, reason=f"{interaction.user.name} requested name change to {role_name}")
                await interaction.response.send_message(f"Role {role.name} edited.", ephemeral=True)
            else:
                random_hex_code = discord.Color.random()
                role_name = interaction.user.name + f"'s Role ({random_hex_code.value})"
                role = await interaction.guild.create_role(name=role_name, colour=random_hex_code, reason=f"{interaction.user.name} requested name change to {role_name}", position=reference_role.position + 1)
                database.update_user_role(interaction.user.id, role.id)
                await interaction.response.send_message(f"Role {role.name} assigned.", ephemeral=True)
        else:
            random_hex_code = discord.Color.random()
            role_name = interaction.user.name + f"'s Role ({random_hex_code.value})"
            role = await interaction.guild.create_role(name=role_name, colour=random_hex_code, reason=f"{interaction.user.name} requested name change to {role_name}", position=reference_role.position + 1)
            query = database.ColorUser.create(user_id=interaction.user.id, role_id=role.id)
            query.save()
            database.update_user_role(interaction.user.id, role.id)
            await interaction.user.add_roles(role, reason=f"{interaction.user.name} requested name change to {role_name}")
            await interaction.response.send_message(f"Role {role.name} given!", ephemeral=True)


    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Contact rohit if this keeps happening :(.', ephemeral=True)

        # Make sure we know what the error actually is
        traceback.print_exception(type(error), error, error.__traceback__)


class CustomizeView(View):
    def __init__(self):
        super().__init__(timeout=None)  # Persistent view
        options = [
            SelectOption(label="Customize Role Color", value="customize_role_color", emoji="🎨"),
            SelectOption(label="Customize Role Name", value="customize_role_name", emoji="📝"),
            SelectOption(label="Get Roblox Role", value="get_roblox_role", emoji="🤖"),
            SelectOption(label="Get Valorant Role", value="get_valorant_role", emoji="🔫")
        ]
        self.add_item(CustomizeDropdown(options=options))

class CustomizeDropdown(Select):
    def __init__(self, options):
        super().__init__(placeholder="Choose an action...", min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        if self.values[0] == "customize_role_color":
            modal = RoleColorModal(title="Customize Your Role Color")
            await interaction.response.send_modal(modal)
        elif self.values[0] == "customize_role_name":
            modal = RoleNameModal(title="Customize Your Role Name")
            await interaction.response.send_modal(modal)
        elif self.values[0] == "get_roblox_role":
            roblox_role = discord.utils.get(interaction.guild.roles, id=1239657271143698564)
            if roblox_role in interaction.user.roles:
                await interaction.user.remove_roles(roblox_role, reason="User requested to remove Roblox role")
                await interaction.response.send_message("Roblox role removed!", ephemeral=True)
            else:
                await interaction.user.add_roles(roblox_role, reason="User requested to add Roblox role")
                await interaction.response.send_message("Roblox role added!", ephemeral=True)
        elif self.values[0] == "get_valorant_role":
            valorant_role = discord.utils.get(interaction.guild.roles, id=1249529840034512946)
            if valorant_role in interaction.user.roles:
                await interaction.user.remove_roles(valorant_role, reason="User requested to remove Valorant role")
                await interaction.response.send_message("Valorant role removed!", ephemeral=True)
            else:
                await interaction.user.add_roles(valorant_role, reason="User requested to add Valorant role")
                await interaction.response.send_message("Valorant role added!", ephemeral=True)