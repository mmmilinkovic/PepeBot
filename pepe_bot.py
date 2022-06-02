'''
PepeBot made by reyy

'''

import os
import json
import random
import asyncio
import psutil
import discord
from discord.ext import commands
from discord.utils import get
import yt_dlp
from youtubesearchpython.__future__ import VideosSearch # Needed to run youtubesearch in async
#from googleapiclient.discovery import build
#from urllib.parse import parse_qs, urlparse

# Sets the high process prio remove when testing on windows
#p = psutil.Process(os.getpid())
#p.nice(10)

TOKEN = '' # Setting bots token

bot = commands.Bot(command_prefix='=') # Setting bots command prefix

# Executes when bot is booted up (ready)
@bot.event
async def on_ready():
    print('Logged in as')
    print(bot.user.name)
    print(bot.user.id)
    print('------------')
    remove_song()
    clear_queues()
    global _guild
    global _v_channel_id
    global _v_channel
    global _t_channel
    _guild = bot.get_guild(902694643769176104) # PEPEBOT TEST SERVER
    _v_channel_id = 902957500406583336
    _v_channel = bot.get_channel(902957500406583336) # PEPEBOT TEST SERVER MUSIC VOICE CHANNEL
    _t_channel = bot.get_channel(902694643769176107) # PEPEBOT TEST SERVER general text channel

# In case someone uses command incorrectly the program doesnt stop
@bot.event
async def on_command_error(error, ctx):
    print('ERROR OCCURED')

# Test command
@bot.command()
async def hi(ctx):
    response = 'Hello ' + ctx.author.name
    await ctx.reply(response, mention_author=False)

# Join the bot in the voice channel where the person who typed the command in is
# If another person requests the bot it will not move unless someone requests the bot
# to leave first
@bot.command(aliases=['j'])
async def join(ctx):
    voice = ctx.author.voice
    if voice is None:
        await ctx.send('You are not in any voice channel...')
    else:
        try:
            remove_song()
            await voice.channel.connect()
        except:
            await ctx.send('im already in voice channel')

playlist_mode = False
song_queue = [] # Check if you can remove this !!
current_song_url = ''
current_song_title = ''
current_song_duration = '' # Used to determine if we need to wait since the queue data is currently being written to data.json
def start_playing(v_client, url, title, duration):
    def check_queue():
        print('Checking queue...')
        print('Looping ? ' + str(loop_queue))

        song_queue = get_song_queue()["queue"]
        loop_song_queue = get_song_queue()["loop_song_queue"]
        if len(song_queue["urls"]) != 0:
            next_song_url = song_queue["urls"].pop(0)
            next_song_title = song_queue["titles"].pop(0)
            next_song_duration = song_queue["durations"].pop(0)
            pop_queue()
            print('Playing next song')
            start_playing(v_client, next_song_url, next_song_title, next_song_duration)
        else:
            # If its the last song in queue loop the queue
            if loop_queue:
                print('Loop queue : ')
                print(loop_song_queue)
                song_queue = loop_song_queue.copy()
                print('new queue: ')
                print(song_queue)
                write_song_queue(song_queue)
                next_song_url = song_queue["urls"].pop(0)
                next_song_title = song_queue["titles"].pop(0)
                next_song_duration = song_queue["durations"].pop(0)

                pop_queue()
                start_playing(v_client, next_song_url, next_song_title, next_song_duration)
            else:
                print(loop_song_queue)
                global current_song_url
                current_song_url = ''
                remove_song()
                print('Queue empty, stopping...')

    global current_song_url
    global current_song_title
    global current_song_duration
    current_song_url = url
    current_song_title = title
    current_song_duration = duration
    remove_song()

    print('Current song : ' + current_song_title)
    # Setting parameters to download video from youtube in webm format
    ydl_opts = {
        'format': '249/250/251'
    }
    # Downloading a webm video from youtube
    with yt_dlp.YoutubeDL(ydl_opts, auto_init=True) as ydl:
        ydl.download([url])
    for file in os.listdir('./'):
        if file.endswith('webm'):
            os.rename(file, 'song.webm')

    v_client.play(discord.FFmpegOpusAudio('song.webm'), after=lambda e: check_queue())

