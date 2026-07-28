"""
utils/apify_scraper.py
----------------------
Apify scraping functions shared across all platform transforms.
Each platform transform imports only what it needs from here.

To add a new platform:
  1. Add its Apify actor ID to config.APIFY_ACTORS
  2. Add a new fetch_<platform>_profile() function below
  3. Import and call it from your new transform file
"""

import logging
import unicodedata
import re
from typing import Optional

from apify_client import ApifyClient
import config

log = logging.getLogger(__name__)


def get_client() -> ApifyClient:
    return ApifyClient(config.APIFY_API_TOKEN)


def sanitise(text: Optional[str]) -> str:
    """Normalise unicode, collapse whitespace, strip — safe for CSV and LLM prompts."""
    if not text:
        return ""
    text = unicodedata.normalize("NFC", text)
    text = re.sub(r"[\r\n\t\u00a0\u200b]+", " ", text)
    return re.sub(r" {2,}", " ", text).strip()


# ── INSTAGRAM ─────────────────────────────────────────────────────────────────

def fetch_instagram_profile(username: str) -> dict:
    """
    Fetch Instagram profile metadata via Apify.
    Returns a normalised dict or empty dict on failure.
    """
    log.info("[Apify/Instagram] Fetching profile @%s", username)
    client = get_client()

    try:
        run = client.actor(config.APIFY_ACTORS["instagram_profile"]).call(run_input={
            "usernames":       [username],
            "scrapeFollowing": True,
            "resultsLimit":    1,
        })
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        if not items:
            log.warning("[Apify/Instagram] No data for @%s", username)
            return {}

        raw = items[0]
        # Extract post URLs from latestPosts for comment scraping
        latest_posts = raw.get("latestPosts", []) or []
        post_urls = [
            p.get("url", "")
            for p in latest_posts
            if p.get("url", "")
        ]

        profile = {
            "platform":           "instagram",
            "username":           raw.get("username", username),
            "full_name":          sanitise(raw.get("fullName", "")),
            "bio":                sanitise(raw.get("biography", "")),
            "is_private":         bool(raw.get("private", False)),
            "account_visibility": "private" if raw.get("private", False) else "public",
            "is_verified":        bool(raw.get("verified", False)),
            "followers":          raw.get("followersCount", 0) or 0,
            "following":          raw.get("followsCount", 0) or 0,
            "post_count":         raw.get("postsCount", 0) or 0,
            "profile_url":        f"https://www.instagram.com/{username}/",
            "post_urls":          post_urls[:5],  # top 5 posts for comment scraping
            "following_list":     [
                u.get("username", "").lower()
                for u in (raw.get("followingList") or [])
                if u.get("username")
            ],
        }
        log.info(
            "[Apify/Instagram] @%s | followers=%d | private=%s",
            profile["username"], profile["followers"], profile["is_private"],
        )
        return profile

    except Exception as exc:
        log.error("[Apify/Instagram] Failed for @%s: %s", username, exc)
        return {}


def fetch_instagram_comments(username: str, post_urls: list = None) -> list:
    """Fetch comments using post URLs extracted from the profile."""
    if not post_urls:
        log.info("[Apify/Instagram] No post URLs available for @%s — skipping comments.", username)
        return []

    log.info("[Apify/Instagram] Fetching comments for @%s (%d posts)…", username, len(post_urls))
    client = get_client()

    try:
        run = client.actor(config.APIFY_ACTORS["instagram_comments"]).call(run_input={
            "directUrls":   post_urls,
            "resultsLimit": config.MAX_COMMENTS,
        })
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        comments = [
            {
                "commenter": item.get("ownerUsername", ""),
                "text":      sanitise(item.get("text", "")),
                "timestamp": item.get("timestamp", ""),
            }
            for item in items
        ]
        log.info("[Apify/Instagram] Got %d comments for @%s", len(comments), username)
        return comments

    except Exception as exc:
        log.error("[Apify/Instagram] Comments failed for @%s: %s", username, exc)
        return []


# ── LINKEDIN ──────────────────────────────────────────────────────────────────

