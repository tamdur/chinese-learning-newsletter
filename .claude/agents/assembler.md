---
name: assembler
description: Assemble the 今日讀報 newsletter HTML, run validation, remediate any failures, and commit/push the result.
model: sonnet
tools: Read, Write, Bash, Glob, Grep, Agent
---

# Newsletter Validator

Validate the assembled 今日讀報 newsletter and fix any issues.

## Instructions

### 1. Run assembly

```bash
python3 scripts/assemble.py --date {{date}}
```

If this fails (missing checkpoint files, template errors), report the error and stop.

### 2. Run validation

```bash
python3 scripts/validate.py
```

### 3. Handle validation results

**If PASS:** Proceed to step 4.

**If FAIL (exit code 2):** Read the error details and fix:

- **Simplified characters:** Read the article in `data/pipeline/articles.json` that contains the offending characters. Dispatch an `article-writer` agent to rewrite just that article, then update `data/pipeline/articles.json` with the corrected article. Re-run assembly + validation.

- **Unwrapped Chinese characters:** Same fix as above — the article-writer is responsible for `<span class="c">` wrapping.

- **Missing glossary entries:** Read `data/pipeline/glossary.json` to confirm. Dispatch `glossary-chars` agents for the missing characters, merge results into `data/pipeline/glossary.json`. Re-run assembly + validation.

- **Broken navigation:** Read the archive directory and the generated HTML to diagnose. Fix the navigation links manually in `docs/index.html` if the issue is straightforward.

- **Mobile glossary popup issues:** These indicate a problem with the template or assembly script. Report the specific missing elements — do not attempt to fix `scripts/assemble.py` yourself.

**If WARN (exit code 1):** Report warnings but proceed to step 4. Warnings are informational.

### 4. Commit

```bash
git add docs/index.html docs/archive/ docs/shared.css docs/shared.js docs/glossary/ data/newsletter_topic_ledger.json
git commit -m "Newsletter {{date}}"
```

(`data/newsletter_topic_ledger.json` is the topic ledger updated in Step 5.7; staging it here commits and pushes it atomically with the issue. If it has no changes, `git add` is a harmless no-op.)

Do NOT push — the orchestrator handles pushing via MCP.

### 5. Report

Print a summary:
- Date
- Article count
- Glossary entry count
- Any warnings from validation
- Whether any remediation was needed

## Error Handling

- If assembly fails, do NOT attempt to build HTML manually
- If validation fails after 2 remediation attempts, report the remaining errors and stop
- If git push fails, report the error but don't retry
