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

## 4. Summary

Print a consolidated summary:

- **Newsletter:** The 5 selected story headlines (Chinese + English titles)
- **Wisdom:** Which passages were served (Heart Sutra day, Mengzi index, Zen index), or "skipped (already generated today)"
- **Obsessions:** Which obsessions were covered, or "skipped (no active obsessions)"
- Any warnings from assembly or validation
- **Links:**
  - https://tamdur.github.io/chinese-learning-newsletter/
  - https://tamdur.github.io/chinese-learning-newsletter/wisdom.html
  - https://tamdur.github.io/chinese-learning-newsletter/obsessions.html
