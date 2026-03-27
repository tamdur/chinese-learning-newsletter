# 今日讀報 Expansion Plan

**Created:** 2026-03-27
**Status:** ACTIVE — update this document as phases complete

This plan expands the newsletter into a multi-page site with four content types: Newsletter, Daily Wisdom, Obsessions, and Special Edition. Each phase is a logical stopping point where CC should pause, update this plan with outcomes and surprises, and await `/go` or explicit instructions before continuing.

**How to use this plan:** At the start of each phase, re-read this document. After completing a phase, add a `### Phase N Outcome` subsection noting what changed, any surprises, and any amendments to later phases. If a phase surfaces issues that affect future phases, update those phases inline with `USER:` or `CC:` prefixed annotations.

---

## Architecture Overview

### Site Structure (target state)

```
docs/
  index.html              ← Newsletter (latest issue)
  wisdom.html             ← Daily Wisdom (latest, idempotent per calendar day)
  obsessions.html         ← Obsessions culture desk (latest)
  archive/
    YYYY-MM-DD.html       ← Newsletter archives
    wisdom/
      YYYY-MM-DD.html     ← Wisdom archives
    obsessions/
      YYYY-MM-DD.html     ← Obsessions archives
```

### Command Structure (target state)

```
.claude/commands/
  go.md          ← Master: runs /newsletter + /wisdom + /obsessions sequentially
  newsletter.md  ← News pipeline (extracted + cleaned from current go.md)
  wisdom.md      ← Daily Wisdom pipeline
  obsessions.md  ← Obsessions culture desk pipeline
  se.md          ← Special Edition (on-demand, modifies current index.html)
```

### Shared Infrastructure (target state)

```
config/
  settings.json        ← Global: reading level, language, timezone, article length, pages URL
  interests.json       ← Newsletter-specific: editorial identity, topics, selection rules
  obsessions.json      ← Obsessions-specific: obsession definitions + editorial guidance
  wisdom.json          ← Wisdom-specific: source configs, Zen sutra selection

data/
  cedict_dictionary.json   ← Shared CEDICT dictionary (already exists, .gitignored)
  wisdom_progress.json     ← Mengzi + Zen passage tracking
  sources/
    heart_sutra.json       ← Cached: 7 segments, one per weekday
    mengzi_passages.json   ← Cached: all passages, sequential
    zen_passages.json      ← Cached: curated passages from approved text

templates/
  newsletter.html    ← Newsletter reference template (updated: no Editor's Desk, no feedback)
  wisdom.html        ← Wisdom reference template
  obsessions.html    ← Obsessions reference template
  _shared.css        ← Extracted shared CSS (dark theme, character styling, popup, nav)
  _shared.js         ← Extracted shared JS (translation toggle, mobile glossary popup)

scripts/
  assemble.py            ← Refactored: page-type-aware assembly
  validate.py            ← Refactored: page-type-aware validation
  glossary_lookup.py     ← Unchanged (already page-agnostic — reads from pipeline dir)
  build_dictionary.py    ← Unchanged
  build_wisdom_sources.py ← NEW: fetch + parse Heart Sutra, Mengzi, cache to data/sources/
```

### Shared Content Pipeline

The write→translate→glossary chain is used by Newsletter, Obsessions, and Special Edition. Daily Wisdom uses translate→glossary only (source text is pre-existing, not written by the article-writer).

The pipeline operates on **content units** — an array of objects, each with Chinese text needing translation and glossary. The number of units varies by page type:
- Newsletter: 5 units (articles)
- Wisdom: 3 units (Heart Sutra segment, Mengzi passage, Zen passage)
- Obsessions: N units (one per active obsession)
- Special Edition: 1 unit

Agents that need refactoring for content-unit flexibility:
- `article-writer.md` — currently hardcoded to "5 articles". Needs to accept variable count + content-type context.
- `translator.md` — already generic (takes any Chinese text). No changes needed.
- `glossary-chars.md` — already generic. No changes needed.
- `glossary-words.md` — already generic. No changes needed.
- `assembler.md` — needs page-type parameter.
- `story-selector.md` — newsletter-specific, stays as-is.

---

## Phase 1: Strip Feedback System + Editor's Desk

**Goal:** Remove dead weight before building new features. This touches the template, assembly script, validation script, go.md, and agents.

**Why first:** Every subsequent phase builds HTML from the template and runs through assembly/validation. Cleaning this up now means we don't propagate dead code into 3 new page types.

### Step 1.1: Update `templates/newsletter.html`

