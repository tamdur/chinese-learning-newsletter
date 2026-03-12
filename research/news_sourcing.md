# News Sourcing Research

Research date: 2026-03-12

## Overview

This document evaluates approaches for sourcing English-language news programmatically for the 今日讀報 newsletter pipeline. The pipeline needs to find 8+ candidate stories daily across tech/AI, economics/finance, climate science, Michigan sports, Cubs baseball, and serendipitous general-interest topics, then select 5 for the newsletter plus 3 runner-up headlines.

Two fundamental approaches exist: **RSS/API fetching** (structured, deterministic) and **Claude's built-in web search** (flexible, zero-setup). The recommendation at the end combines both.

---

## 1. Tech / AI / AGI

### Hacker News

The best-served source category. Three access methods:

**Algolia HN Search API (recommended)**
- Endpoint: `https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30`
- Returns current front-page stories with title, URL, points, author, date — all in one request
- No authentication, no API key
- Rate limit: 10,000 requests/hour (irrelevant for daily pipeline)
- Returns structured JSON — easy to parse

**Official Firebase API**
- Base: `https://hacker-news.firebaseio.com/v0/`
- `/v0/topstories.json` returns up to 500 item IDs; each item requires a separate fetch
- No auth, no rate limit
- Drawback: 31 HTTP requests to get 30 stories (1 list + 30 items)

**RSS feeds**
- Official: `https://news.ycombinator.com/rss` — titles and links only, no scores
- Third-party (hnrss.org): `https://hnrss.org/frontpage` — customizable, supports filtering by points (`?points=100`), keywords, etc.
- `https://hnrss.org/best?points=200` is a good serendipity filter — high-scoring HN stories tend to surface intellectually stimulating content across all topics

**Verdict:** Use Algolia API. One call, structured data, zero setup.

### Ars Technica

- RSS: `https://feeds.arstechnica.com/arstechnica/index` (main feed)
- Category feeds: `https://arstechnica.com/ai/feed`, `https://arstechnica.com/science/feed`, etc.
- No auth, no rate limits, no paywall
- Feed provides summaries (possibly full text — reports vary)
- Reliable, well-maintained

### The Verge

- RSS: `https://www.theverge.com/rss/index.xml`
- Category feeds: `/rss/entertainment/index.xml`, `/rss/environment/index.xml`, etc.
- Free tier: excerpts only (full-text RSS requires paid subscription)
- No auth for free feed

### TechCrunch

- RSS: `https://techcrunch.com/feed/`
- Category feeds: `https://techcrunch.com/category/artificial-intelligence/feed/`, etc.
- Generous excerpts (often multiple paragraphs)
- No auth, no paywall on RSS

### Wired

- RSS: `https://www.wired.com/feed/rss`
- Tag feeds: `https://www.wired.com/feed/tag/ai/latest/rss`
- ~600 word excerpts — very generous for RSS
- No auth

### MIT Technology Review

- RSS: `https://www.technologyreview.com/feed/`
- Metered paywall on website (~3-5 free articles/month)
- RSS provides headlines and summaries only
- Useful for topic discovery; search for freely available coverage of the same stories

### Summary: Tech Sources

| Source | Best Access | Auth | Content Depth | Reliability |
|--------|-----------|------|---------------|-------------|
| Hacker News | Algolia API | None | Titles + URLs + scores | Excellent |
| Ars Technica | RSS | None | Summaries (possibly full) | Excellent |
| The Verge | RSS | None | Excerpts | Good |
| TechCrunch | RSS | None | Generous excerpts | Good |
| Wired | RSS | None | ~600 words | Good |
| MIT Tech Review | RSS | None | Summaries only | Good (paywalled) |

---

## 2. Economics & Finance

The hardest category — most premium econ/finance publications are paywalled. The strategy is: use free blogs and feeds for topic discovery and commentary, then use web search to find freely accessible reporting on the same topics.

### Paywalled (not directly usable)

