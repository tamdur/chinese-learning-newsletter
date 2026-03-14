# Cleanup Pipeline

## Overview

The cleanup phase processes exported feedback JSON files from the newsletter reader. It merges character flags and Editor's Desk picks into the project data files, then commits and pushes.

Cleanup runs automatically as Phase 1 of the `/go` command. It is not run independently.

## Feedback File Location

Feedback files are exported from the newsletter's "Export Feedback" button in Chrome. They download to `~/Downloads/` with the naming pattern `feedback_YYYY-MM-DD.json`.

The cleanup phase scans `~/Downloads/` for all files matching `feedback_*.json`. If none are found, cleanup is silently skipped.

## Feedback File Schema

```json
{
  "date": "2026-03-12",
  "characters": {
    "積": { "state": "struggling", "date": "2026-03-12" },
    "膨": { "state": "struggling", "date": "2026-03-12" },
    "鏈": { "state": "learned", "date": "2026-03-12" }
  },
  "editors_desk": {
    "offered": [
      { "headline": "...", "included_in_issue": true },
      { "headline": "...", "included_in_issue": false }
    ],
    "user_top_3": [0, 3, 5]
  }
}
```

## Multi-File Processing

When multiple feedback files exist (e.g., the user skipped `/go` for a day or two):

1. Sort by filename date ascending (oldest first)
2. Process each file sequentially
3. Later files override earlier ones for the same character
4. Delete each file after successful processing
5. Single commit after all files are merged

## Character State Merge Rules

Target file: `data/flagged_characters.json`

| Feedback state | Character exists? | Action |
|----------------|-------------------|--------|
| `struggling` | No | Add: `state: "struggling"`, `first_flagged: <date>`, `last_updated: <date>` |
| `struggling` | Yes | Update: `state: "struggling"`, `last_updated: <date>` (keep `first_flagged`) |
| `learned` | No | Add: `state: "learned"`, `first_flagged: <date>`, `last_updated: <date>` |
| `learned` | Yes | Update: `state: "learned"`, `last_updated: <date>` (keep `first_flagged`) |
| `unmarked` | Yes | Remove the character entry entirely |
| `unmarked` | No | No-op |
| *(absent)* | — | No change. Absence ≠ removal. |

### Effect on generation

- **struggling**: Pipeline naturally increases frequency of this character in future articles
- **learned**: Pipeline stops boosting; character appears at natural frequency
- **unmarked (removed)**: Same as never flagged — natural frequency

## Preference History Merge

Target file: `data/preference_history.json`

Append a new entry to the `sessions` array:

```json
{
  "date": "2026-03-12",
  "offered": [
    { "headline": "...", "included_in_issue": true },
    ...
  ],
  "user_top_3": [0, 3, 5]
}
```

- Append-only — never modify or delete existing sessions
- Skip duplicate dates (same date already in sessions array)
- Trimming/summarization is deferred scope

## Post-Merge

1. Delete the processed feedback file from `~/Downloads/`
2. `git add data/flagged_characters.json data/preference_history.json`
3. `git commit -m "Cleanup: merge feedback"`
4. `git push`
