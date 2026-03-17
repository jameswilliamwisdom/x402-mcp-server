# Phase 14: DOCX-to-PDF Conversion - Research

**Researched:** 2026-03-16
**Domain:** Document conversion — mammoth + WeasyPrint pipeline
**Confidence:** HIGH
**Method:** MECE decomposition (3 dimensions: STACK, INTEGRATION, PITFALLS)

---

## Summary

Phase 14 adds DOCX as a fourth input type to the existing conversion API (`x402-conversion-api/main.py`). The implementation is a two-stage pipeline: `mammoth.convert_to_html()` converts DOCX bytes to a semantic HTML fragment, then the existing `weasyprint.HTML(string=...).write_pdf()` path renders the HTML to PDF. mammoth is pure Python with zero system dependencies — the only infrastructure change is adding one line to `requirements.txt` and extending the Dockerfile smoke test.

The conversion is explicitly semantic-fidelity-not-layout-preserving: mammoth maps Word heading styles to `<h1>`–`<h6>`, preserves paragraphs, tables, lists, hyperlinks, and embedded images (as base64 data URIs). Page layout, margins, Calibri/Cambria fonts, table borders, headers/footers, floating objects, and underlined text are not preserved. The existing `fonts-liberation` package in the Dockerfile provides metric-compatible font substitution (Liberation Sans for Calibri/Arial). A pre-merge test with a real Calibri + table DOCX on Railway is a hard gate.

The integration surface is: one new Pydantic model (`DocxConvertRequest`), one new Union member, one new `elif` branch in the dispatch block, one new `sync_docx_to_pdf()` function, one Zod enum update in `src/index.ts`, and service description string updates. All changes are additive — existing `image`, `csv`, and `html_pdf` callers are unaffected. No Dockerfile apt changes, no schema migrations, no new infra.

**Primary recommendation:** Add mammoth to `requirements.txt`, write `sync_docx_to_pdf()` with minimal CSS wrapper, extend the Pydantic union and dispatch block, update the MCP Zod schema — all as a single atomic change set.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CONV-01 | User can convert DOCX to PDF via x402_convert_file tool (type: "docx") | `DocxConvertRequest` Pydantic model + Union extension + `elif body.type == "docx"` dispatch + Zod enum update in `src/index.ts` [STACK, INTEGRATION] |
| CONV-02 | DOCX conversion preserves text, headings, tables, and images (semantic fidelity) | mammoth's default conversion maps Word heading styles → `<h1>`–`<h6>`, paragraphs, `<table>`, lists, `<img src="data:...">` — exactly the four listed content types [STACK, PITFALLS] |
| CONV-03 | Conversion API docs explicitly note "content-document conversion" — not layout-preserving | Service description string update in `main.py` (`GET /`) + `/convert` route docstring + MCP tool description in `src/index.ts` [INTEGRATION, PITFALLS] |

---

## Standard Stack

### Core Libraries

| Library | Version | Purpose | Status |
|---------|---------|---------|--------|
| mammoth | `>=1.12.0` | DOCX → semantic HTML | Add to `requirements.txt` |
| weasyprint | `>=68.1` | HTML → PDF | Already in `requirements.txt` |

**mammoth** (released March 12, 2026) is pure Python — no system dependencies, no apt packages. It accepts a binary file-like object (`BytesIO`) and returns a result with `.value` (HTML fragment string) and `.messages` (list of non-fatal conversion warnings).

**WeasyPrint** is already installed, already tested at build time with a Dockerfile smoke test, and already used by `sync_html_to_pdf()`. No changes to WeasyPrint usage are needed beyond calling it with the mammoth-produced HTML string.

### Supporting Libraries (already present)

