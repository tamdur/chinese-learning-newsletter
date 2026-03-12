# Zhongwen Chrome Extension — DOM Compatibility Research

Research based on reading the actual source code of [cschiller/zhongwen](https://github.com/cschiller/zhongwen) on GitHub (content.js, ~1141 lines). The extension descends from Rikaikun → Rikaichan → RikaiXUL.

---

## How Zhongwen Works Internally

### 1. Event Binding

When activated on a tab, Zhongwen attaches a **`mousemove`** listener (not `mouseover`) to the document:

```javascript
document.addEventListener('mousemove', onMouseMove);
document.addEventListener('keydown', onKeyDown);
```

`mousemove` fires continuously as the cursor moves, giving character-level precision — the extension knows exactly which pixel the mouse is over.

### 2. Character Detection: `caretRangeFromPoint`

This is the core mechanism. When the mouse moves, the handler calls:

```javascript
range = document.caretRangeFromPoint(mouseMove.clientX, mouseMove.clientY);
rangeNode = range.startContainer;   // a TEXT NODE
rangeOffset = range.startOffset;    // character index within that text node
```

`caretRangeFromPoint` is a browser API that answers: "If I clicked at these pixel coordinates, where would the text cursor land?" It returns a Range pointing to the exact **text node** and **character offset** under the mouse.

**This means Zhongwen does NOT:**
- Use `document.elementFromPoint`
- Inspect element attributes, classes, or IDs
- Look at `mouseover` targets
- Care about element nesting depth

It only cares about **text nodes reachable by `caretRangeFromPoint`**.

### 3. Parent-Target Validation Check

After getting the range, Zhongwen performs a critical check (line ~466):

```javascript
if (!rangeNode || rangeNode.parentNode !== mouseMove.target) {
    rangeNode = null;
    rangeOffset = -1;
}
```

This compares the **direct parent element** of the text node (from `caretRangeFromPoint`) against the **element that received the `mousemove` event** (`event.target`). If they don't match, the result is discarded.

For standard inline elements, this check passes naturally because `mousemove` targets the innermost element, which is also the text node's parent. For example:

```html
<p><span class="char-flaggable">字</span></p>
```
- `mousemove.target` = the `<span>` (innermost element under the cursor)
- `rangeNode` = text node "字"
- `rangeNode.parentNode` = the `<span>`
- Match ✓

### 4. Chinese Character Validation

Once it has the character, Zhongwen checks if it's Chinese:

```javascript
let u = rangeNode.data.charCodeAt(selStartOffset);
let isChineseCharacter = !isNaN(u) && (
    u === 0x25CB ||                        // ○
    (0x3400 <= u && u <= 0x9FFF) ||        // CJK Unified + Extension A
    (0xF900 <= u && u <= 0xFAFF) ||        // CJK Compatibility Ideographs
    (0xFF21 <= u && u <= 0xFF3A) ||        // Fullwidth Latin uppercase
    (0xFF41 <= u && u <= 0xFF5A) ||        // Fullwidth Latin lowercase
    (0xD800 <= u && u <= 0xDFFF)           // Surrogate pairs (Extension B+)
);
```

If the character isn't in these ranges, the popup is hidden. Traditional Chinese characters (繁體中文) are in the main CJK Unified block (0x4E00–0x9FFF) and fully covered.

### 5. Text Extraction Across Boundaries

After finding the starting character, Zhongwen extracts up to **30 characters** forward to look up multi-character words:

```javascript
function getText(startNode, offset, selEndList, maxLength) {
    let text = startNode.data.substring(offset, endIndex);
    let nextNode = startNode;
    while (text.length < maxLength) {
        nextNode = findNextTextNode(nextNode.parentNode, nextNode);
        if (nextNode === null) break;
        text += getTextFromSingleNode(nextNode, selEndList, maxLength - text.length);
    }
    return text;
}
```

The `findNextTextNode` function uses **`document.createNodeIterator(root, NodeFilter.SHOW_TEXT)`** to walk text nodes in document order. This flattens the DOM tree — it doesn't care about element boundaries between text nodes.

Example:
```html
<span>今</span><span>天</span><span>很</span><span>熱</span>
```
Zhongwen sees this as one continuous string "今天很熱" and can look up "今天" as a word even though the characters are in separate `<span>` elements.

### 6. Word Highlighting

When Zhongwen finds a dictionary match, it highlights the matched characters using `document.createRange()` + `window.getSelection()`. The range can span across multiple text nodes (multiple `<span>` elements).

### 7. Popup Display

Creates `<div id="zhongwen-window">` appended to `document.documentElement` with `z-index: 999999999`. Also may create `<div id="zhongwenDiv">` for textarea overlay scenarios.

---

## What Breaks Zhongwen

### Completely Broken

| Pattern | Why | Evidence |
|---------|-----|----------|
| **Canvas text** | No text nodes in DOM; `caretRangeFromPoint` returns null or the canvas element | GitHub issues #61, #83, #86 (Google Docs broke after switching to canvas rendering) |
| **SVG `<text>`** | Different namespace; `caretRangeFromPoint` behavior unreliable with SVG text nodes | Known browser inconsistency |
| **CSS `content` / pseudo-elements** | `::before`/`::after` text is not in the DOM tree; no text nodes exist | By design — pseudo-elements have no DOM representation |
| **Shadow DOM** | `caretRangeFromPoint` cannot penetrate shadow roots; returns the shadow host element | GitHub issue #122 (Bilibili comments); W3C CSSWG issue #556 |
| **`user-select: none`** | Causes `caretRangeFromPoint` to return null in Chromium — the browser considers the element to have no valid caret position | Chromium bug; documented in VSCode PR #219819 |
| **`pointer-events: none`** | Element is invisible to mouse events AND `caretRangeFromPoint` resolves to whatever is behind the element | By CSS spec |

### Interferes But Doesn't Break

| Pattern | Effect |
|---------|--------|
| **`z-index > 999999999`** | Popup appears behind the element; user can't see dictionary results |
| **Opaque overlays covering text** | `caretRangeFromPoint` hits the overlay, not the text beneath |
| **`<iframe>` (cross-origin)** | Content script runs in `all_frames: true` but cross-origin content is inaccessible by browser security |
| **`<iframe>` (same-origin)** | Works — content script is injected into all frames |

### Has No Effect (Safe)

| CSS Property | Why It's Fine |
|-------------|---------------|
| `color`, `background-color` | Visual-only; text nodes unchanged |
| `font-size`, `font-family`, `line-height` | Visual-only; `caretRangeFromPoint` uses pixel coordinates |
| `cursor: pointer` | Doesn't affect text node detection |
| `display: flex`, `display: grid` | Layout method doesn't affect text nodes |
| `position: relative/absolute` | `caretRangeFromPoint` uses viewport coordinates |
| `transform`, `transition`, `animation` | Visual transforms; `caretRangeFromPoint` resolves correctly |
| `overflow: hidden/scroll` | Clipped text isn't reachable by cursor anyway |
| `border`, `padding`, `margin` | Box model; no effect on text nodes |
| `opacity: 0.5` etc. (not 0) | Text nodes still exist and reachable |

---

## Critical Question: Do `<span>` Wrappers With Click Handlers Break Zhongwen?

**No. This is safe.** Here's the detailed reasoning:

### Our template wraps characters like this:
```html
<p>
  <span class="char-flaggable" onclick="...">台</span>
  <span class="char-flaggable" onclick="...">積</span>
  <span class="char-flaggable" onclick="...">電</span>
</p>
```

### Why it works:

1. **`caretRangeFromPoint` finds the text node inside each `<span>`.**
   Each `<span>` contains a single text node (e.g., "台"). `caretRangeFromPoint(x, y)` returns that text node with offset 0. The `<span>` element itself is irrelevant — Zhongwen only looks at text nodes.

2. **The parent-target check passes.**
   `mousemove.target` = the `<span>` (innermost element). `rangeNode.parentNode` = the same `<span>`. They match.

3. **Multi-character word lookup works across `<span>` boundaries.**
   `findNextTextNode` uses `createNodeIterator(SHOW_TEXT)` which flattens the DOM. When the user hovers over "台", Zhongwen reads forward across `<span>` boundaries and sees "台積電" as a continuous string, finding the dictionary entry for the full word.

4. **Click handlers don't interfere with mousemove.**
   `click` and `mousemove` are independent events. Zhongwen listens for `mousemove`; our flagging system listens for `click`. They don't conflict.

5. **Highlighting spans across `<span>` elements.**
   Zhongwen's `highlightMatch` creates a Range that can cover multiple text nodes. When it highlights "台積電", the Range starts in the first `<span>`'s text node and ends in the third `<span>`'s text node. The browser's selection API handles this natively.

### Verified safe: deeply nested inline elements
```html
<span><em><strong>字</strong></em></span>
```
`createNodeIterator(SHOW_TEXT)` finds the text node regardless of nesting depth. `caretRangeFromPoint` returns the text node. `mousemove.target` = `<strong>` = `rangeNode.parentNode`. All checks pass.

---

## Potential Edge Case: The `<a>` Tag

One GitHub issue mentioned that hyperlinked text sometimes only showed the first word's definition. This could relate to the `rangeNode.parentNode !== mouseMove.target` check if the `<a>` tag has complex internal structure. For our use case, we don't wrap Chinese article text in `<a>` tags, so this is not a concern. Source links are in English.

---

## Recommendations for Newsletter HTML

### DO

1. **Use standard inline/block elements** for all Chinese text: `<p>`, `<span>`, `<h2>`, `<li>`, `<em>`, `<strong>`, `<blockquote>`, `<div>`.

2. **Wrap individual characters in `<span>` tags** for click-to-flag functionality. This is the pattern our template already uses and it is fully compatible:
   ```html
   <p>
     <span class="char-flaggable">台</span>
     <span class="char-flaggable">積</span>
     <span class="char-flaggable">電</span>
     今天宣布
   </p>
   ```

3. **Attach click handlers via `addEventListener`** (not inline `onclick`) for clean separation — though inline handlers work too. Our template uses `addEventListener`, which is correct.

4. **Keep `z-index` values well below 999999999** for any page elements. Our toolbar uses `z-index: 100`, which is fine.

5. **Keep non-Chinese text (English translations, source labels) in standard DOM elements.** Zhongwen ignores non-Chinese characters automatically via its Unicode range check.

### DON'T

1. **Never use `user-select: none`** on any element containing Chinese text. This breaks `caretRangeFromPoint` in Chromium.
   ```css
   /* BAD — breaks Zhongwen */
   article p { user-select: none; }

   /* OK — not on Chinese text */
   .toolbar button { user-select: none; }
   ```

2. **Never use `pointer-events: none`** on Chinese text elements.
   ```css
   /* BAD */
   .char-flaggable { pointer-events: none; }

   /* Our template correctly uses pointer-events normally */
   ```

3. **Never render Chinese text in `<canvas>`, SVG `<text>`, or CSS `content`.**
   ```css
   /* BAD — invisible to Zhongwen */
   .article-title::before { content: "📰 "; }  /* fine — emoji, not Chinese */
   .label::before { content: "新聞："; }        /* BAD — Chinese in pseudo-element */
   ```

4. **Never use Shadow DOM** for components that contain readable Chinese text.

5. **Never use the element IDs `zhongwen-window` or `zhongwenDiv`** — these conflict with the extension's popup and textarea overlay.

6. **Avoid wrapping Chinese text in `<button>` elements** when you want Zhongwen lookup. Buttons have complex internal rendering that may not work reliably with `caretRangeFromPoint`. Use `<span>` or `<div>` with click handlers and `cursor: pointer` instead.

---

## Current Template Audit

Reviewing `templates/newsletter.html` against these findings:

| Feature | Status | Notes |
|---------|--------|-------|
| Chinese text in `<p>`, `<h2>`, `<span>` | ✅ Safe | Standard DOM elements |
| Character wrapping in `<span class="char-flaggable">` | ✅ Safe | `caretRangeFromPoint` finds text nodes inside; multi-character lookup works across spans |
| Click handlers via `addEventListener` | ✅ Safe | Independent from Zhongwen's `mousemove` |
| `cursor: default` / `cursor: pointer` on spans | ✅ Safe | No effect on text detection |
| `border-bottom` for struggling/learned states | ✅ Safe | Visual-only CSS |
| Toolbar `z-index: 100` | ✅ Safe | Well below Zhongwen's 999999999 |
| `background` hover effect on chars | ✅ Safe | Visual-only CSS |
| No `user-select: none` on Chinese text | ✅ Safe | Not present in template |
| No `pointer-events: none` on Chinese text | ✅ Safe | Not present in template |
| No Shadow DOM | ✅ Safe | Vanilla HTML |
| No canvas/SVG text | ✅ Safe | All text in DOM |
| No CSS `content` with Chinese | ✅ Safe | Not present |
| No conflicting element IDs | ✅ Safe | No `zhongwen-window` or `zhongwenDiv` |
| Editor's Desk headlines in `<span class="headline">` | ✅ Safe | Standard inline element |
| Translation div (`display: none` when hidden) | ✅ Safe | Hidden text not under cursor; visible text works normally |

**The template is fully compatible. No changes needed.**

---

## How Both Systems Coexist

The user's workflow involves both Zhongwen (hover to look up words) and our flagging system (click to mark characters). Here's how they interact:

1. **Normal reading (flagging mode OFF):**
   - User hovers over characters → Zhongwen popup appears with definition
   - Clicking does nothing (flagging is disabled)
   - `cursor: default` on character spans — normal reading feel

2. **Flagging mode ON:**
   - User hovers over characters → Zhongwen popup still appears (mousemove still fires)
   - User clicks a character → flagging cycles the state (unmarked → struggling → learned → unmarked)
   - `cursor: pointer` on character spans — visual cue that clicking does something
   - Both systems work simultaneously without conflict

3. **Key insight:** Zhongwen's popup appears on hover and disappears when the mouse moves away. The click event for flagging fires independently. The user can see the Zhongwen definition, decide they're struggling with the character, and click to flag it — all in one natural motion.

---

## Sources

- [Zhongwen GitHub repository](https://github.com/cschiller/zhongwen) — `content.js` source code
- [GitHub issue #122](https://github.com/cschiller/zhongwen/issues/122) — Shadow DOM (Bilibili)
- [GitHub issues #61, #83, #86](https://github.com/cschiller/zhongwen/issues/86) — Canvas rendering (Google Docs)
- [MDN: Document.caretRangeFromPoint()](https://developer.mozilla.org/en-US/docs/Web/API/Document/caretRangeFromPoint)
- [W3C CSSWG issue #556](https://github.com/w3c/csswg-drafts/issues/556) — `caretPositionFromPoint` and Shadow DOM
- [VSCode PR #219819](https://github.com/microsoft/vscode/pull/219819) — `caretRangeFromPoint` + `user-select: none` fix
