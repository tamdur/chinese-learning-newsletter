# localStorage + Export — Research for Feedback Pipeline

How the newsletter stores feedback in the browser and exports it for the cleanup pipeline.

---

## How the Blob Download Mechanism Works

This is the approach our template already uses. Step by step:

1. **Build data** — collect character flags and Editor's Desk picks from localStorage into a JS object
2. **Serialize** — `JSON.stringify(data, null, 2)` → a JSON string
3. **Create Blob** — `new Blob([jsonString], { type: 'application/json' })` wraps the string in a file-like object with a MIME type
4. **Generate URL** — `URL.createObjectURL(blob)` creates a temporary `blob:` URL pointing to the in-memory data. Scoped to the page's origin and lifetime
5. **Create anchor** — `document.createElement('a')` — a throwaway `<a>` tag (doesn't need to be in the DOM)
6. **Set download attribute** — `a.download = 'feedback_2026-03-12.json'` tells the browser to download instead of navigate, and sets the suggested filename
7. **Programmatic click** — `a.click()` triggers the download
8. **Cleanup** — `URL.revokeObjectURL(url)` frees the memory

```javascript
function downloadJSON(data, filename) {
    const json = JSON.stringify(data, null, 2);
    const blob = new Blob([json], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    URL.revokeObjectURL(url);
}
```

### UX in Chrome on macOS

Two possible behaviors, depending on the user's Chrome settings:

1. **Default ("Ask where to save" OFF):** File auto-downloads to `~/Downloads` (or whatever Chrome is configured to use). A download chip appears at the bottom of the browser. No dialog. One click.

2. **"Ask where to save" ON (Chrome Settings → Downloads):** A native macOS save dialog appears with the filename pre-filled from the `download` attribute. The user can rename or choose a location.

Either way, the `download` attribute is fully respected for `blob:` URLs. Chrome treats `blob:` URLs as same-origin, so there are no cross-origin restrictions (those only apply to HTTP/HTTPS `<a download>` pointing to a different origin, per Chrome 65+).

### GitHub Pages Restrictions

**None.** The blob is created from in-memory data — no network request, no origin issue. HTTPS (which GitHub Pages provides) satisfies any secure-context requirements. `*.github.io` has no special download restrictions.

---

## localStorage on GitHub Pages

### Persistence

localStorage persists across:
- Page reloads ✓
- Browser restarts ✓
- New tabs/windows to the same origin ✓
- macOS reboots ✓

It does NOT persist across:
- "Clear browsing data" → "Cookies and other site data" (this deletes localStorage)
- Clearing site data for a specific site in Chrome DevTools
- Chrome incognito mode (works during session, cleared on window close)

### Storage Limit

**5 MB per origin** in Chrome. That's ~2.5 million characters of UTF-16 string data. Our feedback data is a few KB per session at most — we'll never hit this limit.

### Origin Scoping — Important Caveat

localStorage is scoped by **origin** (protocol + hostname + port), **not by path**. This means:

```
https://tamdur.github.io/chinese-learning-newsletter/   ← same localStorage
https://tamdur.github.io/some-other-project/             ← same localStorage!
```

All repos served from the same `username.github.io` domain share one localStorage pool. If you ever host another project on this GitHub Pages account, their keys could collide.

**Mitigation:** Prefix all keys with a project namespace. Our template uses `newsletter-feedback` as the key, which is specific enough. If we ever add more keys, keep the `newsletter-` prefix.

### What "Clear Browsing Data" Affects

| Chrome option | Deletes localStorage? |
|---------------|----------------------|
| Cookies and other site data | **YES** |
| Cached images and files | No |
| Browsing history | No |
| Passwords | No |
| Autofill data | No |

**Implication:** The "Export Feedback" button should be treated as the durable save. localStorage is a scratch pad. The user should export before clearing browsing data. We could add a visual reminder if there's unexported feedback.

---

## Recommended localStorage Schema

```javascript
{
    // Key: "newsletter-feedback"
    // Value:
    {
        "characters": {
            "積": "struggling",
            "膨": "struggling",
            "鏈": "learned"
            // Only flagged characters are stored.
            // "unmarked" characters are absent (delete the key).
        },
        "deskPicks": [0, 3, 5]
        // Indices into the desk-item list, in order of selection.
        // Empty array if user hasn't picked yet.
    }
}
```

This is what our template already uses. It's minimal and clean:
- Characters map directly: character → state. No timestamps in localStorage (those are added at export time).
- Desk picks are just indices, in selection order.
- No per-article data needed — the article content is in the HTML, not in localStorage.

### Export Schema (What the JSON File Contains)

```javascript
{
    "date": "2026-03-12",
    "characters": {
        "積": { "state": "struggling", "date": "2026-03-12" },
        "膨": { "state": "struggling", "date": "2026-03-12" },
        "鏈": { "state": "learned", "date": "2026-03-12" }
    },
    "editors_desk": {
        "offered": [
            { "headline": "台積電宣布在日本興建第三座晶圓廠", "included_in_issue": true },
            { "headline": "聯準會維持利率不變，暗示年底前可能降息", "included_in_issue": true },
            { "headline": "北極海冰面積創四十年來新低紀錄", "included_in_issue": true },
            { "headline": "歐盟通過新的人工智慧監管法案", "included_in_issue": false },
            { "headline": "SpaceX 星艦第五次試飛成功回收", "included_in_issue": false },
            { "headline": "日本京都百年老店的經營哲學", "included_in_issue": false }
        ],
        "user_top_3": [0, 3, 5]
    }
}
```

The export enriches the localStorage data:
- Adds the export date
- Adds timestamps to each character flag
- Reads the offered headlines from the DOM (not stored in localStorage)
- Includes which headlines were in the issue vs. excluded

The cleanup pipeline reads this file and merges into `data/flagged_characters.json` and `data/preference_history.json`.

---

## Error Handling

### Detecting localStorage Availability

```javascript
function isLocalStorageAvailable() {
    try {
        const key = '__test__';
        localStorage.setItem(key, '1');
        localStorage.removeItem(key);
        return true;
    } catch (e) {
        return false;
    }
}
```

If unavailable, the page should still be readable — just disable the flagging button and show a note. The newsletter's primary purpose is reading, not feedback.

### Guarding Against JSON Parse Errors

localStorage stores strings. If data is corrupted (manual DevTools editing, partial write from a crash), `JSON.parse` throws. Always wrap:

```javascript
function loadState() {
    try {
        const saved = localStorage.getItem(STORAGE_KEY);
        return saved ? JSON.parse(saved) : { characters: {}, deskPicks: [] };
    } catch (e) {
        // Corrupt data — reset to clean state
        localStorage.removeItem(STORAGE_KEY);
        return { characters: {}, deskPicks: [] };
    }
}
```

Our template already does this correctly.

### Guarding Against QuotaExceededError

When `setItem` exceeds 5 MB, Chrome throws `DOMException` with `name: 'QuotaExceededError'`. Extremely unlikely for our data size, but:

```javascript
function saveState(state) {
    try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify(state));
    } catch (e) {
        if (e.name === 'QuotaExceededError') {
            // Show warning — practically impossible for our data volume
            console.warn('localStorage full');
        }
    }
}
```

### Graceful Degradation Strategy

| Scenario | Behavior |
|----------|----------|
| localStorage available | Full functionality — flagging, desk picks, export |
| localStorage unavailable | Reading works. Flagging button disabled. Show small note: "回饋功能需要啟用瀏覽器儲存" |
| localStorage corrupt | Reset to clean state, continue normally |
| localStorage full | Warn user, suggest exporting and clearing |
| Export fails | Fallback: copy JSON to clipboard via `navigator.clipboard.writeText()` |

---

## Alternatives to Manual File Download

### File System Access API

`window.showSaveFilePicker()` opens a native save dialog and returns a `FileSystemFileHandle` for direct disk writes:

```javascript
async function saveDirectly(data) {
    const handle = await window.showSaveFilePicker({
        suggestedName: 'feedback_2026-03-12.json',
        types: [{ description: 'JSON', accept: { 'application/json': ['.json'] } }]
    });
    const writable = await handle.createWritable();
    await writable.write(JSON.stringify(data, null, 2));
    await writable.close();
}
```

- **Chrome on macOS:** Fully supported since Chrome 86 (Oct 2020).
- **Firefox/Safari:** Not supported. Fine for us — single user, Chrome only.
- **GitHub Pages:** Works. No origin restrictions for HTTPS pages.
- **Persistent handles:** Since Chrome 122, you can store a `FileSystemFileHandle` in IndexedDB and reuse it across sessions. With "Allow always" permission, the user could write to the same file every time without any dialog. But this adds IndexedDB complexity.

**Verdict:** Nice upgrade path for later. Not needed for MVP — the blob download is simpler and already implemented.

### Clipboard API

```javascript
async function copyToClipboard(data) {
    await navigator.clipboard.writeText(JSON.stringify(data, null, 2));
}
```

Works on GitHub Pages (HTTPS, active tab). No permission prompt in Chrome for `clipboard-write`. Could serve as a fallback if the download mechanism fails, but the UX is worse (user must paste into a file manually).

### GitHub API from Browser

Could POST a commit via the GitHub REST API with a Personal Access Token. **Ruled out** — the PAT would be visible in client-side source code. GitHub scans for and revokes exposed tokens. Only secure with a server-side proxy, which violates our "no server" constraint.

### Web Share API

`navigator.share()` opens the macOS share sheet. Not useful — adds friction compared to a direct download, and the user would need to figure out where the shared file went.

---

## Recommendation for MVP

**Stick with the blob download approach.** It's already implemented in our template, works perfectly on GitHub Pages in Chrome, and requires zero additional infrastructure. The user clicks "匯出回饋 Export Feedback", the JSON file appears in their Downloads folder, and they run the cleanup pipeline pointing at that file.

One small improvement to consider: after export, show a confirmation message on the page so the user knows it worked. Our current template doesn't provide visual confirmation — the only signal is the Chrome download chip.

### Post-MVP Upgrade Path

If the manual "find the downloaded file" step becomes annoying:
1. **File System Access API** — let the user pick a save location once, then reuse the handle. Each export writes directly to the chosen file with no dialog.
2. **Auto-clear localStorage after successful export** — with a confirmation prompt, so the next reading session starts clean.

---

## Sources

- [MDN: Blob](https://developer.mozilla.org/en-US/docs/Web/API/Blob)
- [MDN: URL.createObjectURL](https://developer.mozilla.org/en-US/docs/Web/API/URL/createObjectURL_static)
- [MDN: Window.localStorage](https://developer.mozilla.org/en-US/docs/Web/API/Window/localStorage)
- [MDN: Using the Web Storage API (detection pattern)](https://developer.mozilla.org/en-US/docs/Web/API/Web_Storage_API/Using_the_Web_Storage_API)
- [Chrome Developers: File System Access API](https://developer.chrome.com/docs/capabilities/web-apis/file-system-access)
- [Chrome Developers: Persistent permissions for File System Access](https://developer.chrome.com/blog/persistent-permissions-for-the-file-system-access-api)
- [Chrome Status: Block cross-origin `<a download>`](https://chromestatus.com/feature/4969697975992320)
- [GitHub Pages localStorage scoping](https://github.com/TomasHubelbauer/github-pages-local-storage)