# Makes the bot play a song or adds it to a queue if there is a song already playing
@bot.command(aliases=['p'])
async def play(ctx, *, search_key : str):
    global loop_queue
    global playlist_mode
    song_queue = get_song_queue()["queue"]
    voice = ctx.voice_client
    if voice is None:
        await ctx.send('Im not connected to voice channel')
        return

    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")
        return

    # In case link was provided make sure we get rid of any additional parameters
    if search_key.startswith("https:"):
        i = search_key.find('&')
        if i != -1:
            search_key = search_key[:i]

    info = await find_song(search_key)
    if info is None:
        await ctx.send("Can't find the song...try typing its name...")
        return
    print(info)
    url = info[0]
    title = info[1].encode("unicode-escape").decode("utf-8")
    duration = info[2]

    # Sends the message about the song title in the music text channel
    await ctx.send("Queued : " + title.encode("utf-8").decode("unicode-escape"))

    # Checks for the duration of song; if the song is longer than 10 hours and 15 mins don't play it
    if duration > 36900:
        await ctx.send('Song over 10hours and 15 mins...not playing...')
        return

    # Checks if there is already a downloaded song (yt video)
    song = os.path.isfile('song.webm')
    song_queue["urls"].append(url)
    song_queue["titles"].append(title)
    song_queue["durations"].append(duration)
    print("writing song queue")
    write_song_queue(song_queue)
    print("wrote song queue")
    if loop_queue:
        #loop_song_queue.append(url)

        add_loop_song_queue(url, title, duration)

    if song: # If song is getting ready to be played (downloading) put the next one in queue
        await ctx.send('Song added to queue')
    else:
        print("playing first song")
        start_playing(voice, song_queue["urls"].pop(0), song_queue["titles"].pop(0), song_queue["durations"].pop(0))

        pop_queue()

# Shows the current queue (10 songs per page (default: page 1))
@bot.command(aliases=['q'])
async def queue(ctx, x : int = 1):
    print('Checking queue')
    global loop_queue
    loop_song_queue = get_song_queue()["loop_song_queue"]
    song_queue = get_song_queue()["queue"]
    if loop_queue:
        print('loop queue list')
        msg = 'Current songs in loop queue :\n'
        print('Assembling queue')
        l = len(loop_song_queue["titles"])

        # Calculating total number of pages
        n = l
        if n % 10 == 0:
            n = int(n / 10)
        else:
            n = n // 10 + 1

        # Checking if entered number is valid
        if x <= 0 or x > n:
            await ctx.send("Invalid page number or empty queue !")
            return

        st = (x * 10) - 10 # Starting number
        end = x * 10 # Ending number
        if end > l:
            end = l

        try :
            for i in range(st, end):
                song_name = loop_song_queue["titles"][i].encode("utf-8").decode("unicode-escape")
                msg += str(i + 1) + '. ' + song_name + '\n'
        except:
            await ctx.send("Invalid")

        msg += "Page (" + str(x) + "/" + str(n) + ")"
        print('Done assembling')
        await ctx.send(msg)
    else:
        print('Non loop queue list')
        print('Assembling queue')
        if len(song_queue) != 0:
            msg = 'Current songs in queue :\n'
            l = len(song_queue["titles"])
            # Calculating total number of pages
            n = l
            if n % 10 == 0:
                n = int(n / 10)
            else:
                n = n // 10 + 1

            # Checking if entered number is valid
            if x <= 0 or x > n:
                await ctx.send("Invalid page number or empty queue !")
                return

            st = (x * 10) - 10 # Starting number
            end = x * 10 # Ending number
            if end > l:
                end = l

            try :
                for i in range(st, end):
                    song_name = song_queue["titles"][i].encode("utf-8").decode("unicode-escape")
                    msg += str(i + 1) + '. ' + song_name + '\n'
            except:
                await ctx.send("Invalid")

            msg += "Page (" + str(x) + "/" + str(n) + ")"
            print('Done assembling')
            await ctx.send(msg)

# Shuffles the songs in queue
@bot.command()
async def shuffle(ctx):
    global loop_queue
    loop_song_queue = get_song_queue()["loop_song_queue"]

    # Check if loop_queue is on
    if loop_queue:
        # Check if there are any songs in loop queue
        if len(loop_song_queue["titles"]) != 0 :
            seed = random.random() # Gets random number for seed

            random.seed(seed)
            random.shuffle(loop_song_queue["urls"])

            random.seed(seed)
            random.shuffle(loop_song_queue["titles"])

            random.seed(seed)
            random.shuffle(loop_song_queue["durations"])

            # Write shuffled queue to loop song queue and current song queue
            write_loop_song_queue(loop_song_queue)
            write_song_queue(loop_song_queue)

            voice = ctx.voice_client
            voice.stop()
            await ctx.send("Playing new shuffled loop queue...")
        else:
            await ctx.send("There are no songs in loop queue...")

    else:
        song_queue = get_song_queue()["queue"]
        print(song_queue)
        # Check if there are any songs in queue
        if len(song_queue["titles"]) != 0:
            seed = random.random() # Gets random number for seed
            print(song_queue)
            random.seed(seed)
            random.shuffle(song_queue["urls"])

            random.seed(seed)
            random.shuffle(song_queue["titles"])

            random.seed(seed)
            random.shuffle(song_queue["durations"])

            write_song_queue(song_queue)

            voice = ctx.voice_client
            voice.stop()
            await ctx.send("Playing new shuffled queue...")
        else:
            await ctx.send("There are no songs in queue...")


