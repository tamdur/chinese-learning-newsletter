# Plan

## Change 1: Glossary Builder Integration Update

### What changed in the agent

The glossary-builder agent (`.claude/agents/glossary-builder.md`) was upgraded:
- **Model**: Haiku → Sonnet (for better completeness)
- **Input contract**: Now expects TWO inputs — `CHARACTER_LIST` (deduplicated unique characters, one per line) and `TEXT` (full article text for context)
- **Self-verification**: Agent checks its output against the character list before responding

### What needs to change in `go.md`

**Step 5** currently says:
> Launch a glossary-builder agent (Haiku) with all Chinese text from all 5 articles

Updated instructions for Step 5:

1. **Extract character list**: After Step 4 (article-writer returns), extract all unique Chinese characters from the article writer's output (headlines + body text). Deduplicate and list one per line. This is the `CHARACTER_LIST`.
2. **Collect full text**: Concatenate all Chinese text (headlines + body, plain text without span tags). This is the `TEXT`.
3. **Update model reference**: Haiku → Sonnet
4. **Update prompt format**: Pass both `CHARACTER_LIST` and `TEXT` as labeled sections:
   ```
   CHARACTER_LIST:
   台
   積
   電
   ...

   TEXT:
   台積電今天宣布，計畫在日本...
   ```

The assembler (`.claude/agents/assembler.md`) does NOT invoke the glossary builder — it only receives the glossary JSON as a `{{glossary_json}}` placeholder. No changes needed there.

---

## Change 2: Previous/Next Issue Navigation

### Navigation Bar Spec

- Sits between `</header>` and `<main>` in the HTML
- Shows "← 上一期" (left) and "下一期 →" (right)
- On `index.html` (latest issue): "next" link is hidden
- On oldest available issue: "previous" link is hidden
- Links use relative paths: `archive/YYYY-MM-DD.html` from index, `../index.html` or sibling filename from archive
- Navigation text is plain — NOT character-wrapped (not reading content)
- Simple, muted styling matching existing design
- **Strict sequential**: each archive's "next" points to the next archive file in sequence, not jump-to-latest

### HTML Structure

Add this between `</header>` and `<main>`:

```html
<nav class="issue-nav" data-prev="archive/2026-03-13.html" data-next="">
  <a href="archive/2026-03-13.html" class="nav-link nav-prev">← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>
```

- `data-prev` and `data-next` attributes on `<nav>` are the source of truth for the assembler's find-and-replace patching
- `hidden` attribute hides the "next" link when no next issue exists
- When both links should be hidden (first-ever issue), omit the `<nav>` entirely

### CSS

Add to the `<style>` block:

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

### Assembler Changes (`.claude/agents/assembler.md`)

#### Updated Step 2: Build the HTML

Add to the HTML-building instructions:

> **Navigation bar**: After `</header>`, before `<main>`, insert the navigation bar:
> 1. Scan `docs/archive/` for files matching the regex `/^\d{4}-\d{2}-\d{2}\.html$/`
> 2. Sort matching filenames by date descending
> 3. If archive files exist: the most recent is the "previous" issue
>    - Insert nav with `data-prev="archive/{date}.html"`, `href` on `.nav-prev` pointing to same
>    - `data-next=""`, `.nav-next` has `hidden` attribute
> 4. If no archive files exist (first-ever run): omit the `<nav>` element entirely

#### Updated Step 3: Archive the old issue (with strict sequential patching)

Replace current step 3 with:

> **3a. Archive the old issue**
>
> If `docs/index.html` exists:
> 1. Read it and extract the date from `<p class="date">`
> 2. Write it to `docs/archive/{extracted-date}.html`
>
> **3b. Patch the newly archived file**
>
> The newly archived file (formerly index.html) has `data-next=""` and the next link is hidden. Patch it so its "next" points to the new current issue:
> 1. Read `docs/archive/{extracted-date}.html`
> 2. Apply these string replacements:
>    - `data-next=""` → `data-next="../index.html"`
>    - `href="" class="nav-link nav-next" hidden` → `href="../index.html" class="nav-link nav-next"`
> 3. Write the patched file back
>
> **3c. Patch the previous archive file (strict sequential)**
>
> The previously most-recent archive file currently has `data-next="../index.html"` (set during the last run). Update it to point to the newly archived file instead:
> 1. Scan `docs/archive/` for files matching `/^\d{4}-\d{2}-\d{2}\.html$/`, excluding the file just archived in 3a
> 2. Sort by date descending — the first match is the previous archive
> 3. If found, and it contains `<nav class="issue-nav"`:
>    - Replace `data-next="../index.html"` → `data-next="{newly-archived-filename}.html"` (just the filename, since both files are in the same `archive/` directory)
>    - Replace `href="../index.html" class="nav-link nav-next"` → `href="{newly-archived-filename}.html" class="nav-link nav-next"`
> 4. Write the patched file back
> 5. If no previous archive exists (this is the second-ever issue), skip this step
> 6. If the previous archive has no `<nav class="issue-nav"` (pre-navigation issue), skip patching

#### Updated Step 5: Commit and push

```bash
git add docs/index.html docs/archive/
git commit -m "Newsletter {{date}}"
git push
```

No change needed — `git add docs/archive/` picks up both the newly archived file and the patched previous archive file.

### Template Changes (`templates/newsletter.html`)

Add the nav bar HTML and CSS to the template as reference. The nav bar in the template shows the structure with placeholder values:

```html
<!-- After </header>, before <main> -->
<nav class="issue-nav" data-prev="archive/YYYY-MM-DD.html" data-next="">
  <a href="archive/YYYY-MM-DD.html" class="nav-link nav-prev">← 上一期</a>
  <span class="nav-spacer"></span>
  <a href="" class="nav-link nav-next" hidden>下一期 →</a>
</nav>
```

### Strict Sequential Navigation — Concrete Example

State before today's `/go` run:
- `docs/index.html` — date 2026-03-14, nav has `data-prev="archive/2026-03-13.html"`, `data-next=""`
- `docs/archive/2026-03-13.html` — nav has `data-prev="archive/2026-03-12.html"`, `data-next="../index.html"`
- `docs/archive/2026-03-12.html` — nav has `data-prev=""` (oldest), `data-next="2026-03-13.html"`

After today's run (generating 2026-03-15 issue):
1. Old index.html (2026-03-14) archived to `docs/archive/2026-03-14.html`
2. `2026-03-14.html` patched: `data-next=""` → `data-next="../index.html"`, next link unhidden
3. `2026-03-13.html` patched: `data-next="../index.html"` → `data-next="2026-03-14.html"`, href updated too
4. New `index.html` (2026-03-15) written with `data-prev="archive/2026-03-14.html"`, `data-next=""`

Result — full chain:
- `2026-03-12.html` ← → `2026-03-13.html` ← → `2026-03-14.html` ← → `index.html` (2026-03-15)

### Edge Cases

| Scenario | Behavior |
|----------|----------|
| First-ever run (no archive) | No `<nav>` element in index.html |
| Second run (one archive after archiving) | Newly archived file gets next → `../index.html`. No previous archive to patch. New index.html has prev → archive file. |
| Archive file predates navigation feature | No `<nav>` found → skip patching (graceful) |
| `2026-03-12-test.html` in archive | Regex `/^\d{4}-\d{2}-\d{2}\.html$/` excludes it |

### 10-Issue Window

The nav is added at generation time. No nav is stripped from old issues. If there are 50 archived issues, they all keep working nav links. The "10 issues" concept from the original spec is not enforced as a hard limit — skip unless requested.
