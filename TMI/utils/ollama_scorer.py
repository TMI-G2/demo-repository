"""
utils/ollama_scorer.py
-----------------------
Local Ollama LLM risk scoring — zero data leaves the machine.
Uses format="json" for guaranteed valid JSON output every run.
Supports Instagram, Twitter, and LinkedIn with platform-specific rubrics.
"""

import json
import logging
import re

import ollama
import config

log = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a child online safety analyst. You assess social media profiles for
personal safety risk exposure. You are precise, evidence-based, and always
respond in valid JSON only — no markdown, no explanation outside the JSON.\
"""

# ── PII Pre-scanner ───────────────────────────────────────────────────────────

INSTITUTION_KEYWORDS = [
    "university", "college", "school", "academy", "institute", "uni",
    "hs", "ocad", "uoft", "mcmaster", "ubc", "queens", "ryerson", "tmu",
    "york", "waterloo", "carleton", "ottawa", "concordia", "dalhousie",
    "grade ", "year ", "class of", "form ", "sixth form",
]


def prescan_bio(bio: str) -> dict:
    """Regex + keyword scan of the bio field. Returns confirmed PII findings."""
    if not bio:
        return {}

    findings = {}
    bio_lower = bio.lower()

    email_match = re.search(r"[\w.+-]+@[\w-]+\.[a-z]{2,}", bio, re.IGNORECASE)
    if email_match:
        findings["email"] = email_match.group()

    phone_match = re.search(
        r"(\+?1[\s.-]?)?\(?\d{3}\)?[\s.-]?\d{3}[\s.-]?\d{4}", bio
    )
    if phone_match:
        findings["phone"] = phone_match.group()

    age_match = re.search(r"\b(1[3-9]|[2-5]\d)\b", bio)
    if age_match:
        findings["age"] = age_match.group()

    grade_match = re.search(
        r"\b(grade\s*\d+|year\s*\d+|class of \d{4}|form \d+)\b", bio_lower
    )
    if grade_match:
        findings["grade"] = grade_match.group()

    for kw in INSTITUTION_KEYWORDS:
        if kw in bio_lower:
            findings["institution"] = bio.strip()
            break

    location_match = re.search(
        r"\b(toronto|vancouver|montreal|calgary|ottawa|edmonton|"
        r"new york|london|sydney|melbourne|los angeles|chicago)\b",
        bio_lower,
    )
    if location_match:
        findings["location"] = location_match.group()

    return findings


def get_rubric(platform: str) -> dict:
    """Return the correct rubric for the given platform."""
    rubrics = getattr(config, "PLATFORM_RUBRICS", {})
    return rubrics.get(platform, config.RISK_RUBRIC)


def build_prompt(profile: dict, comments: list, flagged_following: list) -> str:
    # NOTE: flagged_following is accepted for backward compatibility with
    # Maltego-side callers, but is no longer used here — network_risk was
    # removed from the Instagram rubric since there is no real flagged-
    # account list in practice (KNOWN_BAD_ACCOUNTS_FILE is unset) and the
    # scraped following_list is stripped from the prompt below anyway.
    profile_clean = {k: v for k, v in profile.items() if k != "following_list"}

    bio = profile.get("bio", "") or ""
    pii_findings = prescan_bio(bio)
    pii_str = (
        f"BIO PII FINDINGS (confirmed by regex — treat as facts):\n"
        f"{json.dumps(pii_findings, ensure_ascii=False)}"
    ) if pii_findings else "None detected"

    platform = profile.get("platform", "instagram")
    platform_name = platform.upper()
    rubric = get_rubric(platform)

    # Platform-specific guidance for what recommendations actually make sense.
    # Prevents the model from suggesting settings changes that don't exist on
    # that platform (e.g. "make your LinkedIn profile private" — LinkedIn
    # profiles reachable by this scraper are public by definition, so that's
    # not an actionable recommendation).
    if platform == "linkedin":
        recommendation_guidance = (
            "Do NOT recommend making the LinkedIn account/profile private — "
            "LinkedIn profiles reachable by this scan are public by definition "
            "and there is no setting that changes that. Instead, if relevant, "
            "suggest platform-appropriate actions such as: limiting visible "
            "contact information, trimming employment/education history "
            "detail, reviewing 'who can see your connections' settings, or "
            "being selective about what appears in the headline/about section."
        )
    elif platform == "twitter":
        recommendation_guidance = (
            "Only recommend a protected/private account if account_visibility "
            "is currently 'public' — do not suggest it if the account is "
            "already private."
        )
    else:
        recommendation_guidance = (
            "Only recommend a private account if account_visibility is "
            "currently 'public' — do not suggest it if the account is "
            "already private."
        )

    # Build the category JSON template dynamically from the rubric
    cat_template = "\n".join(
        f'    "{k}":       {{"score": <int>, "evidence": "...", "reasoning": "..."}}'
        + ("," if i < len(rubric) - 1 else "")
        for i, k in enumerate(rubric.keys())
    )

    return f"""
