---
name: scrape-via-recorded-client
description: >
  Use when you need repeated or programmatic access to a website's data and
  the current plan is "control a browser every time" (Playwright/Puppeteer/
  browser-use). Record one real browsing session into a HAR file (network
  requests) or an MHTML snapshot (rendered DOM), reverse-engineer the
  underlying API or data shape from that recording, then write a small script
  or CLI that hits it directly. Turns a slow, expensive, flaky
  browser-automation loop into a fast, cheap, deterministic one. Trigger
  phrases: "build a CLI for this site", "scrape X repeatedly", "I don't want
  to drive a browser every time", "derive a client from this website".
---

# Scrape via Recorded Client

Don't make an agent (or a script) drive a real browser every time you need
data from a website. Drive the browser **once**, record what happened, then
build a lightweight client from the recording. Re-run the client, not the
browser.

## Decision: HAR vs MHTML

| Site behavior | Record as | Why |
|---|---|---|
| Data comes back as JSON/XHR from an internal API (most modern SPAs: search results, listings, prices) | **`.har`** (HTTP Archive) | The network log contains the exact request (URL, method, headers, auth token/cookies, body) and response (JSON) you need. You can replay that request directly with `curl`/`fetch`/`httpx` — no browser, no JS, no rendering. |
| Data only exists after client-side JS mutates the DOM and never appears as a clean API response (canvas-rendered content, heavily obfuscated/batched GraphQL blobs, server-side-rendered-then-hydrated pages where the useful markup is the final DOM, not any single response) | **`.mhtml`** (MIME HTML web archive) | MHTML captures the browser's *fully rendered* DOM plus all its resources as one self-contained file. You get the end state you'd otherwise have to wait for and click through, saved as plain text you can parse offline with a normal HTML parser (cheerio, BeautifulSoup, lxml). |

Rule of thumb: try HAR first (cheaper — the resulting client is just HTTP
calls, no HTML parsing). Only fall back to MHTML when you've inspected the
HAR and the data genuinely isn't in any response body — it's assembled or
rendered client-side.

## Workflow

1. **Drive the browser once, manually or via browser-control tooling**, doing
   exactly the interaction you want to automate later (search, apply a
   filter, scroll to load more, log in, etc.).
2. **Capture the recording:**
   - HAR: browser DevTools → Network tab → right-click → "Save all as HAR
     with content" (or ask a browser-automation tool/MCP server to dump the
     HAR for the session). Make sure "preserve log" is on and content bodies
     are included, not just headers.
   - MHTML: browser → "Save Page As" → format "Webpage, Single File" (Chrome)
     produces `.mhtml`. Do this *after* the DOM state you care about has
     fully loaded/rendered.
3. **Inspect the recording to find the signal:**
   - HAR: open it as JSON, filter `entries[].request.url` for XHR/fetch calls
     that return the data you saw on screen. Note method, URL pattern, query
     params, required headers (auth token, cookie, `x-csrf`, user-agent),
     and the response JSON shape.
   - MHTML: it's a MIME multipart text file — the first `text/html` part is
     the fully rendered page. Parse it with a normal HTML parser; ignore the
     embedded image/CSS parts unless you need them.
4. **Write the minimal client** (a script or small CLI) that reproduces just
   the request(s) or parse step you identified — no browser dependency.
   Keep any auth token/cookie as a config value, since it will expire; the
   *shape* of the request/response is what's durable, not the captured
   credentials.
5. **Verify** the client's output against what you saw in the browser before
   relying on it, and note that sites can change their internal API or DOM
   structure — treat the client as disposable and cheap to regenerate the
   same way if it breaks.

## Gotchas

- Captured auth tokens/cookies in the HAR are secrets with a short lifespan
  — don't commit the raw HAR/MHTML to a repo; extract only the request
  shape and re-authenticate normally in the client.
- Some endpoints require replaying multiple prior requests (e.g. a
  session-establishing call before the data call) — check the HAR's request
  order, not just the one call that returned the payload you wanted.
- Respect the target site's terms of service and rate limits — this
  technique is for personal/authorized use, not building a scraping product
  against a site that disallows it.
- If the site rotates request signing (HMAC-signed params, per-request
  nonces) you can't just copy the URL — you'll need to find and reimplement
  the signing logic, which may make the "browser every time" approach
  actually cheaper. Check for this before investing in a client.
