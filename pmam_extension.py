import discord, datetime, time, random
from discord.ext import commands
#922653836626243654
#1054029699187216485

pmam_roleid_robot: int = 830240292183212042

class Test(commands.Cog):

    def __init__(self, client):
        self.client = client

    @commands.Cog.listener()
    async def on_message(self, message):
        if "!vote" in message.content.lower() and message.channel.id in [1005658147861573642,1147624721156948068]:
            await message.add_reaction("<:vote_yes:975946668379889684>")
            time.sleep(0.3)
            await message.add_reaction("<:vote_abstain:975946602206363659>")
            time.sleep(0.3)
            await message.add_reaction("<:vote_no:975946731202183230>")
        if "https://steamcommunity.com/sharedfiles" in message.content and "steam://openurl/" not in message.content and message.channel.id in [922653836626243654,941813875538538627]:
            thread = await message.create_thread(name = f"{message.author.name}'s map")
            await thread.send(f"Here is a link that will directly open Steam: steam://openurl/{message.content[message.content.find('https://steamcommunity.com/sharedfiles'):message.content.find('https://steamcommunity.com/sharedfiles')+65]}")
    @commands.Cog.listener()
    @commands.bot_has_role(pmam_roleid_robot) #only works for PMaM
    async def on_raw_reaction_add(self, ctx):
        if ctx.emoji.name != "weebcringe_magnesium":
            return
        channel_starboard = self.client.get_channel(1192917950001315980)
        message = await self.client.get_channel(ctx.channel_id).fetch_message(ctx.message_id)
        for i in message.reactions:
            if i.is_custom_emoji() and i.emoji.id == 1081025872175308901 and i.count == 5 and message.author.id != 973750292074090506:
                with open("starboard.txt", "r+") as f:
                    content = f.read()
                    if str(message.id) not in content:
                        f.write(f"{str(message.id)}\n")
                        await channel_starboard.send(f"Message by @{message.author.name} from <#{message.channel.id}>:\n\n{message.content}{' '.join([j.url for j in message.attachments])}\n\nOriginal message: {message.jump_url}")

async def setup(client):
    await client.add_cog(Test(client))
