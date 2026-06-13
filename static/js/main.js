// ── Theme ────────────────────────────────────────────────────────────────────
function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
  } else if (theme === 'light') {
    document.documentElement.setAttribute('data-theme', 'light');
  } else {
    const pref = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', pref);
  }
}
function toggleTheme() {
  const cur = document.documentElement.getAttribute('data-theme');
  const next = cur === 'dark' ? 'light' : 'dark';
  document.documentElement.setAttribute('data-theme', next);
  localStorage.setItem('ms_theme', next);
}
(function () {
  const saved = localStorage.getItem('ms_theme');
  applyTheme(saved || 'dark');
})();

// ── Sidebar mobile ───────────────────────────────────────────────────────────
function toggleSidebar() {
  const sb = document.getElementById('sidebar');
  const ov = document.getElementById('overlay');
  if (sb) sb.classList.toggle('open');
  if (ov) ov.classList.toggle('show');
}

// ── Stars background ─────────────────────────────────────────────────────────
function createStars() {
  const container = document.querySelector('.stars');
  if (!container) return;
  for (let i = 0; i < 80; i++) {
    const s = document.createElement('div');
    s.className = 'star';
    const size = Math.random() * 3 + 1;
    s.style.cssText = `
      width:${size}px;height:${size}px;
      left:${Math.random() * 100}%;top:${Math.random() * 100}%;
      --op:${(Math.random() * 0.6 + 0.1).toFixed(2)};
      --dur:${(Math.random() * 4 + 2).toFixed(1)}s;
      --delay:-${(Math.random() * 5).toFixed(1)}s;
    `;
    container.appendChild(s);
  }
}
document.addEventListener('DOMContentLoaded', createStars);

// ── Flash message auto-dismiss ───────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const flashes = document.querySelectorAll('.flash-msg');
  flashes.forEach(f => {
    setTimeout(() => {
      f.style.opacity = '0';
      f.style.transform = 'translateY(-10px)';
      f.style.transition = 'all .4s ease';
      setTimeout(() => f.remove(), 400);
    }, 3500);
  });
});

// ── Pomodoro / Focus Timer ───────────────────────────────────────────────────
const MODES = {
  short:   30 * 60,
  medium:  45 * 60,
  long:   120 * 60,
};
let timerInterval = null;
let currentMode = localStorage.getItem('ms_default_timer') || 'short';
let timeLeft = MODES[currentMode] || MODES.short;
let timerRunning = false;
let sessionStart = null;
let totalCircumference = 754; // 2π × r(120) ≈ 754

function updateTimerDisplay() {
  const m = Math.floor(timeLeft / 60).toString().padStart(2, '0');
  const s = (timeLeft % 60).toString().padStart(2, '0');
  const el = document.getElementById('timer-time');
  if (el) el.textContent = `${m}:${s}`;

  const total = MODES[currentMode];
  const progress = (total - timeLeft) / total;
  const offset = totalCircumference * (1 - progress);
  const ring = document.getElementById('timer-ring');
  if (ring) ring.style.strokeDashoffset = totalCircumference - (totalCircumference * progress);
}

function setMode(mode) {
  if (timerRunning) stopTimer();
  currentMode = mode;
  timeLeft = MODES[mode];
  document.querySelectorAll('.timer-mode-tab').forEach(t => t.classList.remove('active'));
  const tab = document.querySelector(`[data-mode="${mode}"]`);
  if (tab) tab.classList.add('active');
  const ring = document.getElementById('timer-ring');
  if (ring) ring.style.strokeDashoffset = 0;
  updateTimerDisplay();
}

function startTimer() {
  if (timerRunning) return;
  timerRunning = true;
  sessionStart = Date.now();
  const btn = document.getElementById('start-btn');
  if (btn) { btn.textContent = '⏸ Pause'; btn.onclick = pauseTimer; }
  const wrap = document.querySelector('.timer-ring-wrap');
  if (wrap) wrap.classList.add('timer-pulse');
  timerInterval = setInterval(() => {
    timeLeft--;
    updateTimerDisplay();
    if (timeLeft <= 0) {
      clearInterval(timerInterval);
      timerRunning = false;
      onTimerComplete();
    }
  }, 1000);
}

function pauseTimer() {
  clearInterval(timerInterval);
  timerRunning = false;
  const btn = document.getElementById('start-btn');
  if (btn) { btn.textContent = '▶ Resume'; btn.onclick = startTimer; }
  const wrap = document.querySelector('.timer-ring-wrap');
  if (wrap) wrap.classList.remove('timer-pulse');
}

