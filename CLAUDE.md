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
- `data/obsessions_headline_log.json` — running headline log with `topic` field for semantic dedup
- `data/newsletter_topic_ledger.json` — newsletter `topic`+`angle` log for semantic/angle dedup (read by story-selector, appended by `ledger_update.py`)
- `data/polyphonic_chars.json` — committed list of polyphonic (多音字) single characters; routes them to the context-aware glossary agent instead of a context-blind dictionary reading
- `data/wisdom_progress.json` — Mengzi + Zen passage tracking
- `data/sources/` — cached source texts (Heart Sutra, Mengzi, Zen passages)
- `templates/_shared.css` — shared CSS for all page types
- `templates/_shared.js` — shared JS (translation toggle, mobile glossary popup)
- `templates/newsletter.html` — newsletter reference template
- `templates/wisdom.html` — wisdom reference template
- `templates/obsessions.html` — obsessions reference template
- `scripts/assemble.py` — page-type-aware HTML assembly (`--page-type newsletter|wisdom|obsessions`)
- `scripts/validate.py` — page-type-aware validation (`--page-type newsletter|wisdom|obsessions`)
- `scripts/glossary_lookup.py` — CEDICT dictionary pre-match for glossary; routes polyphonic chars (from `data/polyphonic_chars.json`) to the context-aware agent
- `scripts/build_dictionary.py` — build CEDICT dictionary (gitignored) + emit committed `data/polyphonic_chars.json`
- `scripts/ledger_update.py` — append a published issue's stories to `data/newsletter_topic_ledger.json`
- `scripts/build_wisdom_sources.py` — fetch and cache Heart Sutra + Mengzi texts

## Commands
- `/go` — daily orchestrator: runs `/newsletter` → `/wisdom` → `/obsessions` sequentially
- `/newsletter` — full news pipeline: scout → select → write (with integrated research) → translate → glossary → assemble → validate → commit/push
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
- Article 5 is ALWAYS a Chicago/Michigan sports story (Cubs, Bulls, Bears, Michigan football & basketball). Article 6 is ALWAYS an Arsenal football story, introduced as the Arsenal beat (兵工廠線). These are reserved beats — but the angle-fatigue rule below applies to them too: on a quiet day pick a fresh facet (preview, player feature, transfer/injury news, season-arc analysis), never reprint the last result.
- **Freshness is non-negotiable.** Every story must have a `published` timestamp within the past 24 hours. A 4-story issue that's all fresh is better than a 6-story issue padded with stale filler.
- **Running stories are welcome — but only with a new ANGLE.** An ongoing story (war, tournament, AI race) can appear on consecutive days, but the test is NOT "did something happen?" (a 1-0 loss and a 2-0 loss both happened). The test is "does today's installment give the reader an angle they haven't seen this week?" A changed score/number alone is the same story — drop it. One event yields several *different* stories over the following days (result → reaction → expert post-mortem → transfer/financial implications → what's next), not the same recap reprinted.
- **Topic ledger.** The selector reads `data/newsletter_topic_ledger.json` — a log of each recent issue's story `topic` + `angle` — to enforce the angle-fatigue rule semantically (not just exact-headline dedup). `scripts/ledger_update.py` appends each published issue's stories (Step 5.7 of `/newsletter`). This is the newsletter analog of `data/obsessions_headline_log.json`.
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

## Local vs. Remote
The daily pipeline runs unattended on a VM via a scheduled Claude routine and commits/pushes to `origin/main`; the user does **not** run it from this local clone. Expect **`origin/main` to be far ahead of local** (often 100+ commits of newsletter/wisdom/obsessions runs). This is normal, not a problem. Before committing local changes, always `git fetch origin main` and `git pull --rebase origin main` first. Those daily commits only touch generated content (`docs/`, glossary JSON, `data/` logs), so they rarely conflict with edits to pipeline source (agents, scripts, configs) — a rebase is typically clean.
