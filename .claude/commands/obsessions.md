# /obsessions — Obsessions Culture Desk Pipeline

You are running the Obsessions pipeline. This generates today's 深度專題 page with web-searched content for each active obsession.

All intermediate results are checkpointed to `data/pipeline/`.

---

## Step 0: Determine today's date in Chicago time

**Do not trust the injected `# currentDate` for `{today}`.** Cloud schedulers may run in UTC, which can put the orchestrator on a different calendar day than Chicago. Compute the authoritative date once, here, and reuse for every downstream substitution (scout prompts, headline log entries, assemble.py --date, commit messages):

```bash
python3 -c "from datetime import datetime; from zoneinfo import ZoneInfo; print(datetime.now(ZoneInfo('America/Chicago')).strftime('%Y-%m-%d'))"
```

Use the stdout — and only this — as the value of `{today}` for the rest of the pipeline.

## Step 1: Read config, headline log, and source files

Read these files:
- `config/settings.json` — reading level, timezone
- `config/obsessions.json` — editorial voice and obsession definitions
- `data/obsessions_headline_log.json` — running log of all past headlines (for dedup)

For any obsession whose `guidance` references a persistent source file (e.g., `data/sources/internet_gems_sources.json`), read that file too. Its contents will be passed to the scout as `sources_context`.

Filter for active obsessions only (`"active": true`). If no obsessions are active, print "No active obsessions — skipping." and stop.

## Step 2: Build dedup context

From the headline log, collect the last 10 headlines **per obsession** (not just globally). Format them as a list for the scouts, including the `topic` field for semantic dedup:

```
Recent coverage for "Interesting Taiwanese Music, Past and Present":
- 2026-03-28: topic=dark electronic music — 鬼島之聲：台灣電子音樂的黑暗面
- 2026-03-27: topic=field recording and sound art — 林強的聲音世界：用台灣的聲音畫一幅畫

Recent coverage for "Discovering Finland for March 2027 Honeymoon":
- 2026-03-28: topic=sauna culture — 芬蘭的公共三溫暖：下班後的新去處
- 2026-03-27: topic=sauna culture — 煙燻桑拿：芬蘭最古老的溫暖

Do NOT cover any topic already listed above. Find a genuinely different facet of this obsession.
```

When formatting recent headlines, use the `topic` field if present. If an entry has no `topic` field, format it as `topic=untagged` and include the headline as usual.

## Step 2.5: Generate entropy tokens

Generate one random entropy token per active obsession to inject serendipity into all scouts. Run:

```bash
python3 -c "
import json, random, time
random.seed(int(time.time()))
with open('data/sources/entropy_tokens.json') as f:
    tokens = json.load(f)['tokens']
n = {number_of_active_obsessions}
picks = random.sample(tokens, n)
for p in picks:
    print(p)
"
```

Save the output as a list of `{entropy_tokens}`, one per obsession in the same order as the active obsessions list.

## Step 3: Dispatch scouts in parallel

For each active obsession, launch an **obsessions-scout** agent (Sonnet):
- Pass the obsession's `label`, `guidance`, **that obsession's** recent headlines, and its entropy token
- If a source file was loaded for this obsession in Step 1, pass its `sources` array as `sources_context`. Otherwise pass `sources_context` as "None — use standard search."
- Agent prompt: "Find a specific, interesting story for this obsession.\n\nLabel: {label}\nGuidance: {guidance}\n\nRecent headlines to avoid:\n{recent_headlines}\n\nKnown sources:\n{sources_context}\n\nEntropy token: {entropy_token} — Let this word nudge your searching in an unexpected direction. Don't search for the word literally; let it guide your associations.\n\nFollow the instructions in your agent definition."

All scouts run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/candidates.json` — array of scouted stories.

**Source file update:** After all scouts return, check each result for a `new_source` field. If present and non-null, append the new source entry to the appropriate source file (e.g., `data/sources/internet_gems_sources.json`). This grows the source list over time.

## Step 4: Dispatch obsessions-writer

Dispatch the **obsessions-writer** agent (Opus). The agent reads `data/pipeline/candidates.json` and `config/obsessions.json` itself, and writes its output directly to `data/pipeline/articles.json`. It returns only a short manifest as text.

- Agent prompt: "Write today's Obsessions articles. Scouted stories are in `data/pipeline/candidates.json`. Follow the instructions in your agent definition."

**Verify checkpoint:** After the agent returns, confirm `data/pipeline/articles.json` exists and contains a JSON array with one entry per successfully scouted story (each with `headline_html`, `body_html`, `headline_plain`, `source_label`, `obsession_id`). If missing or malformed, re-dispatch once.

## Step 5: Dispatch translators in parallel

For each article in `articles.json`, extract the plain Chinese body text by stripping all HTML tags from `body_html` (remove `<span class="c">`, `</span>`, `<p>`, `</p>` etc., leaving only the Chinese characters and punctuation).

Then launch a **translator** agent (Haiku) for each article:
- Agent prompt: "Translate this Traditional Chinese article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All translators run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/translations.json` — an array of HTML strings, one per article. Each entry is the translator's raw HTML output (e.g., `"<p>First paragraph...</p><p>Second paragraph...</p>"`). Do NOT wrap these in objects — the array entries must be plain strings, not dicts.

## Step 6: Build glossary

Follow the same glossary pipeline as the newsletter:

**6a. Ensure CEDICT dictionary exists, then run dictionary pre-match:**
```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
python3 scripts/glossary_lookup.py
```

**6b-6f.** Follow the same glossary-chars and glossary-words agent dispatch, merge script, and remediation steps as documented in `.claude/commands/newsletter.md` (Steps 5.5b through 5.5f). All agents write their own output files to `data/pipeline/`; the merge script writes `glossary.json`.

## Step 7: Assemble and validate

```bash
python3 scripts/assemble.py --page-type obsessions --date {today}
python3 scripts/validate.py --page-type obsessions
```

Handle any validation failures.

## Step 8: Update headline log

Append today's headlines to `data/obsessions_headline_log.json`. For each article produced, add:
```json
{
  "date": "{today}",
  "obsession_id": "{obsession_id from article}",
  "headline": "{headline_plain}",
  "headline_en": "{brief English description}",
  "topic": "{2-4 word English topic label}"
}
```

Generate the `topic` field inline by identifying the article's core subject in 2-4 words (e.g., "sauna culture", "Finnish design", "Taiwanese hip-hop"). This does not need an agent call.

## Step 9: Commit and push

```bash
git add docs/obsessions.html data/obsessions_headline_log.json data/sources/internet_gems_sources.json
git commit -m "Obsessions {today}"
git push
```

## Step 10: Cleanup checkpoints

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- Which obsessions were covered (label + headline)
- Any obsessions that failed scouting
- Link: https://tamdur.github.io/chinese-learning-newsletter/obsessions.html