function stopTimer() {
  clearInterval(timerInterval);
  timerRunning = false;
  if (sessionStart) saveSession();
  sessionStart = null;
  timeLeft = MODES[currentMode];
  updateTimerDisplay();
  const btn = document.getElementById('start-btn');
  if (btn) { btn.textContent = '▶ Start'; btn.onclick = startTimer; }
  const ring = document.getElementById('timer-ring');
  if (ring) ring.style.strokeDashoffset = 0;
  const wrap = document.querySelector('.timer-ring-wrap');
  if (wrap) wrap.classList.remove('timer-pulse');
}

function onTimerComplete() {
  saveSession();
  sessionStart = null;
  const wrap = document.querySelector('.timer-ring-wrap');
  if (wrap) wrap.classList.remove('timer-pulse');
  showNotif('🎉 Session Complete!', 'Great work! Take a break.');
  const btn = document.getElementById('start-btn');
  if (btn) { btn.textContent = '▶ Start'; btn.onclick = startTimer; }
  // Auto start break for pomodoro
  if (currentMode === 'pomodoro') {
    setTimeout(() => setMode('short'), 1000);
  }
}

function saveSession() {
  const elapsed = sessionStart ? Math.round((Date.now() - sessionStart) / 1000) : 0;
  if (elapsed < 30) return;
  const subject = document.getElementById('subject-input')?.value || 'General';
  fetch('/api/save_session', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ duration: elapsed, subject })
  });
}

// ── AI Tips ──────────────────────────────────────────────────────────────────
async function getAITips(mood) {
  const box = document.getElementById('ai-tips-box');
  if (!box) return;
  box.innerHTML = '<div style="color:var(--text-muted);font-size:14px;text-align:center;padding:16px">🤔 Analysing your mood...</div>';
  try {
    const res = await fetch('/api/ai_tips', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ mood })
    });
    const data = await res.json();
    box.innerHTML = `
      <div style="margin-bottom:12px">
        <span style="font-size:12px;color:var(--text-muted);text-transform:uppercase;letter-spacing:.08em">Recommended Mode</span>
        <div style="font-family:'Syne',sans-serif;font-size:18px;font-weight:700;color:var(--p3);margin-top:4px">${data.mode}</div>
      </div>
      <div style="font-size:12px;color:var(--text-muted);margin-bottom:10px;text-transform:uppercase;letter-spacing:.06em">AI Study Tips</div>
      ${data.tips.map(t => `<div class="tip-item"><span class="tip-dot">✦</span><span>${t}</span></div>`).join('')}
    `;
  } catch(e) {
    box.innerHTML = '<div style="color:var(--red);font-size:14px">Failed to load tips.</div>';
  }
}

// ── Mood selection ────────────────────────────────────────────────────────────
function selectMood(btn, mood) {
  document.querySelectorAll('.mood-btn').forEach(b => b.classList.remove('selected'));
  btn.classList.add('selected');
  const input = document.getElementById('mood-input');
  if (input) input.value = mood;
  getAITips(mood);
}

// ── Challenge complete ────────────────────────────────────────────────────────
async function completeChallenge(id, el) {
  await fetch('/api/complete_challenge', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ challenge_id: id })
  });
  el.classList.add('done');
  el.querySelector('.challenge-pts').textContent = '✅';
  showNotif('⚡ Challenge Complete!', 'Keep up the great work!');
}

// ── Weekly goal ───────────────────────────────────────────────────────────────
async function saveGoal() {
  const text    = document.getElementById('goal-text')?.value;
  const hours   = document.getElementById('goal-hours')?.value || 10;
  await fetch('/api/set_goal', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ goal_text: text, target_hours: parseFloat(hours) })
  });
  showNotif('🎯 Goal saved!', 'You got this!');
}

// ── Add reminder ──────────────────────────────────────────────────────────────
async function addReminder() {
  const title = document.getElementById('rem-title')?.value;
  const time  = document.getElementById('rem-time')?.value;
  const days  = Array.from(document.querySelectorAll('.day-check:checked')).map(c => c.value).join(',');
  if (!title || !time) return;
  await fetch('/api/add_reminder', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ title, time, days })
  });
  showNotif('🔔 Reminder added!', `Reminder set for ${time}`);
  setTimeout(() => location.reload(), 1000);
}

// ── Notification toast ────────────────────────────────────────────────────────
function showNotif(title, body) {
  const n = document.createElement('div');
  n.style.cssText = `
    position:fixed;bottom:24px;right:24px;z-index:9999;
    background:rgba(13,13,26,.95);backdrop-filter:blur(20px);
    border:1px solid rgba(139,92,246,.4);border-radius:16px;
    padding:16px 20px;min-width:260px;max-width:320px;
    box-shadow:0 8px 40px rgba(0,0,0,.4),0 0 30px rgba(139,92,246,.2);
    animation:slideIn .4s cubic-bezier(.4,0,.2,1);
  `;
  n.innerHTML = `
    <div style="font-family:'Syne',sans-serif;font-weight:700;font-size:15px;margin-bottom:4px;color:var(--text)">${title}</div>
    <div style="font-size:13px;color:var(--text-muted)">${body}</div>
  `;
  const style = document.createElement('style');
  style.textContent = '@keyframes slideIn{from{opacity:0;transform:translateX(30px)}to{opacity:1;transform:translateX(0)}}';
  document.head.appendChild(style);
  document.body.appendChild(n);
  setTimeout(() => { n.style.opacity='0'; n.style.transition='opacity .4s'; setTimeout(() => n.remove(), 400); }, 3500);
}

