import discord
from discord.ext import commands
from core.database import StarboardMessage

class Starboard(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.starboard_channel_id = 123456789012345678  # Default starboard channel ID
        self.star_threshold = 5  # Default number of stars required to post to starboard

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload):
        if payload.emoji.name == '⭐':  # Check if the reaction is a star
            await self.handle_star_reaction(payload)

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload):
        if payload.emoji.name == '⭐':  # Check if the reaction is a star
            await self.handle_star_reaction(payload)

    async def handle_star_reaction(self, payload):
        channel = self.bot.get_channel(payload.channel_id)
        message = await channel.fetch_message(payload.message_id)
        star_count = sum(1 for reaction in message.reactions if reaction.emoji == '⭐')

        starboard_channel = self.bot.get_channel(self.starboard_channel_id)
        starboard_message = StarboardMessage.get_or_none(StarboardMessage.original_message_id == message.id)

        if star_count >= self.star_threshold:
            embed = discord.Embed(
                description=message.content,
                color=discord.Color.gold()
            )
            embed.set_author(name=message.author.display_name, icon_url=message.author.avatar.url)
            embed.add_field(name="Jump to message", value=f"[Click Here]({message.jump_url})")
            embed.set_footer(text=f"⭐ {star_count} | {message.channel.name}")

            if starboard_message:
                starboard_msg = await starboard_channel.fetch_message(starboard_message.starboard_message_id)
                await starboard_msg.edit(embed=embed)
                starboard_message.star_count = star_count
                starboard_message.save()
            else:
                starboard_msg = await starboard_channel.send(embed=embed)
                StarboardMessage.create(
                    original_message_id=message.id,
                    starboard_message_id=starboard_msg.id,
                    star_count=star_count
                )
        elif starboard_message:
            starboard_msg = await starboard_channel.fetch_message(starboard_message.starboard_message_id)
            await starboard_msg.delete_instance()

    @commands.group(name="starboard", invoke_without_command=True)
    async def starboard(self, ctx):
        await ctx.send("Available subcommands: setchannel, setthreshold")

    @starboard.command(name="setchannel")
    @commands.has_permissions(administrator=True)
    async def set_channel(self, ctx, channel: discord.TextChannel):
        """Set the starboard channel."""
        self.starboard_channel_id = channel.id
        await ctx.send(f"Starboard channel set to {channel.mention}")

    @starboard.command(name="setthreshold")
    @commands.has_permissions(administrator=True)
    async def set_threshold(self, ctx, threshold: int):
        """Set the star count threshold."""
        self.star_threshold = threshold
        await ctx.send(f"Star count threshold set to {threshold}")

async def setup(bot):
    await bot.add_cog(Starboard(bot))