# Phase 13: Email Attachments + CC/BCC - Research

**Researched:** 2026-03-16
**Domain:** FastAPI + Resend Python SDK email extension
**Confidence:** HIGH
**Method:** MECE decomposition (3 dimensions: INTEGRATION, SECURITY, PITFALLS)

---

## Summary

Phase 13 extends the existing `x402-email-api` FastAPI service and the `x402_send_email` MCP tool to accept CC recipients, BCC recipients, and base64-encoded file attachments. The Resend Python SDK (`resend>=2.0.0`, already installed) natively supports all three features via `SendParams` — no new Python packages are required. The Python stdlib `base64` and `mimetypes` modules handle validation and content-type derivation, respectively.

The primary security surface is email header injection via CRLF characters in CC/BCC addresses and MIME injection via the `content_type` field. Both are mitigated by the existing Pydantic `EmailStr` validator (which rejects control characters) and a lightweight MIME regex validator added to the `AttachmentItem` model. A Pydantic `@field_validator` on the `content` field both validates base64 correctness and enforces the 25MB pre-encoding cap by checking decoded byte length — not string length. The Resend SDK's optional `path` field must not be exposed; the `Attachment` Pydantic model is an input contract, not a mirror of the SDK TypedDict.

The three sharpest implementation risks are: (1) the domain rate limiter currently only checks `body.to` — it must be extended to iterate all CC and BCC addresses, (2) the `content` size check must operate on decoded bytes (`len(base64.b64decode(v))`), not string length, to avoid the base64 33% expansion factor distorting the threshold, and (3) all new Zod fields (`cc`, `bcc`, `attachments`) must be `.optional()` with no defaults to preserve backward compatibility for existing MCP callers.

**Primary recommendation:** Extend `EmailRequest` with `cc: Optional[List[EmailStr]]`, `bcc: Optional[List[EmailStr]]`, and `attachments: Optional[List[AttachmentItem]]`. Add a `@field_validator` to `AttachmentItem.content` that calls `base64.b64decode(v, validate=True)` and checks byte length. Extend `check_and_increment_domain_limit` to cover all recipients. Pass the three new fields through `build_send_params` conditionally using the existing `if body.X: params["X"] = ...` pattern.

---

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EMAIL-01 | User can send email with CC recipients via x402_send_email tool | INTEGRATION: Pydantic `cc: Optional[List[EmailStr]]` + Resend `SendParams.cc`; MCP Zod `cc: z.array(z.string().email()).optional()` |
| EMAIL-02 | User can send email with BCC recipients via x402_send_email tool | INTEGRATION: Pydantic `bcc: Optional[List[EmailStr]]` + Resend `SendParams.bcc`; MCP Zod `bcc: z.array(z.string().email()).optional()` |
| EMAIL-03 | User can send email with base64 file attachments (25MB pre-encoding cap) | INTEGRATION: `AttachmentItem` model + Resend `SendParams.attachments`; SECURITY: base64 decode + byte length check; MCP Zod `attachments` array schema |
| EMAIL-04 | Attachment size validated before encoding — reject over 25MB with clear error | SECURITY: `@field_validator("content")` with `base64.b64decode(v, validate=True)` + `len(raw) > 25 * 1024 * 1024` check; PITFALLS: must check decoded bytes, not string length |

---

## Standard Stack

No new Python packages needed. All changes use existing dependencies and Python stdlib.

| Module | Source | Purpose |
|--------|--------|---------|
| `resend` (>=2.0.0, currently 2.24.0) | Already in `x402-email-api/requirements.txt` | CC, BCC, attachments via `SendParams` |
| `pydantic.EmailStr` | Already in use | Validates each CC/BCC address; rejects CRLF injection |
| `base64` | Python stdlib | `b64decode(v, validate=True)` — validates base64 format and gives decoded byte count |
| `mimetypes` | Python stdlib | `guess_type(filename)` — derives `content_type` from filename extension when caller omits it |
| `os.path.basename` | Python stdlib | Strips path separators from filenames before they enter MIME headers |

**MCP side (TypeScript):** No new npm packages. Zod schema additions use `z.array()`, `z.string().email()`, `z.object()`, and `.optional()` — all already available.

---

## Architecture Patterns

### Pydantic Model Extension

Add `AttachmentItem` as a new nested model and extend `EmailRequest` with three optional fields:

