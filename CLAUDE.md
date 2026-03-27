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
- `docs/index.html` — current newsletter (GitHub Pages serves this)
- `docs/archive/` — past newsletters (YYYY-MM-DD.html, YYYY-MM-DD-2.html for same-day re-runs)
- `templates/newsletter.html` — reference HTML for generation (spec, not runtime template)
- `scripts/assemble.py` — deterministic HTML assembly from pipeline checkpoints
- `scripts/validate.py` — post-assembly validation
- `scripts/glossary_lookup.py` — CEDICT dictionary pre-match for glossary
- `scripts/generate_prompt.md` — generation pipeline documentation

## Reading Level Approach
Reading level is natural language guidance to Claude Opus, NOT a character whitelist. Current setting: grade 5 (Taiwanese elementary school equivalent). The description in settings.json tells Claude what vocabulary, grammar, and character complexity to target. Adjust by editing the description conversationally.

## Tone Guidelines
Write like a **knowledgeable friend explaining the news over coffee**. Casual but informed. Uses grammatical structures practical for daily conversation. Crucial proper nouns stay intact; complex domain concepts are simplified naturally. The friend knows the user and doesn't talk down — just speaks clearly.

## Daily Workflow
The user types `/go` in a CC session each morning. The pipeline searches for news, selects stories, writes articles, and publishes the newsletter.

## Editorial Identity
The Economist, reimagined as a Chicago-based local newspaper. Analytical, globally-minded, data-literate. Transformative AI is the defining story of our era. Article 5 is always from the sports desk (Cubs, Bulls, Bears, Michigan football & basketball).

## Story Selection Rules
- Articles 1-4 come from the Economist desk: AI, economics, international affairs, US policy, Chicago, business, science & ideas. Aim for variety but don't force every category.
- Article 5 is ALWAYS a sports story.
- Strong preference for stories from the past 36 hours. Older stories are acceptable only if they are unusually significant or interesting.
- Stories must NOT repeat from past newsletters unless there has been a substantive update or development in the story. Check `docs/archive/` for recent issues before selecting stories.
- AI should appear in most issues — it's the paper's lead beat — but doesn't need to lead every issue.
- The paper should feel like flipping through a smart, cosmopolitan local newspaper, not a hyper-targeted feed.

## Current Scope
- Newsletter generation pipeline (web search → select → rewrite → HTML → commit/push)
- Reference HTML template (Zhongwen-compatible, translation toggle, mobile glossary popup)
- `/go` command runs the full pipeline

## Deferred
- Mobile-optimized layout
- Automated daily scheduling (cron/launchd)
- Reading level auto-progression
- Multi-page site expansion (Daily Wisdom, Obsessions, Special Edition) — see `plans/expansion-plan.md`

## Conventions
- `USER:` prefix for inline annotations in plan/research docs
- Dates in YYYY-MM-DD format, America/Chicago timezone
- Multiple newsletters per day allowed; current issue always at docs/index.html; previous same-day issues archived with `-2`, `-3` suffixes
