# Pitfalls Research

**Domain:** x402 API Network v2.0 — Site Launch & Platform Polish
**Researched:** 2026-03-15
**Confidence:** HIGH (Cloudflare SSL, crawl dedup, Resend limits), MEDIUM (DOCX conversion, Starlight nav)

---

## Critical Pitfalls

### Pitfall 1: Cloudflare SSL "Flexible" Mode Causes Infinite Redirect Loop

**What goes wrong:**
When Cloudflare's SSL/TLS encryption mode is set to "Flexible", Cloudflare connects to the origin server using plain HTTP. If nginx has any HTTP-to-HTTPS redirect rule (e.g., `return 301 https://$host$request_uri`), the request loops: browser connects HTTPS to Cloudflare, Cloudflare connects HTTP to nginx, nginx redirects to HTTPS, Cloudflare connects HTTP again, and the browser receives `ERR_TOO_MANY_REDIRECTS` after ~20 iterations.

This is the single most common self-hosting mistake with Cloudflare. The existing transcription service avoids this because Cloudflare Tunnel bypasses the proxy entirely — but a new tunnel-or-proxy setup for the brand site will hit this if configured carelessly.

**Why it happens:**
"Flexible" appears safer because you don't need an origin SSL certificate, making it tempting for home servers. The mode name implies "flexible support for both HTTP and HTTPS origins" — developers assume it means "handle either gracefully" but it actually means "always use HTTP to the origin regardless of what the origin returns."

**How to avoid:**
Two valid approaches depending on the setup chosen:

- **Cloudflare Tunnel (recommended — matches existing pattern):** Point the tunnel at `http://localhost:8888`. Cloudflare terminates TLS at the edge. No origin certificate needed. Do NOT put an HTTP-to-HTTPS redirect in nginx. Set Cloudflare SSL mode to "Full" (not Flexible, not Full Strict — origin has no cert in tunnel mode).

- **Direct proxy with origin cert:** Generate a Cloudflare Origin Certificate (free, valid 15 years, never expires). Install it in nginx. Set Cloudflare SSL mode to "Full (Strict)". Then adding HTTP-to-HTTPS redirects in nginx is safe because Cloudflare will connect via HTTPS.

**Warning signs:**
- `ERR_TOO_MANY_REDIRECTS` immediately after enabling Cloudflare proxy
- nginx access logs showing repeated `301` responses to the same request
- Chrome DevTools Network tab showing redirect chain cycling between `http://` and `https://` URLs

**Phase to address:**
Custom Domain / SSL setup phase. Verify before adding any HTTP redirect rules to nginx.

---

### Pitfall 2: Crawled URLs Bypass SSRF Validation Because They Were Discovered, Not User-Supplied

**What goes wrong:**
The existing scraping API has SSRF middleware that validates the initial user-supplied URL against private IP ranges (10.x, 172.16.x, 192.168.x, 127.x, 169.254.x). Multi-page crawling discovers new URLs by extracting links from crawled pages. If those discovered URLs are fed back into the scraping pipeline without re-running SSRF validation, a malicious page can embed links to internal resources (`http://10.0.0.2:8888/admin`, `http://169.254.169.254/latest/meta-data/`). The crawler will fetch them because they came from a "trusted" crawl, not from user input.

This is the same vulnerability class as CVE-2026-26019 (LangChain RecursiveUrlLoader SSRF bypass) — the crawler trusted discovered URLs but not their resolved destinations.

**Why it happens:**
SSRF middleware is typically wired to the request entrypoint and validates user input. Developers mentally categorize discovered URLs as "internal" data and don't re-route them through the same validation. The code path is literally different: user URL goes through the FastAPI endpoint validator; discovered URLs often go through a queue or set that bypasses the endpoint entirely.

**How to avoid:**
Validate every URL before fetch, regardless of how it was discovered. Apply the same IP-block logic to crawled links:

```python
# WRONG — validates user input only
@app.post("/crawl")
async def crawl(url: str = Body(...)):
    validate_ssrf(url)  # only runs once
    discovered = await fetch_links(url)  # feeds back unvalidated

# RIGHT — validate at the fetch layer, not the entrypoint
async def safe_fetch(url: str):
    validate_ssrf(url)  # runs for every URL fetched
    return await playwright_fetch(url)
```