You are scoring a {platform_name} profile for online safety risk.

PROFILE DATA:
{json.dumps(profile_clean, ensure_ascii=False, indent=2)}

PRE-SCANNED PII FINDINGS (confirmed by regex — treat as facts, score them accordingly):
{pii_str}

COMMENTS / POSTS ({min(len(comments), config.MAX_COMMENTS)} shown):
{json.dumps(comments[:config.MAX_COMMENTS], ensure_ascii=False, indent=2)}

SCORING RUBRIC (score each category from 0 to its max_points, total = 100):
{json.dumps(rubric, ensure_ascii=False, indent=2)}

INSTRUCTIONS:
- The PRE-SCANNED PII FINDINGS are confirmed facts. You MUST score them.
- For every OTHER category not covered by the pre-scanned findings, only assign
  points if the evidence is a literal, unambiguous match to one of the listed
  criteria. Do not infer age, grade, location, or any other signal from tone,
  slang, exclamations, religious/cultural expressions, or casual language.
  When in doubt, the score for that criterion MUST be 0.
- Example of INCORRECT scoring: a bio containing the phrase "Wallahi I'm
  finished" (a common expression of exasperation, unrelated to age) is NOT
  evidence of "age or grade year mentioned." Scoring bio_risk above 0 for
  that phrase alone is a mistake. The correct score for that criterion is 0.
- Example of INCORRECT scoring: a comment from another account reading
  "Consider me jealous af 😭" is a comment FROM A STRANGER, not something
  the profile owner said or did. Describing this as the user "responding to
  flattery" is a mistake — there is no data showing how the user responded
  to anything. For the stranger-comment-content portion of
  content_location_exposure specifically, only the comment's own content may
  be scored (e.g. does the comment itself contain romantic language, a gift
  offer, or a request for contact info) — never a claim about the account
  owner's behavior.
- Example of INCORRECT recommendation: for account_hygiene, a profile with
  only 2 posts scores 0 (the safe outcome) — it is a mistake to then
  recommend "increasing the post count for better hygiene." A low
  post_count is not a problem to fix; recommending more posts would make
  the account MORE exposed, not less. Never recommend posting more content
  or raising post_count anywhere in top_recommendations or analyst_summary.
- Every "evidence" field you return must be a real, verbatim quote taken
  directly from the PROFILE DATA or COMMENTS/POSTS above — never a
  paraphrase and never invented text.
- {recommendation_guidance}
- Score every rubric category. Quote specific text or data as evidence.
- total_risk_score = sum of all category scores (must equal 0-100).
- risk_level: "LOW" (0-19), "MEDIUM" (20-44), "HIGH" (45-69), "CRITICAL" (70-100).
- Return ONLY this exact JSON structure, nothing else:

