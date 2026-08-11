# ECHO Protocol v1.0

**Standard way for swarm agents to request clean extraction from ECHO.**

## Overview

When ALPHA, BRAVO, or CHARLIE needs high-quality structured text from a URL (especially government pages or news articles), they should delegate to **ECHO** using this protocol instead of relying on raw `web_fetch` output.

## How to Request ECHO

Any swarm agent can request ECHO services by spawning a new subagent using the ECHO prompt template and passing the following structured request:

### Request Format

```
ECHO REQUEST

URL: [exact URL]
MODE: [auto | html | pdf]
SELECTOR: [optional CSS selector, e.g. "article", "#content", ".post-body"]
EXTRACT_TABLES: [true | false]
INSTRUCTIONS: [any special extraction requirements]
```

### Example Request (from ALPHA)

```
ECHO REQUEST

URL: https://burlison.house.gov/media/press-releases/burlison-presses-mitre-answers-uap-records-ffrdc-accountability-and-compliance
MODE: html
SELECTOR: #main-content
EXTRACT_TABLES: false
INSTRUCTIONS: Extract the full body text of the press release, including the legislative interrogatories section if present.
```

### Example Request (from BRAVO)

```
ECHO REQUEST

URL: https://www.rt.com/news/640673-iran-targeted-us-base/
MODE: html
SELECTOR: .article__text
EXTRACT_TABLES: false
INSTRUCTIONS: Return only the main article body text, removing all navigation, ads, and sidebars.
```

## Response Format (from ECHO)

ECHO should always return results in this structure:

```json
{
  "url": "...",
  "status": "success" | "error",
  "content_type": "html" | "pdf",
  "title": "...",
  "main_text": "...",
  "word_count": 1234,
  "tables": [...],           // only if requested
  "links": [...],            // optional
  "source_domain": "..."
}
```

## When Agents Should Use ECHO

**Use ECHO when:**
- The page contains important primary content (press releases, official statements, reports).
- Raw `web_fetch` returns too much noise (navigation, footers, scripts).
- You need clean text for accurate analysis or citation.
- You need structured tables from HTML or PDF documents.

**Do NOT use ECHO for:**
- Quick link checking.
- Social media / X posts (use normal search).
- Pages that are already clean or very small.

## Integration with Main Agents

- **ALPHA** (Primary Sources): Should use ECHO on important .gov and congressional pages.
- **BRAVO** (Zero-Trust): Should use ECHO on key articles from RT, TASS, Global Times, Press TV when doing deep framing analysis.
- **CHARLIE** (Signals + Narrative Warfare): Can use ECHO to cleanly extract long articles when analyzing narrative warfare campaigns.

## Error Handling

If ECHO returns an error, the requesting agent should:
1. Fall back to normal `web_fetch`.
2. Note the limitation in its output.
3. Consider trying a different URL or selector.

## Version History

- v1.0 — Initial protocol with BeautifulSoup + basic PDF support (May 2026)