- **Financial Times** — Hard paywall. RSS provides headlines only. Free account gives a few articles/week. Not usable for the pipeline.
- **Bloomberg** — Hard paywall. No working RSS feeds (dead since ~2023). No free programmatic access.
- **The Economist** — Hard paywall. RSS at `economist.com/[section]/rss.xml` provides headlines only. Useful for topic discovery.

### Freely Accessible

**Marginal Revolution (Tier 1)**
- RSS: `https://marginalrevolution.com/feed`
- Completely free, no paywall, no auth
- 4-5 posts/day since 2003, very reliable
- Tyler Cowen's "assorted links" posts are excellent for topic discovery — curated pointers to interesting economics stories across the web
- Directly matches user's stated interests

**Naked Capitalism (Tier 1)**
- RSS: `https://www.nakedcapitalism.com/feed`
- Completely free, donation-supported
- Daily "Links" posts (curated roundups) plus original analysis
- Strong on finance, regulation, political economy
- Multiple posts daily

**VoxEU / CEPR (Tier 2)**
- RSS: `https://cepr.org/rss/vox-content`
- Completely free (policy research dissemination portal)
- Research-based policy analysis by leading economists
- More academic/policy than breaking news; good for deeper stories

**FRED Blog (Tier 2)**
- RSS: `https://fredblog.stlouisfed.org/feed/`
- Completely free (Federal Reserve Bank of St. Louis)
- Data-focused posts with economic visualizations
- Lower frequency (few times per month) — supplement, not primary

**Reuters (Tier 3 — partial access)**
- Website is freely readable (no paywall on articles)
- RSS feeds were killed in June 2020 — no official feed
- Must rely on web search to discover Reuters stories

**Project Syndicate (Tier 3 — metered)**
- Metered paywall; some free content with registration
- Op-eds by prominent economists (Stiglitz, Roubini, Rogoff)
- Not reliable enough for automated pipeline

**Scott Sumner / The Money Illusion (Tier 3 — niche)**
- Moved to Substack: `https://scottsumner.substack.com/feed`
- Free, monetary economics focus
- Lower posting frequency

### Strategy for Econ/Finance

Since premium sources (FT, Bloomberg, Economist) are paywalled, the pipeline should:
1. Check Marginal Revolution and Naked Capitalism RSS for topic inspiration
2. Use web search to find freely accessible reporting on today's macro/finance stories (Reuters web articles, AP News, wire service coverage will surface)
3. Use Economist/FT RSS headlines for topic discovery when needed

---

## 3. Climate Science

### Freely Accessible (Tier 1)

**Carbon Brief**
- RSS: `https://www.carbonbrief.org/feed/`
- Completely free, no paywall
- WordPress-based (stable RSS)
- One of the best climate journalism outlets — accessible, well-written
- Covers science, energy, and policy

**Yale Climate Connections**
- RSS: `https://yaleclimateconnections.org/feed/`
- Completely free
- Part of Yale Program on Climate Change Communication
- Good topical breadth: policy, science, extreme weather, solutions
- Tone matches well with the newsletter's conversational approach

**Inside Climate News**
- RSS: `https://insideclimatenews.org/feed/`
- Completely free (nonprofit, Pulitzer Prize-winning)
- Strong US-focused investigative climate journalism
- Good for policy, energy transition, environmental justice

**The Conversation (Environment section)**
- Feed: `https://theconversation.com/us/environment/articles.atom` (Atom format)
- Completely free (Creative Commons licensed)
- Written by researchers, edited for general readability
- Great middle ground between journal papers and journalism

### Useful but with Caveats (Tier 2)

**Climate Home News**
- RSS: `https://www.climatechangenews.com/feed/`
- Free, WordPress-based
- Focus: international climate politics, COP negotiations
- Good for international policy angle

**RealClimate**
- RSS: `https://www.realclimate.org/index.php/feed/`
- Free, run by working climate scientists
- Low frequency (few posts per month)
- More technical — good for "big picture" discussions

