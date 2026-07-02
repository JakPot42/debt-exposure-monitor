"""config.py — all tunable constants, thresholds, and cited reference
data. No logic lives here.

Third piece of the supply-chain financial intelligence cluster alongside
FriendShore (P3, physical supply chain) and DIB Monitor (P10, equity-level
distress). Neither tracks debt-market lender identity — a foreign
state-connected institution can become a defense supplier's primary
lender without appearing in either physical BOM data or 13F equity
filings. This project closes that gap.
"""
from __future__ import annotations

import os

DEMO_MODE = os.environ.get("DEMO_MODE", "True") == "True"

# ---------------------------------------------------------------------------
# SEC EDGAR — adapted from GhostTrace's edgar_client.py (same rate limiter,
# same company-ticker lookup, same HTML-stripping approach). Form types
# differ: debt disclosures live in 10-K/10-Q footnotes and 8-K Item 1.01/
# 2.03 ("Entry into a Material Definitive Agreement" / "Creation of a
# Direct Financial Obligation") filings, not ownership filings.
# ---------------------------------------------------------------------------
EDGAR_USER_AGENT = "Portfolio research tool (jak.potvin@gmail.com)"
EDGAR_RATE_LIMIT_PER_SEC = 8
EDGAR_COMPANY_TICKERS_URL = "https://www.sec.gov/files/company_tickers.json"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions/CIK{cik:010d}.json"
EDGAR_ARCHIVES_BASE = "https://www.sec.gov/Archives/edgar/data"

DEBT_RELEVANT_FORM_TYPES = ["10-K", "10-Q", "8-K"]
MAX_10K_10Q_PER_TRACE = 2   # most recent of each — footnotes are cumulative, old ones are superseded
MAX_8K_PER_TRACE = 6         # recent 8-Ks are where new credit facilities/bond issuances get announced
MAX_DOC_CHARS = 30_000

# ---------------------------------------------------------------------------
# FINRA TRACE — bond secondary-market transaction data. Detailed
# security-level TRACE data requires a Historical Data Agreement with
# FINRA (fee-based) or FINRA member access; there is no unauthenticated
# public API for issuer-level bond transaction history. This is stated
# here rather than papered over: trace_client.py implements the interface
# but returns a clearly-labeled "unavailable without a data agreement"
# result rather than fabricating data or silently returning nothing.
# See README "Honest Limitations".
# ---------------------------------------------------------------------------
TRACE_DATA_AGREEMENT_REQUIRED = True

# ---------------------------------------------------------------------------
# Entity name normalization — ported directly from GhostTrace's
# entity_resolver.py (config.NORMALIZE_SUFFIXES). Same technique, same
# corporate-suffix list; lender names need the identical treatment
# ("JPMorgan Chase Bank, N.A." vs "JPMorgan Chase & Co.") that GhostTrace
# built for beneficial-ownership names.
# ---------------------------------------------------------------------------
NORMALIZE_SUFFIXES = [
    "inc", "inc.", "incorporated",
    "llc", "l.l.c.",
    "lp", "l.p.", "llp", "l.l.p.",
    "ltd", "ltd.", "limited",
    "corp", "corp.", "corporation",
    "co", "co.", "company",
    "plc", "sa", "s.a.", "ag", "gmbh", "nv", "n.v.", "bv", "b.v.",
    "holdings", "holding", "group",
    "na", "n.a.", "bank",
]
LENDER_DEDUPE_THRESHOLD = 88  # token-sort similarity to treat two extracted lender names as the same entity

# ---------------------------------------------------------------------------
# OFAC SDN screening — reused directly from GhostTrace's ofac_checker.py,
# same URLs, same threshold, same "candidates not confirmed violations"
# framing.
# ---------------------------------------------------------------------------
OFAC_SDN_CSV_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
OFAC_SDN_ALT_URL = "https://www.treasury.gov/ofac/downloads/alt.csv"
OFAC_MATCH_THRESHOLD = 90

# ---------------------------------------------------------------------------
# BIS screening — new for this project. The Commerce Department's Bureau
# of Industry and Security lists (Entity List, Denied Persons List,
# Unverified List, Military End User List) are published as part of the
# International Trade Administration's Consolidated Screening List (CSL),
# a single public CSV covering eleven Commerce/State/Treasury export-
# control and sanctions lists. This module filters to just the
# BIS-administered rows.
# ---------------------------------------------------------------------------
CSL_CSV_URL = "https://data.trade.gov/downloadable_consolidated_screening_list/v1/consolidated.csv"
BIS_SOURCE_MARKERS = [
    "Bureau of Industry and Security",  # matches EL, DPL, UVL, MEU source labels
]
BIS_MATCH_THRESHOLD = 90

# ---------------------------------------------------------------------------
# Foreign state-connected lenders — a curated, cited list of financial
# institutions that are majority state-owned or state-controlled by a
# nation on FriendShore's (P3) HIGH_RISK_COUNTRIES list. This is a
# DIFFERENT signal than OFAC/BIS: most of these institutions are NOT
# sanctioned (China is not comprehensively sanctioned the way Russia/Iran/
# North Korea are), so a Chinese state policy bank becoming a defense
# supplier's primary lender produces zero OFAC/BIS hits but is still a
# real CFIUS-adjacent financial-exposure fact. This is the gap the spec
# describes: "that risk doesn't appear in equity data" -- it doesn't
# appear in sanctions data either.
# ---------------------------------------------------------------------------
HIGH_RISK_COUNTRIES = {
    "China", "PRC", "People's Republic of China", "Russia", "Iran",
    "North Korea", "DPRK", "Belarus", "Venezuela",
}  # identical set to FriendShore's (P3) config.HIGH_RISK_COUNTRIES, for portfolio consistency