```python
import base64
import mimetypes
import os
import re
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field, field_validator

MAX_ATTACHMENT_BYTES = 25 * 1024 * 1024  # 25MB pre-encoding
MIME_TYPE_PATTERN = re.compile(
    r'^[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_]*\/[a-zA-Z0-9][a-zA-Z0-9!#$&\-^_.+]*$'
)

class AttachmentItem(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255,
                          description="Attachment filename including extension")
    content: str = Field(..., description="Base64-encoded file content")
    content_type: Optional[str] = Field(
        None,
        description="MIME type — auto-derived from filename if omitted"
    )

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        v = os.path.basename(v.replace("\\", "/"))
        if any(ord(c) < 32 for c in v):
            raise ValueError("filename contains control characters")
        if not v:
            raise ValueError("filename is empty after sanitization")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_mime_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not MIME_TYPE_PATTERN.match(v):
            raise ValueError("content_type must be a valid MIME type (e.g. application/pdf)")
        return v

    @field_validator("content")
    @classmethod
    def validate_attachment_size(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("attachment content is not valid base64")
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment exceeds 25MB limit "
                f"({len(raw) / 1024 / 1024:.1f}MB decoded)"
            )
        return v


class EmailRequest(BaseModel):
    to: EmailStr
    subject: str = Field(..., min_length=1, max_length=998)
    body: str = Field(..., min_length=1, max_length=102400)
    reply_to: Optional[EmailStr] = None
    cc: Optional[List[EmailStr]] = Field(
        None,
        description="Carbon copy recipients"
    )
    bcc: Optional[List[EmailStr]] = Field(
        None,
        description="Blind carbon copy recipients"
    )
    attachments: Optional[List[AttachmentItem]] = Field(
        None,
        description="Base64-encoded file attachments (25MB pre-encoding cap per file)"
    )
```

### `build_send_params` Extension

Extend the existing function following the established `if body.X: params["X"] = ...` pattern. Never set `None` as an explicit key value — Resend treats `null` differently from an absent key.

```python
import mimetypes
import base64

def build_send_params(body: EmailRequest) -> dict:
    # ... existing html/text classification logic unchanged ...

    params: resend.Emails.SendParams = {
        "from": FROM_ADDRESS,
        "to": [str(body.to)],
        "subject": body.subject,
    }

    # html/text — unchanged
    if is_html:
        params["html"] = body.body
    else:
        params["text"] = body.body

    if body.reply_to:
        params["reply_to"] = str(body.reply_to)

    # NEW: CC
    if body.cc:
        params["cc"] = [str(addr) for addr in body.cc]

    # NEW: BCC
    if body.bcc:
        params["bcc"] = [str(addr) for addr in body.bcc]

    # NEW: Attachments
    if body.attachments:
        resend_attachments = []
        for att in body.attachments:
            attachment: resend.Attachment = {
                "filename": att.filename,
                "content": att.content,  # base64 string passed directly — no decode needed
            }
            if att.content_type:
                attachment["content_type"] = att.content_type
            else:
                guessed, _ = mimetypes.guess_type(att.filename)
                if guessed:
                    attachment["content_type"] = guessed
            resend_attachments.append(attachment)
        params["attachments"] = resend_attachments

    return params
```

### Domain Rate Limiter Extension

The existing `check_and_increment_domain_limit` only checks `body.to`. It must be called for every recipient address:

```python
# In the /send route handler, replace:
#   check_and_increment_domain_limit(wallet, str(body.to))
# With:
all_recipients = [str(body.to)]
if body.cc:
    all_recipients.extend(str(addr) for addr in body.cc)
if body.bcc:
    all_recipients.extend(str(addr) for addr in body.bcc)
for recipient in all_recipients:
    check_and_increment_domain_limit(wallet, recipient)
```

### MCP Zod Schema Extension (`src/index.ts`)

All new fields are `.optional()` — no defaults — to maintain backward compatibility.

```typescript
{
    to: z.string().email().describe("Recipient email address"),
    subject: z.string().min(1).max(998).describe("Email subject (max 998 chars)"),
    body: z.string().min(1).max(102400).describe("Email body — HTML or plain text (max 100 KB)"),
    reply_to: z.string().email().optional().describe("Optional reply-to address"),
    // NEW:
    cc: z.array(z.string().email()).optional()
        .describe("CC recipients — list of email addresses"),
    bcc: z.array(z.string().email()).optional()
        .describe("BCC recipients — list of email addresses"),
    attachments: z.array(z.object({
        filename: z.string().describe("Filename including extension (e.g. 'report.pdf')"),
        content: z.string().describe("Base64-encoded file content"),
        content_type: z.string().optional()
            .describe("MIME type — auto-derived from filename if omitted"),
    })).optional().describe("File attachments (base64-encoded, max 25MB pre-encoding per file)"),
}
```

