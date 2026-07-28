# TMI — Know Your Exposure

TMI is a privacy risk-scoring utility that assesses public social media profiles for personally identifiable information (PII) and security exposure.

## Overview

TMI functions strictly as an awareness-building utility rather than a surveillance engine. It accesses exclusively publicly visible information — never bypassing privacy settings or requiring logins — and operates on a self-service model where users check their own accounts.

Profile scoring is powered entirely by a local LLM (Ollama), so profile data never leaves your network for the scoring step. The only external call is to Apify's public scraping actors, which is required to pull the public profile data in the first place. A full assessment typically completes in 10–90 seconds, depending on the platform and how much data is scraped.

## Key Features

- **Multi-platform support** — scans public profiles on Instagram, Twitter/X, and LinkedIn.
- **Platform-specific rubrics** — each platform is scored against its own 100-point rubric, built only from the data that platform actually exposes (see `config.py` for the full rationale behind each category).
- **Deterministic + LLM hybrid scoring** — categories with a clear, factual answer (account visibility, post count, regex-confirmed PII like emails/phones) are scored programmatically rather than left to the model; everything else (bio tone, comment content, professional exposure) is judged by the local LLM.
- **PII pre-scanner** — a regex/keyword pass over bio text catches emails, phone numbers, ages, grade levels, and institution names before the LLM even runs, and those findings are treated as confirmed facts in scoring.
- **Async job-based web UI** — submit a username, poll for results, and get a score breakdown with evidence and recommendations, without blocking the request.

## Project Structure

```
.
├── webapp.py               # Flask front-end (port 5001) — UI, job queue, API endpoints
├── config.py                # API credentials, Ollama settings, platform risk rubrics
├── utils/
│   ├── apify_scraper.py     # Apify scraping functions (Instagram, Twitter/X, LinkedIn)
│   └── ollama_scorer.py     # Local Ollama scoring engine, PII pre-scanner, rubric logic
└── TMI-pfp.png               # Logo served at /logo.png (place next to webapp.py)
```

## Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) installed and running, with the `qwen2.5vl:7b` model pulled
- An active [Apify](https://apify.com/) API token
- Python packages: `flask`, `apify-client`, `ollama` (install via `pip install flask apify-client ollama`)

## Installation & Configuration

1. **Set your Apify API token** as an environment variable.

   PowerShell:
   ```powershell
   $env:APIFY_API_TOKEN = "apify_api_xxxx"
   ```

   macOS/Linux:
   ```bash
   export APIFY_API_TOKEN="apify_api_xxxx"
   ```

2. **Pull the Ollama model** used for scoring:
   ```bash
   ollama pull qwen2.5vl:7b
   ```

3. **Review `config.py`** and adjust as needed:
   - `OLLAMA_HOST` / `OLLAMA_PORT` — where your Ollama instance is reachable (defaults to a Tailscale IP; change to `127.0.0.1` if running Ollama on the same machine as the web app).
   - `MAX_COMMENTS` — cap on Instagram comments pulled per profile.
   - `APIFY_ACTORS` — Apify actor IDs used for each platform's scraper.

## Running the Web Application

```bash
python webapp.py
```

Then open in your browser:

- **Desktop:** `http://localhost:5001`
- **Another device via Tailscale:** `http://100.x.x.x:5001`

Enter a username (or LinkedIn public identifier/URL), pick a platform, and submit. The app scrapes the public profile via Apify, runs it through the local Ollama scoring engine, and returns a risk score (0–100) with a category breakdown, supporting evidence, and recommendations.

## How Scoring Works

1. **Scrape** — `utils/apify_scraper.py` fetches the target's public profile (and, for Instagram public accounts, recent comments) via Apify.
2. **Pre-scan** — `utils/ollama_scorer.py` regex-scans the bio for confirmed PII (email, phone, age, grade, institution, location) before any LLM call.
3. **Score** — the profile, pre-scan findings, and platform-specific rubric are sent to the local Ollama model, which returns a JSON breakdown across every rubric category.
4. **Override deterministic categories** — categories backed by hard facts (account visibility, post count, regex-confirmed PII) are recalculated in code and overwrite the model's values, since these don't need — and shouldn't rely on — LLM judgment.
5. **Total & risk level** — category scores are summed to a 0–100 total, mapped to a risk level:

   | Score  | Risk Level |
   |--------|------------|
   | 0–19   | LOW        |
   | 20–44  | MEDIUM     |
   | 45–69  | HIGH       |
   | 70–100 | CRITICAL   |

## Adding a New Platform

1. Add the platform's Apify actor ID to `APIFY_ACTORS` in `config.py`.
2. Write a `fetch_<platform>_profile()` function in `utils/apify_scraper.py` that returns a normalised profile dict.
3. Add a rubric for the platform to `config.py` and register it in `PLATFORM_RUBRICS`, scoping every category strictly to data that function actually returns.
4. Wire the new fetch function into `webapp.py`'s `/api/check` and `_run_pipeline`.

## Notes

- Only public data is scraped — no login credentials, cookies, or authenticated sessions are used for any platform.
- LinkedIn profiles reachable by the scraper are public by definition, so there is no "private account" category for LinkedIn.
- Instagram's `account_hygiene` and all platforms' `private_account`/regex-confirmed PII categories are intentionally scored deterministically rather than by the LLM, since arithmetic and simple thresholds are more reliable done in code.
