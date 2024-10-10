import discord
import os

from discord.ext import commands
from dotenv import load_dotenv

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user}')

@bot.command()
async def ping(ctx):
    await ctx.send('Pong!')

load_dotenv()
bot.run(os.getenv('BOT_TOKEN'))
