import time

import discord
import asyncio
import io
import chat_exporter
from chat_exporter import AttachmentToDiscordChannelHandler
from core import database
from core.logging_module import get_log


class TicketManageView(discord.ui.View):
    def __init__(self, bot, disable=False):
        super().__init__(timeout=None)
        self.bot = bot
        if disable:
            self.add_item(DisabledCloseButton(self.bot))
        else:
            self.add_item(CloseButton(self.bot))


class DisabledCloseButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Close Ticket [IN PROGRESS]", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_close", disabled=True)


class CloseButton(discord.ui.Button):
    def __init__(self, bot):
        super().__init__(label="Close Ticket", style=discord.ButtonStyle.red, emoji="🔒", custom_id="ticket_close")
        self.bot = bot
        self.channel_handler = AttachmentToDiscordChannelHandler(
            channel=bot.get_channel(1273432365967998978),
        )
        self.log_channel = 1273436780875485214

    async def callback(self, interaction: discord.Interaction):
        # get the 1st pinned message
        await interaction.response.defer(thinking=True)

        pinned_messages = await interaction.channel.pins()
        control_panel = pinned_messages[0]
        await control_panel.edit(view=TicketManageView(self.bot, disable=True))


        channel = interaction.channel
        ticket: database.TicketInfo = database.TicketInfo.select().where(
            database.TicketInfo.channel_id == channel.id).get()

        ticket.delete_instance()

        transcript = await chat_exporter.export(interaction.channel)

        if transcript is None:
            return

        transcript_file = discord.File(
            io.BytesIO(transcript.encode()),
            filename=f"transcript-{interaction.channel.name}.html",
        )

        log_embed = discord.Embed(
            title="Ticket Closed",
            description=f"Ticket closed by {interaction.user.mention}",
            color=discord.Color.red()
        )
        log_embed.add_field(name="Ticket Info:", value=f"{channel.name} created by <@{ticket.author_id}>.")
        log_embed.set_footer(text="Transcript attached below.")
        log_channel = self.bot.get_channel(self.log_channel)
        message: discord.Message = await log_channel.send(embed=log_embed, file=transcript_file)
        link = await chat_exporter.link(message)
        await message.reply(f"Transcript: [Link]({link})")

        await interaction.followup.send("Ticket closed. Deleting...", ephemeral=True)
        await asyncio.sleep(4)
        await channel.delete()


class TicketCreateButton(discord.ui.Button):
    cooldowns = {}

    def __init__(self, bot):
        super().__init__(label="Open Ticket", style=discord.ButtonStyle.blurple, emoji="📝", custom_id="ticket_create")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_time = time.time()
        user_id = interaction.user.id
        cooldown_duration = 180

        # Check if the user is on cooldown
        if user_id in self.cooldowns:
            time_since_last_click = current_time - self.cooldowns[user_id]
            if time_since_last_click < cooldown_duration:
                remaining_time = cooldown_duration - time_since_last_click
                await interaction.response.send_message(
                    f"Please wait {int(remaining_time)} seconds before clicking again.", ephemeral=True)
                return

        # Update the cooldown timestamp
        self.cooldowns[user_id] = current_time

        base_info: database.BaseTickerInfo = database.BaseTickerInfo.select().where(database.BaseTickerInfo.id == 1)
        if not base_info.exists():
            base_info = database.BaseTickerInfo.create(counter=1)
        else:
            base_info = base_info.get()

        guild = interaction.guild
        author = interaction.user
        ticket_number = base_info.counter
        base_info.counter += 1
        base_info.save()

        # Create a new text channel for the ticket
        channel_name = f"ticket-{author.name}-{ticket_number}"
        category = discord.utils.get(guild.categories, id=1273436481335201813)

        ticket_channel = await guild.create_text_channel(channel_name, category=category)
        admin_role = discord.utils.get(guild.roles, id=1161339892618494153)

        # Set permissions for the ticket channel
        await ticket_channel.set_permissions(guild.default_role, read_messages=False)
        await ticket_channel.set_permissions(author, read_messages=True, send_messages=True)
        await ticket_channel.set_permissions(admin_role, read_messages=True, send_messages=True)

        # Send and pin the control panel in the ticket channel
        embed = discord.Embed(
            title="Ticket Control Panel",
            description="Use the buttons below to manage your ticket.",
            color=discord.Color.green()
        )
        control_message = await ticket_channel.send(embed=embed, view=TicketManageView(self.bot))
        await control_message.pin()

        # Notify the user
        await interaction.response.send_message(f"Ticket created: {ticket_channel.mention}", ephemeral=True)
        await ticket_channel.send(
            f"Hello {author.mention}!\nPlease describe your issue here and we'll be with you shortly.")

        # Update the database
        ticket: database.TicketInfo = database.TicketInfo.create(
            channel_id=ticket_channel.id,
            author_id=author.id
        )
        ticket.save()

    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        _log = get_log(__name__)

        await interaction.response.send_message("Oops! something went wrong. looks like ur fucked lol. don't open more tickets cause i broke something", ephemeral=True)
        _log.error(error)


class TicketButton(discord.ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.add_item(TicketCreateButton(self.bot))