**NASA Climate**
- RSS: `https://climate.nasa.gov/news/rss.xml`
- Free (government content)
- **Uncertain reliability** — current administration has cut NASA science budget ~50%, may reduce or stop publishing climate content
- Monitor for freshness; have fallback ready

**Copernicus C3S**
- Press releases at `https://climate.copernicus.eu/press-releases`
- RSS feed URL unclear for the climate subdomain
- Mainly monthly climate bulletins — infrequent
- Better to catch Copernicus releases via Carbon Brief or Yale CC coverage

### Not Usable

**NOAA / climate.gov** — climate.gov was shut down June 2025 (staff terminated). Redirects to main NOAA site. Dead for pipeline purposes.

**Nature Climate Change** — Hard paywall. RSS at `https://www.nature.com/nclimate.rss` provides titles/abstracts only. Useful for topic discovery, not content.

### Strategy for Climate

Carbon Brief, Yale Climate Connections, and Inside Climate News are excellent free sources with reliable RSS. For the pipeline, these three alone provide good daily coverage. The Conversation adds academic depth. Web search supplements with stories from sources that don't have RSS or are paywalled.

---

## 4. Michigan Sports (Football & Basketball)

### Sources

**MGoBlog (best Michigan-specific source)**
- RSS: `https://mgoblog.com/rss.xml` (Drupal-based)
- Alternate: `http://feeds.feedburner.com/mgoblog` or `https://mgoblog.com/fbfeed`
- Free, no paywall (premium community board exists separately)
- Gold standard for Michigan analysis — tactical breakdowns, recruiting, game coverage
- **RSS reliability issues documented** — community reports intermittent feed breakage
- Multiple posts daily during football season, lighter in summer
USER: This is my personal favorite

**Maize n Brew (SB Nation)**
- RSS: `https://www.maizenbrew.com/rss/index.xml` (needs verification — SB Nation redesigned all sites Aug 2025)
- Free, fan-community site
- Good quality, covers football and basketball equally
- Multiple posts daily during season

**MLB.com / official sources** — N/A for Michigan college sports

**ESPN** — College football RSS at `https://www.espn.com/espn/rss/ncf/news` covers all FBS, not Michigan-specific. Web search is better for Michigan-specific ESPN content.

**MLive** — Dedicated Michigan beat reporters, but soft paywall and uncertain RSS URL. Content surfaces well via web search.

**The Athletic** — Hard paywall (NYT-owned). Headlines appear in search results but full text inaccessible.

**247Sports** — Dominant for recruiting news. Feed URL format uncertain. Free tier exists but is recruiting-heavy.

**Big Ten Network** — RSS at `https://btn.com/feed` covers all Big Ten schools. Too broad for Michigan-specific needs.

USER: I also recommend examining UMhoops.com

### Seasonal Patterns

| Sport | In-Season | Offseason | Quietest Period |
|-------|-----------|-----------|-----------------|
| Michigan Football | Sep–Jan | Feb–Aug | Jun–Jul |
| Michigan Basketball | Nov–Apr | May–Oct | Jul–Sep |
| Overlap | Nov–Jan (both active) | Jun–Aug (both quiet) | |

- Football offseason still has content: recruiting (Dec signing, Feb NSD), spring practice (Mar–Apr), transfer portal
- Basketball offseason: transfer portal (Apr–May), summer recruiting visits
- **No special pipeline logic needed** — web search naturally returns fewer results during quiet periods; the `selection_note` in `interests.json` already says "don't force every category into every issue"

### Strategy for Michigan Sports

**Web search is the primary approach.** Michigan sports sources have unreliable or uncertain RSS feeds, and web search naturally surfaces MGoBlog, MLive, ESPN, and other content. Queries like "Michigan Wolverines football news" and "Michigan basketball" are specific enough to get targeted results.

If adding RSS: MGoBlog (`mgoblog.com/rss.xml`) is the highest-value feed to try, but have fallback to web search given documented reliability issues.