| Library | Purpose |
|---------|---------|
| `starlette.concurrency.run_in_threadpool` | Offload sync mammoth + WeasyPrint calls — prevents blocking the event loop |
| `io.BytesIO` | Wrap DOCX bytes as file-like object for `mammoth.convert_to_html()` |
| `tempfile.TemporaryDirectory` | Temp dir pattern for `weasyprint.write_pdf()` output path |
| `zipfile` | Import explicitly to catch `zipfile.BadZipFile` on malformed input |

### Alternatives Ruled Out

| Instead of | Reason |
|------------|--------|
| LibreOffice | +300MB Docker image, headless subprocess, cold-start penalty — deferred to CONV-F01 (v2.x) |
| python-docx | Reads DOCX structure but does not produce HTML or PDF |
| docx2pdf | Wraps LibreOffice/Word COM automation — not viable in headless Linux container |

### Dockerfile Changes

The `apt-get` block requires **no changes** for mammoth (pure Python). `fonts-liberation` is already installed. The smoke test should be extended to verify mammoth imports at build time:

```dockerfile
# Current smoke test — extend to include mammoth
RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf(); import mammoth; print('ok')"
```

`requirements.txt` change — one line added:

```
mammoth>=1.12.0
```

---

## Architecture Patterns

### The Conversion Function

The new `sync_docx_to_pdf()` follows the exact pattern of the existing `sync_html_to_pdf()`. Key differences: no `source_url` parameter, no `base_url` argument to `weasyprint.HTML()`, and the HTML is generated by mammoth rather than decoded from input bytes.

The mammoth HTML output is an **HTML fragment** (no `<html>` or `<body>` tags). It must be wrapped in a minimal HTML document with a `<style>` block before passing to WeasyPrint. Without the style wrapper, WeasyPrint renders bare HTML with no margins, no page size, and no table borders.

```python
def sync_docx_to_pdf(file_bytes: bytes) -> bytes:
    """Convert DOCX bytes to PDF bytes via mammoth + WeasyPrint.

    Pipeline: DOCX → HTML fragment (mammoth) → full HTML document → PDF (WeasyPrint).
    Sync — must be called via run_in_threadpool.
    """
    import mammoth
    from io import BytesIO
    import zipfile

    try:
        result = mammoth.convert_to_html(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise ValueError("Not a valid DOCX file (invalid ZIP archive)")
    except KeyError:
        raise ValueError("Not a valid DOCX file (missing internal document structure)")

    # Log conversion warnings for observability (non-fatal: dropped WMF images, unrecognized styles)
    for msg in result.messages:
        logger.warning("mammoth: %s", msg)

    # Wrap fragment in a full HTML document with minimal baseline CSS
    # CSS required: without it WeasyPrint renders no margins, no page size, invisible table borders
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: "Liberation Sans", sans-serif; font-size: 11pt; line-height: 1.4; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: 4px 8px; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 1em; margin-bottom: 0.4em; }}
p {{ margin: 0.4em 0; }}
</style>
</head>
<body>{result.value}</body>
</html>"""

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        weasyprint.HTML(
            string=html,
            url_fetcher=safe_url_fetcher,
        ).write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()
```

### Dispatch Block Extension

Add a new `elif` branch to the existing `if/elif` dispatch in the `/convert` route handler:

```python
elif body.type == "docx":
    output_bytes = await run_in_threadpool(sync_docx_to_pdf, file_bytes)
    mime_type = "application/pdf"
```

mammoth and WeasyPrint are both blocking/CPU-bound. Using `run_in_threadpool` is mandatory to prevent blocking the FastAPI event loop.

### Pydantic Discriminated Union Extension

```python
class DocxConvertRequest(BaseModel):
    type: Literal["docx"]
    url: BoundedHttpUrl

ConvertRequest = Annotated[
    Union[ImageConvertRequest, CsvConvertRequest, HtmlConvertRequest, DocxConvertRequest],
    Field(discriminator="type"),
]
```

`DocxConvertRequest` is url-only (no optional params), identical in structure to `CsvConvertRequest`. Append to the Union — do not reorder existing members.

