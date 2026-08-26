# /newsletter — Newsletter Pipeline

You are running the newsletter pipeline. This generates today's issue of 今日讀報.

All intermediate results are checkpointed to `data/pipeline/`. If a previous run was interrupted, check for existing checkpoint files and resume from where it left off (see Step 0).

---

## Generation

This phase uses the subagent architecture. Execute these steps in order. After each step, **checkpoint results to `data/pipeline/`** using the Write tool.

### Step 0: Sync working tree with origin/main

The cloud Routine's VM may retain working-tree state across runs. If
the previous run's MCP push completed but the volume kept stale local
files (or the previous push left a partial state), the next run will
build against that stale state and the resulting archive will skip
days. Always start from a clean origin/main.

Run as **separate Bash calls** (not chained with `&&`):

```bash
git checkout main
```
```bash
git fetch origin main
```
```bash
git pull --rebase origin main
```

If `git pull` reports merge conflicts, stop the pipeline and surface
the error.

### Step 0a: Determine today's date in Chicago time

**Do not trust the injected `# currentDate` for `{today}`.** Cloud schedulers may run in UTC, which can put the orchestrator on a different calendar day than Chicago. Compute the authoritative date once, here, and reuse it for every downstream `{today}` substitution (scout prompts, selected.json date field, assemble.py --date, commit messages, archive filenames):

```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d'))"
```

Use the stdout of this command — and only this command — as the value of `{today}` for the rest of the pipeline. Same for `{current_hour}` if needed:

```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/Chicago')).strftime('%H'))"
```

### Step 0b: Check for existing checkpoints (resume support)

Check if `data/pipeline/` exists and contains checkpoint files. If it does:

1. Read `data/pipeline/selected.json` (if it exists) and check its date field
2. If the date matches today: resume from the latest checkpoint
   - If `glossary.json` exists → skip to Step 6
   - If `translations.json` exists but not `glossary.json` → skip to Step 5.5
   - If `articles.json` exists but not `translations.json` → skip to Step 5
   - If `selected.json` exists but not `articles.json` → skip to Step 4
   - If `candidates.json` exists but not `selected.json` → skip to Step 3
3. If the date does NOT match today: delete all files in `data/pipeline/` and start fresh

If `data/pipeline/` doesn't exist, create it and start from Step 1.

### Step 1: Read config files

Read these files directly in this session:
- `config/settings.json` — reading level, article count, title
- `config/interests.json` — topics, source hints, selection guidance

### Step 2: Dispatch five scout agents in parallel

Launch all five simultaneously using the Agent tool:

1. **news-scout-hn** (Haiku): Fetch HN front page via Algolia API. No input needed.
   - Agent prompt: "Fetch the Hacker News front page stories via the Algolia API. Follow the instructions in your agent definition."

2. **news-scout-rss** (Haiku): Fetch Marginal Revolution, MLB Cubs, and Arsenal FC RSS feeds. No input needed.
   - Agent prompt: "Fetch and parse RSS feeds for Marginal Revolution, MLB Cubs, and Arsenal FC. Follow the instructions in your agent definition."

3. **news-scout-web** (Sonnet): The Economist desk — AI, economics, world, business, ideas. Pass today's date.
   - Agent prompt: "Today's date is {today}. Run 4-6 targeted web searches as the Economist desk. Lead beat: transformative AI. Also cover global economics/finance, international affairs, business & industry, and science/ideas. Sports and Chicago local are covered by other desks. Return results as a JSON array. Follow the instructions in your agent definition."

4. **news-scout-national** (Sonnet): National & Chicago desk — US policy, Chicago/Illinois. Pass today's date.
   - Agent prompt: "Today's date is {today}. Run 2-3 web searches for US governance/policy and Chicago/Illinois local news. Sports are covered by the sports desk. Return results as a JSON array. Follow the instructions in your agent definition."

5. **news-scout-sports** (Sonnet): Sports desk — Cubs/Bulls/Bears, Michigan, Arsenal. Pass today's date.
   - Agent prompt: "Today's date is {today}. Run 3-4 web searches for Chicago sports (Cubs/Bulls/Bears — whichever in season), Michigan football or basketball, and Arsenal FC. Return results as a JSON array. Follow the instructions in your agent definition."

Wait for all five to return.

**Checkpoint:** Write combined candidate list to `data/pipeline/candidates.json`.

### Step 3: Combine results and dispatch story-selector