MCP handler payload assembly — only include fields when present:

```typescript
const payload: Record<string, unknown> = {
    to: params.to,
    subject: params.subject,
    body: params.body,
};
if (params.reply_to) payload.reply_to = params.reply_to;
if (params.cc) payload.cc = params.cc;
if (params.bcc) payload.bcc = params.bcc;
if (params.attachments) payload.attachments = params.attachments;
```

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Email address validation for CC/BCC | Custom regex, string parsing, manual CRLF checks | Pydantic `EmailStr` (already in use) | `email-validator` rejects control characters (`\r`, `\n`), whitespace, unsafe Unicode, and invalid RFC 5322 syntax — CRLF injection mitigated |
| Base64 validation | Custom regex or character set checker | `base64.b64decode(v, validate=True)` + catch `binascii.Error` | Stdlib is correct, handles padding errors; regex misses padding edge cases |
| Pre-encoding size check | Post-encoding byte count (encode first, then measure) | Decode from base64 first, check `len(raw_bytes)` | Encoding a 30MB file to check its size wastes memory; pre-encoding check is cheaper and catches the constraint earlier |
| MIME type detection from file content | Magic byte sniffing, `python-magic`, libmagic wrapper | `mimetypes.guess_type(filename)` + `content_type` passthrough | Resend handles MIME server-side; sniffing adds complexity for minimal gain |
| Request body size limiting at route level | `Request.body()` read then check in route handler | ASGI middleware checking `Content-Length` header (defense-in-depth; optional for Phase 13) | Route handler approach requires full body in memory before check — defeats the purpose |
| CC/BCC deduplication | Set-based dedup across to/cc/bcc | Pass as-is to Resend | Resend does not document rejecting duplicate recipients; domain limiter already constrains repeat sends per domain |

---

## Common Pitfalls

### 1. Size check on string length, not decoded bytes

The 25MB pre-encoding cap must be checked against decoded byte length, not the base64 string length. A 25MB raw file becomes a ~33.4MB base64 string (4/3 expansion). Checking `len(content_string) > 25MB` rejects files as small as 18.7MB raw.

**Correct:** `len(base64.b64decode(v)) > 25 * 1024 * 1024`

**Wrong:** `len(v) > 25 * 1024 * 1024`

### 2. Setting `None` as an explicit key in the Resend params dict

The existing `build_send_params` already warns: "CRITICAL: Never include `'html': None`." The same applies to `cc`, `bcc`, and `attachments`. Always use the conditional pattern: `if body.cc: params["cc"] = ...`.

### 3. Using `List[str]` instead of `List[EmailStr]` for CC/BCC

`List[str]` bypasses `email-validator` entirely. A CRLF injection string (`"cc@example.com\r\nBcc: victim@target.com"`) passes Pydantic validation and reaches the Resend SDK, which has no client-side sanitization of CC/BCC values. Always use `List[EmailStr]`.

### 4. Domain rate limiter blind to CC/BCC recipients

`check_and_increment_domain_limit` currently only checks `body.to`. With CC/BCC, a caller can send to a domain-limited address via CC while using a throwaway primary recipient. The fix is to call the limit check for every recipient address — `to`, each `cc`, each `bcc`.

### 5. Exposing the Resend SDK `path` field

The Resend SDK `Attachment` TypedDict has an optional `path` field for remote URL-based attachments. Exposing this in the Pydantic input model violates the stated design decision (REQUIREMENTS.md: "Attachment URL fetching — SSRF risk — accept base64 only"). The `AttachmentItem` model must have no `path` field. When building SDK params, only pass `content`, `filename`, and `content_type`.

### 6. Passing `bytes` to Resend SDK `content`

The Resend SDK `Attachment.content` is `Union[List[int], str]` — not `bytes`. Python `bytes` cannot be serialized to JSON and will raise a runtime `TypeError`. Accept the base64 string from callers and pass it directly as-is. Do not decode and re-pass.

### 7. New Zod fields breaking existing MCP callers

All three new MCP tool fields (`cc`, `bcc`, `attachments`) must be `.optional()`. If marked required, existing callers that omit them receive validation errors. Verify: existing callers that pass only `to`, `subject`, `body` still succeed after the schema change.

### 8. Zod v4 description propagation (MEDIUM confidence)

The project uses `zod: ^4.3.6` and `@modelcontextprotocol/sdk: ^1.11.0`. GitHub issue #1143 on the MCP TypeScript SDK reports that Zod v4 `.describe()` metadata may not propagate to the JSON schema output in `listTools`. Verify that descriptions appear in `listTools` output after the schema change; if absent, this is a known SDK issue.

