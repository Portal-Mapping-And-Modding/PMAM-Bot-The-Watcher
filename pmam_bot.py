import discord
from discord import app_commands
from discord.ext import commands, tasks
from steamlib import id_to_name, vanity_to_id, get_friends_ids
import os, datetime, requests, asyncio, traceback, py7zr, threading, typing, io
from dotenv import load_dotenv

from logger import setupLogging, log

load_dotenv() # Get environment variables from .env file.
if os.getenv('TEST') == "1":
    token: str = os.getenv('TEST_TOKEN')
    pmam_roleid_robot: int = 1286723072975569029
    pmam_guild_id: int = 969790418394964019
    pmam_channelid_logs: int = 1287488941255299325
    pmam_channelid_modmail: int = 1287489528176709752
    pmam_channelid_modbots: int = 1287488941255299325
    pmam_messageid_verify: int = 1287488894769696800
    pmam_admin_id: int = 1261420793779191880
else:
    token: str = os.getenv('TOKEN')
    pmam_roleid_robot: int = 1001936969326133371
    pmam_guild_id: int = 830239808596606976
    pmam_channelid_logs: int = 882296490314321961
    pmam_channelid_modmail: int = 1265721193885863936
    pmam_channelid_modbots: int = 830243685135941652
    pmam_messageid_verify: int = 1282465091480064112
    pmam_admin_id: int = 988839520797601904

# Custom CommandTree subclass which handles application commands errors
class PMAMCommandTree(app_commands.CommandTree):
    async def on_error(self, interaction: discord.Interaction, error: app_commands.AppCommandError):
        if isinstance(error, app_commands.errors.CheckFailure) or isinstance(error, app_commands.errors.MissingPermissions):
            await interaction.response.send_message("You can not use this command.", ephemeral=True)
            return
        elif isinstance(error, app_commands.CommandOnCooldown):
            await interaction.response.send_message(f"This command is on cooldown for `{error.retry_after}` seconds. Please try again later.", ephemeral=True)
            return
        else:
            await interaction.response.send_message(f"A error occurred with this command! Notify the mods/admins!", ephemeral=True)

        error_msg = '\nAn error occurred with the bot!'\
                    f'\nError details: {error}'
        error_msg_traceback = f'\nFull traceback:\n{traceback.format_exc()}'
        
        log(error_msg + error_msg_traceback, log_level=2)
        
        # Notify mods and admins the bot did not work correctly
        if len(error_msg + error_msg_traceback) > 2000:
            await bot.get_channel(pmam_channelid_modbots).send(
                error_msg +
                '\nFull traceback is too big to send!'\
                '\nCheck the bot\'s logs for the full error!'
            )
            return
        await bot.get_channel(pmam_channelid_modbots).send(error_msg + error_msg_traceback)

