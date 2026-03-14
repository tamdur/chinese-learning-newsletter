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

If `docs/index.html` doesn't exist, skip this entire step.

**4a. Archive the old issue**

If `docs/index.html` exists:
1. Read it and extract the date from the `<p class="date">` element
2. Write it to `docs/archive/{extracted-date}.html`

**4b. Patch the newly archived file**

The newly archived file (formerly index.html) has `data-next=""` and the next link is hidden. Patch it so its "next" points to the new current issue:
1. Read `docs/archive/{extracted-date}.html`
2. Apply these string replacements:
   - `data-next=""` → `data-next="../index.html"`
   - `href="" class="nav-link nav-next" hidden` → `href="../index.html" class="nav-link nav-next"`
3. Write the patched file back
4. If the archived file has no `<nav class="issue-nav"` (pre-navigation issue), skip patching

**4c. Patch the previous archive file (strict sequential)**

The previously most-recent archive file currently has `data-next="../index.html"` (set during the last run). Update it to point to the newly archived file instead:
1. Scan `docs/archive/` for files matching `/^\d{4}-\d{2}-\d{2}\.html$/`, excluding the file just archived in 4a
2. Sort by date descending — the first match is the previous archive
3. If found, and it contains `<nav class="issue-nav"`:
   - Replace `data-next="../index.html"` → `data-next="{newly-archived-filename}.html"` (just the filename, since both files are in the same `archive/` directory)
   - Replace `href="../index.html" class="nav-link nav-next"` → `href="{newly-archived-filename}.html" class="nav-link nav-next"`
4. Write the patched file back
5. If no previous archive exists or it has no `<nav class="issue-nav"` (pre-navigation issue), skip this step

### 5. Write the new issue

Write the assembled HTML to `docs/index.html`.

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
