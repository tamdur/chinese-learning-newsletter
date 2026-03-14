# Generation Pipeline

## Overview

This document describes the steps to generate a daily newsletter issue. The user types `/go` in a CC session to trigger the full pipeline (cleanup + generation). The generation phase is documented here.

## Steps

### 1. Read configuration and data files

Read these files to understand current settings and user state:

- `config/settings.json` — reading level, article count, title
- `config/interests.json` — topics, source hints, selection guidance
- `data/flagged_characters.json` — characters the user is struggling with or has learned
- `data/preference_history.json` — past Editor's Desk picks (what stories the user preferred)
- `templates/newsletter.html` — reference HTML for the output format

### 2. Search for today's news

Dispatch 4 scout agents in parallel:
- **news-scout-hn** — Hacker News front page via Algolia API
- **news-scout-rss** — Marginal Revolution, Carbon Brief, MLB Cubs RSS feeds
- **news-scout-web** — targeted web searches for AI/AGI, econ/finance, Michigan sports, Cubs, serendipity picks (niche-interesting)
- **news-scout-national** — US national/political news, Chicago local news, water cooler stories (mainstream-big)

Aim for 15+ candidate stories across all scouts.

### 3. Select stories

Choose 5 stories for the issue and 3 runner-up headlines for the Editor's Desk section.

Selection criteria:
- Follow the `selection_note` in `interests.json`
- Variety across topics (but don't force every topic)
- Lead with the genuinely most interesting story
- Consider `preference_history.json` — what kinds of stories has the user favored?
- Include 1-2 stories that a curious generalist would enjoy

### 3.5. Research selected stories

Dispatch 5 story-researcher agents in parallel (one per selected story). Each researcher:
- Fetches the full article via WebFetch
- Falls back to WebSearch if the primary URL is inaccessible (paywall, 403, timeout)
- Falls back to the original selector summary if both fail
- Produces a 200-400 word English briefing with key facts, quotes, context, and interesting details

### 4. Write the articles in Traditional Chinese

For each of the 5 selected stories, using the **detailed research briefings** (not the selector's thin summaries):
- Rewrite in Traditional Chinese (繁體中文) — never simplified characters
- Follow the reading level description in `settings.json` (currently grade 5)
- Use the conversational tone: knowledgeable friend over coffee, not textbook or news anchor
- Include concrete numbers, names, and details from the briefings rather than vague summaries
- Naturally increase frequency of characters listed as "struggling" in `flagged_characters.json` — weave them into the text in varied contexts
- Gloss difficult characters in parentheses on first use when needed
- Each article: 2-4 paragraphs, ~100-200 characters

### 5. Write English translations

Dispatch 5 translator agents in parallel. Each produces a natural English translation for the toggle feature — clear and readable, not literal word-for-word.

### 5.5. Glossary building (handled by main session)

The main session (Opus) builds the glossary directly — NOT delegated to the assembler. Two specialized agents handle different tasks:

**Single-character lookup** (`glossary-chars.md`):
1. Deduplicate all unique Chinese characters across all 5 articles (~200-250 chars)
2. Chunk into batches of 25-30 characters
3. Dispatch 8-10 `glossary-chars` agents in parallel, each returning TSV (char\tzhuyin\tenglish)
4. Convert TSV to JSON programmatically via python (not LLM-mediated)

**Multi-character words** (`glossary-words.md`):
1. Dispatch 5 `glossary-words` agents in parallel (one per article)
2. Each returns JSON with multi-character entries only

**Merge and validate:**
1. Combine single-char and multi-char results
2. Validate zhuyin format (must be 注音符號, discard any pinyin)
3. Validate completeness (every unique character has a single-char entry)
4. Remediate gaps: re-dispatch missing characters in batches of 25, up to 3 passes

Both agents have `tools: []` — their responses ARE the output.

### 6. Generate the complete HTML file

Pass all content to the assembler agent:
- 5 articles, 5 translations, 8 Editor's Desk headlines, validated glossary, today's date
- The assembler reads `templates/newsletter.html` as the spec and produces a complete standalone HTML file
- The assembler embeds the pre-built glossary (it does NOT build the glossary itself)

### 7. Archive and deploy

The assembler handles:
1. Archive existing `docs/index.html` to `docs/archive/YYYY-MM-DD.html`
2. Patch navigation links in archived files
3. Write new newsletter to `docs/index.html`
4. `git add`, commit, push
