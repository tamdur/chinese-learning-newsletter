# Plan: templates/newsletter.html — Reference Template

## Overview

A complete, working HTML page that serves as both:
1. **A spec for Claude Opus** — shows exact HTML structure, CSS classes, and JS behavior the generation pipeline must produce
2. **A testable prototype** — contains 5 fake articles with realistic Traditional Chinese content so we can verify Zhongwen compatibility, character flagging, translation toggle, and Editor's Desk before the pipeline exists

Everything in one file. No external dependencies. Vanilla HTML/CSS/JS.

---

## Layout and Visual Design

### Page Structure (top to bottom)

```
┌─────────────────────────────────────────┐
│  Header: 今日讀報 + date                 │
├─────────────────────────────────────────┤
│  Article 1                              │
│    Headline (h2)                        │
│    Chinese body text                    │
│    [顯示翻譯 / Show Translation]        │
│    English translation (hidden)         │
│  ─── divider ───                        │
│  Article 2 ...                          │
│  ─── divider ───                        │
│  ... Articles 3-5                       │
├─────────────────────────────────────────┤
│  Editor's Desk (編輯台)                  │
│    6 headlines with selection UI        │
├─────────────────────────────────────────┤
│  Toolbar: [標記模式 OFF] [匯出回饋]      │
├─────────────────────────────────────────┤
│  Footer: minimal                        │
└─────────────────────────────────────────┘
```

### Typography and Spacing

- **Max width:** 680px, centered with `margin: 0 auto`
- **Base font size:** 19px for body text
- **Line height:** 1.9 for Chinese body text (generous vertical spacing for character density)
- **Font stack:** `"Noto Serif TC", "PMingLiU", "Apple LiSung", serif` — prioritize fonts with good Traditional Chinese coverage
- **Headlines:** 24px, `font-weight: 700`, same serif stack
- **Background:** `#faf9f6` (warm off-white)
- **Text color:** `#2c2c2c` (soft black — easier on the eyes than pure black)
- **Dividers between articles:** `<hr>` styled as a thin line (`border-top: 1px solid #e0ddd8`), with `margin: 2.5rem 0`
- **Padding:** `1.5rem` on the main container (comfortable on narrower screens)

### Header

```html
<header class="newsletter-header">
  <h1>今日讀報</h1>
  <p class="date">2026-03-12</p>
</header>
```

- `h1` at 32px, centered
- Date in muted color (`#888`), centered below title
- No character wrapping on the title or date — these are not flaggable content

### Toolbar

Positioned at the bottom of the page, below the Editor's Desk and above the footer. **Not sticky** — the user reads first, then interacts with flagging and export after reading. If they want to toggle flagging mid-read, scrolling to the bottom is fine.

```html
<div class="toolbar" id="toolbar">
  <button id="flag-toggle" type="button">標記模式 OFF</button>
  <button id="export-btn" type="button">匯出回饋 Export Feedback</button>
  <span id="export-confirm" class="confirm-msg" hidden>已匯出 ✓</span>
</div>
```

