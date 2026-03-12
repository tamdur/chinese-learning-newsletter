# Cleanup Pipeline

## Overview

After reading a newsletter and exporting feedback from the browser, run cleanup to merge feedback into the project data files.

## Steps

### 1. Read the exported feedback JSON

The user will provide the path to the exported JSON file (e.g., `~/Downloads/feedback_export_2026-03-12.json`). The file has this structure:

```json
{
  "date": "2026-03-12",
  "characters": {
    "碳": { "state": "struggling", "date": "2026-03-12" },
    "氣": { "state": "learned", "date": "2026-03-12" }
  },
  "editors_desk": {
    "offered": [
      { "headline": "...", "included_in_issue": true },
      { "headline": "...", "included_in_issue": false }
    ],
    "user_top_3": [0, 5, 2]
  }
}
```

### 2. Merge character flags into `data/flagged_characters.json`

For each character in the export:
- If the character is **new** (not in flagged_characters.json): add it with `first_flagged` and `last_updated` set to the export date
- If the character **already exists** and the state changed: update `state` and `last_updated`
- If the character **already exists** and the state is the same: update `last_updated` only
- If the exported state is "unmarked" (character was unflagged): remove it from the file

### 3. Merge Editor's Desk picks into `data/preference_history.json`

Append a new session entry:

```json
{
  "date": "2026-03-12",
  "offered": [
    { "headline": "...", "topic_id": "tech", "included_in_issue": true },
    ...
  ],
  "user_top_3": [0, 5, 2]
}
```

Note: `topic_id` may need to be inferred from the headline content or the newsletter HTML if not present in the export. If unsure, use `"unknown"`.

### 4. Commit and push

```
git add data/flagged_characters.json data/preference_history.json
git commit -m "Feedback: YYYY-MM-DD"
git push
```

### 5. Print summary

Show the user:
- New struggling characters added
- Characters that changed state (struggling → learned, learned → unmarked, etc.)
- Editor's Desk picks (which headlines were selected)

## CC Prompt (copy-paste to start a cleanup run)

```
Read the feedback export at [PATH]. Then:

1. Read data/flagged_characters.json and merge the character flags from the export — add new characters, update changed states, remove unflagged characters. Update first_flagged and last_updated dates appropriately.
2. Read data/preference_history.json and append a new session entry with the Editor's Desk data from the export.
3. Write both updated files.
4. git add the data files, commit ("Feedback: YYYY-MM-DD"), and push.
5. Print a summary of changes.
```
