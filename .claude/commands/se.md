# /se — Special Edition

You are adding a Special Edition article to today's newsletter. This is an on-demand deep-dive into a specific topic.

**Arguments:** The user provides a topic description and an optional character count after the `/se` command.

Examples:
- `/se latest change to oil prices 400`
- `/se Taiwan earthquake aftermath`
- `/se Fed rate decision market reaction 300`

If no character count is specified, default to the `article_length.target_characters` from `config/settings.json`.

---

## Step 1: Parse arguments

Extract the topic description and optional character count from `$ARGUMENTS`.

Read `config/settings.json` for the default character count.

## Step 2: Research

Dispatch a **story-researcher** agent (Sonnet) with a web search for the latest on the topic:
- Agent prompt: "Research this topic in depth. Find the most recent developments (past 24 hours if possible).\n\nTopic: {topic}\n\nProduce a detailed English briefing with key facts, quotes, context, and interesting details (200-400 words). If specific URLs are hard to find, search broadly and synthesize."

## Step 3: Write

Dispatch the **article-writer** agent (Opus) with the research briefing:
- Include only this one story
- Specify the character count target
- Agent prompt: "Write 1 article for a Special Edition insert. Target length: {char_count} characters.\n\nResearch briefing:\n{briefing}\n\nFollow the instructions in your agent definition. Output a JSON array with 1 article."

**Checkpoint:** Write `data/pipeline/articles.json`.

## Step 4: Translate

Dispatch one **translator** agent (Haiku):
- Agent prompt: "Translate this Traditional Chinese news article to natural English. Maintain paragraph structure. Output HTML <p> tags only.\n\nHeadline: {headline_plain}\n\n{body_text_plain}"

**Checkpoint:** Write `data/pipeline/translations.json`.

## Step 5: Build glossary

Follow the standard glossary pipeline:

```bash
if [ ! -f data/cedict_dictionary.json ]; then
  python3 scripts/build_dictionary.py
fi
python3 scripts/glossary_lookup.py
```

Then dispatch glossary-chars and glossary-words agents as needed (follow Steps 5.5b-5.5h from `.claude/commands/newsletter.md`).

**Checkpoint:** Write `data/pipeline/glossary.json`.

## Step 6: Insert into docs/index.html

Read the current `docs/index.html`.

### Build the SE article HTML

Using the article from `data/pipeline/articles.json` and translation from `data/pipeline/translations.json`:

```html
<article class="article se-article" data-se-id="{next_id}">
  <h2 class="article-headline">{headline_html}</h2>
  <p class="article-source">{source_label}</p>
  <div class="article-body-zh">{body_html}</div>
  <button class="translation-toggle" type="button">顯示翻譯 Show Translation</button>
  <div class="article-body-en" hidden>{translation}</div>
</article>
```

### Insert into the page

1. Look for `<div id="special-editions">` in the HTML.
2. **If it doesn't exist:** Create it. Insert after `</main>` and before the toolbar `<div class="toolbar"`:
   ```html
   <div id="special-editions">
     <h2 class="se-header">特別報導 Special Edition</h2>
     {se_article_html}
   </div>
   ```
3. **If it already exists:** Find the closing `</div>` of the special-editions container. Insert the new SE article before it. Set `data-se-id` to one more than the highest existing SE id.

### Merge glossary

Read the existing `GLOSSARY` object from the page's `<script>` block. Merge the new glossary entries (new entries override existing ones for the same key). Write the updated GLOSSARY back.

Write the modified HTML back to `docs/index.html`.

## Step 7: Validate

```bash
python3 scripts/validate.py --page-type newsletter
```

## Step 8: Commit and push

```bash
git add docs/index.html
git commit -m "Special Edition: {topic_short}"
git push
```

## Step 9: Cleanup

```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

## Summary

Print:
- SE topic and headline (Chinese + English)
- SE article position (1st, 2nd, 3rd SE of the day)
- Link: https://tamdur.github.io/chinese-learning-newsletter/