# Custom commands.Bot subclass for the bot
class PMAMBot(commands.Bot):
    # command_prefix and description need to be set blank for now so once `bot` is defined here,
    # its prefix can be changed after configs are setup in bot_initialization
    def __init__(self, *,
                 command_prefix: str = "?",
                 tree_cls: app_commands.CommandTree = PMAMCommandTree,
                 description: str = "The Portal Mapping and Modding Discord server's bot, The Watcher!",
                 intents: discord.Intents = discord.Intents.all()
                 ):
        super().__init__(command_prefix=command_prefix, tree_cls=tree_cls, description=description, intents=intents)
        self.dm_cooldown = {} # List of users on the cooldown for modmail DMs
        self.tz = datetime.datetime.now().astimezone().tzinfo # current time zone for the bot

    # Task to restart the bot so the sh script can backup the database
    restart_time = datetime.time(hour=0, tzinfo=datetime.datetime.now().astimezone().tzinfo)
    @tasks.loop(time=restart_time)
    async def restart(self):
        log("Restarting and backing up bot!", 1)
        await self.close()

    # Runs when the bot is being setup
    async def setup_hook(self):
        log("Setting up bot hook...")
        
        # Load extension modules
        await self.load_extension('pmam_extension')
        await self.load_extension('levels')
        
        # Sync application/hybrid commands with the PMAM Discord server
        self.tree.copy_global_to(guild=discord.Object(id=pmam_guild_id))
        await self.tree.sync(guild=discord.Object(id=pmam_guild_id))

        # Start the auto restarting for the bot and check if any local deleted_files are over a month old.
        self.restart.start()
                
        # Check if there are kept deleted_files over a 30 days old, delete if they are.
        log("Checking for any deleted_files for 30 days old...")
        if os.path.exists("deleted_files"):
            for file in os.listdir("deleted_files"):
                if (datetime.datetime.now(tz=self.tz) - datetime.datetime.fromtimestamp(os.path.getmtime(f'deleted_files/{file}'))) > datetime.timedelta(days=30):
                    os.remove(f'deleted_files/{file}')
                    log(f"Removed {file}.")
        else:
            os.mkdir("deleted_files")
            log('Made "deleted_files" directory.')
        
        log("Finished setting up bot hook...")

    # Runs when the bot has finished running through setup_hook
    async def on_ready(self):
        log("Almost ready...")
        log("Setting the bot's Discord presence...")
        # According to the API documentation change_presence can cause problems doing it here, https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-set-the-playing-status
        # However it has yet to cause any actual problems from my (Orsell's) experience, so be warned.
        await self.change_presence( 
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Hammer Crash For The Millionth Time :("
            )
        )
        
        log("Alive and connected!")
        log(f'Logged on as {self.user}!')
        log("----------------------------")
        
    async def on_disconnect(self):
        log("The bot has disconnected from Discord!", 1)
    
    async def on_connect(self):
        log("The bot has connected to Discord!")
    
    # Called when any non-caught command errors occur
    async def on_command_error(self, ctx: commands.Context, exception):
        # Below instance checks are to handle common errors with all commands
        if isinstance(exception, commands.CommandNotFound):
            return
        elif isinstance(exception, commands.MissingRequiredArgument):
            await ctx.reply(f"You're missing the `{exception.param}` parameter of this command.", delete_after=3)
            return
        elif isinstance(exception, commands.MissingPermissions) or isinstance(exception, commands.MissingAnyRole) or isinstance(exception, commands.CheckFailure):
            await ctx.reply(f"You do not have permission to run this command.", delete_after=3)
            return
        elif isinstance(exception, commands.CommandOnCooldown):
            await ctx.reply(f"This command is on cooldown for `{exception.retry_after}` seconds. Please try again later.", delete_after=3)
            return
        else:
            await ctx.reply(f"A error occurred with this command! Notify the mods/admins!", delete_after=3)
        
        error_msg = '\nAn error relating to bot commands occurred!'\
                    f'\nError details: {exception}'\
                    f'\nCommand issued: {ctx.command.name}'\
                    f'\nCommand issued by: {ctx.author.name}'
        error_msg_traceback = f'\nFull traceback:\n{traceback.format_exc()}'

        log(error_msg + error_msg_traceback, log_level=2)

        # Notify mods and admins the bot did not work correctly
        if len(error_msg + error_msg_traceback) > 2000:
            await self.get_channel(pmam_channelid_modbots).send(
                error_msg +
                '\nFull traceback is too big to send!'\
                '\nCheck the bot\'s logs for the full error!'
            )
            return
        await self.get_channel(pmam_channelid_modbots).send(error_msg + error_msg_traceback)

    # Called when there are any non-caught errors that occur
    async def on_error(self, event, *args, **kwargs):
        error_msg = '\nAn error occurred with the bot!'\
                    f'\nError details: {event}'
        error_msg_traceback = f'\nFull traceback:\n{traceback.format_exc()}'
        
        log(error_msg + error_msg_traceback, log_level=2)

        # Notify mods and admins the bot did not work correctly
        if len(error_msg + error_msg_traceback) > 2000:
            await self.get_channel(pmam_channelid_modbots).send(
                error_msg +
                '\nFull traceback is too big to send!'\
                '\nCheck the bot\'s logs for the full error!',
            )
            return
        await self.get_channel(pmam_channelid_modbots).send(error_msg + error_msg_traceback)

bot = PMAMBot()

@bot.check # GLOBAL command check
def pmam_check(ctx: commands.Context) -> bool:
    """Checks if the command is being called in PMAM. Works for both application and normal commands.

    Args:
        ctx (commands.Context): Command context.

    Returns:
        bool: Whether the check passed or not.
    """
    if isinstance(ctx, commands.Context):
        return ctx.author.guild.id == pmam_guild_id
    return ctx.user.guild.id == pmam_guild_id

def pmam_admin(ctx: typing.Union[commands.Context, discord.Interaction]) -> bool:
    """Checks if a PMAM admin is running this command.

    Args:
        ctx (commands.Context, optional): Command context. Defaults to None.
        interaction (discord.Interaction, optional): Interaction context. Defaults to None.

    Returns:
        bool: Whether the user that executed the command is an admin or not.
    """
    if isinstance(ctx, commands.Context):
        user_roles = ctx.author.roles
    else:
        user_roles = ctx.user.roles
    
    if discord.utils.get(ctx.guild.roles, id=pmam_admin_id) in user_roles:
        return True
    
    return False

def check_steam_games(link):
    link = f'{link}/games/?tab=all'

    respons = requests.get(link)
    soup = BeautifulSoup(respons.text, features="html.parser")
    games = str(soup.find_all("div"))
    if '"appid":620' in games:
        return True
    else:
        return False

