---
model: sonnet
tools: Read, Write, Bash, Glob, Grep
---

# Newsletter Assembler

Assemble the 今日讀報 newsletter HTML file from all content pieces.

## Instructions

### 1. Read the template

Read `templates/newsletter.html` for the exact structure, CSS, and JavaScript.

### 2. Embed the glossary

You receive a pre-built, validated glossary JSON object as input. Embed it as:
```javascript
const GLOSSARY = {glossary_json};
```
in the JavaScript section, replacing the `const GLOSSARY = {};` placeholder.

### 3. Build the HTML

Create a complete standalone HTML file matching the template structure exactly:

- **CSS**: Copy verbatim from template
- **JavaScript**: Copy verbatim from template, EXCEPT:
  - In the initialization `else` block, remove the test seed data (`charStates['積'] = 'struggling'` etc.) and replace with just `saveState();`
  - Replace the `const GLOSSARY = {};` placeholder with `const GLOSSARY = {validated_glossary};` using the glossary provided as input.
- **HTML structure**: Same classes, data attributes, and structure

**Navigation bar**: After `</header>`, before `<main>`, insert the navigation bar:
1. Scan `docs/archive/` for files matching the regex `/^\d{4}-\d{2}-\d{2}\.html$/`
2. Sort matching filenames by date descending
3. If archive files exist: the most recent is the "previous" issue
   - Insert `<nav class="issue-nav" data-prev="archive/{date}.html" data-next="">` with `.nav-prev` href pointing to same path, and `.nav-next` with empty href and `hidden` attribute
4. If no archive files exist (first-ever run): omit the `<nav>` element entirely

Fill in:
- Today's date in `<title>` and `.date` element
- All 5 articles with:
  - Chinese headline (in `<h2 class="article-headline">`)
  - Source label (in `<p class="article-source">`)
  - Chinese body (in `<div class="article-body-zh">`)
  - Translation toggle button
  - English translation (in `<div class="article-body-en" hidden>`)
  - `data-article-id` attributes (1-5)
  - `<hr>` between articles
- All 8 Editor's Desk headlines:
  - First 5: class `included`, badge text `收錄`
  - Last 3: class `excluded`, badge text `未收錄`
  - `data-desk-index` attributes (0-7)
  - Headlines in `<span class="desk-headline">` — plain text, no character span wrapping

### 4. Archive the old issue and patch navigation

**CRITICAL: This entire step MUST complete before step 5. You MUST read the OLD docs/index.html, archive it, and patch navigation links BEFORE writing the new newsletter to docs/index.html. If you write the new issue first, the old issue is lost.**

If `docs/index.html` doesn't exist, skip this entire step.

**4a. Read and archive the old issue**

1. Read `docs/index.html` and save its FULL content in memory
2. Extract the date from the `<p class="date">` element — call this `{old_date}`
3. **Fix relative paths for archive location:** The nav links in `index.html` use paths relative to `docs/` (e.g., `archive/2026-03-14.html`). Since the file is moving INTO `docs/archive/`, rewrite the prev link paths:
   - Replace `data-prev="archive/` → `data-prev="`
   - Replace `href="archive/` in the `.nav-prev` link → `href="`
   This changes `archive/2026-03-14.html` to `2026-03-14.html` (correct for a file already in the archive directory).
4. Write the modified content to `docs/archive/{old_date}.html`
5. **Verify:** The date in the archived file should be DIFFERENT from today's date. If it matches today's date, something is wrong — you may have already overwritten index.html. Stop and report the error.

**4b. Patch the newly archived file (MANDATORY — do not skip)**

The newly archived file has `data-next=""` and the next link is hidden. You MUST patch it to point forward to the new current issue:

1. Read `docs/archive/{old_date}.html`
2. If it contains `<nav class="issue-nav"`, apply BOTH of these string replacements:
   - `data-next=""` → `data-next="../index.html"`
   - `href="" class="nav-link nav-next" hidden` → `href="../index.html" class="nav-link nav-next"`
3. Write the patched file back to `docs/archive/{old_date}.html`
4. **Verify:** After writing, grep the file for `data-next="../index.html"` to confirm the patch took effect. If it didn't, report a warning.
5. If the archived file has no `<nav class="issue-nav"` (pre-navigation issue), skip patching.

**4c. Patch the previous archive file (strict sequential chain)**

The previously most-recent archive file (the one before {old_date}) currently has `data-next="../index.html"` (set during the last run). Update it to point to the newly archived file instead:

1. Scan `docs/archive/` for files matching `/^\d{4}-\d{2}-\d{2}\.html$/`, excluding `{old_date}.html`
2. Sort by date descending — the first match is the previous archive
3. If found, and it contains `<nav class="issue-nav"`:
   - Replace `data-next="../index.html"` → `data-next="{old_date}.html"` (just the filename, since both files are in the same `archive/` directory)
   - Replace `href="../index.html" class="nav-link nav-next"` → `href="{old_date}.html" class="nav-link nav-next"`
4. Write the patched file back
5. If no previous archive exists or it has no `<nav class="issue-nav"` (pre-navigation issue), skip this step

### 5. Write the new issue

**Only after step 4 is fully complete**, write the assembled HTML to `docs/index.html`.

### 6. Commit and push

```bash
git add docs/index.html docs/archive/
git commit -m "Newsletter {{date}}"
git push
```

### 7. Validate

Before committing, scan the HTML for:
- Any simplified characters (common ones: 体/國→国, 學→学, 發→发, 時→时, etc.)
- Any Chinese characters NOT wrapped in `<span class="c">` inside article body/headline elements
- Report warnings if found

## Content

### Date
{{date}}

### Articles
{{articles}}

### Translations
{{translations}}

### Editor's Desk Headlines
{{desk_headlines}}

### Glossary
{{glossary}}

## Error Handling

- If `docs/index.html` doesn't exist (first run), skip archiving
- If git push fails, report the error but don't retry
- Report any validation warnings in your response