Also: normalize URLs before validation — `http://127.1/` resolves to loopback, URL-encoded characters can obscure schemes, and `0.0.0.0` is a valid loopback alias on Linux.

**Warning signs:**
- Crawl function receives a URL without calling the SSRF validator
- Discovered URLs added to a queue/set without validation
- SSRF validator only called at the API route level

**Phase to address:**
Multi-page crawl implementation phase. Treat this as a pre-merge security check: every code path that calls `playwright_fetch` or `httpx.get` must call `validate_ssrf` first.

---

### Pitfall 3: Crawl Enters Infinite Loop on Sites With Pagination or Infinite Scroll

**What goes wrong:**
Sites with paginated content (`?page=1`, `?page=2`, ...) or query-string-parameterized views generate an unbounded number of distinct URLs, all within the same domain. A naive crawler that tracks visited URLs and queues all same-domain links will never terminate — it exhausts memory before completing, or runs until the Railway 512MB limit kills the container mid-request.

Common triggers: e-commerce sites, documentation with search URLs, sites that append session tokens to URLs, JavaScript-rendered infinite scroll that writes distinct anchor hashes.

**Why it happens:**
Developers test on small static sites where link discovery terminates naturally. The visited-URL set correctly prevents revisiting the same exact URL, but does not prevent fetching 10,000 paginated variants. Setting "max pages" as a cap requires the developer to think about it upfront — it's easy to omit when prototyping.

**How to avoid:**
Hard-code mandatory limits with sane defaults. Both must be enforced simultaneously:

- `max_pages` parameter (default: 10, max allowed: 50) — abort when hit
- `max_depth` parameter (default: 2) — do not follow links more than N levels from the seed URL
- URL normalization before deduplication — strip query params that don't affect content (e.g., session IDs, analytics params like `utm_*`, `ref=`) OR strip ALL query params for visited-URL tracking
- Visited-URL set caps at `max_pages * 5` entries to avoid memory growth from URL discovery exceeding fetch rate

For Railway 512MB constraint: a Playwright browser context uses ~80-150MB. Two concurrent contexts (seed + one discovered link) uses 250-350MB. Do not launch more than one context per crawl request; crawl serially with a single context.

**Warning signs:**
- Crawl function has no `max_pages` limit
- Visited URL set grows unboundedly
- Test site is a static multi-page blog that happens to terminate at 5 pages

**Phase to address:**
Multi-page crawl implementation phase. Define and document `max_pages` and `max_depth` before writing a single line of link-discovery code.

---

### Pitfall 4: Resend Rejects Attachments Sent via Batch Endpoint

**What goes wrong:**
Resend's batch send endpoint (`/emails/batch`) does not support attachments. Sending a request with `attachments` to the batch endpoint returns an error. This is a documented limitation but easy to miss when adding attachment support to an existing email service that may use batching internally.

Separately: Resend has a 40MB total email size limit that applies after Base64 encoding. Base64 encoding inflates binary file size by ~33%, so a 30MB file attachment becomes ~40MB encoded — hitting the limit exactly. A 25MB file is the practical safe maximum.

**Why it happens:**
Developers copy the sending implementation from a batching code path when adding attachments. The Base64 inflation is a universal email protocol property that most developers don't account for at implementation time — they check file size before encoding.

**How to avoid:**
- Route all emails with attachments through the single-send endpoint, not the batch endpoint
- Validate attachment size before Base64 encoding: `if file_size_bytes > 25 * 1024 * 1024: raise ValueError("Attachment too large")`
- Check MIME type against Resend's allowed list before encoding — Resend blocks certain executable types
- The `content` field in Resend's attachment object must be Base64 string (not bytes). In Python: `base64.b64encode(file_bytes).decode("utf-8")`

**Warning signs:**
- Email sending route uses a batch call path
- File size check happens after base64 encoding
- `content` field set to raw bytes instead of a decoded string

**Phase to address:**
Email attachments / CC/BCC implementation phase. Verify against Resend's current attachment docs before writing the implementation.

---

### Pitfall 5: DOCX-to-PDF on Linux Fails Silently Due to Missing Windows Fonts

