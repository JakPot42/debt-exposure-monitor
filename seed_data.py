"""seed_data.py — fictional demo defense supplier debt disclosure.

"Meridian Defense Systems, Inc." does not exist -- same convention as
GhostTrace's "Harborview Capital Partners" and CFIUS Screener's fictional
demo entities. Lender records below are pre-extracted (as Claude would
extract them from filing text) so `demo` never needs an ANTHROPIC_API_KEY
or an EDGAR fetch. The three screening checkers (OFAC, BIS, foreign-
state-connected) still run for real against live public data -- same
"DEMO_MODE skips Claude/paid calls, not free public-data calls" pattern
GhostTrace established for OFAC screening.
"""
from __future__ import annotations

from models import LenderRecord, SupplierDebtProfile

DEMO_COMPANY_NAME = "Meridian Defense Systems, Inc. (fictional demo entity)"
DEMO_CIK = None

DEMO_LENDERS: list[LenderRecord] = [
    LenderRecord(
        lender_name="JPMorgan Chase Bank, N.A.",
        canonical_name="JPMorgan Chase Bank, N.A.",
        instrument_type="credit_facility",
        role="administrative_agent",
        amount_text="$150,000,000 senior secured revolving credit facility",
        evidence_quote=(
            "The Company maintains a $150,000,000 senior secured revolving "
            "credit facility with JPMorgan Chase Bank, N.A. serving as "
            "Administrative Agent, maturing in 2028."
        ),
        source_filing="10-K filed 2025-02-14",
    ),
    LenderRecord(
        lender_name="Bank of America, N.A.",
        canonical_name="Bank of America, N.A.",
        instrument_type="credit_facility",
        role="lender",
        amount_text="$50,000,000 syndicate commitment",
        evidence_quote=(
            "Bank of America, N.A. holds a $50,000,000 commitment under the "
            "revolving credit facility as a syndicate lender."
        ),
        source_filing="10-K filed 2025-02-14",
    ),
    LenderRecord(
        lender_name="Goldman Sachs & Co. LLC",
        canonical_name="Goldman Sachs & Co. LLC",
        instrument_type="bond",
        role="underwriter",
        amount_text="$100,000,000 aggregate principal amount of 5.75% senior notes due 2031",
        evidence_quote=(
            "Goldman Sachs & Co. LLC acted as sole underwriter for the "
            "Company's $100,000,000 aggregate principal amount of 5.75% "
            "senior notes due 2031."
        ),
        source_filing="10-K filed 2025-02-14",
    ),
    LenderRecord(
        lender_name="Wells Fargo Bank, N.A.",
        canonical_name="Wells Fargo Bank, N.A.",
        instrument_type="term_loan",
        role="lender",
        amount_text="$50,000,000 incremental term loan",
        evidence_quote=(
            "In the second quarter, Wells Fargo Bank, N.A. joined the "
            "credit agreement as a new lender providing a $50,000,000 "
            "incremental term loan."
        ),
        source_filing="10-Q filed 2025-08-05",
    ),
    LenderRecord(
        lender_name="China Development Bank",
        canonical_name="China Development Bank",
        instrument_type="term_loan",
        role="lender",
        amount_text="$75,000,000 term loan",
        evidence_quote=(
            "On October 28, 2025, the Company entered into a $75,000,000 "
            "term loan agreement with China Development Bank to fund "
            "expansion of the Company's Southeast Asia manufacturing "
            "operations."
        ),
        source_filing="8-K filed 2025-11-03",
    ),
    LenderRecord(
        lender_name="VTB Bank",
        canonical_name="VTB Bank",
        instrument_type="bond",
        role="trustee",
        amount_text="$40,000,000 note purchase agreement",
        evidence_quote=(
            "The Company entered into a $40,000,000 note purchase "
            "agreement in which VTB Bank served as trustee for the note "
            "holders."
        ),
        source_filing="8-K filed 2026-03-10",
    ),
]


def build_demo_profile(screening_hits) -> SupplierDebtProfile:
    """screening_hits is supplied by the caller (screening.screen_lenders
    run against the real, live OFAC/BIS/foreign-state-lender checkers) --
    this function doesn't run the checkers itself so tests and the CLI
    both control exactly when the live/mocked screening call happens."""
    return SupplierDebtProfile(
        company_name=DEMO_COMPANY_NAME,
        cik=DEMO_CIK,
        lenders=DEMO_LENDERS,
        screening_hits=screening_hits,
        trace_available=False,
        trace_note=(
            "FINRA TRACE issuer-level bond transaction data requires a "
            "Historical Data Agreement -- not available in this demo. "
            "See README \"Honest Limitations\"."
        ),
    )
