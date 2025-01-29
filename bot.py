from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
import discord
from discord.ext import commands, tasks
from backports.zoneinfo import ZoneInfo
import random
import csv
import datetime
from activity_tracker import ActivityTracker

# Load environment variables
load_dotenv()
CHANNEL_ID = 801236490524164137
BOT_TOKEN = os.getenv('BINKY_BOT_TOKEN')
# Define your ranked channel IDs here
RANKED_CHANNELS = [
    # Add ranked channel IDs here
    797240494006337562, 801236490524164137, 1132448042000330852,
    1116536161121357866, 992809172762632202, 1249093608670498907,
    804789828729700383, 798008323910795275, 800963978037166121,
    823023433411461161, 797575136097730570, 845918076666904586,
    821621256096317491, 803444139302846464, 849297811980025937,
    994447859216822323, 821820402921766974, 1323574175205560320
]

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True  # Need this for mention tracking
bot = commands.Bot(command_prefix='binky!', intents=intents)

# Initialize activity tracker
activity_tracker = None

# Load quotes from ndnws.txt
with open('ndnws.txt', 'r', encoding='utf-8') as f:
    quotes = [line.strip() for line in f if line.strip()]

# Load emojis from emojis.csv
with open('emojis.csv', 'r', encoding='utf-8') as f:
    reader = csv.reader(f)
    emojis = next(reader)  # Assumes all emojis are on the first line

@tasks.loop(time=datetime.time(5, 0, tzinfo=ZoneInfo('America/Los_Angeles')))
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
    
    # Initialize activity tracker
    global activity_tracker
    activity_tracker = ActivityTracker(bot)
    activity_tracker.set_ranked_channels(RANKED_CHANNELS)
    activity_tracker.start_tasks()
    
    # Start the daily message loop
    daily_message.start()

@bot.event
async def on_message(message):
    await bot.process_commands(message)
    if activity_tracker:
        await activity_tracker.on_message(message)

@bot.event
async def on_reaction_add(reaction, user):
    if activity_tracker:
        await activity_tracker.on_reaction_add(reaction, user)

# Debug command to check last few tracked activities
@bot.command(name='debug')
@commands.is_owner()  # Only you can use this command
async def debug_info(ctx):
    """Show recent tracking activity."""
    if activity_tracker:
        recent = activity_tracker.db.get_recent_activity()
        response = "📊 **Recent Activity**\n\n"
        for activity in recent:
            response += f"- {activity}\n"
        await ctx.send(response)

# Add a command to check current standings
@bot.command(name='standings')
async def show_standings(ctx):
    """Show current weekly standings."""
    if activity_tracker:
        scores = activity_tracker.db.get_weekly_scores()
        if scores:
            response = "📊 **Current Weekly Standings**\n\n"
            for i, (_, name, score) in enumerate(scores[:5], 1):
                response += f"{i}. {name}: {score:.2f} points\n"
            await ctx.send(response)
        else:
            await ctx.send("No activity recorded yet this week!")

@bot.command(name='noslop')
async def noslop(ctx):
    await ctx.send("hey")

# Run the bot
bot.run(BOT_TOKEN)
