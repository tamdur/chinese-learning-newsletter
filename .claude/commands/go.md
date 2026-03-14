# /go — Daily Newsletter Pipeline

You are running the daily newsletter pipeline. This has two phases: cleanup (process feedback) then generation (produce today's issue).

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

This phase uses the subagent architecture. Execute these steps in order.

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

### Step 3: Combine results and dispatch story-selector

Merge results from all three scouts into a single candidate list. Launch the **story-selector** agent (Opus):
- Pass the full combined candidate list as context
- The agent will read `config/interests.json`, `data/preference_history.json`, and check `docs/archive/` for recent issues
- Agent prompt: "Here are the candidate stories from today's news scouts:\n\n{combined_candidates}\n\nSelect 5 stories for today's newsletter and 3 runner-up headlines for the Editor's Desk. Follow the instructions in your agent definition."

### Step 3.5: Dispatch 5 story-researcher agents in parallel

For each of the 5 selected stories, launch a **story-researcher** agent (Sonnet):
- Pass the story's URL, title, source, and the selector's summary
- Agent prompt: "Research this story in depth.\n\nURL: {url}\nTitle: {title}\nSource: {source}\nSummary: {summary}\n\nFetch the full article and produce a detailed English briefing with key facts, quotes, context, and interesting details (200-400 words). If the URL is inaccessible, search for alternative sources. Follow the instructions in your agent definition."

All 5 run concurrently. Wait for all to return.

### Step 4: Dispatch article-writer

Pass the 5 selected stories to the **article-writer** agent (Opus):
- Include the **detailed research briefings from Step 3.5** (NOT the selector's thin summaries)
- The agent will read `config/settings.json` and `data/flagged_characters.json`
- Agent prompt: "Write all 5 articles for today's newsletter. Here are the selected stories with detailed research briefings:\n\n{stories_with_briefings}\n\nFollow the instructions in your agent definition."

### Step 5: Dispatch 5 translators in parallel

Launch all 5 agents simultaneously:

**5 translators** (Haiku): For each of the 5 articles, launch a **translator** agent with the plain Chinese text (headline_plain + body text with span tags stripped):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All 5 run concurrently. Wait for all to return.

### Step 5.5: Build and validate glossary

The main session handles glossary building directly. Do NOT delegate this to the assembler.

**5.5a. Extract and deduplicate characters**

Strip `<span class="c">` tags from all 5 articles' `headline_html` + `body_html` to get plain Chinese text. Collect ALL unique Chinese characters across all articles (exclude punctuation: ，。「」！？、：（）). Expected: ~200-250 unique characters.

**5.5b. Dispatch single-character glossary agents (batches of 25)**

Chunk the deduplicated character set into batches of 25-30 characters. At ~200-250 unique chars, this is 8-10 parallel `glossary-chars` agent calls.

Each agent gets:
- CHARACTER_LIST: 25 characters (one per line)
- TEXT: concatenated plain text from all 5 articles (for pronunciation context)
- Agent prompt: "CHARACTER_LIST:\n{characters}\n\nTEXT:\n{plain_text}"

Each agent returns TSV (not JSON). **Convert TSV to JSON programmatically** — write the agent's response to a temp file and parse with:

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

Bad lines are logged and their characters added to the missing list.

**5.5c. Dispatch multi-character word agents (one per article)**

5 parallel `glossary-words` agent calls, one per article's full plain text.
- Agent prompt: "TEXT:\n{article_plain_text}"

Parse each JSON response. Merge all 5 (later overwrites earlier for duplicates).

**5.5d. Merge single-char and multi-char glossaries**

Combine into one object. Both types of entries coexist — the `findLongestMatch()` function in the newsletter JS handles precedence at lookup time.

**5.5e. Validate zhuyin format**

Check every entry's "zhuyin" value contains Bopomofo characters (Unicode U+3100-U+312F: ㄅㄆㄇㄈ etc.), NOT romanized pinyin (Latin characters). Discard entries with pinyin; add their characters to the missing list.

**5.5f. Validate completeness**

Check that every unique character from 5.5a has a single-character key in the merged glossary. Collect missing characters.

**5.5g. Remediation (up to 3 passes)**

If missing characters exist:
1. Dispatch another round of `glossary-chars` agents (still in batches of 25)
2. Convert TSV programmatically, validate zhuyin, merge
3. Repeat up to 3 total remediation passes

With 25-char batches, pass 1 should catch nearly everything; pass 2 guarantees it.

**5.5h. Log stats**

Print: total entries, single-char entries, multi-char entries, missing characters (if any after 3 passes). Pass the validated glossary JSON object to the assembler.

### Step 6: Dispatch assembler

Pass all content to the **assembler** agent (Sonnet):
- 5 articles (headline HTML, body HTML, source labels)
- 5 English translations
- 8 Editor's Desk headlines (5 selected with Chinese headlines from article-writer + 3 runners-up with Chinese headlines from story-selector)
- Validated glossary JSON object (from Step 5.5)
- Today's date
- Agent prompt: include all content pieces and instruct it to follow its agent definition

The assembler receives the pre-built, validated glossary and embeds it directly. It does NOT build the glossary itself.

### Step 7: Done

---

## Phase 3: Summary

Print a combined summary:

- **Cleanup:** How many feedback files processed, new/changed character states, or "No feedback processed"
- **Generation:** The 5 selected story headlines (in Chinese with English titles), the 3 runner-up headlines, any warnings
- **Link:** https://tamdur.github.io/chinese-learning-newsletter/
