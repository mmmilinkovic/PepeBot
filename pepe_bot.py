'''
PepeBot made by reyy

'''

import asyncio
from logging import NullHandler
import psutil
import discord
import aiofiles.os
from discord import channel
from discord import member
from discord.ext import commands
from discord.utils import get
import yt_dlp
from youtubesearchpython.__future__ import VideosSearch # Needed to run youtubesearch in async
import os
import json
import random

# Sets the high process prio remove when testing on windows
#p = psutil.Process(os.getpid())
#p.nice(10)

TOKEN = '' # Setting bots token

bot = commands.Bot(command_prefix='-') # Setting bots command prefix

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
    if voice == None:
        await ctx.send('You are not in any voice channel...')
    else:
        try:
            remove_song()
            await voice.channel.connect()
        except:
            await ctx.send('im already in voice channel')

playlist_mode = False # 
songQueue = [] # Check if you can remove this !!
current_song_url = ''
current_song_title = ''
current_song_duration = '' # Used to determine if we need to wait since the queue data is currently being written to data.json
def start_playing(vClient, url, title, duration):
    def check_queue():
        print('Checking queue...')
        print('Looping ? ' + str(loopQ))

        songQueue = get_song_queue()["queue"]
        loop_song_queue = get_song_queue()["loop_song_queue"]
        if len(songQueue["urls"]) != 0:
            next_song_url = songQueue["urls"].pop(0)
            next_song_title = songQueue["titles"].pop(0)
            next_song_duration = songQueue["durations"].pop(0)
            pop_queue()
            print('Playing next song')
            start_playing(vClient, next_song_url, next_song_title, next_song_duration)
        else:
            # If its the last song in queue loop the queue
            if loopQ:
                print('Loop queue : ')
                print(loop_song_queue)
                songQueue = loop_song_queue.copy()
                print('new queue: ')
                print(songQueue)
                write_song_queue(songQueue)
                next_song_url = songQueue["urls"].pop(0)
                next_song_title = songQueue["titles"].pop(0)
                next_song_duration = songQueue["durations"].pop(0)
        
                pop_queue()
                start_playing(vClient, next_song_url, next_song_title, next_song_duration)
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

    vClient.play(discord.FFmpegOpusAudio('song.webm'), after=lambda e: check_queue())

# Makes the bot play a song or adds it to a queue if there is a song already playing
@bot.command(aliases=['p'])
async def play(ctx, *, searchKey : str):
    global loopQ
    global playlist_mode
    songQueue = get_song_queue()["queue"]
    voice = ctx.voice_client
    if voice == None:
        await ctx.send('Im not connected to voice channel')
        return

    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")
        return

    # In case link was provided make sure we get rid of any additional parameters
    if searchKey.startswith("https:"):
        i = searchKey.find('&')
        if i != -1:
            searchKey = searchKey[:i]

    info = await findSong(searchKey)
    if info == None:
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
    songQueue["urls"].append(url)
    songQueue["titles"].append(title)
    songQueue["durations"].append(duration)
    print("writing song queue")
    write_song_queue(songQueue)
    print("wrote song queue")
    if loopQ:
        #loop_song_queue.append(url)

        add_loop_song_queue(url, title, duration)

    if song: # If song is getting ready to be played (downloading) put the next one in queue
        await ctx.send('Song added to queue')
    else:
        print("playing first song")
        start_playing(voice, songQueue["urls"].pop(0), songQueue["titles"].pop(0), songQueue["durations"].pop(0))

        pop_queue()

# Shows the current queue
@bot.command(aliases=['q'])
async def queue(ctx):
    print('Checking queue')
    global loopQ
    loop_song_queue = get_song_queue()["loop_song_queue"]
    songQueue = get_song_queue()["queue"]
    if loopQ:
        print('loop queue list')
        msg = 'Current songs in loop queue :\n'
        print('Assembling queue')
        i = 0
        for item in loop_song_queue["titles"]:
            i += 1
            song_name = item.encode("utf-8").decode("unicode-escape")
            msg += str(i) + '. ' + song_name + '\n'
        print('Done assembling')
        await ctx.send(msg)
    else:
        print('Non loop queue list')
        if len(songQueue) != 0:
            msg = 'Current songs in queue :\n'
            i = 0
            print('Assembling queue')
            for item in songQueue["titles"]:
                i += 1
                song_name = item.encode("utf-8").decode("unicode-escape")
                msg += str(i) + '. ' + song_name + '\n'
            print('Done assembling')
            await ctx.send(msg)