# Deletes song from queue (by using index of song in queue)
@bot.command(aliases=['del'])
async def delete(ctx, index : int):
    global loop_queue

    global playlist_mode
    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")

    song_queue = get_song_queue()["queue"]
    loop_song_queue = get_song_queue()["loop_song_queue"]
    index -= 1 # Array index compensation
    if (len(song_queue["urls"]) == 0) and (len(loop_song_queue["urls"]) == 0):
        return

    # REWORK THIS! CHEKCKING FOR INDEX!
    # Check if we need to delete song queue or loop song queue
    if loop_queue:
        try:
            del loop_song_queue["urls"][index]
            del loop_song_queue["titles"][index]
            del loop_song_queue["durations"][index]
        except:
            await ctx.send("Invalid song index...")

        write_loop_song_queue(loop_song_queue)
        if index >= 1:
            try:
                del song_queue["urls"][index - 1]
                del song_queue["titles"][index - 1]
                del song_queue["durations"][index - 1]
                write_song_queue(song_queue)
            except:
                await ctx.send("Invalid song index...")
    else:
        try:
            del song_queue["urls"][index]
            del song_queue["titles"][index]
            del song_queue["durations"][index]

            write_song_queue(song_queue)
        except:
            await ctx.send("Invalid song index...")

# Clears song queue or loop song queue depending if loop is turned on
@bot.command(aliases=['c'])
async def clear(ctx):
    global loop_queue
    global playlist_mode
    if loop_queue:
        clear_queues()
        playlist_mode = False
        loop_queue = False
    else:

        with open("data.json", "r") as file:
            data = json.loads(file.read())
        file.close()
        data["queue"] = {
            "urls" : [],
            "titles" : [],
            "durations" : []
        }
        with open("data.json", "w") as outfile:
            json.dump(data, outfile, ensure_ascii=False, indent=4)
        outfile.close()

    await ctx.send("Queue cleared...")



# Pauses the audio play
@bot.command()
async def pause(ctx):
    voice = ctx.voice_client
    if voice.is_playing():
        voice.pause()
    else:
        await ctx.send('No audio is currently playing')

# Stops the audio play
@bot.command()
async def stop(ctx):
    global loop_queue
    voice = ctx.voice_client
    # Clears queues
    clear_queues()
    loop_queue = False
    # Deactivates playlist mode
    global playlist_mode
    playlist_mode = False
    voice.stop()
    await asyncio.sleep(1) # It won't remove song if we dont wait 1 second here
    remove_song()
    await ctx.send('Stopped looping...')


# Resumes the audio play
@bot.command()
async def resume(ctx):
    voice = ctx.voice_client
    if voice.is_paused():
        voice.resume()
    else:
        await ctx.send('Audio is not paused')

loop_queue = False
# Loops the current queue
@bot.command()
async def loop(ctx):
    global loop_queue
    global current_song_url
    global current_song_title
    global current_song_duration
    song_queue = get_song_queue()["queue"]

    global playlist_mode
    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")
        return

    if loop_queue is False:
        loop_queue = True
        await ctx.send('Looping current queue')
        loop_song_queue = song_queue.copy()
        if current_song_url != '':  # In case loop is used before a song played/queued
            loop_song_queue["urls"].insert(0, current_song_url) # Inserts current song in the beggining of loop queue
            loop_song_queue["titles"].insert(0, current_song_title)
            loop_song_queue["durations"].insert(0, current_song_duration)

            write_loop_song_queue(loop_song_queue)
        print(loop_song_queue)
    else:
        loop_queue = False
        await ctx.send('Stopped looping')
        loop_song_queue = []

        write_loop_song_queue(loop_song_queue)

# Reverses the order of songs in song queue
@bot.command(aliases=['r'])
async def reverse(ctx):
    global loop_queue
    if loop_queue:
        loop_song_queue = get_song_queue()["loop_song_queue"]
        if (len(loop_song_queue) < 2):
            await ctx.send("Error / not enough songs in queue !")
            return
        loop_song_queue["urls"].reverse()
        loop_song_queue["titles"].reverse()
        loop_song_queue["durations"].reverse()
        write_loop_song_queue(loop_song_queue)
        write_song_queue(loop_song_queue)
        await ctx.send("Reversed current queue !")
    else:
        song_queue = get_song_queue()["song_queue"]
        if (len(song_queue) < 2):
            await ctx.send("Error / not enough songs in queue !")
            return
        song_queue["urls"].reverse()
        song_queue["titles"].reverse()
        song_queue["durations"].reverse()
        write_song_queue(song_queue)
        await ctx.send("Reversed current queue !")

# Skips to next song in queue
@bot.command(aliases=['s'])
async def skip(ctx):
    if len(song_queue) != 0:
        voice = ctx.voice_client
        voice.stop()
        await ctx.send("Skipped to next song")
        print('Skipping to next song')
    else:
        voice = ctx.voice_client
        voice.stop()
        await ctx.send("Skipped to next song")
        print('Can not skip, stopping...')