Merge results from all five scouts into a single candidate list. Launch the **story-selector** agent (Opus):
- Pass the full combined candidate list as context, prefixed with today's date and approximate time
- The agent will read `config/interests.json` and `data/newsletter_topic_ledger.json` (its semantic memory of which topics/angles the paper already covered — used to reject same-story-different-day repeats)
- Agent prompt: "Today is {today}, approximately {current_hour}:00 Chicago time. Here are the candidate stories from today's news scouts:\n\n{combined_candidates}\n\nSelect 6 stories for today's newsletter. Follow the instructions in your agent definition."

**Checkpoint:** Write `data/pipeline/selected.json` — the selector's full output (6 selected stories + rationale), with a `"date": "{today}"` field added at the top level. Each selected story now carries `topic` and `angle` fields (in addition to `summary`/`new_development`); these are logged to the topic ledger in Step 7.

### Step 4: Dispatch article-writer

Dispatch the **article-writer** agent (Opus). The agent reads `data/pipeline/selected.json` itself, fetches sources via WebFetch/WebSearch, and writes its output directly to `data/pipeline/articles.json`. It returns only a short manifest as text — do not expect the article HTML in the agent response.

- Agent prompt: "Write today's articles. Selected stories are in `data/pipeline/selected.json`. Follow the instructions in your agent definition."

**Verify checkpoint:** After the agent returns, confirm `data/pipeline/articles.json` exists and contains a JSON array of 6 entries (each with `headline_html`, `body_html`, `headline_plain`, `source_label`). If missing or malformed, re-dispatch once.

**Why this pattern:** Large structured artifacts are written by the producing agent and read back by the orchestrator. This avoids streaming a large tool result and a large follow-up `Write` call in the same orchestrator turn — both of which can trip stream idle timeouts on the cloud harness. Apply the same pattern to any future agent whose output exceeds a few KB.

### Step 5: Dispatch 6 translators in parallel

Launch all 6 agents simultaneously:

