# /wisdom — Daily Wisdom Pipeline

You are running the Daily Wisdom pipeline. This generates today's 每日智慧 page with Heart Sutra, Mengzi, and Zen passages.

All intermediate results are checkpointed to `data/pipeline/`.

---

## Step 1: Read config and check idempotency

Read these files:
- `config/settings.json` — reading level, timezone
- `config/wisdom.json` — source configurations for each section
- `data/wisdom_progress.json` — Mengzi and Zen progress tracking

**Idempotency check:** If `wisdom_progress.json` shows `last_served_date` matches today for BOTH Mengzi and Zen, AND `docs/wisdom.html` exists, skip generation entirely. Print "Wisdom page already generated for today." and stop.

## Step 2: Select today's content

Determine today's date in America/Chicago timezone.

For each enabled section in `config/wisdom.json`:

1. **Heart Sutra:** Read `data/sources/heart_sutra.json`. Select the segment matching today's day-of-week (Monday=0, Tuesday=1, ..., Sunday=6).

2. **Mengzi:** Read `data/sources/mengzi_passages.json`. Select the passage at `next_passage_index` from `wisdom_progress.json`. If the index exceeds the total passages, wrap around to 0.

3. **Zen:** Read `data/sources/zen_passages.json`. Select the passage at `next_passage_index` from `wisdom_progress.json`. If the index exceeds the total passages, wrap around to 0.

## Step 3: Wrap Chinese text in character spans

For each content unit's Chinese text, wrap every CJK character in `<span class="c">` tags. This can be done with a simple Python script or inline:

```python
import re
def wrap_chars(text):
    """Wrap each CJK character in <span class="c"> tags."""
    return re.sub(r'([\u4e00-\u9fff\u3400-\u4dbf\uf900-\ufaff，。、「」：；！？（）—])',
                  r'<span class="c">\1</span>', text)
```

Build content units in the same schema as newsletter articles:
```json
[
  {
    "headline_html": "<span class=\"c\">般</span><span class=\"c\">若</span>...",
    "body_html": "<p><span class=\"c\">觀</span>...</p>",
    "headline_plain": "般若波羅蜜多心經 — Heart Sutra — Monday",
    "source_label": ""
  }
]
```

Write to `data/pipeline/articles.json` (same filename the glossary pipeline expects).

## Step 4: Translations

For each content unit, check if a cached English translation exists in the source file (the `translation` or `translation_en` field). If it does, use it directly.

If no cached translation exists, dispatch a **translator-classical** agent:
- Agent prompt: "Translate this classical Chinese text to clear, modern English.\n\nText:\n{chinese_text}\n\nContext: {context_string}"

Write all translations to `data/pipeline/translations.json`.

## Step 5: Build glossary

Follow the same glossary pipeline as the newsletter:

**5a. Ensure CEDICT dictionary exists, then run dictionary pre-match:**
```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
python3 scripts/glossary_lookup.py
```

**5b-5h.** Follow the same glossary-chars and glossary-words agent dispatch, merge, validate, and remediate steps as documented in `.claude/commands/newsletter.md` (Steps 5.5b through 5.5h).

**Checkpoint:** Write `data/pipeline/glossary.json`.

## Step 6: Assemble and validate

```bash
python3 scripts/assemble.py --page-type wisdom --date {today}
python3 scripts/validate.py --page-type wisdom
```

Handle any validation failures.

## Step 7: Update progress

Update `data/wisdom_progress.json`:
- Increment `mengzi.next_passage_index` by 1 (wrap to 0 if past end)
- Increment `zen.next_passage_index` by 1 (wrap to 0 if past end)
- Set `mengzi.last_served_date` and `zen.last_served_date` to today's date

## Step 8: Commit and push

```bash
git add docs/wisdom.html data/wisdom_progress.json
git commit -m "Daily Wisdom {today}"
git push
```

## Step 9: Cleanup checkpoints

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- Heart Sutra: which day-of-week segment was served
- Mengzi: which passage index and chapter
- Zen: which passage index
- Link: https://tamdur.github.io/chinese-learning-newsletter/wisdom.html