### 9. Railway has no body size cap — uvicorn buffers full request

Railway imposes no platform-level HTTP body size limit (confirmed via support thread). Uvicorn buffers the full request body before ASGI application code runs. A 200MB POST will be buffered into RAM before the Pydantic validator can reject it. The Pydantic `@field_validator` on `content` is the primary enforcement gate for EMAIL-04; adding ASGI middleware to check `Content-Length` is defense-in-depth and can be added if memory pressure is observed.

### 10. `content_type` injection via the MIME type field

A caller submitting `content_type: "application/pdf\r\nX-Injected: malicious"` can inject MIME headers if the value is passed without validation. Validate `content_type` with the MIME regex pattern before passing to SDK.

---

## Code Examples

### Complete `AttachmentItem` model with all validators

```python
class AttachmentItem(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    content: str = Field(...)
    content_type: Optional[str] = Field(None)

    @field_validator("filename")
    @classmethod
    def validate_filename(cls, v: str) -> str:
        v = os.path.basename(v.replace("\\", "/"))
        if any(ord(c) < 32 for c in v):
            raise ValueError("filename contains control characters")
        if not v:
            raise ValueError("filename is empty after sanitization")
        return v

    @field_validator("content_type")
    @classmethod
    def validate_mime_type(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and not MIME_TYPE_PATTERN.match(v):
            raise ValueError("content_type must be a valid MIME type (e.g. application/pdf)")
        return v

    @field_validator("content")
    @classmethod
    def validate_attachment_size(cls, v: str) -> str:
        try:
            raw = base64.b64decode(v, validate=True)
        except Exception:
            raise ValueError("attachment content is not valid base64")
        if len(raw) > MAX_ATTACHMENT_BYTES:
            raise ValueError(
                f"Attachment exceeds 25MB limit "
                f"({len(raw) / 1024 / 1024:.1f}MB decoded)"
            )
        return v
```

### Resend SDK attachment passing (base64 string path)

```python
# Pass base64 string directly — Resend SDK accepts Union[List[int], str]
attachment: resend.Attachment = {
    "filename": att.filename,
    "content": att.content,      # base64 str — no decode/re-encode needed
    "content_type": att.content_type,  # or omit if None; Resend derives from filename
}
```

### `mimetypes` content-type auto-derivation

```python
# Extension → MIME type mapping (Python stdlib)
# .pdf  → application/pdf
# .png  → image/png
# .jpg  → image/jpeg
# .docx → application/vnd.openxmlformats-officedocument.wordprocessingml.document
# .csv  → text/csv
# .zip  → application/zip
# unknown extension → None (safe to omit; Resend handles server-side)
guessed, _ = mimetypes.guess_type(att.filename)
if guessed:
    attachment["content_type"] = guessed
```

---

## State of the Art

The Resend Python SDK (2.24.0) uses typed TypedDict params (`resend.Emails.SendParams`, `resend.emails._attachment.Attachment`). The SDK does not perform client-side validation of CC/BCC for CRLF characters, attachment content validity, or size — all of this is handled server-side or must be handled by the application layer. This is consistent with most transactional email SDKs.

Pydantic v2 `@field_validator` is the idiomatic FastAPI pattern for input validation logic that requires computation (decode + measure). The `validate=True` flag on `b64decode` was added in Python 3.x stdlib and is the canonical way to reject non-base64 characters without a custom regex.

There is no industry-standard MCP schema for email attachments. The base64 string + filename + optional content_type pattern mirrors what AWS SES, SendGrid, and Postmark all accept in their HTTP APIs — it's the de facto standard for JSON-native attachment APIs.

---

## Open Questions

1. **Wallet limit reconsideration (deferred to future phase):** The current wallet limit (`DAILY_SEND_LIMIT = 10`) counts sends, not recipients. With CC/BCC, one send can reach 99+ addresses. For Phase 13, the domain limiter (`5/domain/day`) provides anti-spam coverage. A per-recipient wallet limiter would require redesigning the rate limit data structure — defer to future phase, document the decision.

2. **ASGI body size middleware (optional for Phase 13):** Railway has no platform body cap. A malicious caller can submit a 200MB POST before the Pydantic validator runs. The `@field_validator` on attachment content handles EMAIL-04 compliance, but a defense-in-depth `Content-Length` header check at the middleware layer would provide earlier rejection. Assess whether Railway's memory footprint warrants this during implementation.

3. **Zod v4 description propagation:** GitHub issue #1143 on `@modelcontextprotocol/sdk` may affect `.describe()` metadata in `listTools`. Monitor and verify after implementation.

