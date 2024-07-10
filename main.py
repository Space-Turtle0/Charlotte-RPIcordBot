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
from datetime import datetime
from urllib.parse import urlencode, quote

import aiohttp
import aiohttp.payload as payload
import discord
from alive_progress import alive_bar
from discord import app_commands
from discord.ext import commands
from discord_sentry_reporting import use_sentry
from dotenv import load_dotenv
from gtts import gTTS
from openai import OpenAI
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
    # on_command_error_,
    on_ready_,
    on_command_,
)

load_dotenv()
faulthandler.enable()

logger = logging.getLogger("discord")
logger.setLevel(logging.INFO)

_log = get_log(__name__)
_log.info("Starting up...")
#discord.opus.load_opus('libopus.0.dylib')

default_data = {
    "fsize": "25px",
    "fcolor": "cccccc",
    "mode": 0,
    "out": 1,
    "errors": 1,
    "preamble": r"\usepackage{amsmath}\usepackage{amsfonts}\usepackage{amssymb}"
}


class CustomFormData(aiohttp.FormData):
    def _gen_form_urlencoded(self) -> payload.BytesPayload:
        # form data (x-www-form-urlencoded)
        data = []
        for type_options, _, value in self._fields:
            data.append((type_options['name'], value))

        charset = self._charset if self._charset is not None else 'utf-8'

        if charset == 'utf-8':
            content_type = 'application/x-www-form-urlencoded'
        else:
            content_type = ('application/x-www-form-urlencoded; '
                            'charset=%s' % charset)

        return payload.BytesPayload(
            urlencode(data, doseq=False, encoding=charset,
                      quote_via=quote).encode(),
            content_type=content_type)


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

    """async def on_error(
        self, interaction: discord.Interaction, error: app_commands.AppCommandError
    ):
        # await on_app_command_error_(self.bot, interaction, error)
        pass"""


class Charlotte(commands.Bot):
    """
    Generates a StudyBot Instance.
    """

    def __init__(self, uptime: time.time):
        super().__init__(
            command_prefix=commands.when_mentioned_or(os.getenv("PREFIX")),
            intents=discord.Intents.all(),
            case_insensitive=True,
            tree_cls=CharlotteCommandTree,
            activity=discord.Activity(
                type=discord.ActivityType.watching, name="/help | url"
            ),
        )
        self.help_command = None
        self.before_invoke(self.analytics_before_invoke)
        self.add_check(self.check)
        self._start_time = uptime

    async def on_ready(self):
        await on_ready_(self)

    """async def on_command_error(self, ctx: commands.Context, error: Exception):
        await on_command_error_(self, ctx, error)"""

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
        # await bot.tree.set_translator(TimmyTranslator())

    async def on_message(self, message: discord.Message):
        if "<@191666744064999425>" in message.content and message.author != bot.user:
            gif_link = "https://tenor.com/view/are-you-serious-clark-clark-christmas-vacation-dinner-family-gif-5426034"
            await message.channel.send(gif_link)

        await self.process_commands(message)

    async def is_owner(self, user: discord.User):
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

client = OpenAI(
    # This is the default and can be omitted
    api_key=os.getenv("OPENAPI_KEY"),
)


@bot.tree.command(name="ask", description="Ask a question", guild=discord.Object(id=1216429016760717322))
async def ask(interaction: discord.Interaction, *, question: str, be_nice: bool = False):
    """if interaction.channel_id != 1216431006031282286:
        return await interaction.response.send_message("lil bro, you can't use this command here. take your ass to <#1216431006031282286>")"""
    if be_nice:
        content = f"You are Charlotte, you currently attend Rensselaer Polytechnic Institute as an architecture major. Answer as concisely as possible. Have a personality and feel free to be nice when needed. Current date: {datetime.now()}"
    else:
        content = f"You are Charlotte, you currently attend Rensselaer Polytechnic Institute as an architecture major. Answer as concisely as possible. Have a personality and feel free to be mean when needed. Current date: {datetime.now()}"
    response = client.chat.completions.create(
        model="gpt-3.5-turbo-0125",
        messages=[
            {"role": "system",
             "content": content},
            {"role": "user", "content": question}
        ]
    )
    await interaction.response.send_message(response.choices[0].message.content)

@bot.tree.command(name="impersonate", description="do something weird but not by you", guild=discord.Object(id=1216429016760717322))
async def impersonate(interaction: discord.Interaction, person: discord.Member, message: str):
    q = database.Administrators.select().where(database.Administrators.discordID == interaction.user.id)
    if q.exists():
        webhook = await interaction.channel.create_webhook(name=person.display_name)
        avatar_url = person.display_avatar.url
        msg = await webhook.send(content=message, username=person.display_name, avatar_url=avatar_url)
        await webhook.delete()
        await interaction.response.send_message("done!", ephemeral=True)
    else:
        await interaction.response.send_message("who even are you lil bro")

@bot.tree.command(name="say", description="do something weird but not by you but by bot", guild=discord.Object(id=1216429016760717322))
async def say(interaction: discord.Interaction, message: str):
    if interaction.user.id != 409152798609899530:
        return await interaction.response.send_message("who even are you lil bro")
    await interaction.response.send_message("Sent!", ephemeral=True)
    await interaction.channel.send(message)


if os.getenv("DSN_SENTRY") is not None:
    sentry_logging = LoggingIntegration(
        level=logging.INFO,  # Capture info and above as breadcrumbs
        event_level=logging.ERROR,  # Send errors as events
    )

    # Traceback tracking, DO NOT MODIFY THIS
    use_sentry(
        bot,
        dsn=os.getenv("DSN_SENTRY"),
        traces_sample_rate=1.0,
        integrations=[FlaskIntegration(), sentry_logging],
    )


@bot.command()
async def sayvc(ctx: commands.Context, *, text=None):
    query = database.Administrators.select().where(database.Administrators.discordID == ctx.author.id)
    if query.exists():
        await ctx.message.delete()

        if not text:
            await ctx.send(f"Hey {ctx.author.mention}, I need to know what to say please.")
            return

        vc = ctx.voice_client
        if not vc:
            await ctx.send("I need to be in a voice channel to do this, please use the connect command.")
            return

        tts = gTTS(text=text, lang="en")
        tts.save("text.mp3")

        try:
            vc.play(discord.FFmpegOpusAudio('text.mp3'), after=lambda e: print(f"Finished playing: {e}"))
            vc.source = discord.PCMVolumeTransformer(vc.source)
            vc.source.volume = 1

        except Exception as e:
            print(e)
    else:
        await ctx.send("suck my huge throbbing cock lil bro")

@bot.command()
async def connect(ctx, vc_id):
    try:
        ch = await bot.fetch_channel(vc_id)
        await ch.connect()
    except:
        await ctx.send("not a channel noob")
    else:
        await ctx.send("connected")

initialize_database(bot)

if __name__ == "__main__":
    bot.run(os.getenv("TOKEN"))
