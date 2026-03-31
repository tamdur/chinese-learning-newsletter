# /obsessions — Obsessions Culture Desk Pipeline

You are running the Obsessions pipeline. This generates today's 深度專題 page with web-searched content for each active obsession.

All intermediate results are checkpointed to `data/pipeline/`.

---

## Step 1: Read config and headline log

Read these files:
- `config/settings.json` — reading level, timezone
- `config/obsessions.json` — editorial voice and obsession definitions
- `data/obsessions_headline_log.json` — running log of all past headlines (for dedup)

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

## Step 3: Dispatch scouts in parallel

For each active obsession, launch an **obsessions-scout** agent (Sonnet):
- Pass the obsession's `label`, `guidance`, and **that obsession's** recent headlines
- Agent prompt: "Find a specific, interesting story for this obsession.\n\nLabel: {label}\nGuidance: {guidance}\n\nRecent headlines to avoid:\n{recent_headlines}\n\nFollow the instructions in your agent definition."

All scouts run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/candidates.json` — array of scouted stories.

## Step 4: Dispatch obsessions-writer

Pass all successfully scouted stories to the **obsessions-writer** agent (Opus):
- Include the editorial voice from `config/obsessions.json`
- Agent prompt: "Write articles for today's Obsessions page. Here are the scouted stories:\n\n{scouted_stories}\n\nFollow the instructions in your agent definition."

**Checkpoint:** Write `data/pipeline/articles.json` — the writer's JSON array output.

## Step 5: Dispatch translators in parallel

For each content unit, launch a **translator** agent (Haiku):
- Agent prompt: "Translate this Traditional Chinese article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

All translators run concurrently. Wait for all to return.

**Checkpoint:** Write `data/pipeline/translations.json`.

## Step 6: Build glossary

Follow the same glossary pipeline as the newsletter:

**6a. Ensure CEDICT dictionary exists, then run dictionary pre-match:**
```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
python3 scripts/glossary_lookup.py
```

**6b-6h.** Follow the same glossary-chars and glossary-words agent dispatch, merge, validate, and remediate steps as documented in `.claude/commands/newsletter.md` (Steps 5.5b through 5.5h).

**Checkpoint:** Write `data/pipeline/glossary.json`.

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
git add docs/obsessions.html data/obsessions_headline_log.json
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