def fetch_linkedin_profile(identifier: str) -> dict:
    """
    Fetch LinkedIn profile metadata via Apify (harvestapi/linkedin-profile-scraper).

    `identifier` can be either:
      - a public identifier / slug, e.g. "williamhgates"
        (the part after linkedin.com/in/)
      - a full profile URL, e.g. "https://www.linkedin.com/in/williamhgates"

    Returns a normalised dict or empty dict on failure. LinkedIn profiles are
    always public by definition of this actor (no login-gated private scraping),
    so is_private is always False / account_visibility is always "public".
    """
    log.info("[Apify/LinkedIn] Fetching profile '%s'", identifier)
    client = get_client()

    is_url = identifier.strip().lower().startswith("http") or "linkedin.com" in identifier.lower()
    run_input = {"urls": [identifier]} if is_url else {"publicIdentifiers": [identifier]}

    try:
        run = client.actor(config.APIFY_ACTORS["linkedin_profile"]).call(run_input=run_input)
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        if not items:
            log.warning("[Apify/LinkedIn] No data for '%s'", identifier)
            return {}

        raw = items[0]

        first_name = raw.get("firstName", "") or ""
        last_name  = raw.get("lastName", "") or ""
        full_name  = sanitise(f"{first_name} {last_name}".strip())

        username = raw.get("publicIdentifier", identifier)

        location_obj = raw.get("location", {}) or {}
        location = sanitise(
            location_obj.get("linkedinText")
            or (location_obj.get("parsed") or {}).get("text", "")
        )

        current_position_list = raw.get("currentPosition", []) or []
        experience_list        = raw.get("experience", []) or []

        current_company = ""
        if current_position_list:
            current_company = sanitise(current_position_list[0].get("companyName", ""))
        elif experience_list:
            current_company = sanitise(experience_list[0].get("companyName", ""))

        current_position = ""
        if experience_list:
            current_position = sanitise(experience_list[0].get("position", ""))

        education_list = raw.get("education", []) or []
        schools = [
            sanitise(e.get("schoolName", ""))
            for e in education_list
            if e.get("schoolName")
        ]

        profile_url = raw.get("linkedinUrl", "") or f"https://www.linkedin.com/in/{username}/"

        profile = {
            "platform":           "linkedin",
            "username":           username,
            "full_name":          full_name,
            "bio":                sanitise(raw.get("about", "")),
            "headline":           sanitise(raw.get("headline", "")),
            "location":           location,
            "current_position":   current_position,
            "current_company":    current_company,
            "schools":            schools,
            "followers":          raw.get("followerCount", 0) or 0,
            "connections":        raw.get("connectionsCount", 0) or 0,
            "is_private":         False,
            "account_visibility": "public",
            "profile_url":        profile_url,
            "following_list":     [],
            "post_urls":          [],
        }

        log.info(
            "[Apify/LinkedIn] %s | connections=%d | followers=%d",
            profile["username"], profile["connections"], profile["followers"],
        )
        return profile

    except Exception as exc:
        log.error("[Apify/LinkedIn] Failed for '%s': %s", identifier, exc)
        return {}


# ── TWITTER/X ─────────────────────────────────────────────────────────────────

def fetch_twitter_profile(username: str) -> dict:
    """
    Fetch Twitter/X profile metadata via Apify.
    Returns a normalised dict or empty dict on failure.

    Apify output fields used:
      username, name, bio, location, followers, following,
      tweets_count, is_protected, is_blue_verified, is_verified,
      website, created_at, url
    """
    log.info("[Apify/Twitter] Fetching profile @%s", username)
    client = get_client()

    try:
        run = client.actor(config.APIFY_ACTORS["twitter_profile"]).call(run_input={
            "startUrls": [f"https://x.com/{username}"],
            "onlyUserInfo": True,
        })
        items = list(client.dataset(run.default_dataset_id).iterate_items())
        if not items:
            log.warning("[Apify/Twitter] No data for @%s", username)
            return {}

        raw = items[0]



        profile = {
            "platform":           "twitter",
            "username":           raw.get("username", username),
            "full_name":          sanitise(raw.get("name", "")),
            "bio":                sanitise(raw.get("bio", "")),
            "location":           sanitise(raw.get("location", "")),
            "website":            raw.get("website", ""),
            "is_private":         bool(raw.get("is_protected", False)),
            "account_visibility": "private" if raw.get("is_protected", False) else "public",
            "is_verified":        bool(raw.get("is_blue_verified") or raw.get("is_verified")),
            "followers":          raw.get("followers", 0) or 0,
            "following":          raw.get("following", 0) or 0,
            "tweet_count":        raw.get("tweets_count", 0) or 0,
            "profile_url":        raw.get("url", f"https://x.com/{username}"),
            "created_at":         raw.get("created_at", ""),
            "following_list":     [],  # not returned by this actor
        }

        log.info(
            "[Apify/Twitter] @%s | followers=%d | protected=%s",
            profile["username"], profile["followers"], profile["is_private"],
        )
        return profile

    except Exception as exc:
        log.error("[Apify/Twitter] Failed for @%s: %s", username, exc)
        return {}