import asyncio
import datetime
import os
import time
from datetime import timedelta
from typing import TYPE_CHECKING

import discord
import openai
import psutil
from discord import app_commands, FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS

from core import database
from core.common import (
    Emoji,
    TicTacToe,
)
from core.logging_module import get_log

if TYPE_CHECKING:
    pass

_log = get_log(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")
load_dotenv()


class MiscCMD(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__cog_name__ = "General"
        self.bot: commands.Bot = bot
        self.client = openai.OpenAI(
            api_key=os.getenv("OPENAPI_KEY"),
        )
        self.interaction = []

    @property
    def display_emoji(self) -> str:
        return Emoji.schoolsimplified

    @app_commands.command(name="ping", description="Pong!")
    @app_commands.guilds(1216429016760717322, 1161339749487870062)
    async def ping(self, interaction: discord.Interaction):
        database.db.connect(reuse_if_open=True)

        current_time = float(time.time())
        difference = int(round(current_time - float(self.bot.start_time)))
        text = str(timedelta(seconds=difference))

        pingembed = discord.Embed(
            title="Pong! ⌛",
            color=discord.Colour.gold(),
            description="Current Discord API Latency",
        )
        pingembed.set_author(
            name=self.bot.user.display_name, url=self.bot.user.display_avatar.url, icon_url=self.bot.user.display_avatar.url
        )
        pingembed.add_field(
            name="Ping & Uptime:",
            value=f"```diff\n+ Ping: {round(self.bot.latency * 1000)}ms\n+ Uptime: {text}\n```",
        )

        pingembed.add_field(
            name="System Resource Usage",
            value=f"```diff\n- CPU Usage: {psutil.cpu_percent()}%\n- Memory Usage: {psutil.virtual_memory().percent}%\n```",
            inline=False,
        )
        pingembed.set_footer(
            text=f"{self.bot.user.display_name} Version: {self.bot.version}",
            icon_url=interaction.user.display_avatar.url,
        )

        await interaction.response.send_message(embed=pingembed)
        database.db.close()

    @app_commands.command(description="Play a game of TicTacToe with someone!")
    @app_commands.describe(user="The user you want to play with.")
    @app_commands.guilds(1216429016760717322, 1161339749487870062)
    async def tictactoe(self, interaction: discord.Interaction, user: discord.Member):
        if user is None:
            return await interaction.response.send_message(
                "lonely :(, sorry but you need a person to play against!"
            )
        elif user == self.bot.user:
            return await interaction.response.send_message("i'm good.")
        elif user == interaction.user:
            return await interaction.response.send_message(
                "lonely :(, sorry but you need an actual person to play against, not yourself!"
            )

        await interaction.response.send_message(
            f"Tic Tac Toe: {interaction.user.mention} goes first",
            view=TicTacToe(interaction.user, user),
        )

    @commands.command()
    async def sayvc(self, ctx: commands.Context, *, message):
        # Create the gTTS object
        tts = gTTS(text=message, lang='en')
        tts.save('output.mp3')

        # Check if the author is in a voice channel
        if ctx.author.voice is None:
            await ctx.send("You must be in a voice channel to use this command.")
            return

        # Join the author's voice channel
        voice_channel = ctx.author.voice.channel
        if ctx.voice_client is None:
            await voice_channel.connect()
        else:
            await ctx.voice_client.move_to(voice_channel)

        # Play the generated audio file
        voice_client = ctx.voice_client
        voice_client.stop()
        audio_source = FFmpegPCMAudio('output.mp3')
        if not voice_client.is_playing():
            voice_client.play(audio_source)

            # Wait for the audio to finish playing, then disconnect
            while voice_client.is_playing():
                await asyncio.sleep(1)

        # Remove the output file after playing
        os.remove('output.mp3')

    @app_commands.command(name="ask", description="Ask a question")
    @app_commands.guilds(1216429016760717322, 1161339749487870062)
    async def ask(self, interaction: discord.Interaction, *, question: str, be_nice: bool = False):
        if be_nice:
            content = f"You are Charlotte, you currently attend Rensselaer Polytechnic Institute as an architecture major. Answer as concisely as possible. Have a personality and feel free to be nice when needed. Current date: {datetime.now()}"
        else:
            content = f"You are Charlotte, you currently attend Rensselaer Polytechnic Institute as an architecture major. Answer as concisely as possible. Have a personality and feel free to be mean when needed. Current date: {datetime.now()}"
        response = self.client.chat.completions.create(
            model="gpt-3.5-turbo-0125",
            messages=[
                {"role": "system",
                "content": content},
                {"role": "user", "content": question}
            ]
        )
        await interaction.response.send_message(response.choices[0].message.content)

    @app_commands.command(name="impersonate", description="do something weird but not by you")
    @app_commands.guilds(1216429016760717322)
    async def impersonate(self, interaction: discord.Interaction, person: discord.Member, message: str):
        q = database.Administrators.select().where(database.Administrators.discordID == interaction.user.id)
        if q.exists():
            webhook = await interaction.channel.create_webhook(name=person.display_name)
            avatar_url = person.display_avatar.url
            msg = await webhook.send(content=message, username=person.display_name, avatar_url=avatar_url)
            await webhook.delete()
            await interaction.response.send_message("done!", ephemeral=True)
        else:
            await interaction.response.send_message("who even are you lil bro")

    @app_commands.command(name="say", description="do something weird but not by you but by bot")
    @app_commands.guilds(1216429016760717322, 1161339749487870062)
    async def say(self, interaction: discord.Interaction, message: str):
        if interaction.user.id != 409152798609899530:
            return await interaction.response.send_message("who even are you lil bro")
        await interaction.response.send_message("Sent!", ephemeral=True)
        await interaction.channel.send(message)

    @commands.command()
    async def connect(self, ctx, vc_id):
        """
        A very lazy implementation of allowing users to make the bot join a VC.
        Used as a pre-req for sayvc. 
        """
        try:
            ch = await self.bot.fetch_channel(vc_id)
            await ch.connect()
        except:
            await ctx.send("not a channel buddy")
        else:
            await ctx.send("connected")



async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCMD(bot))
