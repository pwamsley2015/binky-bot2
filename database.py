import sqlite3
from datetime import datetime, date
from typing import Optional, List, Tuple
import os
import logging

logger = logging.getLogger('binky.database')

class Database:
    def __init__(self, db_path: str = "binky_bot.db"):
        """Initialize database connection and create tables if they don't exist."""
        self.db_path = db_path
        self._create_tables()

    def _create_tables(self):
        """Create all necessary tables if they don't exist."""
        with open('schema.sql', 'r') as f:
            schema = f.read()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(schema)
            conn.commit()

    def add_user(self, user_id: int, username: str) -> None:
        """Add a new user or update existing user's username."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO users (user_id, username)
                VALUES (?, ?)
                ON CONFLICT(user_id) DO UPDATE SET username = excluded.username
            """, (user_id, username))
            conn.commit()

    def record_message(self, message_id: int, user_id: int, channel_id: int, 
                      is_ranked: bool, timestamp: datetime) -> None:
        """Record a new message."""
        base_points = 1.5 if is_ranked else 1.0
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO messages (message_id, user_id, channel_id, is_ranked, timestamp, points)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (message_id, user_id, channel_id, is_ranked, timestamp, base_points))
            
            # Update user's last active date and streak
            self._update_user_streak(conn, user_id, timestamp.date())
            conn.commit()

    def record_reaction(self, message_id: int, reactor_id: int, timestamp: datetime) -> None:
        """Record a new reaction."""
        with sqlite3.connect(self.db_path) as conn:
            # Count existing reactions from this user on this message
            existing_count = conn.execute("""
                SELECT COUNT(*) FROM reactions 
                WHERE message_id = ? AND reactor_id = ?
            """, (message_id, reactor_id)).fetchone()[0]
            
            # Calculate points (0.5 for first reaction, 0.2 for subsequent)
            points = 0.2 if existing_count > 0 else 0.5
            
            conn.execute("""
                INSERT INTO reactions (message_id, reactor_id, timestamp, points)
                VALUES (?, ?, ?, ?)
            """, (message_id, reactor_id, timestamp, points))
            conn.commit()

    def record_mention(self, message_id: int, mentioned_user_id: int, timestamp: datetime) -> None:
        """Record a new user mention."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO mentions (message_id, mentioned_user_id, timestamp)
                VALUES (?, ?, ?)
            """, (message_id, mentioned_user_id, timestamp))
            conn.commit()

    def _update_user_streak(self, conn: sqlite3.Connection, user_id: int, current_date: date) -> None:
        """Update user's activity streak."""
        last_active = conn.execute("""
            SELECT last_active FROM users WHERE user_id = ?
        """, (user_id,)).fetchone()

        if last_active:
            last_active = datetime.strptime(last_active[0], '%Y-%m-%d').date()
            days_diff = (current_date - last_active).days
            
            if days_diff == 1:  # Consecutive day
                conn.execute("""
                    UPDATE users 
                    SET current_streak = current_streak + 1,
                        last_active = ?
                    WHERE user_id = ?
                """, (current_date, user_id))
            elif days_diff > 1:  # Streak broken
                conn.execute("""
                    UPDATE users 
                    SET current_streak = 1,
                        last_active = ?
                    WHERE user_id = ?
                """, (current_date, user_id))
        else:  # First activity
            conn.execute("""
                UPDATE users 
                SET current_streak = 1,
                    last_active = ?
                WHERE user_id = ?
            """, (current_date, user_id))

    def get_weekly_scores(self) -> List[Tuple[int, str, float]]:
        """Get scores for all users for the current week."""
        with sqlite3.connect(self.db_path) as conn:
            return conn.execute("""
                SELECT u.user_id, u.username, 
                       COALESCE(SUM(m.points), 0) + 
                       COALESCE(SUM(r.points), 0) + 
                       COALESCE(SUM(men.points), 0) AS total_score
                FROM users u
                LEFT JOIN messages m ON u.user_id = m.user_id 
                    AND m.timestamp >= date('now', '-7 days')
                LEFT JOIN reactions r ON m.message_id = r.message_id
                LEFT JOIN mentions men ON m.message_id = men.message_id
                GROUP BY u.user_id, u.username
                ORDER BY total_score DESC
            """).fetchall()

    def record_weekly_winner(self, user_id: int, score: float) -> None:
        """Record a weekly winner."""
        week_start = date.today() - datetime.timedelta(days=7)
        week_end = date.today()
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO weekly_winners (user_id, week_start, week_end, total_score)
                VALUES (?, ?, ?, ?)
            """, (user_id, week_start, week_end, score))
            conn.commit()

    def reset_weekly_scores(self) -> None:
        """Reset weekly scores while maintaining streaks."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE users SET weekly_score = 0")
            conn.commit()
            
    def get_recent_activity(self, limit: int = 10) -> List[str]:
        """Get recent activity for debugging purposes."""
        with sqlite3.connect(self.db_path) as conn:
            # Get recent messages
            messages = conn.execute("""
                SELECT u.username, m.timestamp, m.is_ranked, m.points
                FROM messages m
                JOIN users u ON m.user_id = u.user_id
                ORDER BY m.timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            # Get recent reactions
            reactions = conn.execute("""
                SELECT u.username, r.timestamp, r.points
                FROM reactions r
                JOIN users u ON r.reactor_id = u.user_id
                ORDER BY r.timestamp DESC
                LIMIT ?
            """, (limit,)).fetchall()
            
            # Combine and sort activities
            activities = []
            for username, timestamp, is_ranked, points in messages:
                activities.append(f"Message by {username} ({'ranked' if is_ranked else 'social'}) - {points} points")
            
            for username, timestamp, points in reactions:
                activities.append(f"Reaction by {username} - {points} points")
            
            return activities[:limit]
