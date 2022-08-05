import asyncio
from ntpath import join
import sys
from unittest import result
import youtube_dl
import pafy
import discord
import aiohttp
from discord.ext import commands


if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="?", intents=intents)
bot.remove_command('help')


@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")
    listening_activity = discord.Activity(type=discord.ActivityType.listening, name="!help")
    await bot.change_presence(activity=listening_activity) 


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.song_queue = {}
        self.avatar_queue = {}
        self.name_queue = {}
        self.current_track = {}
    
        self.setup()

    def setup(self):
        for guild in self.bot.guilds:
            self.song_queue[guild.id] = []
            self.avatar_queue[guild.id] = []
            self.name_queue[guild.id] = []
            self.current_track = {}
    
    global user #i forgot what this affects but im just gonna leave it here

    async def play_song(self, ctx, song):
        url = pafy.new(song).getbestaudio().url
        ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url)), after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
        ctx.voice_client.source.volume = 0.5

    async def check_queue(self, ctx): #plays next song in queue

        if len(self.song_queue[ctx.guild.id]) > 0:
            async with ctx.typing():
                await self.play_song(ctx, self.song_queue[ctx.guild.id][0])
            title = pafy.new(self.song_queue[ctx.guild.id][0]).title
            embed = discord.Embed(title="Now Playing", description=f"[{title}]({self.song_queue[ctx.guild.id][0]})", color=0xf8c8dc)
            embed.set_author(name=f"{self.name_queue[ctx.guild.id][0]}", icon_url= self.avatar_queue[ctx.guild.id][0])
            embed.set_thumbnail(url=pafy.new(self.song_queue[ctx.guild.id][0]).getbestthumb())
            embed.set_footer(text=f"Duration: {pafy.new(self.song_queue[ctx.guild.id][0]).duration}")
            self.song_queue[ctx.guild.id].pop(0)
            self.avatar_queue[ctx.guild.id].pop(0)
            self.name_queue[ctx.guild.id].pop(0)
            await ctx.send(embed=embed)


    @commands.Cog.listener()
    async def on_guild_join(self, guild):
        await guild.create_role(name="DJ", color=0xf8c8dc)
        embed = discord.Embed(title="Hi, I'm Melody!", description="**Thanks for inviting me!** \n Use !help to get started.", color=0xf8c8dc)
        embed.set_thumbnail(url="https://cdn.discordapp.com/attachments/644707361273020447/964421954918580294/85c5b108a94bfa15fe88342f38b42530.gif")
        embed.set_footer(text="Created by xuo#0009 🖤")
        return await guild.system_channel.send(embed=embed)

    @commands.Cog.listener() #auto disconnect after 5 minutes when no song is playing
    async def on_voice_state_update(self, member, before, after):   
    
        if not member.id == self.bot.user.id:
            return

        elif before.channel is None:
            voice = after.channel.guild.voice_client
            time = 0
            while True:
                await asyncio.sleep(1)
                time = time + 1
                if voice.is_playing() and not voice.is_paused():
                    time = 0
                if time == 300:
                    await voice.disconnect()
                if not voice.is_connected():
                    break
        

            

    async def search_song(self, amount, song, get_url=False): #searhes youtube for song
        info = await self.bot.loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL({"format" : "bestaudio", "quiet" : True}).extract_info(f"ytsearch{amount}:{song}", download=False, ie_key="YoutubeSearch"))
        if len(info["entries"]) == 0: return None

        return [entry["webpage_url"] for entry in info["entries"]] if get_url else info
    
    @commands.command() #help command
    async def help(self,ctx): 
        embed = discord.Embed(title="**Melody Commands**", description= "", color=0xf8c8dc)
        embed.add_field(name="!play", value="Plays song from Youtube", inline=False)
        embed.add_field(name="!pop", value="Removes song from queue", inline=False)
        embed.add_field(name="!search", value="Searches for song on Youtube", inline=False)
        embed.add_field(name="!skip", value="Skips the current song \n (Assign role 'DJ' to allow users to forceskip)", inline=False)
        embed.add_field(name="!queue", value="Shows the current queue", inline=False)
        embed.add_field(name="!clear", value="Clears the current queue", inline=False)
        embed.add_field(name="!pause", value="Pauses the current song", inline=False)
        embed.add_field(name="!resume", value="Resumes the current song", inline=False)
        embed.add_field(name="!stop", value="Leaves the voice channel", inline=False)
        embed.add_field(name="!venmo", value="I am a humble person", inline=False)
        await ctx.send(embed=embed)

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice is None:
            return await ctx.send("**Please join a voice channel first.**")

        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

        await ctx.author.voice.channel.connect()


    @commands.command(name="play")
    async def play(self, ctx, *, song=None):
        if song is None:
            return await ctx.send("**You must include a song to play.**")

        if ctx.voice_client is None:
             await ctx.invoke(self.bot.get_command('join'))

        # handle song where song isn't url
        if not ("youtube.com/watch?" in song or "https://youtu.be/" in song):
            async with ctx.typing():
                

                global result
            result = await self.search_song(1, song, get_url=True)

            if result is None:
                return await ctx.send("**Sorry, I could not find the given song, try using my search command.**")

            song = result[0] 
            

        if ctx.voice_client.source is not None: #adds to queue if song is already playing
            queue_len = len(self.song_queue[ctx.guild.id])
            if ctx.voice_client.is_playing():
                if queue_len < 10:
                    self.song_queue[ctx.guild.id].append(song)
                    self.avatar_queue[ctx.guild.id].append(ctx.author.avatar_url)
                    self.name_queue[ctx.guild.id].append(ctx.author.name)
                    title = pafy.new(song).title
                    thumbnail = pafy.new(song).getbestthumb()
                    embed = discord.Embed(title=f"Position in queue: {queue_len+1}",description= f"[{title}]({song})", color=0x0096FF)
                    embed.set_author(name=f"{ctx.author.name} added to queue", icon_url=ctx.author.avatar_url)
                    embed.set_thumbnail(url=thumbnail)
                    await ctx.send(embed=embed)

                else:
                    return await ctx.send("**Sorry, I can only queue up to 10 songs, please wait for the current song to finish.**")

        await self.play_song(ctx, song) #involes player 
        user = ctx.message.author.name
        title = pafy.new(song).title
        thumbnail = pafy.new(song).getbestthumb()
        embed = discord.Embed(title="Now Playing", description=f"[{title}]({song})", color=0xf8c8dc)
        embed.set_thumbnail(url=thumbnail)
        embed.set_author(name=f"{user}", icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"Duration: {pafy.new(song).duration}")
        await ctx.send(embed=embed)
        

    @commands.command(name="np") #now_playing command (bugged doesn't work properly)
    async def now_playing(self, ctx):
        if ctx.voice_client is None:
            return await ctx.send("**I am not connected to a voice channel.**")

        if ctx.voice_client.source is None:
            return await ctx.send("**I am not playing anything.**")

        current = pafy.new(result).title
        await ctx.send(current)
                    
             
    
    @commands.command() #searches song on youtube
    async def search(self, ctx, *, song=None):
        if song is None: return await ctx.send("**You forgot to include a song to search for.**")

        async with ctx.typing():
            info = await self.search_song(5, song)

        embed = discord.Embed(title=f"Results for '{song}'", description="**You can use these URL's to play an exact song if the one you want isn't the first result.**\n\n", color=0xf8c8dc)
        
        amount = 0
        for entry in info["entries"]:
            embed.description += f"• [{entry['title']}]({entry['webpage_url']})\n"
            amount += 1

        embed.set_footer(text=f"Displaying top {amount} results.")
        await ctx.send(embed=embed)

    @commands.command() #displays queue
    async def queue(self, ctx):
        async with ctx.typing():
            if len(self.song_queue[ctx.guild.id]) == 0:
                return await ctx.send("**There are currently no songs in the queue.**")

        embed = discord.Embed(title="Song Queue", description="", colour=discord.Colour.greyple())
        i = 1
        for url in self.song_queue[ctx.guild.id]:
            title = pafy.new(url).title
            embed.description += f"{i}. [{title}]({url})\n"

            i += 1
            
        await ctx.send(embed=embed)

    @commands.command(name="pop") #pops [index] from queue
    async def queue_remove(self, ctx, *, index=None):
        if len(self.song_queue[ctx.guild.id]) == 0:
            await ctx.send("**There are currently no songs in the queue.**")

        if index is None: return await ctx.send("**Please include the queue number you would like removed.**")

        
        pop = discord.Embed(title="", description=f"{index}. {pafy.new(self.song_queue[ctx.guild.id][0]).title}", colour=discord.Colour.red())
        pop.set_author(name=f"{ctx.author.name} removed from queue", icon_url=ctx.author.avatar_url)
        self.song_queue[ctx.guild.id].pop(int(index)-1)
        self.avatar_queue[ctx.guild.id].pop(int(index)-1)
        self.name_queue[ctx.guild.id].pop(int(index)-1)
        return await ctx.send(embed=pop)


        
        
    

    @commands.command() 
    async def skip(self, ctx): #skips song if user is 'DJ' or 'Admin' or 'xuo'
        owner_id = 212702039103373312 # xuo#9999        
        
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)

        if role in ctx.author.roles or ctx.author.id == owner_id or ctx.author.guild_permissions.administrator and len(self.song_queue[ctx.guild.id]) > 0: #skips song if DJ or owner of bot
            skip = True
            ctx.voice_client.stop()
           # title = pafy.new(self.song_queue[ctx.guild.id][0]).title
           # thumbnail = pafy.new(self.song_queue[ctx.guild.id][0]).bigthumbhd
            embed = discord.Embed(color=0xf8c8dc)
            embed.set_author(name=f"{ctx.author.name} has skipped the song", icon_url=ctx.author.avatar_url)
           # embed.set_thumbnail(url=thumbnail)
            
            return await ctx.send(embed=embed)

        if len(self.song_queue[ctx.guild.id]) == 0:
            return await ctx.send("**There are no more songs queued.**")

        if ctx.voice_client is None:
            return await ctx.send("*I am not playing any song.*")

        if ctx.author.voice is None:
            return await ctx.send("**You are not connected to any voice channel.**")

        if ctx.author.voice.channel.id != ctx.voice_client.channel.id:
            return await ctx.send("**I am not currently playing any songs for you.**")

        #vote to skip functionality
        poll = discord.Embed(description="**70% of the voice channel must vote to skip for it to pass.**", colour=discord.Colour.green()) 
        poll.set_author(name=f"{ctx.author.name} has voted to skip the song", icon_url=ctx.author.avatar_url)
        poll.add_field(name="Skip", value=":white_check_mark:")
        poll.add_field(name="Don't Skip", value=":no_entry_sign:")
        poll.set_footer(text="Voting ends in 10 seconds.")

        poll_msg = await ctx.send(embed=poll) # only returns temporary message, need to get the cached message to get the reactions
        poll_id = poll_msg.id

        await poll_msg.add_reaction(u"\u2705") # yes
        await poll_msg.add_reaction(u"\U0001F6AB") # no
        
        await asyncio.sleep(10) # 10 seconds to vote

        poll_msg = await ctx.channel.fetch_message(poll_id)
        
        votes = {u"\u2705": 0, u"\U0001F6AB": 0}
        reacted = []

        for reaction in poll_msg.reactions:
            if reaction.emoji in [u"\u2705", u"\U0001F6AB"]:
                async for user in reaction.users():
                    if user.voice.channel.id == ctx.voice_client.channel.id and user.id not in reacted and not user.bot:
                        votes[reaction.emoji] += 1

                        reacted.append(user.id)

        skip = False

            

        if votes[u"\u2705"] > 0:
            if votes[u"\U0001F6AB"] == 0 or votes[u"\u2705"] / (votes[u"\u2705"] + votes[u"\U0001F6AB"]) > 0.69: # 70% or higher
                skip = True
                #title = pafy.new(self.song_queue[ctx.guild.id][0]).title
                #thumbnail = pafy.new(self.song_queue[ctx.guild.id][0]).bigthumbhd
                embed = discord.Embed(title="Vote Skip Successful",colour=discord.Colour.green())
                #embed.set_thumbnail(url=thumbnail)

        if not skip:
            embed = discord.Embed(title="Skip Failed", description="**The vote requires at least 70% of users to vote to skip.**", colour=discord.Colour.red())

        await poll_msg.clear_reactions()
        await poll_msg.edit(embed=embed)

        if skip:
            ctx.voice_client.stop()

    @commands.command()
    async def pause(self, ctx):
        if ctx.voice_client.is_paused():
            return await ctx.send("**I am already paused.**")

        ctx.voice_client.pause()
        await ctx.send("**The current song has been paused.**")

    @commands.command()
    async def resume(self, ctx):
        if ctx.voice_client is None:
            return await ctx.send("**I am not connected to a voice channel.**")

        if not ctx.voice_client.is_paused():
            return await ctx.send("**I am already playing a song.**")
        
        ctx.voice_client.resume()
        await ctx.send("**The current song has been resumed.**")


    @commands.command()
    async def clear(self, ctx): #clears the queue
        if len(self.song_queue[ctx.guild.id]) == 0:
            return await ctx.send("**There are currently no songs in the queue to clear.**")
        else:
            self.song_queue[ctx.guild.id] = []
            self.name_queue[ctx.guild.id] = []
            self.avatar_queue[ctx.guild.id] = []
            await ctx.send("**Queue cleared!**")
            
    @commands.command()
    async def venmo(self,ctx):
        venmo = discord.Embed(title="Donations for bot hosting fees pls   <a:heartreceive:960379950760861736><a:heartsend:960380078158651423>",color=0xf8c8dc)
        venmo.description = "[@xuo__](https://account.venmo.com/u/xuo__ 'Venmo')" 
        venmo.set_image(url="https://cdn.discordapp.com/attachments/644707361273020447/962728466271334400/IMG_9155.png")
        await ctx.send(embed=venmo)

    @commands.command() #disconnects bot, clears queue
    async def stop(self, ctx):
        if ctx.voice_client is not None:
            self.song_queue[ctx.guild.id] = []
            self.name_queue[ctx.guild.id] = []
            self.avatar_queue[ctx.guild.id] = []
            return await ctx.voice_client.disconnect()

        await ctx.send("**I am not connected to a voice channel.**")
        


async def setup():
    await bot.wait_until_ready()
    bot.add_cog(Player(bot))

bot.loop.create_task(setup())
bot.run("")



