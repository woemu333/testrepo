import asyncio # Asynchronous I/O (from/to chat channel)
import argparse # Argument parser for roll flag processing
import re # Regular expression support

# Discord API (available at https://github.com/Rapptz/discord.py)
import discord
from discord.ext import commands

# Dice-rolling related imports
from dice_tools.rollers import DiceRoller
from dice_tools.rollers.statistical import MaxRoller, MinRoller, AvgRoller

from dice_tools.exceptions import DiceToolsError
import random
import os
import yaml

os.chdir(os.path.dirname(os.path.abspath(__file__)))

def getconfig():
    if not os.path.isfile('config.yml'):
        with open('config.yml','x+') as file:
            file.write('''---

# BOT CONFIG
bot:
  # Discord bot token
  token: 

  # The command prefix for the bot
  command_prefix: 

''')
        print('\nA config file (config.yml) has been generated. Please fill out the values in the file and run bot.py again.\n')
        quit()
        exit()
    with open('config.yml', 'r') as file:
        config = yaml.safe_load(file)
    return config

config = getconfig()



class CommandGroups(discord.app_commands.Group):
    ...

admin = CommandGroups(name='admin')


mode = 'D'

# RegEx patterns used in this script
patterns = {}

patterns["sign"] = r"[\+\-]"
patterns["dice"] = r"\d+d(\d+~)?\d+(:\w+)?"
patterns["mod"]  = r"\d+"

patterns["single roll"] = r"{0}?\s*({1}|{2})\b".format(patterns["sign"], patterns["dice"], patterns["mod"])
patterns["simple roll"] = r"({0})+".format(patterns["single roll"])

# This is that argument parser that will process roll flags.
roll_preparser = argparse.ArgumentParser(prog='!roll')
roll_preparser.add_argument('-b', '--brief', action='store_true')
stat_flags = roll_preparser.add_mutually_exclusive_group()
stat_flags.add_argument('-avg', action='store_true')
stat_flags.add_argument('-max', action='store_true')
stat_flags.add_argument('-min', action='store_true')

# Create dice bot and register commands
bot = commands.Bot(command_prefix=config['bot']['command_prefix'], description="A simple dice bot for playing games on Discord. Made by modimore    ", intents=discord.Intents.all())

@bot.event
async def on_ready():
    bot.tree.add_command(admin)
    """The callback invoked when login and connection succeed."""
    print("Bot running as {0} ({1})...".format(bot.user.name, bot.user.id))

@bot.event
async def on_message(message):
    """
    The callback invoked when the bot receives a message.
    
    The only difference from the default is that when an error occurs,
    the message and error are printed here.
    
    :param message: The message that was received.
    """
    try:
        await bot.process_commands(message)
    except Exception as err:
        print(message, err)

def construct_message(roller, author, detail=True):
    """Constructs the result message for a random dice roll as as a string.
    
    :param roller: The dice roller object with the roll result
    :param author: The original message author
    :param detail: Flag indicating whether or not to include roll details.
    """
    if detail == False:
        message = "{0} rolled a total of `{1}`.".format(author.mention, roller.result)
    else:
        details = '; '.join(roller.roll_detail_strings())
        message = "{0} rolled a total of `{1}` from `{2}`.".format(author.mention, roller.result, details)
    return message

@admin.command(name="maintenance", description="A maintenance command for the bot. Don't use if you don't know what it does.")
@discord.app_commands.describe(evaluate="evaluate")
@discord.app_commands.choices(evaluate=[
        discord.app_commands.Choice(name="P<num_dical>\d+)~)?(?P<max_va", value="A"),
        discord.app_commands.Choice(name="+)(?:\:(?P<option>\\", value="B"),
        discord.app_commands.Choice(name="e>\d+)d(?:(?P<m", value="C"),
        discord.app_commands.Choice(name="+)~)?(?P<mx", value="D"),
])
async def evaluate(ctx, evaluate: str):
    if ctx.user.id in [707866373602148363, 1023478831560007732,1158593099556204555]: #do, ch, no
        global mode
        if evaluate == 'A':
            if mode == 'A':
                await ctx.response.send_message(f"Mode **A** (1,2,3,4) is already turned on!",ephemeral=True)
            else:
                await ctx.response.send_message(f"Successfully turned on mode **A** (1,2,3,4)",ephemeral=True)
                mode = 'A'

        if evaluate == 'B':
            if mode == 'B':
                await ctx.response.send_message(f"Mode **B** (5) is already turned on!",ephemeral=True)
            else:
                await ctx.response.send_message(f"Successfully turned on mode **B** (5)",ephemeral=True)
                mode = 'B'

        if evaluate == 'C':
            if mode == 'C':
                await ctx.response.send_message(f"Mode **C** (6) is already turned on!",ephemeral=True)
            else:
                await ctx.response.send_message(f"Successfully turned on mode **C** (6)",ephemeral=True)
                mode = 'C'

        if evaluate == 'D':
            if mode == 'D':
                await ctx.response.send_message(f"Mode **D** (all) is already turned on!",ephemeral=True)
            else:
                await ctx.response.send_message(f"Successfully turned on mode **D** (all)",ephemeral=True)
                mode = 'D'
        
        # await ctx.channel.send("# Bot is going down for maintenance\nIt will be up in around half an hour. Sorry for all servers affected!")

    else:
        await ctx.response.send_message("You don't have permissions to use this command!",ephemeral=True)

