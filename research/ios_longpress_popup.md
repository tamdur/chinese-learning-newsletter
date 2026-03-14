# iOS Long-Press Popup for Chinese Character Lookup

Research document for implementing a long-press (touch-and-hold) popup on individual Chinese characters in an HTML page on iOS Safari/Chrome. The newsletter wraps each character in `<span class="c">字</span>`.

**Critical constraint:** The Zhongwen Chrome extension on desktop requires standard CSS. Applying `user-select: none` globally breaks it. All mobile touch handling and CSS must be scoped to mobile devices only.

---

## 1. iOS WebKit Native Long-Press Behavior

### Default behavior on `<span>` with a single Chinese character

When a user long-presses a `<span>` containing a single Chinese character in iOS Safari or Chrome (both use WebKit on iOS), the following sequence occurs:

1. **~500ms hold**: The magnifying glass "loupe" appears, showing a zoomed view of the text under the finger.
2. **On release**: The character (or a span of text around it) is selected, shown with blue highlight and selection handles.
3. **Context menu**: A menu appears above the selection with options like Copy, Look Up, Share, etc. The "Look Up" option triggers iOS's built-in dictionary lookup, which can show Chinese definitions if the appropriate dictionary is installed.

### Chinese vs English text selection

iOS handles Chinese text selection differently from English:

- **English**: Double-tap or long-press selects a whole word (space-delimited).
- **Chinese/CJK**: Because Chinese has no spaces between words, iOS uses its own segmentation heuristics. A long-press on a single character in a `<span class="c">` that contains only one character will typically select just that character, since the span boundary acts as a natural segmentation point. However, if characters are in a continuous text node, iOS may select multiple characters based on its word-boundary algorithm (using `Intl.Segmenter`-like logic internally).

Since each character is in its own `<span class="c">`, iOS will typically select just the single character, which actually works in our favor for per-character interaction.

### CSS properties affecting native behavior

| Property | Effect on iOS |
|---|---|
| `-webkit-touch-callout: none` | Suppresses the context menu (Copy/Look Up/Share) on long-press for links. For plain text, effect is limited — it primarily targets link callouts. |
| `-webkit-user-select: none` / `user-select: none` | Prevents text selection entirely. Also suppresses the magnifying glass loupe (confirmed fixed in WebKit post-iOS 15 — earlier versions had a bug where the loupe appeared even with this property). |
| Neither property set (default) | Full native behavior: loupe, selection, context menu. |

### iOS 15+ loupe bug (resolved)