### MCP Tool Schema Extension

In `src/index.ts`, extend the Zod enum and tool description:

```typescript
type: z.enum(["image", "csv", "html_pdf", "docx"])
  .describe("Conversion type: image (resize/reformat), csv (CSV to JSON), html_pdf (HTML to PDF), docx (DOCX to PDF)"),
```

Add a `docx` bullet to the tool description block:

```typescript
- docx: convert a DOCX document URL to PDF — outputs base64-encoded bytes (mammoth + WeasyPrint, content-fidelity not layout-preserving)
```

### Service Description Updates

`GET /` response string and `/convert` route docstring both need a fourth entry:

```python
"description": "Convert files: image resize/reformat, CSV→JSON, HTML→PDF, DOCX→PDF",
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| DOCX parsing and content extraction | Custom XML parser for `word/document.xml` | `mammoth.convert_to_html()` | DOCX internal XML spans multiple XML files (relationships, content types, numbering, styles). mammoth handles all edge cases including linked vs. embedded images. |
| HTML-to-PDF rendering | Custom PDF layout engine | `weasyprint.HTML(...).write_pdf()` | Page layout, text wrapping, table spanning, page breaks require a full CSS layout engine. Already integrated and tested. |
| Font fallback detection | `fc-match` subprocess calls at request time | Trust fontconfig at container startup | fontconfig caches font resolution. Build-time smoke test with a `font-family: Calibri` element is the right verification point. |
| WMF/EMF image conversion | ImageMagick subprocess for legacy WMF | Skip (mammoth warns, output continues) | WMF conversion requires LibreOffice or ImageMagick with legacy codec support (+100MB Docker). Out of scope per CONV-F01. |
| DOCX pre-validation | ZipFile structure inspection or XML schema validation | `try/except zipfile.BadZipFile` + `KeyError` | mammoth's own parser surfaces structural issues through exceptions and warnings. Pre-validation adds no value. |
| CSS injection for visual accuracy | Regenerate Word styles from mammoth HTML | Minimal static CSS block (`@page`, `body`, `table`, `td`) | Reconstructing Word formatting requires full style-map parsing. Static baseline CSS is sufficient for CONV-02 semantic fidelity. |
| mammoth warning inspection | Regex scan of HTML output | `result.messages` list from mammoth return value | mammoth explicitly surfaces warnings through its API. The messages list is the authoritative source for unsupported features (WMF images, unrecognized styles). |

**Key principle:** The mammoth → WeasyPrint pipeline is intentionally lossy. CONV-02 requires semantic fidelity (text, headings, tables, images), not layout fidelity. Any attempt to hand-roll visual accuracy beyond the baseline CSS wrapper approaches LibreOffice territory (CONV-F01, future). Resist the temptation.

---

## Common Pitfalls

### P1: mammoth outputs an HTML fragment, not a full document [STACK, PITFALLS]

Passing `result.value` directly to `weasyprint.HTML(string=...)` without `<html><head><style>...</style></head><body>` wrapper. WeasyPrint handles it "gracefully" in most cases but CSS resets, font inheritance, and `@page` rules do not apply without a proper document root. Table rendering degrades without `border-collapse` CSS.

**Fix:** Always wrap with a full HTML document and minimal CSS block. See the `sync_docx_to_pdf()` function above.

### P2: Font substitution fails on Railway Docker [STACK, PITFALLS — confirmed in WeasyPrint #2334]

Calibri (Word's default body font since Office 2007) is a proprietary Microsoft font not in Debian repositories. Without `fonts-liberation`, fontconfig may fall back to DejaVu or, in the worst case (Pango 1.55+), segfault with `"No fonts configured in FontConfig"` (WeasyPrint GitHub issue #2334, December 2024).

**Fix:** `fonts-liberation` is already in the Dockerfile — Liberation Sans substitutes for Calibri/Arial. Verify with `fc-match Calibri` inside a built container (expected: `LiberationSans-Regular.ttf`). The STATE.md pre-merge gate ("Test with real Calibri + table DOCX on Railway") is mandatory before merge.

### P3: Embedded images bloat HTML string and memory [STACK, PITFALLS]

mammoth's default `images.data_uri` converter base64-encodes all images inline. A DOCX with several high-res PNG images produces an HTML string many times larger than the input file. WeasyPrint holds both the HTML string and decoded image copies in memory during layout. The existing `MAX_FILE_BYTES = 10MB` download cap limits input size. The `MAX_OUTPUT_BYTES = 8MB` guard catches oversized PDFs after the fact but does not prevent WeasyPrint OOM during layout.

**Fix:** Accept as a best-effort v2.0 limitation. The 10MB input cap constrains the problem in practice. Do not attempt to write images to temp files — mammoth's library API only supports data URI output for in-memory (BytesIO) usage; the `output_dir` CLI option is not available from the library API.

### P4: WMF and EMF images are silently dropped [PITFALLS — mammoth #41]

Older Word documents (pre-Office 2007, legacy clipart, pasted Excel charts) frequently embed images in WMF/EMF format. mammoth omits these without raising an exception — it emits a warning in `result.messages` and the PDF has a blank space where the image was.

**Fix:** Surface mammoth warnings in the API response `warnings` array. Do not attempt to handle WMF/EMF conversion (LibreOffice/ImageMagick required — out of scope per CONV-F01).

### P5: mammoth produces no inline CSS — bare HTML renders as plain text [PITFALLS]

mammoth's design philosophy is "semantic over visual." It emits `<h1>`, `<p>`, `<table>`, `<td>` but no `style=""` attributes. Without a CSS block, WeasyPrint renders: no margins, no A4 page size, table rows with no visible borders, paragraphs with no spacing.

**Fix:** Inject the minimal CSS block in the HTML wrapper. See `sync_docx_to_pdf()` code example above.

### P6: Malformed DOCX raises `zipfile.BadZipFile` as an unhandled exception [PITFALLS — mammoth #89]

DOCX files are ZIP archives. A truncated download, a `.docx` extension on a non-DOCX file, or a zero-byte file causes mammoth to crash with `zipfile.BadZipFile`. Also catch `KeyError` — mammoth raises this for valid-ZIP files where `word/document.xml` is absent.

**Fix:** Wrap `mammoth.convert_to_html()` in `try/except zipfile.BadZipFile` and `except KeyError`. Return a structured `conversion_error` response. See `sync_docx_to_pdf()` code example above.

### P7: Underlined text is silently dropped by mammoth [PITFALLS]

mammoth does not map underlined text to any HTML element by default — the README explicitly states underlining is ignored to avoid confusion with hyperlinks. A DOCX where section headers use underline formatting (common in corporate Word templates) produces headings with no visual underline in the PDF.

**Fix:** Accept as known behavior. CONV-02 lists "text, headings, tables, and images" — underline is not in scope. Document in CONV-03 note: "Underlined text formatting is not preserved; use Word heading styles for structural emphasis."

### P8: Pydantic Union + dispatch `elif` + Zod enum are three separate change sites [INTEGRATION, PITFALLS]

It is easy to add `DocxConvertRequest` to the model but forget to (a) add it to the `ConvertRequest` Union, (b) add the `elif body.type == "docx"` dispatch branch, or (c) update the Zod enum in `src/index.ts`. Each omission produces a distinct silent failure mode: 422 error, missing dispatch, or MCP-layer rejection before the HTTP call.

**Fix:** Treat these as a single atomic change set in one task. Union update + dispatch `elif` + Zod enum update must all land in the same commit.

### P9: Table rendering is slow for large DOCX files [PITFALLS — WeasyPrint #1104]

WeasyPrint's table layout algorithm is computationally expensive for tables spanning multiple pages. A DOCX with 50+ row tables can take 5-30 seconds to convert, approaching Railway's request timeout ceiling.

**Fix:** Accept as a known v2.0 limitation. `run_in_threadpool` already prevents event loop blocking. Document in API docs: "Conversion time scales with document complexity; table-heavy documents may take 10-30 seconds."

### P10: No `base_url` needed for DOCX-sourced HTML (avoid copying `sync_html_to_pdf` verbatim) [INTEGRATION]

`sync_html_to_pdf` passes `source_url` as `base_url` to `weasyprint.HTML()` so relative CSS/image paths in the source HTML resolve correctly. For DOCX conversion, mammoth produces self-contained HTML (images as data URIs, no external CSS references) — passing the `.docx` file's URL as `base_url` is meaningless and potentially confusing.

**Fix:** Omit `base_url` from `weasyprint.HTML()` in `sync_docx_to_pdf`. Keep all CSS inline in the `<style>` block; never reference external stylesheets or font files.

---

## Code Examples

### Full `sync_docx_to_pdf()` Implementation

```python
def sync_docx_to_pdf(file_bytes: bytes) -> bytes:
    """Convert DOCX bytes to PDF bytes via mammoth + WeasyPrint.

    Pipeline: DOCX bytes → HTML fragment (mammoth) → full HTML document → PDF (WeasyPrint).
    Images are embedded as base64 data URIs by mammoth — no external URL fetches occur.
    Sync — must be called via run_in_threadpool.
    """
    import mammoth
    from io import BytesIO
    import zipfile

    try:
        result = mammoth.convert_to_html(BytesIO(file_bytes))
    except zipfile.BadZipFile:
        raise ValueError("Not a valid DOCX file (invalid ZIP archive)")
    except KeyError:
        raise ValueError("Not a valid DOCX file (missing internal document structure)")

    # Log non-fatal conversion warnings (dropped WMF images, unrecognized styles, etc.)
    for msg in result.messages:
        logger.warning("mammoth: %s", msg)

    # Wrap HTML fragment in full document with baseline CSS
    # Required: mammoth produces no CSS; without this WeasyPrint renders plain text with no layout
    html = f"""<!DOCTYPE html>
<html>
<head>
<style>
@page {{ size: A4; margin: 2cm; }}
body {{ font-family: "Liberation Sans", sans-serif; font-size: 11pt; line-height: 1.4; }}
table {{ width: 100%; border-collapse: collapse; }}
td, th {{ border: 1px solid #ccc; padding: 4px 8px; }}
h1, h2, h3, h4, h5, h6 {{ margin-top: 1em; margin-bottom: 0.4em; }}
p {{ margin: 0.4em 0; }}
</style>
</head>
<body>{result.value}</body>
</html>"""

    with tempfile.TemporaryDirectory() as tmpdir:
        out_path = os.path.join(tmpdir, "output.pdf")
        weasyprint.HTML(
            string=html,
            url_fetcher=safe_url_fetcher,
        ).write_pdf(out_path)
        with open(out_path, "rb") as f:
            return f.read()
