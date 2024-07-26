import discord
from discord import app_commands
from discord.ext import commands, tasks
from itertools import cycle
from steamlib import id_to_name, vanity_to_id, get_friends_ids
import os, datetime, requests, asyncio, traceback
#from bs4 import BeautifulSoup

from logger import setup_logging, log

token: str = os.getenv('TOKEN')
pmam_guildid: int = 830239808596606976
test_guildid: int = 845791759984230430 #! REWORK FOR BOT TO BE ABLE TO BE PROPERLY TESTED
pmam_channelid_logs: int = 882296490314321961
pmam_channelid_modmail: int = 1265721193885863936
pmam_channelid_modbots: int = 830243685135941652
test_channelid_modmail: int = 845791759984230433
pmam_roleid_robot: int = 830240292183212042
tz = datetime.datetime.now().astimezone().tzinfo

class PMAMBot(commands.Bot):
    # command_prefix and description need to be set blank for now so once `bot` is defined here,
    # its prefix can be changed after configs are setup in bot_initialization
    def __init__(self, *,
                 command_prefix: str = "?",
                 description: str = "The Portal Mapping and Modding Discord server's bot, The Watcher!",
                 intents: discord.Intents
                 ):
        super().__init__(command_prefix=command_prefix, description=description, intents=intents)
        self.bot.dm_cooldown = {}

    # Task to restart the bot so the sh script can backup the database
    time = datetime.time(hour=00, tzinfo=tz)
    @tasks.loop(time=time)
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
        # Test bot is not in PMAM server so it can't sync specifically to PMAM
        try:
            self.tree.copy_global_to(guild=discord.Object(id=pmam_guildid))
            await self.tree.sync(guild=discord.Object(id=pmam_guildid))
        except Exception as e:
            log("Application command syncing failed!", 1)
            log("This is mostly likely because this is the test bot so please ignore.", 1)
            log(e, 1)

        self.restart.start()

        log("Finished setting up bot hook...")

    # Runs when the bot has finished running through setup_hook
    async def on_ready(self):
        #special_role.start()
        log("Almost ready...")
        log("Setting the bot's Discord presence...")
        # According to the API documentation change_presence can cause problems doing it here, https://discordpy.readthedocs.io/en/latest/faq.html#how-do-i-set-the-playing-status
        # However it has yet to cause any actual problems from my (Orsell's) experience, so be warned.
        await self.change_presence( 
            activity=discord.Activity(
                type=discord.ActivityType.watching,
                name="Hammer Crash For The Millonth Time :("
            )
        )
        
        log("Alive and connected!")
        log(f'Logged on as {self.user}!')
        log("----------------------------")
        
    async def on_disconnect(self):
        log("The bot has disconnected from Discord!", 1)
    
    async def on_connect(self):
        log("The bot has connected to Discord!")
    
    # Called when any non-caught errors occur with any commands
    async def on_command_error(self, ctx: commands.Context, exception):
        if isinstance(exception, discord.ext.commands.errors.CommandNotFound):
            return

        log(
            f'\nAn error relating to bot commands occurred!'\
            f'\nEvent details: {exception}'\
            f'\nCheck the latest log for the full traceback...',
            log_level=2
        )
        log("Check the latest log for the full traceback...", 2)
        log(f"Full traceback:\n{traceback.format_exc()}", 2, False)

        # Notify mods and admins the bot did not work correctly
        await self.get_channel(pmam_channelid_modbots).send(
            f'\nAn error relating to bot commands occurred!'\
            f'\nEvent details: {exception}'\
            f'\nCheck the latest log for the full traceback...'
        )

    # Called when there are any non-caught errors that occur
    async def on_error(self, event):
        log(
            f'\nAn error occurred with the bot!'\
            f'\nEvent details: {event}'\
            f'\nCheck the latest log for the full traceback...',
            log_level=2
        )
        log("Check the latest log for the full traceback...", 2)
        log(f"Full traceback:\n{traceback.format_exc()}", 2, False)

        # Notify mods and admins the bot did not work correctly
        await self.get_channel(pmam_channelid_modbots).send(
            f'\nAn error occurred with the bot!'\
            f'\nEvent details: {event}'\
            f'\nCheck the latest log for the full traceback...'
        )
        log(traceback.format_exc())

intents = discord.Intents.default()
intents.members = True
intents.presences = True
intents.message_content = True
bot = PMAMBot(intents = discord.Intents.all())

def check_steam_games(link):
    link = f'{link}/games/?tab=all'

    respons = requests.get(link)
    soup = BeautifulSoup(respons.text, features="html.parser")
    games = str(soup.find_all("div"))
    if '"appid":620' in games:
        return True
    else:
        return False

