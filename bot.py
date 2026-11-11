import os
import discord
from discord.ext import commands
import random
import json
import time
import math
import asyncio

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='>', intents=intents)

token = os.getenv('DISCORD_BOT_TOKEN')

# list of Pokémon names
pokemon = ['Pikachu', 'Charmander', 'Squirtle', 'Bulbasaur']

# level ranges
low_level = list(range(1,35))
medium_level = list(range(35, 70))
high_level = list(range(70, 101))

level_ranges = [low_level, medium_level, high_level]

# weighting for level range randomness
level_weights = [80, 15, 5]

# dictionary for pokemon sprites
sprites = {'Pikachu': {'default': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/25.png', 'shiny': 'https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/25.png'}, 'Charmander' : {'default': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/4.png", 'shiny': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/4.png" }, 'Squirtle' : { 'default': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/7.png", 'shiny': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/7.png"}, 'Bulbasaur' : {'default': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/1.gif", 'shiny': "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/home/shiny/1.png"}}

# index of current encounter
current = None

# dealine for current encounter
encounter_deadline = None

# tracks each users collection of Pokémon
collections = {}

# bool flag of whether usage message has sent
has_sent = False


usage_text= """Usage
    >encounter : Spawns a Pokémon
    >seen : Checks last encounter
    >catch : Add Pokémon to your collection
    >caught : Displays your caught Pokémon
    >usage : Display command usage
    """

# use bot token
if not token:
    print('No token. Exiting. \n')
    raise SystemExit


"""
function: async def usage(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - displays bots available commands
"""
@bot.command()
async def usage(ctx):
    await ctx.send(usage_text)

"""
function: async def encounter(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - generate a random integer *result*  between 0 and the length of list - 1 of pokemon *pokemon*
    - sets active encounter *current* to the value at *result* in the list *pokemon*
    - displays message saying *current* has been encountered
"""
@bot.command()
async def encounter(ctx):
    global current
    global encounter_deadline

    # check if existing encounter
    if current and time.monotonic() < encounter_deadline:
        text = "A Pokémon is already here!"
        await ctx.send(text)
        return

    # generate pokemon fields
    species = pokemon[random.randint(0, len(pokemon) - 1)]
    level = get_level()
    shiny = True if random.randint(1, 4096) == 1 else False
    current = {"species": species, "level" :level, "shiny?":shiny}

    encounter_deadline = time.monotonic() + 30

    asyncio.create_task(expire_encounter(ctx.channel, encounter_deadline))
    
    await display_encounter(ctx)

"""
HELPER
function: get_level()

parameters:
    - none

returns:
    - integer

description:
    - randomly picks a single list of integers (level range), from a list of weighted ranges *level_ranges*
    - selects a random value within that range
"""

def get_level():
    random_range = random.choices(level_ranges, level_weights)

    return random.choice(random_range[0])

"""
HELPER
function: async def display_encounter(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - generate a discord embed to display an encounter
    - sends the embed 
"""
async def display_encounter(ctx):
    title = f'A wild {current['species']} appeared!'
    description = f'Lv. {current['level']} · You have 30 seconds to use >catch .'
    sprite = sprites[current['species']]['shiny'] if current['shiny?'] else sprites[current['species']]['default']

    embed = discord.Embed()
    embed.title = title
    embed.description = description
    embed.set_image(url=sprite)

    await ctx.send(embed=embed)

"""
HELPER
function: async def expire_encounter(channel, spawn_deadline)

parameters: 
    - channel : the channel from the discord context in which encounter has been called
    - spawn_deadline :  the time at which the encounter expires, before another one has been caught and author has called >encounter again

returns:
    none

description: 
    - sleeps until deadline has expired
    - if encounter has not changed, resets *current* and *encounter_deadline*
    - sends message that the pokemon ran away
    - else, returns
"""

async def expire_encounter(channel, spawn_deadline):
    global encounter_deadline
    global current

    duration = max(0, spawn_deadline - time.monotonic())

    await asyncio.sleep(duration)

    if spawn_deadline == encounter_deadline:
        ran = current['species']

        current = None
        encounter_deadline = None

        text = f"The wild {ran} ran away!"
        await channel.send(text)
    else:
        return

"""
function: async def seen(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - if no last encounter exists *current*, then display error message
    - else, displays the last encounter
"""
@bot.command()
async def seen(ctx):
    global encounter_deadline
    global current

    if current is None:
        text = "There's no wild Pokémon right now."
        await ctx.send(text)
        return
    
    remaining = encounter_deadline - time.monotonic()
    
    if remaining <= 0:
        ran = current['species']

        encounter_deadline = None
        current = None

        text = f'The wild {ran} ran away!'
        await ctx.send(text)
    else:
        text = f"A wild {current['species']} is here! {math.ceil(remaining)} left to >catch ."
        await ctx.send(text)


"""
function: async def catch(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - adds the current encounter *current* to the dictionary *collections* containing each user's caught pokemon
    - if no *current* , displays error state
    - else, appends to *current* to corresponding entry in *collections* or created entry with empty list
    - then displays success message
"""
@bot.command()
async def catch(ctx):
    global current
    global encounter_deadline

    if current is None:
        text = "There's no wild Pokémon to catch."
        await ctx.send(text)
    elif time.monotonic() >= encounter_deadline:
        text = "The wild Pokémon ran away!"

        # clear current encounter and deadline
        current = None
        encounter_deadline = None

        await ctx.send(text)
    else:
        caught = current

        # clear current encounter and deadline
        current = None
        encounter_deadline = None

        # store the author id as str for JSON
        author_id_str = str(ctx.author.id)

        collections.setdefault(author_id_str, [])
        collections[author_id_str].append(caught)
        
        # save data to JSON
        with open("collections.json", "w", encoding="utf-8") as file:
            json.dump(collections, file, indent=4)

        text = f'{ctx.author.name} caught {caught['species']}!'
        await ctx.send(text)

"""
function: async def caught(ctx)

parameters: 
    - ctx : discord context object

returns:
    none

description: 
    - displays the authors list of caught pokemon in a string joined by ', '
    - if the author has no saved pokemon, displays empty message
    - else, displays a list 
"""
@bot.command()
async def caught(ctx):
    captured = collections.get(str(ctx.author.id)) or None

    if captured is None:
        text = "You haven't caught any pokemon yet."
        await ctx.send(text)
    else:
        await display_caught(ctx, captured)

"""
function: async display_caught(ctx, captured)

parameters: 
    - ctx : discord context object
    - captured : list of pokemon dictionaries associated with an authord id

returns:
    none

description: 
    - displays an embed for the authors pokemon collection
"""
async def display_caught(ctx, captured):

    title = f"{ctx.author.name}'s Pokémon Collection "
    description = "\n".join(f'{p['species']} · Lv.{p['level']}{' · Shiny' if p['shiny?'] else ''}' for p in captured) 
    embed = discord.Embed()
    embed.title = title
    embed.description = description

    await ctx.send(embed=embed)


"""
function: async def on_ready()

"""

@bot.event
async def on_ready():
    global has_sent
    channel = bot.get_channel(1569517676781375488)

    if channel is None:
        print('Channel not found.')
        return
    elif has_sent:
        pass
    else:
        await channel.send(usage_text)
        has_sent = True

# 
try :
    # load json with existing collection data
    with open('collections.json', 'r') as file:
        collections = json.load(file)
except FileNotFoundError:
    collections = {}

bot.run(token=token)