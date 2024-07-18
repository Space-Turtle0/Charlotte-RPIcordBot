"""
Copyright (C) TriageSpace - All Rights Reserved
 * Permission is granted to use this application as a boilerplate.
 * Written by Rohit. December 2022
"""

__author__ = "TriageSpace/Rohit"
__project__ = "Charlotte/RPIcordBot"

import faulthandler
import logging
import os
import time

import discord
from alive_progress import alive_bar
from discord import app_commands
from discord.ext import commands
from discord_sentry_reporting import use_sentry
from dotenv import load_dotenv
from pygit2 import Repository, GIT_DESCRIBE_TAGS
from sentry_sdk.integrations.flask import FlaskIntegration
from sentry_sdk.integrations.logging import LoggingIntegration

from core import database
from core.common import get_extensions
from core.logging_module import get_log
from core.rolecolors import CustomizeView
from core.rpi.email_verification import EmailVerificationView
from core.rpi.reaction_roles import DormRoleView, ClassYearRoleView
from core.special_methods import (
    before_invoke_,
    initialize_database,
    main_mode_check_,
    on_ready_,
    on_command_,
)

load_dotenv()
faulthandler.enable()

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

_log = get_log(__name__)
_log.info("Starting up...")

class CharlotteCommandTree(app_commands.CommandTree):
    def __init__(self, bot):
        super().__init__(bot)
        self.bot = bot

    async def interaction_check(self, interaction: discord.Interaction, /) -> bool:
        blacklisted_users = [p.discordID for p in database.Blacklist]
        if interaction.user.id in blacklisted_users:
            await interaction.response.send_message(
                "You have been blacklisted from using commands!", ephemeral=True
            )
            return False
        return True


class Charlotte(commands.Bot):
    """
    Generates a Charlotte Instance.
    """

    def __init__(self, uptime: time.time):
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
            intents=discord.Intents.all(),
            case_insensitive=True,
            tree_cls=CharlotteCommandTree,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="over QuACS"
            ),
        )
        self.help_command = None
        self.before_invoke(self.analytics_before_invoke)
        self.add_check(self.check)
        self._start_time = uptime

    async def on_ready(self):
        await on_ready_(self)

    async def on_command(self, ctx: commands.Context):
        await on_command_(self, ctx)

    async def analytics_before_invoke(self, ctx: commands.Context):
        await before_invoke_(ctx)

    async def check(self, ctx: commands.Context):
        return await main_mode_check_(ctx)

    async def setup_hook(self) -> None:
        bot.add_view(CustomizeView())
        bot.add_view(DormRoleView())
        bot.add_view(ClassYearRoleView())
        bot.add_view(EmailVerificationView(bot))

        with alive_bar(
            len(get_extensions()),
            ctrl_c=False,
            bar="bubbles",
            title="Initializing Cogs:",
        ) as bar:

            for ext in get_extensions():
                try:
                    await bot.load_extension(ext)
                except commands.ExtensionAlreadyLoaded:
                    await bot.unload_extension(ext)
                    await bot.load_extension(ext)
                except commands.ExtensionNotFound:
                    raise commands.ExtensionNotFound(ext)
                bar()

    async def on_message(self, message: discord.Message):
        """
        Process the message for the bot.
        -> For now this only modifies behavior in the r(evolution)pi server.

        :param message: discord.Message: The message to process.
        """
        if "<@191666744064999425>" in message.content and message.author != bot.user:
            gif_link = "https://tenor.com/view/are-you-serious-clark-clark-christmas-vacation-dinner-family-gif-5426034"
            await message.channel.send(gif_link)

        await self.process_commands(message)

    async def on_member_join(self, member: discord.Member):
        if member.guild.id == 1216429016760717322 and not member.bot:
            welcome_channel = await self.bot.fetch_channel(1216429018744885321)

            await welcome_channel.send(f"hi loser, {member.mention}. im just here to tell you that if you want a custom role, go to <#1219037652414894310>. bye. also keira sucks lol")

    async def is_owner(self, user: discord.User):
        """
        Checks if the user is the owner of the bot.
        NOTE: This is a custom implementation to check if the user is an owner.
        The user must be assigned a TierLevel of **3** or higher in the database
        to be qualified as a "Owner".

        :param user: discord.User: The user to check.
        :return: bool: True if the user is the owner, False otherwise.
        """
        admin_ids = []
        query = database.Administrators.select().where(
            database.Administrators.TierLevel >= 3
        )
        for admin in query:
            admin_ids.append(admin.discordID)

        if user.id in admin_ids:
            return True

        return await super().is_owner(user)

    @property
    def version(self):
        """
        Returns the current version of the bot.
        """
        repo = Repository(".")
        current_commit = repo.head
        current_branch = repo.head.shorthand

        version = ...  # type: str
        if current_branch == "HEAD":
            current_tag = repo.describe(committish=current_commit, describe_strategy=GIT_DESCRIBE_TAGS)
            version = f"{current_tag} (stable)"
        else:
            version = "development"
        version += f" | {str(current_commit.target)[:7]}"

        return version

    @property
    def author(self):
        """
        Returns the author of the bot.
        """
        return __author__

    @property
    def start_time(self):
        """
        Returns the time the bot was started.
        """
        return self._start_time


bot = Charlotte(time.time())
initialize_database(bot)

if os.getenv("DSN_SENTRY") is not None:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    use_sentry(
        bot,  # Traceback tracking, DO NOT MODIFY THIS
        dsn=os.getenv("DSN_SENTRY"),
        traces_sample_rate=1.0,
        integrations=[FlaskIntegration(), sentry_logging],
    )

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))