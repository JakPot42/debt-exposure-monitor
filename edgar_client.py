"""edgar_client.py — SEC EDGAR HTTP layer.

Adapted directly from GhostTrace's (P6) edgar_client.py: same process-wide
rate limiter, same company-ticker lookup, same stdlib-only HTML-to-text
extraction. What differs is which forms matter: GhostTrace pulls
ownership filings (SC 13D/13G, DEF 14A, 10-K Exhibit 21); this pulls
debt-disclosure filings (10-K/10-Q footnotes, 8-K Item 1.01/2.03 "Entry
into a Material Definitive Agreement" announcements) -- where credit
facilities and bond issuances actually get disclosed.

Pure data fetching: no Claude, no database. Everything here is testable
with mocked HTTP responses alone.
"""
from __future__ import annotations

import threading
import time
from html.parser import HTMLParser

import httpx

from config import (
    DEBT_RELEVANT_FORM_TYPES,
    EDGAR_ARCHIVES_BASE,
    EDGAR_COMPANY_TICKERS_URL,
    EDGAR_RATE_LIMIT_PER_SEC,
    EDGAR_SUBMISSIONS_URL,
    EDGAR_USER_AGENT,
    MAX_10K_10Q_PER_TRACE,
    MAX_8K_PER_TRACE,
    MAX_DOC_CHARS,
)


class EdgarError(Exception):
    pass


# ---------------------------------------------------------------------------
# Rate limiting
# ---------------------------------------------------------------------------

class _RateLimiter:
    """Process-wide rate limiter shared by every EDGAR call. SEC's limit
    applies per IP, not per code path, so state must be shared across
    concurrent callers, guarded by a lock."""

    def __init__(self, max_per_second: float):
        self._min_interval = 1.0 / max_per_second
        self._lock = threading.Lock()
        self._last_request = 0.0

    def wait(self) -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_request
            if elapsed < self._min_interval:
                time.sleep(self._min_interval - elapsed)
            self._last_request = time.monotonic()


_limiter = _RateLimiter(EDGAR_RATE_LIMIT_PER_SEC)
_HEADERS = {"User-Agent": EDGAR_USER_AGENT}


def _get(url: str) -> httpx.Response:
    _limiter.wait()
    try:
        resp = httpx.get(url, headers=_HEADERS, timeout=15.0, follow_redirects=True)
    except httpx.HTTPError as exc:
        raise EdgarError(f"EDGAR request failed: {url} -- {exc}") from exc
    if resp.status_code != 200:
        raise EdgarError(f"EDGAR returned HTTP {resp.status_code} for {url}")
    return resp


# ---------------------------------------------------------------------------
# CIK lookup
# ---------------------------------------------------------------------------

_TICKER_CACHE: dict = {"fetched_at": 0.0, "rows": []}
_TICKER_CACHE_TTL_SECONDS = 24 * 3600


def _ticker_table() -> list[dict]:
    age = time.monotonic() - _TICKER_CACHE["fetched_at"]
    if not _TICKER_CACHE["rows"] or age > _TICKER_CACHE_TTL_SECONDS:
        data = _get(EDGAR_COMPANY_TICKERS_URL).json()
        _TICKER_CACHE["rows"] = list(data.values())
        _TICKER_CACHE["fetched_at"] = time.monotonic()
    return _TICKER_CACHE["rows"]


def _norm(name: str) -> str:
    return "".join(ch for ch in name.lower() if ch.isalnum() or ch == " ").strip()


def get_company_candidates(query: str, limit: int = 8) -> list[dict]:
    """Ranked CIK candidates for a user-typed company name or ticker.
    Never silently picks one match -- a confident report about the wrong
    company is worse than no report."""
    q = _norm(query)
    if not q:
        return []
    rows = _ticker_table()
    exact_ticker = [r for r in rows if r["ticker"].lower() == query.strip().lower()]
    name_matches = [r for r in rows if q in _norm(r["title"])]

    seen: set[int] = set()
    out: list[dict] = []
    for r in exact_ticker + name_matches:
        cik = int(r["cik_str"])
        if cik in seen:
            continue
        seen.add(cik)
        out.append({"cik": cik, "ticker": r["ticker"], "name": r["title"]})
        if len(out) >= limit:
            break
    return out


# ---------------------------------------------------------------------------
# Filing index
# ---------------------------------------------------------------------------

def get_debt_relevant_filings(cik: int) -> list[dict]:
    """Recent 10-K/10-Q/8-K filings, capped per trace. Keeps the most
    recent 10-K and 10-Q (footnotes are cumulative -- an old one is
    superseded, not additive) plus several recent 8-Ks (new credit
    facilities and bond issuances are announced there before showing up
    in the next periodic report's footnotes)."""
    data = _get(EDGAR_SUBMISSIONS_URL.format(cik=cik)).json()
    recent = data.get("filings", {}).get("recent", {})

    out: list[dict] = []
    count_10k = count_10q = count_8k = 0
    for form, acc, doc, date in zip(
        recent.get("form", []),
        recent.get("accessionNumber", []),
        recent.get("primaryDocument", []),
        recent.get("filingDate", []),
    ):
        if form not in DEBT_RELEVANT_FORM_TYPES:
            continue
        if form == "10-K":
            if count_10k >= MAX_10K_10Q_PER_TRACE:
                continue
            count_10k += 1
        elif form == "10-Q":
            if count_10q >= MAX_10K_10Q_PER_TRACE:
                continue
            count_10q += 1
        elif form == "8-K":
            if count_8k >= MAX_8K_PER_TRACE:
                continue
            count_8k += 1
        out.append({
            "form": form,
            "accession_number": acc,
            "primary_document": doc,
            "filing_date": date,
        })
    return out


def fetch_document_text(cik: int, accession_number: str, document_name: str) -> str:
    """Fetch one filing document and return plain text, truncated to
    MAX_DOC_CHARS."""
    acc = accession_number.replace("-", "")
    url = f"{EDGAR_ARCHIVES_BASE}/{cik}/{acc}/{document_name}"
    raw = _get(url).text
    if document_name.lower().endswith((".htm", ".html")):
        raw = _strip_html(raw)
    return raw[:MAX_DOC_CHARS]


# ---------------------------------------------------------------------------
# HTML -> text (stdlib only)
# ---------------------------------------------------------------------------

class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self._chunks: list[str] = []
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag in ("script", "style"):
            self._skip_depth += 1

    def handle_endtag(self, tag: str) -> None:
        if tag in ("script", "style") and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data: str) -> None:
        if not self._skip_depth and data.strip():
            self._chunks.append(data.strip())

    def get_text(self) -> str:
        return " ".join(self._chunks)


def _strip_html(raw: str) -> str:
    parser = _TextExtractor()
    parser.feed(raw)
    return parser.get_text()
