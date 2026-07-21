import os
import discord
import datetime, typing, re

from logger import log
from discord.ext import commands

if os.getenv('TEST') == '1':
    pmam_channelid_starboard: int = 1296927868156116992
    pmam_vote_channelids: int = 1287488941255299325
    pmam_showcasing_channelids: int = [1296972883708346460]
    pmam_finishedmaps_channelid: int = 1528464163859333231
    pmam_emoji_yes: str = '<:vote_yes:1296964724319195188>'
    pmam_emoji_abstain: str = '<:vote_abstain:1296964800982548511>'
    pmam_emoji_no: str = '<:vote_no:1296964759916122207>'
    starboard_emoji_id: int = 1528483599974666410
    starboard_reactions_needed: int = 1
else:
    pmam_channelid_starboard: int = 1192917950001315980
    pmam_vote_channelids: typing.List[int] = [1005658147861573642, 1147624721156948068] # #moderator-discussion and #basement-area
    pmam_showcasing_channelids: typing.List[int] = [941813875538538627] #🎮┃playtesting
    pmam_finishedmaps_channelid: int = 1352328855938924564 # finished-map-links (forum)
    pmam_emoji_yes: str = "<:vote_yes:975946668379889684>"
    pmam_emoji_abstain: str = "<:vote_abstain:975946602206363659>"
    pmam_emoji_no: str = "<:vote_no:975946731202183230>"
    starboard_emoji_id: int = 1081025872175308901 #emoji ID used for starboard
    starboard_reactions_needed: int = 5
    

#link_prefixs: typing.List[str] = ["https://steamcommunity.com/sharedfiles/filedetails/", "https://steamcommunity.com/workshop/filedetails/", "https://steamcommunity.com/sharedfiles/itemedittext/"]
link_regex: re.Pattern = re.compile(r'https://steamcommunity.com/(sharedfiles|workshop)/(filedetails|itemedittext)[/]?\?id\=([0-9]+)')

class Extension(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot: commands.Bot = bot
        
    async def if_map_link_send_steam(self, message: discord.Message, thread_override: discord.Thread | None = None):
        '''
        If the provided `message` has any Steam workshop links, 
        create a thread (or use `thread_override`, if given)
        and send a steamitem link there.
        '''
        # If we found at least one Steam workshop link in the message
        matches = re.findall(link_regex, message.content)
        
        if len(matches) > 0:
            # Only use the first link found
            link_match = matches[0]
            map_id = link_match[-1]
            
            thread = thread_override or await message.create_thread(name = f"{message.author.display_name}'s Map")
            await thread.send(
                f"Here is a link that will directly open Steam: https://electrovoyage.github.io/steamitem?id={map_id}"
            )
            log(f"Steam workshop map thread created:")
            log(f"\"{message.author.display_name}'s Map\": " \
                f"https://electrovoyage.github.io/steamitem?id={map_id}"
            )
            log(f"Thread ID: {thread.id} Thread's Parent Channel: {thread.parent.name}")
        
    @commands.Cog.listener()
    async def on_thread_create(self, thread: discord.Thread):
        if thread.parent_id == pmam_finishedmaps_channelid:
            # The starter message is the same ID as the thread
            await self.if_map_link_send_steam(await thread.fetch_message(thread.id), thread)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message):
        # Special vote command only useable in select channels
        if (("!vote" in message.content.lower()) and (message.channel.id in pmam_vote_channelids)):
            await message.add_reaction(pmam_emoji_yes)
            await message.add_reaction(pmam_emoji_abstain)
            await message.add_reaction(pmam_emoji_no)
            
        if message.channel.id in pmam_showcasing_channelids:
            await self.if_map_link_send_steam(message)
    
    @commands.Cog.listener()
    async def on_raw_reaction_add(self, ctx: commands.Context):
        # Check if the emoji added is the starboard emoji.
        if ctx.emoji.id != starboard_emoji_id:
            return
        
        channel_starboard: discord.TextChannel = self.bot.get_channel(pmam_channelid_starboard)
        message: discord.Message = await self.bot.get_channel(ctx.channel_id).fetch_message(ctx.message_id)

        for reaction in message.reactions:
            # Only get the starboard emoji reactions information.
            if ((not reaction.is_custom_emoji()) or (reaction.emoji.id != starboard_emoji_id)): continue

            # Potentially come back to using history to search if a starboard message has already been boarded instead of using a txt file.
            # async for oldmessage in channel_starboard.history(limit=10, around=message.created_at):
            #     print(oldmessage.id)
            #     if oldmessage.id == message.id:
            #         return
            
            # Once the message has five starboard emoji reactions and its not a message by The Watcher,
            # add it to the starboard list and send a message to the channel.
            if ((reaction.count >= starboard_reactions_needed) and (message.author.id != self.bot.user.id)):
                with open("starboard.txt", "r+") as f:
                    content = f.read()
                    if str(message.id) in content: return
                    f.write(f"{str(message.id)}\n")
                
                # Message references could also mean replies, but we don't care about those.
                forwarded = message.reference and message.reference.type == discord.MessageReferenceType.forward
                content_message = message.message_snapshots[0] if forwarded else message
                
                # Ideally we'd have some kind of way to prevent forwarding the same message multiple times
                # from being starboarded multiple times, but I can't see a way that can be done.
                
                await message.forward(channel_starboard)
                
                log("Starboard Message:")
                log(f"Message by @{message.author.display_name} from #{message.channel.name}:")
                log(f"Message: {content_message.content}" if content_message.content else "")
                log(f"Attachments: {content_message.attachments}" if content_message.attachments else "")
                log(f"Original message: {message.jump_url}")

async def setup(bot: commands.Bot):
    await bot.add_cog(Extension(bot))