In iOS 15, there was a WebKit bug where `-webkit-user-select: none` did not suppress the magnifying glass loupe. This was tracked as [WebKit bug #231161](https://bugs.webkit.org/show_bug.cgi?id=231161) and has been fixed in subsequent releases. Modern iOS (16+) correctly respects `user-select: none` and suppresses both text selection and the loupe.

Sources:
- [Leaflet iOS 15 magnifying loupe issue](https://github.com/Leaflet/Leaflet/issues/7678)
- [WKWebView iOS 15 long press text selection](https://developer.apple.com/forums/thread/691568)
- [-webkit-touch-callout - MDN](https://developer.mozilla.org/en-US/docs/Web/CSS/-webkit-touch-callout)

---

## 2. Intercepting Long-Press Without Native Selection

### Strategy overview

To implement a custom long-press handler, we need two things working together:

1. **CSS** to prevent native text selection and callout (mobile only)
2. **JavaScript** touch event handlers with a timer to detect the hold duration

Neither alone is sufficient. CSS prevents the visual artifacts (loupe, selection handles, context menu) while JavaScript provides the custom behavior.

### CSS (mobile-only, scoped via media query)

```css
@media (pointer: coarse) {
  .c {
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
    touch-action: manipulation;  /* prevents double-tap zoom delay */
  }
}
```

**Why `@media (pointer: coarse)` and not global:**
The Zhongwen Chrome extension on desktop requires standard text selection behavior. The `user-select: none` property breaks Zhongwen's ability to detect characters under the cursor. By scoping to `pointer: coarse`, these styles only apply on touch-primary devices (phones, tablets), leaving desktop browsers completely unaffected.

The `touch-action: manipulation` property is a bonus: it tells the browser this element only needs panning and pinching, which eliminates the ~300ms delay iOS adds to detect double-tap-to-zoom.

### JavaScript long-press handler

```javascript
// Only activate on touch devices
if (!window.matchMedia('(pointer: coarse)').matches) {
  // Desktop: do nothing, let Zhongwen work undisturbed
  return;
}

let longPressTimer = null;
let startX = 0;
let startY = 0;
const LONG_PRESS_MS = 400;     // duration threshold
const MOVE_THRESHOLD = 10;      // pixels of movement allowed

document.addEventListener('touchstart', function(e) {
  const span = e.target.closest('.c');
  if (!span) return;

  const touch = e.touches[0];
  startX = touch.clientX;
  startY = touch.clientY;

  // Visual feedback: subtle highlight after ~100ms
  const feedbackTimer = setTimeout(() => {
    span.classList.add('touch-active');
  }, 100);

  longPressTimer = setTimeout(() => {
    // Long press confirmed
    showCharacterPopup(span.textContent, span);
  }, LONG_PRESS_MS);

  // Store feedbackTimer for cleanup
  span._feedbackTimer = feedbackTimer;

  // preventDefault suppresses native selection/loupe
  // But ONLY on .c spans, not on other page content
  e.preventDefault();
}, { passive: false });

document.addEventListener('touchmove', function(e) {
  if (!longPressTimer) return;

  const touch = e.touches[0];
  const dx = Math.abs(touch.clientX - startX);
  const dy = Math.abs(touch.clientY - startY);

  // User is scrolling, cancel long press
  if (dx > MOVE_THRESHOLD || dy > MOVE_THRESHOLD) {
    clearTimeout(longPressTimer);
    longPressTimer = null;
    document.querySelectorAll('.touch-active').forEach(el =>
      el.classList.remove('touch-active')
    );
  }
});

document.addEventListener('touchend', function(e) {
  clearTimeout(longPressTimer);
  longPressTimer = null;

  // Clean up visual feedback
  const span = e.target.closest('.c');
  if (span) {
    clearTimeout(span._feedbackTimer);
    span.classList.remove('touch-active');
  }
});

document.addEventListener('touchcancel', function(e) {
  clearTimeout(longPressTimer);
  longPressTimer = null;
  document.querySelectorAll('.touch-active').forEach(el =>
    el.classList.remove('touch-active')
  );
});
```

### Is `preventDefault()` on touchstart sufficient?

**Short answer: Yes, but with caveats.**

- `e.preventDefault()` on `touchstart` prevents iOS from initiating text selection and showing the loupe. It also prevents scrolling from that touch point.
- The CSS properties (`-webkit-user-select: none`, `-webkit-touch-callout: none`) serve as a belt-and-suspenders approach. Some iOS versions (especially older ones) may not fully respect `preventDefault()` alone.
- **Important:** Calling `preventDefault()` on touchstart for the entire document would break scrolling. The handler must only call it when the touch target is a `.c` span. Alternatively, attach listeners specifically to `.c` elements rather than using event delegation.

### Interaction with existing flagging mode

The current newsletter has a flagging mode where single-tap cycles character states (unmarked -> struggling -> learned). On mobile:

- **Flagging mode OFF**: Long-press triggers character lookup popup. Single tap does nothing (or could scroll, or do nothing special).
- **Flagging mode ON**: Single tap cycles state (existing behavior). Long-press could either be disabled or still show lookup. Recommend: long-press always shows lookup regardless of flagging mode, since the gestures don't conflict (tap vs hold).

### Scrolling concern

The `MOVE_THRESHOLD` of 10px handles the scrolling case. If a user touches a character and immediately starts scrolling (vertical swipe), the touchmove handler detects movement > 10px and cancels the long-press timer. The `e.preventDefault()` on touchstart does suppress scroll initiation from that specific touch, which is a problem.

**Better approach — use `{ passive: false }` selectively:**

Instead of calling `preventDefault()` immediately on touchstart, delay the prevention. Start the timer on touchstart without preventing default. Only if the user hasn't moved after ~100ms, then prevent further default behavior. However, this is complex and fragile on iOS.

**Pragmatic solution:** Since `.c` spans are small (single characters), users are unlikely to begin a scroll gesture precisely on a character. And if they do, the touch will move beyond the threshold quickly, canceling the long press. The scroll itself won't be blocked because `preventDefault()` is only called when `e.target.closest('.c')` matches — if the user starts scrolling from whitespace or non-character areas, scrolling works normally.

Sources:
- [Apple: Handling Events in Safari](https://developer.apple.com/library/archive/documentation/AppleApplications/Reference/SafariWebContent/HandlingEvents/HandlingEvents.html)
- [MDN: Touch events](https://developer.mozilla.org/en-US/docs/Web/API/Touch_events)
- [How to prevent context menu on long press](https://additionalknowledge.com/2024/08/02/how-to-prevent-the-default-context-menu-live-preview-on-long-press-in-mobile-safari-chrome/)
- [use-long-press: iOS text selection issue](https://github.com/minwork/use-long-press/issues/7)

---

## 3. Alternative Gestures to Long-Press

### Option A: Long-press (recommended)

| Aspect | Assessment |
|---|---|
| Familiarity | Standard iOS gesture for "more info" — users already know it from Look Up in Safari, iBooks |
| Conflict with flagging | None — flagging uses single tap, long-press is a distinct gesture |
| Conflict with native | Must suppress native selection/loupe via CSS+JS (solved in section 2) |
| Discovery | Low — users may not know to try it. Need onboarding hint on first mobile visit |
| Speed | Slower than single tap (~400-500ms hold), but acceptable for occasional lookups |

### Option B: Double-tap

| Aspect | Assessment |
|---|---|
| Familiarity | Less standard for "lookup" on iOS; double-tap usually means zoom |
| Conflict with flagging | Does not conflict (flagging is single tap) |
| Implementation | Requires tracking tap timing and suppressing the first tap's action for ~300ms, which adds latency to all taps |
| Native conflict | Double-tap-to-zoom must be disabled (via `touch-action: manipulation`) |
| Speed | Faster than long-press (~300ms total), but feels "fiddly" on small character targets |

**Verdict:** Viable but introduces tap-delay complexity and feels less natural than long-press.

### Option C: Single tap (with "lookup mode" toggle)

| Aspect | Assessment |
|---|---|
| Design | Add a second toggle button alongside the existing "flagging mode" toggle. When "lookup mode" is ON, single tap shows definition instead of cycling states |
| Familiarity | Very intuitive — tap to look up, like Pleco and other Chinese reading apps |
| Conflict with flagging | Modes are mutually exclusive: either flagging mode or lookup mode is active (or neither) |
| Speed | Fastest — immediate response on tap |
| Discovery | Toggle button is visible, more discoverable than long-press |
| Complexity | Moderate — need mode state management, clear visual indicators of which mode is active |

**Verdict:** Strong option, especially for mobile. Pleco and similar Chinese reading apps use exactly this pattern. Could be combined with long-press (long-press always works, toggle provides a fast single-tap alternative).

### Option D: Swipe-up on character

| Aspect | Assessment |
|---|---|
| Familiarity | Non-standard gesture, no iOS precedent for this |
| Implementation | Difficult to detect a short upward swipe on a 19px-wide character |
| Conflict | Could conflict with scrolling |

**Verdict:** Not recommended. Too unusual and too easy to trigger accidentally.

### Option E: Dedicated "lookup mode" toggle + long-press fallback (hybrid)

This combines options A and C:
- **Lookup mode OFF**: Long-press on any character shows the popup (always available, no mode needed)
- **Lookup mode ON**: Single tap shows the popup (fast mode for power users)
- **Flagging mode ON**: Single tap cycles states (existing behavior); long-press still shows popup

This mirrors the Pleco approach and gives users both a discoverable fast path (toggle) and a zero-setup fallback (long-press).

**Verdict:** Best of both worlds. Recommended approach.

Sources:
- [Pleco Chinese Dictionary](https://www.pleco.com/) — uses tap-to-lookup in reader mode
- [Mandarin Companion: Best Apps for Reading Chinese](https://mandarincompanion.com/6-best-apps-for-reading-chinese/)

---

## 4. Touch Event Timing

### iOS native long-press duration

Apple's `UILongPressGestureRecognizer` has a default `minimumPressDuration` of **0.5 seconds (500ms)**. This is the system-wide standard that users are trained on.

However, iOS 17 introduced a "Fast" Haptic Touch setting that reduces this to approximately **200ms**. Users who enable this setting expect faster long-press responses. Web apps cannot detect this user preference.

### Recommended duration for this use case: 400ms

| Duration | Pros | Cons |
|---|---|---|
| 200ms | Very fast, feels responsive | Too close to a normal tap; high false-positive rate, especially during scrolling |
| 300ms | Fast | Still risky for accidental triggers |
| **400ms** | **Good balance: faster than the system 500ms, clearly distinct from a tap** | **Slightly faster than iOS default — unusual** |
| 500ms | Matches iOS system default; familiar | Feels slow for a reading app where you're looking up characters frequently |
| 700ms+ | Very safe from false positives | Feels sluggish; users may release before it triggers |

**Why 400ms, not 500ms:** In a reading context, users may want to look up many characters in succession. The iOS 500ms standard is designed for actions that are less frequent (context menus, rearranging icons). A reading app benefits from a slightly shorter threshold. Pleco and similar apps use even faster tap-based lookup, suggesting users in this context want speed.

### Visual feedback during hold

Visual feedback is essential for long-press interactions. Without it, users don't know if their gesture is being recognized.

**Recommended feedback timeline:**

| Time | Feedback |
|---|---|
| 0ms (touchstart) | No immediate change — prevents flicker on normal taps and scroll-start |
| 100ms | Subtle highlight: character gets a light background color (`rgba(59, 130, 246, 0.15)`) |
| 400ms | Popup appears; highlight transitions to a stronger "selected" state |
| On dismiss | All highlights removed |

```css
@media (pointer: coarse) {
  .c.touch-active {
    background: rgba(59, 130, 246, 0.15);
    border-radius: 2px;
    transition: background 0.1s ease;
  }

  .c.touch-selected {
    background: rgba(59, 130, 246, 0.25);
    border-radius: 2px;
  }
}
```

### Haptic feedback

Web apps on iOS can trigger haptic feedback via the (non-standard but widely supported) `navigator.vibrate()` API — however, **Safari on iOS does not support `navigator.vibrate()`**. There is no reliable way to trigger haptic feedback from a web page on iOS Safari. This is a platform limitation. Native apps can use `UIImpactFeedbackGenerator`, but web apps cannot.

Sources:
- [Apple: UILongPressGestureRecognizer minimumPressDuration](https://developer.apple.com/documentation/uikit/uilongpressgesturerecognizer/minimumpressduration) — default 0.5s
- [MacRumors: Speed up Haptic Touch](https://www.macrumors.com/how-to/speed-up-haptic-touch-iphone/) — iOS 17 fast mode ~200ms
- [9to5Mac: iOS 17 fast long-press](https://9to5mac.com/2023/06/22/ios-17-fast-long-press-menu/)

---

## 5. Popup Positioning on Small Screens

### Core positioning algorithm

Use `getBoundingClientRect()` on the tapped `<span class="c">` to get its position relative to the viewport, then position the popup to avoid overflowing any edge.

```javascript
function positionPopup(popup, targetSpan) {
  const rect = targetSpan.getBoundingClientRect();
  const popupWidth = 280;   // fixed width for the popup
  const popupHeight = popup.offsetHeight || 120; // measure after content render
  const margin = 8;         // minimum distance from viewport edge
  const gap = 6;            // gap between character and popup
  const vw = window.innerWidth;
  const vh = window.innerHeight;

  // Horizontal: center on the character, clamp to viewport
  let left = rect.left + rect.width / 2 - popupWidth / 2;
  left = Math.max(margin, Math.min(left, vw - popupWidth - margin));

  // Vertical: prefer above the character
  let top = rect.top - popupHeight - gap;
  let arrowDirection = 'below'; // arrow points down toward the character

  // If not enough room above, place below
  if (top < margin) {
    top = rect.bottom + gap;
    arrowDirection = 'above'; // arrow points up toward the character
  }

  // If still not enough room (very tall popup near bottom),
  // fall back to centered overlay
  if (top + popupHeight > vh - margin) {
    top = Math.max(margin, (vh - popupHeight) / 2);
    arrowDirection = 'none';
  }

  popup.style.position = 'fixed';
  popup.style.left = `${left}px`;
  popup.style.top = `${top}px`;
  popup.style.width = `${popupWidth}px`;
  popup.dataset.arrow = arrowDirection;
}
```

### iPhone viewport dimensions (reference)

| Device | Viewport width | Viewport height (approx, Safari) |
|---|---|---|
| iPhone SE (3rd gen) | 375px | ~548px |
| iPhone 14 | 390px | ~664px |
| iPhone 14 Pro Max | 430px | ~740px |
| iPhone 15 Pro | 393px | ~659px |

### Popup width considerations

On a 375px viewport with 8px margins on each side, the maximum usable width is 359px. A popup width of **280px** leaves comfortable margins and doesn't feel cramped. Content includes:
- Character (large, centered)
- Pinyin with tone marks
- English definition (1-2 lines)
- Optional: "Flag as struggling" button

### Above vs below the character

**Prefer above** the character:
- The user's finger is below/on the character during the long press. Placing the popup above keeps it visible and not obscured by the finger.
- This matches iOS's native "Look Up" popup behavior.
- If the character is near the top of the viewport, fall back to below.

### Bottom sheet alternative

For very small screens or very long definitions, a fixed-position bottom sheet is an option:

```css
@media (pointer: coarse) {
  .char-popup.bottom-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    max-height: 40vh;
    border-radius: 12px 12px 0 0;
    padding: 1rem;
    background: #fff;
    box-shadow: 0 -2px 10px rgba(0,0,0,0.1);
    overflow-y: auto;
    z-index: 1000;
  }

  .char-popup-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0,0,0,0.3);
    z-index: 999;
  }
}
```

**Verdict:** Start with a floating tooltip-style popup (simpler, less disruptive to reading flow). Reserve bottom sheet for a future iteration if definitions become long or if the popup needs to include more interactive elements (e.g., example sentences, stroke order).

### Dismiss patterns

Multiple dismiss methods should be supported for good UX:

1. **Tap outside the popup** — most intuitive, expected on mobile
2. **Tap the X button** — explicit, accessible, small target but discoverable
3. **Tap another character** — dismiss current popup and show new one (essential for rapid lookups)
4. **Scroll** — dismiss popup when page scrolls (attaching a scroll listener while popup is visible)

**Not recommended:** Swipe-down to dismiss. This conflicts with scrolling behavior and adds complexity without clear benefit for a small popup.

### Popup HTML structure

```html
<div class="char-popup" role="tooltip" aria-label="Character definition">
  <button class="char-popup-close" aria-label="Close">&times;</button>
  <div class="char-popup-char">字</div>
  <div class="char-popup-pinyin">zì</div>
  <div class="char-popup-def">character; letter; word</div>
</div>
```

Sources:
- [Everything about positioning poppers](https://dev.to/atomiks/everything-i-know-about-positioning-poppers-tooltips-popovers-dropdowns-in-uis-3nkl)
- [MDN: getBoundingClientRect()](https://developer.mozilla.org/en-US/docs/Web/API/Element/getBoundingClientRect)
- [NN/g: Bottom Sheets UX Guidelines](https://www.nngroup.com/articles/bottom-sheet/)

---

## 6. Mobile vs Desktop Detection

### Goal

On desktop: the long-press feature is completely inert. No CSS changes, no event listeners, no interference with Zhongwen extension.

On mobile: activate long-press handling, apply `user-select: none` to `.c` spans, show lookup-related UI.

### Detection methods compared

| Method | CSS | JS | Reliability | Edge cases |
|---|---|---|---|---|
| `@media (pointer: coarse)` | Yes | Via `matchMedia` | High | Touch-enabled laptops report `any-pointer: coarse` but `pointer: fine` (primary = trackpad). This is correct behavior for our use case. |
| `'ontouchstart' in window` | No | Yes | Medium | Returns `true` on touch-enabled laptops and some desktop browsers. False positives. |
| `navigator.maxTouchPoints > 0` | No | Yes | Medium | Same false positive issue as ontouchstart. |
| `navigator.userAgent` | No | Yes | Low | Unreliable, browser-spoofable, high maintenance. |
| Viewport width `@media (max-width: 768px)` | Yes | Via `matchMedia` | Low | Desktop windows can be narrow; tablets can be wide. Tests size, not input type. |

### Recommended: `@media (pointer: coarse)` + `matchMedia` in JS

This is the best option because:

1. **`pointer: coarse` tests the primary input mechanism**, not just whether touch is available. A laptop with a touchscreen reports `pointer: fine` (trackpad is primary) and `any-pointer: coarse` (touchscreen is secondary). Using `pointer: coarse` means the feature only activates on devices where touch is the primary input — exactly what we want.

2. **Same query works in CSS and JS**, keeping behavior synchronized:

```css
/* CSS: only apply on touch-primary devices */
@media (pointer: coarse) {
  .c {
    -webkit-user-select: none;
    user-select: none;
    -webkit-touch-callout: none;
  }

  .lookup-toggle-btn {
    display: inline-block;  /* show the lookup mode toggle */
  }
}
```

```javascript
// JS: only attach touch handlers on touch-primary devices
const isTouchPrimary = window.matchMedia('(pointer: coarse)').matches;

if (isTouchPrimary) {
  initLongPressHandlers();
  initLookupModeToggle();
}
```

3. **Browser support is excellent.** `pointer` media query is supported in Safari 9+, Chrome 41+, Firefox 64+, Edge 12+. Effectively universal for any device capable of running this newsletter.

### Edge cases

**iPad with keyboard + trackpad:**
- When a Magic Keyboard is connected, iPad Safari may report `pointer: fine` as the primary pointer. This means the long-press feature would deactivate, which is actually correct — with a trackpad, the user can use the Zhongwen extension if installed, and normal selection-based lookup works.
- Without a keyboard, iPad reports `pointer: coarse` and the long-press feature activates.
- Note: `matchMedia` is evaluated at page load and does not dynamically update when input devices are connected/disconnected during a session. This is acceptable — the user can reload the page.

**Touch-enabled Windows laptops:**
- Report `pointer: fine` (trackpad/mouse is primary). Long-press feature stays inactive. Correct.
- `any-pointer: coarse` would be true, but we intentionally use `pointer` not `any-pointer` to avoid activating on these devices.

**Samsung DeX (desktop mode on phone):**
- Reports `pointer: fine` when in desktop mode with mouse. Feature stays inactive. Correct.

### Dynamic detection (optional enhancement)

For cases where input method changes during a session (e.g., detaching iPad keyboard), you can listen for changes:

```javascript
const touchQuery = window.matchMedia('(pointer: coarse)');

function handleInputChange(e) {
  if (e.matches) {
    initLongPressHandlers();
  } else {
    teardownLongPressHandlers();
  }
}

touchQuery.addEventListener('change', handleInputChange);
```

This is a nice-to-have. For the MVP, checking once at page load is sufficient.

Sources:
- [Smashing Magazine: Guide to hover and pointer media queries](https://www.smashingmagazine.com/2022/03/guide-hover-pointer-media-queries/)
- [DEV: Testing for touch devices with pointer media query](https://dev.to/cooty/a-new-way-to-test-for-touch-devices-without-javascript-enter-the-pointer-media-query-2kok)
- [CSS-Tricks: Interaction media features](https://css-tricks.com/interaction-media-features-and-their-potential-for-incorrect-assumptions/)
- [MDN: pointer media feature](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/pointer)
- [CSS { In Real Life }: Detecting hover-capable devices](https://css-irl.info/detecting-hover-capable-devices/)

---

## Recommended Approach

Based on the research above, here is the recommended implementation path.

### Architecture summary

```
Desktop (pointer: fine)          Mobile (pointer: coarse)
========================         ========================
Zhongwen extension works         Long-press → popup (always)
No CSS changes applied           Lookup mode toggle (optional fast path)
No touch handlers attached       Flagging mode toggle (existing, single tap)
Flagging mode via click          user-select: none on .c spans only
```

### Detection: `@media (pointer: coarse)` in CSS + `matchMedia` in JS

- CSS scopes `user-select: none` and `-webkit-touch-callout: none` to `.c` spans on touch-primary devices only.
- JS checks `matchMedia('(pointer: coarse)')` before attaching any touch event listeners.
- Desktop browsers are completely unaffected. Zhongwen works normally.

### Primary gesture: Long-press at 400ms

- Touch-and-hold a character for 400ms triggers the lookup popup.
- Slightly faster than the iOS default (500ms) for a better reading experience.
- Visual feedback (subtle highlight) starts at 100ms into the hold.
- Movement threshold of 10px cancels the long-press (prevents conflict with scrolling).
- Works in both flagging mode and normal mode — long-press and single-tap are distinct gestures.

### Optional enhancement: Lookup mode toggle

- A toggle button (alongside the existing flagging mode toggle) that puts the page into "lookup mode."
- In lookup mode, single tap on a character shows the popup immediately (no hold required).
- Flagging mode and lookup mode are mutually exclusive — activating one deactivates the other.
- This provides a fast path for intensive reading sessions where the user needs to look up many characters.

### Popup: Fixed-position floating tooltip

- Positioned above the character by default (below if near top of viewport).
- Width: 280px, horizontally centered on the character, clamped to viewport edges.
- Content: character (large), pinyin, English definition.
- Dismiss: tap outside, tap X button, tap another character, or scroll.
- Simple tooltip style for MVP. Bottom sheet reserved for future if needed.

### Dictionary data source (out of scope but noted)

The popup needs a dictionary to look up characters. Options to investigate separately:
- **CC-CEDICT**: Open-source Chinese-English dictionary. Can be bundled as a JSON file or loaded on demand. ~120K entries, ~4MB compressed.
- **API call**: Could call an external dictionary API, but adds latency and requires network.
- **Pre-computed in generation**: The generation pipeline (Claude Opus) already knows every character in the newsletter. It could embed a lookup table of pinyin + definitions for all characters used in the issue, directly in the HTML. This would be small (a few KB per issue) and require zero network requests.

The pre-computed approach is most aligned with the project's "no server, no dependencies" philosophy.

### Implementation priority

1. **Phase 1 (MVP):** Long-press with 400ms threshold, floating tooltip popup, `pointer: coarse` detection, pre-computed dictionary embedded in HTML by the generation pipeline.
2. **Phase 2:** Lookup mode toggle for fast single-tap lookup.
3. **Phase 3 (if needed):** Bottom sheet for longer definitions, stroke order display, example sentences.

### What NOT to do

- Do NOT apply `user-select: none` globally or outside the `@media (pointer: coarse)` query.
- Do NOT use `'ontouchstart' in window` for detection (false positives on touch laptops).
- Do NOT use viewport width as a proxy for mobile (unreliable).
- Do NOT implement double-tap (conflicts with zoom, adds tap delay, feels unnatural).
- Do NOT try to trigger haptic feedback from the web page (not supported in iOS Safari).