# Skips to specific song in queue based on song number in queue
@bot.command(aliases=['sto'])
async def skipto(ctx, x : int):
    # Checks if song is being played
    song = os.path.isfile("song.webm")
    if not song:
        await ctx.send("Song isn't being played...")
        return

    # Checks what needs to be updated
    global loop_queue
    voice = ctx.voice_client
    song_queue = get_song_queue()["queue"]
    print("got voice")
    if loop_queue:
        loop_song_queue = get_song_queue()["loop_song_queue"]
        if x < 1 or x > len(loop_song_queue["urls"]):
            await ctx.send("Error / Entered wrong number !")
            return
        song_queue["urls"] = loop_song_queue["urls"][x - 1:]
        song_queue["titles"] = loop_song_queue["titles"][x - 1:]
        song_queue["durations"] = loop_song_queue["durations"][x - 1:]
        write_song_queue(song_queue) # Updating song queue in data.json
        voice.stop() # Makes it stop current song and skip to next one
    else:
        print("GOT q")
        # Checks if the entered number is valid
        if x < 1 or x > len(song_queue["urls"]):
            await ctx.send("Error / Entered wrong number !")
            return
        print("Editing song queue")
        song_queue["urls"] = song_queue["urls"][x - 1:]
        song_queue["titles"]= song_queue["titles"][x - 1:]
        song_queue["durations"] = song_queue["durations"][x - 1:]
        write_song_queue(song_queue) # Updating song queue in data.json
        voice.stop() # Makes it stop current song and skip to next one

# Commands the bot to leave the voice channel it is currently in making it available
# to join in other voice channel in case anyone requests it
@bot.command()
async def leave(ctx):
    try:
        global loop_queue
        loop_queue = False
        clear_queues()
        print("cleared queues due to leave")
        voice = discord.utils.get(bot.voice_clients, guild=ctx.guild)
        voice.stop()
        print("Stopped due to leave")
        await voice.disconnect()
        print("Dissconnected due to leave")
        await asyncio.sleep(0.5) # Must have so the remove_song function proceeds without errors
        remove_song()
        print("Removed song due to leave")
        global playlist_mode
        playlist_mode = False
        print("Turned off playlist mode due to leave")
        await ctx.send('Leaving...')
    except:
        await ctx.send('wtf lmao')

# Sends the link of picture with all commands available
@bot.command()
async def cmds(ctx):
    await ctx.send("https://i.imgur.com/iRJX6k2.png")


# Automatic music playing system
# ------------------------------

_guild = bot.get_guild(902694643769176104) # PEPEBOT TEST SERVER
_v_channel_id = 902957500406583336
_v_channel = bot.get_channel(902957500406583336) # PEPEBOT TEST SERVER MUSIC VOICE CHANNEL
_t_channel = bot.get_channel(902694643769176107) # PEPEBOT TEST SERVER general text channel

@bot.event
async def on_voice_state_update(member, before, after):
    # Connecting to users channel and playing their playlits
    global _guild
    global _v_channel
    global _t_channel
    global _v_channel_id
    voice = discord.utils.get(bot.voice_clients, guild=_guild)
    if after.channel and member.voice.channel.id == _v_channel_id:
        user_playlist = get_playlist(member.id)
        print(user_playlist)
        if voice is None and user_playlist is not None:
            await play_the_playlist(_t_channel, member.name, voice, _v_channel, user_playlist)

# Turns on or off the playlist mode
@bot.command()
async def playlist(ctx):
    global playlist_mode
    if playlist_mode:
        print("Turning off playlist mode")
        playlist_mode = False
        await ctx.send("Playlist mode turned off...")
    else:
        voice = ctx.author.voice
        if voice is None:
            print("User tried to turn on playlist mode but the user is not in voice")
            await ctx.send('You are not in any voice channel...')
        else:
            song = os.path.isfile("song.webm")
            if song:
                await ctx.send("I'm already in voice channel being used...")
                return
            # If we are already in voice channel and we want to turn on the playlist mode
            print("Playling playlist mode manually by user...")
            user_playlist = get_playlist(ctx.author.id)
            print(user_playlist)
            if user_playlist is not None:
                global _guild
                #global _v_channel
                v = ctx.author.voice
                if v is not None:
                    _v_channel = v
                else:
                    await ctx.send("You are not in voice channel...")
                    return
                global _t_channel
                bot_voice = discord.utils.get(bot.voice_clients, guild=_guild)
                if bot_voice is None:
                    bot_voice = await voice.channel.connect()
                    print("Connected bot to voice channel")
                print("Should play playlist")
                print(ctx.author.name)
                await play_the_playlist(_t_channel, ctx.author.name, bot_voice, _v_channel, user_playlist)
                print("Played playlist manualy")
            else:
                await ctx.send("Can't play your playlist because its empty...to create one use -playlistadd")


