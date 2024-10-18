import os, datetime, typing
import discord
from discord.ext import commands

if os.getenv('TEST') == "1":
    pmam_channelid_starboard: int = 1296927868156116992
    pmam_vote_channelids: typing.List[int] = [1287488941255299325]
    pmam_showcasing_channelids: typing.List[int] = [1296972883708346460]
    pmam_emoji_yes: str = "<:vote_yes:1296964724319195188>"
    pmam_emoji_abstain: str = "<:vote_abstain:1296964800982548511>"
    pmam_emoji_no: str = "<:vote_no:1296964759916122207>"
else:
    pmam_channelid_starboard: int = 1192917950001315980
    pmam_vote_channelids: typing.List[int] = [1005658147861573642, 1147624721156948068] # #moderator-discussion and #basement-area
    pmam_showcasing_channelids: typing.List[int] = [922653836626243654, 941813875538538627] #📢┃finished-map-links and #🎮┃playtesting
    pmam_emoji_yes: str = "<:vote_yes:975946668379889684>"
    pmam_emoji_abstain: str = "<:vote_abstain:975946602206363659>"
    pmam_emoji_no: str = "<:vote_no:975946731202183230>"

starboard_emoji_id: int = 1081025872175308901 #emoji ID used for starboard
link_prefixs: typing.List[str] = ["https://steamcommunity.com/sharedfiles/filedetails/", "https://steamcommunity.com/workshop/filedetails/"]

class Extension(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        if (("!vote" in message.content.lower()) and (message.channel.id in pmam_vote_channelids)):
            await message.add_reaction(pmam_emoji_yes)
            await message.add_reaction(pmam_emoji_abstain)
            await message.add_reaction(pmam_emoji_no)
        
        if (("https://steamcommunity.com" in message.content) and ("steam://openurl/" not in message.content) and (message.channel.id in pmam_showcasing_channelids)):
            link_prefix = next((link_prefix for link_prefix in link_prefixs if link_prefix in  message.content), None)
            thread = await message.create_thread(name = f"{message.author.display_name}'s Map")
            await thread.send(
                f"Here is a link that will directly open Steam: https://electrovoyage.github.io/steamitem{message.content.removeprefix(link_prefix)}"
            )
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, ctx: commands.Context):
        if ctx.emoji.id != starboard_emoji_id:
            return
        
        channel_starboard: discord.TextChannel = self.bot.get_channel(pmam_channelid_starboard)
        message: discord.Message = await self.bot.get_channel(ctx.channel_id).fetch_message(ctx.message_id)

        for reaction in message.reactions:
            if ((not reaction.is_custom_emoji()) or (reaction.emoji.id != starboard_emoji_id)): continue

            # Potentially come back to using history to search if a starboard message has already been boarded instead of using a txt file
            # async for oldmessage in channel_starboard.history(limit=10, around=message.created_at):
            #     print(oldmessage.id)
            #     if oldmessage.id == message.id:
            #         return
            
            if ((reaction.count >= 5) and (message.author.id != self.bot.user.id)):
                with open("starboard.txt", "r+") as f:
                    content = f.read()
                    if str(message.id) in content: return
                    f.write(f"{str(message.id)}\n")
                starboard_embed = discord.Embed(
                    color = discord.Color.yellow(),
                    description = f"Message by <@!{message.author.id}> from <#{message.channel.id}>:\n\n" \
                                  f'{f"```{message.content}```" if message.content != "" else ""}\n\n' \
                                  f"Original message: {message.jump_url}",
                    timestamp = datetime.datetime.now(tz=datetime.timezone.utc)
                )
                starboard_embed.set_author(name=f"{message.author.display_name}", icon_url=message.author.display_avatar.url)
                starboard_embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")
                await channel_starboard.send(embed=starboard_embed)
                if message.attachments != []:
                    await channel_starboard.send(content=f"\n{' '.join([attachment.url for attachment in message.attachments])}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Extension(bot))
