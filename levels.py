from io import BytesIO
import discord, sqlite3, requests, datetime, typing
from discord.ext import commands, tasks
from PIL import Image, ImageFont, ImageDraw

from logger import log

pmam_guildid: int = 830239808596606976 #originally 969790418394964019
pmam_roleid_robot: int = 830240292183212042
pmam_categorychannel_staff: int = 830243658204184617

exp_channels = [ # Individual channels which allow users to earn exp, any channel not listed here, except for the mod channels, will not allow users to earn EXP
    1047272745106423838,    # "off-topic-showcasing"
    830243614382227498,     # "help-modding"
    830243415009918996,     # "help-mapping"
    1136502439504252938,    # "help-puzzles"
    830243544269717555,     # "help-assets"
    941813875538538627,     # "playtesting"
    830518892786876489,     # "showcasing"
    922653836626243654,     # "finished-map-links"
    930548541607280731      # "tips"
] 

font_colors = {"0": (143, 143, 143), "1": (172, 161, 144), "2": (175, 147, 108), "3": (164, 122, 102), "4": (185, 93, 81) ,"5": (193, 66, 66)} #font colors for card generation
font = ImageFont.truetype("DIN-Bold.ttf", 102)
font2 = ImageFont.truetype("DIN-Medium.ttf", 51)
font3 = ImageFont.truetype("DIN-Bold.ttf", 69)
level_roles_ids = [894351178702397520, 1261327532934959186, 1261328505367695360, 1261329668561178756, 1261330263099707503, 1261330725010149486] #originally [1261326357002981386, 1261326272181698661, 1261326153629831249, 1261326092631933018, 1261325982749692026, 1261325887295717409]

def add_exp(user, amount):

    connection = sqlite3.connect("database.db")
    cursor = connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = ?;", (user, ))
    connection.commit()

    if cursor.fetchall() == []:
        cursor.execute(f"INSERT INTO users VALUES (?, ?);", (user, amount))
        connection.commit()
    else:
        cursor.execute(f"UPDATE users SET exp = exp + ? WHERE id = ?;", (amount, user))
        connection.commit()

    connection.close()

def generate_card(user_object, acc_level:str, rank:int, exp:int):

    #pasting user profile
    profile = Image.open(BytesIO(requests.get(user_object.display_avatar.url).content))
    profile = profile.resize((645, 645))

    base_image = Image.open(f'./card_templates/level_{acc_level}.png')
    base_image.paste(profile, (82, 178))

    drawable = ImageDraw.Draw(base_image)

    try:
        drawable.text((833, 177), user_object.global_name, font_colors[acc_level], font) #Username
    except Exception:
        drawable.text((833, 177), user_object.name, font_colors[acc_level], font)
    drawable.text((870, 273), user_object.name, (41, 41, 41), font2) #user mention
    drawable.text((98, 895), str(rank), (41, 41, 41), font3) #ranking
    drawable.text((630, 966), str(exp), (41, 41, 41), font3, "rs") #exp

    base_image.save("card.png")

def intersection(list1, list2): #intersection of 2 lists, returns only one item
    return [i for i in list1 if i in list2][0]