# Plays the playlist
async def play_the_playlist(t_channel, member_name : str, voice, v_channel, u_playlist):
    global playlist_mode
    playlist_mode = True
    remove_song()
    try:
        voice = await v_channel.connect() # Sets the voice client
    except:
        print("User is already in voice channel")
    await t_channel.send(member_name + " has joined music voice channel...playing his playlist...")
    write_song_queue(u_playlist) # Writes down the song queue from the users playlist
    song_queue = get_song_queue()["queue"]
    start_playing(voice, song_queue["urls"].pop(0), song_queue["titles"].pop(0), song_queue["durations"].pop(0))
    pop_queue()

    global loop_queue
    loop_queue = True
    await t_channel.send('Looping current queue')
    loop_song_queue = song_queue.copy()
    loop_song_queue["urls"].insert(0, current_song_url) # Inserts current song in the beggining of loop queue
    loop_song_queue["titles"].insert(0, current_song_title)
    loop_song_queue["durations"].insert(0, current_song_duration)
    write_loop_song_queue(loop_song_queue)

# Copies the playlist in song or loop song queue
@bot.command()
async def copyplaylist(ctx):
    # Check if the song is already being played if it is we add all songs
    # to queue if not we play the first one and add the rest
    song = os.path.isfile("song.webm")
    song_queue = get_song_queue()["queue"]
    loop_song_queue = get_song_queue()["loop_song_queue"]
    member_id = ctx.author.id
    user_playlist = get_playlist(member_id)
    voice = ctx.voice_client
    if voice is None:
        await ctx.send("Im not connected to any voice channels...")
        return
    if song:
        for i in user_playlist["urls"]: song_queue["urls"].append(i)
        for i in user_playlist["titles"]: song_queue["titles"].append(i)
        for i in user_playlist["durations"]: song_queue["durations"].append(i)
        write_song_queue(song_queue)
        await ctx.send("Copied songs from your playlist to queue...")
    else:
        for i in user_playlist["urls"]: song_queue["urls"].append(i)
        for i in user_playlist["titles"]: song_queue["titles"].append(i)
        for i in user_playlist["durations"]: song_queue["durations"].append(i)
        write_song_queue(song_queue)
        start_playing(voice, song_queue["urls"].pop(0), song_queue["titles"].pop(0), song_queue["durations"].pop(0))
        pop_queue()
        await ctx.send("Copied songs from your playlist to queue...")

    global loop_queue
    if loop_queue:
        for i in user_playlist["urls"]: loop_song_queue["urls"].append(i)
        for i in user_playlist["titles"]: loop_song_queue["titles"].append(i)
        for i in user_playlist["durations"]: loop_song_queue["durations"].append(i)
        write_loop_song_queue(loop_song_queue)
        await ctx.send("Added songs to loop as well...")

# Makes or adds the song to someones playlist
@bot.command(aliases=['pladd'])
async def playlistadd(ctx, *, search_key : str):
    print('Adding song')
    info = await find_song(search_key)
    url = info[0]
    title = info[1].encode("unicode-escape").decode("utf-8")
    duration = info[2]
    await ctx.send("Queued : " + title.encode("utf-8").decode("unicode-escape"))
    member_id = ctx.author.id
    member_playlist = get_playlist(member_id)
    if member_playlist is not None:
        print(member_playlist["urls"])
        print(url, title, duration)
        member_playlist["urls"].append(url)
        member_playlist["titles"].append(title)
        member_playlist["durations"].append(duration)
        save_playlist(member_playlist, member_id)
        print("Done")
        print("Updating song queue and loop song queue")
        global playlist_mode
        if playlist_mode:
            song_queue = get_song_queue()["queue"]
            song_queue["urls"].append(url)
            song_queue["titles"].append(title)
            song_queue["durations"].append(duration)
            write_song_queue(song_queue)

            loop_song_queue = get_song_queue()["loop_song_queue"]
            loop_song_queue["urls"].append(url)
            loop_song_queue["titles"].append(title)
            loop_song_queue["durations"].append(duration)
            write_loop_song_queue(loop_song_queue)
            print("Updated current song and loop song queue")
        await ctx.send("Song added to your playlist")
    else:
        print("Making new playlist and adding song to it")
        member_playlist = make_playlist(ctx.author.name, member_id)
        print(url, title, duration)
        member_playlist["urls"].append(url)
        member_playlist["titles"].append(title)
        member_playlist["durations"].append(duration)
        save_playlist(member_playlist, member_id)
        print("Done")
        await ctx.send("Song added to your playlist")

