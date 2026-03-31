# /newsletter — Newsletter Pipeline

You are running the newsletter pipeline. This generates today's issue of 今日讀報.

All intermediate results are checkpointed to `data/pipeline/`. If a previous run was interrupted, check for existing checkpoint files and resume from where it left off (see Step 0).

---

## Generation

This phase uses the subagent architecture. Execute these steps in order. After each step, **checkpoint results to `data/pipeline/`** using the Write tool.

### Step 0: Check for existing checkpoints (resume support)

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
- The agent will read `config/interests.json` and check `docs/archive/` for recent issues
- Agent prompt: "Today is {today}, approximately {current_hour}:00 Chicago time. Here are the candidate stories from today's news scouts:\n\n{combined_candidates}\n\nSelect 6 stories for today's newsletter. Follow the instructions in your agent definition."

**Checkpoint:** Write `data/pipeline/selected.json` — the selector's full output (6 selected stories + rationale), with a `"date": "{today}"` field added at the top level.

### Step 4: Dispatch article-writer

Pass the 6 selected stories to the **article-writer** agent (Opus):
- Include for each story: `title`, `url`, `source`, `summary`, `new_development`
- The agent will fetch the sources itself using WebFetch/WebSearch
- Agent prompt: "Write all 6 articles for today's newsletter. Here are the selected stories:\n\n{stories_with_urls_and_summaries}\n\nFollow the instructions in your agent definition."

**Checkpoint:** Write `data/pipeline/articles.json` — the article-writer's JSON array output (each entry has `headline_html`, `body_html`, `headline_plain`, `source_label`).

### Step 5: Dispatch 6 translators in parallel

Launch all 6 agents simultaneously:

**6 translators** (Haiku): For each of the 6 articles, launch a **translator** agent with the plain Chinese text (headline_plain + body text with span tags stripped):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All 6 run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/translations.json` — array of 6 HTML translation strings.

### Step 5.5: Build and validate glossary

The main session handles glossary building. This step uses a dictionary pre-match to minimize agent calls.

**5.5a. Ensure CEDICT dictionary exists, then run dictionary pre-match**

First, check if the CEDICT dictionary exists. If not, build it (this happens on first run in cloud environments since the file is in .gitignore):

```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
```

Then run the pre-match:

```bash
python3 scripts/glossary_lookup.py
```

This script:
1. Reads `data/pipeline/articles.json`
2. Extracts all unique Chinese characters
3. Looks up each against `data/cedict_dictionary.json`
4. Performs longest-match word scanning against the dictionary
5. Writes `data/pipeline/glossary_matched.json` (resolved entries) and `data/pipeline/glossary_unresolved.txt` (characters needing agent lookup)

If `build_dictionary.py` fails (e.g., network error downloading CEDICT), fall back to the full agent-based approach (steps 5.5b-5.5c below with ALL characters).

**5.5b. Dispatch single-character glossary agents for unresolved characters**

Read `data/pipeline/glossary_unresolved.txt`. If empty, skip to 5.5d.

Chunk unresolved characters into batches of 25. Dispatch parallel `glossary-chars` agent calls.

Each agent gets:
- CHARACTER_LIST: 25 characters (one per line)
- TEXT: concatenated plain text from all 6 articles (for pronunciation context)
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

**5.5c. Dispatch multi-character word agents (ALWAYS run)**

Even when the dictionary resolves all single characters, CEDICT definitions are often too generic for proper nouns, transliterated names, and context-specific compound words. Always dispatch glossary-words agents to supplement the dictionary.

Batch articles into 2 parallel `glossary-words` agent calls to keep agent count low while ensuring full coverage:
- Agent 1: articles 1-3 concatenated plain text
- Agent 2: articles 4-6 concatenated plain text

Each agent prompt: "Be aggressive about coverage — include ALL proper nouns (especially transliterated names), ALL compound words, ALL technical terms. More entries is always better than fewer. When in doubt, include it.\n\nTEXT:\n{article_plain_text}"

If NOT using dictionary pre-match (fallback, no CEDICT file): dispatch 6 parallel agents instead (one per article).

Parse each JSON response. Merge all (later overwrites earlier for duplicates). Agent word entries override dictionary entries for the same key, since agents have article context for better definitions of proper nouns and specialized terms.

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
- The agent runs `python3 scripts/assemble.py --page-type newsletter --date {today}` and `python3 scripts/validate.py --page-type newsletter`
- It handles any validation failures by re-dispatching sub-agents as needed
- It commits and pushes the result

### Step 7: Cleanup checkpoints

After successful commit, delete checkpoint files:
```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

---

## Summary

Print a summary:

- The 6 selected story headlines (in Chinese with English titles)
- Any warnings from assembly or validation
- **Link:** https://tamdur.github.io/chinese-learning-newsletter/
