import discord
import json
import os

from datetime import datetime, timedelta
from discord.ext import commands
from dotenv import load_dotenv

# Load or create a xp data file
def load_data():
    try:
        with open('xp.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {
            "seasons": {},
            "current_season": 1,
            "season_end": None,
            "all_time_xp": {}
        }

def save_data(xp):
    with open('xp.json', 'w') as f:
        json.dump(xp, f)

load_dotenv()

# Create bot instance
intents = discord.Intents.default()
intents.guilds = True
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# xp for each channel
xp_per_channel = {
    int(os.getenv('MOVIES_ID')): 7,
    int(os.getenv('GAME_ID')): 38,
    int(os.getenv('BOOK_ID')): 25,
    int(os.getenv('AUDIO_BOOK_ID')): 18,
    int(os.getenv('TV_SHOW_ID')): 30,
    int(os.getenv('ALBUM_ID')): 2,
    int(os.getenv('COMIC_ID')): 2,
    int(os.getenv('PODCASTS_ID')): 2,
}

# Load xp from file
data = load_data()
user_xp = data["seasons"].setdefault(str(data["current_season"]), {})
total_xp = data["all_time_xp"].setdefault("total", {})

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name}')

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return

    if not message.content.startswith(bot.command_prefix):
        channel_id = message.channel.id
        if channel_id in xp_per_channel:
            user_id = str(message.author.id)
            xp_awarded = xp_per_channel[channel_id]

            # Award xp
            if user_id not in user_xp:
                user_xp[user_id] = 0
            user_xp[user_id] += xp_awarded

            save_data(user_xp)  # Save updated xp
            await message.channel.send(f'{message.author.mention}, you have been awarded {xp_awarded} xp!')

    await bot.process_commands(message)

@bot.command(name='xp')
async def xp_command(ctx):
    user_id = str(ctx.author.id)
    xp = user_xp.get(user_id, 0)
    await ctx.send(f'{ctx.author.mention}, you currently have {xp} xp this season.')

@bot.command(name='alltimexp')
async def all_time_xp_command(ctx):
    user_id = str(ctx.author.id)
    xp = total_xp.get(user_id, 0)
    await ctx.send(f'{ctx.author.mention}, you have a total of {xp} xp all time.')

@bot.command(name='yearlyxp')
async def yearly_xp_command(ctx):
    user_id = str(ctx.author.id)
    current_year = datetime.now().year
    yearly_xp = sum(xp for season, xp in user_xp.items() if datetime.strptime(season, "%Y").year == current_year)
    await ctx.send(f'{ctx.author.mention}, you have earned {yearly_xp} xp this year.')

@bot.command(name='addxp')
@commands.has_permissions(administrator=True)
async def add_xp(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] += amount

    # Update all-time xp
    if user_id not in total_xp:
        total_xp[user_id] = 0
    total_xp[user_id] += amount

    save_data(data)
    await ctx.send(f'Added {amount} xp to {member.mention}. They now have {user_xp[user_id]} xp this season and {total_xp[user_id]} xp alltime.')

@bot.command(name='subtractxp')
@commands.has_permissions(administrator=True)
async def subtract_xp(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] -= amount

    # Update all-time xp
    if user_id not in total_xp:
        total_xp[user_id] = 0
    total_xp[user_id] -= amount

    save_data(data)
    await ctx.send(f'Subtracted {amount} xp from {member.mention}. They now have {user_xp[user_id]} xp this season and {total_xp[user_id]} xp alltime.')

@bot.command(name='leaderboard')
async def leaderboard(ctx):
    # Sort users by xp
    sorted_users = sorted(user_xp.items(), key=lambda x: x[1], reverse=True)
    leaderboard_message = "🏆 **Leaderboard** 🏆\n"

    for idx, (user_id, xp) in enumerate(sorted_users, start=1):
        member = ctx.guild.get_member(int(user_id))
        if member:
            leaderboard_message += f"{idx}. {member.mention} - {xp} xp this season\n"

    await ctx.send(leaderboard_message or "No xp to display.")

@bot.command(name='newseason')
@commands.has_permissions(administrator=True)
async def new_season(ctx):
    # Transition to a new season
    data["current_season"] += 1
    data["season_end"] = (datetime.now() + timedelta(days=30)).strftime("%Y-%m-%d %H:%M:%S")  # Season lasts 30 days
    data["seasons"][str(data["current_season"])] = {}
    save_data(data)
    await ctx.send(f'Season {data["current_season"]} has started!')

@bot.command(name='seasoninfo')
async def season_info(ctx):
    season_info = (f"Current Season: {data['current_season']}\n"
                   f"Season Ends: {data['season_end']}")
    await ctx.send(season_info)

# Handle errors for admin commands
@add_xp.error
@subtract_xp.error
async def xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f'{ctx.author.mention}, you do not have permission to use this command.')

bot.run(os.getenv('BOT_TOKEN'))