**6 translators** (Haiku): For each of the 6 articles, launch a **translator** agent with the plain Chinese text (headline_plain + body text with span tags stripped):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All 6 run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/translations.json` — array of 6 HTML translation strings.

### Step 5.5: Build and validate glossary

This step keeps the orchestrator's tool-call payloads small: every agent writes its own output file, and a Python script does the merge/validation. The orchestrator never holds the merged glossary in-context.

**5.5a. Ensure CEDICT dictionary exists, then run dictionary pre-match**

```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
python3 scripts/glossary_lookup.py
```

This writes `data/pipeline/glossary_matched.json` (dictionary-resolved entries) and `data/pipeline/glossary_unresolved.txt` (characters needing agent lookup).

If `build_dictionary.py` fails (network error), fall back: skip 5.5a and treat ALL article characters as unresolved in 5.5b, with an empty `glossary_matched.json`.

**5.5b. Dispatch glossary-chars agents for unresolved characters**

Read `data/pipeline/glossary_unresolved.txt`. If empty, skip to 5.5c.

Chunk into batches of 25 characters. For each batch index `i` (starting at 1), dispatch one `glossary-chars` agent in parallel. Each agent prompt MUST include the OUTPUT_PATH:

> "CHARACTER_LIST:\n{characters}\n\nTEXT:\n{plain_text}\n\nOUTPUT_PATH: data/pipeline/glossary_chars_b{i}.tsv"

The agent writes its TSV directly to that unique path and returns a one-line manifest. The orchestrator does NOT need to capture or parse the TSV — the merge script reads it from disk.

**5.5c. Dispatch glossary-words agents (ALWAYS run, in parallel with 5.5b)**

Even when the dictionary resolves all single characters, CEDICT definitions are often too generic for proper nouns, transliterated names, and context-specific compounds. Always dispatch.

Two parallel agents (or 6 if no CEDICT):
- Agent 1 → `data/pipeline/glossary_words_b1.json` for articles 1-3 plain text
- Agent 2 → `data/pipeline/glossary_words_b2.json` for articles 4-6 plain text

Each prompt MUST include the OUTPUT_PATH:

> "Be aggressive about coverage — include ALL proper nouns (especially transliterated names), ALL compound words, ALL technical terms. More entries is always better than fewer. When in doubt, include it.\n\nTEXT:\n{article_plain_text}\n\nOUTPUT_PATH: data/pipeline/glossary_words_b{i}.json"

Each agent writes its JSON directly to that unique path and returns a one-line manifest.

**5.5d. Merge and validate**

```bash
python3 scripts/glossary_merge.py
```

This script reads `glossary_matched.json` + every `glossary_chars_*.tsv` + every `glossary_words_*.json`, applies override order (dictionary < chars-agent < words-agent), drops entries with non-Bopomofo zhuyin, checks completeness against `articles.json`, and writes `data/pipeline/glossary.json` plus `data/pipeline/glossary_missing.txt`.

**5.5e. Remediation (up to 3 passes)**

Read `data/pipeline/glossary_missing.txt`. If non-empty:

1. Chunk the missing characters into batches of 25.
2. Dispatch fresh `glossary-chars` agents, each writing to a NEW unique path (e.g. `glossary_chars_r1_b1.tsv` for the first remediation round, batch 1) so prior batch outputs are preserved.
3. Re-run `python3 scripts/glossary_merge.py`.
4. Repeat up to 3 remediation rounds total.

After 3 rounds, accept any remaining missing characters and continue — the script's stdout reports the count.

**5.5f. Verify checkpoint**

Confirm `data/pipeline/glossary.json` exists and contains entries. Note any chars from `glossary_missing.txt` for the run summary.

### Step 5.7: Update the topic ledger

Append today's stories to the topic ledger so tomorrow's selector remembers what
angles ran today:

```bash
python3 scripts/ledger_update.py
```

This reads `data/pipeline/selected.json` (topic/angle per story) and
`data/pipeline/articles.json` (Chinese headlines) and appends to the committed
`data/newsletter_topic_ledger.json`. It is idempotent per date (safe on re-runs)
and trims to the last ~30 days. The assembler stages this file in Step 6's
commit, so it lands on origin atomically with the issue in Step 6.5 — if the
push fails, the ledger isn't published either, keeping ledger and site in sync.

### Step 6: Dispatch validator

Launch the **assembler** agent (Sonnet) — this is now a validation agent, not a content generator:
- Agent prompt: "Today's date is {today}. Run assembly and validation per your agent definition. All checkpoint files are in data/pipeline/."
- The agent runs `python3 scripts/assemble.py --page-type newsletter --date {today}` and `python3 scripts/validate.py --page-type newsletter`
- It handles any validation failures by re-dispatching sub-agents as needed
- It commits (but does NOT push — the orchestrator handles that)

### Step 6.5: Push via MCP (chunked + verified)

The cloud Routine uses `mcp__github__push_files` because the git proxy
returns HTTP 403 on push. A single push call has been observed to
silently drop the largest files when the commit includes many or
large files (the orchestrator exceeds its per-turn budget while
reading file contents). The fix: push in small groups with explicit
verification.

1. **Plan the push.** Run:
   ```bash
   python3 scripts/push_planner.py
   ```
   The script reads `git diff --name-only HEAD~1`, sizes each file,
   and prints a JSON plan with one or more `groups`, each ≤25 KB.
   Read the plan output.

2. **Push each group as a SEPARATE `mcp__github__push_files` call.**
   Do NOT try to push everything in one call. For each group in order:
   - Read every file in the group via the Read tool
   - Call `mcp__github__push_files` with just that group's files
   - Use commit message "Newsletter {today}" for every group (a single
     run will produce one commit per group on origin/main; that is
     expected and acceptable — better than dropped files)
   - Wait for the call to return successfully before starting the
     next group

3. **Verify.** After the last group, run the plan's `verify_cmd`:
   ```bash
   git fetch origin main && git diff origin/main..HEAD --name-only
   ```
   Output MUST be empty. Any line is a file that did not land on
   origin/main. Re-push each missing file in its own MCP call, then
   re-verify.

4. **Sync local.** Once verification is clean:
   ```bash
   git fetch origin main
   git checkout main
   git pull --rebase origin main
   ```

5. If MCP push fails repeatedly, fall back to `git push origin HEAD:main`
   — this publishes the current commits straight to the Pages branch.
   Do NOT use plain `git push`: in an unattended cloud session the
   checkout may be on a `claude/*` working branch, and plain `git push`
   would strand the day's commits off `main`, where GitHub Pages can't
   see them (this is exactly what happened on 2026-07-03). After the
   fallback, verify with `git log --oneline -1 origin/main` that
   origin/main shows today's date. Report any error so the user can
   investigate; do NOT generate top-up commits (that's what produced the
   broken 2026-05-10 state).

### Step 7: Cleanup checkpoints

After successful push, delete checkpoint files:
```bash
rm -f data/pipeline/*.json data/pipeline/*.txt data/pipeline/*.tsv
```

---

## Summary

Print a summary:

- The 6 selected story headlines (in Chinese with English titles)
- Any warnings from assembly or validation
- **Link:** https://tamdur.github.io/chinese-learning-newsletter/