'''
# Used to import youtube playlist and make it into playable playlist
@bot.command()
async def importplaylist(ctx, url : str):
    # Google API credentials key
    key = ''

    try:
        query = parse_qs(urlparse(url).query, keep_blank_values=True)
        playlist_id = query["list"][0]
    except:
        await ctx.send("ERROR")
        return

    print(f'get all playlist items links from {playlist_id}')
    youtube = build("youtube", "v3", developerKey = key)

    request = youtube.playlistItems().list(
        part = "snippet",
        playlistId = playlist_id
    )
    response = request.execute()
    print("Got request")
    playlist_items = []
    while request is not None:
        response = request.execute()
        playlist_items += response["items"]
        request = youtube.playlistItems().list_next(request, response)

    member_id = ctx.author.id
    pl = get_playlist(member_id)
    if pl is not None:
        pl_delete_by_id(member_id)

    print("Making new playlist and adding songs to it")
    member_playlist = make_playlist(ctx.author.name, member_id)
    for item in playlist_items:
        s_url = "https://www.youtube.com/watch?v=" + item["snippet"]["resourceId"]["videoId"]
        s_title = item['snippet']['title'].encode("unicode-escape").decode("utf-8")
        print(s_url + " / " + s_title)
        member_playlist["urls"].append(s_url)
        member_playlist["titles"].append(s_title)
        member_playlist["durations"].append('123')

    save_playlist(member_playlist, member_id)
    await ctx.send("Imported playlist from youtube!")
'''

# Shows the user their current saved playlist (10 songs per page (default: page 1))
@bot.command(aliases=['plq'])
async def playlistq(ctx, x : int = 1):
    msg = 'Current songs in your playlist:\n'
    queue = get_playlist(ctx.author.id)
    l = len(queue["titles"])
    if queue is None:
        await ctx.send("Make your playlist using -playlistadd")
        return

    # Calculating total number of pages
    n = l
    if n % 10 == 0:
        n = int(n / 10)
    else:
        n = n // 10 + 1

    # Checking if entered number is valid
    if x <= 0 or x > n:
        await ctx.send("Invalid page number or empty queue !")
        return

    st = (x * 10) - 10 # Starting number
    end = x * 10 # Ending number
    if end > l:
        end = l

    # Assembling queue
    try :
        for i in range(st, end):
            song_name = queue["titles"][i].encode("utf-8").decode("unicode-escape")
            msg += str(i + 1) + '. ' + song_name + '\n'
    except:
        await ctx.send("Invalid!")

    msg += "Page (" + str(x) + "/" + str(n) + ")"
    print('Done assembling')
    await ctx.send(msg)

# Shuffles users playlist
@bot.command(aliases=['plshuffle'])
async def playlistshuffle(ctx):
    id = ctx.author.id
    playlist_q = get_playlist(id)
    seed = random.random()

    random.seed(seed)
    random.shuffle(playlist_q["urls"])
    random.seed(seed)
    random.shuffle(playlist_q["titles"])
    random.seed(seed)
    random.shuffle(playlist_q["durations"])
    save_playlist(playlist_q, id)
    await ctx.send("Shuffled your playlist...")

    if playlist_mode:
        write_song_queue(playlist_q)
        write_loop_song_queue(playlist_q)



# Deletes the song from users playlist
@bot.command(aliases=['pldel'])
async def playlistdel(ctx, index : int):
    print("Deleting song from playlist")
    loop_song_queue = get_song_queue()["loop_song_queue"]
    song_queue = get_song_queue()["queue"]
    id = ctx.author.id
    index -= 1 # Index compensation
    playlist_q = get_playlist(id)
    try:
        del playlist_q["urls"][index]
        del playlist_q["titles"][index]
        del playlist_q["durations"][index]
        save_playlist(playlist_q, id)
        await ctx.send("Deleted " + str(index + 1) + ". song")
    except:
        await ctx.send("Invalid song index entered...")

# Deletes the whole users playlist also deletes their list in data.json
@bot.command(aliases=['pldelall'])
async def playlistdelall(ctx):
    member_id = ctx.author.id
    member_playlist = get_playlist(member_id)
    global playlist_mode
    playlist_mode = False
    print("Turned off playlist mode due to playdelall")
    if member_playlist is not None:
        delete_playlist(member_id)
        await ctx.send("Deleted your playlist...you may create new by using -playlistadd")
    else:
        await ctx.send("You don't have your own playlist...to create one use -playlistadd and add your first song")

'''
# Deletes the whole users playlist by user id also deletes their list in data.json
def pl_delete_by_id(member_id):
    member_playlist = get_playlist(member_id)
    global playlist_mode
    playlist_mode = False
    print("Turned off playlist mode due to playdelall")
    if member_playlist is not None:
        delete_playlist(member_id)
'''

# Returns the users playlist list with urls, titles and durations of songs
def get_playlist(id : int):
    print("CHEKCING PLAYLIST")
    try:
        with open("data.json", "r") as file:
            data = json.loads(file.read())
        file.close()
        queue = data[str(id)]
        print("Returned queue")
        return queue
    except:
        print("Returned null")
        return None