```

### Pydantic Model and Union

```python
class DocxConvertRequest(BaseModel):
    type: Literal["docx"]
    url: BoundedHttpUrl

ConvertRequest = Annotated[
    Union[ImageConvertRequest, CsvConvertRequest, HtmlConvertRequest, DocxConvertRequest],
    Field(discriminator="type"),
]
```

### Dispatch `elif` Branch

```python
elif body.type == "docx":
    output_bytes = await run_in_threadpool(sync_docx_to_pdf, file_bytes)
    mime_type = "application/pdf"
```

### MCP Zod Schema Update (`src/index.ts`)

```typescript
type: z.enum(["image", "csv", "html_pdf", "docx"])
  .describe("Conversion type: image (resize/reformat), csv (CSV to JSON), html_pdf (HTML to PDF), docx (DOCX to PDF)"),
```

### Dockerfile Smoke Test Extension

```dockerfile
RUN python -c "from weasyprint import HTML; HTML(string='<p>test</p>').write_pdf(); import mammoth; print('ok')"
```

### mammoth API Reference (for implementation)

```python
import mammoth
from io import BytesIO

result = mammoth.convert_to_html(BytesIO(docx_bytes))
html_fragment = result.value    # str: HTML fragment (no <html>/<body> wrapper)
messages = result.messages      # list: non-fatal conversion warnings