# Shuffles the songs in queue
@bot.command()
async def shuffle(ctx):
    global loopQ
    loop_song_queue = get_song_queue()["loop_song_queue"]

    # Check if loopQ is on
    if loopQ:
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
            await ctx.send("Shuffled loop queue...")

        else:
            await ctx.send("There are no songs in loop queue...")
    
    else:
        songQueue = get_song_queue()["queue"]
        print(songQueue)        
        # Check if there are any songs in queue
        if len(songQueue["titles"]) != 0:
            seed = random.random() # Gets random number for seed
            print(songQueue)
            random.seed(seed)
            random.shuffle(songQueue["urls"])

            random.seed(seed)
            random.shuffle(songQueue["titles"])

            random.seed(seed)
            random.shuffle(songQueue["durations"])

            write_song_queue(songQueue)
            await ctx.send("Shuffled queue...")
        
        else:
            await ctx.send("There are no songs in queue...")


# Deletes song from queue (by using index of song in queue)
@bot.command(aliases=['del'])
async def delete(ctx, index : int):
    global loopQ

    global playlist_mode
    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")

    songQueue = get_song_queue()["queue"]
    loop_song_queue = get_song_queue()["loop_song_queue"]
    index -= 1 # Array index compensation
    if (len(songQueue["urls"]) == 0) and (len(loop_song_queue["urls"]) == 0):
        return

    # REWORK THIS! CHEKCKING FOR INDEX!
    # Check if we need to delete song queue or loop song queue
    if loopQ:
        try:
            del loop_song_queue["urls"][index]
            del loop_song_queue["titles"][index]
            del loop_song_queue["durations"][index]
        except:
            await ctx.send("Invalid song index...")

        write_loop_song_queue(loop_song_queue)
        if index >= 1:
            try:
                del songQueue["urls"][index - 1]
                del songQueue["titles"][index - 1]
                del songQueue["durations"][index - 1]
        
                write_song_queue(songQueue)
            except:
                await ctx.send("Invalid song index...")
    else:
        try:
            del songQueue["urls"][index]
            del songQueue["titles"][index]
            del songQueue["durations"][index]

            write_song_queue(songQueue)
        except:
            await ctx.send("Invalid song index...")

# Clears song queue or loop song queue depending if loop is turned on
@bot.command(aliases=['c'])
async def clear(ctx):
    global loopQ
    global playlist_mode
    if loopQ:
        clear_queues()
        playlist_mode = False
        loopQ = False
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
    global loopQ
    voice = ctx.voice_client
    # Clears queues
    clear_queues()
    loopQ = False
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

loopQ = False
# Loops the current queue
@bot.command()
async def loop(ctx):
    global loopQ
    global current_song_url
    global current_song_title
    global current_song_duration
    songQueue = get_song_queue()["queue"]

    global playlist_mode
    if playlist_mode:
        await ctx.send("Can't use this command...playlist mode is on...(-playlist)")
        return

    if loopQ == False:
        loopQ = True
        await ctx.send('Looping current queue')
        loop_song_queue = songQueue.copy()
        if current_song_url != '':  # In case loop is used before a song played/queued
            loop_song_queue["urls"].insert(0, current_song_url) # Inserts current song in the beggining of loop queue
            loop_song_queue["titles"].insert(0, current_song_title)
            loop_song_queue["durations"].insert(0, current_song_duration)
    
            write_loop_song_queue(loop_song_queue)
        print(loop_song_queue)
    else:
        loopQ = False
        await ctx.send('Stopped looping')
        loop_song_queue = []

        write_loop_song_queue(loop_song_queue)

# Skips to next song in queue
@bot.command(aliases=['s'])
async def skip(ctx):
    if len(songQueue) != 0:
        voice = ctx.voice_client
        voice.stop()
        print('Skipping to next song')
    else:
        print('Can not skip, stopping...')
        voice = ctx.voice_client
        voice.stop()
        return