Remove these sections entirely:
- The `<section class="editors-desk">` block (lines ~317-350 in template)
- The `#flag-toggle` button from toolbar
- The `#export-btn` button and `#export-confirm` span from toolbar
- All localStorage-related JS: `STORAGE_KEY`, `charStates`, `deskPicks`, `loadState`, `saveState`, `getCharState`, `setCharState`, `updateCharVisuals`, `disableFeedbackFeatures`, the flagging mode toggle listener, the click-to-cycle listener, the Editor's Desk click listeners, the `exportFeedback` / `downloadJSON` functions
- CSS for: `.editors-desk`, `.desk-item`, `.desk-badge`, `.desk-headline`, `.desk-count`, `.desk-instructions`, `.c.struggling`, `.c.learned`, `.flagging-on .c`, `.confirm-msg`, `.storage-warning`

Keep intact:
- Translation toggle JS + CSS
- Mobile character lookup (popup glossary) JS + CSS — this is the core learning UX
- The `GLOSSARY` script block
- The `#lookup-toggle` button in toolbar (mobile glossary)
- All `.c` base styling, `.char-popup` styling
- The `<nav class="issue-nav">` block

Simplify the toolbar to just:
```html
<div class="toolbar" id="toolbar">
  <button id="lookup-toggle" class="lookup-toggle" type="button">查詢模式 OFF</button>
</div>
```

### Step 1.2: Update `scripts/assemble.py`

- Remove the `build_desk_item()` function
- Remove the `desk` checkpoint from `CHECKPOINT_FILES` — assembly no longer needs `desk_headlines.json`
- Remove the Editor's Desk section from `build_newsletter()` HTML output
- Remove the feedback/flagging toolbar buttons from HTML output
- Update the article count validation to be a warning, not a hard assumption of 5 (future-proofing for variable content units)
- The `build_newsletter()` function signature loses `desk_headlines` parameter

### Step 1.3: Update `scripts/validate.py`

- Remove `check_editors_desk()` entirely
- Remove the flagging-related checks from `check_essential_css()` (`.c.struggling`, `.c.learned` are gone)
- Keep all other checks: simplified chars, character wrapping, glossary, navigation, translation toggles, mobile popup

### Step 1.4: Update `.claude/commands/go.md`

- Remove entire Phase 1 (Cleanup): steps 1a-1e (feedback file scanning, character flag merging, preference history appending, feedback file deletion, cleanup commit)
- Remove Step 1's reference to `data/flagged_characters.json` and `data/preference_history.json` from the "Read config" step
- Remove Step 3's desk_headlines.json checkpoint and the "Update desk_headlines.json" substep after article writing
- Remove references to Editor's Desk throughout
- Simplify Phase 3 summary: no cleanup report, no runner-up headlines

### Step 1.5: Update `.claude/agents/story-selector.md`

- Remove runner-up selection: the selector now picks 5 stories only, no "3 runner-up headlines"
- Remove references to `data/preference_history.json`
- Remove output field `runners_up` — output is just `{selected: [...], rationale: "..."}`
- Total output: 5 selected stories, not 8

### Step 1.6: Update `.claude/agents/article-writer.md`

- Remove step 4 ("Incorporate struggling characters") — no more `flagged_characters.json`
- Remove instruction to read `data/flagged_characters.json`

### Step 1.7: Clean up data files

- Delete `data/flagged_characters.json` (or empty it to `{"version": 1, "characters": {}}` if you want to preserve the schema for potential future use)
- Delete `data/preference_history.json`

### Step 1.8: Test

Run `/go` (the existing command, now updated) end-to-end. Verify:
- Newsletter generates successfully without Editor's Desk or feedback features
- `docs/index.html` has no desk section, no flagging buttons, no export button
- Translation toggle and mobile glossary popup still work
- Validation passes
- Git commit and push succeed

### Phase 1 Outcome

**Completed:** 2026-03-27

**Changes made (Steps 1.1-1.7):**

- `templates/newsletter.html` — Removed Editor's Desk HTML, feedback/flagging CSS (`.editors-desk`, `.desk-item`, `.c.struggling`, `.c.learned`, `.flagging-on`, `.confirm-msg`, `.storage-warning`), stripped toolbar to just `#lookup-toggle`, removed all localStorage/feedback/flagging/export JS. Translation toggle and mobile glossary popup preserved.
- `scripts/assemble.py` — Removed `desk` checkpoint, `build_desk_item()`, `desk_headlines` param from `build_newsletter()`, Editor's Desk HTML output, feedback toolbar. Simplified `extract_main_js()`. Article count validation now warns instead of assuming 5.
- `scripts/validate.py` — Removed `check_editors_desk()` and its call. `check_article_count()` now flexible (error at 0, warn at <5).
- `.claude/commands/go.md` — Removed Phase 1 (Cleanup) entirely. Removed feedback/desk data file reads and desk checkpoint.
- `.claude/agents/story-selector.md` — Now selects 5 stories only (no runner-ups). Removed `preference_history.json` and `runners_up` output.
- `.claude/agents/article-writer.md` — Removed struggling characters step and `flagged_characters.json` read.
- Deleted `data/flagged_characters.json` and `data/preference_history.json`.
- `CLAUDE.md` — Removed Feedback System, Character States, Editor's Desk sections. Updated File Structure and scope.

