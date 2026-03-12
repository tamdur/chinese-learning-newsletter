# Plan: Repository Initialization

## Overview

Set up the project skeleton for a daily Traditional Chinese reading newsletter. A Claude Code pipeline searches English-language news, selects 5 stories, rewrites them in Traditional Chinese at a calibrated reading level, and outputs an HTML file. The newsletter is served via **GitHub Pages** from a public repo, giving the user a stable bookmarkable URL and free mobile access.

Every file and directory listed below will be created in a single implementation pass after this plan is reviewed and approved.

---

## Directory Structure

```
newsletter/
├── config/
│   ├── settings.json
│   └── interests.json
├── data/
│   ├── flagged_characters.json
│   └── preference_history.json
├── docs/                        # GitHub Pages serves from here
│   ├── index.html               # always the latest newsletter
│   └── archive/                 # past issues (YYYY-MM-DD.html)
│       └── .gitkeep
├── templates/
│   └── newsletter.html          # reference example, not a runtime template
├── scripts/
│   ├── generate_prompt.md       # documents the generation pipeline + prompt
│   └── cleanup_prompt.md        # documents the cleanup steps + prompt
├── CLAUDE.md
├── plan.md                      # this file — kept as persistent documentation
├── .gitignore
└── README.md                    # minimal public-facing description
```

### Key structural decisions

**GitHub Pages via `docs/`.** GitHub Pages can serve from the `/docs` directory on the main branch. `docs/index.html` is always the current newsletter. After generation, the previous `index.html` gets moved to `docs/archive/YYYY-MM-DD.html` before the new one takes its place. Git history provides full version control — no separate archive-management logic needed beyond the rename.

**No shell scripts.** For MVP, the user runs the pipeline by typing commands in a CC session, not by executing shell scripts. `scripts/generate_prompt.md` and `scripts/cleanup_prompt.md` document the pipeline steps and the CC prompts to run them. Actual `.sh` automation belongs in a future sprint when non-interactive CC invocation is validated.

**`templates/newsletter.html` is a reference, not a runtime template.** Claude Opus generates the complete HTML file each run. The template serves as a spec — "make the output look like this" — included in the generation prompt as a reference. No string replacement, no template engine.

**Plan survives implementation.** This file is kept as persistent project documentation, not deleted.

---

## File-by-File Specification

### `config/settings.json`

Global generation parameters. Read by the pipeline at the start of every run.

```json
{
  "reading_level": {
    "grade": 5,
    "description": "Equivalent to a Taiwanese elementary school 5th-grader. Use common characters and straightforward grammar. Avoid literary idioms, classical constructions, and low-frequency characters unless they are essential to the topic. When a harder character is unavoidable, embed a brief natural-language gloss in parentheses on first use."
  },
  "article_count": 5,
  "language": "Traditional Chinese",
  "timezone": "Asia/Taipei",
  "newsletter_title": "今日讀報",
  "date_format": "YYYY-MM-DD",
  "github_pages_url": "https://<username>.github.io/newsletter/"
}
```

**Why `reading_level` is a description, not a character list:** Claude Opus responds better to natural language guidance than to rigid constraints. A description lets the user tune difficulty conversationally ("now aim for grade 6") without maintaining brittle character frequency tables.

---

### `config/interests.json`

Topic preferences and source hints. The pipeline uses this to steer story selection.

```json
{
  "topics": [
    {
      "id": "tech",
      "label": "Tech / AI / AGI",
      "source_hints": ["Hacker News", "Ars Technica"]
    },
    {
      "id": "econ_finance",
      "label": "Economics & Finance",
      "source_hints": ["Financial Times style coverage", "Marginal Revolution"]
    },
    {
      "id": "climate",
      "label": "Climate Science",
      "source_hints": ["Carbon Brief", "Nature Climate Change"]
    },
    {
      "id": "michigan_sports",
      "label": "Michigan Football & Basketball",
      "source_hints": ["MGoBlog", "The Athletic"]
    },
    {
      "id": "cubs",
      "label": "Cubs Baseball",
      "source_hints": ["ESPN", "The Athletic"]
    }
  ],
  "selection_note": "Pick 5 stories total. Aim for variety across topics but don't force every category into every issue. Lead with whatever is genuinely most interesting today. Include 1-2 stories outside these core topics that would appeal to a curious, well-read generalist — science, culture, history, unusual economics, etc. Think: the experience of flipping through a physical newspaper, not a hyper-targeted feed."
}
```