def real():
    url = "https://developer.valvesoftware.com/w/index.php?search=cubemap"
    #url = "https://developer.valvesoftware.com/w/index.php?search=big_chungus"
    r = requests.get(url,allow_redirects=False)
    #r2 = requests.get(url2)
    soup = BeautifulSoup(r.text, features="html.parser")
    #soup2 = BeautifulSoup(r2.text, features="html.parser")
    log(r.headers["Location"])


#hex = cycle([0x12c6ce,0xa34ec9,0xce2a61,0xd8791d,0x46944f,0x52c995])
hex = cycle([0xff0000,0xffff00,0x00ff00,0x00ffff,0x0000ff,0xff00ff])
@tasks.loop(hours=6)
async def special_role():
    role = discord.utils.get(bot.guilds[0].roles, id = 998311522461818893)
    await role.edit(colour = next(hex))

@bot.event
async def on_member_update(member_before, member_after):
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
async def on_member_join(member):
    if member.guild.id != pmam_guildid:
        return

    account_time = member.created_at
    age = datetime.datetime.now(datetime.timezone.utc) - account_time

    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(title = "Member joined!",color=discord.Color.green())
    embed.add_field(name="User",value=f"{member.display_name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID",value=member.id,inline=False)
    embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    await channel.send(embed=embed)

@bot.event
async def on_member_remove(member):
    if member.guild.id != pmam_guildid:
        return

    account_time = member.created_at
    age = datetime.datetime.now(datetime.timezone.utc) - account_time

    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(title = "Member left!",color=discord.Color.red())
    embed.add_field(name="User",value=f"{member.display_name}#{member.discriminator}", inline=False)
    embed.add_field(name="ID",value=member.id,inline=False)
    embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
    await channel.send(embed=embed)

@bot.event #! REWORK
async def on_message_delete(message):
    if message.author.bot and message.guild.id != pmam_guildid:
        return
    
    if len(message.content) > 1024: message.content = message.content[:995] + "\nMore than 1024 characters..."

    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(color = 0xff470f, timestamp = datetime.datetime.now(), description = f"**Message sent by <@!{message.author.id}> deleted in <#{message.channel.id}>**\n{message.content}")
    embed.set_author(name = f"{message.author.display_name}#{message.author.discriminator}", icon_url = message.author.display_avatar.url)
    embed.set_footer(text = f"Author: {message.author.id} | Message ID: {message.id}")
    await channel.send(embed = embed)
    
    if message.attachments is []:
        return
    
    for i in message.attachments:
        if i.content_type.startswith("image"):
            # os.remove("image.png")
            await i.save("image.png")
            image_embed = discord.Embed(color=0xff470f, timestamp=datetime.datetime.now(), description=f"**Image sent by <@!{message.author.id}> deleted in <#{message.channel.id}>**")
            image_embed.set_author(name=f"{message.author.display_name}#{message.author.discriminator}", icon_url=message.author.display_avatar.url)
            image_embed.set_image(url="attachment://image.png")
            image_embed.set_footer(text=f"Author: {message.author.id} | Message ID: {message.id}")
            await channel.send(file=discord.File("image.png"), embed=image_embed)

@bot.event
async def on_message_edit(before, after):    
    if (before.author.bot) or (before.guild.id != pmam_guildid) or (before.content == after.content):
        return
    
    if len(before.content) > 1024: before.content = before.content[:995] + "\nMore than 1024 characters..."
    if len(after.content) > 1024: after.content = after.content[:995] + "\nMore than 1024 characters..."
    
    channel = bot.get_channel(pmam_channelid_logs)
    embed = discord.Embed(color=0x307dd5, timestamp=datetime.datetime.now(), description=f"**Message edited in <#{before.channel.id}>** [Jump to message]({after.jump_url})")
    embed.set_author(name=f"{before.author.display_name}", icon_url=before.author.display_avatar.url)
    embed.add_field(name="Before", value=before.content, inline=False)
    embed.add_field(name="After", value=after.content, inline=False)
    embed.set_footer(text=f"User ID: {before.author.id}")
    await channel.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or (not isinstance(message.channel, discord.DMChannel)) or (bot.get_guild(pmam_guildid).get_member(message.author.id) == None):
        return

    if message.author.id in bot.dm_cooldown.keys() and bot.dm_cooldown[message.author.id] > datetime.datetime.now().second:
        await message.channel.send(f"DM messaging is on cooldown for 15 seconds!")

    if bot.dm_cooldown.get(message.author.id): bot.dm_cooldown.pop(message.author.id)
    channel = bot.get_channel(pmam_channelid_modmail)
    embed = discord.Embed(color=0xff470f)
    embed.set_author(name=f"Author: {message.author.display_name}")
    embed.set_footer(text=f"User ID: {message.author.id}")
    embed.set_thumbnail(url=(message.author.display_avatar.url))
    embed.add_field(name="Message:", value=message.content, inline=False)
    
    bot.dm_cooldown[message.author.id] = datetime.datetime.now().second + 15
    await channel.send(embed=embed)    

