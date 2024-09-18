import asyncio
from discord.ext import commands

pmam_roleid_robot: int = 830240292183212042
vote_channels = [1005658147861573642,1147624721156948068]
showcasing_channels = [922653836626243654,941813875538538627]
starboard_channel_id: int = 1192917950001315980
emoji_id: int = 1081025872175308901 #emoji ID used for starboard
emoji_name = "weebcringe_magnesium" 
bot_id: int = 973750292074090506 #bot ID, very important to prevent situation where starboard posts are being starboarded

class Extension(commands.Cog):

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_message(self, message):
        if "!vote" in message.content.lower() and message.channel.id in vote_channels:
            await message.add_reaction("<:vote_yes:975946668379889684>")
            asyncio.sleep(0.3)
            await message.add_reaction("<:vote_abstain:975946602206363659>")
            asyncio.sleep(0.3)
            await message.add_reaction("<:vote_no:975946731202183230>")
        if "https://steamcommunity.com/sharedfiles" in message.content and "steam://openurl/" not in message.content and message.channel.id in showcasing_channels:
            thread = await message.create_thread(name = f"{message.author.name}'s map")
            await thread.send(f"Here is a link that will directly open Steam: https://tpecool.github.io/steamitem/{message.content[message.content.find('https://steamcommunity.com/sharedfiles'):message.content.find('https://steamcommunity.com/sharedfiles')+65]}")
    @commands.Cog.listener()
    @commands.bot_has_role(pmam_roleid_robot) #only works for PMaM
    async def on_raw_reaction_add(self, ctx):
        if ctx.emoji.name != emoji_name:
            return
        channel_starboard = self.bot.get_channel(starboard_channel_id)
        message = await self.bot.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
        for i in message.reactions:
            if i.is_custom_emoji() and i.emoji.id == emoji_id and i.count == 5 and message.author.id != bot_id:
                with open("starboard.txt", "r+") as f:
                    content = f.read()
                    if str(message.id) not in content:
                        f.write(f"{str(message.id)}\n")
                        await channel_starboard.send(f"Message by @{message.author.name} from <#{message.channel.id}>:\n\n```{message.content}```{' '.join([j.url for j in message.attachments])}\n\nOriginal message: {message.jump_url}")

async def setup(bot):
    await bot.add_cog(Extension(bot))
