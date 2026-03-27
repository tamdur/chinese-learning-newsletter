---
model: haiku
tools: Bash, WebSearch
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

## Error Handling — 403 Fallback

If any individual feed fails (timeout, HTTP 403, other HTTP error, unparseable XML), **fall back to web search** for that source:

- Marginal Revolution RSS fails → `WebSearch "Marginal Revolution blog latest posts today"`
- Carbon Brief RSS fails → `WebSearch "Carbon Brief climate news today"`
- Cubs RSS fails → `WebSearch "Chicago Cubs news today"`

Parse the web search results into the same JSON format (title, url, source, summary). Continue with the other feeds.

If ALL three feeds fail AND all three web search fallbacks return no results, return:
```json
{
  "stories": [],
  "error": "All RSS feeds and web search fallbacks failed: [details]"
}
```

Do not retry failed feeds beyond the single web search fallback.