@bot.command(aliases = ['id_check','check_id'])
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def _id_check(ctx, id = None):
    if id is None:
        id = ctx.author.id
        user = await bot.fetch_user(int(id))
    else:    
        try:
            user = await bot.fetch_user(int(id))
        except Exception:
            await ctx.send("An error has occured!")
    
    time = datetime.datetime.now(datetime.timezone.utc)
    account_time = user.created_at
    age = time - account_time
    if age.total_seconds() < 259200:
        embed = discord.Embed(title = "Account is less than 3 days old!",color=discord.Color.red())
        embed.add_field(name="User",value=f"{user.display_name}#{user.discriminator}", inline=False)
        embed.add_field(name="ID",value=user.id,inline=False)
        embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
        await ctx.send(embed=embed)
    else:
        embed = discord.Embed(title = "Account is more than 3 days old!",color=discord.Color.green())
        embed.add_field(name="User",value=f"{user.display_name}#{user.discriminator}", inline=False)
        embed.add_field(name="ID",value=user.id,inline=False)
        embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
        await ctx.send(embed=embed)

@bot.command()
async def membercount(ctx):
    embed = discord.Embed(color=0x307dd4,timestamp=datetime.datetime.now())
    embed.add_field(name="Members",value=ctx.guild.member_count)
    await ctx.send(embed=embed)

@bot.command()
@commands.has_permissions(ban_members=True)
async def ban(ctx, user):
    try:
        if user.startswith("<"):
            user = await bot.fetch_user(int(user[2:-1]))
        else:
            user = await bot.fetch_user(user)
        await ctx.guild.ban(user)
        embed = discord.Embed(color=discord.Color.green(),description = f"<:vote_yes:975946668379889684> ***{user.display_name}#{user.discriminator} was banned***")
        await ctx.send(embed = embed)
    except:
        embed = discord.Embed(color=discord.Color.red(),description = "<:vote_no:975946731202183230> ***Invalid ID/user!***")
        await ctx.send(embed = embed)

def important_message(message):
    return ("instructions on how to verify" not in message.content)

@bot.command() #! REWORK
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def purge(ctx,number):
    channel = bot.get_channel(pmam_channelid_logs)
    try:
        number = int(number)
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
    except Exception as e:
        log(e, 2)
        await ctx.send("Please provide a number!")


@bot.hybrid_command()
@commands.bot_has_role(pmam_roleid_robot)
async def verify(ctx):
    time = datetime.datetime.now(datetime.timezone.utc)
    account_time = ctx.author.created_at
    age = time - account_time
    channel = bot.get_channel(pmam_channelid_logs)
    with open("./locked_ids.txt","r") as f:
        banned_ids = f.read()
        if str(ctx.author.id) in banned_ids:
            await ctx.send("The moderator team has blocked you from using the verification commands! Please ping an online mod to sort thing out.")
        f.close()
            
    if age.days > 450:
        role = discord.utils.get(ctx.author.guild.roles, id = 894351178702397520)
        if role in ctx.author.roles:
            await ctx.send('You are already verified!')
        else:
            await ctx.send("Verification successful!")
            await asyncio.sleep(1)
            await ctx.author.add_roles(role)
            await asyncio.sleep(1)
            await ctx.channel.purge(limit = 2)
    else:
        await ctx.send("Since your account is rather new you will need to connect your Steam account and then ping any online moderator.")
        embed = discord.Embed(title = "`?verify` command failed!", color=discord.Color.red())
        embed.add_field(name="User", value=f"{ctx.author.display_name}#{ctx.author.discriminator}", inline=False)
        embed.add_field(name="ID", value=ctx.author.id, inline=False)
        embed.set_thumbnail(url=ctx.author.display_avatar.url)
        await channel.send(embed=embed)

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
async def lockverify(ctx,user):
    try:
        if user.startswith("<"):
            user = await bot.fetch_user(int(user[2:-1]))
        else:
            user = await bot.fetch_user(user)
    except:
        await ctx.send("Invalid ID/user!")
        
    with open("locked_ids.txt","r+") as f:
        if str(user.id) not in f.read():
            f.write(f'{user.id}\n')
            await ctx.send("User blocked from verification!")
        else:
            await ctx.send("This user is already blocked!")

