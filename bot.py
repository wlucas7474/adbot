import discord
import json
import os

from discord.ext import commands
from dotenv import load_dotenv

# Load or create a xp data file
def load_xp():
    try:
        with open('xp.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def save_xp(xp):
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
user_xp = load_xp()

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

            save_xp(user_xp)  # Save updated xp
            await message.channel.send(f'{message.author.mention}, you have been awarded {xp_awarded} xp!')

    await bot.process_commands(message)

@bot.command(name='xp')
async def xp_command(ctx):
    user_id = str(ctx.author.id)
    xp = user_xp.get(user_id, 0)
    await ctx.send(f'{ctx.author.mention}, you currently have {xp} xp.')

@bot.command(name='addxp')
@commands.has_permissions(administrator=True)
async def add_xp(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] += amount
    save_xp(user_xp)
    await ctx.send(f'Added {amount} xp to {member.mention}. They now have {user_xp[user_id]} xp.')

@bot.command(name='subtractxp')
@commands.has_permissions(administrator=True)
async def subtract_xp(ctx, member: discord.Member, amount: int):
    user_id = str(member.id)
    if user_id not in user_xp:
        user_xp[user_id] = 0
    user_xp[user_id] -= amount
    save_xp(user_xp)
    await ctx.send(f'Subtracted {amount} xp from {member.mention}. They now have {user_xp[user_id]} xp.')

# Handle errors for admin commands
@add_xp.error
@subtract_xp.error
async def xp_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send(f'{ctx.author.mention}, you do not have permission to use this command.')


bot.run(os.getenv('BOT_TOKEN'))
