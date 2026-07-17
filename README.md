# Defense Supplier Debt Exposure Monitor

Tracks who is actually **funding** a defense supplier through debt
markets — credit facilities, bond issuances, term loans — and screens
every disclosed lender against OFAC sanctions, BIS export-control lists,
and a curated list of foreign state-owned/state-controlled financial
institutions.


---

## The Gap This Fills

[FriendShore](https://github.com/JakPot42/friendshore-supply-chain)
maps a defense supplier's *physical* supply chain — parts, sub-tier
vendors, single points of failure. [DIB Monitor](https://github.com/JakPot42/dib-monitor)
 tracks *equity-level* distress — going-concern language, debt
covenants, earnings signals. **Neither tracks who is lending the money.**
13F filings show equity ownership changes; they say nothing about a
credit facility's administrative agent or a bond issuance's underwriter.
A foreign state-connected institution can become a Tier 2 defense
supplier's primary lender without appearing in either physical supply
chain data or equity ownership data. This project closes that specific
gap — the third piece of the supply-chain financial intelligence cluster
alongside FriendShore and DIB Monitor (and reuses GhostTrace's and
CFIUS Screener's sanctions-screening and entity-resolution
techniques directly, the same cluster referenced as "Arbor" in the
portfolio's deferred Merger Vision).

---

## What It Does

1. **Pulls SEC EDGAR debt disclosures** — 10-K/10-Q footnotes (credit
   facility and bond disclosures are cumulative; only the most recent of
   each is fetched) and 8-K Item 1.01/2.03 filings ("Entry into a
   Material Definitive Agreement" — where new credit facilities and bond
   issuances actually get announced, often before showing up in the next
   periodic report's footnotes).
2. **Claude extracts lender/counterparty identities** from that filing
   text — names, roles (administrative agent, lender, underwriter,
   trustee), instrument type, and the amount disclosed near each. Claude
   never scores or flags anything; it only extracts what the text names.
3. **Deduplicates lender name variants** ("JPMorgan Chase Bank, N.A." vs
   "JPMorgan Chase & Co.") via the same token-sort fuzzy-matching
   technique GhostTrace built for corporate ownership names.
4. **Screens every canonical lender name against three lists:**
   - **OFAC SDN** — reused directly from GhostTrace's `ofac_checker.py`.
   - **BIS export-control lists** (Entity List, Denied Persons List,
     Unverified List, Military End User List) — new for this project, via
     the International Trade Administration's Consolidated Screening List
     (a single public CSV covering eleven Commerce/State/Treasury lists).
   - **Foreign state-connected lenders** — a curated, cited list of
     institutions majority-owned or controlled by a government on
     FriendShore's `HIGH_RISK_COUNTRIES` list (China, Russia, Iran, North
     Korea, Belarus, Venezuela). This is the genuinely novel signal: most
     of these institutions (China Development Bank, the PRC's "Big Four"
     state commercial banks) are **not** OFAC/BIS-listed at all — China
     is not comprehensively sanctioned the way Russia/Iran/North Korea
     are — so a Chinese state policy bank becoming a defense supplier's
     lender produces zero sanctions hits. That's exactly the blind spot
     this project exists to surface.
5. **Scores lender concentration** — a Herfindahl-Hirschman Index (HHI)
   over each lender's share of disclosed relationships, plus the
   screening-hit counts, combine into a deterministic 0-100 risk score
   and LOW/MEDIUM/HIGH/CRITICAL tier. Claude never sets the score.
6. **Generates a lender-concentration risk brief** for a given supplier —
   Claude writes the prose synthesis of already-computed facts; it never
   recomputes or contradicts the score.

---

## Genuine Reuse, Not Just a Pattern Match

| Module | Source | What changed |
|---|---|---|
| `edgar_client.py` | GhostTrace's `edgar_client.py` | Same rate limiter, same ticker lookup, same stdlib HTML-to-text. Form types changed from ownership filings (13D/13G/DEF 14A) to debt-disclosure filings (10-K/10-Q/8-K). |
| `entity_resolver.py` | GhostTrace's `entity_resolver.py` | Same normalize+token-sort technique. Fixed a real bug the port surfaced: the original single-pass suffix stripper left "Wells Fargo Bank, N.A." as "wells fargo bank" instead of "wells fargo" because "N.A." splits into two single-char tokens that only collapse to the known suffix "na" on the second (multi-token) pass, which never re-ran the single-token pass. Lender names stack suffixes ("Bank, N.A.") far more than the corporate names GhostTrace originally targeted, so this was fixed to loop to a fixed point. |
| `ofac_checker.py` | GhostTrace's `ofac_checker.py` | **Unchanged algorithm**, reused directly per the build spec. |
| `bis_checker.py` | New | Same rapidfuzz token-sort pattern as `ofac_checker.py`, applied to a different public data source (Consolidated Screening List, BIS-administered rows only). |

---

## Screening Results Are Candidates, Not Confirmations

Every OFAC/BIS/foreign-state-lender hit is a fuzzy name match, never a
confirmed legal identity — the same discipline GhostTrace and CFIUS
Screener apply to their own OFAC screening. Every hit in this tool's
output is labeled as requiring human verification before any compliance
or investment action.

---

## FINRA TRACE — Honestly Unavailable Without a Data Agreement

The spec asks for "FINRA TRACE bond data where available (public)" —
researched before building, per that hedge. FINRA does not offer an
unauthenticated public API for issuer-level bond transaction history;
detailed TRACE data requires FINRA member access or a fee-based
Historical Data Agreement (FINRA's own "TRACE Data & Licensing" page).
FINRA does publish aggregate, market-wide statistics (e.g. the daily
corporate-bond "Report Card") without authentication, but that's useless
for "who is lending to this one defense supplier."

Rather than silently return an empty result (indistinguishable from "we
checked and found nothing") or fabricate data, `trace_client.py` returns
an explicit `TraceResult(available=False, reason="...")` that the brief
states plainly every time. `fetch_bond_activity()` is the integration
point if a data agreement is ever obtained — the rest of the pipeline
already handles both a populated and an unavailable TRACE result.

---

## Architecture

```
config.py                       Thresholds, cited foreign-state-lender list, risk weights -- no logic
edgar_client.py                    SEC EDGAR HTTP layer (adapted from GhostTrace)
entity_resolver.py                   Lender name normalization + dedup (ported from GhostTrace, bug-fixed)
ofac_checker.py                       OFAC SDN screening (reused directly from GhostTrace)
bis_checker.py                         BIS export-control list screening (new)
foreign_state_lender_checker.py         Curated foreign state-connected lender screening (new, no network)
trace_client.py                          Honest FINRA TRACE "unavailable" stub
screening.py                              Orchestrates all three checkers into one hit list
claude_lender_extractor.py                 Claude: filing text -> structured LenderRecord list
risk_engine.py                              Deterministic HHI concentration + weighted risk score
brief.py                                     Risk brief synthesis (DEMO_MODE template or live Claude)
pipeline.py                                   Live orchestration: EDGAR -> Claude -> dedup -> screen -> TRACE
seed_data.py                                   Fictional demo supplier ("Meridian Defense Systems, Inc.")
dashboard.py                                    Rich terminal rendering (ASCII-safe -- Table AND Panel)
main.py                                          Click CLI
```

---

## Quick Start

```bash
git clone https://github.com/JakPot42/debt-exposure-monitor.git
cd debt-exposure-monitor
python -m venv venv
venv\Scripts\pip install -r requirements.txt
venv\Scripts\python main.py demo
```

## Commands

```bash
python main.py demo                       # fictional demo supplier, live OFAC/BIS screening, no API key needed
python main.py screen "Lockheed Martin"    # real company (needs ANTHROPIC_API_KEY for extraction)
python main.py screen "LMT" --format json  # machine-readable output
```

`demo` needs zero API keys for lender extraction (pre-baked records, same
DEMO_MODE convention as the rest of this portfolio) but genuinely calls
the live public OFAC SDN and BIS Consolidated Screening List data — no
key required for those, same "DEMO_MODE skips paid calls, not free
public-data calls" pattern GhostTrace established for its own OFAC
screening. First run downloads the public lists (a few hundred KB for
OFAC, ~16 MB for the Consolidated Screening List) and may take several
seconds.

`screen` is always live — it needs a real `ANTHROPIC_API_KEY` to extract
lenders from real filing text; there's no meaningful "demo" version of
checking a real company.

---

## Tests

```bash
python -m pytest -q
# 96 passed
```

No test makes a real HTTP call — EDGAR, Claude, OFAC, and BIS are all
mocked, same discipline as GhostTrace's own test suite ("No test ever
makes a real HTTP call"). Covers: entity resolution (including the
suffix-stripping bug fix above), EDGAR client filing filters/caps, both
screening checkers (including a check that a Treasury-sourced row never
leaks into BIS results even on a name match), the foreign-state-lender
curated list, the FINRA TRACE stub, deterministic HHI concentration and
risk scoring (including tier boundaries and score capping), Claude
extraction (including malformed-response handling), full pipeline
orchestration (company disambiguation, dedup, screening wiring), and
end-to-end CLI commands.

---

## Honest Limitations

- FINRA TRACE issuer-level data is unavailable without a paid data
  agreement — see above. The bond-issuance signal here comes entirely
  from SEC EDGAR footnote/8-K disclosures.
- Claude's lender extraction depends on filing text actually naming
  specific lenders; a syndicate described only as "a group of lenders"
  with no names given yields no record, by design (the extraction prompt
  explicitly forbids inferring an unnamed entity).
- Lender-concentration scoring uses a relationship-count HHI, not a
  dollar-volume-weighted HHI — filing text rarely gives clean per-lender
  dollar splits for a syndicate. Disclosed simplification, not hidden
  (see `risk_engine.py`).
- The foreign state-connected lender list is curated and necessarily
  incomplete — it covers well-documented, major institutions with cited
  ownership sources, not an exhaustive registry.
- Fuzzy name matching (OFAC, BIS, foreign-state-lender) produces
  candidates requiring human verification, never confirmed identities.

---

*All OFAC/BIS/foreign-state-lender matches are candidates from fuzzy name
matching, not confirmed identities. Human verification required before
any compliance or investment action.*