class leveling_system(commands.Cog):

    def __init__(self, bot):
        self.bot = bot
        self.cooldowns = {} # EXP user cooldown list

    @commands.Cog.listener()
    async def on_message(self, message):
        if isinstance(message.channel, discord.DMChannel):
            return

        if (message.guild.id != pmam_guildid) or (message.author.bot) or ((message.channel.id not in exp_channels) and (message.channel.category_id != pmam_categorychannel_staff)):
            return

        if message.author.id not in self.cooldowns.keys():
            self.cooldowns[message.author.id] = datetime.datetime.timestamp(datetime.datetime.now())
        
        if self.cooldowns[message.author.id] < datetime.datetime.timestamp(datetime.datetime.now()):
            #! Reuse this function for future EXP timeout
            # if (message.author.id == int(os.getenv('THE_ID'))):
            #     if len(message.content.split()) > 20:
            #         add_exp(message.author.id, round(0.2), 1)
            #     else:
            #         add_exp(message.author.id, round(0.1, 1))
            #     self.cooldowns[message.author.id] = datetime.datetime.timestamp(datetime.datetime.now()) + 50 #50 seconds cooldown
            #     return

            if len(message.content.split()) > 20:
                add_exp(message.author.id, 2)
            else:
                add_exp(message.author.id, 1)
            self.cooldowns[message.author.id] = datetime.datetime.timestamp(datetime.datetime.now()) + 15 #15 seconds cooldown 
   
    @commands.command()
    @commands.has_permissions(kick_members=True)
    @commands.bot_has_role(pmam_roleid_robot)
    async def addexp(self, ctx: commands.Context, user: discord.Member, amount: int):
        if ctx.guild.fetch_member(user.id) == None:
            await ctx.send("Invalid ID/user!", delete_after=3)
            return
        
        try:
            add_exp(user.id, amount)
            embed = discord.Embed(color=discord.Color.green(), description="<:vote_yes:975946668379889684> ***Successfully added EXP!***") 
        except Exception as e:
            log(f"The command 'addexp' failed to execute. Below is the error that occurred:\n\n{e}", 2)
            embed = discord.Embed(color=discord.Color.red(), description=f"<:vote_no:975946731202183230> ***Adding EXP failed! ***\n\n***ERROR:***\n```{e}```")
            raise e
        
        await ctx.send(embed=embed)
    
    @commands.hybrid_command()
    @commands.bot_has_role(pmam_roleid_robot)
    @commands.cooldown(1, 5)
    async def exp(self, ctx: commands.Context, user: typing.Union[discord.Member, int] = None):
        # Tell the interaction ahead of time that it received the prompt so it doesn't timeout
        await ctx.defer()

        if not isinstance(user, discord.Member):
            user = ctx.author

        if (ctx.guild.fetch_member(user.id) and user) == None:
            embed = discord.Embed(color=discord.Color.red(), description="<:vote_no:975946731202183230> ***Invalid ID/user!***")
            await ctx.send(embed=embed)
            return
        
        #read from database
        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = ?", (user.id, ))
        connection.commit()

        result = cursor.fetchone()

        if result == None: #user is not in database
            embed = discord.Embed(color=discord.Color.red(), description=f"<:vote_no:975946731202183230> ***`{user.name}` doesn't have any EXP***")
            await ctx.send(embed=embed)
            return
        
        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()
        cursor.execute("SELECT row_number FROM (SELECT ROW_NUMBER () OVER ( ORDER BY exp DESC ) row_number, id, exp FROM users) WHERE id = ?;",(user, )) #this actually calculates the position of user in the leaderboard
        connection.commit()
        rank = cursor.fetchone()[0]
        connection.close()

        try:
            #await ctx.send(f"user {user} has {result[1]} EXP. Position: {rank}{user.name}{user.nick}{user.display_name}")

            #yes I know this isn't great thing to do, but I want my code to be readable for future me/future The Watcher maintainer
            if result[1] < 100: #control group
                if level_roles_ids[0] not in (user_roles_ids := [i.id for i in user.roles]): 
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids)))
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[0]))
                generate_card(user, "0", rank, result[1])
            
            elif result[1] < 1000: #test subject
                if level_roles_ids[1] not in (user_roles_ids := [i.id for i in user.roles]): #this if statement promotes user to next access level
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids)))
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[1]))
                generate_card(user, "1", rank, result[1])
            
            elif result[1] < 5000: #testing bot
                if level_roles_ids[2] not in (user_roles_ids := [i.id for i in user.roles]):
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids))) #removing "old" roles and adding role that corresponds to EXP level
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[2]))
                generate_card(user, "2", rank, result[1])
            
            elif result[1] < 10000: #military android
                if level_roles_ids[3] not in (user_roles_ids := [i.id for i in user.roles]):
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids)))
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[3]))
                generate_card(user, "3", rank, result[1])
            
            elif result[1] < 70000: #scientist
                if level_roles_ids[4] not in (user_roles_ids := [i.id for i in user.roles]):
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids)))
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[4]))
                generate_card(user, "4", rank, result[1])
            
            else: #no life user
                if level_roles_ids[5] not in (user_roles_ids := [i.id for i in user.roles]):
                    await user.remove_roles(ctx.guild.get_role(intersection(user_roles_ids, level_roles_ids)))
                    await user.add_roles(ctx.guild.get_role(level_roles_ids[5]))
                generate_card(user, "5", rank, result[1])

            await ctx.send(file = discord.File("card.png"))
        except Exception as e:
            log(f"Failed to generate EXP card: {e}", 2)
            embed = discord.Embed(color=discord.Color.red(), description="<:vote_no:975946731202183230> ***Failed to generate EXP card!***")
            await ctx.send(embed=embed)
            raise e

    @commands.hybrid_command()
    @commands.bot_has_role(pmam_roleid_robot)
    @commands.cooldown(1, 5)
    async def leaderboard(self, ctx: commands.Context):
        # Tell the interaction ahead of time that it received the prompt so it doesn't timeout
        await ctx.defer()

        connection = sqlite3.connect("database.db")
        cursor = connection.cursor()
        cursor.execute("SELECT * FROM users ORDER BY exp DESC")
        connection.commit()
        rank = 1

        base_embed = discord.Embed(title="PMaM Leaderboard", color=0xf9f02a)
        for i in cursor.fetchmany(10):
            try:
                user = await ctx.guild.fetch_member(i[0])
                username = user.global_name
            except Exception:
                username = str(i[0])
            base_embed.add_field(name=f"#{rank} {username}", value=f"{i[1]} EXP", inline=False)
            rank+=1
        
        try:
            cursor.execute("SELECT row_number FROM (SELECT ROW_NUMBER () OVER ( ORDER BY exp DESC ) row_number, id, exp FROM users) WHERE id = ?;",(ctx.author.id, )) #this actually calculates the position of user in the leaderboard
            connection.commit()
            rank = cursor.fetchone()[0]
        except Exception:
            rank = "you found super secret error!"
        
        connection.close()
        
        thumbnail = discord.File("images/pmamlogo.png", "pmamlogo.png") #pmam icon
        base_embed.set_thumbnail(url="attachment://pmamlogo.png") 
        base_embed.set_footer(text=f"Your position in ranking: {rank}", icon_url="attachment://pmamlogo.png")
        await ctx.send(file=thumbnail, embed=base_embed)
        
async def setup(bot):
    await bot.add_cog(leveling_system(bot))
