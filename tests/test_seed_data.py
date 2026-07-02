"""Tests for seed_data.py — the fictional demo defense supplier."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import seed_data


class TestDemoLenders:
    def test_includes_a_foreign_state_connected_lender(self):
        names = {l.canonical_name for l in seed_data.DEMO_LENDERS}
        assert "China Development Bank" in names

    def test_includes_an_ofac_relevant_lender(self):
        names = {l.canonical_name for l in seed_data.DEMO_LENDERS}
        assert "VTB Bank" in names

    def test_includes_clean_us_banks_too(self):
        # The demo shouldn't be all-red -- a realistic mix includes normal lenders.
        names = {l.canonical_name for l in seed_data.DEMO_LENDERS}
        assert "JPMorgan Chase Bank, N.A." in names
        assert "Goldman Sachs & Co. LLC" in names

    def test_every_lender_has_an_evidence_quote(self):
        assert all(l.evidence_quote.strip() for l in seed_data.DEMO_LENDERS)

    def test_company_name_marked_fictional(self):
        assert "fictional" in seed_data.DEMO_COMPANY_NAME.lower()


class TestBuildDemoProfile:
    def test_wires_provided_screening_hits(self):
        profile = seed_data.build_demo_profile(screening_hits=["placeholder"])
        assert profile.screening_hits == ["placeholder"]

    def test_trace_marked_unavailable(self):
        profile = seed_data.build_demo_profile(screening_hits=[])
        assert profile.trace_available is False
        assert profile.trace_note
