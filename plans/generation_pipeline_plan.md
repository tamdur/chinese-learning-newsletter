# Generation Pipeline Plan

## Overview

The generation pipeline runs in a single Claude Code session and produces a complete newsletter HTML file at `docs/index.html`. The user triggers it with `/go`. The main session (Opus) orchestrates subagents for parallelism and cost efficiency.

Total pipeline: ~5-8 minutes. Nine subagent types, up to 28-30 invocations per run.

---

## Subagent Architecture

### 1. news-scout-hn (Haiku)

**Purpose:** Fetch Hacker News front page stories via the Algolia API.

**File:** `.claude/agents/news-scout-hn.md`

**Model:** Haiku

**Tools:** Bash (curl), no web search needed

**System prompt summary:** Fetch `https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30` via curl. Parse the JSON response. Filter for stories from the past 36 hours where possible (use `created_at` field). Return a structured JSON list.

**Input:** None (self-contained — fetches from API)

**Output:** JSON array:
```json
[
  {
    "title": "...",
    "url": "...",
    "source": "Hacker News",
    "points": 342,
    "created_at": "2026-03-12T08:15:00Z",
    "hn_id": 12345678
  }
]
```

**Error handling:** If the API call fails (timeout, HTTP error), return an empty array with an error message. The pipeline continues — web search will cover tech/AI stories.

---

### 2. news-scout-rss (Haiku)

**Purpose:** Fetch and parse RSS feeds for Marginal Revolution, Carbon Brief, and MLB.com Cubs.

**File:** `.claude/agents/news-scout-rss.md`

**Model:** Haiku

**Tools:** Bash (curl)

**System prompt summary:** Fetch these three RSS feeds via curl:
1. `https://marginalrevolution.com/feed` — Econ/finance topic discovery
2. `https://www.carbonbrief.org/feed/` — Climate stories
3. `https://www.mlb.com/cubs/feeds/news/rss.xml` — Cubs baseball

Parse the XML responses. Extract titles, links, publication dates, and brief descriptions from each feed. Filter for items from the past 36 hours where possible. Return a structured JSON list.

**Input:** None (self-contained — fetches from feeds)

**Output:** JSON array:
```json
[
  {
    "title": "...",
    "url": "...",
    "source": "Marginal Revolution",
    "pub_date": "2026-03-12",
    "summary": "Brief description from feed..."
  }
]
```

**Error handling:** If any individual feed fails, skip it and continue with the others. Return partial results with a note about which feeds failed. Even if all three fail, the pipeline continues — web search covers all these topics.

---

### 3. news-scout-web (Sonnet)

**Purpose:** Run targeted web searches to fill gaps the feeds don't cover and find serendipitous stories.

**File:** `.claude/agents/news-scout-web.md`

**Model:** Sonnet (needs web search tool + judgment to evaluate relevance)

**Tools:** WebSearch

**System prompt summary:** Run 4-6 targeted web searches. The agent receives guidance on what to search for but uses judgment about query phrasing and result evaluation. Searches:

1. **Generative AI / AGI news** — This is the user's primary tech interest. Search for recent AI model releases, lab announcements, capability demonstrations, policy developments. Not "tech" broadly — specifically generative AI and AGI progress.
2. **Economics / finance / macro news** — GDP, central bank decisions, trade policy, market-moving stories. Look for freely accessible reporting (Reuters, AP, wire services).
3. **Michigan football or basketball** — Seasonal awareness: check if either sport is currently in-season. During football season (Sep–Jan), search for game results, recruiting, coaching news. During basketball season (Nov–Apr), search for tournament results, conference play. During quiet periods (Jun–Aug), search for transfer portal, recruiting, or skip if nothing notable.
4. **Serendipity pick 1** — Something a curious, well-read generalist would find fascinating. Science discoveries, unusual history, ideas, culture. Niche-interesting, not mainstream trending (water cooler stories are covered by the national scout).
5. **Serendipity pick 2** — A different angle from query 4. Could be: interesting economics, philosophy, food science, architecture, linguistics, etc.
6. **Optional: fill a gap** — If the agent notices a major news category is underrepresented, run one more search.

