from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash
from werkzeug.security import generate_password_hash, check_password_hash
from database import init_db, get_db
from datetime import datetime, timedelta
import json
import random
import urllib.request
import os

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'sunsync_secret_key_2024')

# ─── Init DB ───────────────────────────────────────────────────────────────────
with app.app_context():
    init_db()

@app.teardown_appcontext
def close_connection(exception):
    from flask import g
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.context_processor
def inject_globals():
    return dict(session=session, now=datetime.now())

# ─── Auth ──────────────────────────────────────────────────────────────────────
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email    = request.form['email']
        password = generate_password_hash(request.form['password'])
        db = get_db()
        try:
            db.execute('INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
                       (username, email, password))
            db.commit()
            flash('Account created! Please log in.', 'success')
            return redirect(url_for('login'))
        except:
            flash('Username or email already exists.', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        user = db.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        if user and check_password_hash(user['password'], password):
            session['user_id']  = user['id']
            session['username'] = user['username']
            # Update last login & streak
            today = datetime.now().date()
            last  = user['last_login']
            streak = user['streak_count'] or 0
            if last:
                last_date = datetime.strptime(last, '%Y-%m-%d').date()
                if (today - last_date).days == 1:
                    streak += 1
                elif (today - last_date).days > 1:
                    streak = 1
            else:
                streak = 1
            db.execute('UPDATE users SET last_login = ?, streak_count = ? WHERE id = ?',
                       (today.strftime('%Y-%m-%d'), streak, user['id']))
            db.commit()
            session['streak'] = streak
            session['timer_default'] = user['default_timer'] or 30
            return redirect(url_for('dashboard'))
        flash('Invalid credentials.', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('home'))

# ─── Dashboard ─────────────────────────────────────────────────────────────────
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db   = get_db()
    uid  = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()

    today = datetime.now().date().strftime('%Y-%m-%d')
    sessions_today = db.execute(
        "SELECT SUM(duration) as total FROM study_sessions WHERE user_id = ? AND DATE(start_time) = ?",
        (uid, today)).fetchone()
    study_today = sessions_today['total'] or 0

    last_mood = db.execute(
        "SELECT mood FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 1", (uid,)).fetchone()

    recent = db.execute(
        "SELECT * FROM study_sessions WHERE user_id = ? ORDER BY start_time DESC LIMIT 5", (uid,)).fetchall()

    challenges = db.execute("SELECT * FROM daily_challenges ORDER BY RANDOM() LIMIT 3").fetchall()
    completed_ids = [r['challenge_id'] for r in db.execute(
        "SELECT challenge_id FROM user_challenges WHERE user_id = ? AND DATE(completed_at) = ?",
        (uid, today)).fetchall()]

    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date().strftime('%Y-%m-%d')
    goal = db.execute("SELECT * FROM weekly_goals WHERE user_id = ? AND week_start = ?",
                      (uid, week_start)).fetchone()

    leaderboard = db.execute(
        "SELECT username, total_study_time, streak_count FROM users ORDER BY total_study_time DESC LIMIT 5"
    ).fetchall()

    return render_template('dashboard.html',
        user=user,
        study_today=round(study_today / 60, 1),
        last_mood=last_mood['mood'] if last_mood else None,
        recent=recent,
        challenges=challenges,
        completed_ids=completed_ids,
        goal=goal,
        leaderboard=leaderboard
    )

# ─── Focus Mode ────────────────────────────────────────────────────────────────
@app.route('/focus')
def focus():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    user = db.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    return render_template('focus.html', user=user)

@app.route('/api/save_session', methods=['POST'])
def save_session():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data     = request.get_json()
    uid      = session['user_id']
    duration = data.get('duration', 0)
    subject  = data.get('subject', 'General')
    db = get_db()
    db.execute(
        "INSERT INTO study_sessions (user_id, duration, subject, start_time) VALUES (?, ?, ?, ?)",
        (uid, duration, subject, datetime.now().isoformat()))
    db.execute("UPDATE users SET total_study_time = total_study_time + ? WHERE id = ?",
               (duration, uid))
    db.commit()
    return jsonify({'status': 'saved'})

@app.route('/api/set_timer_default', methods=['POST'])
def set_timer_default():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    mins = data.get('minutes', 30)
    if mins not in (30, 45, 120):
        return jsonify({'error': 'invalid duration'}), 400
    db = get_db()
    db.execute('UPDATE users SET default_timer = ? WHERE id = ?', (mins, session['user_id']))
    db.commit()
    session['timer_default'] = mins
    return jsonify({'status': 'saved', 'default_timer': mins})

# ─── Mood Tracking ─────────────────────────────────────────────────────────────
@app.route('/mood', methods=['GET', 'POST'])
def mood():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        selected_mood = request.form['mood']
        notes = request.form.get('notes', '')
        db.execute("INSERT INTO mood_logs (user_id, mood, notes, timestamp) VALUES (?, ?, ?, ?)",
                   (uid, selected_mood, notes, datetime.now().isoformat()))
        db.commit()
        return redirect(url_for('mood'))
    mood_history = db.execute(
        "SELECT * FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 20", (uid,)).fetchall()
    mood_counts = {m: 0 for m in ['Happy', 'Focused', 'Tired', 'Stressed', 'Relaxed']}
    for m in mood_history:
        if m['mood'] in mood_counts:
            mood_counts[m['mood']] += 1
    return render_template('mood.html', mood_history=mood_history, mood_counts=json.dumps(mood_counts))

@app.route('/api/ai_tips', methods=['POST'])
def ai_tips():
    data = request.get_json()
    mood = data.get('mood', 'Focused')
    tips = {
        'Happy':    ['Channel your energy into hard topics!', 'Great time for creative projects.', 'Tackle your most challenging tasks now.', 'Use this mood to set ambitious goals.'],
        'Focused':  ['Perfect for deep work sessions.', 'Try a 90-min flow sprint.', 'Minimize notifications and go deep.', 'This is your peak performance state!'],
        'Tired':    ['Take a 20-min power nap first.', 'Do light review instead of new material.', 'Hydrate and take short breaks.', 'Try 30-min sessions with 10-min breaks.'],
        'Stressed': ['Start with the easiest task to build momentum.', 'Try 5 min of box breathing.', 'Break big tasks into tiny steps.', 'Reward yourself after each small win.'],
        'Relaxed':  ['Good for reading and passive review.', 'Great time to plan your week.', 'Try creative brainstorming.', 'Review flashcards or notes slowly.'],
    }
    selected = random.sample(tips.get(mood, tips['Focused']), min(3, len(tips.get(mood, []))))
    study_modes = {
        'Happy':    'Power Sprint Mode 🚀',
        'Focused':  'Deep Work Mode 🎯',
        'Tired':    'Gentle Review Mode 💤',
        'Stressed': 'Calm Focus Mode 🌿',
        'Relaxed':  'Exploration Mode 🌊',
    }
    return jsonify({'tips': selected, 'mode': study_modes.get(mood, 'Focus Mode')})

# ─── Analytics ─────────────────────────────────────────────────────────────────
@app.route('/analytics')
def analytics():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']

    daily_data = []
    for i in range(6, -1, -1):
        day = (datetime.now() - timedelta(days=i)).date().strftime('%Y-%m-%d')
        row = db.execute(
            "SELECT SUM(duration) as total FROM study_sessions WHERE user_id = ? AND DATE(start_time) = ?",
            (uid, day)).fetchone()
        daily_data.append({'date': day, 'minutes': round((row['total'] or 0) / 60, 1)})

    subjects = db.execute(
        "SELECT subject, SUM(duration) as total FROM study_sessions WHERE user_id = ? GROUP BY subject",
        (uid,)).fetchall()
    subject_data = {s['subject']: round(s['total'] / 60, 1) for s in subjects}

    mood_trend = db.execute(
        "SELECT mood, DATE(timestamp) as day FROM mood_logs WHERE user_id = ? ORDER BY timestamp DESC LIMIT 14",
        (uid,)).fetchall()

    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()

    return render_template('analytics.html',
        daily_data=json.dumps(daily_data),
        subject_data=json.dumps(subject_data),
        mood_trend=json.dumps([dict(r) for r in mood_trend]),
        user=user
    )

# ─── Profile ───────────────────────────────────────────────────────────────────
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        bio    = request.form.get('bio', '')
        avatar = request.form.get('avatar', '👤')
        db.execute("UPDATE users SET bio = ?, avatar = ? WHERE id = ?", (bio, avatar, uid))
        db.commit()
        flash('Profile updated!', 'success')
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    total_sessions = db.execute("SELECT COUNT(*) as c FROM study_sessions WHERE user_id = ?", (uid,)).fetchone()
    return render_template('profile.html', user=user, total_sessions=total_sessions['c'])

# ─── Account (Edit username / email / password) ────────────────────────────────
@app.route('/account', methods=['GET', 'POST'])
def account():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']

    if request.method == 'POST':
        errors = []
        new_username = request.form.get('username', '').strip()
        new_email    = request.form.get('email', '').strip()
        new_password = request.form.get('password', '').strip()
        confirm_pw   = request.form.get('confirm_password', '').strip()

        if not new_username or len(new_username) < 3:
            errors.append('Username must be at least 3 characters.')
        if '@' not in new_email or '.' not in new_email:
            errors.append('Please enter a valid email address.')
        if new_password and new_password != confirm_pw:
            errors.append('Passwords do not match.')
        if new_password and len(new_password) < 6:
            errors.append('Password must be at least 6 characters.')

        clash_user  = db.execute(
            'SELECT id FROM users WHERE username = ? AND id != ?', (new_username, uid)).fetchone()
        clash_email = db.execute(
            'SELECT id FROM users WHERE email = ? AND id != ?', (new_email, uid)).fetchone()
        if clash_user:
            errors.append('That username is already taken.')
        if clash_email:
            errors.append('That email is already registered.')

        if errors:
            for e in errors:
                flash(e, 'error')
        else:
            if new_password:
                db.execute(
                    'UPDATE users SET username=?, email=?, password=? WHERE id=?',
                    (new_username, new_email, generate_password_hash(new_password), uid))
            else:
                db.execute(
                    'UPDATE users SET username=?, email=? WHERE id=?',
                    (new_username, new_email, uid))
            db.commit()
            session['username'] = new_username
            flash('Account updated successfully! ✅', 'success')
            return redirect(url_for('account'))

    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    return render_template('account.html', user=user)

# ─── Leaderboard ───────────────────────────────────────────────────────────────
@app.route('/leaderboard')
def leaderboard():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db = get_db()
    board = db.execute(
        "SELECT username, avatar, total_study_time, streak_count FROM users ORDER BY total_study_time DESC LIMIT 20"
    ).fetchall()
    return render_template('leaderboard.html', board=board, current_user=session['username'])

# ─── Weekly Goals ──────────────────────────────────────────────────────────────
@app.route('/api/set_goal', methods=['POST'])
def set_goal():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data  = request.get_json()
    uid   = session['user_id']
    db    = get_db()
    week_start = (datetime.now() - timedelta(days=datetime.now().weekday())).date().strftime('%Y-%m-%d')
    existing = db.execute("SELECT id FROM weekly_goals WHERE user_id = ? AND week_start = ?",
                          (uid, week_start)).fetchone()
    if existing:
        db.execute("UPDATE weekly_goals SET goal_text = ?, target_hours = ? WHERE id = ?",
                   (data.get('goal_text', ''), data.get('target_hours', 10), existing['id']))
    else:
        db.execute("INSERT INTO weekly_goals (user_id, goal_text, target_hours, current_hours, week_start) VALUES (?, ?, ?, 0, ?)",
                   (uid, data.get('goal_text', ''), data.get('target_hours', 10), week_start))
    db.commit()
    return jsonify({'status': 'saved'})

# ─── Challenges ────────────────────────────────────────────────────────────────
@app.route('/api/complete_challenge', methods=['POST'])
def complete_challenge():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    uid  = session['user_id']
    cid  = data.get('challenge_id')
    db   = get_db()
    today = datetime.now().date().strftime('%Y-%m-%d')
    existing = db.execute(
        "SELECT id FROM user_challenges WHERE user_id = ? AND challenge_id = ? AND DATE(completed_at) = ?",
        (uid, cid, today)).fetchone()
    if not existing:
        db.execute("INSERT INTO user_challenges (user_id, challenge_id, completed_at) VALUES (?, ?, ?)",
                   (uid, cid, datetime.now().isoformat()))
        db.commit()
    return jsonify({'status': 'completed'})

# ─── Settings ──────────────────────────────────────────────────────────────────
@app.route('/settings', methods=['GET', 'POST'])
def settings():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']
    if request.method == 'POST':
        theme = request.form.get('theme', 'auto')
        notifs = 1 if request.form.get('notifications') else 0
        db.execute("UPDATE users SET theme = ?, notifications = ? WHERE id = ?", (theme, notifs, uid))
        db.commit()
        flash('Settings saved!', 'success')
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()
    reminders = db.execute("SELECT * FROM reminders WHERE user_id = ?", (uid,)).fetchall()
    return render_template('settings.html', user=user, reminders=reminders)

@app.route('/api/add_reminder', methods=['POST'])
def add_reminder():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    uid  = session['user_id']
    db   = get_db()
    db.execute("INSERT INTO reminders (user_id, title, reminder_time, days) VALUES (?, ?, ?, ?)",
               (uid, data.get('title'), data.get('time'), data.get('days', 'Mon,Tue,Wed,Thu,Fri')))
    db.commit()
    return jsonify({'status': 'added'})

# ─── Solaris Chatbot ───────────────────────────────────────────────────────────
SOLARIS_SYSTEM = """You are Solaris, a warm and motivating AI study assistant built into SunSync — a sunrise-themed productivity app for college students. SunSync features:
- Focus Mode: timer with 30-min (Focus), 45-min (Deep Work), and 120-min (Marathon) sessions
- Mood Tracking: log Happy, Focused, Tired, Stressed, or Relaxed
- Analytics: charts for daily study time, subject breakdown, mood trend
- Weekly Goals: set target study hours each week
- Leaderboard: global ranking by total study time
- Daily Challenges: micro-challenges worth points
- Streaks: daily login streak tracking
- Settings: theme (dark/light/auto), reminders, edit account
- Gaming Zone: stress-relief mini-games — Snake, Jumping Ball, Memory Cards, and Reaction Speed. Perfect for short mental breaks!

Keep replies concise (3-5 sentences max unless the user asks for detail). Be encouraging, upbeat, and use sunrise/dawn metaphors occasionally. If asked about a feature, explain it clearly. If asked something outside your knowledge, say so kindly."""

@app.route('/api/chat', methods=['POST'])
def chat():
    if 'user_id' not in session:
        return jsonify({'error': 'unauthorized'}), 401
    data = request.get_json()
    messages = data.get('messages', [])
    if not messages:
        return jsonify({'error': 'no messages'}), 400

    api_key = os.environ.get('ANTHROPIC_API_KEY', '')
    if not api_key:
        fallback = {
            'focus':      "Focus Mode lets you pick a 30, 45, or 120-minute session. Hit ▶ Start and SunSync tracks your time automatically! ☀️",
            'mood':       "Head to Mood Track and tap how you're feeling. SunSync will suggest a matching study mode!",
            'streak':     "Your streak ticks up every day you log in and study. Keep the sunrise energy going! 🔥",
            'challenge':  "Each day brings 3 new micro-challenges. Complete them for bonus points on the leaderboard!",
            'goal':       "In Dashboard you can set a weekly study-hours goal and watch the progress bar fill up. 🌅",
            'leaderboard':"The Leaderboard ranks all students by total study time. Grind those sessions! 🏆",
            'timer':      "You can set your default timer in Edit Account — choose 30 min, 45 min, or the 2-hour Marathon mode.",
            'account':    "Go to Edit Account to update your username, email, or password anytime.",
        }
        user_text = (messages[-1].get('content') or '').lower()
        reply = next((v for k, v in fallback.items() if k in user_text),
                     "I'm Solaris ☀️, your SunSync study assistant! Ask me about Focus Mode, streaks, challenges, goals, or anything else.")
        return jsonify({'reply': reply})

    payload = json.dumps({
        'model': 'claude-sonnet-4-20250514',
        'max_tokens': 300,
        'system': SOLARIS_SYSTEM,
        'messages': messages[-10:],
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.anthropic.com/v1/messages',
        data=payload,
        headers={
            'Content-Type': 'application/json',
            'x-api-key': api_key,
            'anthropic-version': '2023-06-01',
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
        reply = result['content'][0]['text']
        return jsonify({'reply': reply})
    except Exception:
        return jsonify({'reply': "I'm having a little trouble connecting right now. Try again in a moment! ☀️"}), 200

# ─── Weekly Summary ────────────────────────────────────────────────────────────
@app.route('/weekly')
def weekly():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    db  = get_db()
    uid = session['user_id']
    user = db.execute('SELECT * FROM users WHERE id = ?', (uid,)).fetchone()

    weeks = []
    for w in range(4):
        week_end   = datetime.now() - timedelta(weeks=w)
        week_start = week_end - timedelta(days=6)
        rows = db.execute(
            "SELECT SUM(duration) as total, COUNT(*) as sessions FROM study_sessions "
            "WHERE user_id = ? AND DATE(start_time) BETWEEN ? AND ?",
            (uid, week_start.date().strftime('%Y-%m-%d'), week_end.date().strftime('%Y-%m-%d'))
        ).fetchone()
        top_subject = db.execute(
            "SELECT subject, SUM(duration) as dur FROM study_sessions "
            "WHERE user_id = ? AND DATE(start_time) BETWEEN ? AND ? "
            "GROUP BY subject ORDER BY dur DESC LIMIT 1",
            (uid, week_start.date().strftime('%Y-%m-%d'), week_end.date().strftime('%Y-%m-%d'))
        ).fetchone()
        moods = db.execute(
            "SELECT mood, COUNT(*) as c FROM mood_logs "
            "WHERE user_id = ? AND DATE(timestamp) BETWEEN ? AND ? "
            "GROUP BY mood ORDER BY c DESC LIMIT 1",
            (uid, week_start.date().strftime('%Y-%m-%d'), week_end.date().strftime('%Y-%m-%d'))
        ).fetchone()
        weeks.append({
            'label':       f"Week of {week_start.strftime('%b %d')}",
            'minutes':     round((rows['total'] or 0) / 60),
            'sessions':    rows['sessions'] or 0,
            'top_subject': top_subject['subject'] if top_subject else '—',
            'top_mood':    moods['mood'] if moods else '—',
        })
    return render_template('weekly.html', user=user, weeks=weeks, weeks_json=json.dumps(weeks))

# ─── Gaming Zone ──────────────────────────────────────────────────────────────
@app.route('/gaming')
def gaming():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    return render_template('gaming.html')

# ─── Error Handlers ────────────────────────────────────────────────────────────
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('404.html', code=500, msg='Internal Server Error'), 500

if __name__ == '__main__':
    app.run(debug=True, port=5000)
