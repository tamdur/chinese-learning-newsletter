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

## Step 2: Research and write

Dispatch the **article-writer** agent (Opus) with the topic. The article-writer has WebFetch and WebSearch tools and handles its own research.

- Include only this one story
- Specify the character count target
- Agent prompt: "Write 1 article for a Special Edition insert. Target length: {char_count} characters.\n\nTopic: {topic}\nInstructions: Search the web for the latest developments on this topic (past 24 hours if possible). Fetch the best source you find. Then write the article directly from what you learn.\n\nFollow the instructions in your agent definition. Output a JSON array with 1 article."

**Checkpoint:** Write `data/pipeline/articles.json`.

## Step 3: Translate

Dispatch one **translator** agent (Haiku):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

**Checkpoint:** Write `data/pipeline/translations.json`.

## Step 4: Build glossary

**4a. Dictionary pre-match:**

```bash
python3 scripts/glossary_lookup.py
```

(This also builds the CEDICT dictionary on first run if missing.)

**4b. Agent word lookup:**

Dispatch a **glossary-words** agent (Sonnet) with the article plain text. The agent must return raw JSON only (no markdown fences). Write the agent's JSON response to `data/pipeline/glossary_agent_words.json` using the Write tool.

**4c. Merge and validate:**

```bash
python3 scripts/glossary_merge.py
```

This merges dictionary pre-match + agent entries, validates zhuyin (Bopomofo only), and writes `data/pipeline/glossary.json`.

## Step 5: Insert into docs/index.html

```bash
python3 scripts/insert_se.py
```

This script reads checkpoint files from `data/pipeline/`, builds the SE HTML, inserts it into `docs/index.html` (creating the special-editions container if needed), and merges the new glossary into the existing GLOSSARY object.

## Step 6: Validate

```bash
python3 scripts/validate.py --page-type newsletter
```

## Step 7: Commit and push

```bash
git add docs/index.html
git commit -m "Special Edition: {topic_short}"
git push
```

## Step 8: Cleanup

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- SE topic and headline (Chinese + English)
- SE article position (1st, 2nd, 3rd SE of the day)
- Link: https://tamdur.github.io/chinese-learning-newsletter/