# Saves the provided list to users playlist
def save_playlist(member_playlist, member_id : int):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    data[str(member_id)] = member_playlist.copy()
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()

# Makes the users playlist in data.json
def make_playlist(member_name, id : int):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    data[str(id)] = {
        "urls" : [],
        "titles" : [],
        "durations" : []
    }
    data["username_base"]["ids"].append(id)
    data["username_base"]["usernames"].append(member_name)
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()
    return data[str(id)]

# Deletes the key named by users id in data.json
def delete_playlist(id : int):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    del data[str(id)]
    index = data["username_base"]["ids"].index(id)
    del data["username_base"]["ids"][index]
    del data["username_base"]["usernames"][index]
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()
    print("Deleted playlist under id : " + str(id))

# Sets the music text channel (by default its PEPEBOT TEST SERVER)
@bot.command()
async def settext(ctx, msg):
    global _t_channel
    # In case the channel id is wrong
    try:
        id = int(msg)
        _t_channel = bot.get_channel(id)
        await ctx.send("Set the text channel (" + str(id) + ")")
    except:
        await ctx.send("ERROR: Wrong text channel...")

# Sets the music(playlist) voice channel (by default its PEPEBOT TEST SERVER)
@bot.command()
async def setvoice(ctx, msg):
    global _v_channel
    global _v_channel_id
    # In case the channel id is wrong
    try:
        id = int(msg)
        _v_channel = bot.get_channel(id)
        _v_channel_id = id
        await ctx.send("Set the voice channel (" + str(id) + ")")
    except:
        await ctx.send("ERROR: Wrong voice channel...")

# Sets the guild where playlist mode can be used (by default its PEPEBOT TEST SERVER)
@bot.command()
async def setguild(ctx, msg):
    global _guild
    # In case the guild id is wrong
    try:
        id = int(msg)
        _guild = bot.get_guild(id)
        await ctx.send("Set the guild (" + str(id) + ")")
    except:
        await ctx.send("ERROR: Wrong guild...")

# ------------------------------

# Voting system
# ------------------------------

# Makes the vote
# Format : [Vote question];[Option1];[Option2];[Option3]...
@bot.command()
async def vote(ctx, *, key : str):
    arr = key.split(';')
    num = len(arr)
    # Making sure we have at least two choices and max 10
    if num < 3 or num > 11:
        await ctx.send("Invalid number of voting options (min: 2, max: 10)")
        return

    # Emojies used for numbers encoded in unicode-escape
    emojies = ["\u0031\ufe0f\u20e3", "\u0032\ufe0f\u20e3", "\u0033\ufe0f\u20e3", "\u0034\ufe0f\u20e3",
                "\u0035\ufe0f\u20e3", "\u0036\ufe0f\u20e3", "\u0037\ufe0f\u20e3", "\u0038\ufe0f\u20e3",
                "\u0039\ufe0f\u20e3", "\U0001F51F"]

    # Assembling the message used for voting
    msg_text = "Vote : " + arr[0] + "\n\n"
    for i in range(num - 1):
        option = emojies[i] + " - " + arr[i + 1] + "\n"
        msg_text += option
    message = await ctx.send(msg_text)
    for i in range(num - 1):
        await message.add_reaction(emojies[i]) # Adding reactions that are used to vote

    # Saving the vote data to vote_data.json
    await asyncio.sleep(0.5)
    print("Sent everyting")
    vote_data = get_vote_data()
    print("Got vote data")
    msg_data = { "id" : message.id, "voters" : [], "votes" : []}
    vote_data["messages"].append(msg_data)
    print("Appended vote data")
    save_vote_data(vote_data)

# Using on_raw_reaction_add instead of on_reaction_add so bot
# can check for added reactions even if messages aren't in bots cache
@bot.event
async def on_raw_reaction_add(payload):
    # Getting payload (user and emoji data)
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = bot.get_user(payload.user_id)
    if not user:
        user = await bot.fetch_user(payload.user_id)
    print(str(user.id) + " reaction : " + payload.emoji.name)
    print(message.id)

    # Making sure we add votes only from reactions on vote messages
    vote_data = get_vote_data()
    for i in range(len(vote_data["messages"])):
        if vote_data["messages"][i]["id"] == message.id:
            if user.id in vote_data["messages"][i]["voters"]:
                # In case someone votes for multiple things we remove additional votes
                print("removing users emoji/vote...")
                await message.remove_reaction(payload.emoji, user)
            else:
                # Saving who voted and their vote
                vote_data["messages"][i]["voters"].append(user.id)
                emoji = payload.emoji.name.encode("unicode-escape").decode("utf-8")
                vote_data["messages"][i]["votes"].append(emoji)
                print("Added user to 'voters' for vote id : " + str(message.id))
                save_vote_data(vote_data)