No topic weights — Claude reads the `selection_note` as natural language guidance, which is more effective than numeric weights for prompt-driven selection.

---

### `data/flagged_characters.json`

Tracks per-character state from user feedback. Starts empty. Populated when the user exports feedback from the newsletter page.

```json
{
  "version": 1,
  "characters": {}
}
```

After use, an entry looks like:

```json
{
  "version": 1,
  "characters": {
    "碳": {
      "state": "struggling",
      "first_flagged": "2026-03-12",
      "last_updated": "2026-03-12"
    },
    "氣": {
      "state": "learned",
      "first_flagged": "2026-03-10",
      "last_updated": "2026-03-14"
    }
  }
}
```

**State semantics:**
- `struggling` — user flagged this character as difficult. The pipeline should increase its natural frequency in future articles (use it more often, in varied contexts) to reinforce recognition.
- `learned` — user marked a previously-struggling character as known. The pipeline stops boosting it; it appears at whatever frequency is natural.

Characters never flagged are not in this file — they flow at natural frequency.

No `encounter_count` for MVP. The struggling/learned states are sufficient to drive frequency adjustment. Usage tracking can be added later if needed.

---

### `data/preference_history.json`

Stores Editor's Desk data: what was offered and what the user picked. This gives Claude both positive and negative signal for refining future story selection.

```json
{
  "version": 1,
  "sessions": []
}
```

After use, an entry looks like:

```json
{
  "version": 1,
  "sessions": [
    {
      "date": "2026-03-12",
      "offered": [
        {"headline": "台積電宣布新廠計畫", "topic_id": "tech", "included_in_issue": true},
        {"headline": "聯準會維持利率不變", "topic_id": "econ_finance", "included_in_issue": true},
        {"headline": "北極海冰面積創新低", "topic_id": "climate", "included_in_issue": true},
        {"headline": "密西根大學新教練首場比賽", "topic_id": "michigan_sports", "included_in_issue": false},
        {"headline": "新研究發現咖啡的意外好處", "topic_id": "serendipity", "included_in_issue": false},
        {"headline": "小乘太空旅行時代來臨", "topic_id": "tech", "included_in_issue": false}
      ],
      "user_top_3": [0, 5, 2]
    }
  ]
}
```

**Why both included and excluded headlines:** The Editor's Desk shows 3 stories that made the cut and 3 that didn't. The user picks their top 3 from all 6. This gives Claude richer signal — it learns not just what the user liked, but what they preferred over what, and whether excluded stories would have been better picks.

`user_top_3` is an array of indices into `offered`, so a pick of `[0, 5, 2]` means: "I wanted the TSMC story, the space tourism story, and the Arctic ice story."

---

### `templates/newsletter.html`

A reference HTML file showing the target layout and interaction patterns. Claude Opus generates the complete HTML each run using this as a spec, not as a literal template.

