# 🌙 MoodSync Lite – Smart Productivity Web App
Link : https://dummy-zeta-pearl.vercel.app/

A **cosmic-themed**, mood-aware productivity web app for college students.
Track mood, focus with Pomodoro, analyse study habits, and compete on leaderboards.

---

## ✨ Features

| Feature | Description |
|---|---|
| 🎯 Focus Mode | Pomodoro (25/5/15/45 min) timer with ring animation |
| 💜 Mood Tracking | Log Happy/Focused/Tired/Stressed/Relaxed + history |
| 🤖 AI Study Tips | Mood-based personalised study recommendations |
| 📊 Analytics | Daily bar chart, subject breakdown doughnut, mood timeline |
| 🔥 Streaks | Daily login streak tracking + achievements |
| ⚡ Challenges | Randomised daily micro-challenges with points |
| 🏆 Leaderboard | Global ranking by total study time |
| 🎯 Weekly Goals | Set and track weekly study hour targets |
| 🔔 Reminders | Schedule study reminders by day and time |
| 🌙 Dark/Light Mode | Auto-detect from system + manual toggle |

---

## 🚀 Quick Start

### 1. Clone / unzip the project
```bash
cd moodsync_lite
```

### 2. Create a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
venv\Scripts\activate           # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the app
```bash
python app.py
```

### 5. Open your browser
```
http://localhost:5000
```

---

## 📁 Project Structure

```
moodsync_lite/
├── app.py               ← Flask routes & API endpoints
├── database.py          ← SQLite init & schema
├── moodsync.db          ← Auto-created SQLite database
├── requirements.txt
├── static/
│   ├── css/style.css    ← Complete purple/blue cosmic CSS
│   └── js/main.js       ← Timer, charts, interactions
└── templates/
    ├── base.html         ← Sidebar, mobile nav, theme toggle
    ├── home.html         ← Landing page
    ├── login.html
    ├── register.html
    ├── dashboard.html    ← Stats, challenges, leaderboard widget
    ├── focus.html        ← Pomodoro timer + AI tips
    ├── mood.html         ← Mood selector + history + chart
    ├── analytics.html    ← Charts: daily, subject, mood trend
    ├── profile.html      ← Avatar, bio, achievements
    ├── leaderboard.html  ← Global student rankings
    └── settings.html     ← Theme, reminders, account
```

---

## 🗃️ Database Schema

```sql
users          (id, username, email, password, bio, avatar, theme,
                notifications, streak_count, total_study_time,
                last_login, created_at)
mood_logs      (id, user_id, mood, notes, timestamp)
study_sessions (id, user_id, duration, subject, start_time)
daily_challenges  (id, title, description, points, icon)
user_challenges   (id, user_id, challenge_id, completed_at)
weekly_goals   (id, user_id, goal_text, target_hours, current_hours, week_start)
reminders      (id, user_id, title, reminder_time, days, active)
```

---

## 🌐 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/save_session` | Save a completed focus session |
| POST | `/api/ai_tips` | Get AI study tips based on mood |
| POST | `/api/set_goal` | Create/update weekly goal |
| POST | `/api/complete_challenge` | Mark a daily challenge done |
| POST | `/api/add_reminder` | Add a new study reminder |

---

## 🛠️ Tech Stack

- **Frontend**: HTML5 · CSS3 · Vanilla JS · Chart.js
- **Backend**: Python · Flask
- **Database**: SQLite (via sqlite3)
- **Fonts**: Syne (headings) · DM Sans (body)
- **Design**: Glassmorphism · Purple/Blue cosmic theme · Dark/Light mode

---

## 🚀 Deploy to Production

For production, use **Gunicorn** + **Nginx**:

```bash
pip install gunicorn
gunicorn -w 4 -b 0.0.0.0:8000 app:app
```

Change `app.secret_key` to a secure random string before deploying.

---

Built with 💜 for students who want to study smarter.
