# Chinese Reading Newsletter — 今日讀報

## Purpose
A daily Chinese reading newsletter for a single user. A Claude Code pipeline searches English-language news, selects 5 stories, rewrites them in Traditional Chinese at a calibrated reading level, and outputs an HTML file served via GitHub Pages. The user reads in Chrome with the Zhongwen: Chinese-English Dictionary extension for hover-based character lookup.

## User Background
- Heritage Mandarin speaker (rusty), actively re-learning
- Lives in Taipei
- PhD climate scientist — technically proficient but no web development experience
- Reads: HN, FT-style econ/finance, Marginal Revolution, AI/AGI, climate science, Michigan football/basketball, Cubs baseball

## Technical Constraints
- **Traditional Chinese only** (繁體中文) — never output simplified characters
- **Zhongwen extension compatibility** — all Chinese text in standard DOM elements (p, span, h2, li, etc.); no canvas, SVG text, or CSS content for readable characters
- **GitHub Pages delivery** — newsletter served from docs/ directory; docs/index.html is always the latest issue
- **Claude Opus for generation** — use Opus for all newsletter content generation
- **No frameworks** — vanilla HTML/CSS/JS only in generated output

## File Structure
- `config/settings.json` — reading level, article count, timezone, global prefs
- `config/interests.json` — topic labels, source hints, selection guidance
- `data/flagged_characters.json` — per-character struggling/learned states with dates
- `data/preference_history.json` — editor's desk sessions (offered headlines + user picks)
- `docs/index.html` — current newsletter (GitHub Pages serves this)
- `docs/archive/` — past newsletters (YYYY-MM-DD.html)
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
5. User clicks "Export Feedback" — triggers a JSON file download
6. User runs cleanup in a CC session — CC reads the exported JSON and merges into data/ files, then commits and pushes

## Character States
- **struggling** — user flagged as difficult. Pipeline increases natural frequency in future articles.
- **learned** — user marked as mastered. Pipeline stops boosting; appears at natural frequency.
- **unmarked** (default) — never flagged. Natural frequency.

## Editor's Desk
Each newsletter includes 3 headlines that made the cut and 3 that didn't. User picks their top 3 from all 6. This data (what was offered + what was chosen) is stored in preference_history.json and included in future generation prompts to refine story selection. Claude pattern-matches on this history — no scoring algorithm needed.

## Current Scope (Sprint 1)
- Repo structure, config files, CLAUDE.md
- Reference HTML template (Zhongwen-compatible, character flagging, translation toggle, editor's desk, feedback export)
- Generation pipeline (web search → select → rewrite → HTML → commit/push)
- Cleanup pipeline (merge feedback → commit/push)
- End-to-end test: generate one newsletter, read it, give feedback, run cleanup

## Deferred
- Mobile-optimized layout
- Automated daily scheduling (cron/launchd — requires validating non-interactive CC invocation)
- Reading level auto-progression based on flagging rates
- Preference history trimming/summarization

## Conventions
- `USER:` prefix for inline annotations in plan/research docs
- Dates in YYYY-MM-DD format, Asia/Taipei timezone
- One newsletter per day, current issue always at docs/index.html
