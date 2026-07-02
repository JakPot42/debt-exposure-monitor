"""trace_client.py — FINRA TRACE bond secondary-market data.

Researched before building (per the spec's "where available" hedge):
FINRA does not offer an unauthenticated public API for issuer-level TRACE
transaction history. Detailed corporate-bond TRACE data requires either
FINRA member access or a Historical Data Agreement (fee-based),
per FINRA's own "TRACE Data & Licensing" page. FINRA does publish
aggregate market statistics (e.g. the daily corporate-bond "Report Card")
without authentication, but that's market-wide, not issuer-specific --
useless for "who is lending to this one defense supplier."

Rather than silently return an empty list (which would look identical to
"we checked and found nothing") or fabricate data, this module returns an
explicit, labeled "unavailable" result so the brief can say so plainly.
If a FINRA data agreement is ever obtained, `fetch_bond_activity` is the
integration point -- swap the body of this function, the rest of the
pipeline (risk_engine.py, brief.py) is agreement-agnostic and already
handles both a populated and an empty/unavailable TRACE result.
"""
from __future__ import annotations

from dataclasses import dataclass

from config import TRACE_DATA_AGREEMENT_REQUIRED


@dataclass
class TraceResult:
    available: bool
    reason: str
    bond_records: list[dict]


def fetch_bond_activity(cik: int) -> TraceResult:
    if TRACE_DATA_AGREEMENT_REQUIRED:
        return TraceResult(
            available=False,
            reason=(
                "FINRA TRACE issuer-level bond transaction data requires a "
                "Historical Data Agreement with FINRA (fee-based) or FINRA "
                "member access -- there is no unauthenticated public API "
                "for this. This brief's bond-issuance signal comes from SEC "
                "EDGAR 10-K/10-Q footnote disclosures and 8-K Item 1.01/2.03 "
                "filings instead. See README \"Honest Limitations.\""
            ),
            bond_records=[],
        )
    return TraceResult(available=True, reason="", bond_records=[])
