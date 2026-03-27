# /obsessions — Obsessions Culture Desk Pipeline

You are running the Obsessions pipeline. This generates today's 深度專題 page with web-searched content for each active obsession.

All intermediate results are checkpointed to `data/pipeline/`.

---

## Step 1: Read config

Read these files:
- `config/settings.json` — reading level, timezone
- `config/obsessions.json` — editorial voice and obsession definitions

Filter for active obsessions only (`"active": true`). If no obsessions are active, print "No active obsessions — skipping." and stop.

## Step 2: Check recent archives for dedup

List files in `docs/archive/obsessions/` (last 3-5 issues). For each recent issue, read it and extract headlines. Collect these as "recent headlines" to pass to scouts for dedup.

## Step 3: Dispatch scouts in parallel

For each active obsession, launch an **obsessions-scout** agent (Sonnet):
- Pass the obsession's `label`, `guidance`, and recent headlines
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

## Step 8: Commit and push

```bash
git add docs/obsessions.html
git commit -m "Obsessions {today}"
git push
```

## Step 9: Cleanup checkpoints

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- Which obsessions were covered (label + headline)
- Any obsessions that failed scouting
- Link: https://tamdur.github.io/chinese-learning-newsletter/obsessions.html
