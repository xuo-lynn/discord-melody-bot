import asyncio
from ntpath import join
import sys
from unittest import result
import youtube_dl
import pafy
import discord
from discord.ext import commands

if sys.version_info[0] == 3 and sys.version_info[1] >= 8 and sys.platform.startswith('win'):
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

intents = discord.Intents.default()
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user.name} is ready.")


class Player(commands.Cog):
    def __init__(self, bot):
        self.bot = bot 
        self.song_queue = {}
        self.avatar_queue = {}
        self.name_queue = {}

        self.setup()

    def setup(self):
        for guild in self.bot.guilds:
            self.song_queue[guild.id] = []
            self.avatar_queue[guild.id] = []
            self.name_queue[guild.id] = []
    
    global user

    async def play_song(self, ctx, song):
        url = pafy.new(song).getbestaudio().url
        ctx.voice_client.play(discord.PCMVolumeTransformer(discord.FFmpegPCMAudio(url)), after=lambda error: self.bot.loop.create_task(self.check_queue(ctx)))
        ctx.voice_client.source.volume = 0.5

    async def check_queue(self, ctx):
        if len(self.song_queue[ctx.guild.id]) > 0:
            await self.play_song(ctx, self.song_queue[ctx.guild.id][0])
            title = pafy.new(self.song_queue[ctx.guild.id][0]).title
            embed = discord.Embed(title="Now Playing", description=title, color=0xf8c8dc)
            embed.set_author(name=f"{self.name_queue[ctx.guild.id][0]}", icon_url= self.avatar_queue[ctx.guild.id][0])
            embed.set_thumbnail(url=pafy.new(self.song_queue[ctx.guild.id][0]).bigthumbhd)
            embed.set_footer(text=f"Duration: {pafy.new(self.song_queue[ctx.guild.id][0]).duration}")
            self.song_queue[ctx.guild.id].pop(0)
            self.avatar_queue[ctx.guild.id].pop(0)
            self.name_queue[ctx.guild.id].pop(0)
            await ctx.send(embed=embed)
            

    async def search_song(self, amount, song, get_url=False):
        info = await self.bot.loop.run_in_executor(None, lambda: youtube_dl.YoutubeDL({"format" : "bestaudio", "quiet" : True}).extract_info(f"ytsearch{amount}:{song}", download=False, ie_key="YoutubeSearch"))
        if len(info["entries"]) == 0: return None

        return [entry["webpage_url"] for entry in info["entries"]] if get_url else info

    @commands.command()
    async def join(self, ctx):
        if ctx.author.voice is None:
            return await ctx.send("**Please join a voice channel first.**")

        if ctx.voice_client is not None:
            await ctx.voice_client.disconnect()

        await ctx.author.voice.channel.connect()

    @commands.command()
    async def stop(self, ctx):
        if ctx.voice_client is not None:
            return await ctx.voice_client.disconnect()

        await ctx.send("**I am not connected to a voice channel.**")

    @commands.command(name="play")
    async def play(self, ctx, *, song=None):
        if song is None:
            return await ctx.send("**You must include a song to play.**")

        if ctx.voice_client is None:
             await ctx.invoke(self.bot.get_command('join'))

        # handle song where song isn't url
        if not ("youtube.com/watch?" in song or "https://youtu.be/" in song):
            await ctx.send("**Searching for Song...**")

            global result
            result = await self.search_song(1, song, get_url=True)

            if result is None:
                return await ctx.send("**Sorry, I could not find the given song, try using my search command.**")

            song = result[0]

        if ctx.voice_client.source is not None:
            queue_len = len(self.song_queue[ctx.guild.id])
            if ctx.voice_client.is_playing():
                if queue_len < 10:
                    self.song_queue[ctx.guild.id].append(song)
                    self.avatar_queue[ctx.guild.id].append(ctx.author.avatar_url)
                    self.name_queue[ctx.guild.id].append(ctx.author.name)
                    title = pafy.new(song).title
                    thumbnail = pafy.new(song).bigthumbhd
                    embed = discord.Embed(title=f"Position in queue: {queue_len+1}",description= title, color=0x0096FF)
                    embed.set_author(name=f"{ctx.author.name} added to queue", icon_url=ctx.author.avatar_url)
                    embed.set_thumbnail(url=thumbnail)
                    await ctx.send(embed=embed)

                else:
                    return await ctx.send("**Sorry, I can only queue up to 10 songs, please wait for the current song to finish.**")

        await self.play_song(ctx, song)
        user = ctx.message.author.name
        title = pafy.new(song).title
        thumbnail = pafy.new(song).bigthumbhd
        embed = discord.Embed(title="Now Playing", description=title, color=0xf8c8dc)
        embed.set_thumbnail(url=thumbnail)
        embed.set_author(name=f"{user}", icon_url=ctx.author.avatar_url)
        embed.set_footer(text=f"Duration: {pafy.new(song).duration}")
        await ctx.send(embed=embed)

    #@commands.command(name="np")
    #async def now_playing(self, ctx):
     #   if ctx.voice_client is None:
     #       return await ctx.send("**I am not connected to a voice channel.**")

     #   if ctx.voice_client.source is None:
     #       return await ctx.send("**I am not playing anything.**")

        #if ctx.voice_client.source is not None:
            
             
    
    @commands.command()
    async def search(self, ctx, *, song=None):
        if song is None: return await ctx.send("**You forgot to include a song to search for.**")

        await ctx.send("**Searching for song, this may take a few seconds.**")

        info = await self.search_song(5, song)

        embed = discord.Embed(title=f"Results for '{song}':", description="**You can use these URL's to play an exact song if the one you want isn't the first result.**\n", colour=discord.Colour.red())
        
        amount = 0
        for entry in info["entries"]:
            embed.description += f"[{entry['title']}]({entry['webpage_url']})\n"
            amount += 1

        embed.set_footer(text=f"Displaying the first {amount} results.")
        await ctx.send(embed=embed)

    @commands.command()
    async def queue(self, ctx): # display the current guilds queue
        if len(self.song_queue[ctx.guild.id]) == 0:
            return await ctx.send("**There are currently no songs in the queue.**")

        embed = discord.Embed(title="Song Queue", description="", colour=discord.Colour.greyple())
        i = 1
        for url in self.song_queue[ctx.guild.id]:
            url = pafy.new(url).title
            embed.description += f"{i}. {url}\n"

            i += 1
            
        await ctx.send(embed=embed)

    @commands.command()
    async def skip(self, ctx):
        owner_id = 212702039103373312
        role = discord.utils.find(lambda r: r.name == 'DJ', ctx.message.guild.roles)

        if role in ctx.author.roles or ctx.author.id == owner_id and len(self.song_queue[ctx.guild.id]) > 0:
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
    async def clear(self, ctx): # display the current guilds queue
        if len(self.song_queue[ctx.guild.id]) == 0:
            return await ctx.send("**There are currently no songs in the queue to clear.**")
        else:
            self.song_queue[ctx.guild.id] = []
            self.name_queue[ctx.guild.id] = []
            self.avatar_queue[ctx.guild.id] = []
            await ctx.send("**Queue cleared!**")
            


async def setup():
    await bot.wait_until_ready()
    bot.add_cog(Player(bot))

bot.loop.create_task(setup())
bot.run("")



