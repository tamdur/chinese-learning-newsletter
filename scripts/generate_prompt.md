# Generation Pipeline

## Overview

This document describes the steps to generate a daily newsletter issue. Run these in a Claude Code session.

## Steps

### 1. Read configuration and data files

Read these files to understand current settings and user state:

- `config/settings.json` — reading level, article count, title
- `config/interests.json` — topics, source hints, selection guidance
- `data/flagged_characters.json` — characters the user is struggling with or has learned
- `data/preference_history.json` — past Editor's Desk picks (what stories the user preferred)
- `templates/newsletter.html` — reference HTML for the output format

### 2. Search for today's news

Use web search to find current English-language news stories. Search across the topics defined in `interests.json`, using source hints as guidance. Also search for 1-2 serendipitous stories outside core topics.

Aim for 8+ candidate stories to select from.

### 3. Select stories

Choose 5 stories for the issue and 3 runner-up headlines for the Editor's Desk section.

Selection criteria:
- Follow the `selection_note` in `interests.json`
- Variety across topics (but don't force every topic)
- Lead with the genuinely most interesting story
- Consider `preference_history.json` — what kinds of stories has the user favored?
- Include 1-2 stories that a curious generalist would enjoy

### 4. Write the articles in Traditional Chinese

For each of the 5 selected stories:
- Rewrite in Traditional Chinese (繁體中文) — never simplified characters
- Follow the reading level description in `settings.json` (currently grade 5)
- Use the conversational tone: knowledgeable friend over coffee, not textbook or news anchor
- Naturally increase frequency of characters listed as "struggling" in `flagged_characters.json` — weave them into the text in varied contexts
- Gloss difficult characters in parentheses on first use when needed
- Each article: 2-4 paragraphs, ~150-300 characters

### 5. Write English translations

For each article, write a natural English translation for the toggle feature. These should be clear and readable, not literal word-for-word translations.

### 6. Generate the complete HTML file

Using `templates/newsletter.html` as the reference spec:
- Generate a complete, standalone HTML file
- Include all 5 articles with Chinese text and English translations
- Include the Editor's Desk section with 6 headlines (3 included, 3 not included)
- Include all CSS and JavaScript inline
- All Chinese text in standard DOM elements (Zhongwen extension compatibility)
- Update the date in the header and title

### 7. Archive and deploy

```
# If docs/index.html exists, archive it
# Get the date from the existing file's content or use yesterday's date
mv docs/index.html docs/archive/YYYY-MM-DD.html  # (use actual date)

# Write new newsletter
# (write the generated HTML to docs/index.html)

# Commit and push
git add .
git commit -m "Newsletter YYYY-MM-DD"
git push
```

## CC Prompt (copy-paste to start a generation run)

```
Read config/settings.json, config/interests.json, data/flagged_characters.json, data/preference_history.json, and templates/newsletter.html. Then:

1. Search for today's top news stories across these topics: tech/AI, economics/finance, climate science, Michigan sports, Cubs baseball, and 1-2 serendipitous picks for a curious generalist.
2. Select 5 stories for the newsletter and 3 runner-up headlines for the Editor's Desk.
3. Rewrite each story in Traditional Chinese following the reading level and tone in settings.json. Naturally work in any "struggling" characters from flagged_characters.json.
4. Write English translations for each article.
5. Generate a complete HTML newsletter file using templates/newsletter.html as the reference layout. Include all interaction features (character flagging, translation toggle, editor's desk, feedback export).
6. If docs/index.html exists, move it to docs/archive/ with its date as filename.
7. Write the new newsletter to docs/index.html.
8. git add, commit ("Newsletter YYYY-MM-DD"), and push.
```