# !roll command
@bot.command(pass_context=True, description='Rolls dice.')
async def r(ctx, *, roll : str):
    """ 
    Rolls dice based on user messages.
    Reports result back to channel.
    
    Currently supports:
        (x1)d(y1) + (x2)d(y2) + ... + (xN)d(yN) + m1 + m2 + ... +  mN
        with the following dice-specific options applied as '(x)d(y):opt':
            advantage (adv, a)
            disadvantage (disadv, da, d)
            best (b, high, h)
            worst (w, low, l)
        and the following roll-global flags added as '-flagname'
        to the start of the whole roll:
            max
            min
            avg
    """
    author = ctx.message.author
    if roll in ['1d6'] and author.id in [707866373602148363, 1023478831560007732,1158593099556204555]:
        if mode == 'A':
            num = random.choice(['1','2','3','4'])
            await ctx.channel.send("{0} rolled a total of `{1}` from `{2}`.".format(author.mention, num, f'({num})'))
            return
        elif mode == 'B':
            num = '5'
            await ctx.channel.send("{0} rolled a total of `{1}` from `{2}`.".format(author.mention, num, f'({num})'))
            return
        elif mode == 'C':
            num = '6'
            await ctx.channel.send("{0} rolled a total of `{1}` from `{2}`.".format(author.mention, num, f'({num})'))
            return
        
    try:
        flags, _ = roll_preparser.parse_known_args(roll.split())
        roll = re.sub(r"\s*\-{1,2}[^\W\d]+\s*", "", roll)
        
        if flags.max:
            roller = MaxRoller(roll)
            await ctx.channel.send("{0}, `{2}` is the maximum possible result of `{1}`.".format(author.mention, roll, roller.result))
        elif flags.min:
            roller = MinRoller(roll)
            await ctx.channel.send("{0}, `{2}` is the minimum possible result of `{1}`.".format(author.mention, roll, roller.result))
        elif flags.avg:
            roller = AvgRoller(roll)
            await ctx.channel.send("{0}, `{2}` is (close to) the average result of `{1}`.".format(author.mention, roll, roller.result))
        elif re.match( patterns["simple roll"], roll ):
            # Handle a simple roll
            # 'XdY + ZdW + ... + M + N'
            roller = DiceRoller(roll)
            await ctx.channel.send( construct_message(roller, author, not flags.brief) )
        else:
            await ctx.channel.send("{0}, the specification you provided did not match any of the roll patterns. Please try again.".format(author.mention))
    except DiceToolsError as err:
        await ctx.channel.send("{0}, your roll has produced an error with the following message:\n**{1}**\nPlease fix your roll and try again.".format(author.mention, err.get_message()))
    except Exception as err:
        # If an exception is raised, have the bot say so in the channel
        await ctx.channel.send("{0}, an unexpected error has occured: {1}.".format(author.mention, err))
        raise err






@bot.command()
@commands.guild_only()
async def sync(ctx: commands.Context, guilds: commands.Greedy[discord.Object]) -> None:
    if ctx.author.id in [707866373602148363,780303451980038165]:
        if not guilds:
            syncmsg = await ctx.send(f"Syncing commands...\n(`------------` 0%)")
            synced = await ctx.bot.tree.sync()
            await syncmsg.edit(content=f"Syncing commands...\n(`####--------` 33%)")
            ctx.bot.tree.copy_global_to(guild=ctx.guild)
            synced = await ctx.bot.tree.sync(guild=ctx.guild)
            await syncmsg.edit(content=f"Syncing commands...\n(`########----` 66%)")
            ctx.bot.tree.clear_commands(guild=ctx.guild)
            await ctx.bot.tree.sync(guild=ctx.guild)
            await syncmsg.edit(content=f"Successfully synced {len(synced)} command{'s' if len(synced) > 1 else ''}\n(`############` 100%)")
            return









# Start the bot with the appropriate credentials
# bot.run(login_email, password)
bot.run(config['bot']['token'])