# Full signature (all params optional after fileobj):
mammoth.convert_to_html(
    fileobj,                          # binary file-like object (required)
    style_map=None,                   # str: custom Word style → HTML element mapping
    include_embedded_style_map=True,
    include_default_style_map=True,
    convert_image=None,               # callable: custom image handler (default: data URI)
    ignore_empty_paragraphs=True,
    id_prefix="",
    transform_document=None,
)
```

---

## State of the Art

### mammoth 1.12.0 (March 12, 2026)

mammoth converts DOCX to a semantic HTML fragment. It is production stable, pure Python, zero system dependencies, Python >=3.7.

**What mammoth preserves:** Headings (Word styles → `<h1>`–`<h6>`), paragraphs, bold/italic, tables (content and structure), images (as base64 data URIs), ordered/unordered lists, hyperlinks, footnotes and endnotes.

**What mammoth does NOT preserve:** Page layout, margins, column layout, table borders/cell backgrounds, complex Word custom styles, text boxes and floating objects, page headers/footers, underlined text (intentional design decision).

### WeasyPrint 68.1 (February 6, 2026)

Already installed and tested. The existing `sync_html_to_pdf()` function is the reference implementation pattern. Phase 14 reuses it with no structural changes to the WeasyPrint integration.

### Decision History

The mammoth-over-LibreOffice decision was made during milestone research and is locked in STATE.md. LibreOffice is deferred to CONV-F01 (v2.x) for layout-preserving use cases. This decision does not need re-evaluation in Phase 14.

---

## Open Questions

1. **Font substitution severity on Railway** — The `fonts-liberation` package provides Liberation Sans for Calibri substitution. How degraded is the rendering for Calibri+table-heavy DOCX in practice? This is empirical and cannot be determined from documentation alone. The STATE.md pre-merge gate (test on Railway with a real Calibri + table DOCX) is the resolution path.

2. **mammoth warnings in API response** — The existing `ConvertResponse` model has a `warnings: list[str]` field. Should mammoth's `result.messages` be surfaced there? The messages provide caller visibility into dropped images and unrecognized styles. This is a quality-of-life decision, not a blocking requirement.

3. **CONV-03 documentation scope** — CONV-03 requires that the API docs "explicitly note content-document conversion — not layout-preserving." This applies to: (a) the `GET /` service description string, (b) the `/convert` route docstring, (c) the `x402_convert_file` MCP tool description in `src/index.ts`, and (d) the Bismuth docs site (`/docs/file-conversion`). Items (a)–(c) are in scope for Phase 14 code changes. Item (d) may require a separate docs update task or may be captured in Phase 16 MCP-05.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | No conflicts between dimensions. STACK and INTEGRATION both note `safe_url_fetcher` should be passed to WeasyPrint — this is consistent. STACK notes `base_url` is not needed; INTEGRATION confirms via the "no external CSS references" finding. PITFALLS notes P7 (WeasyPrint base_url), which is consistent with both. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples, State of the Art, Open Questions. Phase Requirements table present with all 3 req IDs mapped. |
| Dimension Coverage | PASS | STACK: installation, API, Dockerfile, State of the Art, function skeleton integrated. INTEGRATION: discriminated union, dispatch, Zod schema, service string, fixture note integrated. PITFALLS: all 9 dimension pitfalls mapped to Common Pitfalls P1–P10 (P7/base_url is a PITFALLS+INTEGRATION cross-dimension finding). |
| Requirement Coverage | PASS | CONV-01 → DocxConvertRequest + Union + elif dispatch + Zod enum. CONV-02 → mammoth semantic preservation list in Standard Stack + State of the Art. CONV-03 → service description string updates + MCP tool description update + PITFALLS underline/limitation documentation. |

---

## Sources

### Primary (HIGH confidence — direct codebase inspection or official docs)

- `/Users/jameswisdom/projects/x402-mcp-server/x402-conversion-api/main.py` — discriminated union, dispatch block, `sync_html_to_pdf()`, `safe_url_fetcher`, `run_in_threadpool`, `download_file()`, `MAX_FILE_BYTES`, `MAX_OUTPUT_BYTES`
- `/Users/jameswisdom/projects/x402-mcp-server/x402-conversion-api/requirements.txt` — current deps; mammoth confirmed absent
- `/Users/jameswisdom/projects/x402-mcp-server/x402-conversion-api/Dockerfile` — WeasyPrint system deps, `fonts-liberation` install, smoke test pattern
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — `x402_convert_file` Zod enum, tool description, payload assembly
- [pypi.org/project/mammoth](https://pypi.org/project/mammoth/) — version 1.12.0 confirmed March 12, 2026; pure Python; no system deps
- [github.com/mwilliamson/python-mammoth](https://github.com/mwilliamson/python-mammoth) — `convert_to_html()` API, result object, image data URI behavior, tables behavior
- [mammoth GitHub issue #89](https://github.com/mwilliamson/python-mammoth/issues/89) — `zipfile.BadZipFile` on malformed DOCX
- [mammoth GitHub issue #41](https://github.com/mwilliamson/python-mammoth/issues/41) — EMF/WMF images unsupported
- [WeasyPrint GitHub issue #2334](https://github.com/Kozea/WeasyPrint/issues/2334) — segfault with Pango 1.55 + no fonts (December 2024)
- [WeasyPrint docs — Common Use Cases](https://doc.courtbouillon.org/weasyprint/stable/common_use_cases.html) — table performance warning

### Secondary (MEDIUM confidence)

- [deepwiki.com/mwilliamson/python-mammoth/3-using-mammoth](https://deepwiki.com/mwilliamson/python-mammoth/3-using-mammoth) — full `convert_to_html()` parameter table, result object fields, image handling details
- `.planning/research/SUMMARY.md` — milestone decision: mammoth over LibreOffice confirmed, font substitution pitfall noted, Railway pre-merge test requirement flagged
- [WeasyPrint GitHub issue #1104](https://github.com/Kozea/WeasyPrint/issues/1104) — table rendering memory/performance
- [WeasyPrint GitHub issue #671](https://github.com/Kozea/WeasyPrint/issues/671) — memory consumption on long documents
- [WeasyPrint GitHub issue #501](https://github.com/Kozea/WeasyPrint/issues/501) — base_url required for relative URL resolution

### Tertiary (LOW confidence — single source, not independently verified)

- Actual font substitution severity on Railway containers with `fonts-liberation` for Calibri/Cambria-heavy DOCX files — confirmed problem class; severity unknown without empirical Railway test
- [WeasyPrint GitHub issue #1496](https://github.com/Kozea/WeasyPrint/issues/1496) — memory leak report (older; may be fixed in 68.1)

---

## Metadata

**Confidence breakdown:**
- STACK: HIGH (live codebase + pypi + GitHub)
- INTEGRATION: HIGH (direct `main.py` + `src/index.ts` inspection)
- PITFALLS: HIGH (official GitHub issues + README)

**Research date:** 2026-03-16
**Valid until:** 2026-06-01 (mammoth and WeasyPrint are stable; re-validate if either bumps major version)
**Dimensions researched:** 3 (STACK, INTEGRATION, PITFALLS)
