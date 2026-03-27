# /go — Daily Newsletter Pipeline

You are running the daily newsletter pipeline. This has two phases: cleanup (process feedback) then generation (produce today's issue).

All intermediate results are checkpointed to `data/pipeline/`. If a previous run was interrupted, check for existing checkpoint files and resume from where it left off (see Step 0).

---

## Phase 1: Cleanup

### 1a. Scan for feedback files

Look for files matching the glob pattern `feedback_*.json` in `~/Downloads/`. Sort any matches by the date in the filename (ascending — oldest first).

- **No files found:** Print "No feedback to process — skipping cleanup." and go straight to Phase 2.
- **One or more files found:** Process each one in chronological order (steps 1b–1d), then commit (step 1e).

### 1b. Merge character flags

Read `data/flagged_characters.json`. For each character in the feedback file's `characters` object:

- **`"struggling"`**: Add or update the entry. Set `"state": "struggling"`, `"last_updated"` to the feedback date. If new, also set `"first_flagged"` to the feedback date.
- **`"learned"`**: Update the entry. Set `"state": "learned"`, `"last_updated"` to the feedback date. Keep existing `"first_flagged"`. If new, set `"first_flagged"` to the feedback date.
- **`"unmarked"`**: Remove the character from `flagged_characters.json` entirely — it's no longer tracked.
- **Character absent from feedback**: No change. Absence means "no update", not "remove".

When processing multiple feedback files, apply them in order. Later files override earlier ones for the same character.

### 1c. Append to preference history

Read `data/preference_history.json`. Append a new entry to the `sessions` array:

```json
{
  "date": "<feedback date>",
  "offered": [<the offered array from the feedback>],
  "user_top_3": [<the user_top_3 array from the feedback>]
}
```

If a session with the same date already exists, skip it (don't double-append).

### 1d. Delete the processed feedback file

After successfully merging, delete the feedback file from `~/Downloads/`. This prevents reprocessing on the next run.

### 1e. Commit and push cleanup changes

After ALL feedback files are processed:

```
git add data/flagged_characters.json data/preference_history.json
git commit -m "Cleanup: merge feedback"
git push
```

Only commit if there are actual changes to data files.

---

## Phase 2: Generation

This phase uses the subagent architecture. Execute these steps in order. After each step, **checkpoint results to `data/pipeline/`** using the Write tool.

### Step 0: Check for existing checkpoints (resume support)

Check if `data/pipeline/` exists and contains checkpoint files. If it does:

1. Read `data/pipeline/selected.json` (if it exists) and check its date field
2. If the date matches today: resume from the latest checkpoint
   - If `glossary.json` exists → skip to Step 6
   - If `translations.json` exists but not `glossary.json` → skip to Step 5.5
   - If `articles.json` exists but not `translations.json` → skip to Step 5
   - If `briefings.json` exists but not `articles.json` → skip to Step 4
   - If `selected.json` exists but not `briefings.json` → skip to Step 3.5
   - If `candidates.json` exists but not `selected.json` → skip to Step 3
3. If the date does NOT match today: delete all files in `data/pipeline/` and start fresh

If `data/pipeline/` doesn't exist, create it and start from Step 1.

### Step 1: Read config and data files

Read these files directly in this session:
- `config/settings.json` — reading level, article count, title
- `config/interests.json` — topics, source hints, selection guidance
- `data/flagged_characters.json` — characters the user is struggling with or has learned
- `data/preference_history.json` — past Editor's Desk picks

### Step 2: Dispatch four scout agents in parallel

Launch all four simultaneously using the Agent tool:

1. **news-scout-hn** (Haiku): Fetch HN front page via Algolia API. No input needed.
   - Agent prompt: "Fetch the Hacker News front page stories via the Algolia API. Follow the instructions in your agent definition."

2. **news-scout-rss** (Haiku): Fetch Marginal Revolution, Carbon Brief, MLB Cubs RSS feeds. No input needed.
   - Agent prompt: "Fetch and parse RSS feeds for Marginal Revolution, Carbon Brief, and MLB Cubs. Follow the instructions in your agent definition."

3. **news-scout-web** (Sonnet): Run targeted web searches. Pass today's date.
   - Agent prompt: "Today's date is {today}. Run 4-6 targeted web searches to find current news stories. The user's core interests: generative AI/AGI, economics/finance, Michigan sports, Cubs baseball. Also find 1-2 serendipitous stories (niche-interesting, not mainstream trending — water cooler stories are covered by the national scout). Return results as a JSON array. Follow the instructions in your agent definition."

4. **news-scout-national** (Sonnet): Run web searches for national politics, Chicago local news, and water cooler stories. Pass today's date.
   - Agent prompt: "Today's date is {today}. Run 3-4 web searches for US national/political news (policy changes, legislation, court rulings, agency decisions), Chicago local news (city council, transit, public safety), and big water-cooler stories everyone is talking about. Return results as a JSON array. Follow the instructions in your agent definition."

Wait for all four to return.

**Checkpoint:** Write combined candidate list to `data/pipeline/candidates.json`.

### Step 3: Combine results and dispatch story-selector

Merge results from all four scouts into a single candidate list. Launch the **story-selector** agent (Opus):
- Pass the full combined candidate list as context
- The agent will read `config/interests.json`, `data/preference_history.json`, and check `docs/archive/` for recent issues
- Agent prompt: "Here are the candidate stories from today's news scouts:\n\n{combined_candidates}\n\nSelect 5 stories for today's newsletter and 3 runner-up headlines for the Editor's Desk. Follow the instructions in your agent definition."

**Checkpoint:** Write two files:
- `data/pipeline/selected.json` — the selector's full output (5 selected stories + rationale), with a `"date": "{today}"` field added at the top level
- `data/pipeline/desk_headlines.json` — array of 8 headlines for the Editor's Desk:
  - First 5: the selected stories' headlines with `"included_in_issue": true`
  - Last 3: the runner-up headlines with `"included_in_issue": false`
  - Each entry has `"headline_zh"` (the Chinese headline — these come from the article-writer in Step 4, so for now use the English headline as a placeholder; update after Step 4)

### Step 3.5: Dispatch 5 story-researcher agents in parallel

For each of the 5 selected stories, launch a **story-researcher** agent (Sonnet):
- Pass the story's URL, title, source, and the selector's summary
- Agent prompt: "Research this story in depth.\n\nURL: {url}\nTitle: {title}\nSource: {source}\nSummary: {summary}\n\nFetch the full article and produce a detailed English briefing with key facts, quotes, context, and interesting details (200-400 words). If the URL is inaccessible, search for alternative sources. Follow the instructions in your agent definition."

All 5 run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/briefings.json` — array of 5 briefing objects keyed by article index (0-4).

### Step 4: Dispatch article-writer

Pass the 5 selected stories to the **article-writer** agent (Opus):
- Include the **detailed research briefings from Step 3.5** (NOT the selector's thin summaries)
- The agent will read `config/settings.json` and `data/flagged_characters.json`
- Agent prompt: "Write all 5 articles for today's newsletter. Here are the selected stories with detailed research briefings:\n\n{stories_with_briefings}\n\nFollow the instructions in your agent definition."

**Checkpoint:** Write `data/pipeline/articles.json` — the article-writer's JSON array output (each entry has `headline_html`, `body_html`, `headline_plain`, `source_label`).

**Update desk_headlines.json:** Now that we have the Chinese headlines from the article-writer, update the first 5 entries in `data/pipeline/desk_headlines.json` to use `headline_plain` from the articles as their `headline_zh`. The 3 runner-up headlines need Chinese translations — ask the story-selector's output for the Chinese headlines it provided, or use the English headlines if Chinese wasn't provided.

### Step 5: Dispatch 5 translators in parallel

Launch all 5 agents simultaneously:

**5 translators** (Haiku): For each of the 5 articles, launch a **translator** agent with the plain Chinese text (headline_plain + body text with span tags stripped):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All 5 run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/translations.json` — array of 5 HTML translation strings.

### Step 5.5: Build and validate glossary

The main session handles glossary building. This step uses a dictionary pre-match to minimize agent calls.

**5.5a. Run dictionary pre-match**

```bash
python3 scripts/glossary_lookup.py
```

This script:
1. Reads `data/pipeline/articles.json`
2. Extracts all unique Chinese characters
3. Looks up each against `data/cedict_dictionary.json`
4. Performs longest-match word scanning against the dictionary
5. Writes `data/pipeline/glossary_matched.json` (resolved entries) and `data/pipeline/glossary_unresolved.txt` (characters needing agent lookup)

If `data/cedict_dictionary.json` doesn't exist, print a warning and fall back to the full agent-based approach (steps 5.5b-5.5c below with ALL characters).

**5.5b. Dispatch single-character glossary agents for unresolved characters**

Read `data/pipeline/glossary_unresolved.txt`. If empty, skip to 5.5d.

Chunk unresolved characters into batches of 25. Dispatch parallel `glossary-chars` agent calls.

Each agent gets:
- CHARACTER_LIST: 25 characters (one per line)
- TEXT: concatenated plain text from all 5 articles (for pronunciation context)
- Agent prompt: "CHARACTER_LIST:\n{characters}\n\nTEXT:\n{plain_text}"

Each agent returns TSV (not JSON). **Convert TSV to JSON programmatically:**

```bash
echo "{agent_response}" | python3 -c "
import json, sys
glossary = {}
for line in sys.stdin:
    parts = line.strip().split('\t')
    if len(parts) == 3:
        glossary[parts[0]] = {'zhuyin': parts[1], 'english': parts[2]}
    else:
        if line.strip():
            print(f'WARN: bad line: {line.strip()}', file=sys.stderr)
print(json.dumps(glossary, ensure_ascii=False))
"
```

**5.5c. Dispatch multi-character word agents**

If using dictionary pre-match: dispatch `glossary-words` agents only for articles that have proper nouns or technical terms not covered by the dictionary. In practice, dispatch 2-3 agents for articles with the most specialized vocabulary.

If NOT using dictionary pre-match (fallback): dispatch 5 parallel `glossary-words` agent calls, one per article's full plain text.
- Agent prompt: "Be aggressive about coverage — include ALL proper nouns (especially transliterated names), ALL compound words, ALL technical terms. More entries is always better than fewer. When in doubt, include it.\n\nTEXT:\n{article_plain_text}"

Parse each JSON response. Merge all (later overwrites earlier for duplicates).

**5.5d. Merge all glossary sources**

Combine:
1. Dictionary pre-matched entries (`glossary_matched.json`)
2. Agent single-char entries (from 5.5b)
3. Agent multi-char word entries (from 5.5c)

Agent entries override dictionary entries for the same key (agents have article context for better definitions).

**5.5e. Validate zhuyin format**

Check every entry's "zhuyin" value contains Bopomofo characters (Unicode U+3100-U+312F: ㄅㄆㄇㄈ etc.), NOT romanized pinyin (Latin characters). Discard entries with pinyin; add their characters to the missing list.

**5.5f. Validate completeness**

Check that every unique character from the articles has a single-character key in the merged glossary. Collect missing characters.

**5.5g. Remediation (up to 3 passes)**

If missing characters exist:
1. Dispatch another round of `glossary-chars` agents (still in batches of 25)
2. Convert TSV programmatically, validate zhuyin, merge
3. Repeat up to 3 total remediation passes

**5.5h. Log stats and checkpoint**

Print: total entries, single-char entries, multi-char entries, dictionary-matched entries, agent-resolved entries, missing characters (if any after 3 passes).

**Checkpoint:** Write `data/pipeline/glossary.json` — the final merged glossary object.

### Step 6: Dispatch validator

Launch the **assembler** agent (Sonnet) — this is now a validation agent, not a content generator:
- Agent prompt: "Today's date is {today}. Run assembly and validation per your agent definition. All checkpoint files are in data/pipeline/."
- The agent runs `python3 scripts/assemble.py --date {today}` and `python3 scripts/validate.py`
- It handles any validation failures by re-dispatching sub-agents as needed
- It commits and pushes the result

### Step 7: Cleanup checkpoints

After successful commit, delete checkpoint files:
```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

---

## Phase 3: Summary

Print a combined summary:

- **Cleanup:** How many feedback files processed, new/changed character states, or "No feedback processed"
- **Generation:** The 5 selected story headlines (in Chinese with English titles), the 3 runner-up headlines, any warnings
- **Link:** https://tamdur.github.io/chinese-learning-newsletter/