{{
  "username": "...",
  "platform": "{platform}",
  "total_risk_score": <integer 0-100>,
  "risk_level": "LOW|MEDIUM|HIGH|CRITICAL",
  "category_scores": {{
{cat_template}
  }},
  "top_recommendations": ["...", "...", "..."],
  "analyst_summary": "2-3 sentence plain-English summary for a parent or guardian."
}}
"""


def score_profile(
    profile: dict,
    comments: list,
    flagged_following: list,
) -> dict:
    """Score a profile locally using Ollama. Nothing is sent to any external API."""
    username   = profile.get("username", "unknown")
    platform   = profile.get("platform", "instagram")
    visibility = profile.get("account_visibility", "public")

    log.info("[Ollama] Scoring @%s (%s) with %s …", username, platform, config.OLLAMA_MODEL)

    # Explicit timeout so a stuck/queued Ollama request fails fast instead of
    # hanging indefinitely (seen in practice: requests silently stalling for
    # 60s+ with no error, no progress, and no HTTP response logged at all).
    OLLAMA_TIMEOUT_SECONDS = 90
    client = ollama.Client(
        host=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )

    MAX_COMMENTS    = 20
    MAX_COMMENT_LEN = 150
    trimmed_comments = [
        c[:MAX_COMMENT_LEN] if isinstance(c, str) else c
        for c in comments[:MAX_COMMENTS]
    ]

    prompt = build_prompt(profile, trimmed_comments, flagged_following)
    log.info("[Ollama] Prompt length: %d characters", len(prompt))

    raw = ""

    # Try once, then retry once on connection/timeout-style failures only —
    # a stuck request or transient network blip often clears on a second
    # attempt once the model slot frees up. JSON parse failures are NOT
    # retried here since those go through _extract_json_fallback() instead.
    for attempt in (1, 2):
        try:
            response = client.chat(
                model=config.OLLAMA_MODEL,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user",   "content": prompt},
                ],
                format="json",
                options={
                    "num_predict": 1024,
                    "temperature": 0.1,
                },
            )

            raw = response.message.content.strip()
            log.info("[Ollama] Full raw response: %r", raw)

            raw = re.sub(r"^```(?:json)?\s*", "", raw)
            raw = re.sub(r"\s*```$", "", raw)

            result = json.loads(raw)
            break  # success — fall through to post-processing below

        except json.JSONDecodeError:
            log.warning("[Ollama] JSON parse failed — attempting extraction fallback")
            return _extract_json_fallback(raw, username, platform)

        except Exception as exc:
            if attempt == 1:
                log.warning(
                    "[Ollama] Attempt 1 failed for @%s (%s) — retrying once: %s",
                    username, platform, exc,
                )
                continue
            log.error(
                "[Ollama] Attempt 2 failed for @%s (%s), giving up: %s",
                username, platform, exc,
            )
            return _error_result(username, platform, str(exc))

    try:
        if "category_scores" not in result:
            result["category_scores"] = {}

        # ── Post-process: override categories with confirmed data ─────────────

        bio = profile.get("bio", "") or ""
        pii_findings = prescan_bio(bio)
        rubric = get_rubric(platform)

        # 1. pii_exposure — only override if pre-scanner found something
        pii_score   = 0
        pii_evidence = []
        if "email" in pii_findings:
            pii_score += 7
            pii_evidence.append(f"Email: {pii_findings['email']}")
        if "phone" in pii_findings:
            pii_score += 10
            pii_evidence.append(f"Phone: {pii_findings['phone']}")
        if "institution" in pii_findings:
            pii_score += 8
            pii_evidence.append(f"Institution: {pii_findings['institution']}")
        pii_score = min(pii_score, rubric.get("pii_exposure", {}).get("max_points", 30))
        if pii_evidence:
            result["category_scores"]["pii_exposure"] = {
                "score":     pii_score,
                "evidence":  ", ".join(pii_evidence),
                "reasoning": "Scored by pre-scanner.",
            }

        # 2. bio_risk — Twitter/LinkedIn only (Instagram merged bio_risk into
        #    content_location_exposure, handled separately below). Only
        #    override if pre-scanner found something.
        bio_score   = 0
        bio_evidence = []
        if "age" in pii_findings or "grade" in pii_findings:
            bio_score += 5
            bio_evidence.append(f"Age/grade: {pii_findings.get('age') or pii_findings.get('grade')}")
        if "institution" in pii_findings:
            bio_score += 5
            bio_evidence.append("Institution in bio")
        if "location" in pii_findings:
            bio_score += 5
            bio_evidence.append(f"Location: {pii_findings['location']}")
        bio_score = min(bio_score, rubric.get("bio_risk", {}).get("max_points", 15))
        if bio_evidence and "bio_risk" in rubric:
            result["category_scores"]["bio_risk"] = {
                "score":     bio_score,
                "evidence":  ", ".join(bio_evidence),
                "reasoning": "Scored by pre-scanner.",
            }

        # 2b. content_location_exposure — Instagram only. Only the
        #     bio-derived sub-component is deterministically overridden
        #     (capped at 20, the bio-content sub-bucket size within this
        #     merged 45-point category — NOT the full category max). The
        #     comment-PII and stranger-comment-content sub-components have
        #     no regex backing, so they remain fully LLM-judged; when this
        #     override fires it replaces the LLM's whole category score,
        #     same tradeoff already accepted for pii_exposure/bio_risk above.
        CONTENT_LOCATION_BIO_SUBCAP = 20
        cl_bio_score   = 0
        cl_bio_evidence = []
        if "age" in pii_findings or "grade" in pii_findings:
            cl_bio_score += 5
            cl_bio_evidence.append(f"Age/grade: {pii_findings.get('age') or pii_findings.get('grade')}")
        if "institution" in pii_findings:
            cl_bio_score += 5
            cl_bio_evidence.append("Institution in bio")
        if "location" in pii_findings:
            cl_bio_score += 4
            cl_bio_evidence.append(f"Location: {pii_findings['location']}")
        cl_bio_score = min(cl_bio_score, CONTENT_LOCATION_BIO_SUBCAP)
        if cl_bio_evidence and "content_location_exposure" in rubric:
            result["category_scores"]["content_location_exposure"] = {
                "score":     cl_bio_score,
                "evidence":  ", ".join(cl_bio_evidence),
                "reasoning": "Scored by pre-scanner (bio-derived signals only).",
            }

        # 3. private_account — always override with actual scraped data
        max_private = rubric.get("private_account", {}).get("max_points", 10)
        if "private_account" in rubric:
            result["category_scores"]["private_account"] = {
                "score":     max_private if visibility == "public" else 0,
                "evidence":  f"account_visibility = '{visibility}'",
                "reasoning": "Public account has full exposure." if visibility == "public"
                             else "Private account restricts content access.",
            }

        # 4. account_hygiene — Instagram only, always overridden from the
        #    actual post_count field. This is a simple numeric threshold, and
        #    the LLM's own arithmetic has proven unreliable in practice (it
        #    has repeatedly miscalculated its own total_risk_score even when
        #    just summing 5-6 numbers) — so this is computed directly rather
        #    than trusted to the model.
        if "account_hygiene" in rubric:
            post_count = profile.get("post_count", 0) or 0
            max_hygiene = rubric.get("account_hygiene", {}).get("max_points", 10)
            if post_count >= 500:
                hygiene_score = max_hygiene
            elif post_count >= 200:
                hygiene_score = round(max_hygiene * 0.7)
            elif post_count >= 50:
                hygiene_score = round(max_hygiene * 0.3)
            else:
                hygiene_score = 0
            result["category_scores"]["account_hygiene"] = {
                "score":     hygiene_score,
                "evidence":  f"post_count = {post_count}",
                "reasoning": (
                    f"{post_count} posts on the account — large, unpruned "
                    "post history increases exposure of old content and "
                    "outdated personal information."
                    if hygiene_score > 0 else
                    f"{post_count} posts — limited historical content exposure."
                ),
            }

        # 5. Recalculate total from all category scores
        computed_total = sum(
            v.get("score", 0)
            for v in result["category_scores"].values()
            if isinstance(v, dict)
        )
        result["total_risk_score"] = min(computed_total, 100)

        # 6. Recalculate risk_level
        score = result["total_risk_score"]
        if score <= 19:
            result["risk_level"] = "LOW"
        elif score <= 44:
            result["risk_level"] = "MEDIUM"
        elif score <= 69:
            result["risk_level"] = "HIGH"
        else:
            result["risk_level"] = "CRITICAL"

        # 7. Force correct username and platform
        result["username"] = profile.get("username", result.get("username", "unknown"))
        result["platform"] = platform

        log.info(
            "[Ollama] @%s (%s) → %d/100 (%s)",
            username, platform,
            result.get("total_risk_score", 0),
            result.get("risk_level", "?"),
        )
        return result

    except Exception as exc:
        # Post-processing errors only (API call + JSON parsing already
        # handled inside the retry loop above).
        log.error("[Ollama] Unexpected error processing result for @%s: %s", username, exc)
        return _error_result(username, platform, str(exc))


def _extract_json_fallback(raw: str, username: str, platform: str = "instagram") -> dict:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            pass
    return _error_result(username, platform, "Could not parse model output as JSON")


def _error_result(username: str, platform: str = "instagram", error: str = "") -> dict:
    return {
        "username":            username,
        "platform":            platform,
        "total_risk_score":    -1,
        "risk_level":          "ERROR",
        "category_scores":     {},
        "top_recommendations": [],
        "analyst_summary":     f"Scoring failed: {error}",
        "error":               error,
    }


def check_ollama_available() -> bool:
    try:
        client    = ollama.Client(host=f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}")
        models    = client.list()
        available = [m.model for m in models.models]
        base      = config.OLLAMA_MODEL.split(":")[0]
        found     = any(base in m for m in available)
        if not found:
            log.error("Model '%s' not found. Run: ollama pull %s",
                      config.OLLAMA_MODEL, config.OLLAMA_MODEL)
        return found
    except Exception as exc:
        log.error("Cannot reach Ollama: %s — is it running?", exc)
        return False