---

## Coverage Audit

| Check | Status | Details |
|-------|--------|---------|
| Mutually Exclusive | PASS | All three dimensions agree on: base64 string passthrough (no decode before sending), `List[EmailStr]` for CC/BCC, no `path` field, pre-encoding size check. No conflicts found. |
| Collectively Exhaustive | PASS | All required sections populated: Summary, Standard Stack, Architecture Patterns, Don't Hand-Roll, Common Pitfalls, Code Examples. Phase Requirements table present. |
| Dimension Coverage | PASS | INTEGRATION: API call patterns, SDK params, schema changes represented. SECURITY: CRLF injection, SSRF prevention, validators represented. PITFALLS: all 7 pitfalls + 2 dimension-specific pitfalls represented. |
| Requirement Coverage | PASS | EMAIL-01 → CC field pattern; EMAIL-02 → BCC field pattern; EMAIL-03 → AttachmentItem + SDK passthrough; EMAIL-04 → `@field_validator` with decoded byte check. All 4 requirements mapped. |

---

## Sources

### Primary (HIGH confidence)
- `https://raw.githubusercontent.com/resend/resend-python/main/resend/emails/_attachment.py` — `Attachment` TypedDict: `content: Union[List[int], str]`, `filename` required, `path` optional, `content_type` optional
- `https://raw.githubusercontent.com/resend/resend-python/main/resend/emails/_emails.py` — `SendParams`: `cc/bcc: NotRequired[Union[List[str], str]]`, `attachments: NotRequired[List[...]]`, no client-side sanitization confirmed
- `https://raw.githubusercontent.com/resend/resend-python/main/examples/with_attachments.py` — Official attachment usage example
- `https://resend.com/docs/api-reference/emails/send-email#body-parameters` — Confirms `content` accepts base64 string; `content_type` auto-derived from filename; 40MB post-encoding limit
- `https://resend.com/docs/dashboard/emails/attachments` — 40MB limit confirmation, base64 accepted
- `https://pypi.org/project/email-validator/` — Control char rejection, whitespace rejection, unsafe Unicode rejection
- `https://station.railway.com/questions/request-size-limit-c493c3a4` — Railway has no platform-level body size cap (confirmed)
- `/Users/jameswisdom/projects/x402-mcp-server/x402-email-api/main.py` — Current `EmailRequest` model, `build_send_params`, rate limit patterns, existing None-key warning
- `/Users/jameswisdom/projects/x402-mcp-server/src/index.ts` — Current `x402_send_email` Zod schema (lines 484-502)
- `/Users/jameswisdom/projects/x402-mcp-server/x402-email-api/requirements.txt` — Confirms `resend>=2.0.0,<3.0.0` already pinned
- `/Users/jameswisdom/projects/x402-mcp-server/.planning/REQUIREMENTS.md` — EMAIL-01 through EMAIL-04; Out of Scope: "Attachment URL fetching — SSRF risk — accept base64 only"

### Secondary (MEDIUM confidence)
- `https://pypi.org/pypi/resend/json` — Latest resend Python package version is 2.24.0 (within pinned range)
- `https://github.com/modelcontextprotocol/typescript-sdk/issues/1143` — Zod v4 `.describe()` metadata may not propagate to JSON schema in `listTools`
- `https://github.com/Kludex/uvicorn/issues/443` — Full body buffered before app code; 10MB+ payloads show measurable memory impact
- `https://portswigger.net/kb/issues/00200800_smtp-header-injection` — CRLF injection via CC/BCC fields, CWE-93
- `https://snyk.io/blog/avoiding-smtp-injection/` — Python SMTP injection vectors, CRLF in address fields
- `https://docs.pydantic.dev/latest/api/networks/` — `EmailStr` raises `PydanticCustomError` for invalid input, normalizes addresses

### Tertiary (LOW confidence)
- Base64 33% overhead — confirmed by multiple sources (cross-referenced to HIGH)
- MIME type regex pattern for `content_type` validation — standard pattern, not from official source
- FastAPI body size limiting strategies — ASGI middleware approach (no authoritative library recommendation found)

---

## Metadata

**Confidence breakdown:**
- INTEGRATION: HIGH
- SECURITY: HIGH
- PITFALLS: HIGH (MEDIUM for Zod v4 description propagation, Railway OOM thresholds)

**Research date:** 2026-03-16
**Valid until:** Resend SDK breaking change or Resend API limit change (neither anticipated in 2026)
**Dimensions researched:** INTEGRATION, SECURITY, PITFALLS
**Nyquist validation:** false (not applicable — no sampling/signal-processing concerns)
