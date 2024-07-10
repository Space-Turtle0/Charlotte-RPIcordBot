import asyncio
import datetime
import os
import time
from datetime import timedelta
from typing import List, TYPE_CHECKING

import discord
import openai
import psutil
from discord import app_commands, ui, FFmpegPCMAudio
from discord.ext import commands
from dotenv import load_dotenv
from gtts import gTTS

from core import database
from core.common import (
    Emoji,
    Colors,
    ButtonHandler,
)
from core.logging_module import get_log

if TYPE_CHECKING:
    from main import JPBot

_log = get_log(__name__)

openai.api_key = os.getenv("OPENAI_API_KEY")


def get_chat_response(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "system", "content": f"You are charlotte, you currently attend Rensselaer Polytechnic Institute "
                                          f"as a architecture major. you're also oiled up. Answer as"
                                          f"concisely as possible. Current date: {datetime.datetime.now()}"},
            {"role": "user", "content": message}
        ],
        temperature=0,
        max_tokens=258,
        top_p=1.0,
        frequency_penalty=0.0,
        presence_penalty=0.0,
    )
    return response


class ChatGPTForm(ui.Modal, title="Ask Dabid!"):
    def __init__(self, bot: "JPBot") -> None:
        super().__init__(timeout=None)
        self.bot = bot

    question = ui.TextInput(
        label="How can I help you today?",
        placeholder="just a reminder: you're smart!",
        max_length=2000,
        required=True,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(thinking=True, ephemeral=False)
        chat_response = get_chat_response(self.question.value)

        # Send the ChatGPT response to the channel
        text = chat_response['choices'][0]['message']['content']

        if text is None or text == "":
            text = "I'm sorry, I don't understand. Please try again."
        msg = await interaction.followup.send(text)
        log_channel = await self.bot.fetch_channel(1075927416654004315)
        embed = discord.Embed(
            title = f"New Query from {interaction.user.display_name}",
            description=f"Completed Transaction",
            color=discord.Color.gold()
        )
        embed.add_field(name="Query", value=self.question.value)
        embed.add_field(name="Response", value=msg.jump_url, inline=False)
        embed.set_footer(text=f"User ID: {interaction.user.id}")
        await log_channel.send(embed=embed)



class DMForm(ui.Modal, title="Mass DM Announcement"):
    def __init__(self, bot: "JPBot", target_role: discord.Role) -> None:
        super().__init__(timeout=None)
        self.bot = bot
        self.role: discord.Role = target_role

    message_content = ui.TextInput(
        label="Paste Message to Send Here",
        placeholder="Markdown is supported!",
        max_length=2000,
        required=True,
        style=discord.TextStyle.long,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Send the message to everyone in the guild with that role.
        mass_dm_message = (
            self.message_content.value
            + "\n\n"
            + f"Sent by: {interaction.user.mention} | Report abuse "
            f"to any bot developer. "
        )
        await interaction.response.send_message("Starting DM Announcement...")
        await interaction.channel.send(
            f"**This is a preview of what you are about to send.**\n\n{mass_dm_message}"
        )
        await asyncio.sleep(3)
        # Send a confirm button to the user.
        view = ui.View(timeout=30)
        button_confirm = ButtonHandler(
            style=discord.ButtonStyle.green,
            label="Confirm",
            emoji="✅",
            button_user=interaction.user,
        )
        button_cancel = ButtonHandler(
            style=discord.ButtonStyle.red,
            label="Cancel",
            emoji="❌",
            button_user=interaction.user,
        )
        view.add_item(button_confirm)
        view.add_item(button_cancel)

        embed_confirm = discord.Embed(
            color=Colors.yellow,
            title="Mass DM Confirmation",
            description=f"Are you sure you want to send this message to all members with the role, `{self.role.name}`?",
        )
        message_confirm = await interaction.followup.send(
            embed=embed_confirm, view=view
        )
        timeout = await view.wait()
        if not timeout:
            if view.value == "Confirm":
                embed_confirm = discord.Embed(
                    color=Colors.yellow,
                    title="Mass DM Queued",
                    description=f"Starting Mass DM...\n**Role:** `{self.role.name}`",
                )
                await message_confirm.edit(embed=embed_confirm, view=None)
                for member in self.role.members:
                    await asyncio.sleep(0.2)
                    try:
                        await member.send(mass_dm_message)
                    except:
                        await interaction.channel.send(
                            f"{member.mention} is not accepting DMs from me."
                        )

                embed_confirm = discord.Embed(
                    color=Colors.green,
                    title="Mass DM Complete",
                    description=f"I've sent everyone with the role, `{self.role.name}`, your message and listed anyone who didn't accept DMs from me.",
                )
                await message_confirm.edit(embed=embed_confirm, view=None)
            else:
                embed_confirm = discord.Embed(
                    color=Colors.red,
                    title="Mass DM Canceled",
                    description=f"Canceled sending message to all members with the role, `{self.role.name}`.",
                )
                await message_confirm.edit(embed=embed_confirm, view=None)
        else:
            embed_confirm = discord.Embed(
                color=Colors.red,
                title="Mass DM Canceled",
                description=f"Canceled sending message to all members with the role, `{self.role.name}`.",
            )
            await message_confirm.edit(embed=embed_confirm, view=None)


class TicTacToeButton(discord.ui.Button["TicTacToe"]):
    def __init__(self, x: int, y: int, xUser: discord.User, yUser: discord.User):
        super().__init__(style=discord.ButtonStyle.secondary, label="\u200b", row=y)
        self.x = x
        self.xUser = xUser

        self.y = y
        self.yUser = yUser

    async def callback(self, interaction: discord.Interaction):
        assert self.view is not None
        view: TicTacToe = self.view
        state = view.board[self.y][self.x]
        if state in (view.X, view.O):
            return
        if view.current_player == view.X and self.xUser.id == interaction.user.id:
            self.style = discord.ButtonStyle.danger
            self.label = "X"
            self.disabled = True
            view.board[self.y][self.x] = view.X
            view.current_player = view.O
            content = f"It is now {self.yUser.mention}'s turn"

        elif view.current_player == view.O and self.yUser.id == interaction.user.id:
            self.style = discord.ButtonStyle.success
            self.label = "O"
            self.disabled = True
            view.board[self.y][self.x] = view.O
            view.current_player = view.X
            content = f"It is now {self.xUser.mention}'s turn"

        elif not interaction.user.id == view.current_player and interaction.user in [
            self.yUser,
            self.xUser,
        ]:
            return await interaction.response.send_message(
                f"{interaction.user.mention} It's not your turn!", ephemeral=True
            )
        else:
            return await interaction.response.send_message(
                f"{interaction.user.mention} Woah! You can't join this game "
                f"as you weren't invited, if you'd like to play you can start "
                f"a session by doing `+ttc @UserYouWannaPlayAgainst`!",
                ephemeral=True,
            )

        winner = view.check_board_winner()
        if winner is not None:
            if winner == view.X:
                content = f"{self.xUser.mention} won!"
            elif winner == view.O:
                content = f"{self.yUser.mention} won!"
            else:
                content = "It's a tie!"

            for child in view.children:
                child.disabled = True

            view.stop()

        await interaction.response.edit_message(content=content, view=view)


# This is our actual board View
class TicTacToe(discord.ui.View):
    # This tells the IDE or linter that all our children will be TicTacToeButtons
    # This is not required
    children: List[TicTacToeButton]
    X = -1
    O = 1
    Tie = 2

    def __init__(self, XPlayer, OPlayer):
        super().__init__()
        self.current_player = self.X
        self.board = [
            [0, 0, 0],
            [0, 0, 0],
            [0, 0, 0],
        ]
        self.XPlayer = XPlayer
        self.OPlayer = OPlayer

        # Our board is made up of 3 by 3 TicTacToeButtons
        # The TicTacToeButton maintains the callbacks and helps steer
        # the actual game.
        for x in range(3):
            for y in range(3):
                self.add_item(TicTacToeButton(x, y, XPlayer, OPlayer))

    # This method checks for the board winner -- it is used by the TicTacToeButton
    def check_board_winner(self):
        for across in self.board:
            value = sum(across)
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check vertical
        for line in range(3):
            value = self.board[0][line] + self.board[1][line] + self.board[2][line]
            if value == 3:
                return self.O
            elif value == -3:
                return self.X

        # Check diagonals
        diag = self.board[0][2] + self.board[1][1] + self.board[2][0]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        diag = self.board[0][0] + self.board[1][1] + self.board[2][2]
        if diag == 3:
            return self.O
        elif diag == -3:
            return self.X

        # If we're here, we need to check if a tie was made
        if all(i != 0 for row in self.board for i in row):
            return self.Tie

        return None


load_dotenv()


class MiscCMD(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.__cog_name__ = "General"
        self.bot: commands.Bot = bot
        self.interaction = []

    @property
    def display_emoji(self) -> str:
        return Emoji.schoolsimplified

    @app_commands.command(name="ping", description="Pong!")
    @app_commands.guilds(1216429016760717322)
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
    @app_commands.guilds(1216429016760717322)
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

    @commands.command(description="Ask Dabid something!")
    async def sayvclol(self, ctx: commands.Context, *, message):
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



async def setup(bot: commands.Bot):
    await bot.add_cog(MiscCMD(bot))
