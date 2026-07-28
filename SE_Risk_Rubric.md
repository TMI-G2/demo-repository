# Social Engineering Risk Rubric

OSINT-based scoring framework for assessing social media exposure to social engineering attacks.
Each platform is scored out of **100 points**. Higher score = larger attack surface available to a social engineer.

---

## Risk Tiers

| Score | Tier | Description |
|-------|------|-------------|
| 0 – 19 | 🟢 LOW | Minimal social engineering exposure |
| 20 – 44 | 🟡 MEDIUM | Some exploitable indicators present |
| 45 – 69 | 🟠 HIGH | Significant pretexting surface available |
| 70 – 100 | 🔴 CRITICAL | Rich attack profile — immediate review needed |

---

## Platforms

- [Instagram](#instagram)
- [Twitter / X](#twitter--x)
- [LinkedIn](#linkedin)

---

## Instagram

### Category 1 — PII & Profile Exposure `max 30 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Full legal name visible on profile | 11 pts | Collapses pseudonymity. Enables cross-platform search, court records, and breach database correlation. Prerequisite for weaponising every other PII field. |
| Email address visible / inferrable from bio or captions | 10 pts | Primary delivery channel for spear-phishing. Confirmed contact point — no guessing required. |
| Date of birth visible | 9 pts | Combined with real name: sufficient to pass verbal identity verification at banks and telecoms. SIM-swap social engineering vector. |

**Category total: 30 pts**

---

### Category 2 — Content & Location Exposure `max 45 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Geotags enabled on posts / stories | 14 pts | Native metadata, fully automatable to detect. Builds a complete pattern-of-life map: home address, workplace, daily routine. |
| Bio reveals location, school, or workplace | 10 pts | Static declaration anchoring subject to a physical institution. Enables institutional pretexts ("I'm calling from your school's IT department") immediately. |
| PII disclosed by others in comments (phone, email, location) | 9 pts | Third-party disclosure beyond the subject's control. Persistently visible and difficult to fully remediate. |
| Engagement with strangers — sharing plans or responding to gifts / flattery | 7 pts | Behavioural susceptibility signal. Indicates rapport-based approaches will receive a response. |
| Posts contain minors with identifying info | 5 pts | School names, uniforms, and routines create family-based leverage for urgency pretexts targeting the account holder. |

**Category total: 45 pts**

---

### Category 3 — Account Privacy Settings `max 15 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Account set to public | 10 pts | Full post history, follower/following list, tagged content, and stories freely accessible with zero friction. Gate that makes all content-based indicators exploitable. |
| Stories unrestricted (no Close Friends use) | 5 pts | Real-time context feed open to all followers including unknown or attacker-controlled accounts. Requires attacker to be a follower — one step of friction. |

**Category total: 15 pts**

---

### Category 4 — Account Hygiene `max 10 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Account inactive 12+ months but still public | 6 pts | Dormant accounts go unmonitored. Post history provides authentic-looking material for impersonation clones that the owner won't notice. |
| Username exactly matches other platforms | 4 pts | Trivial cross-platform aggregation. Allows attacker to build a dossier from LinkedIn, Twitter, Reddit, and GitHub from a single identifier. |

**Category total: 10 pts**

---

### Instagram Total: `100 pts`

| Category | Points |
|----------|--------|
| PII & Profile Exposure | 30 |
| Content & Location Exposure | 45 |
| Account Privacy Settings | 15 |
| Account Hygiene | 10 |
| **Total** | **100** |

---

## Twitter / X

### Category 1 — PII & Profile Exposure `max 50 pts`

> Twitter is bio-first. The profile fields are the only reliable data surface — unlike Instagram where risk is distributed across posts, stories, and comments. This is why PII alone carries 50 pts (half the total score).

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Full legal name in display name or bio | 14 pts | Appears on every tweet and reply — more persistently and prominently exposed than an Instagram bio field. |
| Phone number visible | 12 pts | Directly actionable for vishing. Enables reverse lookup revealing carrier, address, and name history. No additional research required. |
| Email address visible / inferrable | 10 pts | Primary spear-phishing delivery channel. Same risk mechanism as Instagram. |
| Home address or neighbourhood in location field | 9 pts | Persistent single field. Less precise than a geotag series but permanently available without any post-history analysis. |
| School or workplace named in bio | 5 pts | Corroborates LinkedIn data. Enables institution-specific pretexts. |

**Category total: 50 pts**

---

### Category 2 — Account Privacy Settings `max 15 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Account not protected (tweets public) | 15 pts | Zero access friction — every tweet, reply, like, and follower list accessible with no account required. Single binary flag; carries the full 15 pts. |

**Category total: 15 pts**

---

### Category 3 — Bio Risk Signals `max 35 pts`

> Twitter bios are high-density self-descriptions. Users are expected to write about themselves here — age, location, school, interests, and relationship status can all appear in a single 160-character field.

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Age or grade level stated in bio | 10 pts | Calibrates the entire attack approach. Grade level confirms minor status, significantly expanding applicable vectors. |
| Specific location or neighbourhood in bio | 9 pts | More granular than the location field. Enables physical-proximity pretexts and narrows target geography precisely. |
| School or institution named in bio | 8 pts | Highly credible institutional pretexts. Especially effective against younger subjects. |
| Contact solicitation in bio | 5 pts | "DMs open" removes outreach friction. Subject has pre-approved contact from strangers. |
| Romantic or sexual signals in bio | 3 pts | Targeting signal indicating susceptibility to romance-based social engineering. |

**Category total: 35 pts**

---

### Twitter / X Total: `100 pts`

| Category | Points |
|----------|--------|
| PII & Profile Exposure | 50 |
| Account Privacy Settings | 15 |
| Bio Risk Signals | 35 |
| **Total** | **100** |

---

## LinkedIn

> LinkedIn carries both personal and professional risk. It is the single richest OSINT source for corporate-targeted social engineering — an attacker can identify employer, title, manager, colleagues, career history, and direct contact info in one place.

### Category 1 — PII & Profile Exposure `max 40 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Name + employer + role combination visible | 15 pts | Highest-weighted single indicator across all three platforms. Complete professional identity package enabling impersonation of IT, HR, vendors, or regulators — and attacks against the employer as well as the individual. |
| Personal email address listed | 10 pts | Non-corporate channel that bypasses employer email security and monitoring. Spear-phishing lures are more convincing in a professional context. |
| Phone number visible | 9 pts | Often a work mobile — reaches subject in a professional frame of mind, increasing susceptibility to authority-based pretexts. |
| Home address or personal location listed | 6 pts | Contributes to a comprehensive target profile. Less directly weaponisable on LinkedIn than on Instagram — primary surface here is professional, not physical. |

**Category total: 40 pts**

---

### Category 2 — Account Privacy Settings `max 0 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| No private state — publicly scraped by default | — | LinkedIn profiles are indexed by search engines and accessible to any logged-in user. Privacy settings are trivially bypassed with a free account and a search engine. **Zero points is a deliberate architectural observation, not an omission.** |

**Category total: 0 pts**

---

### Category 3 — Bio Risk Signals `max 15 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Graduation year revealing approximate age | 5 pts | High-accuracy age inference. Combined with name and employer: sufficient for many identity verification checks. |
| Specific personal location in headline / About | 5 pts | Granularity beyond the standard location field. Enables proximity-based pretexts. |
| Personal life details in headline or About section | 5 pts | Rapport-building material. Family, hobbies, and values give an attacker immediate conversation openers for pretexting calls. |

**Category total: 15 pts**

---

### Category 4 — Professional Exposure `max 25 pts`

> LinkedIn-exclusive category. No other platform in this rubric is designed to collect and publicly display employment history as its core function.

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Current employer and title publicly visible | 10 pts | Entry point for every corporate social engineering attack. Enables targeted impersonation and attacks against the organisation. |
| 3+ past employers listed (detailed career timeline) | 9 pts | Enables false-familiarity pretexts ("I worked with you at [company] in 2019"). Reveals industry network and career trajectory. |
| Detailed education history visible | 6 pts | Pretexting material for alumni associations, credential verification services, and academic institution impersonation. |

**Category total: 25 pts**

---

### Category 5 — Contact & Cross-platform Links `max 20 pts`

| Indicator | Points | Justification |
|-----------|--------|---------------|
| Email or phone in contact info section | 9 pts | Available to any logged-in LinkedIn user. Direct attack channel combining professional credibility with a personal contact point. |
| Personal website linked | 6 pts | May reveal additional PII not on LinkedIn — personal email, address, or unguarded personal narrative. Conditional amplifier. |
| Other social handles linked (Twitter, GitHub, etc.) | 5 pts | Turns LinkedIn into a gateway to a multi-platform dossier. Each linked platform adds a different intelligence layer. |

**Category total: 20 pts**

---

### LinkedIn Total: `100 pts`

| Category | Points |
|----------|--------|
| PII & Profile Exposure | 40 |
| Account Privacy Settings | 0 |
| Bio Risk Signals | 15 |
| Professional Exposure | 25 |
| Contact & Cross-platform Links | 20 |
| **Total** | **100** |

---

## Cross-Platform Comparison

| Category | Instagram | Twitter / X | LinkedIn |
|----------|-----------|-------------|----------|
| PII & Profile Exposure | 30 | 50 | 40 |
| Content & Location Exposure | 45 | — | — |
| Account Privacy Settings | 15 | 15 | 0 |
| Account Hygiene | 10 | — | — |
| Bio Risk Signals | — | 35 | 15 |
| Professional Exposure | — | — | 25 |
| Contact & Cross-platform Links | — | — | 20 |
| **Total** | **100** | **100** | **100** |

---

## Notes

- **Authentication indicators are intentionally excluded.** This rubric focuses exclusively on what is observable via OSINT. MFA status, password strength, and recovery methods are internal account security indicators — not visible to a social engineering attacker and therefore not scored.
- **Photo background analysis is excluded.** Extracting geolocation from image backgrounds requires computer vision analysis that lacks sufficient reliability and consistency to score fairly.
- **LinkedIn privacy is scored at zero by design.** LinkedIn profiles are indexed by search engines and accessible to any logged-in member. No private state exists that a social engineering attacker cannot trivially circumvent.
- Categories differ per platform because each platform has a structurally different data surface. Instagram is content-first; Twitter is bio-first; LinkedIn is identity-and-career-first.
