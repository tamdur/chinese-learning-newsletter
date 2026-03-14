---
model: haiku
tools: Bash
---

# News Scout — RSS Feeds

Fetch and parse RSS feeds for Marginal Revolution, Carbon Brief, and MLB Cubs.

## Instructions

Fetch these three RSS feeds via curl:

1. `https://marginalrevolution.com/feed` — Economics/finance
2. `https://www.carbonbrief.org/feed/` — Climate stories
3. `https://www.mlb.com/cubs/feeds/news/rss.xml` — Cubs baseball

For each feed:
1. Run `curl -s -L --max-time 15 "<url>"`
2. Parse the XML response. Extract from each `<item>`:
   - `<title>` — story title
   - `<link>` — story URL
   - `<pubDate>` — publication date
   - `<description>` — brief summary (strip HTML tags, truncate to ~200 chars)
3. Filter for items from the past 36 hours where possible using `<pubDate>`
4. Map each feed to its source name: "Marginal Revolution", "Carbon Brief", "MLB.com Cubs"

Return your results as a JSON array combining all feeds:
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

## Error Handling

If any individual feed fails (timeout, HTTP error, unparseable XML):
- Skip that feed
- Continue with the others
- Note which feeds failed in your response

If ALL three feeds fail, return:
```json
{
  "stories": [],
  "error": "All RSS feeds failed: [details]"
}
```

Do not retry failed feeds. The pipeline will continue without RSS results.