@bot.command()
async def search(ctx,*, word:str):
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
    
@bot.command()
async def mutual_friends(ctx, link1, link2):
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
        await ctx.send("An error occured!")
        log(e, 2)

@bot.command()
@commands.has_permissions(ban_members=True)
@commands.bot_has_role(pmam_roleid_robot)
async def mass_id_check(ctx):
    channel = bot.get_channel(pmam_channelid_logs)
    em1 = discord.Embed(title = "`?mass_id_check` command used!",color=discord.Color.green())
    await channel.send(embed=em1)
    for i in bot.guilds[0].humans:
        if len(i.roles) == 1:
            time = datetime.datetime.now(datetime.timezone.utc)
            account_time = i.created_at
            age = time - account_time
            embed = discord.Embed(title = f"{i.name}#{i.discriminator}",color=discord.Color.blue())
            embed.add_field(name="ID",value=i.id,inline=False)
            embed.add_field(name="Created at: ", value = f"`{str(account_time)[:-7]}` ({str(age)[:-7]} ago)")
            await channel.send(embed = embed)
            
@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
async def selfroles(ctx):
    value2 = []
    with open ("./selfroles.txt", "r") as f:
        embed = discord.Embed(title = "Selfroles",color = discord.Color.dark_blue())
        value = str(f.read()).split()
        log(value)
        for i in value:
            try:
                value2.append(discord.utils.get(ctx.author.guild.roles, id = int(i)).name)
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
async def _selfrole_add(ctx,*,role_name:str):
    try:
        role = discord.utils.get(ctx.guild.roles, name= role_name)
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
async def _selfrole_remove(ctx,*,role_name:str):
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
        
@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
async def iam(ctx,*,role_name:str):
    try:
        role = discord.utils.get(ctx.guild.roles, name= role_name)
        with open("selfroles.txt", "r") as f:
            if str(role.id) in f.read():
                if role not in ctx.author.roles:
                    await ctx.author.add_roles(role)
                    await ctx.send("Selfrole added!")
                else:
                    await ctx.send("You already have this role")
            else:
                await ctx.send("You can't get this role!")
                
    except:
        await ctx.send("Invalid role name!")

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
async def iamnot(ctx,*,role_name:str):
    try:
        role = discord.utils.get(ctx.guild.roles, name= role_name)
        with open("selfroles.txt", "r") as f:
            if str(role.id) in f.read():
                if role in ctx.author.roles:
                    await ctx.author.remove_roles(role)
                    await ctx.send("Selfrole removed!")
                else:
                    await ctx.send("You don't have this role")
            else:
                await ctx.send("You can't remove this role!")
                
    except:
        await ctx.send("Invalid role name!")

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
@commands.has_permissions(ban_members=True)
async def chocolate(ctx, user):
    try:
        if user.startswith("<"):
            user = await bot.fetch_user(int(user[2:-1]))
        else:
            user = await bot.fetch_user(user)
    except:
        await ctx.send("Invalid ID/user!")
        return
    await ctx.send(f"{user.mention} has been given one chocolate bar :chocolate_bar:")

@bot.hybrid_command()
async def ping(ctx: commands.Context):
    """Pings the bot"""

    ping_embed = discord.Embed(
        title="Pong!",
        description=f'**Latency: {round((bot.latency * 1000), 2)} ms**',
        colour=discord.Colour.brand_green())
    ping_thumbnail = discord.File(f"{os.getcwd() + os.sep}Images{os.sep}ping_pong.png", filename="ping_thumbnail.png")
    ping_embed.set_thumbnail(url="attachment://ping_thumbnail.png")
    await ctx.send(file=ping_thumbnail, embed=ping_embed)

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
@commands.has_permissions(ban_members=True)
async def restart(ctx: commands.Context):
    """Manually restart the bot."""

    log("Manually restarting the bot!", 1)
    await ctx.send("Restarting, good bye!")
    await bot.close()

@bot.command()
@commands.bot_has_role(pmam_roleid_robot)
@commands.has_permissions(ban_members=True)
async def reply(ctx: commands.Context, userid: discord.Member, message: str):
    """Anomalously replies to a select user.

    Args:
        ctx (commands.Context): Command context.
        userid (discord.Member): The Member/User to target.
    """
    reply_user = await bot.get_user(userid)
    await bot.send_message(reply_user, "Hello!")

setup_logging(os.getcwd())
bot.run(token, log_handler=None, root_logger=True)
