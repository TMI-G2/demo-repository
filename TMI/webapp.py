"""
webapp.py
----------
Front-facing web application for Instagram, Twitter, and LinkedIn PII risk scoring.
Runs on port 5001.

Start with:
  python webapp.py

Then open in any browser:
  http://localhost:5001          (desktop)
  http://100.x.x.x:5001         (laptop via Tailscale)
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import logging
import threading
import uuid
from flask import Flask, request, jsonify, render_template_string, send_file

import config
from utils.apify_scraper import (
    fetch_instagram_profile,
    fetch_instagram_comments,
    fetch_twitter_profile,
    fetch_linkedin_profile,
)
from utils.ollama_scorer import score_profile

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
log = logging.getLogger(__name__)

app = Flask(__name__)

_jobs: dict = {}
_jobs_lock = threading.Lock()


HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>TMI — Know Your Exposure</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Space+Mono:wght@400;700&display=swap" rel="stylesheet">
<style>
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  :root {
    --bg:         #F7F8FC;
    --surface:    #FFFFFF;
    --border:     #E4E7EF;
    --text:       #111827;
    --muted:      #6B7280;
    --accent:     #2563EB;
    --accent-lt:  #EFF6FF;
    --low:        #059669;
    --low-lt:     #ECFDF5;
    --medium:     #D97706;
    --medium-lt:  #FFFBEB;
    --high:       #DC2626;
    --high-lt:    #FEF2F2;
    --critical:   #7C3AED;
    --critical-lt:#F5F3FF;
    --radius:     12px;
    --radius-sm:  8px;
  }
  body {
    background: var(--bg);
    color: var(--text);
    font-family: 'Inter', sans-serif;
    font-size: 15px;
    line-height: 1.6;
    min-height: 100vh;
  }
  .page { max-width: 680px; margin: 0 auto; padding: 3rem 1.5rem 6rem; }
  .site-header { margin-bottom: 3rem; }
  .header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 2rem;
  }
  .header-text { flex: 1; min-width: 0; }
  .header-image {
    max-width: 110px;
    width: 100%;
    height: auto;
    border-radius: 50%;
    flex-shrink: 0;
    display: block;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }
  .wordmark {
    font-family: 'Space Mono', monospace;
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.2em;
    text-transform: uppercase;
    color: var(--accent);
    margin-bottom: 1.5rem;
    display: block;
  }
  h1 {
    font-size: 2rem;
    font-weight: 700;
    letter-spacing: -0.02em;
    line-height: 1.2;
    margin-bottom: 0.75rem;
  }
  .subtitle { color: var(--muted); font-size: 0.95rem; max-width: 480px; }
  .card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 1.75rem;
    margin-bottom: 1.5rem;
  }
  .form-label {
    display: block;
    font-size: 0.8rem;
    font-weight: 600;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.5rem;
  }

  /* Platform tabs */
  .platform-tabs {
    display: flex;
    gap: 0.5rem;
    margin-bottom: 1rem;
    flex-wrap: wrap;
  }
  .tab-btn {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    padding: 0.45rem 1rem;
    border-radius: 2rem;
    border: 1.5px solid var(--border);
    background: var(--bg);
    color: var(--muted);
    font-family: 'Inter', sans-serif;
    font-size: 0.82rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.15s;
  }
  .tab-btn:hover { border-color: var(--accent); color: var(--accent); }
  .tab-btn.active {
    background: var(--accent);
    border-color: var(--accent);
    color: #fff;
  }
  .tab-icon { font-size: 0.9rem; }

  .input-row {
    display: flex;
    gap: 0.75rem;
    align-items: stretch;
  }
  .handle-wrap {
    flex: 1;
    display: flex;
    align-items: center;
    border: 1.5px solid var(--border);
    border-radius: var(--radius-sm);
    overflow: hidden;
    transition: border-color 0.15s;
    background: var(--bg);
  }
  .handle-wrap:focus-within { border-color: var(--accent); background: #fff; }
  .at-sign {
    padding: 0 0.75rem;
    color: var(--muted);
    font-family: 'Space Mono', monospace;
    font-size: 0.9rem;
    user-select: none;
  }
  input[type="text"] {
    flex: 1;
    border: none;
    outline: none;
    background: transparent;
    font-family: 'Space Mono', monospace;
    font-size: 0.9rem;
    color: var(--text);
    padding: 0.75rem 0.75rem 0.75rem 0;
  }
  input[type="text"]::placeholder { color: var(--border); }
  button[type="submit"] {
    background: var(--accent);
    color: #fff;
    border: none;
    border-radius: var(--radius-sm);
    padding: 0 1.5rem;
    font-family: 'Inter', sans-serif;
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
    transition: background 0.15s, transform 0.1s;
  }
  button[type="submit"]:hover { background: #1d4ed8; }
  button[type="submit"]:active { transform: scale(0.98); }
  button[type="submit"]:disabled { background: var(--border); color: var(--muted); cursor: not-allowed; }
  .privacy-note {
    margin-top: 0.85rem;
    font-size: 0.78rem;
    color: var(--muted);
    display: flex;
    align-items: center;
    gap: 0.4rem;
  }
  .privacy-note::before { content: "🔒"; font-size: 0.75rem; }

  /* Platform notice for Twitter / LinkedIn */
  .platform-notice {
    margin-top: 0.75rem;
    font-size: 0.78rem;
    color: var(--muted);
    padding: 0.6rem 0.9rem;
    background: var(--accent-lt);
    border-radius: var(--radius-sm);
    display: none;
  }
  .platform-notice.visible { display: block; }

  #loading {
    display: none;
    text-align: center;
    padding: 3rem 1rem;
    color: var(--muted);
  }
  .spinner {
    width: 36px; height: 36px;
    border: 3px solid var(--border);
    border-top-color: var(--accent);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin: 0 auto 1rem;
  }
  @keyframes spin { to { transform: rotate(360deg); } }
  .loading-steps { font-size: 0.82rem; line-height: 2; }
  .loading-step { opacity: 0.4; transition: opacity 0.3s; }
  .loading-step.active { opacity: 1; color: var(--accent); }
  .loading-step.done { opacity: 0.6; }
  .loading-step.done::after { content: " ✓"; }

  #error {
    display: none;
    background: var(--high-lt);
    border: 1px solid #FECACA;
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    color: var(--high);
    font-size: 0.9rem;
  }
  #results { display: none; }

  .score-hero {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius);
    padding: 2rem;
    margin-bottom: 1rem;
    display: grid;
    grid-template-columns: 1fr auto;
    gap: 1.5rem;
    align-items: center;
  }
  .score-handle {
    font-family: 'Space Mono', monospace;
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.25rem;
  }
  .score-handle span { color: var(--muted); font-weight: 400; }
  .score-meta { font-size: 0.78rem; color: var(--muted); margin-top: 0.5rem; }
  .score-display { text-align: right; }
  .score-number {
    font-family: 'Space Mono', monospace;
    font-size: 3.5rem;
    font-weight: 700;
    line-height: 1;
  }
  .score-badge {
    display: inline-block;
    margin-top: 0.4rem;
    padding: 0.2rem 0.75rem;
    border-radius: 2rem;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
  }
  .score-bar-wrap {
    grid-column: 1 / -1;
    height: 6px;
    background: var(--border);
    border-radius: 3px;
    overflow: hidden;
  }
  .score-bar { height: 100%; border-radius: 3px; width: 0; transition: width 1.2s cubic-bezier(0.4,0,0.2,1); }
  .risk-LOW      { color: var(--low);      }
  .risk-MEDIUM   { color: var(--medium);   }
  .risk-HIGH     { color: var(--high);     }
  .risk-CRITICAL { color: var(--critical); }
  .badge-LOW      { background: var(--low-lt);      color: var(--low);      }
  .badge-MEDIUM   { background: var(--medium-lt);   color: var(--medium);   }
  .badge-HIGH     { background: var(--high-lt);     color: var(--high);     }
  .badge-CRITICAL { background: var(--critical-lt); color: var(--critical); }
  .bar-LOW      { background: var(--low);      }
  .bar-MEDIUM   { background: var(--medium);   }
  .bar-HIGH     { background: var(--high);     }
  .bar-CRITICAL { background: var(--critical); }
  .summary-card {
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid var(--accent);
    border-radius: var(--radius);
    padding: 1.25rem 1.5rem;
    margin-bottom: 1rem;
    font-size: 0.9rem;
    line-height: 1.7;
  }
  .section-label {
    font-size: 0.72rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--muted);
    margin-bottom: 0.75rem;
    margin-top: 1.5rem;
  }
  .categories { display: flex; flex-direction: column; gap: 0.5rem; }
  .cat-row {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 1rem 1.25rem;
  }
  .cat-top {
    display: flex;
    justify-content: space-between;
    align-items: baseline;
    margin-bottom: 0.4rem;
  }
  .cat-name { font-size: 0.85rem; font-weight: 500; }
  .cat-score { font-family: 'Space Mono', monospace; font-size: 0.8rem; color: var(--muted); }
  .cat-bar-wrap { height: 3px; background: var(--border); border-radius: 2px; overflow: hidden; margin-bottom: 0.5rem; }
  .cat-bar { height: 100%; border-radius: 2px; width: 0; transition: width 1s ease 0.3s; }
  .cat-evidence { font-size: 0.75rem; color: var(--muted); font-family: 'Space Mono', monospace; line-height: 1.5; }
  .recs { display: flex; flex-direction: column; gap: 0.5rem; }
  .rec-item {
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    padding: 0.85rem 1.25rem;
    font-size: 0.875rem;
    line-height: 1.5;
    display: flex;
    gap: 0.75rem;
    align-items: flex-start;
  }
  .rec-icon { color: var(--accent); font-size: 0.75rem; margin-top: 0.15rem; flex-shrink: 0; }
  .site-footer {
    margin-top: 4rem;
    padding-top: 1.5rem;
    border-top: 1px solid var(--border);
    font-size: 0.75rem;
    color: var(--muted);
    text-align: center;
    line-height: 1.8;
  }
  @media (max-width: 500px) {
    .input-row { flex-direction: column; }
    button[type="submit"] { padding: 0.75rem; }
    .score-hero { grid-template-columns: 1fr; }
    .score-display { text-align: left; }
    .header-row { flex-direction: column-reverse; align-items: flex-start; gap: 1.25rem; }
    .header-image { max-width: 72px; }
  }
</style>
</head>
<body>
<div class="page">
  <header class="site-header">
    <div class="header-row">
      <div class="header-text">
        <span class="wordmark">TMI · Privacy Check</span>
        <h1>How exposed are you online?</h1>
        <p class="subtitle">Enter your username and we'll scan your public profile for personally identifiable information and privacy risks.</p>
      </div>
      <img src="/logo.png" alt="TMI Logo" class="header-image">
    </div>
  </header>

  <div class="card">
    <label class="form-label">Platform</label>
    <div class="platform-tabs">
      <button class="tab-btn active" id="tab-instagram" onclick="selectPlatform('instagram')">
        <span class="tab-icon">📸</span> Instagram
      </button>
      <button class="tab-btn" id="tab-twitter" onclick="selectPlatform('twitter')">
        <span class="tab-icon">🐦</span> X / Twitter
      </button>
      <button class="tab-btn" id="tab-linkedin" onclick="selectPlatform('linkedin')">
        <span class="tab-icon">💼</span> LinkedIn
      </button>
    </div>

    <label class="form-label" for="username-input" id="username-label">Username</label>
    <div class="input-row">
      <div class="handle-wrap">
        <span class="at-sign" id="at-sign">@</span>
        <input
          type="text"
          id="username-input"
          placeholder="yourhandle"
          autocomplete="off"
          autocorrect="off"
          autocapitalize="off"
          spellcheck="false"
        >
      </div>
      <button type="submit" id="check-btn" onclick="startCheck()">Check</button>
    </div>

    <div class="platform-notice" id="twitter-notice">
      This check analyses your public profile and bio only — not individual tweets.
    </div>

    <div class="platform-notice" id="linkedin-notice">
      This check analyses your public profile only — not individual posts. Enter your profile slug (the part after linkedin.com/in/), e.g. "williamhgates" — not an @ handle.
    </div>

    <p class="privacy-note">Your username is only used to fetch public profile data. No information is stored or shared.</p>
  </div>

  <div id="loading">
    <div class="spinner"></div>
    <div class="loading-steps">
      <div class="loading-step" id="step-1">Fetching profile</div>
      <div class="loading-step" id="step-2">Analysing bio and content</div>
      <div class="loading-step" id="step-3">Calculating risk score</div>
    </div>
  </div>

  <div id="error"></div>
  <div id="results"></div>

  <footer class="site-footer">
    Analysis runs locally on private infrastructure.<br>
    No data is sent to third-party AI services. Scoring is powered by a local language model.
  </footer>
</div>

<script>
let selectedPlatform = 'instagram';

const CAT_LABELS_INSTAGRAM = {
  pii_exposure:               'PII & Profile Exposure',
  private_account:            'Account Privacy Settings',
  content_location_exposure:  'Content & Location Exposure',
  account_hygiene:            'Account Hygiene & History',
};

const CAT_LABELS_TWITTER = {
  pii_exposure:    'PII & Profile Exposure',
  private_account: 'Account Privacy Settings',
  bio_risk:        'Bio Risk Signals',
};

const CAT_LABELS_LINKEDIN = {
  pii_exposure:          'PII & Profile Exposure',
  bio_risk:              'Bio Risk Signals',
  professional_exposure: 'Professional Exposure',
  contact_information:   'Contact & Cross-platform Links',
};

const CAT_MAX_INSTAGRAM = {
  pii_exposure: 30, private_account: 15,
  content_location_exposure: 45, account_hygiene: 10,
};

const CAT_MAX_TWITTER = {
  pii_exposure: 50, private_account: 15, bio_risk: 35,
};

const CAT_MAX_LINKEDIN = {
  pii_exposure: 40, bio_risk: 15,
  professional_exposure: 25, contact_information: 20,
};

const RISK_COLORS = {
  LOW: '#059669', MEDIUM: '#D97706', HIGH: '#DC2626', CRITICAL: '#7C3AED',
};

function selectPlatform(platform) {
  selectedPlatform = platform;
  document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
  document.getElementById('tab-' + platform).classList.add('active');

  document.getElementById('twitter-notice').classList.toggle('visible', platform === 'twitter');
  document.getElementById('linkedin-notice').classList.toggle('visible', platform === 'linkedin');

  const atSign = document.getElementById('at-sign');
  const input  = document.getElementById('username-input');
  const label  = document.getElementById('username-label');

  if (platform === 'linkedin') {
    atSign.style.display = 'none';
    input.placeholder = 'e.g. williamhgates';
    label.textContent = 'LinkedIn Profile Slug';
  } else {
    atSign.style.display = '';
    input.placeholder = platform === 'twitter' ? 'twitterhandle' : 'yourhandle';
    label.textContent = 'Username';
  }

  // Hide previous results when switching platform
  document.getElementById('results').style.display = 'none';
  document.getElementById('error').style.display = 'none';
}

function setStep(n) {
  for (let i = 1; i <= 3; i++) {
    const el = document.getElementById('step-' + i);
    if (i < n) el.className = 'loading-step done';
    else if (i === n) el.className = 'loading-step active';
    else el.className = 'loading-step';
  }
}

async function startCheck() {
  const input = document.getElementById('username-input');
  const username = input.value.trim().replace(/^@/, '');
  if (!username) { input.focus(); return; }

  document.getElementById('check-btn').disabled = true;
  document.getElementById('error').style.display = 'none';
  document.getElementById('results').style.display = 'none';
  document.getElementById('loading').style.display = 'block';
  setStep(1);

  try {
    const startRes = await fetch('/api/check', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, platform: selectedPlatform }),
    });

    if (!startRes.ok) {
      const err = await startRes.json();
      throw new Error(err.error || 'Failed to start assessment.');
    }

    const { job_id } = await startRes.json();

    let dots = 0;
    const pollTimer = setInterval(async () => {
      dots++;
      if (dots < 15) setStep(1);
      else if (dots < 30) setStep(2);
      else setStep(3);

      try {
        const pollRes = await fetch('/api/result/' + job_id);
        if (!pollRes.ok) return;
        const data = await pollRes.json();
        if (data.status === 'done') {
          clearInterval(pollTimer);
          showResults(data.result);
        } else if (data.status === 'error') {
          clearInterval(pollTimer);
          showError(data.message || 'Assessment failed. Please try again.');
        }
      } catch (e) {}
    }, 2000);

  } catch (err) {
    showError(err.message);
  }
}

function showError(msg) {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('check-btn').disabled = false;
  const errEl = document.getElementById('error');
  errEl.style.display = 'block';
  errEl.textContent = msg;
}

function showResults(d) {
  document.getElementById('loading').style.display = 'none';
  document.getElementById('check-btn').disabled = false;

  const risk  = d.risk_level || 'LOW';
  const score = d.total_risk_score ?? 0;
  const cats  = d.category_scores || {};
  const recs  = d.top_recommendations || [];
  const color = RISK_COLORS[risk] || RISK_COLORS.LOW;
  const platform = d.platform || 'instagram';

  let catLabels, catMax, platformLabel;
  if (platform === 'twitter') {
    catLabels = CAT_LABELS_TWITTER; catMax = CAT_MAX_TWITTER; platformLabel = 'X / Twitter';
  } else if (platform === 'linkedin') {
    catLabels = CAT_LABELS_LINKEDIN; catMax = CAT_MAX_LINKEDIN; platformLabel = 'LinkedIn';
  } else {
    catLabels = CAT_LABELS_INSTAGRAM; catMax = CAT_MAX_INSTAGRAM; platformLabel = 'Instagram';
  }

  let catsHTML = '';
  for (const [key, val] of Object.entries(cats)) {
    // Categories with max_points = 0 (e.g. LinkedIn's private_account,
    // which is always 0/0 by rubric design) contribute nothing and
    // shouldn't be shown in the breakdown at all.
    const max = key in catMax ? catMax[key] : 10;
    if (max === 0) continue;

    const s   = val.score ?? 0;
    const pct = Math.min(100, (s / max) * 100);
    const ev  = val.evidence || '';
    catsHTML += `
      <div class="cat-row">
        <div class="cat-top">
          <span class="cat-name">${catLabels[key] || key}</span>
          <span class="cat-score">${s} / ${max}</span>
        </div>
        <div class="cat-bar-wrap">
          <div class="cat-bar" data-pct="${pct}" style="background:${color}"></div>
        </div>
        ${ev && ev !== 'None detected' && ev !== 'None' && ev !== '[]'
          ? `<div class="cat-evidence">${ev.slice(0,140)}${ev.length>140?'…':''}</div>`
          : ''}
      </div>`;
  }

  const recsHTML = recs.map(r => `
    <div class="rec-item">
      <span class="rec-icon">→</span>
      <span>${r}</span>
    </div>`).join('');

  document.getElementById('results').innerHTML = `
    <div class="score-hero">
      <div>
        <div class="score-handle"><span>${platform === 'linkedin' ? '' : '@'}</span>${d.username || '—'}</div>
        <div class="score-meta">${platformLabel} · public profile analysis</div>
      </div>
      <div class="score-display">
        <div class="score-number risk-${risk}">${score}</div>
        <div class="score-badge badge-${risk}">${risk}</div>
      </div>
      <div class="score-bar-wrap">
        <div class="score-bar bar-${risk}" id="main-bar"></div>
      </div>
    </div>

    ${d.analyst_summary ? `<div class="summary-card">${d.analyst_summary}</div>` : ''}

    <div class="section-label">Risk breakdown</div>
    <div class="categories">${catsHTML}</div>

    ${recs.length ? `
      <div class="section-label">What you can do</div>
      <div class="recs">${recsHTML}</div>
    ` : ''}
  `;

  document.getElementById('results').style.display = 'block';

  requestAnimationFrame(() => requestAnimationFrame(() => {
    const mainBar = document.getElementById('main-bar');
    if (mainBar) mainBar.style.width = score + '%';
    document.querySelectorAll('.cat-bar[data-pct]').forEach(b => {
      b.style.width = b.dataset.pct + '%';
    });
  }));

  document.getElementById('results').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

document.addEventListener('DOMContentLoaded', () => {
  document.getElementById('username-input').addEventListener('keydown', e => {
    if (e.key === 'Enter') startCheck();
  });
});
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/logo.png")
def logo():
    """
    Serve the local TMI logo. Expected to sit next to webapp.py
    (i.e. D:\\TMI\\TMI-pfp.png) — resolved relative to this file so it
    doesn't depend on the drive letter or working directory.
    """
    logo_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "TMI-pfp.png")
    if not os.path.exists(logo_path):
        log.warning("[WebApp] Logo not found at %s", logo_path)
        return jsonify({"error": "Logo not found."}), 404
    return send_file(logo_path, mimetype="image/png")


@app.route("/api/check", methods=["POST"])
def check():
    data     = request.get_json(force=True)
    username = (data.get("username") or "").strip().lstrip("@")
    platform = (data.get("platform") or "instagram").strip().lower()

    if not username:
        return jsonify({"error": "No username provided."}), 400

    if platform not in ("instagram", "twitter", "linkedin"):
        return jsonify({"error": f"Unsupported platform: {platform}"}), 400

    job_id = str(uuid.uuid4())
    with _jobs_lock:
        _jobs[job_id] = {"status": "running"}

    thread = threading.Thread(
        target=_run_pipeline,
        args=(job_id, username, platform),
        daemon=True,
    )
    thread.start()

    return jsonify({"job_id": job_id})


@app.route("/api/result/<job_id>")
def result(job_id):
    with _jobs_lock:
        job = _jobs.get(job_id)
    if not job:
        return jsonify({"status": "not_found"}), 404
    return jsonify(job)


def _run_pipeline(job_id: str, username: str, platform: str):
    try:
        log.info("[WebApp] Starting %s assessment for @%s (job %s)", platform, username, job_id)

        if platform == "instagram":
            profile = fetch_instagram_profile(username)
            if not profile:
                _set_job_error(job_id, f"Could not find Instagram profile @{username}. Check the username is correct.")
                return
            comments = []
            if not profile.get("is_private"):
                comments = fetch_instagram_comments(username, profile.get("post_urls", []))

        elif platform == "twitter":
            profile = fetch_twitter_profile(username)
            if not profile:
                _set_job_error(job_id, f"Could not find Twitter/X profile @{username}. Check the username is correct.")
                return
            comments = []  # Twitter comments not yet implemented

        elif platform == "linkedin":
            profile = fetch_linkedin_profile(username)
            if not profile:
                _set_job_error(job_id, f"Could not find LinkedIn profile '{username}'. Check the profile slug is correct.")
                return
            comments = []  # LinkedIn post/comment analysis not implemented

        else:
            _set_job_error(job_id, f"Unsupported platform: {platform}")
            return

        result = score_profile(profile, comments, flagged_following=[])

        if result.get("risk_level") == "ERROR":
            _set_job_error(job_id, "Scoring failed. Please try again in a moment.")
            return

        with _jobs_lock:
            _jobs[job_id] = {"status": "done", "result": result}

        log.info(
            "[WebApp] @%s (%s) complete → %d/100 (%s)",
            username, platform,
            result.get("total_risk_score", 0),
            result.get("risk_level", "?"),
        )

    except Exception as exc:
        log.error("[WebApp] Pipeline error for @%s: %s", username, exc)
        _set_job_error(job_id, "An unexpected error occurred. Please try again.")


def _set_job_error(job_id: str, message: str):
    with _jobs_lock:
        _jobs[job_id] = {"status": "error", "message": message}


if __name__ == "__main__":
    log.info("TMI Risk Web App starting on http://0.0.0.0:5001")
    log.info("Open on laptop: http://%s:5001", config.OLLAMA_HOST)
    app.run(host="0.0.0.0", port=5001, debug=False, threaded=True)