FOREIGN_STATE_LENDERS: list[dict] = [
    {
        "name": "China Development Bank",
        "country": "China",
        "basis": "Policy bank wholly owned by the State Council of the PRC.",
        "citation": "China Development Bank Corporation 2023 Annual Report, "
                     "\"Shareholder Structure\" (Ministry of Finance + Central "
                     "Huijin Investment + National Council for Social "
                     "Security Fund -- 100% state ownership).",
    },
    {
        "name": "Export-Import Bank of China",
        "country": "China",
        "basis": "Policy bank wholly owned by the State Council of the PRC.",
        "citation": "Export-Import Bank of China, \"About Us -- Corporate "
                     "Governance\" (state-funded policy financial institution "
                     "directly under the State Council).",
    },
    {
        "name": "Bank of China",
        "country": "China",
        "basis": "Majority state-owned; one of China's \"Big Four\" state "
                  "commercial banks, controlled via Central Huijin Investment.",
        "citation": "Bank of China Limited 2023 Annual Report, \"Substantial "
                     "Shareholders\" (Central Huijin Investment Ltd., a PRC "
                     "sovereign entity, majority shareholder).",
    },
    {
        "name": "Industrial and Commercial Bank of China",
        "country": "China",
        "basis": "Majority state-owned; one of China's \"Big Four\" state "
                  "commercial banks, controlled via Central Huijin Investment.",
        "citation": "ICBC 2023 Annual Report, \"Shareholder Structure\" "
                     "(Central Huijin Investment Ltd. majority shareholder).",
    },
    {
        "name": "China Construction Bank",
        "country": "China",
        "basis": "Majority state-owned; one of China's \"Big Four\" state "
                  "commercial banks, controlled via Central Huijin Investment.",
        "citation": "China Construction Bank 2023 Annual Report, \"Substantial "
                     "Shareholders\" (Central Huijin Investment Ltd. majority "
                     "shareholder).",
    },
    {
        "name": "Agricultural Bank of China",
        "country": "China",
        "basis": "Majority state-owned; one of China's \"Big Four\" state "
                  "commercial banks, controlled via Central Huijin Investment.",
        "citation": "Agricultural Bank of China 2023 Annual Report, "
                     "\"Substantial Shareholders\" (Central Huijin Investment "
                     "Ltd. majority shareholder).",
    },
    {
        "name": "VTB Bank",
        "country": "Russia",
        "basis": "Majority owned by the Russian Federation (Federal Agency "
                  "for State Property Management).",
        "citation": "VTB Bank PJSC ownership disclosure, Russian Federation "
                     "as controlling shareholder (also OFAC SDN-designated "
                     "since Feb 2022 -- see OFAC screening).",
    },
    {
        "name": "Sberbank",
        "country": "Russia",
        "basis": "Majority owned by Russia's National Wealth Fund.",
        "citation": "Sberbank of Russia PJSC ownership disclosure, National "
                     "Wealth Fund of the Russian Federation as controlling "
                     "shareholder (also OFAC SDN-designated since Feb 2022 "
                     "-- see OFAC screening).",
    },
    {
        "name": "Bank Melli Iran",
        "country": "Iran",
        "basis": "Wholly state-owned, Iran's largest commercial bank.",
        "citation": "U.S. Treasury OFAC designation history (also OFAC "
                     "SDN-designated -- see OFAC screening).",
    },
    {
        "name": "Foreign Trade Bank",
        "country": "North Korea",
        "basis": "State bank of the DPRK, primary foreign-exchange bank.",
        "citation": "U.S. Treasury OFAC designation history (also OFAC "
                     "SDN-designated -- see OFAC screening).",
    },
]
FOREIGN_STATE_LENDER_MATCH_THRESHOLD = 88

# ---------------------------------------------------------------------------
# Risk scoring
# ---------------------------------------------------------------------------
RISK_WEIGHT_OFAC_HIT = 35        # matches GhostTrace's RISK_WEIGHT_OFAC_CANDIDATE convention
RISK_WEIGHT_BIS_HIT = 35
RISK_WEIGHT_FOREIGN_STATE_LENDER = 20
RISK_WEIGHT_HIGH_CONCENTRATION = 15  # single lender >50% of disclosed facilities

CONCENTRATION_HHI_HIGH = 5000    # HHI scale 0-10000; >5000 = highly concentrated (DOJ/FTC merger-guideline convention)
CONCENTRATION_HHI_MODERATE = 2500

RISK_TIERS = [
    (25, "LOW"),
    (50, "MEDIUM"),
    (75, "HIGH"),
]
RISK_TIER_DEFAULT = "CRITICAL"

# ---------------------------------------------------------------------------
# Claude — extraction and brief synthesis only. Claude never scores; the
# risk tier is entirely deterministic (risk_engine.py). "Claude extracts,
# rules decide" -- the doctrine used throughout this portfolio.
# ---------------------------------------------------------------------------
CLAUDE_MODEL = "claude-haiku-4-5-20251001"
