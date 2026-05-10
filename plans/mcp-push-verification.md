# MCP Push Verification Plan

## Context

On 2026-05-09, the git proxy in the Claude Code web environment started returning HTTP 403 on push operations. All content generation worked, but nothing could be deployed to GitHub Pages.

### Root cause
The Anthropic API backend rejected `git-receive-pack` requests for this session. The local proxy faithfully forwarded the request — the 403 came from `api.anthropic.com` (confirmed via `GIT_CURL_VERBOSE=1`). This may be session credential expiration or a transient backend issue.

### Fix implemented
Refactored `assemble.py` to externalize CSS, JS, and glossary from HTML pages:

- **Before:** Each HTML page was 55-110KB (inlined CSS + JS + glossary JSON). Too large for MCP `push_files` tool (which requires reading file content into the LLM context, limited to ~25K tokens per file read).
- **After:** HTML pages are 2-25KB. CSS → `docs/shared.css`, JS → `docs/shared.js`, glossary → `docs/glossary/{type}-{date}.json`. All files now small enough to read and push via MCP.
- **Backward compatible:** Old archive pages with inline glossary still work via JS fallback in `_shared.js`.

### Files changed (all pushed to GitHub via MCP)
1. `scripts/assemble.py` — write external assets, generate `<link>` and `<script src>` references
2. `scripts/validate.py` — accept external CSS/JS/glossary references in validation checks
3. `templates/_shared.js` — async glossary fetch with inline fallback for legacy archives
4. `.claude/agents/assembler.md` — updated `git add` pattern, removed push responsibility
5. `.claude/commands/newsletter.md` — added Step 6.5 (MCP push by orchestrator)
6. `.claude/commands/wisdom.md` — updated commit/push step for MCP
7. `.claude/commands/obsessions.md` — updated commit/push step for MCP

### What still needs verification

## Verification Steps

### 1. Run `/go` in a fresh session

Run the full daily pipeline. The key things to watch for:

- **Assembly:** Does `assemble.py` produce small HTML files (~2-25KB) with `<link>` and `<script src>` tags instead of inline CSS/JS/glossary?
- **Validation:** Does `validate.py` pass with the new external file format?
- **MCP Push:** Does the orchestrator successfully push all generated files via `mcp__github__push_files`?
- **Archive handling:** When the old (inline) pages get archived, do they retain their inline format? Do new archive pages get external references with correct relative paths?

### 2. Check the live site

After the pipeline completes, verify:
- https://tamdur.github.io/chinese-learning-newsletter/ loads and renders correctly
- Chinese text is readable, translation toggles work
- Mobile glossary popup works (glossary loads async from `glossary/*.json`)
- CSS loads from `shared.css` (check Network tab — no 404s)

### 3. Verify archive backward compatibility

Navigate to an older archive page (e.g., `archive/2026-05-08.html`). It should still work with its inline glossary via the `window.GLOSSARY` fallback in `shared.js`.

## Potential Issues

1. **Glossary JSON too large for MCP push:** If a newsletter has 500+ glossary entries, the compacted JSON could be 30-60KB. This should still be readable (~12-24K tokens) but is borderline. If push fails, the glossary may need to be split or further compacted.

2. **Archive path rewriting:** The `fix_paths_for_archive()` function rewrites `href="shared.css"` to `href="../shared.css"` (or `../../shared.css`). If an archive page was created from a page that already had inline CSS (pre-refactor), the rewrite has no effect (no `shared.css` link to rewrite). This is correct behavior.

3. **First run after refactor:** The existing `docs/index.html`, `docs/wisdom.html`, and `docs/obsessions.html` on GitHub are still in the old inline format. The first `/go` run will archive them (preserving their inline format) and replace them with new small-format pages.
