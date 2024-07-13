"""
This module provides special methods for a Discord bot, including command analytics, bot readiness, command handling, 
and database initialization.

Functions:
    before_invoke_(ctx: commands.Context): Logs command usage and sets user context in Sentry.
    on_ready_(bot): Executes tasks when the bot is ready, including database checks and logging.
    on_command_(bot, ctx: commands.Context): Handles command usage, enforcing slash commands if necessary.
    main_mode_check_(ctx: commands.Context) -> bool: Checks various conditions to determine if a command can be executed.
    initialize_database(bot): Initializes the database and creates necessary table data if they don't exist.
"""

from __future__ import annotations

import collections
import os
import subprocess
from datetime import datetime

import discord
import sentry_sdk
from discord.ext import commands

from core import database
from core.common import (
    ConsoleColors,
)
from core.logging_module import get_log

_log = get_log(__name__)


async def before_invoke_(ctx: commands.Context):
    q = database.CommandAnalytics.create(
        command=ctx.command.name,
        user=ctx.author.id,
        date=datetime.now(),
        command_type="regular",
        guild_id=ctx.guild.id,
    ).save()

    sentry_sdk.set_user(None)
    sentry_sdk.set_user({"id": ctx.author.id, "username": ctx.author.name})
    sentry_sdk.set_tag("username", f"{ctx.author.name}#{ctx.author.discriminator}")
    if ctx.command is None:
        sentry_sdk.set_context(
            "user",
            {
                "name": ctx.author.name,
                "id": ctx.author.id,
                "command": ctx.command,
                "guild": ctx.guild.name,
                "guild_id": ctx.guild.id,
                "channel": ctx.channel.name,
                "channel_id": ctx.channel.id,
            },
        )
    else:
        sentry_sdk.set_context(
            "user",
            {
                "name": ctx.author.name,
                "id": ctx.author.id,
                "command": "Unknown",
                "guild": ctx.guild.name,
                "guild_id": ctx.guild.id,
                "channel": ctx.channel.name,
                "channel_id": ctx.channel.id,
            },
        )


async def on_ready_(bot):
    
    now = datetime.now()
    query: database.CheckInformation = (
        database.CheckInformation.select()
        .where(database.CheckInformation.id == 1)
        .get()
    )

    if not query.persistent_change:
        # bot.add_view(ViewClass(bot))

        query.persistent_change = True
        query.save()

    if not os.getenv("USEREAL"):
        IP = os.getenv("DATABASE_IP")
        database_field = f"{ConsoleColors.OKGREEN}Selected Database: External ({IP}){ConsoleColors.ENDC}"
    else:
        database_field = (
            f"{ConsoleColors.FAIL}Selected Database: localhost{ConsoleColors.ENDC}\n{ConsoleColors.WARNING}WARNING: Not "
            f"recommended to use SQLite.{ConsoleColors.ENDC} "
        )

    try:
        p = subprocess.run(
            "git describe --always",
            shell=True,
            text=True,
            capture_output=True,
            check=True,
        )
        output = p.stdout
    except subprocess.CalledProcessError:
        output = "ERROR"

    # chat_exporter.init_exporter(bot)

    print(
        f"""
            {bot.user.name} is ready!

            Bot Account: {bot.user.name} | {bot.user.id}
            {ConsoleColors.OKCYAN}Discord API Wrapper Version: {discord.__version__}{ConsoleColors.ENDC}
            {ConsoleColors.WARNING}StudyBot Version: {output}{ConsoleColors.ENDC}
            {database_field}

            {ConsoleColors.OKCYAN}Current Time: {now}{ConsoleColors.ENDC}
            {ConsoleColors.OKGREEN}Cogs, libraries, and views have successfully been initialized.{ConsoleColors.ENDC}
            ==================================================
            {ConsoleColors.WARNING}Statistics{ConsoleColors.ENDC}

            Guilds: {len(bot.guilds)}
            Members: {len(bot.users)}
            """
    )


"""async def on_command_error_(bot: BotObject, ctx: commands.Context, error: Exception):
    raise error"""




async def on_command_(bot, ctx: commands.Context):
    return
    # if you want to enforce slash commands only, uncomment the return statement above
    if ctx.command.name in ["sync", "ping", "kill", "jsk", "py"]:
        return

    await ctx.reply(
        f":x: This command usage is deprecated. Use the equivalent slash command by using `/{ctx.command.name}` instead."
    )


async def main_mode_check_(ctx: commands.Context) -> bool:
    CI_query: database.CheckInformation = database.CheckInformation.select().where(database.CheckInformation.id == 1).get()

    blacklisted_users = []
    db_blacklist: collections.Iterable = database.Blacklist
    for p in db_blacklist:
        blacklisted_users.append(p.discordID)

    admins = []
    query = database.Administrators.select().where(
        database.Administrators.TierLevel == 4
    )
    for admin in query:
        admins.append(admin.discordID)

    # Permit 4 Check
    if ctx.author.id in admins:
        return True

    # Maintenance Check
    elif CI_query.maintenance_mode:
        embed = discord.Embed(
            title="Master Maintenance ENABLED",
            description=f"❌ The bot is currently unavailable as it is under maintenance, check back later!",
            color=discord.Colour.gold(),
        )
        embed.set_footer(
            text="Message the bot owner for more information!"
        )
        await ctx.send(embed=embed)

        return False

    # Blacklist Check
    elif ctx.author.id in blacklisted_users:
        return False

    # DM Check
    elif ctx.guild is None:
        return CI_query.no_guild

    # Else...
    else:
        return CI_query.else_situation


def initialize_database(bot):
    """
    Initializes the database, and creates the needed table data if they don't exist.
    """
    database.db.connect(reuse_if_open=True)
    CIQ = database.CheckInformation.select().where(database.CheckInformation.id == 1)

    if not CIQ.exists():
        database.CheckInformation.create(
            maintenance_mode=False,
            no_guild=False,
            else_situation=True,
            persistent_change=False,
        )
        _log.info("Created CheckInformation Entry.")

    if len(database.Administrators) == 0:
        for person in bot.owner_ids:
            database.Administrators.create(discordID=person, TierLevel=4)
            _log.info("Created Administrator Entry.")

    query: database.CheckInformation = (
        database.CheckInformation.select()
        .where(database.CheckInformation.id == 1)
        .get()
    )
    query.persistent_change = False
    query.save()
    database.db.close()


