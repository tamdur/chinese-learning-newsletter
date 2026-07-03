# /go — Daily Content Pipeline

You are running the daily content pipeline for 今日讀報. This generates all pages for today.

Execute each pipeline in sequence. After each pipeline completes (including its commit/push), clean up checkpoint files before starting the next one:
```bash
rm -f data/pipeline/*.json data/pipeline/*.txt
```

---

## 1. Newsletter

Read and follow the full instructions in `.claude/commands/newsletter.md`. This is the main news pipeline: scout dispatch → story selection → research → article writing → translation → glossary → assembly → validation → commit/push.

---

## 2. Daily Wisdom

Read and follow the full instructions in `.claude/commands/wisdom.md`. This generates the Daily Wisdom page with Heart Sutra, Mengzi, and Zen passages. It has an idempotency check — if already generated today, it will skip.

---

## 3. Obsessions

Read and follow the full instructions in `.claude/commands/obsessions.md`. This generates the Obsessions culture desk page with web-searched content for each active obsession.

---

## 4. Verify published to main

The live site is served by GitHub Pages from the `main` branch, so a run
only counts as published once all three pipelines' commits are on
`origin/main`. Confirm this before reporting success:
```bash
git fetch origin main && git log --oneline -3 origin/main
```
The top three commits should be today's **Obsessions**, **Daily Wisdom**,
and **Newsletter**. If any are missing, the push fell back onto a stray
working branch (e.g. a `claude/*` branch in an unattended cloud session).
Publish the local commits to the Pages branch and re-verify:
```bash
git push origin HEAD:main
git fetch origin main && git log --oneline -3 origin/main
```
Do not report success until today's three commits are visible on
`origin/main`.

## 5. Summary

Print a consolidated summary:

- **Newsletter:** The 5 selected story headlines (Chinese + English titles)
- **Wisdom:** Which passages were served (Heart Sutra day, Mengzi index, Zen index), or "skipped (already generated today)"
- **Obsessions:** Which obsessions were covered, or "skipped (no active obsessions)"
- Any warnings from assembly or validation
- **Links:**
  - https://tamdur.github.io/chinese-learning-newsletter/
  - https://tamdur.github.io/chinese-learning-newsletter/wisdom.html
  - https://tamdur.github.io/chinese-learning-newsletter/obsessions.html
