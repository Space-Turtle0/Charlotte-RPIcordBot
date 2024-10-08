import datetime
import os
import random
import time


import discord
from discord.ui import Modal, TextInput, View, Button
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

from core import database

def generate_verification_code():
    return str(random.randint(100000, 999999))


class EmailVerificationModal(Modal):
    email = TextInput(label="RPI Email", placeholder="Enter your @rpi.edu email", required=True, max_length=50)
    class_year = TextInput(label="Class Year", placeholder="Enter your class year (e.g., 2025)", required=True, max_length=4)

    def __init__(self, bot, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bot = bot

    async def on_submit(self, interaction: discord.Interaction):
        if any(role.id in [1161340010822385694, 1161340010822385694] for role in interaction.user.roles):
            await interaction.response.send_message("You are already verified.", ephemeral=True)
            return

        rpi_email = self.email.value
        if not rpi_email.endswith('@rpi.edu'):
            await interaction.response.send_message("Please use a valid @rpi.edu email address.", ephemeral=True)
            return

        check = database.FinalizedEmailVerification.select().where(database.FinalizedEmailVerification.email == rpi_email)
        if check.exists():
            for record in check:
                print("e:" + str(record.discord_id) + ":" + str(interaction.user.id))
                if record.discord_id != interaction.user.id:
                    await interaction.response.send_message(
                        "This email has already been used for verification. Please use a different email.",
                        ephemeral=True)
                    return
        #return await interaction.response.send_message("Please wait while we send a verification email to your RPI email...", ephemeral=True)

        if not self.class_year.value.isdigit() or len(self.class_year.value) != 4 or int(self.class_year.value) < 2022 or int(self.class_year.value) > 2030:
            await interaction.response.send_message("Invalid class year. Please use the format 20XX.", ephemeral=True)
            return

        verification_code = generate_verification_code()
        check = database.EmailVerification.select().where(database.EmailVerification.discord_id == interaction.user.id)
        if check.count() > 0:
            for record in check:
                record.delete_instance()

        q = database.EmailVerification.create(discord_id=interaction.user.id, email=rpi_email, verification_code=verification_code, class_year=self.class_year.value)
        q.save()

        message = Mail(
            from_email='no-reply@charlotteverifies.site',
            to_emails=rpi_email,
            subject='Verification Email'
        )
        message.dynamic_template_data = {
            'twilio_code': str(verification_code),
            'discord_username': interaction.user.name,
            'discord_id': interaction.user.id,
            'timestamp': datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        message.template_id = "d-18c06f10e9164d0cb22a2c3d77cee2c6"

        try:
            sendgrid_client = SendGridAPIClient(os.getenv("SENDGRID"))
            response = sendgrid_client.send(message)
        except:
            await interaction.response.send_message("Looks like the SendGrid API is down. Please try again later. (Contact <@409152798609899530> if this keeps happening.)", ephemeral=True)
            return
        await interaction.response.send_message(
            f'Verification email sent to {rpi_email}. Please check your inbox *(and junk folder)* for the email.\n\n'
            'If you don\'t see it and it\'s been over 2 minutes, visit [Microsoft Quarantine](https://security.microsoft.com/quarantine) '
            'and sign in with your @rpi.edu account.\n\n'
            '> **Use /verification verify_code in <#1161341529516949626> to finalize verification!**',
            ephemeral=True
        )
    async def on_error(self, interaction: discord.Interaction, error: Exception) -> None:
        await interaction.response.send_message('Oops! Something went wrong. Contact the bot admin (<@409152798609899530>) if this keeps happening.', ephemeral=True)
        print(error)


class EmailVerificationButton(Button):
    cooldowns = {}
    def __init__(self, bot):
        super().__init__(custom_id="email_verification_button", label="Verify Email", emoji="✉️")
        self.bot = bot

    async def callback(self, interaction: discord.Interaction):
        current_time = time.time()
        user_id = interaction.user.id
        cooldown_duration = 180  # Cooldown duration in seconds

        # Check if the user is on cooldown
        if user_id in self.cooldowns:
            time_since_last_click = current_time - self.cooldowns[user_id]
            if time_since_last_click < cooldown_duration:
                remaining_time = cooldown_duration - time_since_last_click
                await interaction.response.send_message(f"Please wait {int(remaining_time)} seconds before clicking again.", ephemeral=True)
                return

        # Update the cooldown timestamp
        self.cooldowns[user_id] = current_time

        # Proceed with showing the modal
        modal = EmailVerificationModal(self.bot, title="Email Verification")
        await interaction.response.send_modal(modal)


class EmailVerificationView(View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.add_item(EmailVerificationButton(bot))