# Using on_raw_reactio_remove to check if a person wants to withdraw a vote
# and change it
@bot.event
async def on_raw_reaction_remove(payload):
    # Getting payload (user and emoji data)
    channel = bot.get_channel(payload.channel_id)
    message = await channel.fetch_message(payload.message_id)
    user = bot.get_user(payload.user_id)
    if not user:
        user = await bot.fetch_user(payload.user_id)
    print(str(user.id) + " removed reaction : " + payload.emoji.name)
    print(message.id)

    # Checking if vote is supposed to be withdrawn
    vote_data = get_vote_data()
    for i in range(len(vote_data["messages"])):
        if vote_data["messages"][i]["id"] == message.id:
            if user.id in vote_data["messages"][i]["voters"]:
                ind = vote_data["messages"][i]["voters"].index(user.id)
                emoji = payload.emoji.name.encode("unicode-escape").decode("utf-8")
                # Checking if votes match
                if vote_data["messages"][i]["votes"][ind] == emoji:
                    print("removing users vote and removing them from list of voters...")
                    del vote_data["messages"][i]["votes"][ind]
                    del vote_data["messages"][i]["voters"][ind]
                    await message.remove_reaction(payload.emoji, user)
                    save_vote_data(vote_data)


# ------------------------------

# OWNER COMMAND ONLY
# Shuts down the bot (Takes some time for bot to log off)
@bot.command()
@commands.is_owner()
async def shutdown(ctx):
    try:
        await stop(ctx)
        await leave(ctx)
    except:
        pass

    print('--------------')
    print('Max memory usage (bytes) :')
    print("WIP")
    await ctx.send('Shutting down...')
    await bot.close()
    print('')
    print('Bot logged out')
    print('--------------')


# -------------------------
# Non-Bot related functions
# -------------------------

# Looking up for url of song by its name
async def find_song(name : str):
    videos_search = VideosSearch(name, limit = 1)
    videos_result = await videos_search.next()
    videos_result = videos_result["result"]
    print(videos_result)
    if videos_result == []:
        print("Didn't find a song...returning None")
        return None
    link = videos_result[0]["link"]
    title = videos_result[0]["title"]
    duration = hms_to_seconds(videos_result[0]["duration"])
    return(link, title, duration)

# Remove song.webm from storage if it exists
def remove_song():
    try:
        song_directory = os.listdir('./')
        for item in song_directory:
            if item.endswith('.webm'):
                os.remove(item)
    except:
        print("Error in deleting song")

# Converts time from string (HH:MM:SS) to seconds
def hms_to_seconds(t : str):
    if len(t) <= 5:
        t = '00:' + t[:]
        print(t)
    h, m, s = [int(i) for i in t.split(':')]
    return 3600*h + 60*m + s

# Gets the data list from data.json
def get_song_queue():
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    return data

# Saves the song to queue in data.json
def add_song_queue(url : str, title : str, duration : int):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    queue = data["queue"]
    queue["urls"].append(url)
    queue["titles"].append(title)
    queue["durations"].append(duration)
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()


# Saves the song to loop queue in data.json
def add_loop_song_queue(url : str, title : str, duration : int):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    queue = data["loop_song_queue"]
    queue["urls"].append(url)
    queue["titles"].append(title)
    queue["durations"].append(duration)
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()


# Saves the array to song queue in data.json
def write_song_queue(q_list):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    print("copying array")
    data["queue"] = q_list.copy()
    print("copied array saving now")
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()


# Saves the array to loop song queue in data.json
def write_loop_song_queue(q_list):
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    data["loop_song_queue"] = q_list.copy()
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    file.close()


# Pops one song from queue in data.json
def pop_queue():
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    queue = data["queue"]
    queue["urls"].pop(0)
    queue["titles"].pop(0)
    queue["durations"].pop(0)
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()


# Pops one song from queue in data.json
def pop_loop_queue():
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    queue = data["loop_song_queue"]
    queue["urls"].pop(0)
    queue["titles"].pop(0)
    queue["durations"].pop(0)
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()


# Deletes both queue lists in data.json
def clear_queues():
    with open("data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    data["queue"] = {
        "urls" : [],
        "titles" : [],
        "durations" : []
    }
    data["loop_song_queue"] = {
        "urls" : [],
        "titles" : [],
        "durations" : []
    }
    with open("data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()

def get_vote_data():
    with open("vote_data.json", "r") as file:
        data = json.loads(file.read())
    file.close()
    return data

def save_vote_data(data):
    with open("vote_data.json", "w") as outfile:
        json.dump(data, outfile, ensure_ascii=False, indent=4)
    outfile.close()

# -------------------------
#
# -------------------------

process = psutil.Process(os.getpid())
bot.run(TOKEN)

# -------------------------