**What goes wrong:**
Common DOCX documents use Windows/Office fonts: Calibri, Cambria, Times New Roman, Arial, Wingdings. These fonts are not installed on a stock Linux/Debian container (Railway's base environment). Lightweight Python libraries (`python-docx`, `mammoth`) that convert DOCX to HTML or then to PDF via WeasyPrint will substitute system fonts (DejaVu, Liberation, etc.). The PDF renders without error, looks "done" during testing, but has wrong line heights, overflowing text boxes, misaligned tables, and broken page breaks.

This is the #1 cause of "works on my Mac, broken in production" for DOCX conversion. The Railway container returns HTTP 200 with a valid PDF — the broken layout is a content problem, not a server error.

**Why it happens:**
Developers test conversion on their Mac where Calibri and other fonts are installed via Microsoft Office. The conversion succeeds silently on Linux using font substitution — no error, no warning, corrupted layout.

**How to avoid:**
Two strategies, pick one:

1. **Scope the feature to simple DOCX only** — document in the API that complex layouts (tables, columns, custom fonts) will have degraded output. Suitable for the v2.0 MVP since this is an extension of the existing conversion API, not a full Office suite replacement.

2. **Install Microsoft-compatible fonts** — add `ttf-mscorefonts-installer` (or manually install Liberation fonts as open-source equivalents) to the Railway Dockerfile. Liberation fonts are metric-compatible with Arial, Times New Roman, and Courier New, catching the most common substitutions.

Avoid `docx2pdf` entirely on Linux — it requires Microsoft Word to be installed and will fail immediately on Railway.

For Railway: use mammoth (DOCX → HTML) + WeasyPrint (HTML → PDF). WeasyPrint uses less memory than browser-based approaches and has no JS runtime. Test with a real-world DOCX containing tables and mixed fonts before shipping.

**Warning signs:**
- Testing conversion only with simple single-column, single-font documents
- No font installation step in the Railway Dockerfile
- Using `docx2pdf` library (will fail on Linux — requires Word)

**Phase to address:**
DOCX conversion implementation phase. Before writing the endpoint, create a test DOCX with Calibri font, a table, and a multi-column layout. Attempt conversion on Railway and inspect the PDF output.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|----------------|-----------------|
| Use Cloudflare SSL "Flexible" mode | No origin cert needed | Redirect loops when any redirect rule is added | Never — use Tunnel (HTTP backend) or Full Strict (with origin cert) |
| Skip SSRF validation on discovered crawl URLs | Simpler code path | SSRF vulnerability — attackers can probe internal network via crawl | Never |
| No `max_pages` limit on crawl | Simple code | Memory exhaustion, Railway OOM kills, slow DoS vector | Never |
| Test DOCX conversion with simple single-font docs | Fast feedback loop | Font substitution bugs invisible until real-world use | Never in production sign-off |
| Manually list all sidebar items in Starlight config | Explicit ordering | Config drift when adding/renaming pages, silent stale entries | Acceptable for small stable nav sections (top-level only) |

---

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|-------------|----------------|------------------|
| Cloudflare Tunnel + nginx | Pointing tunnel at `https://localhost:8888` and expecting Cloudflare to handle TLS end-to-end | Point tunnel at `http://localhost:8888`; Cloudflare terminates external TLS at the edge |
| Cloudflare Proxy (non-tunnel) + nginx | Using "Flexible" SSL mode with HTTP-to-HTTPS redirect in nginx | Use "Full (Strict)" with a Cloudflare Origin Certificate, or switch to Tunnel |
| Resend attachments | Passing file bytes directly as `content` field | Base64-encode first: `base64.b64encode(data).decode("utf-8")` |
| Resend batch + attachments | Using batch endpoint for emails with attachments | Use single-send endpoint when attachments are present |
| mammoth DOCX conversion | Treating HTML output as complete — missing styles, headers not mapped | Configure explicit style maps for Heading 1/2/3; test with real-world documents |
| WeasyPrint on Railway | Assuming fonts available from previous container | Explicitly install Liberation or MS fonts in Dockerfile |
| Starlight sidebar autogenerate | Mixing autogenerated directories with manually listed items in the same config block | Keep autogenerated groups in separate directories from manually configured items |
| Playwright crawl + SSRF | Extracting links from page and queueing without re-validating | Every URL handed to a fetch function must pass through `validate_ssrf()` |

---

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|----------------|
| Multiple Playwright browser contexts per crawl request | Railway OOM kill mid-crawl, 502s from the service | One browser context per request; close it in `finally` block | Second concurrent request on 512MB Railway instance |
| Python `set()` for visited URLs with no size cap | Memory grows until OOM on large sites | Cap set size at `max_pages * 5`; abort crawl when cap hit | ~5,000 URLs discovered (set uses ~2MB/1000 string entries) |
| Crawling entire domain when user only wants N pages | Slow response times, Railway timeout (300s default) | Enforce `max_pages` before queueing; BFS not DFS to get best pages first | Sites with > 50 same-domain links on the seed page |
| WeasyPrint rendering large complex DOCX-derived HTML | 30-60s conversion times, Railway timeout | Set page complexity expectations; reject documents over a threshold size | Documents with >50 pages or complex float layouts |
| Starlight full rebuild on every doc change | Slow CI/CD iteration during docs sprint | Use `astro dev` locally; only rebuild for deployment; Pagefind index builds at deploy time | Sites with >200 pages (build time starts exceeding 30s) |

---

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Not re-validating discovered crawl URLs | SSRF — internal service probing, cloud metadata access | Validate every URL at the fetch layer, not just the API entrypoint |
| Crawl follows `javascript:` or `data:` scheme links | XSS vector if content is rendered; unexpected behavior | Filter links to `http://` and `https://` schemes only before queueing |
| Crawl follows open redirects to external domains | Escapes same-origin restriction; can fetch attacker-controlled content | Validate that the final resolved URL (after redirects) matches the seed domain |
| Accepting DOCX files from user upload without size cap | OOM on Railway from malicious large files | Enforce max upload size (e.g., 10MB) before attempting conversion |
| Logging email attachment content for debugging | Sensitive data in Railway logs | Log only filename and size, never content |
| Cloudflare "Always Use HTTPS" enabled without Full/Full Strict | Redirect loop when origin serves HTTP | Use with Tunnel (origin serves HTTP natively) or add origin cert |

---

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-----------------|
| Crawl returns all pages as flat array with no structure | Agent has to infer site structure from flat list | Return structured result: `{ seed: {...}, pages: [{url, depth, content}] }` |
| DOCX conversion returns generic 500 on font substitution | User thinks conversion failed; output is silently wrong | Return 200 with `warnings: ["Font substitution applied — layout may differ from original"]` |
| Email attachment error after 30s encode attempt | Timeout with no feedback | Validate file size and type synchronously before Base64 encoding |
| Doc pages missing from Starlight sidebar | Users can't find API reference | Verify every new doc page appears in the sidebar before deployment |
| Custom domain accessible but `http://x402.jameswisdom.ink` still works alongside HTTPS | Mixed signals in docs/README; security perception | Enable "Always Use HTTPS" in Cloudflare after tunnel is confirmed working |

---

## "Looks Done But Isn't" Checklist

- [ ] **Cloudflare tunnel for brand site:** Tunnel shows "healthy" in dashboard — verify the domain actually loads in an incognito browser tab (not just `curl localhost:8888`) before declaring done
- [ ] **SSL/custom domain:** HTTPS loads — verify there is no HTTP version still accessible (test `http://x402.jameswisdom.ink` explicitly); verify no mixed content warnings in browser console
- [ ] **Multi-page crawl:** Returns results for a 5-page site — test with a site known to have pagination (e.g., a blog with page=2 URLs) to verify `max_pages` cap fires correctly
- [ ] **SSRF on crawl:** Existing validator passes for the seed URL — verify discovered URLs also pass through validation, not just the initial endpoint
- [ ] **Email attachments:** Attachment sends successfully with a 1KB PDF — test with a 25MB file to verify size rejection works; test with an .exe to verify type rejection
- [ ] **DOCX conversion:** Simple single-column DOCX converts correctly — test with a DOCX containing a table and Calibri font before declaring Railway deployment done
- [ ] **Resend CC/BCC:** Email sends with CC — verify the CC recipient actually receives the email (check inbox, not just API 200 response)
- [ ] **Starlight nav:** New doc pages are visible in sidebar — check each new page is either in autogenerate directory or manually listed; draft pages are hidden in production builds

---

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|---------------|----------------|
| Redirect loop (Cloudflare SSL mode) | LOW | Change SSL mode in Cloudflare dashboard from Flexible to Full or Off; takes effect in <60s |
| Crawl OOM kills Railway container | LOW | Railway auto-restarts; add `max_pages` limit and redeploy; no data loss |
| SSRF discovered URL exploited | HIGH | Audit Railway service logs for internal IP requests; patch by adding validation at fetch layer; rotate any exposed secrets |
| DOCX conversion broken in production | MEDIUM | Roll back Railway deploy to previous working version; fix font installation in Dockerfile; redeploy |
| Resend attachment rejected (wrong endpoint) | LOW | Route attachment emails to single-send endpoint; no infra change needed |
| Starlight page missing from nav | LOW | Add to sidebar config or rename to match autogenerate pattern; rebuild and redeploy |

---

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|------------------|--------------|
| Cloudflare redirect loop | Custom domain / SSL phase | Load site in incognito browser; check Cloudflare SSL mode setting matches tunnel vs proxy setup |
| Mixed content after SSL | Custom domain / SSL phase | Browser DevTools → Console; check for mixed content warnings on all pages |
| Discovered URL SSRF bypass | Multi-page crawl phase | Code review: trace every URL that reaches a fetch call; unit test with `http://10.0.0.1/` as a discovered link |
| Crawl infinite loop / OOM | Multi-page crawl phase | Integration test with a paginated site; verify request returns within 30s with capped results |
| Resend batch + attachment error | Email attachments phase | Check routing before writing attachment code; test with a dummy PDF attachment |
| Base64 size inflation | Email attachments phase | Test with a 26MB file — verify rejection; test with a 24MB file — verify success |
| DOCX font substitution | DOCX conversion phase | Test with a Calibri + table DOCX on Railway before PR merge |
| Missing fonts on Railway | DOCX conversion phase | Inspect Railway deploy logs for font warnings; compare PDF output on Mac vs Railway |
| Starlight nav drift | Docs update phase | After adding pages, run `astro build` and visually audit the sidebar |
| Autogenerate ordering surprises | Docs update phase | Check frontmatter `sidebar.order` on new pages; compare rendered sidebar to intended order |

---

## Sources

- Cloudflare SSL/TLS encryption modes docs: https://developers.cloudflare.com/ssl/origin-configuration/ssl-modes/
- Cloudflare ERR_TOO_MANY_REDIRECTS troubleshooting: https://developers.cloudflare.com/ssl/troubleshooting/too-many-redirects/
- Cloudflare Community: "Why you should choose Full Strict, and only Full Strict": https://community.cloudflare.com/t/why-you-should-choose-full-strict-and-only-full-strict/286652
- Cloudflare mixed content errors: https://developers.cloudflare.com/ssl/troubleshooting/mixed-content-errors/
- LangChain SSRF bypass (CVE-2026-26019) — RecursiveUrlLoader discovered URL validation failure: https://cybersecuritynews.com/langchain-community-ssrf-bypass-vulnerability/
- Playwright memory issues with browser contexts: https://github.com/microsoft/playwright/issues/29163
- Resend attachments documentation: https://resend.com/docs/dashboard/emails/attachments
- docx2pdf Linux limitation (requires Microsoft Word): https://github.com/AlJohri/docx2pdf/issues/95
- WeasyPrint vs Pandoc comparison: https://stackshare.io/stackups/pandoc-vs-weasyprint
- Aspose DOCX font handling on Linux: https://docs.aspose.com/words/python-net/installing-truetype-fonts-on-linux/
- Starlight sidebar autogenerate ordering: https://starlight.astro.build/guides/sidebar/
- Starlight frontmatter reference: https://starlight.astro.build/reference/frontmatter/
- URL deduplication and cycle detection in Python crawlers: https://www.zenrows.com/blog/web-crawler-python
- OWASP SSRF prevention cheat sheet: https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

---

*Pitfalls research for: x402 API Network v2.0 — Site Launch & Platform Polish*
*Researched: 2026-03-15*