// ── Profile avatar picker ─────────────────────────────────────────────────────
function selectAvatar(el, emoji) {
  document.querySelectorAll('.avatar-option').forEach(a => a.classList.remove('selected'));
  el.classList.add('selected');
  const input = document.getElementById('avatar-input');
  if (input) input.value = emoji;
  const preview = document.getElementById('avatar-preview');
  if (preview) preview.textContent = emoji;
}

// ── Chart.js helpers ──────────────────────────────────────────────────────────
function buildBarChart(id, labels, data, color1, color2) {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  const isDark = document.documentElement.getAttribute('data-theme') !== 'light';
  new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: labels.map((_, i) => {
          const g = ctx.getContext('2d').createLinearGradient(0, 0, 0, 260);
          g.addColorStop(0, color1);
          g.addColorStop(1, color2);
          return g;
        }),
        borderRadius: 8,
        borderSkipped: false,
      }]
    },
    options: {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        x: { grid: { color: 'rgba(255,255,255,.05)' }, ticks: { color: isDark ? '#8888aa' : '#5555aa', font: { family: 'DM Sans', size: 12 } } },
        y: { grid: { color: 'rgba(255,255,255,.05)' }, ticks: { color: isDark ? '#8888aa' : '#5555aa', font: { family: 'DM Sans', size: 12 } } }
      }
    }
  });
}

function buildDoughnut(id, labels, data, colors) {
  const ctx = document.getElementById(id);
  if (!ctx) return;
  new Chart(ctx, {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{ data, backgroundColor: colors, borderWidth: 0, hoverOffset: 8 }]
    },
    options: {
      responsive: true, maintainAspectRatio: false, cutout: '70%',
      plugins: {
        legend: { position: 'bottom', labels: { color: '#8888aa', font: { family: 'DM Sans', size: 12 }, padding: 16 } }
      }
    }
  });
}

// ── Countdown greeting ────────────────────────────────────────────────────────
function updateGreeting() {
  const el = document.getElementById('greeting-time');
  if (!el) return;
  const h = new Date().getHours();
  const greeting = h < 12 ? '🌅 Good morning' : h < 17 ? '☀️ Good afternoon' : h < 21 ? '🌆 Good evening' : '🌙 Good night';
  el.textContent = greeting + ' · ' + new Date().toLocaleDateString('en-US', { weekday: 'long', month: 'long', day: 'numeric' });
}
document.addEventListener('DOMContentLoaded', updateGreeting);

// ── Particle burst ────────────────────────────────────────────────────────────
function burstParticles(x, y) {
  const colors = ['#8b5cf6','#a78bfa','#06b6d4','#10b981','#f59e0b','#ec4899'];
  for (let i = 0; i < 24; i++) {
    const p = document.createElement('div');
    const angle = (Math.PI * 2 * i) / 24;
    const speed = 60 + Math.random() * 80;
    const size  = 4 + Math.random() * 6;
    p.style.cssText = `
      position:fixed;left:${x}px;top:${y}px;
      width:${size}px;height:${size}px;
      background:${colors[Math.floor(Math.random()*colors.length)]};
      border-radius:50%;pointer-events:none;z-index:9999;
      transition:all .8s cubic-bezier(.2,0,.8,1);
      transform:translate(-50%,-50%);
    `;
    document.body.appendChild(p);
    requestAnimationFrame(() => {
      p.style.left  = `${x + Math.cos(angle) * speed}px`;
      p.style.top   = `${y + Math.sin(angle) * speed}px`;
      p.style.opacity = '0';
      p.style.transform = 'translate(-50%,-50%) scale(0)';
    });
    setTimeout(() => p.remove(), 900);
  }
}

// Wrap timer complete to add burst
const _onTimerComplete = onTimerComplete;
window.onTimerComplete = function() {
  const wrap = document.querySelector('.timer-ring-wrap');
  if (wrap) {
    const r = wrap.getBoundingClientRect();
    burstParticles(r.left + r.width/2, r.top + r.height/2);
  }
  _onTimerComplete();
};

// ── Load sidebar streak ───────────────────────────────────────────────────────
document.addEventListener('DOMContentLoaded', () => {
  const el = document.getElementById('sidebar-streak');
  if (!el) return;
  // Read from a meta tag injected server-side if present
  const meta = document.querySelector('meta[name="user-streak"]');
  if (meta) el.textContent = meta.getAttribute('content');
});