**Surprises:** None. Clean removal with no unexpected dependencies.
**Step 1.8 (e2e test):** Deferred to user's next `/go` run.

---

## Phase 2: Extract Shared Infrastructure

**Goal:** Factor out CSS, JS, and assembly logic that will be reused across all page types. This is the foundation for Phases 3-6.

### Step 2.1: Create `templates/_shared.css`

Extract from the cleaned-up `templates/newsletter.html`:
- Reset (`* { margin: 0; ... }`)
- `body` styling (font family, size, line-height, colors, max-width, padding)
- `.c` base styling (cursor, hover states)
- `hr` styling
- `.translation-toggle` and `.article-body-en` styling
- `.char-popup` and all popup sub-element styling
- `.toolbar` and toolbar button styling
- `.lookup-toggle` visibility rules
- `@media (pointer: coarse)` touch styles
- `footer` styling
- Navigation (`.issue-nav`, `.nav-link`)

Leave in the newsletter-specific template:
- `.newsletter-header` (each page type has its own header styling, though they may be identical)
- `.article` margins (if they differ across page types — likely they won't)

The shared CSS file is a reference artifact, not a runtime import. `assemble.py` reads it and injects it into each page's `<style>` block.

### Step 2.2: Create `templates/_shared.js`

Extract from `templates/newsletter.html` the JS that all pages need:
- Translation toggle logic (`.translation-toggle` click listeners)
- Mobile glossary popup logic (the entire `if (isMobile)` block: long-press, `findLongestMatch`, `positionPopup`, `showPopup`, popup close handler, lookup toggle)
- The `GLOSSARY` variable reference (each page provides its own glossary data; the JS just reads from `GLOSSARY`)

This is also a reference artifact. `assemble.py` reads it and injects it.

### Step 2.3: Create site-wide navigation component

Add a function to `assemble.py` — `build_site_nav(current_page, pages_available)` — that generates a nav bar appearing at the top of every page:

```html
<nav class="site-nav">
  <a href="index.html" class="site-nav-link active">今日讀報</a>
  <a href="wisdom.html" class="site-nav-link">每日智慧</a>
  <a href="obsessions.html" class="site-nav-link">深度專題</a>
</nav>
```

- `current_page` gets the `active` class
- Links to pages that don't exist yet are omitted (check `docs/` for file existence)
- Add corresponding CSS to `_shared.css`

The existing issue-level prev/next nav (`.issue-nav`) remains below the site nav, specific to each page type's archive chain.

### Step 2.4: Refactor `assemble.py` into page-type-aware architecture

The current `assemble.py` has one function: `build_newsletter()`. Refactor to:

```python
# Core shared functions (keep existing)
load_json(), extract_css(), extract_main_js()  # now reads from _shared files
archive_old_issue()  # parameterized: archive_dir, index_path
list_archive_files()  # parameterized: archive_dir
build_nav()  # existing issue nav, parameterized
build_site_nav()  # new cross-page nav

# Article/content-unit builder (shared across all page types)
build_content_unit_html(unit, translation, unit_id)  # renamed from build_article_html

# Page-type builders
build_newsletter_page(date, units, translations, glossary, ...)
build_wisdom_page(date, units, translations, glossary, ...)
build_obsessions_page(date, units, translations, glossary, ...)

# CLI interface
--page-type newsletter|wisdom|obsessions  (default: newsletter)
--date YYYY-MM-DD
```

Each page-type builder:
1. Reads shared CSS + any page-specific CSS from its template
2. Reads shared JS + any page-specific JS from its template
3. Calls `build_content_unit_html()` for each content unit
4. Wraps in page-specific layout (header, sections, footer)
5. Injects the glossary
6. Handles archiving for its page type

Key changes to support this:
- `CHECKPOINT_FILES` becomes a parameter, not a module-level constant
- Pipeline directories can be namespaced: `data/pipeline/newsletter/`, `data/pipeline/wisdom/`, etc. (or kept flat if only one pipeline runs at a time — simpler; `/go` runs them sequentially)
- Archive directories are per-page-type: `docs/archive/` (newsletter), `docs/archive/wisdom/`, `docs/archive/obsessions/`

**Decision: flat pipeline directory.** Since `/go` runs pipelines sequentially and each pipeline cleans up its checkpoints after success, a flat `data/pipeline/` directory is fine. Each pipeline writes to it, assembles, cleans up, then the next pipeline starts. This avoids namespace complexity.

### Step 2.5: Refactor `validate.py` for page-type awareness

Add `--page-type` argument. Core checks shared across all types:
- Simplified characters
- Character wrapping
- Glossary populated
- Navigation integrity
- Translation toggles
- Mobile glossary popup
- Essential CSS

Newsletter-specific checks:
- Article count (currently hardcoded to 5; make configurable or just "at least 1")

Wisdom-specific checks:
- Exactly 3 content sections (Heart Sutra, Mengzi, Zen)
- Content matches expected day-of-week for Heart Sutra

Obsessions-specific checks:
- At least 1 content section
- Each obsession has a source attribution

### Step 2.6: Update `templates/newsletter.html`

Slim it down to newsletter-specific structure only. The shared CSS/JS lives in `_shared` files. The template becomes:
- Newsletter-specific header (`今日讀報`)
- Article layout (already generic)
- No Editor's Desk (removed in Phase 1)
- References `_shared.css` and `_shared.js` via comments for documentation, but `assemble.py` handles injection

### Step 2.7: Test

Run the refactored pipeline via the existing `/go` command (which still only produces the newsletter). Verify:
- Newsletter output is identical to pre-refactoring (diff the HTML structure, ignoring content)
- Site nav appears at top (with only Newsletter link active, since other pages don't exist yet)
- Assembly and validation pass
- Archive chain still works correctly

### Phase 2 Outcome
*(CC fills this in after completing Phase 2)*

---

## Phase 3: Extract `/newsletter` Command

**Goal:** Move the newsletter pipeline from `go.md` into its own `newsletter.md` command. Transform `go.md` into a thin orchestrator that calls sub-commands.

### Step 3.1: Create `.claude/commands/newsletter.md`

Move the entire Phase 2 (Generation) content from the current `go.md` into `newsletter.md`. This is the full pipeline: scout dispatch → story selection → research → article writing → translation → glossary → assembly → validation → commit/push.

Adjustments:
- Remove the Phase 1 (Cleanup) content — that's gone (Phase 1 of this plan removed it)
- Remove the Step 0 resume logic preamble about cleanup
- The command is self-contained: reads config, dispatches scouts, selects, writes, translates, glossaries, assembles, validates, commits
- Assembly call becomes: `python3 scripts/assemble.py --page-type newsletter --date {today}`
- Validation call becomes: `python3 scripts/validate.py --page-type newsletter`

### Step 3.2: Rewrite `.claude/commands/go.md`

The new `go.md` is a thin orchestrator:

```markdown
# /go — Daily Pipeline

You are running the daily content pipeline. This generates all pages for today.

## Steps

### 1. Newsletter
Run the /newsletter command pipeline. (Inline the full newsletter.md instructions here,
or dispatch a subagent with the newsletter.md prompt.)

### 2. Daily Wisdom
Run the /wisdom command pipeline. (Placeholder — Phase 4)

### 3. Obsessions
Run the /obsessions command pipeline. (Placeholder — Phase 5)

### 4. Summary
Print a consolidated summary with links to all generated pages.
```

**Implementation note:** CC commands can't invoke other CC commands directly. So `go.md` will inline or reference the instructions from each sub-command. The cleanest approach: `go.md` references the sub-command files and says "Follow the instructions in `.claude/commands/newsletter.md`, then `.claude/commands/wisdom.md`, then `.claude/commands/obsessions.md`." CC can read those files and execute them in sequence.

### Step 3.3: Test

- Run `/newsletter` standalone — verify it produces the newsletter as before
- Run `/go` — verify it runs the newsletter pipeline (wisdom/obsessions are placeholders)

### Phase 3 Outcome
*(CC fills this in after completing Phase 3)*

---

## Phase 4: Daily Wisdom Page

**Goal:** Build the Daily Wisdom page with Heart Sutra, Mengzi, and Zen Buddhism content.

### Step 4.1: Fetch and cache source texts

Create `scripts/build_wisdom_sources.py`:

**Heart Sutra:**
- Fetch https://pages.ucsd.edu/~dkjordan/chin/chtxts/ShinJing.html
- Parse the Traditional Chinese text of the Heart Sutra
- Segment into 7 roughly-equal parts (by natural sentence/phrase boundaries, not mechanical character count)
- Assign each to a weekday: Monday=0, Tuesday=1, ..., Sunday=6
- Write to `data/sources/heart_sutra.json`:
  ```json
  {
    "source_url": "https://pages.ucsd.edu/~dkjordan/chin/chtxts/ShinJing.html",
    "segments": [
      {"day_index": 0, "day_name": "Monday", "text": "觀自在菩薩..."},
      ...
    ]
  }
  ```

**Mengzi:**
- Fetch the table of contents from https://ctext.org/mengzi/liang-hui-wang-i (and subsequent chapters)
- Parse passages preserving the original chapter/passage structure from ctext.org
- Group short adjacent passages to approximate target length (~150 chars, matching `settings.json`)
- Write to `data/sources/mengzi_passages.json`:
  ```json
  {
    "source_url": "https://ctext.org/mengzi",
    "total_passages": 286,
    "passages": [
      {"index": 0, "chapter": "梁惠王上", "passage_id": "liang-hui-wang-i/1", "text": "孟子見梁惠王..."},
      ...
    ]
  }
  ```

**Zen — interactive curation step:**
- This is a one-time setup. CC searches for well-regarded Zen sutras/texts available online with Traditional Chinese text.
- CC presents candidates to the user (title, source, sample text, length estimate)
- User approves/rejects
- For approved text(s), CC fetches, parses, segments into ~150-char passages
- Write to `data/sources/zen_passages.json` (same structure as Mengzi)

Run `build_wisdom_sources.py` once. Commit the output JSON files to the repo. The daily pipeline reads from these cached files, never fetches live.

### Step 4.2: Create `data/wisdom_progress.json`

```json
{
  "mengzi": {
    "next_passage_index": 0,
    "last_served_date": null
  },
  "zen": {
    "next_passage_index": 0,
    "last_served_date": null
  }
}
```

Heart Sutra doesn't need progress tracking — it's determined by day-of-week.

### Step 4.3: Create `config/wisdom.json`

```json
{
  "heart_sutra": {
    "enabled": true,
    "source_file": "data/sources/heart_sutra.json",
    "section_title": "般若波羅蜜多心經",
    "section_title_en": "Heart Sutra"
  },
  "mengzi": {
    "enabled": true,
    "source_file": "data/sources/mengzi_passages.json",
    "section_title": "孟子",
    "section_title_en": "Mencius"
  },
  "zen": {
    "enabled": true,
    "source_file": "data/sources/zen_passages.json",
    "section_title": "禪宗經典",
    "section_title_en": "Zen Buddhism"
  }
}
```

### Step 4.4: Create `templates/wisdom.html`

Structure:
```html
<header class="page-header">
  <h1>每日智慧</h1>
  <p class="subtitle">Daily Wisdom</p>
  <p class="date">YYYY-MM-DD</p>
</header>

<!-- Site nav (generated by assemble.py) -->
<!-- Issue nav prev/next (generated by assemble.py) -->

<main>
  <section class="wisdom-section" data-section="heart-sutra">
    <h2 class="section-title">般若波羅蜜多心經 <span class="section-subtitle">Heart Sutra — Monday</span></h2>
    <div class="section-body-zh">
      <!-- Chinese text with <span class="c"> wrapping -->
    </div>
    <button class="translation-toggle">顯示翻譯 Show Translation</button>
    <div class="section-body-en" hidden>
      <!-- English translation -->
    </div>
  </section>

  <hr>

  <section class="wisdom-section" data-section="mengzi">
    <h2 class="section-title">孟子 <span class="section-subtitle">Mencius — 梁惠王上 §1</span></h2>
    <!-- same structure -->
  </section>

  <hr>

  <section class="wisdom-section" data-section="zen">
    <h2 class="section-title">禪宗經典 <span class="section-subtitle">Zen Buddhism</span></h2>
    <!-- same structure -->
  </section>
</main>

<!-- Toolbar with lookup toggle -->
<!-- Glossary popup -->
<!-- Shared JS -->
```

Uses the same dark theme, same character styling, same popup glossary, same translation toggle as the newsletter.

### Step 4.5: Create the wisdom content pipeline

The Wisdom pipeline is simpler than the newsletter — no web search, no story selection, no article writing. The source text is pre-cached.

Pipeline steps:
1. **Read config:** `config/settings.json`, `config/wisdom.json`, `data/wisdom_progress.json`
2. **Check idempotency:** If `wisdom_progress.json` shows `last_served_date` matches today for both Mengzi and Zen, AND `docs/wisdom.html` exists, skip generation entirely. Print "Wisdom page already generated for today."
3. **Select today's content:**
   - Heart Sutra: day-of-week index (Python: `datetime.today().weekday()`, Monday=0)
   - Mengzi: `next_passage_index` from progress file
   - Zen: `next_passage_index` from progress file
4. **Wrap Chinese text in `<span class="c">` tags:** The source texts are raw Traditional Chinese. Each character needs wrapping. This can be done deterministically in Python (a simple function that wraps each CJK character).
5. **Translate:** Dispatch 3 translator agents in parallel (one per content unit). These are classical/literary texts, so the translator prompt needs a tweak: "Translate this classical Chinese text to clear, modern English. Maintain the original's meaning faithfully. This is from [Heart Sutra / Mencius / Zen text]."
   - **Important:** For Heart Sutra and Mengzi, high-quality existing translations are available. Consider whether to use a canonical English translation (fetched and cached alongside the Chinese) rather than generating one. This avoids translation drift on well-known texts. If canonical translations are cached, skip the translator agents for those units and only translate the Zen passage.
   - CC: Check during Phase 4.1 whether the source pages include English translations. If yes, cache them alongside the Chinese and skip agent translation for those texts.

   USER: Yes, we want to save high-quality translations that already exist, for example from https://ctext.org/mengzi or https://pages.ucsd.edu/~dkjordan/chin/chtxts/ShinJing.html. Let's use those instead of retranslating every time, although we should keep the optionality to translate for sutras or texts for which good translations are not available.
6. **Build glossary:** Run `glossary_lookup.py` (it reads from `data/pipeline/articles.json` — rename the checkpoint to be generic, or have the wisdom pipeline write its content units to the same filename). Then dispatch glossary-chars and glossary-words agents as usual.
7. **Assemble:** `python3 scripts/assemble.py --page-type wisdom --date {today}`
8. **Validate:** `python3 scripts/validate.py --page-type wisdom`
9. **Update progress:** Increment `next_passage_index` for Mengzi and Zen. Set `last_served_date` to today.
10. **Commit and push.**

### Step 4.6: Create `.claude/commands/wisdom.md`

Document the full pipeline from Step 4.5. Include the idempotency check at the top.

### Step 4.7: Create a wisdom-specific translator agent variant

Create `.claude/agents/translator-classical.md`:
```markdown
---
model: haiku
tools: []
---
# Translator — Classical Chinese to English

Translate a classical Chinese text passage to clear, modern English.

## Instructions
- Faithful to the original meaning
- Clear and accessible to a modern reader
- Maintain paragraph/verse structure
- Output HTML <p> tags only
- This is NOT a news article — it is classical literature. Translate accordingly.

## Text to Translate
{{text}}

## Context
{{context}}  (e.g., "This is a passage from the Heart Sutra" or "This is from Mencius, Chapter: 梁惠王上")
```

If canonical translations are available from the source pages, this agent is only needed for the Zen passage.

### Step 4.8: Update `go.md` orchestrator

Replace the Phase 4 placeholder with the actual wisdom pipeline instructions (reference `.claude/commands/wisdom.md`).

### Step 4.9: Test

- Run `/wisdom` standalone. Verify:
  - Page generates with 3 sections
  - Heart Sutra section matches today's day-of-week
  - Mengzi starts at passage 0
  - Translation toggle works
  - Mobile glossary popup works
  - Site nav shows Newsletter + Daily Wisdom links
- Run `/wisdom` again on the same day. Verify it skips generation (idempotency).
- Run `/go`. Verify newsletter + wisdom both generate.

### Phase 4 Outcome
*(CC fills this in after completing Phase 4)*

---

## Phase 5: Obsessions Page

**Goal:** Build the culture desk page with configurable obsessions, web-searched content, and the shared content pipeline.

### Step 5.1: Create `config/obsessions.json`

```json
{
  "editorial_voice": "A thoughtful museum curator sharing real knowledge succinctly and clearly with the public. Not academic, not dumbed-down — the voice of someone who has spent years with this material and can make it vivid in a few sentences. Like a great wall text at a world-class museum.",
  "obsessions": [
    {
      "id": "taiwan-electronic-music-70s",
      "label": "Taiwanese Electronic Music Pioneers",
      "guidance": "Discovering highly-regarded electronic music artists from Taiwan working in the 1970s. Focus on specific artists, albums, techniques, and cultural context.",
      "active": true
    }
  ]
}
```

The user adds/removes/edits obsessions by editing this file directly. Each obsession has a short `guidance` field (1-2 sentences) that drives the scout's web search.

### Step 5.2: Create obsessions-specific agents

**`.claude/agents/obsessions-scout.md`** (Sonnet):
- Receives one obsession's `label` + `guidance`
- Runs 2-3 targeted web searches to find a specific, interesting story/fact/discovery related to the obsession
- Returns a candidate story with title, URL, source, and 2-3 sentence summary
- The scout should find something NEW and SPECIFIC each time — not a generic overview. Think: a specific album, a specific artist's technique, a specific historical event. The kind of thing you'd learn at a museum, not from a Wikipedia intro paragraph.

**`.claude/agents/obsessions-writer.md`** (Opus):
- Similar to `article-writer.md` but with the museum curator voice
- Reads `config/settings.json` for reading level, `config/obsessions.json` for editorial voice
- Writes one content unit per obsession
- Same `<span class="c">` wrapping requirement
- Output: JSON array of content units (same schema as article-writer)

### Step 5.3: Create `templates/obsessions.html`

Structure mirrors the newsletter but with obsession-specific headers:

```html
<header class="page-header">
  <h1>深度專題</h1>
  <p class="subtitle">Obsessions</p>
  <p class="date">YYYY-MM-DD</p>
</header>

<!-- Site nav -->
<!-- Issue nav -->

<main>
  <!-- One section per obsession -->
  <section class="obsession-section" data-obsession-id="taiwan-electronic-music-70s">
    <h2 class="section-title">Taiwanese Electronic Music Pioneers</h2>
    <div class="section-body-zh">...</div>
    <button class="translation-toggle">顯示翻譯 Show Translation</button>
    <div class="section-body-en" hidden>...</div>
  </section>
</main>

<!-- Toolbar, glossary popup, shared JS -->
```

### Step 5.4: Build the obsessions pipeline

Pipeline steps:
1. **Read config:** `config/settings.json`, `config/obsessions.json`
2. **Filter active obsessions:** Only process obsessions where `"active": true`
3. **Dispatch scouts in parallel:** One `obsessions-scout` agent per active obsession. Each scout searches for a fresh, specific story.
4. **Check for recent obsessions archives:** Read last 3-5 obsessions issues from `docs/archive/obsessions/` to avoid repeating the same story. Pass recent headlines to the scout or writer.
5. **Dispatch obsessions-writer:** Pass all scouted stories + editorial voice. Writer produces one content unit per obsession.
6. **Translate:** Dispatch translator agents (one per content unit, parallel).
7. **Build glossary:** Standard glossary pipeline.
8. **Assemble:** `python3 scripts/assemble.py --page-type obsessions --date {today}`
9. **Validate:** `python3 scripts/validate.py --page-type obsessions`
10. **Commit and push.**

### Step 5.5: Create `.claude/commands/obsessions.md`

Document the full pipeline.

### Step 5.6: Update `go.md` orchestrator

Replace the Phase 5 placeholder with the actual obsessions pipeline.

### Step 5.7: Test

- Add one obsession to `config/obsessions.json`
- Run `/obsessions` standalone. Verify page generates with museum curator voice.
- Add a second obsession. Run again. Verify both appear.
- Run `/go`. Verify all three pages generate (newsletter + wisdom + obsessions).
- Check site nav: all three page links should be active.

### Phase 5 Outcome
*(CC fills this in after completing Phase 5)*

---

## Phase 6: Special Edition Command

**Goal:** Build the `/se` command for on-demand topic deep-dives that insert into the current newsletter page.

### Step 6.1: Define `/se` command syntax

```
/se <topic description> [character count]
```

Examples:
- `/se latest change to oil prices 400`
- `/se Taiwan earthquake aftermath`
- `/se Fed rate decision market reaction 300`

If character count is omitted, default to the `article_length.target_characters` from `settings.json`.

### Step 6.2: Create `.claude/commands/se.md`

Pipeline steps:
1. **Parse arguments:** Extract topic and optional character count from the command input.
2. **Research:** Dispatch a `story-researcher` agent (Sonnet) with a web search for the latest on the topic. The researcher should find the most recent developments (past 24 hours if possible).
3. **Write:** Dispatch `article-writer` agent (Opus) with the research briefing. One content unit. Character count target from argument or default.
4. **Translate:** Dispatch one translator agent.
5. **Build glossary:** Run glossary pipeline for the one content unit.
6. **Insert into `docs/index.html`:**
   - Read current `docs/index.html`
   - Look for `<div id="special-editions">`. If it doesn't exist, create it after `</main>` and before the toolbar.
   - Append the new SE content unit inside `<div id="special-editions">`:
     ```html
     <div id="special-editions">
       <h2 class="se-header">特別報導 Special Edition</h2>
       <!-- SE articles appended here -->
       <article class="article se-article" data-se-id="1">
         ...
       </article>
     </div>
     ```
   - If the div already exists (second/third SE of the day), append below existing SE articles. Increment `data-se-id`.
   - Merge the new glossary entries into the page's existing `GLOSSARY` object.
7. **Validate:** Run `python3 scripts/validate.py --page-type newsletter` (SE articles should pass the same checks).
8. **Commit and push.**

### Step 6.3: Handle SE persistence across regeneration

When `/newsletter` or `/go` regenerates `docs/index.html`, SEs from the same calendar day are wiped (the page is rebuilt from scratch). This is the intended behavior — SEs are ephemeral same-day additions.

No special code needed: regeneration already replaces `index.html` entirely. The SE container simply doesn't exist in the newly assembled page.

If the user wants to preserve an SE across regeneration, they can manually not regenerate that day, or we can add a `--preserve-se` flag later (deferred).

### Step 6.4: Add SE-specific CSS to `_shared.css`

```css
.se-header {
  font-size: 22px;
  color: #d4a574;  /* warm accent */
  margin-top: 2.5rem;
  margin-bottom: 1.5rem;
  padding-top: 1.5rem;
  border-top: 2px solid #d4a574;
}
.se-article {
  /* inherits from .article */
}
```

### Step 6.5: Test

- Generate a newsletter via `/newsletter`
- Run `/se latest change to oil prices 400`
- Verify SE section appears below main articles
- Run `/se Taiwan earthquake aftermath` (second SE)
- Verify both SE articles appear, in order
- Run `/newsletter` again — verify SEs are gone (fresh page)

### Phase 6 Outcome
*(CC fills this in after completing Phase 6)*

---

## Phase 7: Integration Test + CLAUDE.md Update

**Goal:** Full end-to-end validation and documentation update.

### Step 7.1: Full `/go` pipeline test

Run `/go` and verify:
1. Newsletter generates (5 articles, site nav, no Editor's Desk, no feedback)
2. Daily Wisdom generates (3 sections, correct day-of-week for Heart Sutra, Mengzi passage 0)
3. Obsessions generates (one story per active obsession)
4. All three pages have working: translation toggle, mobile glossary popup, site nav cross-links
5. Archive chain works for each page type
6. Git commit includes all three pages

### Step 7.2: Run `/se` after `/go`

Verify SE inserts correctly into the just-generated newsletter.

### Step 7.3: Re-run `/go`

Verify:
- Newsletter regenerates (SE is gone)
- Wisdom skips (idempotent — already generated today)
- Obsessions regenerates with fresh content
- Mengzi progress did NOT increment (wisdom was skipped)

### Step 7.4: Update `CLAUDE.md`

Rewrite to reflect the new multi-page architecture:
- Updated file structure
- New commands (`/newsletter`, `/wisdom`, `/obsessions`, `/se`, `/go`)
- Removed: feedback system, Editor's Desk, flagged characters, preference history
- New pages: Daily Wisdom, Obsessions
- Obsessions config format
- Wisdom source management
- SE behavior (ephemeral, same-day only)

### Step 7.5: Update `README.md`

Brief update for the public repo.

### Phase 7 Outcome
*(CC fills this in after completing Phase 7)*

---

## Reference: Glossary Pipeline Refactoring Detail

The glossary pipeline (`glossary_lookup.py` + glossary-chars + glossary-words agents) currently reads from `data/pipeline/articles.json`. For multi-page support, the pipeline needs to work with any content units, not just newsletter articles.

**Minimal change approach:** Each page's pipeline writes its content units to `data/pipeline/articles.json` using the same schema (array of objects with `headline_html`, `body_html`). The glossary scripts don't care what the content is — they just extract CJK characters and look them up. After the glossary is built and assembly is complete, the checkpoint files are cleaned up before the next page's pipeline runs.

This means `glossary_lookup.py` needs zero changes. The content-unit abstraction is handled at the command level (each command writes its units to the expected checkpoint filename), not at the script level.

For Wisdom, the content units would be:
```json
[
  {"headline_html": "<span class=\"c\">般</span>...", "body_html": "...", "headline_plain": "般若波羅蜜多心經", "source_label": "Heart Sutra"},
  {"headline_html": "...", "body_html": "...", "headline_plain": "孟子 — 梁惠王上 §1", "source_label": "Mencius"},
  {"headline_html": "...", "body_html": "...", "headline_plain": "禪宗經典", "source_label": "Zen Buddhism"}
]
```

Same schema, different content. The pipeline doesn't know or care.

---

## Deferred / Future Considerations

- **Mobile-optimized layout** for all pages
- **Wisdom auto-progression:** If the user skips a day, should Mengzi advance anyway? Current design: no — it only advances when the page is generated. This means skipping days doesn't lose passages.
- **Obsessions archive search:** Preventing repeat stories across obsessions issues. Phase 5 includes basic "check recent archives" but a more robust dedup system could be added later.
- **SE preservation flag:** `--preserve-se` to carry special edition content across regeneration.
- **Reading level auto-progression:** Deferred from Sprint 1, still deferred.
- **Scheduled daily generation:** cron/launchd automation (deferred from Sprint 1).
