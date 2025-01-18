import discord
import json
import os

from datetime import datetime
from discord.ext import commands, tasks

def load_data():
    try:
        with open('data.json', 'r') as f:
            data = json.load(f)
            if "last_activity" in data and data["last_activity"] is not None:
                data["last_activity"] = datetime.fromisoformat(data["last_activity"])
            return data
    except FileNotFoundError:
        return {
            "seasons": {},
            "current_season": int(datetime.now().strftime("%Y")),
            "all_time_xp": {},
            "last_activity": None
        }

def save_data(data):
    data["last_activity"] = datetime.now().isoformat()
    with open('data.json', 'w') as f:
        json.dump(data, f)
    data["last_activity"] = datetime.fromisoformat(data["last_activity"])

with open('config.json', 'r') as file:
    config = json.load(file)

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents, help_command=commands.DefaultHelpCommand(show_parameter_descriptions=False))

data = load_data()
user_xp = data["seasons"].setdefault(str(data["current_season"]), {})
total_xp = data["all_time_xp"].setdefault("total", {})
xp_per_channel = {int(channel_id): data['xp'] for channel_id, data in config['channel_xp'].items() if 'xp' in data}
announcement_channel = {int(channel_id) for channel_id, data in config['channel_xp'].items() if 'announcements' in data}

async def award_xp_for_unread_messages(channel):
    last_activity = data["last_activity"]
    if last_activity is None:
        return

    async for message in channel.history(after=last_activity):
        if message.author == bot.user:
            continue

        user_id = str(message.author.id)
        xp_awarded = xp_per_channel.get(channel.id, 0)

        if user_id not in user_xp:
            user_xp[user_id] = 0
        user_xp[user_id] += xp_awarded

        if user_id not in total_xp:
            total_xp[user_id] = 0
        total_xp[user_id] += xp_awarded

    save_data(data)

@bot.event
async def on_ready():
    for channel_id in xp_per_channel.keys():
        channel = bot.get_channel(channel_id)
        if channel:
            await award_xp_for_unread_messages(channel)

    check_season_rollover.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        save_data(data)
        return

    if not message.content.startswith(bot.command_prefix):
        channel_id = message.channel.id
        if channel_id in xp_per_channel:
            user_id = str(message.author.id)
            xp_awarded = xp_per_channel[channel_id]

            if user_id not in user_xp:
                user_xp[user_id] = 0
            user_xp[user_id] += xp_awarded

            if user_id not in total_xp:
                total_xp[user_id] = 0
            total_xp[user_id] += xp_awarded

            await message.channel.send(f'{message.author.mention}, you have been awarded {xp_awarded} xp!')

    await bot.process_commands(message)
    save_data(data)

@bot.command(name='xp')
async def xp_command(ctx):
    """
    Show your xp amount this season
    """
    user_id = str(ctx.author.id)
    xp = user_xp.get(user_id, 0)
    await ctx.send(f'{ctx.author.mention}, you currently have {xp} xp this season.')

@bot.command(name='alltimexp')
async def all_time_xp_command(ctx):
    """
    Show your all-time xp amount
    """
    user_id = str(ctx.author.id)
    xp = total_xp.get(user_id, 0)
    await ctx.send(f'{ctx.author.mention}, you have a total of {xp} xp all-time.')

@bot.command(name='addxp')
@commands.has_permissions(administrator=True)
async def add_xp(ctx, member: discord.Member, amount: int):
    """
    Adds xp to member
    """
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] += amount

    if user_id not in total_xp:
        total_xp[user_id] = 0
    total_xp[user_id] += amount

    await ctx.send(f'Added {amount} xp to {member.mention}. They now have {user_xp[user_id]} xp this season and {total_xp[user_id]} xp alltime.')

@bot.command(name='subtractxp')
@commands.has_permissions(administrator=True)
async def subtract_xp(ctx, member: discord.Member, amount: int):
    """
    Subtracts xp from member
    """
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] -= amount

    if user_id not in total_xp:
        total_xp[user_id] = 0
    total_xp[user_id] -= amount

    await ctx.send(f'Subtracted {amount} xp from {member.mention}. They now have {user_xp[user_id]} xp this season and {total_xp[user_id]} xp alltime.')

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    """
    Display leaderboard
    """
    sorted_users = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)
    leaderboard_message_title = "🏆 **Leaderboard** 🏆\n"
    leaderboard_message = leaderboard_message_title
    leaderboard_message_empty = "No xp to display. Get to it!"

    for idx, (user_id, xp) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        if member:
            leaderboard_message += f"{idx}. {member.mention} - {xp} xp this season\n"

    await ctx.send(leaderboard_message_empty if leaderboard_message == leaderboard_message_title else leaderboard_message)

@tasks.loop(hours=24)
async def check_season_rollover():
    now = datetime.now()
    if now.year != data["current_season"]:
        previous_season = data["current_season"]
        data["current_season"] = now.year
        data["seasons"][str(data["current_season"])] = {}
        await bot.get_channel(announcement_channel).send(f'Season {previous_season} has ended, and Season {data["current_season"]} has begun!')
        save_data(data)

@bot.command(name='seasoninfo')
async def season_info(ctx):
    """
    Display season info
    """
    now = datetime.now()
    season_info = (f"Current Season: {data['current_season']}\n"
                   f"Season Ends: {datetime(now.year, 12, 31).strftime('%Y-%m-%d')}")
    await ctx.send(season_info)

@add_xp.error
@subtract_xp.error
async def xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f'{ctx.author.mention}, you do not have permission to use this command.')

bot.run(config['bot_token'])
