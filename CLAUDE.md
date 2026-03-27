# Chinese Reading Newsletter — 今日讀報

## Purpose
A daily Chinese reading newsletter for a single user. A Claude Code pipeline searches English-language news, selects 5 stories, rewrites them in Traditional Chinese at a calibrated reading level, and outputs an HTML file served via GitHub Pages. The user reads in Chrome with the Zhongwen: Chinese-English Dictionary extension for hover-based character lookup.

## User Background
- Heritage Mandarin speaker (rusty), actively re-learning
- Lives in Chicago
- PhD climate scientist — builds hurricane catastrophe models for industry. Technically proficient but no web development experience
- Reads: HN, FT-style econ/finance, Marginal Revolution, AI/AGI, climate science, Michigan football/basketball, Cubs baseball

## Technical Constraints
- **Traditional Chinese only** (繁體中文) — never output simplified characters
- **Zhongwen extension compatibility** — all Chinese text in standard DOM elements (p, span, h2, li, etc.); no canvas, SVG text, or CSS content for readable characters
- **GitHub Pages delivery** — newsletter served from docs/ directory; docs/index.html is always the latest issue
- **Dark theme** — night-mode color scheme (dark navy background `#1a1a2e`, warm light text `#e0dcd4`). All generated HTML must use the dark palette from `templates/newsletter.html`
- **Claude Opus for generation** — use Opus for all newsletter content generation
- **No frameworks** — vanilla HTML/CSS/JS only in generated output

## File Structure
- `config/settings.json` — reading level, article count, timezone, global prefs
- `config/interests.json` — topic labels, source hints, selection guidance
- `data/flagged_characters.json` — per-character struggling/learned states with dates
- `data/preference_history.json` — editor's desk sessions (offered headlines + user picks)
- `docs/index.html` — current newsletter (GitHub Pages serves this)
- `docs/archive/` — past newsletters (YYYY-MM-DD.html, YYYY-MM-DD-2.html for same-day re-runs)
- `templates/newsletter.html` — reference HTML for generation (spec, not runtime template)
- `scripts/generate_prompt.md` — generation pipeline documentation and CC prompt
- `scripts/cleanup_prompt.md` — cleanup pipeline documentation and CC prompt

## Reading Level Approach
Reading level is natural language guidance to Claude Opus, NOT a character whitelist. Current setting: grade 5 (Taiwanese elementary school equivalent). The description in settings.json tells Claude what vocabulary, grammar, and character complexity to target. Adjust by editing the description conversationally.

## Tone Guidelines
Write like a **knowledgeable friend explaining the news over coffee**. Casual but informed. Uses grammatical structures practical for daily conversation. Crucial proper nouns stay intact; complex domain concepts are simplified naturally. The friend knows the user and doesn't talk down — just speaks clearly.

## Feedback System
1. User reads the newsletter at the GitHub Pages URL in Chrome
2. User clicks characters to flag as struggling or mark as learned
3. User selects top 3 headlines in the Editor's Desk section
4. All feedback stored in localStorage during the reading session
5. User clicks "Export Feedback" — triggers a JSON file download to `~/Downloads/`
6. Next morning, user types `/go` in a fresh CC session — cleanup processes feedback, then generation produces the new issue

The user's daily workflow is just two actions: (1) click "Export Feedback" after reading, (2) type `/go` the next morning. The `/go` command handles everything else.

### Feedback File Location
Cleanup scans `~/Downloads/` for files matching `feedback_*.json`. Files are deleted after successful processing. If no files are found, cleanup is silently skipped — this is normal (the user may not have read yesterday's issue).

## Character States
- **struggling** — user flagged as difficult. Pipeline increases natural frequency in future articles.
- **learned** — user marked as mastered. Pipeline stops boosting; appears at natural frequency.
- **unmarked** (default) — never flagged. Natural frequency.

### Merge Rules
- Later feedback files override earlier ones for the same character (e.g., if 03-11 says "struggling" and 03-12 says "learned", final state is "learned")
- A character explicitly set to "unmarked" is removed from `flagged_characters.json` entirely — no longer tracked
- A character absent from a feedback file is unchanged — absence means "no update", not "remove"

## Editor's Desk
Each newsletter includes 3 headlines that made the cut and 3 that didn't. User picks their top 3 from all 6. This data (what was offered + what was chosen) is stored in preference_history.json and included in future generation prompts to refine story selection. Claude pattern-matches on this history — no scoring algorithm needed.

## Editorial Identity
The Economist, reimagined as a Chicago-based local newspaper. Analytical, globally-minded, data-literate. Transformative AI is the defining story of our era. Article 5 is always from the sports desk (Cubs, Bulls, Bears, Michigan football & basketball).

## Story Selection Rules
- Articles 1-4 come from the Economist desk: AI, economics, international affairs, US policy, Chicago, business, science & ideas. Aim for variety but don't force every category.
- Article 5 is ALWAYS a sports story.
- Strong preference for stories from the past 36 hours. Older stories are acceptable only if they are unusually significant or interesting.
- Stories must NOT repeat from past newsletters unless there has been a substantive update or development in the story. Check `docs/archive/` for recent issues before selecting stories.
- AI should appear in most issues — it's the paper's lead beat — but doesn't need to lead every issue.
- The paper should feel like flipping through a smart, cosmopolitan local newspaper, not a hyper-targeted feed.

## Current Scope (Sprint 1)
- Repo structure, config files, CLAUDE.md
- Reference HTML template (Zhongwen-compatible, character flagging, translation toggle, editor's desk, feedback export)
- Generation pipeline (web search → select → rewrite → HTML → commit/push)
- Cleanup pipeline (merge feedback → commit/push)
- End-to-end test: generate one newsletter, read it, give feedback, run cleanup
- `/go` command (cleanup + generation in one step)

## Deferred
- Mobile-optimized layout
- Automated daily scheduling (cron/launchd — requires validating non-interactive CC invocation)
- Reading level auto-progression based on flagging rates
- Preference history trimming/summarization

## Conventions
- `USER:` prefix for inline annotations in plan/research docs
- Dates in YYYY-MM-DD format, America/Chicago timezone
- Multiple newsletters per day allowed; current issue always at docs/index.html; previous same-day issues archived with `-2`, `-3` suffixes