**Input:** Today's date (for recency filtering and seasonal awareness)

**Output:** JSON array:
```json
[
  {
    "title": "...",
    "url": "...",
    "source": "Reuters",
    "summary": "2-3 sentence summary of the story...",
    "topic_hint": "econ_finance",
    "search_query": "the query that found this"
  }
]
```

**Error handling:** If web search fails entirely (rare), return an empty array with error. The pipeline can still work from RSS/API results alone, though story selection quality may suffer.

---

### 3b. news-scout-national (Sonnet)

**Purpose:** Find national political news, Chicago local news, and water cooler stories.

**File:** `.claude/agents/news-scout-national.md`

**Model:** Sonnet (needs web search + judgment)

**Tools:** WebSearch

**System prompt summary:** Run 3-4 web searches:

1. **US national / political news** — Consequential policy changes, executive actions, legislative votes, court rulings, major agency decisions. Include Illinois state politics when significant. Skip polls, campaign strategy, pundit takes.
2. **Chicago local news** — City council votes, transit/infrastructure, public safety data. Skip mayoral press conferences and minor announcements.
3. **Water cooler stories** — The big stories everyone is talking about. Mainstream-big, not niche-interesting (that's the web scout's serendipity job).
4. **Optional gap-fill** — If any category came up thin.

**Input:** Today's date

**Output:** Same JSON array format as news-scout-web, with `topic_hint` values: `national_politics`, `chicago_local`, `water_cooler`.

**Error handling:** Same as news-scout-web.

---

### 4. story-selector (Opus)

**Purpose:** Editorial judgment — select the 5 best stories for the newsletter and 3 runner-up headlines for the Editor's Desk.

**File:** `.claude/agents/story-selector.md`

**Model:** Opus (editorial judgment needs the best model)

**Tools:** Read (for config/data files and archive)

**System prompt summary:** You are the editor for 今日讀報, a daily Traditional Chinese reading newsletter. You receive a pool of candidate stories from three news scouts and must select the day's issue.

Read these files for context:
- `config/interests.json` — topic definitions and selection guidance
- `data/preference_history.json` — past Editor's Desk sessions showing what the user has preferred
- Recent files in `docs/archive/` — to enforce the no-repeat rule

Selection rules:
- Pick exactly 5 stories for the newsletter
- Pick exactly 3 runner-up headlines for the Editor's Desk (stories considered but not included)
- Total: 8 headlines (5 included + 3 excluded)
- Follow the `selection_note` in `interests.json`: variety across topics, lead with most interesting, don't force every category, include 1-2 serendipitous picks
- Strong preference for stories from the past 36 hours
- Stories must NOT repeat from recent newsletters unless there's been a substantive update — check `docs/archive/` files
- Climate stories only if directly relevant to hurricane catastrophe modeling: large loss events, changes to data agencies/sources, major shifts in climate research establishment
- Consider `preference_history.json` to align with user taste over time

**Input:** Combined candidate story list from all three scouts (passed as prompt context by the orchestrator)

**Output:** JSON object:
```json
{
  "selected": [
    {
      "rank": 1,
      "title": "...",
      "url": "...",
      "source": "...",
      "summary": "3-5 sentence English summary with enough context for the article writer to work from",
      "topic_id": "gen_ai"
    }
  ],
  "runners_up": [
    {
      "title": "...",
      "source": "...",
      "topic_id": "econ_finance",
      "included_in_issue": false,
      "headline_zh": "Suggested Traditional Chinese headline"
    }
  ],
  "rationale": "Brief explanation of selection logic — what was prioritized, what was dropped and why"
}
```

**Error handling:** If the candidate pool has fewer than 8 stories, the selector should still pick the best 5 (or as many as available) and note the shortage. If fewer than 5 worthy stories exist, fail the pipeline with an explanation — this likely means all scouts failed.

---

### 4b. story-researcher (Sonnet) — 5 parallel invocations

**Purpose:** Deep-dive research on each selected story to produce rich English briefings for the article writer.

**File:** `.claude/agents/story-researcher.md`

**Model:** Sonnet (needs judgment to evaluate sources, handle paywalls, synthesize)