# Commands the bot to leave the voice channel it is currently in making it available
# to join in other voice channel in case anyone requests it
@bot.command()
async def leave(ctx):
    try:
        global loopQ
        loopQ = False
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
        if voice == None and user_playlist != None:
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
        if voice == None:
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
            if user_playlist != None:
                global _guild
                #global _v_channel
                v = ctx.author.voice
                if v != None:
                    _v_channel = v
                else:
                    await ctx.send("You are not in voice channel...")
                    return
                global _t_channel
                bot_voice = discord.utils.get(bot.voice_clients, guild=_guild)
                if bot_voice == None:
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
    songQueue = get_song_queue()["queue"]
    start_playing(voice, songQueue["urls"].pop(0), songQueue["titles"].pop(0), songQueue["durations"].pop(0))
    pop_queue()

    global loopQ
    loopQ = True
    await t_channel.send('Looping current queue')
    loop_song_queue = songQueue.copy()
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
    songQueue = get_song_queue()["queue"]
    loop_song_queue = get_song_queue()["loop_song_queue"]
    member_id = ctx.author.id
    user_playlist = get_playlist(member_id)
    voice = ctx.voice_client
    if voice == None:
        await ctx.send("Im not connected to any voice channels...")
        return
    if song:
        for i in user_playlist["urls"]: songQueue["urls"].append(i)
        for i in user_playlist["titles"]: songQueue["titles"].append(i)
        for i in user_playlist["durations"]: songQueue["durations"].append(i)
        write_song_queue(songQueue)
        await ctx.send("Copied songs from your playlist to queue...")
    else:
        for i in user_playlist["urls"]: songQueue["urls"].append(i)
        for i in user_playlist["titles"]: songQueue["titles"].append(i)
        for i in user_playlist["durations"]: songQueue["durations"].append(i)
        write_song_queue(songQueue)
        start_playing(voice, songQueue["urls"].pop(0), songQueue["titles"].pop(0), songQueue["durations"].pop(0))
        pop_queue()
        await ctx.send("Copied songs from your playlist to queue...")
    
    global loopQ
    if loopQ:
        for i in user_playlist["urls"]: loop_song_queue["urls"].append(i)
        for i in user_playlist["titles"]: loop_song_queue["titles"].append(i)
        for i in user_playlist["durations"]: loop_song_queue["durations"].append(i)
        write_loop_song_queue(loop_song_queue)
        await ctx.send("Added songs to loop as well...")

# Makes or adds the song to someones playlist
@bot.command(aliases=['pladd'])
async def playlistadd(ctx, *, searchKey : str):
    print('Adding song')
    info = await findSong(searchKey)
    url = info[0]
    title = info[1].encode("unicode-escape").decode("utf-8")
    duration = info[2]
    await ctx.send("Queued : " + title.encode("utf-8").decode("unicode-escape"))
    member_id = ctx.author.id
    member_playlist = get_playlist(member_id)
    if member_playlist != None:
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
            songQueue = get_song_queue()["queue"]
            songQueue["urls"].append(url)
            songQueue["titles"].append(title)
            songQueue["durations"].append(duration)
            write_song_queue(songQueue)

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


# Shows the user their current saved playlist
@bot.command(aliases=['plq'])
async def playlistq(ctx):
    msg = 'Current songs in your playlist:\n'
    queue = get_playlist(ctx.author.id)
    if queue == None:
        await ctx.send("Make your playlist using -playlistadd")
        return
    i = 0
    for item in queue["titles"]:
        i += 1
        song_name = item.encode("utf-8").decode("unicode-escape")
        msg += str(i) + '. ' + song_name + '\n'
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
    songQueue = get_song_queue()["queue"]
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
    if member_playlist != None:
        delete_playlist(member_id)
        await ctx.send("Deleted your playlist...you may create new by using -playlistadd")
    else:
        await ctx.send("You don't have your own playlist...to create one use -playlistadd and add your first song")


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
async def findSong(name : str):
    videosSearch = VideosSearch(name, limit = 1)
    videosResult = await videosSearch.next()
    videosResult = videosResult["result"]
    print(videosResult)
    if videosResult == []:
        print("Didn't find a song...returning None")
        return None
    link = videosResult[0]["link"]
    title = videosResult[0]["title"]
    duration = hms_to_seconds(videosResult[0]["duration"])
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


# -------------------------
#
# -------------------------

process = psutil.Process(os.getpid())
bot.run(TOKEN)

# -------------------------