@bot.event
async def on_member_update(member_before: discord.Message, member_after: discord.Message):
    if member_before.roles == member_after.roles:
        return
    
    role = discord.utils.get(bot.guilds[0].roles, id = 894351178702397520)
    channel = bot.get_channel(pmam_channelid_logs)
    
    if not (role in member_after.roles and role not in member_before.roles):
        return

    embed = discord.Embed(title = "Member verified!",color=discord.Color.green())
    embed.add_field(name="User",value=f"{member_after.display_name}#{member_after.discriminator}", inline=False)
    embed.add_field(name="ID",value=member_after.id,inline=False)
    embed.set_thumbnail(url=member_after.avatar.url)
    await channel.send(embed=embed)

@bot.event
async def on_member_join(member: discord.Member):
    if member.guild.id != pmam_guild_id:
        return

    account_time = member.created_at
    age = datetime.datetime.now(tz=datetime.timezone.utc) - account_time

    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(title = "Member joined!",color=discord.Color.green())
    embed.add_field(name="User",value=f"{member.display_name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID",value=member.id,inline=False)
    embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member: discord.Member):
    if member.guild.id != pmam_guild_id:
        return

    account_time = member.created_at
    age = datetime.datetime.now(tz=datetime.timezone.utc) - account_time

    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(title = "Member left!",color=discord.Color.red())
    embed.add_field(name="User",value=f"{member.display_name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID",value=member.id,inline=False)
    embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    await channel.send(embed=embed)

# Have to make separate function in order to thread compressing a 7zip archive so it doesn't cause blocking.
def compressFile(fp):
   with py7zr.SevenZipFile(fp + ".7z", "w") as archive:
        archive.write(fp)

@bot.event
async def on_message_delete(message: discord.Message):
    if message.author.bot or message.guild.id != pmam_guild_id:
        return
    
    channel = bot.get_channel(pmam_channelid_logs)

    if len(message.content) > 0:
        log(f"Member {message.author} has deleted a message.")
        if len(message.content) > 1024: message.content = message.content[:995] + "\nMore than 1024 characters..."
        message_embed = discord.Embed(
            color = 0xff470f,
            timestamp = datetime.datetime.now(tz=datetime.timezone.utc),
            description = f"**Message sent by <@!{message.author.id}> deleted in <#{message.channel.id}>**\n{message.content}"
        )
        message_embed.set_author(name = f"{message.author.display_name}#{message.author.discriminator}", icon_url = message.author.display_avatar.url)
        message_embed.set_footer(text = f"Author: {message.author.id} | Message ID: {message.id}")
        await channel.send(embed = message_embed)
        log(f"Message sent by {message.author} deleted in {message.channel.name}:\n{message.content}")
    
    if message.attachments == []:
        log("Finished on_message_delete event.")
        return
    
    log(f"Member {message.author} has deleted attachment(s).")
    if not os.path.exists("deleted_files"): # Make "deleted_files" folder if for some reason it doesn't exist
        os.mkdir("deleted_files")
    
    # Attachments were part of the message, so get them and log them if possible.
    attachment_num = 1
    attachment_list = []
    compressFileThread = None
    for deleted_attachment in message.attachments:
        attachment_name = f"{message.author}-{attachment_num}_{deleted_attachment.filename}" # Format name of deleted file to mention the original author.
        # Some file types on Discord's servers aren't cached so getting the saved cache might fail, instead save without the cache if it fails.
        try:
            await deleted_attachment.save("deleted_files/" + attachment_name, use_cached=True)
        except:
            await deleted_attachment.save("deleted_files/" + attachment_name)
        
        # Bot has a 8MB upload limit. So if it is over this limit compress it into a 7zip archive.
        if deleted_attachment.size > 8000000:
            log(f'The file "{attachment_name}" is over 8MB, compressing into 7z...', 1)
            compressFileThread = threading.Thread(target=compressFile, args=("deleted_files/" + attachment_name,))
            compressFileThread.start()
            attachment = "deleted_files/" + attachment_name + ".7z"
        else:
            attachment = "deleted_files/" + attachment_name

        attachment_list.append(attachment)
        attachment_num += 1
    if compressFileThread:
        compressFileThread.join()

    deleted_attachment_embed = discord.Embed(
        color = 0xff470f,
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc),
        description = f"**File(s) sent by <@!{message.author.id}> deleted in <#{message.channel.id}>**\nFile(s) are attached below..."
    )
    deleted_attachment_embed.set_author(name=f"{message.author.display_name}", icon_url=message.author.display_avatar.url)
    deleted_attachment_embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")
    await channel.send(embed=deleted_attachment_embed)
    log(f"File(s) sent by {message.author} deleted in {message.channel.name}")

    for attachment in attachment_list:
        # If the file is still too big even after compression, to have the file still be logged, it will be kept on the server for a month after which it is automatically deleted.
        if os.path.getsize(attachment) > 8000000:
            await channel.send(content=f'\n**The file "{attachment}" exceeds Discord\'s 8MB bot upload limit even after compression.\nIt\'s archive size is `{os.path.getsize(attachment)}` bytes.\nThe archive will be stored locally on the bot\'s server for 30 days.**\n')
            log(f'**The file "{attachment}" exceeds Discord\'s 8MB bot upload limit even after compression.\nIt\'s archive size is `{os.path.getsize(attachment)}` bytes.\nThe archive will be stored locally on the bot\'s server for 30 days.**\n', 2) 
            os.remove(attachment.replace(".7z", "")) # Remove the original non-archived file and keep the 7z
        else:
            await channel.send(file=discord.File(attachment))
            log(f"Sent {attachment} to logs channel.")
        
        if ".7z" in attachment: os.remove(attachment.replace(".7z", "")) # Remove the original non-archived file
        os.remove(attachment) # Remove the original uploaded file
        log(f'Removed {attachment}.')
    
    log("Finished on_message_delete event.")