- Background: `#f0ede8` (matches Editor's Desk tint), with `border-top: 1px solid #e0ddd8`
- Buttons styled as minimal pill shapes: `border-radius: 4px`, `border: 1px solid #ccc`, `background: #fff`, `padding: 6px 14px`
- Active flag toggle gets a colored border: `border-color: #d4a574` (warm amber)
- `user-select: none` on toolbar buttons (safe — no Chinese text here)
- `margin-top: 2rem`, `padding: 1.5rem 0`, centered

### Editor's Desk

Visually distinct section with a different background to separate from articles:

```css
.editors-desk {
  background: #f0ede8;
  border-radius: 8px;
  padding: 1.5rem;
  margin-top: 2.5rem;
}
```

Details in the Editor's Desk section below.

### Overall Feel

Calm, spacious, unhurried. A well-designed blog post, not a news portal. Plenty of whitespace. The reading experience comes first; interactive elements are present but unobtrusive.

---

## Zhongwen Compatibility

All rules derived from `research/zhongwen_compatibility.md`.

### Character Wrapping

Every Chinese character in article **body text** is wrapped in an individual `<span>`:

```html
<p>
  <span class="c">台</span><span class="c">積</span><span class="c">電</span><span class="c">今</span><span class="c">天</span><span class="c">宣</span><span class="c">布</span>
</p>
```

- Class name: `c` (short — there will be thousands of these per page)
- No whitespace between spans (Chinese text has no word spacing)
- Punctuation characters (。、！？「」) are also wrapped in `<span class="c">` — they should be flaggable and they don't interfere with Zhongwen (the extension ignores non-CJK characters automatically via its Unicode range check)

### Article Headlines

Headlines **are also character-wrapped** for flagging. The headline is where the user first encounters a story's key vocabulary, and being able to flag unfamiliar characters there is valuable.

```html
<h2 class="article-headline">
  <span class="c">台</span><span class="c">積</span><span class="c">電</span><span class="c">宣</span><span class="c">布</span><span class="c">新</span><span class="c">廠</span><span class="c">計</span><span class="c">畫</span>
</h2>
```

### Multi-Character Word Lookup Across Span Boundaries

This is the most important compatibility finding. Zhongwen uses `document.createNodeIterator(root, NodeFilter.SHOW_TEXT)` to walk text nodes in document order. This **flattens the DOM tree** — it doesn't care about `<span>` element boundaries.

When the user hovers over 台 in `<span class="c">台</span><span class="c">積</span><span class="c">電</span>`, Zhongwen:
1. Gets the text node "台" via `caretRangeFromPoint`
2. Calls `findNextTextNode` to walk forward through sibling text nodes
3. Reads "積" from the next span's text node, then "電" from the next
4. Concatenates to "台積電" and finds the dictionary entry for TSMC

**This works because each `<span>` contains exactly one text node, and `createNodeIterator` traverses them in document order regardless of element boundaries.**

### DOM Rules (all enforced)

| Rule | Implementation |
|------|---------------|
| All Chinese text in standard DOM elements | `<p>`, `<span>`, `<h2>`, `<li>` only |
| No `user-select: none` on Chinese text | Applied only to `.toolbar button` elements |
| No `pointer-events: none` on Chinese text | Not used anywhere on text |
| No canvas, SVG text, CSS `content` for Chinese | Not present |
| No Shadow DOM | Vanilla HTML throughout |
| No conflicting element IDs | No `zhongwen-window` or `zhongwenDiv` |
| z-index values below 999999999 | No elevated z-index used (toolbar is not sticky) |

### Parent-Target Check

Zhongwen validates: `rangeNode.parentNode === mousemove.target`. For our spans:
- `mousemove.target` = the `<span class="c">` (innermost element under cursor)
- `rangeNode` = text node inside the span (e.g., "台")
- `rangeNode.parentNode` = the `<span class="c">`
- Match passes every time.

---

## Character Flagging System

### Mode Toggle

- Default: **OFF** (normal reading mode)
- Toggle button in toolbar: `標記模式 OFF` / `標記模式 ON`
- Button text and border color change to indicate active state

```javascript
let flaggingMode = false;

document.getElementById('flag-toggle').addEventListener('click', function() {
  flaggingMode = !flaggingMode;
  this.textContent = flaggingMode ? '標記模式 ON' : '標記模式 OFF';
  this.classList.toggle('active', flaggingMode);
  document.body.classList.toggle('flagging-on', flaggingMode);
});
```

### Cursor Behavior

```css
/* Normal reading mode — default cursor */
.c { cursor: default; }

/* Flagging mode — pointer cursor on all characters */
.flagging-on .c { cursor: pointer; }
```

### Click-to-Cycle States

When flagging mode is ON, clicking a character span cycles: **unmarked → struggling → learned → unmarked**.

```javascript
document.addEventListener('click', function(e) {
  if (!flaggingMode) return;
  const span = e.target.closest('.c');
  if (!span) return;

  const char = span.textContent;
  const state = getCharState(char);

  let newState;
  if (state === 'unmarked') newState = 'struggling';
  else if (state === 'struggling') newState = 'learned';
  else newState = 'unmarked';

  setCharState(char, newState);
  updateCharVisuals(char, newState);
});
```

`setCharState` and `getCharState` read/write the localStorage state object. `updateCharVisuals` applies the CSS class to **all instances** of that character on the page (a character flagged as struggling in article 1 should also show as struggling in article 3).

### Visual Indicators

Subtle — must not interfere with readability:

```css
/* Struggling: soft warm underline */
.c.struggling {
  border-bottom: 2px solid #d4a574;
}

/* Learned: brief dotted green underline, then remove */
.c.learned {
  border-bottom: 2px dotted #7aab7a;
}

/* Unmarked: no decoration (default) */
```

Both treatments use `border-bottom` rather than `text-decoration` to avoid interfering with Zhongwen's text selection highlighting. The colors are muted enough to not distract during reading.

**No background color change** — that would interfere with the Zhongwen hover highlight, which uses selection/range highlighting.

### Hover Effect in Flagging Mode

A very subtle background on hover, only in flagging mode:

```css
.flagging-on .c:hover {
  background: rgba(0, 0, 0, 0.04);
  border-radius: 2px;
}
```

### Zhongwen Coexistence

Both systems work simultaneously when flagging mode is ON:
- **Hover** → Zhongwen popup appears (mousemove event)
- **Click** → Character state cycles (click event)
- These are independent events that don't conflict
- The user can hover to see the definition, then click to flag the character — one natural motion

---

## Translation Toggle

### Per-Article Toggle

Each article has its own toggle button. Per-article (not global) because:
- The user reads one article at a time and may want the translation for a harder article but not an easier one
- A global toggle would force an all-or-nothing choice

### HTML Structure

```html
<article class="article" data-article-id="1">
  <h2 class="article-headline">
    <span class="c">台</span><span class="c">積</span><span class="c">電</span>...
  </h2>
  <p class="article-source">來源：Hacker News</p>

  <div class="article-body-zh">
    <p><span class="c">台</span><span class="c">積</span>...</p>
    <p>...</p>
  </div>

  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>

  <div class="article-body-en" hidden>
    <p>TSMC announced today that...</p>
    <p>...</p>
  </div>
</article>
```

### Toggle Behavior

```javascript
document.querySelectorAll('.translation-toggle').forEach(btn => {
  btn.addEventListener('click', () => {
    const article = btn.closest('.article');
    const enDiv = article.querySelector('.article-body-en');
    const isHidden = enDiv.hidden;
    enDiv.hidden = !isHidden;
    btn.textContent = isHidden
      ? '隱藏翻譯 Hide Translation'
      : '顯示翻譯 Show Translation';
  });
});
```

### English Translation Styling

```css
.article-body-en {
  font-family: Georgia, "Times New Roman", serif;
  color: #666;
  font-size: 16px;
  line-height: 1.6;
  border-left: 3px solid #e0ddd8;
  padding-left: 1rem;
  margin-top: 1rem;
}
```

- Visually distinct: smaller font, muted color, left border
- No character wrapping — English text is plain
- No flagging interaction on English text
- `hidden` attribute used for toggle (not `display: none` in CSS) — simpler, more semantic

---

## Editor's Desk Section

### Layout

```html
<section class="editors-desk">
  <h2>編輯台 Editor's Desk</h2>
  <p class="desk-instructions">選擇你最感興趣的 3 則標題 Pick your top 3 headlines</p>

  <div class="desk-items">
    <div class="desk-item included" data-desk-index="0">
      <span class="desk-badge">收錄</span>
      <span class="desk-headline">台積電宣布在日本興建第三座晶圓廠</span>
    </div>
    <div class="desk-item included" data-desk-index="1">
      <span class="desk-badge">收錄</span>
      <span class="desk-headline">聯準會維持利率不變，暗示年底前可能降息</span>
    </div>
    <div class="desk-item included" data-desk-index="2">
      <span class="desk-badge">收錄</span>
      <span class="desk-headline">密西根大學籃球隊闖進八強</span>
    </div>
    <div class="desk-item excluded" data-desk-index="3">
      <span class="desk-badge">未收錄</span>
      <span class="desk-headline">歐盟通過新的人工智慧監管法案</span>
    </div>
    <div class="desk-item excluded" data-desk-index="4">
      <span class="desk-badge">未收錄</span>
      <span class="desk-headline">SpaceX 星艦第五次試飛成功回收</span>
    </div>
    <div class="desk-item excluded" data-desk-index="5">
      <span class="desk-badge">未收錄</span>
      <span class="desk-headline">日本京都百年老店的經營哲學</span>
    </div>
  </div>

  <p class="desk-count">已選：<span id="desk-count-num">0</span> / 3</p>
</section>
```

### Visual Design

- **Included items:** Normal text weight, `收錄` badge in muted green
- **Excluded items:** Normal text weight, `未收錄` badge in muted gray
- **Both are equally clickable** — the distinction is informational, not functional
- Headlines are in standard `<span>` elements — not character-wrapped (no flagging needed), but these are readable Chinese text and the user may want to look up words with Zhongwen. **Zhongwen hover lookup works here**: the headlines are plain text nodes inside `<span>` elements, which is exactly what `caretRangeFromPoint` + the parent-target check expects. Multi-character word lookup works across the text naturally since each headline is a single text node

```css
.desk-item {
  padding: 12px 14px;
  border: 1px solid #e0ddd8;
  border-radius: 6px;
  margin-bottom: 8px;
  cursor: pointer;
  transition: border-color 0.15s;
}

.desk-item:hover {
  border-color: #b8b3aa;
}

.desk-item.selected {
  border-color: #d4a574;
  background: rgba(212, 165, 116, 0.08);
}

.desk-badge {
  font-size: 12px;
  padding: 2px 6px;
  border-radius: 3px;
  margin-right: 8px;
}

.included .desk-badge {
  background: #e8f0e8;
  color: #5a7a5a;
}

.excluded .desk-badge {
  background: #eee;
  color: #999;
}
```

### Selection Behavior

**Maximum 3 selections. Clicking a 4th deselects the oldest.**

This is better UX than blocking because:
- The user doesn't need to figure out which one to deselect first
- It mirrors a "replace the oldest pick" mental model
- No error states or confusing "you can't do that" messages

```javascript
let deskPicks = []; // ordered array of indices

document.querySelectorAll('.desk-item').forEach(item => {
  item.addEventListener('click', () => {
    const index = parseInt(item.dataset.deskIndex);
    const existingPos = deskPicks.indexOf(index);

    if (existingPos !== -1) {
      // Already selected — deselect
      deskPicks.splice(existingPos, 1);
      item.classList.remove('selected');
    } else {
      // New selection
      if (deskPicks.length >= 3) {
        // Remove oldest pick
        const oldest = deskPicks.shift();
        document.querySelector(`[data-desk-index="${oldest}"]`).classList.remove('selected');
      }
      deskPicks.push(index);
      item.classList.add('selected');
    }

    document.getElementById('desk-count-num').textContent = deskPicks.length;
    saveState();
  });
});
```

---

## localStorage

### Key and Schema

Single key: `newsletter-feedback` (namespaced to avoid collision with other GitHub Pages projects on same origin).

```javascript
const STORAGE_KEY = 'newsletter-feedback';

// Stored value shape:
{
  "characters": {
    "積": "struggling",
    "膨": "struggling",
    "鏈": "learned"
    // Only flagged characters. Unmarked = absent.
  },
  "deskPicks": [0, 3, 5]
  // Indices into desk items, in selection order.
}
```

### Load on Page Open

On `DOMContentLoaded`, restore state from localStorage:

```javascript
document.addEventListener('DOMContentLoaded', () => {
  if (!isLocalStorageAvailable()) {
    disableFeedbackFeatures();
    return;
  }

  const state = loadState();

  // Restore character visuals
  for (const [char, charState] of Object.entries(state.characters)) {
    updateCharVisuals(char, charState);
  }

  // Restore desk picks
  for (const index of state.deskPicks) {
    const item = document.querySelector(`[data-desk-index="${index}"]`);
    if (item) {
      item.classList.add('selected');
      deskPicks.push(index);
    }
  }

  document.getElementById('desk-count-num').textContent = deskPicks.length;
});
```

### Save on Every Change

Both `setCharState` and desk item clicks call `saveState()`:

```javascript
const saveState = () => {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({
      characters: charStates,
      deskPicks: deskPicks
    }));
  } catch (e) {
    if (e.name === 'QuotaExceededError') {
      console.warn('localStorage full');
    }
  }
};

const loadState = () => {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    return saved ? JSON.parse(saved) : { characters: {}, deskPicks: [] };
  } catch (e) {
    localStorage.removeItem(STORAGE_KEY);
    return { characters: {}, deskPicks: [] };
  }
};
```

---

## Feedback Export

### Export Button

In the toolbar: `匯出回饋 Export Feedback`

### What Gets Exported

The export JSON matches what the cleanup pipeline expects:

```javascript
const exportFeedback = () => {
  const state = loadState();

  // Read offered headlines from the DOM (not localStorage)
  const offered = [...document.querySelectorAll('.desk-item')].map(item => ({
    headline: item.querySelector('.desk-headline').textContent,
    included_in_issue: item.classList.contains('included')
  }));

  const today = document.querySelector('.date').textContent; // "2026-03-12"

  const charExport = {};
  for (const [char, charState] of Object.entries(state.characters)) {
    charExport[char] = { state: charState, date: today };
  }

  const exportData = {
    date: today,
    characters: charExport,
    editors_desk: {
      offered,
      user_top_3: state.deskPicks
    }
  };

  downloadJSON(exportData, `feedback_${today}.json`);
  showExportConfirmation();
};
```

### Download Mechanism

Blob download per `research/localstorage_export.md`:

```javascript
const downloadJSON = (data, filename) => {
  const json = JSON.stringify(data, null, 2);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
};
```

### Confirmation Message

After successful export, show a brief confirmation next to the export button:

```javascript
const showExportConfirmation = () => {
  const msg = document.getElementById('export-confirm');
  msg.hidden = false;
  setTimeout(() => { msg.hidden = true; }, 3000);
};
```

Styled: green text, small font, appears inline next to the button.

### Fallback: Clipboard Copy

If the Blob download fails (unlikely but possible):

```javascript
const downloadJSON = (data, filename) => {
  const json = JSON.stringify(data, null, 2);
  try {
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
  } catch (e) {
    // Fallback: copy to clipboard
    navigator.clipboard.writeText(json).then(() => {
      alert('下載失敗，已複製到剪貼簿。請貼到一個 .json 檔案。\nDownload failed. Copied to clipboard. Paste into a .json file.');
    });
  }
};
```

### Post-Export: Do NOT Auto-Clear localStorage

Reasoning:
- The user might export, then realize they want to flag more characters and re-export
- The user might forget to run cleanup before reading the next newsletter — old flags still visible would remind them
- Cleanup pipeline handles the merge; clearing is cleanup's responsibility
- If we clear and the export file gets lost, the feedback is gone

The next newsletter generation overwrites `docs/index.html`, at which point the old localStorage data is no longer relevant to the page content. The cleanup pipeline should clear the localStorage key as a final step (documented in cleanup_prompt.md), or the user can clear manually.

---

## Graceful Degradation

### localStorage Unavailable

```javascript
const isLocalStorageAvailable = () => {
  try {
    const key = '__test__';
    localStorage.setItem(key, '1');
    localStorage.removeItem(key);
    return true;
  } catch (e) {
    return false;
  }
};

const disableFeedbackFeatures = () => {
  document.getElementById('flag-toggle').disabled = true;
  document.getElementById('export-btn').disabled = true;
  const note = document.createElement('p');
  note.className = 'storage-warning';
  note.textContent = '回饋功能需要啟用瀏覽器儲存 Feedback features require browser storage';
  document.getElementById('toolbar').after(note);
};
```

Reading, Zhongwen lookup, and translation toggles all still work. Only flagging and export are disabled.

### localStorage Corrupt

`loadState()` catches JSON parse errors, removes the corrupt key, and returns a clean default. The user loses any in-progress feedback but the page works normally.

### Export Fails

Falls back to clipboard copy (see Export section above).

---

## Sample Content

The template includes 5 fake articles with realistic Traditional Chinese content at roughly grade 5 level, plus English translations. Article length follows `config/settings.json`'s `article_length` guidance (~100-200 characters per article). The articles don't need to be real news — they should be representative of the newsletter's tone (knowledgeable friend over coffee) and difficulty level.

### Sample Articles

1. **台積電宣布在日本興建第三座晶圓廠** (TSMC Japan fab — tech/AI)
   - ~150 characters of Chinese body text
   - English translation

2. **聯準會維持利率不變** (Fed holds rates — econ/finance)
   - ~150 characters
   - English translation

3. **密西根大學籃球隊闖進八強** (Michigan basketball Elite Eight — sports)
   - ~150 characters
   - English translation

4. **科學家發現一種新的深海魚類** (New deep-sea fish discovered — serendipity/science)
   - ~150 characters
   - English translation

5. **小乘太空旅行時代來臨** (Space tourism — serendipity/tech)
   - ~150 characters
   - English translation

### Sample Editor's Desk Headlines

3 included (matching articles 1, 2, 3) + 3 excluded:
- 歐盟通過新的人工智慧監管法案
- SpaceX 星艦第五次試飛成功回收
- 日本京都百年老店的經營哲學

### Sample Character Pre-Flags

Include 2-3 characters pre-flagged as struggling in the sample localStorage state (e.g., 積, 廠) so the visual indicators are immediately testable without needing to activate flagging mode first.

---

## Code Organization

### Single-File Structure

```html
<!DOCTYPE html>
<html lang="zh-Hant">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>今日讀報 — 2026-03-12</title>
  <style>
    /* All CSS here — see sections above for specifics */
  </style>
</head>
<body>
  <header class="newsletter-header">...</header>
  <main>
    <article class="article" data-article-id="1">...</article>
    <hr>
    <article class="article" data-article-id="2">...</article>
    <!-- ... articles 3-5 ... -->
  </main>
  <section class="editors-desk">...</section>
  <div class="toolbar" id="toolbar">...</div>
  <footer>...</footer>
  <script>
    /* All JS here — see sections above for specifics */
  </script>
</body>
</html>
```

### HTML Markers for Generation Pipeline

The generation pipeline must produce these exact structural patterns:

| Structure | Marker | Purpose |
|-----------|--------|---------|
| Article boundary | `<article class="article" data-article-id="N">` | Identifies each article |
| Chinese body | `<div class="article-body-zh">` | Contains character-wrapped Chinese text |
| English body | `<div class="article-body-en" hidden>` | Contains plain English translation |
| Character span | `<span class="c">字</span>` | Individual character for flagging |
| Headline | `<h2 class="article-headline">` | Contains character-wrapped headline |
| Source label | `<p class="article-source">` | Plain-text attribution (no link) to the single most primary source |
| Translation toggle | `<button class="translation-toggle">` | Per-article toggle |
| Desk item (included) | `<div class="desk-item included" data-desk-index="N">` | Headline that made the cut |
| Desk item (excluded) | `<div class="desk-item excluded" data-desk-index="N">` | Headline that didn't |
| Desk headline text | `<span class="desk-headline">` | Headline text (read by export) |
| Desk badge | `<span class="desk-badge">` | 收錄 / 未收錄 label |
| Date | `<p class="date">` | YYYY-MM-DD (read by export for filename) |

### Major JS Functions

| Function | Purpose |
|----------|---------|
| `isLocalStorageAvailable()` | Feature-detect localStorage |
| `loadState()` | Read and parse localStorage, with JSON error recovery |
| `saveState()` | Serialize current state to localStorage |
| `getCharState(char)` | Return 'struggling', 'learned', or 'unmarked' for a character |
| `setCharState(char, state)` | Update in-memory state + save to localStorage |
| `updateCharVisuals(char, state)` | Apply/remove CSS classes on ALL instances of a character |
| `exportFeedback()` | Build export JSON from localStorage + DOM, trigger download |
| `downloadJSON(data, filename)` | Blob download with clipboard fallback |
| `showExportConfirmation()` | Flash confirmation message |
| `disableFeedbackFeatures()` | Disable flagging/export when localStorage unavailable |

### In-Memory State

Two JS variables track the live state:

```javascript
const charStates = {};  // { "積": "struggling", "鏈": "learned", ... }
let deskPicks = [];     // [0, 3, 5] — ordered indices
```

These are initialized from localStorage on page load and written back on every change. They are the single source of truth during the session; localStorage is the persistence layer.

---

## Implementation Notes

- The template should be fully functional when opened as a local file (`file://`) and when served from GitHub Pages (`https://`). All features work in both contexts except: localStorage may behave differently in some browsers for `file://` URLs (Chrome treats each file as a unique origin). This is fine — the primary use case is GitHub Pages.
- Use modern JavaScript throughout: `const`, `let`, arrow functions, template literals. This is a single-user tool on a recent Chrome version — no browser compatibility concerns. The generation pipeline should use the same modern syntax.
- The generation pipeline's job is to produce HTML matching these structural patterns with real content. The pipeline prompt will reference this template file and say "produce output matching this structure."