**Tools:** WebFetch, WebSearch

**System prompt summary:** Research a single news story in depth. Produce a 200-400 word English briefing with key facts, quotes, context, and interesting details.

**Fallback chain:**
1. WebFetch the primary URL
2. If that fails (paywall, 403, timeout): WebSearch for the same story from other sources
3. If that also fails: return the original selector summary with a warning

**Input:** Story URL, title, source, and selector's 3-5 sentence summary

**Output:** Plain text briefing (not JSON) with sections: Key Facts, Quotes, Context, Interesting Details.

**Why 5 parallel invocations:** Each story is independent. Parallel execution adds only ~30-60 seconds of wall-clock time (one researcher's latency, not five).

**Error handling:** Never returns empty. At minimum, returns the original summary. If content is behind a hard paywall with no free alternatives, says so explicitly and provides whatever partial info from search result snippets.

---

### 5. article-writer (Opus) — Single invocation for all 5 articles

**Purpose:** Rewrite each selected story in Traditional Chinese at the calibrated reading level with natural incorporation of struggling characters.

**File:** `.claude/agents/article-writer.md`

**Model:** Opus (core product — Chinese writing quality is everything)

**Tools:** Read (for config/data files)

**System prompt summary:** You write Traditional Chinese news articles for 今日讀報. Your tone is a knowledgeable friend explaining the news over coffee — casual but informed, using grammar practical for daily conversation. You never talk down.

Read these files:
- `config/settings.json` — reading level (grade 5), article length (~150 chars)
- `data/flagged_characters.json` — characters the user is struggling with

For each of the 5 stories:
1. Write a headline in Traditional Chinese
2. Write body text (2-3 paragraphs, ~100-200 characters total)
3. Follow the reading level description exactly — common characters, straightforward grammar, no literary idioms, gloss difficult characters in parentheses on first use
4. Naturally increase frequency of "struggling" characters — weave them into varied contexts across all 5 articles. Distribute them; don't front-load into article 1
5. Wrap every Chinese character in `<span class="c">` tags (including punctuation). This is critical for Zhongwen extension compatibility
6. Use Traditional Chinese only — never simplified characters

**Input:** The 5 selected stories with **detailed research briefings from story-researcher** (200-400 words each with key facts, quotes, context)

**Output:** JSON array of 5 articles:
```json
[
  {
    "article_id": 1,
    "headline_html": "<span class=\"c\">台</span><span class=\"c\">積</span>...",
    "body_html": "<p><span class=\"c\">台</span>...</p><p>...</p>",
    "headline_plain": "台積電宣布在日本興建第三座晶圓廠",
    "source_label": "來源：Hacker News"
  }
]
```

**Why single invocation (not 5 parallel):** The article writer needs cross-article context for two reasons:
1. **Struggling character distribution** — with 5 parallel writers, each would try to use all struggling characters in its own article, creating awkward repetition. A single writer distributes them naturally across all 5 articles.
2. **Vocabulary variety** — a single writer avoids repeating the same sentence patterns and transitional phrases across articles. Five parallel writers would likely produce stylistically repetitive output.

The tradeoff is speed (sequential is slower than parallel). But at ~150 characters per article, all 5 articles are only ~750 characters total — well within a single Opus call. Speed difference is negligible.

**Error handling:** If the writer produces simplified characters, the assembler should catch this and flag it. If an article is too long or too short relative to `article_length`, the assembler notes it but doesn't fail.

---

### 6. translator (Haiku) — 5 parallel invocations

**Purpose:** Translate each Chinese article to English for the translation toggle.

**File:** `.claude/agents/translator.md`

**Model:** Haiku (mechanical task, doesn't need Opus quality)

**Tools:** None (pure text transformation)

**System prompt summary:** Translate the following Traditional Chinese news article to natural English. The translation should be clear and readable, not a literal word-for-word translation. Maintain the same paragraph structure. Output plain HTML paragraphs (`<p>` tags).

**Input:** One article's plain Chinese text (without span tags — raw text extracted from `headline_plain` and body text with tags stripped)

**Output:** HTML string:
```html
<p>TSMC announced today it plans to build a third wafer fabrication plant...</p>
<p>The Japanese government will provide approximately...</p>
```

**Why 5 parallel invocations:** Translations are fully independent. No cross-article context needed. Running 5 in parallel saves time. Each translation is a trivial Haiku task.

**Error handling:** If a translation fails, retry once. If it fails again, use a placeholder: `<p>[Translation unavailable]</p>`. The newsletter is still readable without translations.

---

### 6b. glossary-chars (Sonnet) — 8-10 parallel invocations

**Purpose:** Single-character lookup in small batches for reliable completeness.

**File:** `.claude/agents/glossary-chars.md`

**Model:** Sonnet

**Tools:** None (pure text output)

**System prompt summary:** Given a batch of 25-30 Chinese characters and article text for context, return TSV with one line per character: `char\tzhuyin\tenglish`. Only single-character entries. Uses 注音符號, never pinyin.

**Input:** CHARACTER_LIST (25 chars, one per line) + TEXT (concatenated plain text from all articles)

**Output:** TSV text (not JSON). Converted to JSON programmatically by the main session via python.

**Why TSV:** Cuts structural overhead dramatically. One bad line doesn't break the entire response (unlike malformed JSON). Partial failure is recoverable.

**Why batches of 25:** ~100-150 entries per call was too many for models to reliably enumerate. At 25, the model can hold the full list in working memory and verify completeness.

---

### 6c. glossary-words (Sonnet) — 5 parallel invocations

**Purpose:** Multi-character word identification via word segmentation.

**File:** `.claude/agents/glossary-words.md`

**Model:** Sonnet

**Tools:** None (pure text output)

**System prompt summary:** Given an article's full text, identify every multi-character word/phrase that functions as a meaning unit. Return JSON with entries for compound words, proper nouns, technical terms, idiomatic expressions.

**Input:** One article's full plain text

**Output:** JSON object with multi-character keys only.

**Why separate from single-char:** These are fundamentally different tasks. Single-char is boring mechanical lookup that models drop entries on. Multi-char is word segmentation that models are good at. Splitting them plays to the model's strengths.

---

### 7. assembler (Sonnet) — Single invocation

**Purpose:** Assemble all outputs into a complete HTML file matching the template spec.

**File:** `.claude/agents/assembler.md`

**Model:** Sonnet (string assembly with attention to spec compliance, not creative work)

**Tools:** Read (for template), Write (for output), Bash (for git operations and file moves), Glob, Grep

**System prompt summary:** You assemble the 今日讀報 newsletter HTML file. You receive all content (5 Chinese articles, 5 English translations, 8 Editor's Desk headlines, validated glossary, today's date) and produce a complete standalone HTML file.

Read `templates/newsletter.html` as the spec. The output must match its structure exactly:
- Same CSS (copy verbatim from template)
- Same JavaScript (copy verbatim from template — but remove the seed/test data in the initialization block)
- Same HTML structure, classes, data attributes
- Same interaction features (character flagging, translation toggle, editor's desk, feedback export)

Glossary embedding:
- Receive pre-built, validated glossary JSON object as input
- Embed as `const GLOSSARY = {glossary_json};` in the JavaScript section
- The assembler does NOT build the glossary — that's handled by the main session

Assembly steps:
1. Read `templates/newsletter.html` for the exact structure
2. Fill in: today's date, all 5 articles, all 8 Editor's Desk headlines, embedded glossary
3. Ensure the JavaScript initialization block does NOT contain test seed data

After assembling:
1. If `docs/index.html` exists, extract the date, archive it, patch navigation
2. Write the new HTML to `docs/index.html`
3. Run: `git add docs/index.html docs/archive/` then `git commit -m "Newsletter YYYY-MM-DD"` then `git push`

**Input:** All content pieces (articles, translations, headlines, glossary, date) passed as prompt context.

**Output:** Confirmation message with the committed file path and any warnings.

**Error handling:**
- If `docs/index.html` doesn't exist (first run), skip the archive step
- If git push fails, report the error but don't retry — the user can push manually
- Verify that no simplified characters appear in the final HTML (scan for common simplified-only code points)

---

## Pipeline Orchestration

The main CC session (Opus) orchestrates the flow. Here's the step-by-step:

### Step 1: Read config and data files

The main session reads:
- `config/settings.json`
- `config/interests.json`
- `data/flagged_characters.json`
- `data/preference_history.json`

These are small files. Read them directly in the main session to pass relevant context to subagents.

### Step 2: Dispatch four scout agents in parallel

Launch all four simultaneously using the Agent tool:
- `news-scout-hn` — no input needed
- `news-scout-rss` — no input needed
- `news-scout-web` — pass today's date for seasonal awareness
- `news-scout-national` — pass today's date

All four run concurrently. The main session waits for all to return.

### Step 3: Combine and dispatch story-selector

Merge results from all four scouts into a single candidate list. Pass to `story-selector` along with instructions to read `interests.json`, `preference_history.json`, and recent archive files.

### Step 3.5: Dispatch 5 story-researcher agents in parallel

For each of the 5 selected stories, launch a `story-researcher` agent with the URL, title, source, and selector summary. All 5 run concurrently.

### Step 4: Dispatch article-writer

Pass the 5 selected stories with **detailed research briefings** (from story-researcher, not selector summaries) to `article-writer`. Wait for return.

### Step 5: Dispatch 5 translators in parallel

For each of the 5 articles, launch a `translator` agent with the plain Chinese text. All 5 run concurrently.

### Step 5.5: Build and validate glossary

The main session (Opus) builds the glossary directly:
1. Extract and deduplicate all unique Chinese characters across all 5 articles (~200-250 chars)
2. Dispatch 8-10 `glossary-chars` agents in parallel (batches of 25 chars, TSV output)
3. Convert TSV to JSON programmatically via python
4. Dispatch 5 `glossary-words` agents in parallel (one per article, JSON output)
5. Merge single-char and multi-char results
6. Validate zhuyin format (discard pinyin entries)
7. Validate completeness (every unique character has a single-char entry)
8. Remediate gaps: re-dispatch missing characters in batches of 25, up to 3 passes
9. Log stats, pass validated glossary to assembler

### Step 6: Dispatch assembler

Pass to the assembler:
- 5 articles (headline HTML, body HTML, source labels)
- 5 English translations
- 8 Editor's Desk headlines (5 selected + 3 runners-up, with `included_in_issue` flags and Chinese headlines)
- Validated glossary JSON object
- Today's date

The assembler receives the pre-built glossary and embeds it directly. It reads the template, builds the HTML, archives the old issue, writes the new one, commits, and pushes.

### Step 7: Confirm success

The main session prints a summary:
- Which 5 stories were selected (with topic IDs)
- The 3 runner-up headlines
- Glossary stats (total entries, single-char, multi-char, any missing)
- Any warnings (scout failures, simplified character detections, etc.)
- The GitHub Pages URL

### Failure Modes

| Failure | Impact | Recovery |
|---------|--------|----------|
| HN API down | Lose ~30 tech/serendipity candidates | Web scout + national scout cover gaps; proceed normally |
| One RSS feed broken | Lose one topic's feed candidates | Web/national scouts cover all topics; proceed normally |
| All RSS feeds broken | Lose all feed candidates | Web + national + HN still provide candidates; proceed normally |
| Web search down | Lose serendipity + gap-filling | HN + RSS + national still provide candidates; proceed with warning |
| National scout fails | Lose politics/Chicago/water-cooler | Web scout serendipity may partially cover; proceed with warning |
| All scouts fail | No candidates | **Fail the pipeline.** Print error, suggest retrying later |
| Story researcher can't access URL | Degraded content for that story | Fallback chain: WebSearch → original summary. Pipeline continues |
| Story selector can't find 5 worthy stories | Insufficient content | **Fail the pipeline.** Print the candidate list for user inspection |
| Article writer produces simplified chars | Wrong character set | Assembler flags it; main session reports warning |
| Glossary batch returns bad TSV | Missing chars for that batch | Chars added to missing list, caught in remediation passes |
| Git push fails | Newsletter not deployed | Report error; user pushes manually. Newsletter file is still written locally |

---

## Generation Command

The user types `/go` to run the full pipeline (cleanup + generation). The generation phase is defined in `.claude/commands/go.md` Phase 2.

---

## Files Created or Modified

### New files

| File | Purpose |
|------|---------|
| `.claude/agents/news-scout-hn.md` | HN Algolia API scout agent definition |
| `.claude/agents/news-scout-rss.md` | RSS feed scout agent definition |
| `.claude/agents/news-scout-web.md` | Web search scout agent definition |
| `.claude/agents/news-scout-national.md` | National politics, Chicago local, water cooler scout |
| `.claude/agents/story-selector.md` | Story selection agent definition |
| `.claude/agents/story-researcher.md` | Deep-dive story research for richer article content |
| `.claude/agents/article-writer.md` | Chinese article writing agent definition |
| `.claude/agents/translator.md` | Chinese-to-English translation agent definition |
| `.claude/agents/glossary-chars.md` | Single-character glossary lookup (TSV output, batches of 25) |
| `.claude/agents/glossary-words.md` | Multi-character word identification (JSON output) |
| `.claude/agents/assembler.md` | HTML assembly + deploy agent definition |
| `.claude/commands/go.md` | `/go` slash command (cleanup + generation) |

### Modified files

| File | Change |
|------|--------|
| `docs/index.html` | Replaced with new newsletter |
| `docs/archive/YYYY-MM-DD.html` | Previous newsletter archived |
| `scripts/generate_prompt.md` | Updated to reference the slash command and agent architecture instead of the manual prompt |

### Not modified

| File | Why |
|------|-----|
| `CLAUDE.md` | Pipeline details belong in agent definitions and this plan, not in the top-level project doc. CLAUDE.md already describes the pipeline at the right level of abstraction. |
| `config/settings.json` | Read-only during generation |
| `config/interests.json` | Read-only during generation |
| `data/flagged_characters.json` | Read-only during generation (only modified by cleanup pipeline) |
| `data/preference_history.json` | Read-only during generation (only modified by cleanup pipeline) |
| `templates/newsletter.html` | Reference spec — never modified by pipeline |

---

## Resolved Decisions

All open questions have been resolved. Decisions are recorded here for reference during implementation.

1. **Runner-up headlines:** The story-selector produces Traditional Chinese headlines for the 3 runner-up stories. The article-writer does not touch them.

2. **Selected story headlines:** Only the article-writer produces Chinese headlines for the 5 selected stories. The selector provides English summaries and metadata only.

3. **First run (template sample in docs/index.html):** Archive it normally to `docs/archive/2026-03-12.html`. No special-case logic.

4. **JS seed data:** The assembler strips the template's test seed data (`charStates['積']`, `charStates['廠']`) and replaces the else block with a clean `saveState()` call.

5. **Date backdating:** Not supported for MVP. The `/generate` command always uses today's date.

6. **Cost:** ~$2-3 per run (Max subscription, not a concern).

7. **Character span wrapping:** The article-writer wraps every Chinese character in `<span class="c">` tags. The assembler validates that no Chinese characters are unwrapped and flags any issues.

8. **Editor's Desk headlines:** Plain text in `<span class="desk-headline">` — no character-level span wrapping. These are UI elements, not reading content.

9. **Glossary architecture (revised):** Split into two agent types — `glossary-chars` (single-character TSV, batches of 25) and `glossary-words` (multi-character JSON, one per article). TSV output for single chars is converted to JSON programmatically, not by an LLM. This replaced the old single `glossary-builder` agent which failed to produce complete output at ~100-150 entries per call.

10. **Glossary ownership:** Main session (Opus) handles glossary building, not the assembler. The assembler receives a pre-built glossary as input. This prevents the assembler from cutting corners on a complex multi-step process.

11. **Story research step:** After story selection, 5 parallel `story-researcher` agents fetch full articles and produce 200-400 word briefings. The article-writer receives these rich briefings instead of the selector's thin 3-5 sentence summaries.

12. **Broader topics:** Added `national_politics`, `chicago_local`, and `water_cooler` to interests.json. A 4th scout (`news-scout-national`) covers these. The web scout's serendipity picks remain niche-interesting, not mainstream-big.
