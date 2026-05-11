# 2026-05-10 — Stability Fix (v2, post re-diagnosis)

Earlier draft assumed the pipeline had been failing since 2026-04-14
because I was operating on a stale local working tree. Discarded.
The real failure mode is on the 2026-05-09 MCP push refactor — the
cron has been running daily; what broke is *which files get pushed*.

## Symptoms on the live site (origin/main HEAD = 8b6189d)

- `docs/index.html` declares `data-prev="archive/2026-05-08.html"` but
  `docs/archive/2026-05-08.html` is missing → back link 404s.
- `docs/index.html` declares `GLOSSARY_URL="glossary/newsletter-2026-05-10.json"`
  but `docs/glossary/newsletter-2026-05-10.json` is missing → fetch
  fails → mobile lookup never has data → every long-press shows
  "(not in glossary)".
- Same two failures on `docs/wisdom.html`.
- `docs/obsessions.html` is intact (its glossary made it through a
  retry, its archive made it through another retry).
- Latent CSS bug: `.lookup-toggle { display: none; }` follows the
  `@media (pointer: coarse)` block in `docs/shared.css`, so even with
  a working glossary the mobile lookup-mode button is hidden.

## What the May 10 commit series tells us

```
09200d0 Newsletter 2026-05-10        3 files (index, shared.css, shared.js)
fa4268a Daily Wisdom 2026-05-10      4 files (wisdom_progress, css/js, wisdom)
fda01dd Daily Wisdom ... archives    1 file (archive/wisdom/2026-05-07.html)
1aa5302 Daily Wisdom 2026-05-10      3 files (wisdom_progress, ..-05-07.html, wisdom)
17e858e Obsessions 2026-05-10        1 file (obsessions.html)
9877e09 Obsessions ... headline+...  1 file (headline_log)
8b6189d Obsessions ... glossary+arch 2 files (archive/obsessions/05-08.html, glossary)
```

Each pipeline made multiple commits within minutes of each other,
each carrying a subset of the files the pipeline actually produced.
This is the orchestrator retrying — the MCP push was leaving files
on the floor and the orchestrator was generating top-up commits.

The files that consistently went missing are the **biggest**:
yesterday's archive HTML (~60 KB) and today's glossary JSON
(30–60 KB). Smaller files (shared.css 4 KB, index.html 25 KB,
wisdom_progress.json 1 KB) made it through every time.

That points at the MCP push step: it reads each file via the `Read`
tool, then passes the contents into a single `mcp__github__push_files`
call. By the time the orchestrator gets to the 5th or 6th file,
it has eaten enough context budget that the larger files are the
first to be dropped.

## Fixes

### Fix 1 — CSS rule order

One-line move in `templates/_shared.css`. Then `docs/shared.css`
gets the same edit so the live pages are corrected immediately.
Future `assemble.py` runs already overwrite `docs/shared.css` from
the template, so the template fix carries forward.

### Fix 2 — restore the missing live-site files (data repair)

The 5/8 newsletter and wisdom archives are missing on origin/main
even though they were produced on 5/8 and lived in `docs/index.html`
/ `docs/wisdom.html` until 5/10 archived them. Extract them from
the 5/8 commits and write to disk:

- `git show 37cebce:docs/index.html` → fix_paths_for_archive →
  `docs/archive/2026-05-08.html`
- `git show 94d060d:docs/wisdom.html` → fix_paths_for_archive →
  `docs/archive/wisdom/2026-05-08.html`

Then walk the nav chain to make sure 5/7 → 5/8 → live-index is
linked correctly for both page types.

The missing glossary files (`newsletter-2026-05-10.json` and
`wisdom-2026-05-10.json`) cannot be regenerated faithfully without
re-running the agent pipeline (we don't have `articles.json`).
Closest substitute: extract every wrapped character from the live
`docs/index.html` / `docs/wisdom.html` and run them through
`scripts/glossary_lookup.py` against the cached CEDICT dictionary.
That gives us a working glossary for single-character lookups
(~70-90% of what a fully-agent-built glossary covers — every char,
just thinner multi-word definitions).

Each of these is a one-shot Python helper: simple, reviewable,
diff is small.

### Fix 3 — harden the MCP push step

This is the structural change. Current Step 6.5 (newsletter) /
Step 8 (wisdom) / Step 9 (obsessions) all read the file list,
read every file, and push in one call. Replace with:

1. List changed files via `git diff --name-only HEAD~1`.
2. Push files in **deterministic groups**, in dependency order, so
   that even a partial failure leaves the chain self-consistent:
   - Group A: shared assets that other files reference (shared.css,
     shared.js)
   - Group B: per-issue files (glossary, archive of yesterday)
   - Group C: the live index file
   This way, if Group C succeeds but Group B fails, the live page
   exists but has broken refs → at least we can see what's missing
   in a single verification call instead of silently dropping.
3. After each MCP call, run `git fetch origin main` and compare the
   pushed file's hash against `origin/main` to verify it landed.
4. If a file isn't on origin/main after one retry, halt and report
   the missing files explicitly. Better to leave a broken state
   that the next run can detect and rebuild than to keep generating
   ghost top-up commits.

A small helper script (`scripts/mcp_push.py`) encapsulates the
list/group/verify logic. The commands' push step becomes:
`python3 scripts/mcp_push.py --message "Newsletter {today}"` plus
the orchestrator handling the actual MCP tool calls (since only the
orchestrator session has the MCP tools). The script generates a
push manifest the orchestrator iterates through.

### Fix 4 — assemble.py defends against incomplete prior runs

If the cloud VM clones origin/main and finds that `docs/index.html`
references an archive file that doesn't exist (current state), the
next run's `archive_old_issue` will still archive whatever's in
`docs/index.html` — but the chain it produces will still skip the
missing dates. Add a startup self-check: when assemble.py runs, if
the live index points to an archive that's missing on disk, log a
warning. (No automatic repair — that risks compounding errors;
just surfaces the gap.)

## Out of scope

- No changes to scout/selector/writer/translator agents.
- No model swaps.
- No automated scheduling change.
- The mass nav-chain rewrite from the previous (mis-rooted) plan —
  the current chain on origin/main is mostly fine except the 5/8
  gap, which Fix 2 closes.
- Pre-shared-template archive pages (March pre-3/27) are not
  rewritten.

## Test plan

1. Apply Fix 1; diff `templates/_shared.css` and `docs/shared.css`
   shows only the rule move.
2. Apply Fix 2; verify `docs/archive/2026-05-08.html` and
   `docs/archive/wisdom/2026-05-08.html` exist and that
   `docs/index.html` / `docs/wisdom.html` `data-prev` resolves.
3. Apply Fix 2 glossary regen; verify `docs/glossary/newsletter-2026-05-10.json`
   and `docs/glossary/wisdom-2026-05-10.json` are non-empty.
4. `python3 scripts/validate.py --page-type newsletter` (and
   `wisdom`, `obsessions`) — all PASS.
5. Manual: open `docs/index.html` in a browser, mobile viewport,
   long-press a Chinese character → popup shows zhuyin + def.
6. Push via MCP per the same flow the cloud Routine uses (helper
   script). Verify origin/main contains every file.
7. Trigger or wait for the next /go run. Confirm 5/11 commits
   include every changed file in one commit (no top-up).