---

## 5. Cubs Baseball

### Sources

**MLB.com Cubs (most reliable)**
- RSS: `https://www.mlb.com/cubs/feeds/news/rss.xml`
- Official source, team-specific, always available
- No auth, no paywall
- Content: game recaps, transactions, injury reports, features
- Factual reporting tone (not opinion/analysis)

**Cubs Insider**
- RSS: `https://www.cubsinsider.com/feed`
- Free, no paywall
- Active — multiple posts daily (verified Mar 2026)
- Good blend of news, rumors, culture, commentary

**Bleacher Nation Cubs**
- RSS: `https://www.bleachernation.com/cubs/feed/`
- Free, established since 2008
- Multiple posts daily, even in offseason
- Opinionated analysis, rumors, trade speculation, good humor
- Use Cubs-specific feed to avoid Bears/Bulls content

**Bleed Cubbie Blue (SB Nation)**
- RSS: `https://www.bleedcubbieblue.com/rss/index.xml`
- Free, fan-community site
- Subject to SB Nation Aug 2025 redesign feed URL changes

**ESPN** — MLB RSS at `https://www.espn.com/espn/rss/mlb/news` is league-wide, not Cubs-specific. Web search is better.

**NBC Sports Chicago** — No confirmed RSS feed URL. Web search only.

USER: The CHICubs subreddit may also be of interest for surfacing stories

### Seasonal Patterns

| Period | Content Level | Topics |
|--------|--------------|--------|
| Apr–Oct (season) | Very high — daily | Game recaps, analysis, standings, trades |
| Nov–Dec | Moderate | Hot stove, free agency, Winter Meetings |
| Jan | Moderate | Cubs Convention, trade rumors |
| Feb–Mar | Rising | Spring Training, roster battles |

Cubs offseason is surprisingly active — Bleacher Nation and Cubs Insider publish daily even Nov–Jan. The pipeline will find content year-round.

### Strategy for Cubs

MLB.com Cubs RSS is the anchor — official, reliable, team-specific. Supplement with Cubs Insider and Bleacher Nation for analysis/opinion. Web search fills gaps from ESPN, NBC Sports, etc.

---

## 6. Serendipitous / General Interest

This category serves the `selection_note` requirement: "Include 1-2 stories outside these core topics that would appeal to a curious, well-read generalist."

### Tier 1 — Free, reliable RSS, high quality, no paywall

**Aeon**
- RSS: `https://aeon.co/feed.rss`
- Category feeds: `https://aeon.co/philosophy.rss`, `https://aeon.co/science.rss`, etc.
- Free, ad-free, funded by donations/grants
- Long-form essays on philosophy, science, psychology, society, culture
- Excellent match for "stories you wouldn't seek out but would love"

**Quanta Magazine**
- RSS: `https://www.quantamagazine.org/feed/`
- Category feeds: `/physics/feed`, `/mathematics/feed`, `/biology/feed`
- Free (Simons Foundation funded)
- Accessible, award-winning science and math journalism
- Relevant to user's science background

**Kottke.org**
- RSS: `https://kottke.org/feed/`
- Free, supported by memberships
- Multiple posts daily since 1998
- Eclectic: science, design, culture, technology, food, art, history
- Posts often link to external content — useful as curated discovery

**Atlas Obscura**
- RSS: `https://www.atlasobscura.com/feeds/latest`
- Free (monetizes via travel experiences)
- Unusual places, hidden histories, weird science, food
- High serendipity factor

**The Marginalian (formerly Brain Pickings)**
- RSS: `https://www.themarginalian.org/feed/`
- Free, ad-free, reader-supported
- Essays on literature, science, philosophy, art
- Deeply thoughtful, unique perspective

### Tier 2 — Good for discovery, but aggregator pattern (linked articles may be paywalled)

**Arts & Letters Daily**
- RSS: `https://www.aldaily.com/feed/`
- Free aggregator (Chronicle of Higher Education)
- ~18 links/week to essays and reviews across humanities
- Links to external articles — some may be paywalled
- Editorial blurbs are themselves useful for topic selection

