# After-Action Report: 2026-03-27 Newsletter Pipeline (Cloud/Scheduled)

## Summary
First attempt to run the `/go` newsletter pipeline via Claude Code on the web (scheduled/remote session). The pipeline reached Step 6 (assembly) but failed to produce a correct final newsletter. The run was interrupted by the user after ~15 minutes of active work.

## What Worked

### Phase 1: Cleanup
- Feedback file scanning worked fine (no files to process — clean skip).

### Phase 2: Steps 1-3 (Config + Scouts + Selection)
- Config/data file reads: flawless.
- **4 parallel scout agents** launched successfully. Two (HN Algolia, RSS feeds) returned 403 errors due to the remote environment's HTTP restrictions, but the two web-search scouts (Sonnet) returned excellent results — 20 candidate stories total.
- **Story selector** (Opus) worked well. Produced a thoughtful 5+3 selection with good rationale, correctly avoided repeats from recent archives.

### Phase 2: Step 3.5 (Story Researchers)
- 5 parallel researcher agents launched successfully.
- All 5 produced detailed briefings (200-400 words each) via web search fallback when direct URLs returned 403.
- **Problem:** These were launched as background agents, and reading their output was cumbersome — the output files contain raw JSON message logs, not clean text. I had to `tail` the files and parse through protocol messages to extract the actual briefings. This is fragile and time-consuming.

### Phase 2: Step 4 (Article Writer)
- Opus article-writer agent worked perfectly. Returned 5 well-formed articles with correct `headline_html`, `body_html`, `source_label` — all with proper `<span class="c">` wrapping, Traditional Chinese, grade-4 reading level, and natural incorporation of struggling characters.

### Phase 2: Step 5 (Translators)
- 5 parallel Haiku translators all returned clean, accurate English translations in under 5 seconds each.

### Phase 2: Step 5.5 (Glossary)
- **13 single-character agents** (batches of 25) + **5 multi-character word agents** all returned successfully.
- Programmatic TSV→JSON parsing worked.
- Zhuyin validation passed (0 bad entries).
- **314/314 characters covered, 475 total glossary entries, 0 missing.** No remediation needed.
- This step was the most mechanically reliable part of the pipeline.

## What Failed

### Step 6: Assembly
The assembler agent (Opus) was the critical failure point. Despite receiving explicit instructions with all 5 articles' exact HTML content, it:
1. Read the previous issue's HTML (correct)
2. **Ignored the provided article content entirely** and generated its own articles from scratch
3. Wrote an `index.html` with wrong stories (e.g., a tariff story that wasn't selected, different Michigan article content)

**Root cause:** The assembler prompt was ~12,000 tokens of article HTML content. Combined with the instruction to read the 800-line previous issue, the agent's context was overwhelmed. It likely lost track of the provided content and fell back to generating new content based on the template structure it read.

### HTTP 403 Errors (Scouts)
- HN Algolia API, Marginal Revolution RSS, Carbon Brief RSS, MLB RSS — all returned 403.
- The web/remote environment apparently has a more restrictive HTTP client than local Claude Code.
- **Impact:** Lost ~15 candidate stories from HN and RSS sources. The web search scouts compensated adequately, but story diversity suffered.

## Architectural Issues Identified

### 1. Agent Output Readability
Background agent output files contain raw JSON protocol messages, not clean results. Extracting the actual content requires parsing through `{"parentUuid":...}` message envelopes. This makes it nearly impossible to efficiently read agent results when they exceed the direct-return limit.

**Recommendation:** The pipeline should have agents write their results to well-known temp files in a structured format, not rely on the protocol output files.

### 2. Assembler Context Overload
The assembler agent receives the most content of any agent in the pipeline: 5 articles (HTML), 5 translations, 8 editor's desk headlines, a 23KB glossary JSON, plus it needs to read the ~800-line template. This is too much for a single agent call.

**Recommendation:** Split assembly into a programmatic step:
- Use Python to construct the HTML mechanically (template substitution, not LLM generation)
- The assembler agent should NOT exist — assembly is a deterministic operation, not a creative one
- A Python script can: read the previous issue, extract CSS/JS, slot in the new articles/translations/glossary, write the file

### 3. Scout 403 Failures
The RSS/API scouts assume direct HTTP access that may not be available in all environments.

**Recommendation:**
- Make RSS scouts fall back to web search when feeds return 403
- Consider caching HN front page data or using alternative endpoints
- The web search scouts are the most reliable; consider making them the primary path

### 4. Glossary Pipeline is Over-Engineered for This Environment
18 parallel agent calls (13 char batches + 5 word agents) for 314 characters works, but generates enormous context overhead. Each agent call has ~27K tokens of overhead for a relatively simple lookup task.

**Recommendation:** Consider a single Python script that generates the glossary from a pre-built dictionary file, only using agents for characters not in the dictionary. Or use fewer, larger batches.

### 5. No Incremental Checkpointing
If the pipeline fails at Step 6, all work from Steps 1-5.5 is lost. There's no way to resume from a checkpoint.

**Recommendation:** Write intermediate results to disk:
- `data/pipeline/candidates.json` after scouts
- `data/pipeline/selected.json` after selection
- `data/pipeline/articles.json` after article writing
- `data/pipeline/translations.json` after translation
- `data/pipeline/glossary.json` after glossary
- Then assembly reads all of these — and can be re-run independently

### 6. Total Agent Count is Excessive
This run launched approximately **35-40 agents** across all steps. In the cloud/scheduled environment, this creates:
- Long total wall-clock time (each agent has startup overhead)
- Massive total token usage
- Risk of hitting rate limits or session timeouts

**Recommendation:** Consolidate where possible. The glossary step alone used 18 agents for what could be 1-2 calls with a smarter batching strategy or a local dictionary.

## Token/Cost Estimate
Rough estimate of total token usage for this (incomplete) run:
- 4 scout agents: ~100K tokens
- 1 selector agent: ~15K tokens
- 5 researcher agents: ~100K tokens
- 1 article writer: ~20K tokens
- 5 translator agents: ~140K tokens
- 18 glossary agents: ~530K tokens
- 1 assembler agent (failed): ~50K tokens
- Main session orchestration: ~200K tokens
- **Total: ~1.15M tokens** (and the newsletter wasn't completed)

## Recommendations for Next Run

### Short-term (next `/go` run)
1. **Replace the assembler agent with a Python script** that mechanically constructs the HTML
2. **Write intermediate results to temp files** so the main session can read clean data
3. **If RSS feeds 403, fall back to web search immediately** rather than failing

### Medium-term (pipeline redesign)
1. **Pre-build a character dictionary** (`data/glossary_dictionary.json`) so the glossary step only needs agents for new/unknown characters
2. **Reduce agent count** to ~15 by consolidating glossary into 2-3 larger batches
3. **Add checkpointing** so partial runs can be resumed
4. **Make assembly deterministic** — Python template substitution, not LLM generation

### Environment-specific
1. Document which HTTP endpoints are accessible from the cloud environment
2. Consider whether the scheduled/remote environment has different rate limits
3. Test whether `WebFetch` works differently in cloud vs local CLI