Requirements for the reference:
- **Zhongwen extension compatibility:** All Chinese text in standard DOM elements (`<p>`, `<span>`, `<h2>`, `<li>`, etc.) — no `<canvas>`, no `<svg>` text, no CSS `content:` for readable characters. The extension attaches mouseover handlers to text nodes; anything that breaks normal text node structure breaks hover lookup.
- **Clean reading layout:** Single-column, generous line-height (1.8+), large base font (18–20px). Light background, dark text.
- **Translation toggle:** Each article has a button to show/hide an English version. Both versions exist in the DOM; toggling swaps visibility.
- **Character flagging:** A mode toggle that lets the user click individual characters to cycle through states (unmarked → struggling → learned → unmarked). Visual indicators are subtle (e.g., light underline for struggling, none for learned/unmarked).
- **Editor's Desk section:** Shows 6 headlines (3 included, 3 not included). User selects their top 3 via click.
- **Export Feedback button:** Serializes all feedback (character flags + editor's desk picks) from localStorage to JSON and triggers a browser file download.
- **No external dependencies:** Vanilla HTML/CSS/JS only.

---

### `scripts/generate_prompt.md`

Documents the generation pipeline as a sequence of steps and the CC prompt to execute them:

1. Read `config/settings.json`, `config/interests.json`
2. Read `data/flagged_characters.json` for current character states
3. Read `data/preference_history.json` for taste signal
4. Search English-language news for candidate stories
5. Select 5 stories (mix of targeted interests and serendipitous discovery), plus 3 runner-up headlines for the Editor's Desk
6. Rewrite each story in Traditional Chinese at the configured reading level, conversational tone, naturally increasing frequency of struggling characters
7. Generate English translations for each article (for the toggle feature)
8. Generate the complete HTML file using `templates/newsletter.html` as reference
9. Move the current `docs/index.html` to `docs/archive/YYYY-MM-DD.html` (if it exists)
10. Write the new file to `docs/index.html`
11. `git add . && git commit -m "Newsletter YYYY-MM-DD" && git push`

---

### `scripts/cleanup_prompt.md`

Documents the post-reading cleanup as a sequence of steps and the CC prompt to execute them:

1. Read the exported feedback JSON (user will provide path or drag into CC session)
2. Merge character flags into `data/flagged_characters.json` — add new struggling characters, update state changes (struggling → learned), update `last_updated` dates
3. Merge Editor's Desk picks into `data/preference_history.json` — append the full session entry (offered headlines + user picks)
4. Commit and push data file changes
5. Print a summary of what changed (new struggling characters, newly learned characters, preference picks)

---

### `CLAUDE.md`

Project memory file. Claude Code reads this at the start of every session.

```markdown
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
```

---

### `.gitignore`

```
# Feedback exports (processed and discarded)
feedback_export*.json

# OS files
.DS_Store
Thumbs.db

# Editor files
*.swp
*.swo
*~
```

---

### `README.md`

Minimal public-facing description for the GitHub repo.

```markdown
# 今日讀報 — Daily Chinese Reading Newsletter

A personal tool that generates a daily Chinese reading newsletter from English-language news sources. Built with Claude Code, served via GitHub Pages.

Traditional Chinese (繁體中文) · Grade-calibrated reading level · Spaced character repetition
```

---

## Implementation Order

When approved, create files in this sequence:

1. Initialize git repo, create `.gitignore` and `README.md`
2. `CLAUDE.md` — so CC has context for everything that follows
3. `config/settings.json`
4. `config/interests.json`
5. `data/flagged_characters.json`
6. `data/preference_history.json`
7. `docs/archive/.gitkeep`
8. `templates/newsletter.html` — reference layout with all interaction patterns
9. `scripts/generate_prompt.md`
10. `scripts/cleanup_prompt.md`
11. `plan.md` — copy this file into the repo
12. Create GitHub repo (public), set remote, push
13. Enable GitHub Pages (serve from `docs/` on main branch)

---

## Open Questions (Resolved)

1. **Feedback export path:** User saves the exported JSON wherever the browser defaults (likely ~/Downloads/). During cleanup, user provides the path to CC or drags the file into the session. No need to configure a fixed path.
2. **Template approach:** Claude Opus generates complete HTML each run. `templates/newsletter.html` is a reference spec, not a runtime template.
3. **News search mechanism:** Claude's built-in web search for MVP.
4. **Git + hosting:** Public GitHub repo with GitHub Pages serving from `docs/`.