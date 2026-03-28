# Chinese Reading Newsletter — 今日讀報

## Purpose
A daily Chinese reading site for a single user. A Claude Code pipeline generates multiple page types — news, classical wisdom, and culture desk articles — in Traditional Chinese at a calibrated reading level, served as static HTML via GitHub Pages. The user reads in Chrome with the Zhongwen extension for hover-based character lookup.

## User Background
- Heritage Mandarin speaker (rusty), actively re-learning
- Lives in Chicago
- PhD climate scientist — builds hurricane catastrophe models for industry. Technically proficient but no web development experience
- Reads: HN, FT-style econ/finance, Marginal Revolution, AI/AGI, climate science, Michigan football/basketball, Cubs baseball

## Technical Constraints
- **Traditional Chinese only** (繁體中文) — never output simplified characters
- **Zhongwen extension compatibility** — all Chinese text in standard DOM elements (p, span, h2, li, etc.); no canvas, SVG text, or CSS content for readable characters
- **GitHub Pages delivery** — site served from docs/ directory
- **Dark theme** — night-mode color scheme (dark navy background `#1a1a2e`, warm light text `#e0dcd4`). All generated HTML uses the dark palette from `templates/_shared.css`
- **Claude Opus for generation** — use Opus for all content generation (articles, wisdom, obsessions)
- **No frameworks** — vanilla HTML/CSS/JS only in generated output

## Site Structure
```
docs/
  index.html              ← Newsletter (latest issue)
  wisdom.html             ← Daily Wisdom (latest, idempotent per day)
  obsessions.html         ← Obsessions culture desk (latest)
  archive/
    YYYY-MM-DD.html       ← Newsletter archives
    wisdom/
      YYYY-MM-DD.html     ← Wisdom archives
    obsessions/
      YYYY-MM-DD.html     ← Obsessions archives
```

## File Structure
- `config/settings.json` — reading level, article count, timezone, global prefs
- `config/interests.json` — newsletter topic labels, source hints, selection guidance
- `config/wisdom.json` — wisdom source configs (Heart Sutra, Mengzi, Zen)
- `config/obsessions.json` — obsession definitions + editorial voice
- `data/wisdom_progress.json` — Mengzi + Zen passage tracking
- `data/sources/` — cached source texts (Heart Sutra, Mengzi, Zen passages)
- `templates/_shared.css` — shared CSS for all page types
- `templates/_shared.js` — shared JS (translation toggle, mobile glossary popup)
- `templates/newsletter.html` — newsletter reference template
- `templates/wisdom.html` — wisdom reference template
- `templates/obsessions.html` — obsessions reference template
- `scripts/assemble.py` — page-type-aware HTML assembly (`--page-type newsletter|wisdom|obsessions`)
- `scripts/validate.py` — page-type-aware validation (`--page-type newsletter|wisdom|obsessions`)
- `scripts/glossary_lookup.py` — CEDICT dictionary pre-match for glossary
- `scripts/build_wisdom_sources.py` — fetch and cache Heart Sutra + Mengzi texts

## Commands
- `/go` — daily orchestrator: runs `/newsletter` → `/wisdom` → `/obsessions` sequentially
- `/newsletter` — full news pipeline: scout → select → research → write → translate → glossary → assemble → validate → commit/push
- `/wisdom` — wisdom pipeline: select passages → wrap chars → translate (cached or agent) → glossary → assemble → commit/push. Idempotent per day.
- `/obsessions` — obsessions pipeline: scout → write → translate → glossary → assemble → commit/push
- `/se <topic> [char_count]` — on-demand Special Edition: research → write → translate → glossary → insert into current newsletter → commit/push. Ephemeral (wiped on next `/newsletter` run).

## Reading Level Approach
Reading level is natural language guidance to Claude Opus, NOT a character whitelist. Current setting: grade 4 (Taiwanese elementary school equivalent). The description in settings.json tells Claude what vocabulary, grammar, and character complexity to target. Adjust by editing the description conversationally.

## Tone Guidelines
- **Newsletter:** Knowledgeable friend explaining the news over coffee. Casual but informed.
- **Wisdom:** Faithful rendering of classical texts with clear modern translations.
- **Obsessions:** Museum curator voice — real knowledge shared vividly and succinctly.

## Editorial Identity
The Economist, reimagined as a Chicago-based local newspaper. Analytical, globally-minded, data-literate. Transformative AI is the defining story of our era. Articles 5-6 are always from the sports desk: Article 5 covers Chicago & Michigan (Cubs, Bulls, Bears, Michigan football & basketball), Article 6 is the Arsenal beat (兵工廠線).

## Story Selection Rules
- Articles 1-4 come from the Economist desk: AI, economics, international affairs, US policy, Chicago, business, science & ideas. Aim for variety but don't force every category.
- Article 5 is ALWAYS a Chicago/Michigan sports story (Cubs, Bulls, Bears, Michigan football & basketball).
- Article 6 is ALWAYS an Arsenal football story, introduced as the Arsenal beat (兵工廠線).
- Strong preference for stories from the past 36 hours.
- Stories must NOT repeat from past newsletters unless there has been a substantive update.
- AI should appear in most issues — it's the paper's lead beat — but doesn't need to lead every issue.
- The paper should feel like flipping through a smart, cosmopolitan local newspaper, not a hyper-targeted feed.

## Daily Wisdom
Three sections served daily:
- **Heart Sutra** — 7 segments, one per weekday (Monday=0), cycles weekly
- **Mengzi (Mencius)** — sequential passages, advances one per day
- **Zen Buddhism** — sequential passages from curated source, advances one per day

Cached translations are used when available (Heart Sutra, Mengzi from ctext.org). Agent translation only when no cached version exists.

## Obsessions
User-configured topics in `config/obsessions.json`. Each active obsession gets a web-searched, specifically-sourced article daily. Museum curator editorial voice. User adds/removes/edits obsessions by editing the config file directly.

## Special Edition
On-demand deep-dive articles via `/se`. Inserts into the current newsletter page below main articles. Multiple SEs per day supported. Ephemeral — wiped when newsletter regenerates.

## Deferred
- Mobile-optimized layout
- Automated daily scheduling (cron/launchd)
- Reading level auto-progression
- SE preservation across regeneration (`--preserve-se` flag)

## Conventions
- `USER:` prefix for inline annotations in plan/research docs
- Dates in YYYY-MM-DD format, America/Chicago timezone
- Multiple issues per day allowed; current issue always at index file; previous same-day issues archived with `-2`, `-3` suffixes
