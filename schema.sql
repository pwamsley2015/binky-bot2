-- Users table to track basic user info and streaks
CREATE TABLE users (
    user_id INTEGER PRIMARY KEY,
    username TEXT NOT NULL,
    current_streak INTEGER DEFAULT 0,
    last_active DATE,
    weekly_score REAL DEFAULT 0,
    total_score REAL DEFAULT 0
);

-- Messages table to track all messages
CREATE TABLE messages (
    message_id INTEGER PRIMARY KEY,
    user_id INTEGER NOT NULL,
    channel_id INTEGER NOT NULL,
    is_ranked BOOLEAN NOT NULL,
    timestamp DATETIME NOT NULL,
    points REAL DEFAULT 1,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Reactions table to track reactions given and received
CREATE TABLE reactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    reactor_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    points REAL DEFAULT 0.5,
    FOREIGN KEY (message_id) REFERENCES messages(message_id),
    FOREIGN KEY (reactor_id) REFERENCES users(user_id)
);

-- Mentions table to track user mentions
CREATE TABLE mentions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    mentioned_user_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    points REAL DEFAULT 2,
    FOREIGN KEY (message_id) REFERENCES messages(message_id),
    FOREIGN KEY (mentioned_user_id) REFERENCES users(user_id)
);

-- Weekly winners table for historical tracking
CREATE TABLE weekly_winners (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    week_start DATE NOT NULL,
    week_end DATE NOT NULL,
    total_score REAL NOT NULL,
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Table to track member pings
CREATE TABLE IF NOT EXISTS member_pings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    timestamp DATETIME NOT NULL,
    question TEXT NOT NULL,
    forced BOOLEAN DEFAULT FALSE,  -- Track if it was a manual !ping
    FOREIGN KEY (user_id) REFERENCES users(user_id)
);

-- Create indexes for better query performance
CREATE INDEX idx_messages_user ON messages(user_id);
CREATE INDEX idx_messages_timestamp ON messages(timestamp);
CREATE INDEX idx_reactions_message ON reactions(message_id);
CREATE INDEX idx_mentions_message ON mentions(message_id);
CREATE INDEX idx_weekly_winners_date ON weekly_winners(week_start, week_end);