**Longreads**
- RSS: `https://longreads.com/feed/`
- Free (Automattic/WordPress supported)
- Curated long-form nonfiction, plus original essays
- Similar aggregator pattern — linked articles may be paywalled

**3 Quarks Daily**
- RSS: `https://3quarksdaily.com/feed/`
- Free, eclectic aggregator (science, art, literature, philosophy)
- Active since 2004

### Tier 3 — Usable with caveats

**Nautilus** — RSS at `https://nautil.us/feed/`; soft paywall (2 free articles/month). Summaries from RSS may suffice.

**Smithsonian Magazine** — RSS at `https://www.smithsonianmag.com/rss/` with category feeds. Soft paywall.

**Damn Interesting** — RSS at `https://www.damninteresting.com/feeds/`. Very low posting frequency.

**Wikipedia Current Events** — Structured, factual, global summaries. Third-party RSS at `https://wcepr.exch.gr/`. Good for hard news backbone, not for serendipity.

### Not suitable for pipeline

- **The Browser** — Paid ($48/yr), email-only, no RSS. Gold standard curation but not automatable.
- **Wait But Why** — Essentially dormant (2 posts in 2025).
- **BBC Future** — No dedicated RSS feed confirmed.

### Strategy for Serendipity

Aeon, Quanta, Kottke, and Atlas Obscura form an excellent free serendipity pool. Polling these 4 feeds gives a diverse set of science, culture, history, and ideas stories. Claude selects the most interesting/relevant ones for the day's newsletter.

HN with a high-points filter (`hnrss.org/best?points=200`) is also an excellent serendipity source — viral HN stories often surface exactly the kind of cross-disciplinary content the user would enjoy.

---

## 7. Claude's Built-in Web Search

### Capabilities

- Returns a list of links (title + URL) plus a synthesized summary
- Supports domain filtering (`allowed_domains`, `blocked_domains`)
- Backed by a real search engine
- Currently noted as "only available in the US" — pipeline runs from a CC session, location depends on where Claude's infrastructure routes

### Recency

Tested with 6 queries across all topic areas. Results consistently returned content from 1-3 days ago (March 9-11 for a March 12 search). Did not return same-day content — typical search engine indexing lag. **1-3 day lag is acceptable for a daily newsletter** that is rewriting stories in Chinese, not breaking news.

USER: True, but there's a preference for stories that have happened in the past 36 hours, and a STRONG preference for stories to not repeat from past newsletters unless there's been a substantive update in the story

### Coverage

Strong across all tested categories:
- **Tech/AI**: Specific details (Nvidia GTC, Apple Siri rewrite, OpenAI acquisition)
- **Economics/Finance**: Macro data (GDP forecasts, unemployment, Fed rate expectations)
- **Michigan sports**: Very specific game results, records, tournament seedings
- **Climate science**: Recent peer-reviewed research summaries
- **Cubs baseball**: Spring training details, roster moves, Opening Day dates
- **Hacker News**: Found specific front-page stories with titles from HN archives

### Rate Limits

No explicit per-session limit documented. 5-10 searches per pipeline run is well within practical limits.

### WebSearch vs. RSS/API

| Factor | WebSearch | RSS/API Fetching |
|--------|-----------|-----------------|
| Setup | Zero — built-in | Must curate feed URLs |
| Recency | 1-3 day lag | Real-time (minutes) |
| Content | Synthesized summaries | Raw titles + links (sometimes full text) |
| Flexibility | Any query, any topic | Only configured feeds |
| Determinism | Results vary by ranking | Same feed = same items |
| Structured data | Unstructured | Structured XML/JSON |
| Maintenance | None | Feed URLs can break |

### WebFetch for RSS

WebFetch converts HTML to markdown via an AI model — **not suitable for RSS XML**. For raw RSS/API fetching, `curl` via Bash is the correct tool. WebFetch is useful for reading article pages when more context is needed.

