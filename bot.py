import discord
from discord.ext import tasks, commands
import os
from dotenv import load_dotenv
import random
import csv
import datetime
from backports.zoneinfo import ZoneInfo  

# Load environment variables
load_dotenv()
CHANNEL_ID = 801236490524164137  
BOT_TOKEN = os.getenv('BINKY_BOT_TOKEN')


intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
bot = commands.Bot(command_prefix='binky!', intents=intents)

# Load quotes from ndnws.txt
with open('ndnws.txt', 'r', encoding='utf-8') as f:
    quotes = [line.strip() for line in f if line.strip()]

# Load emojis from emojis.csv
with open('emojis.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    emojis = next(reader)  # Assumes all emojis are on the first line

@tasks.loop(time=datetime.time(hour=5, minute=0, tzinfo=ZoneInfo('America/Los_Angeles')))
async def daily_message():
    """Task that sends a daily motivational message at 5 AM PT."""
    channel = bot.get_channel(CHANNEL_ID)
    if channel is None:
        print(f"Could not find channel with ID {CHANNEL_ID}.")
        return

    # Select a random quote and 4 random emojis
    quote = random.choice(quotes)
    chosen_emojis = ''.join(random.choices(emojis, k=4))

    # Send the message
    await channel.send(f"{quote}")
    await channel.send(f"{chosen_emojis}")

@bot.event
async def on_ready():
    print(f'Logged in as {bot.user} (ID: {bot.user.id})')
    # Start the daily message loop when bot is ready
    daily_message.start()

# Run the bot
bot.run(BOT_TOKEN)
