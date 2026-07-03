# /se — Special Edition

You are adding a Special Edition article to today's newsletter. This is an on-demand deep-dive into a specific topic.

**Arguments:** The user provides a topic description and an optional character count after the `/se` command.

Examples:
- `/se latest change to oil prices 400`
- `/se Taiwan earthquake aftermath`
- `/se Fed rate decision market reaction 300`

If no character count is specified, default to the `article_length.target_characters` from `config/settings.json`.

## Shell conventions

**CRITICAL:** All Bash commands MUST use relative paths from the project root. The working directory is already the project root. NEVER prefix commands with `cd` — doing so breaks the auto-approval permission patterns. Use dedicated tools (Grep, Glob, Read) instead of bash grep/find/cat.

---

## Step 1: Parse arguments

Extract the topic description and optional character count from `$ARGUMENTS`.

Read `config/settings.json` for the default character count.

## Step 1.5: Ensure main branch and build dependencies

The SE must be committed to main so GitHub Pages publishes it immediately. Cloud environments may start on a feature branch — switch to main first.

Run these as **separate Bash calls** (not chained with `&&`):

```bash
git checkout main
```
```bash
git pull origin main
```

Create the pipeline directory if needed:

```bash
mkdir -p data/pipeline
```

Ensure the CEDICT dictionary exists (it's in .gitignore and won't be present in fresh cloud environments). The script is idempotent — it skips if the file already exists:

```bash
python3 scripts/build_dictionary.py
```

## Step 2: Research and write

Dispatch the **article-writer** agent (Opus). The agent has WebFetch and WebSearch tools for research.

Agent prompt — use this EXACTLY, substituting only `{char_count}` and `{topic}`:

```
Write 1 Special Edition article in Traditional Chinese about this topic.

Topic: {topic}
Target length: {char_count} characters of Chinese body text.

Instructions:
1. Use WebSearch to find the latest developments on this topic (past 24 hours if possible).
2. Use WebFetch on the best source you find.
3. Write the article from what you learn.

Reading level: Grade 4 Taiwanese elementary school. Common characters, straightforward grammar. Traditional Chinese (繁體中文) only.

Tone: A knowledgeable friend explaining the news over coffee. Casual but informed.

CRITICAL OUTPUT FORMAT — you MUST return exactly this JSON structure:

[
  {
    "article_id": 1,
    "headline_html": "<headline with each CJK char wrapped in <span class=\"c\"> tags>",
    "body_html": "<p><span class=\"c\">每</span><span class=\"c\">個</span>Chinese chars wrapped...</p>",
    "headline_plain": "The headline in plain text, no HTML tags",
    "source_label": "來源：Source Name"
  }
]

Every Chinese character (including punctuation like 。，、「」：；！？（）) in headline_html, body_html, and source_label MUST be individually wrapped in <span class="c"> tags. English text, numbers, and HTML tags are NOT wrapped.

Example wrapping: <span class="c">油</span><span class="c">價</span><span class="c">飆</span><span class="c">升</span>

Return ONLY the JSON array. No markdown fences. No explanation before or after.
```

**Checkpoint:** Write the agent's response to `data/pipeline/articles.json`.

## Step 3: Translate

Strip `<span class="c">` tags from `body_html` and `headline_plain` to get plain Chinese text. Dispatch one **translator** agent (Haiku):

Agent prompt:
```
Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output ONLY the HTML — <p> tags only, no markdown fences, no other text.

Headline: {headline_plain}

{body_text_plain}
```

**Checkpoint:** Write `data/pipeline/translations.json` — a JSON array with 1 string element (the HTML translation).

Format: `["<p>English translation...</p><p>Second paragraph...</p>"]`

IMPORTANT: If the translator returns a JSON object (e.g., `{"body_en": "..."}`) instead of a plain string, extract the string value. The checkpoint MUST be an array of strings, not an array of objects.

## Step 4: Build glossary

**4a. Dictionary pre-match:**

```bash
python3 scripts/glossary_lookup.py
```

**4b. Agent word lookup:**

Strip `<span class="c">` tags from headline and body to get plain text. Dispatch a **glossary-words** agent (Sonnet):

Agent prompt:
```
Be aggressive about coverage — include ALL proper nouns (especially transliterated names), ALL compound words, ALL technical terms. More entries is always better than fewer. When in doubt, include it.

TEXT:
{article_plain_text}
```

The agent MUST return a JSON **object** (NOT an array) where each key is a Chinese word and each value has "zhuyin" and "english" fields:

```json
{"台積電": {"zhuyin": "ㄊㄞˊ ㄐㄧ ㄉㄧㄢˋ", "english": "TSMC"}}
```

Write the agent's response to `data/pipeline/glossary_agent_words.json` using the Write tool.

IMPORTANT: If the agent returns an array like `[{"word": "X", "zhuyin": "Y", "english": "Z"}]`, convert it to dict format before writing: `{"X": {"zhuyin": "Y", "english": "Z"}}`.

**4c. Merge and validate:**

```bash
python3 scripts/glossary_merge.py
```

This merges dictionary pre-match + agent entries, validates zhuyin (Bopomofo only), and writes `data/pipeline/glossary.json`.

## Step 5: Insert into docs/index.html

```bash
python3 scripts/insert_se.py
```

This script reads checkpoint files from `data/pipeline/`, normalizes field names if needed, builds the SE HTML, inserts it into `docs/index.html` (creating the special-editions container if needed), and merges the new glossary into the existing GLOSSARY object.

## Step 6: Validate

```bash
python3 scripts/validate.py --page-type newsletter
```

## Step 7: Commit and push

Run these as **separate Bash calls** (each must complete before the next):

```bash
git add docs/index.html
```
```bash
git commit -m "Special Edition: {topic_short}"
```
```bash
git push origin HEAD:main
```

The explicit `HEAD:main` ensures the push targets the Pages branch (`main`) regardless of what branch the session is checked out on. In an unattended cloud session the working branch may be a `claude/*` branch; a plain `git push` (or even `git push origin main` while off `main`) would strand the commit where GitHub Pages can't see it.

## Step 8: Cleanup

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- SE topic and headline (Chinese + English)
- SE article position (1st, 2nd, 3rd SE of the day)
- Link: https://tamdur.github.io/chinese-learning-newsletter/