@bot.event
async def on_message_edit(before: discord.Message, after: discord.Message):    
    if (before.author.bot) or (before.guild.id != pmam_guild_id) or (before.content == after.content):
        return
    
    if len(before.content) > 1024: before.content = before.content[:995] + "\nMore than 1024 characters..."
    if len(after.content) > 1024: after.content = after.content[:995] + "\nMore than 1024 characters..."
    
    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(color=0x307dd5, timestamp=datetime.datetime.now(tz=datetime.timezone.utc), description=f"**Message edited in <#{before.channel.id}>** [Jump to message]({after.jump_url})")
    embed.set_author(name=f"{before.author.display_name}", icon_url=before.author.display_avatar.url)
    embed.add_field(name="Before", value=before.content, inline=False)
    embed.add_field(name="After", value=after.content, inline=False)
    embed.set_footer(text=f"User ID: {before.author.id}")
    await channel.send(embed=embed)

@bot.event
async def on_message(message: discord.Message):
    if message.author.bot or (not isinstance(message.channel, discord.DMChannel)) or (bot.get_guild(pmam_guild_id).get_member(message.author.id) == None):
        await bot.process_commands(message)
        return

    if message.author.id in bot.dm_cooldown.keys() and bot.dm_cooldown[message.author.id] > datetime.datetime.now(tz=datetime.timezone.utc).second:
        await message.channel.send(f"DM messaging is on cooldown for 15 seconds!")
        return

    if bot.dm_cooldown.get(message.author.id): bot.dm_cooldown.pop(message.author.id)
    channel = bot.get_channel(pmam_channelid_modmail)
    embed = discord.Embed(color=0xff470f)
    embed.set_author(name=f"Author: {message.author.display_name}")
    embed.set_footer(text=f"User ID: {message.author.id}")
    embed.set_thumbnail(url=(message.author.display_avatar.url))
    embed.add_field(name="Message:", value=message.content, inline=False)
    
    bot.dm_cooldown[message.author.id] = datetime.datetime.now(tz=datetime.timezone.utc).second + 15
    await channel.send(embed=embed)    

