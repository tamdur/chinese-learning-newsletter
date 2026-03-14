# Research: Previous/Next Navigation

## Archive File Convention

Files in `docs/archive/` follow the pattern `YYYY-MM-DD.html`. Current contents:
- `2026-03-12.html`
- `2026-03-12-test.html` (anomaly — test artifact)
- `2026-03-13.html`

The assembler should only consider files matching the strict `YYYY-MM-DD.html` pattern (4-4-2 digits, nothing else before `.html`) to avoid picking up test files.

## Current Assembler Archive Flow (from `.claude/agents/assembler.md`)

1. Read `templates/newsletter.html` for structure/CSS/JS reference
2. Build complete HTML with all 5 articles, translations, Editor's Desk, glossary
3. If `docs/index.html` exists: read it, extract date from `<p class="date">`, move to `docs/archive/{date}.html`
4. Write new HTML to `docs/index.html`
5. `git add docs/index.html docs/archive/` → commit → push
6. Validation scan (simplified chars, unwrapped chars)

Key detail: the assembler reads the old `index.html` to get its date, then writes it to archive. It does NOT currently modify the archived file after writing it. This is where the "next" link patching needs to happen.

## Current HTML Structure (header area)

From `templates/newsletter.html` lines 187-190:
```html
<header class="newsletter-header">
  <h1>今日讀報</h1>
  <p class="date">2026-03-12</p>
</header>

<main>
```

The navigation bar should sit between `</header>` and `<main>`. This is a natural visual position and keeps the nav separate from both the header branding and the article content.

## Navigation Bar HTML Design

Requirements: minimal, not a major visual element, plain text (not character-wrapped), consistent with existing design.

```html
<nav class="issue-nav" data-prev="archive/2026-03-13.html" data-next="">
  <a href="archive/2026-03-13.html" class="nav-link nav-prev">← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>
```

Design choices:
- **`data-prev` / `data-next` attributes on `<nav>`**: These serve as the source of truth for the assembler when patching. The assembler can find `data-next=""` and replace it with the actual URL. This is much more reliable than trying to parse/replace href values inside anchor tags.
- **`hidden` attribute on next link**: When no next issue exists (i.e., this is the current issue), the link is hidden. The assembler patches by removing `hidden` and setting the href + data-next value.
- **Flexbox layout**: `nav-prev` on the left, `nav-next` on the right, spacer in between.
- **Plain text labels**: "← 上一期" and "下一期 →" are NOT wrapped in `<span class="c">` — these are UI elements, not reading content.

## How the Assembler Determines Links

At generation time, the assembler needs to:

1. **Scan `docs/archive/`** for files matching `/^\d{4}-\d{2}-\d{2}\.html$/`
2. **Sort by date descending** — the most recent archive file is the "previous" issue
3. **For the new `index.html`**: set `data-prev` and `href` on `.nav-prev` to `archive/{most-recent-date}.html`. Leave `.nav-next` hidden with empty href.
4. **If no archive files exist** (first run): hide both links or omit the nav entirely.

## How the Assembler Patches the Previous Issue

After archiving the old `index.html` to `docs/archive/{date}.html`:

1. Read the newly archived file
2. Find the `<nav class="issue-nav"` element
3. Replace `data-next=""` with `data-next="../index.html"`
4. Replace `<a href="" class="nav-link nav-next" hidden>` with `<a href="../index.html" class="nav-link nav-next">`
5. Write the patched file back

The patching uses simple string replacement — no DOM parsing needed. The patterns are unique and deterministic:
- `data-next=""` → `data-next="../index.html"` (on the nav element)
- `href="" class="nav-link nav-next" hidden` → `href="../index.html" class="nav-link nav-next"`

## Archive-to-Archive Navigation

When an archived issue eventually gets a "next" that is also archived (not index.html), this happens automatically: the "next" link points to `../index.html` at creation time, and when THAT issue gets archived, its "prev" still points correctly. But the "next" link on the older issue keeps pointing to `../index.html`, which is always the latest.

**Strict sequential navigation** (user decision): Each archive file's "next" link points to the next archive file in sequence, NOT to `../index.html`. Only the most recent archive file's "next" points to `../index.html`.

This means the assembler must patch **two** files when archiving:

1. **The newly archived file** (old index.html → `docs/archive/{today-date}.html`): Set its "next" to `../index.html` (it's now the most recent archive).
2. **The previous most-recent archive file**: Change its "next" from `../index.html` to the newly archived file's filename (e.g., `2026-03-14.html` — same directory, no `../` needed since both are in `archive/`).

Example: Before today's run, `2026-03-13.html` has `data-next="../index.html"`. After archiving today's index.html to `2026-03-14.html`:
- `2026-03-13.html` gets patched: `data-next="../index.html"` → `data-next="2026-03-14.html"`, and `href="../index.html"` on `.nav-next` → `href="2026-03-14.html"`
- `2026-03-14.html` (newly archived): already has `data-next=""` from when it was index.html. Patch it to `data-next="../index.html"` and unhide the next link.

## CSS for Navigation Bar

Minimal styling consistent with the existing design:

```css
.issue-nav {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  font-size: 14px;
}
.nav-link {
  color: #888;
  text-decoration: none;
}
.nav-link:hover {
  color: #666;
}
```

This uses the same muted color (#888) as the date element, keeping it unobtrusive. No borders, no background — just simple text links.

## 10-Issue Window

The user spec says "Navigation only covers the last 10 issues." Two approaches:
1. **At generation time**: When the assembler scans archive files and finds more than 10, strip the nav bar from the 11th-oldest file.
2. **Leave them**: Old archive files keep their nav links, which still work. The "10 issues" limit just means the assembler doesn't go back and add nav to very old issues that never had it.

I recommend approach 2 (leave them). The nav is added at generation time — if there are only 3 issues, there are only 3 issues with nav. No need to remove nav from old files.

## Edge Cases

1. **First run (no archive)**: Nav bar is present but both links are hidden. Or omit the nav entirely — simpler.
2. **Second run (one archive file)**: Nav bar shows "← 上一期" linking to the one archive file. No "next" on index.html.
3. **Archive file has no nav bar** (pre-navigation issues): The patching step should check if the nav bar exists before attempting to patch. If the archived file lacks `<nav class="issue-nav"`, skip patching.
