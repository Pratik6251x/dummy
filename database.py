import sqlite3
from flask import g
import os

DATABASE = 'sunsync.db'

def get_db():
    from flask import current_app
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
        db.row_factory = sqlite3.Row
    return db

def init_db():
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.executescript('''
        CREATE TABLE IF NOT EXISTS users (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            username        TEXT UNIQUE NOT NULL,
            email           TEXT UNIQUE NOT NULL,
            password        TEXT NOT NULL,
            bio             TEXT DEFAULT '',
            avatar          TEXT DEFAULT '🎓',
            theme           TEXT DEFAULT 'auto',
            notifications   INTEGER DEFAULT 1,
            streak_count    INTEGER DEFAULT 0,
            total_study_time INTEGER DEFAULT 0,
            last_login      TEXT,
            created_at      TEXT DEFAULT (datetime('now'))
        );

        CREATE TABLE IF NOT EXISTS mood_logs (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id   INTEGER NOT NULL,
            mood      TEXT NOT NULL,
            notes     TEXT DEFAULT '',
            timestamp TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS study_sessions (
            id         INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id    INTEGER NOT NULL,
            duration   INTEGER NOT NULL,
            subject    TEXT DEFAULT 'General',
            start_time TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS daily_challenges (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT NOT NULL,
            description TEXT NOT NULL,
            points      INTEGER DEFAULT 10,
            icon        TEXT DEFAULT '⚡'
        );

        CREATE TABLE IF NOT EXISTS user_challenges (
            id           INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id      INTEGER NOT NULL,
            challenge_id INTEGER NOT NULL,
            completed_at TEXT DEFAULT (datetime('now')),
            FOREIGN KEY (user_id)      REFERENCES users(id),
            FOREIGN KEY (challenge_id) REFERENCES daily_challenges(id)
        );

        CREATE TABLE IF NOT EXISTS weekly_goals (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            goal_text     TEXT DEFAULT '',
            target_hours  REAL DEFAULT 10,
            current_hours REAL DEFAULT 0,
            week_start    TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );

        CREATE TABLE IF NOT EXISTS reminders (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id       INTEGER NOT NULL,
            title         TEXT NOT NULL,
            reminder_time TEXT NOT NULL,
            days          TEXT DEFAULT 'Mon,Tue,Wed,Thu,Fri',
            active        INTEGER DEFAULT 1,
            FOREIGN KEY (user_id) REFERENCES users(id)
        );
    ''')

    # Migration: add default_timer column if not present
    try:
        db.execute("ALTER TABLE users ADD COLUMN default_timer INTEGER DEFAULT 30")
        db.commit()
    except Exception:
        pass  # column already exists

    # Seed daily challenges
    existing = db.execute("SELECT COUNT(*) as c FROM daily_challenges").fetchone()
    if existing['c'] == 0:
        challenges = [
            ('Focus Sprint', 'Complete a 30-min focus session', 15, '☀️'),
            ('No Phone Zone', 'Study for 1 hour without touching your phone', 25, '📵'),
            ('Morning Warrior', 'Start studying before 9 AM', 20, '🌅'),
            ('Deep Dive', 'Spend 2 hours on one subject without switching', 30, '🔬'),
            ('Note Master', "Summarize today's lessons in under 200 words", 10, '📝'),
            ('Hydration Hero', 'Drink 8 glasses of water while studying', 10, '💧'),
            ('Streak Keeper', 'Log in and study for at least 30 mins today', 15, '🔥'),
            ('Quiz Yourself', "Test yourself on yesterday's material", 20, '🧠'),
            ('Clean Desk', 'Organize your study space before starting', 10, '✨'),
            ('Early Bird', 'Complete your first session before noon', 15, '🐦'),
        ]
        db.executemany("INSERT INTO daily_challenges (title, description, points, icon) VALUES (?, ?, ?, ?)", challenges)
    db.commit()
    db.close()