@bot.command(aliases = ['id_check','check_id'])
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def _id_check(ctx: commands.Context, user: discord.Member = None):
    if (ctx.guild.fetch_member(user.id) and user) == None:
        await ctx.send("Invalid ID/user!", delete_after=3)
        return
    
    time = datetime.datetime.now(tz=datetime.timezone.utc)
    account_time = user.created_at
    age = time - account_time
    if age.total_seconds() < 259200:
        embed = discord.Embed(title="Account is less than 3 days old!", color=discord.Color.red())
        embed.add_field(name="User", value=f"{user.display_name}#{user.discriminator}", inline=False)
        embed.add_field(name="ID", value=user.id, inline=False)
        embed.add_field(name="Created at: ", value=f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    else:
        embed = discord.Embed(title="Account is more than 3 days old!", color=discord.Color.green())
        embed.add_field(name="User", value=f"{user.display_name}#{user.discriminator}", inline=False)
        embed.add_field(name="ID", value=user.id,inline=False)
        embed.add_field(name="Created at: ", value=f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    
    await ctx.send(embed=embed)

@bot.tree.command()
async def membercount(interaction: discord.Interaction):
    embed = discord.Embed(color=0x307dd4, timestamp=datetime.datetime.now(tz=datetime.timezone.utc))
    embed.add_field(name="Members 🤖", value=interaction.guild.member_count)
    await interaction.response.send_message(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def ban(ctx: commands.Context, user: discord.Member):
    if ctx.guild.fetch_member(user.id) == None:
        await ctx.send(embed=discord.Embed(color=discord.Color.red(), description="<:vote_no:975946731202183230> ***Invalid ID/user!***"))
        return
    
    await ctx.guild.ban(user.id)
    await ctx.send(embed=discord.Embed(color=discord.Color.green(), description=f"<:vote_yes:975946668379889684> ***{user.display_name}#{user.discriminator} was banned***"))

def important_message(message):
    return (pmam_messageid_verify != message.id)

@bot.command() #! REWORK
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def purge(ctx: commands.Context, number: int):
    channel = bot.get_channel(pmam_channelid_logs)
    if os.path.exists("./deleted.txt"): os.remove("./deleted.txt")
    with open ("./deleted.txt", "w") as f:
        list = []
        async for i in ctx.history(limit=(number+1)):
            list.append(i)
        f.write(f"Deleted messages log from: #{ctx.channel.name}\n")
        for i in reversed(list):
            if i.attachments == []:
                f.write(f"[{str(i.created_at)[:-13]}] [{i.author.name}]: {i.content}\n")
            else:
                f.write(f"[{str(i.created_at)[:-13]}] [{i.author.name}]: {i.content} [Attachments: {', '.join([x.url for x in i.attachments])}]\n")

    await ctx.channel.purge(limit=number+1, check=important_message)
    await ctx.send(f"Purged `{number}` messages!", delete_after=2)
    await channel.send(file=discord.File("./deleted.txt"))

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
async def verify(ctx: commands.Context):
    time = datetime.datetime.now(tz=datetime.timezone.utc)
    account_time = ctx.author.created_at
    age = time - account_time
    channel = bot.get_channel(pmam_channelid_logs)
    with open("./locked_ids.txt", "r") as f:
        banned_ids = f.read()
        if str(ctx.author.id) in banned_ids:
            await ctx.send("The moderator team has blocked you from using the verification command! Please ping an online mod/admin to sort things out.", delete_after=5)
            f.close()
            return
        f.close()
            
    if age.days > 450:
        role = discord.utils.get(ctx.author.guild.roles, id=894351178702397520)
        if role in ctx.author.roles:
            await ctx.send('You are already verified!', delete_after=2)
        else:
            await ctx.send("Verification successful!", delete_after=2)
            await ctx.author.add_roles(role)
            await asyncio.sleep(1)
            await ctx.channel.purge(limit=1)
    else:
        embed = discord.Embed(title = "`?verify` command failed!", color=discord.Color.red())
        embed.add_field(name="User", value=f"{ctx.author.display_name}#{ctx.author.discriminator}", inline=False)
        embed.add_field(name="ID", value=ctx.author.id, inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)
        await ctx.send("Since your account is rather new you will need to connect your Steam account and then ping any online moderator.", delete_after=5)

#@bot.command()
#async def steamverify(ctx, steamlink = None):
    #role = discord.utils.get(ctx.author.guild.roles, id = 894351178702397520)
    #channel = bot.get_channel(pmam_channelid_logs)
    #if role in ctx.author.roles:
        #await ctx.send('You are already verified!')
    #else:
        #if steamlink is not None:
            #if "steamcommunity.com" in steamlink:
                #if check_steam_games(steamlink):
                    #await ctx.author.add_roles(role)
                    #await ctx.send("Verification sucessful!")
                    #embed = discord.Embed(title = "`?steamverify` command success!",color=discord.Color.green())
                    #embed.add_field(name="User",value=f"{ctx.author.display_name}#{ctx.author.discriminator}", inline=False)
                    #embed.add_field(name="ID",value=ctx.author.id,inline=False)
                    #embed.add_field(name="Used link",value=steamlink,inline=False)
                    #embed.set_thumbnail(url=ctx.author.display_avatar.url)
                    #await channel.send(embed=embed)
                #elif check_steam_games(steamlink) is False:
                    #await ctx.send("Verification failed! Make sure you have your games set to be publicly visible")
                    #embed = discord.Embed(title = "`?steamverify` command failed!",color=discord.Color.red())
                    #embed.add_field(name="User",value=f"{ctx.author.display_name}#{ctx.author.discriminator}", inline=False)
                    #embed.add_field(name="ID",value=ctx.author.id,inline=False)
                    #embed.set_thumbnail(url=ctx.author.display_avatar.url)
                    #await channel.send(embed=embed)
            #else:
                #await ctx.send("This is not Steam link!")
        #else:
            #await ctx.send("Please provide link to Steam profile!")
            #user = await bot.fetch_user(ctx.author.id)
            #profile = await user.profile()
            #print(profile)

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def lockverify(ctx: commands.Context, user: discord.Member):
    if ctx.guild.fetch_member(user.id) == None:
        await ctx.send("Invalid ID/user!", delete_after=3)
        return
        
    with open("locked_ids.txt","r+") as f:
        if str(user.id) not in f.read():
            f.write(f'{user.id}\n')
            await ctx.send("User blocked from verification!")
        else:
            await ctx.send("This user is already blocked!")
        f.close()

@bot.hybrid_command()
async def search(ctx: commands.Context, *, word: str):
    word = word.replace(" ","_")
    url = f"https://developer.valvesoftware.com/w/index.php?search={word}"
    r = requests.get(url,allow_redirects=False)
    try:  
        if "There were no results matching the query." in str(r.content):
            await ctx.send("This page doesn't not exist!")
        else:
            final = r.headers["Location"]
            await ctx.send(final)
    except KeyError:
        await ctx.send(f'This page might not exist, check it manually: {url}')
    
@bot.hybrid_command()
async def mutual_friends(ctx: commands.Context, link1: str, link2: str):
    if "profiles" in link1: link1 = link1[36:]
    elif link1.endswith("/"):
        link1 = link1[:-1]
        link1 = vanity_to_id(link1)
    if "profiles" in link2:
        link2 = link2[36:]
    elif link2.endswith("/"):
        link2 = link2[:-1]
        link2 = vanity_to_id(link2)

    try:
        l1 = get_friends_ids(link1)
        l2 = get_friends_ids(link2)
        mutual = []
        for i in l1:
            if i in l2:
                mutual.append(id_to_name(i))
        if mutual == []:
            await ctx.send("These 2 people don't have any mutual friends")
        else:
            await ctx.send(f"Mutual friends list: {', '.join(mutual)}")
    except Exception as e:
        await ctx.send("An error occurred!")
        log(e, 2)
        raise e

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def mass_id_check(ctx: commands.Context):
    channel = bot.get_channel(pmam_channelid_logs)
    em1 = discord.Embed(title = "`?mass_id_check` command used!", color=discord.Color.green())
    await channel.send(embed=em1)
    for i in bot.guilds[0].humans:
        if len(i.roles) == 1:
            time = datetime.datetime.now(tz=datetime.timezone.utc)
            account_time = i.created_at
            age = time - account_time
            embed = discord.Embed(title = f"{i.name}#{i.discriminator}", color=discord.Color.blue())
            embed.add_field(name="ID", value=i.id, inline=False)
            embed.add_field(name="Created at: ", value=f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
            await channel.send(embed=embed)
            
@bot.hybrid_command()
@commands.bot_has_role(pmam_roleid_robot)
async def selfroles(ctx: commands.Context):
    value2 = []
    with open ("./selfroles.txt", "r") as f:
        embed = discord.Embed(title="Selfroles", color=discord.Color.dark_blue())
        value = str(f.read()).split()
        log(value)
        for i in value:
            try:
                value2.append(discord.utils.get(ctx.author.guild.roles, id=int(i)).name)
            except Exception:
                pass
        log(value2)
        value = "\n".join(value2)
        log(value)
        embed.add_field(name="You can have these roles: ",value=f"{value}",inline=False)
        await ctx.send(embed = embed)

@bot.command(aliases = ["selfrole_add","selfroles_add"])
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def _selfrole_add(ctx: commands.Context, *, role_name: str):
    try:
        role = discord.utils.get(ctx.guild.roles, name=role_name)
        with open("selfroles.txt", "r+") as f:
            if str(role.id) not in f.read():
                current = f.read()
                current = current + f" {role.id}" 
                #print(current)
                f.write(str(current))
                await ctx.send("Selfrole added!")
            else:
                await ctx.send("This role is already self-assignable!")
    #await ctx.send(role.id)
    except:
        await ctx.send(f"Couldn't find role with a name `{role_name}`")

@bot.command(aliases = ["selfrole_remove","selfroles_remove"])
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def _selfrole_remove(ctx: commands.Context, *, role_name: str):
    current = ""
    role_is_here = False
    try:
        role = discord.utils.get(ctx.guild.roles, name= role_name)
        with open("selfroles.txt", "r") as f:
            if str(role.id) in f.read():
                role_is_here = True
        if role_is_here:
            with open("selfroles.txt", "r") as f:
                current = f.read()
                current = current.replace(str(role.id),"")
            os.remove("selfroles.txt")
            with open("./selfroles.txt","w") as f:
                f.write(current)
                await ctx.send("Selfrole removed!")
        else:
            await ctx.send("This role is not self-assignable!")

    except:
        await ctx.send(f"Couldn't find role with a name `{role_name}`")
        
@bot.hybrid_command()
@commands.bot_has_role(pmam_roleid_robot)
async def iam(ctx: commands.Context, *, role_name: str):
    if discord.utils.get(ctx.guild.roles, name=role_name) == None:
        await ctx.send("Invalid role name!", delete_after=2)
        return
    
    role = discord.utils.get(ctx.guild.roles, name=role_name)
    with open("selfroles.txt", "r") as f:
        if str(role.id) in f.read():
            if role not in ctx.author.roles:
                await ctx.author.add_roles(role)
                await ctx.send("Selfrole added!")
            else:
                await ctx.send("You already have this role")
        else:
            await ctx.send("You can't get this role!")
        f.close()

@bot.hybrid_command()
@commands.bot_has_role(pmam_roleid_robot)
async def iamnot(ctx: commands.Context, *, role_name: str):
    if discord.utils.get(ctx.guild.roles, name=role_name) == None:
        await ctx.send("Invalid role name!", delete_after=2)
        return

    role = discord.utils.get(ctx.guild.roles, name=role_name)
    with open("selfroles.txt", "r") as f:
        if str(role.id) in f.read():
            if role in ctx.author.roles:
                await ctx.author.remove_roles(role)
                await ctx.send("Selfrole removed!")
            else:
                await ctx.send("You don't have this role")
        else:
            await ctx.send("You can't remove this role!")
        f.close()

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
@commands.has_permissions(ban_members=True)
async def chocolate(ctx: commands.Context, user: discord.Member):
    if ctx.guild.fetch_member(user.id) == None:
        await ctx.send("Invalid ID/user!", delete_after=3)
        return
    
    await ctx.send(f"{user.mention} has been given one chocolate bar :chocolate_bar:")

@bot.tree.command()
@app_commands.checks.cooldown(1, 3)
@app_commands.check(pmam_check)
async def ping(interaction: discord.Interaction):
    """Pings The Bot"""

    await interaction.response.defer(thinking=True)

    ping_embed = discord.Embed(
        title="Pong!",
        description=f'**Latency: {round((bot.latency * 1000), 2)} ms**',
        color=discord.Color.brand_green())
    ping_thumbnail = discord.File(f"{os.getcwd() + os.sep}images{os.sep}ping_pong.png", filename="ping_thumbnail.png")
    ping_embed.set_thumbnail(url="attachment://ping_thumbnail.png")
    await interaction.followup.send(file=ping_thumbnail, embed=ping_embed)

@bot.command()
@commands.check(pmam_admin)
async def restart(ctx: commands.Context):
    """Manually restart the bot."""

    log("Manually restarting the bot!", 1)
    await ctx.send("Restarting, good bye!")
    await bot.close()

def ByteAttachmentsToFiles(byte_list: list[bytes, str]) -> typing.List[discord.File]:
    """Turns a list of the bytes of a attachment with the original attachment file name into a discord.File.

    Args:
        byte_list (list[bytes, str]): A list that contains a list pairs of the attachments bytes and original attachment file name.

    Returns:
        typing.List[discord.File]: The list of converted discord.File.
    """
    attachments = []
    for fb in byte_list:
        attachments.append(discord.File(io.BytesIO(fb[0]), fb[1]))
    return attachments

class ModMailModal(discord.ui.Modal, title='Send ModMail Message'):
    def __init__(self, member: discord.Member, attachments: typing.List[discord.Attachment]):
        self.member = member
        self.attachments = attachments
        super().__init__()

        self.message = discord.ui.TextInput(
            label = 'Message You Want To Send',
            style = discord.TextStyle.long,
            placeholder = 'Insert yapping here...',
            required = False,
            min_length= 0,
            max_length = 1950, # Max message size for bot is 2000, but the heading sent with the message needs to be accounted for.
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: discord.Interaction):
        # Check if user is in server
        if bot.get_user(self.member.id) == None:
            await interaction.response.send_message(f"Could not find user {self.member}!", ephemeral=True)
            return
        
        attachments = []
        # Convert and replace each discord.Attachment in the provided attachments with the bytes of each attachment so they can be send multiple times.
        for i, attachment in enumerate(self.attachments):
            file_bytes: bytes = None
            # Some file types on Discord's servers aren't cached or the attachment can't be cached, so getting the attachment's cache might fail.
            # Instead use without the cache if it fails.
            try:
                file_bytes = await attachment.read(use_cached=True)
            except:
                file_bytes = await attachment.read()
            attachments.append([file_bytes, attachment.filename])
        
        await bot.get_user(self.member.id).send(f"Message from the PMAM Moderation Team:\n ```{self.message.value}```", files=ByteAttachmentsToFiles(attachments))
        await interaction.response.send_message(f"Message has been sent to {self.member.name}!", ephemeral=True)

        modmail_embed = discord.Embed(
            color = 0xff9b00,
            timestamp = datetime.datetime.now(tz=datetime.timezone.utc),
            description = f"**ModMail message sent by <@!{interaction.user.id}> to <@!{self.member.id}>**\n{self.message}\n{'Sent file(s) are attached below...' if self.attachments != [] else ''}"
        )
        modmail_embed.set_author(name=f"{interaction.user.display_name}", icon_url=interaction.user.display_avatar.url)
        modmail_embed.set_footer(text=f"Author: {interaction.user.id} | Interaction ID: {interaction.id}")
        await bot.get_channel(pmam_channelid_logs).send(embed=modmail_embed)
        if self.attachments != []: await bot.get_channel(pmam_channelid_logs).send(files=ByteAttachmentsToFiles(attachments))

        log(f"ModMail message was sent by {interaction.user.name} to member {self.member.name}.")
        log(f"Message sent:\n{self.message}")
        log(f"Attachments: {self.attachments}")

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        await interaction.response.send_message('Congrats! You broke this interaction somehow. DM to target user was not send. Tell Orsell that this broke.', ephemeral=True)

        error_msg = '\nAn error occurred with the bot!'\
                    f'\nError details: {error}'
        error_msg_traceback = f'\nFull traceback:\n{traceback.format_exc()}'
        
        log(error_msg + error_msg_traceback, log_level=2)

        # Notify mods and admins the bot did not work correctly
        if len(error_msg + error_msg_traceback) > 2000:
            await bot.get_channel(pmam_channelid_modbots).send(
                error_msg +
                '\nFull traceback is too big to send!'\
                '\nCheck the bot\'s logs for the full error!',
            )
            return
        await bot.get_channel(pmam_channelid_modbots).send(error_msg + error_msg_traceback)

@bot.tree.command()
@app_commands.check(pmam_check)
@app_commands.check(pmam_admin)
async def modmail(
    interaction: discord.Integration,
    *,
    member: discord.Member,
    attachment1: discord.Attachment = None,
    attachment2: discord.Attachment = None,
    attachment3: discord.Attachment = None,
    attachment4: discord.Attachment = None,
    attachment5: discord.Attachment = None,
    attachment6: discord.Attachment = None,
    attachment7: discord.Attachment = None,
    attachment8: discord.Attachment = None,
    attachment9: discord.Attachment = None,
    attachment10: discord.Attachment = None
    ):
    """Anomalously sends a message to a select user using the ModMail system.

    Args:
        interaction (discord.Interaction): Interaction context.
        attachment1-9 (discord.Attachment): Attachments to send to user. Only ten can be sent.
    """
    # Group together all attachment parameters into a list.
    attachments = [
        attachment1, attachment2, attachment3, attachment4,
        attachment5, attachment6, attachment7, attachment8,
        attachment9, attachment10
    ]
    # Filter out all the attachment parameters that weren't defined and keep the ones that were.
    attachments = list(filter(lambda x: isinstance(x, discord.Attachment), attachments))
    await interaction.response.send_modal(ModMailModal(member=member, attachments=attachments))

@bot.command()
@commands.check(pmam_admin)
async def modmail(ctx: commands.Context, member: discord.Member, *, message: str = ""):
    """Anomalously sends a message to a select user using the ModMail system.

    Args:
        interaction (discord.Interaction): Interaction context.
        user (discord.Member): Member to send message to.
        message (str): Message to send to member.
    """
    # Check if user is in server
    if bot.get_user(member.id) == None:
        await ctx.reply(f"Could not find user {member}!", delete_after=3)
        return

    if len(message) > 1950:
        await ctx.reply(f"Message exceeds 1950 characters!", delete_after=3)
        return

    attachments = []
    # Convert and replace each discord.Attachment in the provided attachments with the bytes of each attachment so they can be send multiple times.
    for i, attachment in enumerate(ctx.message.attachments):
        file_bytes: bytes = None
        # Some file types on Discord's servers aren't cached or the attachment can't be cached, so getting the attachment's cache might fail.
        # Instead use without the cache if it fails.
        try:
            file_bytes = await attachment.read(use_cached=True)
        except:
            file_bytes = await attachment.read()
        attachments.append([file_bytes, attachment.filename])
    
    await bot.get_user(member.id).send(f"Message from the PMAM Moderation Team:\n ```{message}```", files=ByteAttachmentsToFiles(attachments))
    await ctx.reply(f"Message has been sent to {member.name}!", delete_after=3)

    modmail_embed = discord.Embed(
        color = 0xff9b00,
        timestamp = datetime.datetime.now(tz=datetime.timezone.utc),
        description = f"**ModMail message sent by <@!{ctx.author.id}> to <@!{member.id}>**\n{message}\n{'Sent file(s) are attached below...' if ctx.message.attachments != [] else ''}"
    )
    modmail_embed.set_author(name=f"{ctx.author.display_name}", icon_url=ctx.author.display_avatar.url)
    modmail_embed.set_footer(text=f"Author: {ctx.author.id} | Message ID: {ctx.message.id}")
    await bot.get_channel(pmam_channelid_logs).send(embed=modmail_embed)
    if ctx.message.attachments != []: await bot.get_channel(pmam_channelid_logs).send(files=ByteAttachmentsToFiles(attachments))

    log(f"ModMail message was sent by {ctx.author.name} to member {member.name}.")
    log(f"Message sent:\n{message}")
    log(f"Attachments: {ctx.message.attachments}")
    


setupLogging(os.getcwd())
bot.run(token, log_handler=None, root_logger=True)
