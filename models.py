"""models.py — shared dataclasses. No logic."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class LenderRecord:
    """One lender/counterparty extracted from a filing. Claude produces
    these (claude_lender_extractor.py); nothing here scores or flags --
    that's risk_engine.py's job, working from the canonical_name field
    entity_resolver.dedupe_lenders() fills in."""

    lender_name: str
    canonical_name: str
    instrument_type: str      # "credit_facility" | "bond" | "term_loan" | "syndicated_loan" | "other"
    role: str                  # "administrative_agent" | "lender" | "underwriter" | "trustee" | "unspecified"
    amount_text: str
    evidence_quote: str
    source_filing: str         # e.g. "10-K filed 2025-02-14"


@dataclass
class ScreeningHit:
    list_name: str             # "OFAC SDN" | "BIS Entity/Denied/Unverified/MEU List" | "Foreign State-Connected Lender"
    lender_name: str
    matched_name: str
    score: int
    detail: str                 # program / source list / country+basis, depending on list_name
    citation: str = ""


@dataclass
class SupplierDebtProfile:
    company_name: str
    cik: int | None
    lenders: list[LenderRecord] = field(default_factory=list)
    screening_hits: list[ScreeningHit] = field(default_factory=list)
    trace_available: bool = False
    trace_note: str = ""