---

## 8. Recommended Sourcing Strategy for MVP

### Design Principles

1. **Web search first** — Claude's web search is the simplest approach and covers all topics well. It requires zero infrastructure and handles seasonality naturally.
2. **RSS/API for high-value, reliable sources** — A small number of direct feeds supplement web search where they add clear value (structured data, guaranteed coverage, topic discovery).
3. **Minimal complexity** — The MVP should not require maintaining a large feed list. Start small, add feeds only when web search proves insufficient for a category.

### MVP Pipeline: Two-Phase Discovery

**Phase 1: Direct feed check (structured, fast)**

Fetch these 4 feeds via `curl` in the pipeline for guaranteed story candidates:

| Feed | URL | Purpose |
|------|-----|---------|
| HN front page | `https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30` | Tech/AI + serendipity |
| Marginal Revolution | `https://marginalrevolution.com/feed` | Econ topic discovery |
| Carbon Brief | `https://www.carbonbrief.org/feed/` | Climate stories |
| MLB.com Cubs | `https://www.mlb.com/cubs/feeds/news/rss.xml` | Cubs coverage |

These four were chosen because they are: (a) the highest-signal source for their category, (b) completely free with no auth, (c) proven reliable, and (d) provide content not easily replicated by web search alone (HN scores, MR's curated links, Carbon Brief's climate depth, official Cubs news).

**Phase 2: Web search expansion (flexible, broad)**

Run 4-6 targeted web searches to fill gaps and find serendipitous stories:

1. `"top tech AI news today"` — catches stories HN might miss (Ars, Verge, Wired)
2. `"economics finance news"` — surfaces Reuters, AP, freely readable macro coverage
3. `"Michigan Wolverines [football/basketball] news"` — seasonal, covers MGoBlog/ESPN/MLive
4. `"climate science news this week"` — supplements Carbon Brief
5. `"interesting science culture essays"` or similar broad query — serendipity
6. Optional: topic-specific search based on what's trending in Phase 1 feeds

### Story Selection

After both phases, Claude has ~50-80 candidate stories. Claude then:
- Selects 5 for the newsletter + 3 runner-up headlines for Editor's Desk
- Follows the `selection_note` from `interests.json` (variety, lead with most interesting, don't force every category)
- Considers `preference_history.json` for alignment with user taste

### Future Enhancements (not MVP)

If web search proves insufficient for any category, add targeted RSS feeds:

- **More serendipity**: Aeon (`aeon.co/feed.rss`), Quanta (`quantamagazine.org/feed/`), Kottke (`kottke.org/feed/`)
- **More climate**: Yale Climate Connections, Inside Climate News, The Conversation
- **More econ**: Naked Capitalism, VoxEU/CEPR
- **More Cubs analysis**: Cubs Insider, Bleacher Nation
- **Michigan (if web search is weak)**: MGoBlog (with caveat about RSS reliability)

### What This Approach Avoids

- No API keys or authentication required
- No paid subscriptions needed
- No fragile scraping of paywalled sites
- No large feed list to maintain
- No special seasonal logic — web search and story selection handle it naturally
- No RSS parsing library — just `curl` for 4 feeds + Claude's native JSON/XML reading

### Tradeoffs Accepted

- **1-3 day lag on web search results** — acceptable; the newsletter rewrites stories for language learning, not breaking news
USER: See above for preferences
- **HN bias toward tech** — mitigated by dedicated econ, climate, and sports feeds + searches
USER: bias is specifically towards generative AI more than tech writ large. Climate is far and away least important, only if stories are directly relevant to my work as a hurricane catastrophe modeler for industry (large loss event, change in provided data sources or agencies or the climate research establishment)
- **No guaranteed Michigan sports coverage** — web search handles this well in-season; offseason naturally has fewer stories, which is fine per `selection_note`
- **RSS feeds can break** — only 4 feeds to monitor, and web search is always the fallback
