"""
config.py
---------
Central configuration for the Maltego Risk Transform Server.
Edit this file only — nothing else needs changing for basic setup.
"""

import os

# ── API credentials ────────────────────────────────────────────────────────────
# Set these as environment variables in PowerShell before running:
#   $env:APIFY_API_TOKEN = "apify_api_xxxx"
APIFY_API_TOKEN = os.environ.get("APIFY_API_TOKEN", "YOUR_APIFY_TOKEN_HERE")

# ── Local LLM (Ollama) ─────────────────────────────────────────────────────────
OLLAMA_MODEL       = "qwen2.5vl:7b"
OLLAMA_TEMPERATURE = 0.1       # low = more consistent JSON output
OLLAMA_MAX_TOKENS  = 4096
OLLAMA_HOST = "100.103.8.99"  # your actual Tailscale IP
OLLAMA_PORT = 11434

# ── Transform server ───────────────────────────────────────────────────────────
TRANSFORM_SERVER_HOST = "0.0.0.0"
TRANSFORM_SERVER_PORT = 8080

# ── Scraping limits ────────────────────────────────────────────────────────────
MAX_COMMENTS = 50             # per profile — keeps prompt size manageable

# ── Known-bad accounts ────────────────────────────────────────────────────────
# Path to a newline-separated list of flagged Instagram handles.
# Set to None to skip the cross-reference step.
KNOWN_BAD_ACCOUNTS_FILE = None   # e.g. "bad_accounts.txt"

# ── Apify actor IDs ───────────────────────────────────────────────────────────
# These are public Apify actors — no install needed, called via API.
# Add new platform actor IDs here as you expand.
APIFY_ACTORS = {
    "instagram_profile":  "apify/instagram-profile-scraper",
    "instagram_comments": "apify/instagram-comment-scraper",
    "twitter_profile":    "apidojo/twitter-profile-scraper",
    "linkedin_profile":   "harvestapi/linkedin-profile-scraper",
}

# ── Risk rubrics ───────────────────────────────────────────────────────────────
# One rubric per platform. Each is scored independently and must total 100.
#
# Design principle: every category must be backed by data that is ACTUALLY
# scraped for that platform AND actually passed to the scorer. Instagram has
# comment data from other users (fetch_instagram_comments), so it can score
# content_location_exposure — a merged category covering bio content risk,
# comment-disclosure risk, and stranger-comment content, all in one bucket.
# That category is scoped to comment CONTENT only where relevant, never the
# account owner's behavior, since nothing captures how the owner responds.
# account_hygiene is scored entirely deterministically from post_count (see
# the override in ollama_scorer.py) rather than left to the LLM, since it's
# a simple numeric threshold and the model's own arithmetic has proven
# unreliable in practice. Instagram's following_list is scraped but
# deliberately stripped out of the prompt in build_prompt() (too large / not
# useful as free text), and there is no flagged-account list in practice
# (KNOWN_BAD_ACCOUNTS_FILE is unset) — so there is no real network signal to
# score, and network_risk / connected-accounts was removed rather than kept
# ungrounded. Twitter and LinkedIn only pull the target's own profile (bio/
# headline/about, name, location, account visibility) — no post-scraping, no
# follower/following data, no comment data, and none of that is planned.
# Their rubrics are scoped entirely to what the profile fields expose. Do
# not add network/connected-accounts, engagement, or comment-disclosure
# categories back to Twitter or LinkedIn — and do not add them back to
# Instagram either — unless a fetch function is actually built and wired
# into the prompt to back it with real data.

