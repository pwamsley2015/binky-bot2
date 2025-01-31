from database import Database
from datetime import datetime, timedelta
from backports.zoneinfo import ZoneInfo
import discord
from discord.ext import commands, tasks
from typing import Set, Dict, List
import logging
import random

logger = logging.getLogger('binky.activity')

class ActivityTracker:
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.db = Database()
        # Set of channel IDs that are considered "ranked"
        self.ranked_channels: Set[int] = set()
        
    def set_ranked_channels(self, channel_ids: List[int]) -> None:
        """Set the channel IDs that should be considered ranked channels."""
        self.ranked_channels = set(channel_ids)

    async def on_message(self, message: discord.Message) -> None:
        """Handle new messages."""
        # Ignore bot messages
        if message.author.bot:
            return

        # Ensure user exists in database
        self.db.add_user(message.author.id, str(message.author))
        
        # Record the message
        is_ranked = message.channel.id in self.ranked_channels
        logger.info(f"Recording message from {message.author} in channel {message.channel.name} (ranked: {is_ranked})")
        self.db.record_message(
            message_id=message.id,
            user_id=message.author.id,
            channel_id=message.channel.id,
            is_ranked=is_ranked,
            timestamp=datetime.utcnow()
        )
        
        # Process any mentions in the message
        for mention in message.mentions:
            if not mention.bot:  # Ignore bot mentions
                self.db.add_user(mention.id, str(mention))
                self.db.record_mention(
                    message_id=message.id,
                    mentioned_user_id=mention.id,
                    timestamp=datetime.utcnow()
                )

    async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None:
        """Handle reaction additions."""
        # Ignore bot reactions
        if user.bot:
            return
            
        # Ignore reactions to bot messages
        if reaction.message.author.bot:
            return

        # Ensure both users exist in database
        self.db.add_user(user.id, str(user))
        self.db.add_user(reaction.message.author.id, str(reaction.message.author))
        
        # Record the reaction
        logger.info(f"Recording reaction from {user} on message by {reaction.message.author}")
        self.db.record_reaction(
            message_id=reaction.message.id,
            reactor_id=user.id,
            timestamp=datetime.utcnow()
        )

    @tasks.loop(hours=24)
    async def process_weekly_winner(self) -> None:
        """Process and announce weekly winner. Runs daily but only takes action on Sundays."""
        if datetime.utcnow().weekday() == 6:  # Sunday
            scores = self.db.get_weekly_scores()
            if scores:
                winner_id, winner_name, score = scores[0]  # Get top scorer
                logger.info(f"Weekly winner: {winner_name} with score {score:.2f}")
                logger.info("Top 3 scores: " + ", ".join(f"{name}: {score:.2f}" for _, name, score in scores[:3]))
                
                # Record the winner
                self.db.record_weekly_winner(winner_id, score)
                
                # Announce the winner in all ranked channels
                announcement = (
                    f"🎉 **Weekly Winner Announcement!** 🎉\n\n"
                    f"Congratulations to **{winner_name}** for being this week's most active contributor!\n"
                    f"Score: {score:.2f} points\n\n"
                    f"Top Contributors:\n"
                )
                
                # Add top 3 to announcement
                for i, (_, name, user_score) in enumerate(scores[:3], 1):
                    announcement += f"{i}. {name}: {user_score:.2f} points\n"
                
                for channel_id in self.ranked_channels:
                    channel = self.bot.get_channel(channel_id)
                    if channel:
                        await channel.send(announcement)
                
                # Reset weekly scores
                self.db.reset_weekly_scores()

    def start_tasks(self) -> None:
        """Start background tasks."""
        self.process_weekly_winner.start()

    def cog_unload(self) -> None:
        """Clean up tasks when cog is unloaded."""
        self.process_weekly_winner.cancel()


class PingManager:
    def __init__(self, db: Database, bot: commands.Bot, channel_id: int):
        self.db = db
        self.bot = bot
        self.channel_id = channel_id
        self.questions = self._load_questions()
        self.tz = ZoneInfo('America/Los_Angeles')
    
    def _load_questions(self) -> List[str]:
        """Load questions from questions.txt."""
        with open('questions.txt', 'r', encoding='utf-8') as f:
            return [line.strip() for line in f if line.strip()]
    
    def _is_active_hours(self) -> bool:
        """Check if current time is between 9 AM and 10 PM PT."""
        current_time = datetime.now(self.tz)
        return 9 <= current_time.hour < 22
    
    async def check_and_ping(self) -> None:
        """Check if we should ping someone and do it if conditions are met."""
        if not self._is_active_hours():
            return
            
        # Check last activity
        last_activity = self.db.get_last_activity_time()
        if not last_activity or datetime.utcnow() - last_activity < timedelta(hours=14):
            return
            
        # Check last ping
        last_ping = self.db.get_last_ping_time()
        if last_ping and datetime.utcnow() - last_ping < timedelta(days=7):
            return
            
        # Get candidate members
        candidates = self.db.get_pingable_members()
        if not candidates:
            return
            
        # Select from top 5 (or fewer if less available)
        top_candidates = candidates[:5]
        selected = random.choice(top_candidates)
        
        await self.ping_member(selected[0], selected[1])
    
    async def ping_member(self, user_id: int, username: str, forced: bool = False) -> None:
        """Ping a specific member with a random question."""
        question = random.choice(self.questions)
        channel = self.bot.get_channel(self.channel_id)
        
        if channel:
            await channel.send(f"<@{user_id}>, {question}")
            self.db.record_ping(user_id, question, forced)
    
    @tasks.loop(hours=1)
    async def ping_check_loop(self) -> None:
        """Regular check for inactivity."""
        await self.check_and_ping()
    
    def start(self) -> None:
        """Start the ping check loop."""
        self.ping_check_loop.start()
