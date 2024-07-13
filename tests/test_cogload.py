import glob
import sys
import os

import discord
import discord.ext.test as dpytest
import pytest
from discord.ext import commands
from pathlib import Path

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))


def get_extensions():
    extensions = ["jishaku"]
    utils_path = Path(__file__).parent.parent / 'utils'

    for file in utils_path.glob("**/*.py"):
        # Skip files that contain certain symbols or keywords
        if any(dev_symbol in file.name for dev_symbol in ["!", "DEV"]):
            continue
        # Construct the module path
        module_path = file.relative_to(utils_path.parent).with_suffix('').as_posix().replace('/', '.')
        extensions.append(module_path)
    return extensions


@pytest.fixture
def bot(event_loop):
    bot = commands.Bot(
        command_prefix="/", event_loop=event_loop, intents=discord.Intents.all()
    )
    bot.remove_command("help")
    dpytest.configure(bot)
    return bot


@pytest.mark.asyncio
async def test_cogs(bot):
    for ext in get_extensions():
        await bot.load_extension(ext)