RISK_RUBRIC_INSTAGRAM = {
    "pii_exposure": {
        "max_points": 30,
        "guidance": (
            "Check the bio, username, and post captions for any of these: "
            "Full first+last name visible: 8 pts. "
            "Phone number present: 10 pts. "
            "Home address or suburb: 10 pts. "
            "School or workplace named (e.g. 'St John's High', 'Grade 10', 'Works at X'): 8 pts. "
            "Email address present: 7 pts. Cap at 30."
        ),
    },
    "private_account": {
        "max_points": 15,
        "guidance": (
            "Check the account_visibility field ONLY. "
            "account_visibility = 'public'  → score MUST be 15. "
            "account_visibility = 'private' → score MUST be 0. "
            "No other values are possible. Do not use any other reasoning."
        ),
    },
    "content_location_exposure": {
        "max_points": 45,
        "guidance": (
            "This category merges bio content risk, PII disclosed by OTHER "
            "people in comments, and concerning stranger comment content. "
            "Score across all three sub-areas below and cap the TOTAL at 45.\n"
            "BIO CONTENT (sub-cap 20): age or grade year mentioned in bio "
            "(e.g. '16', 'Year 11', 'Class of 2027'): 5 pts. School or "
            "university named in bio: 5 pts. Location pinned or mentioned in "
            "bio: 4 pts. Contact solicitation e.g. 'DM me', 'snap me', 'text "
            "me' (NOT email addresses — those are scored in pii_exposure): "
            "2 pts. Romantic or sexual availability signals in bio: 4 pts.\n"
            "COMMENT PII (sub-cap 15): phone or email shared by someone else "
            "in the comments: 7 pts. Location, school, or workplace named in "
            "comments: 5 pts. Age or birthday shared in comments: 3 pts.\n"
            "STRANGER COMMENT CONTENT (sub-cap 10) — score ONLY the literal "
            "CONTENT of a comment left by another account; never a claim "
            "about how the profile owner responded or behaved, since that is "
            "not visible in the scraped data: a comment from an unknown/"
            "stranger account contains romantic, flirtatious, or sexual "
            "language directed at the user: 5 pts. a comment from an "
            "unknown/stranger account offers gifts, money, or a meetup, or "
            "asks for personal contact info/location: 5 pts."
        ),
    },
    "account_hygiene": {
        "max_points": 10,
        "guidance": (
            "This is calculated programmatically from the post_count field "
            "and is not something you need to judge — the value you return "
            "for it will be overwritten. Check post_count ONLY: "
            "post_count >= 500 → score MUST be 10. "
            "post_count 200-499 → score MUST be 7. "
            "post_count 50-199 → score MUST be 3. "
            "post_count under 50 → score MUST be 0. "
            "A large, unpruned post_count reflects an extensive, undeleted "
            "history of old content, past locations, and outdated personal "
            "information that stays publicly exposed over time. "
            "IMPORTANT — DIRECTION: a LOW post_count is the SAFE outcome for "
            "this category, not a problem. Do NOT recommend posting more, "
            "increasing post_count, or 'improving hygiene' by adding "
            "content — that would make the account MORE exposed, the "
            "opposite of what this category measures. If anything is worth "
            "recommending here, it is the reverse: periodically reviewing "
            "and deleting old posts to keep post_count low."
        ),
    },
}

# Backward-compat alias — the Maltego transform server (server.py / transforms/)
# imports config.RISK_RUBRIC directly and only ever handles Instagram.
RISK_RUBRIC = RISK_RUBRIC_INSTAGRAM


RISK_RUBRIC_TWITTER = {
    "pii_exposure": {
        "max_points": 50,
        "guidance": (
            "Check the bio, username, location, and website fields for any of "
            "these: "
            "Full first+last name visible: 12 pts. "
            "Phone number present: 12 pts. "
            "Home address or suburb: 10 pts. "
            "School or workplace named: 8 pts. "
            "Email address present: 8 pts. Cap at 50."
        ),
    },
    "private_account": {
        "max_points": 15,
        "guidance": (
            "Check the account_visibility field ONLY. "
            "account_visibility = 'public'  → score MUST be 15. "
            "account_visibility = 'private' → score MUST be 0. "
            "No other values are possible. Do not use any other reasoning."
        ),
    },
    "bio_risk": {
        "max_points": 35,
        "guidance": (
            "Read the bio field carefully for any of these: "
            "Age or grade year mentioned: 10 pts. "
            "School or university named in bio: 10 pts. "
            "Location pinned or mentioned in bio: 8 pts. "
            "Contact solicitation e.g. 'DM me', 'text me' (NOT email addresses — "
            "those are scored in pii_exposure): 3 pts. "
            "Romantic or sexual availability signals: 4 pts. Cap at 35."
        ),
    },
}


RISK_RUBRIC_LINKEDIN = {
    "pii_exposure": {
        "max_points": 40,
        "guidance": (
            "Check the headline, about section, current position/company, "
            "location, and schools for any of these: "
            "Full name combined with current employer AND role (a common doxxing "
            "combo): 14 pts. "
            "Phone number present anywhere in profile: 13 pts. "
            "Home address or specific suburb/neighbourhood: 8 pts. "
            "Personal (non-work) email address present: 5 pts. Cap at 40."
        ),
    },
    "bio_risk": {
        "max_points": 15,
        "guidance": (
            "Read the headline and about section for: "
            "Age or graduation year mentioned: 6 pts. "
            "Specific location (city/neighbourhood) mentioned: 5 pts. "
            "Personal life details (family, home situation) shared: 4 pts. Cap at 15."
        ),
    },
    "professional_exposure": {
        "max_points": 25,
        "guidance": (
            "Current employer named: 8 pts. "
            "Current job title/role named: 6 pts. "
            "Full employment history (3+ past employers) visible, enabling a "
            "detailed career timeline to be built: 6 pts. "
            "Schools/education history naming specific institutions and years: "
            "5 pts. Cap at 25."
        ),
    },
    "contact_information": {
        "max_points": 20,
        "guidance": (
            "Email address visible in profile or 'Contact info': 8 pts. "
            "Phone number visible in profile or 'Contact info': 8 pts. "
            "Personal website or other social handles linked, allowing "
            "cross-platform tracking: 4 pts. Cap at 20."
        ),
    },
}
# NOTE: LinkedIn has no "private_account" category. Profiles reachable by
# this scraper are public by definition — there is no private-account state
# to detect, so the category was removed rather than kept as a permanent 0.


PLATFORM_RUBRICS = {
    "instagram": RISK_RUBRIC_INSTAGRAM,
    "twitter":   RISK_RUBRIC_TWITTER,
    "linkedin":  RISK_RUBRIC_LINKEDIN,
}