"""End-to-end CLI tests. `demo` command's screening step is mocked so no
test in this file makes a real network call (same "no test ever makes a
real HTTP call" discipline as GhostTrace's own test suite)."""
from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

from click.testing import CliRunner

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import cli
from models import ScreeningHit


def _run(*args):
    runner = CliRunner()
    return runner.invoke(cli, args)


_FAKE_HITS = [
    ScreeningHit(list_name="OFAC SDN", lender_name="VTB Bank", matched_name="VTB BANK", score=100, detail="Program: RUSSIA-EO14024 (entity)", citation="U.S. Treasury OFAC SDN"),
    ScreeningHit(list_name="Foreign State-Connected Lender", lender_name="China Development Bank", matched_name="China Development Bank", score=100, detail="China: Policy bank", citation="cite"),
    ScreeningHit(list_name="Foreign State-Connected Lender", lender_name="VTB Bank", matched_name="VTB Bank", score=100, detail="Russia: Majority state-owned", citation="cite"),
]


class TestDemoCommand:
    def test_runs_without_error(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert result.exit_code == 0

    def test_shows_gap_framing_banner(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert "FUNDING defense suppliers" in result.output

    def test_shows_lender_table(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert "JPMorgan" in result.output
        assert "China Development" in result.output

    def test_shows_screening_hits(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert "OFAC SDN" in result.output
        assert "Foreign" in result.output

    def test_shows_verification_required_note(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        flat = " ".join(result.output.split())
        assert "CANDIDATES" in flat
        assert "human verification" in flat

    def test_shows_risk_score(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert "Lender-Concentration Risk" in result.output

    def test_shows_trace_unavailable_note(self):
        with patch("screening.screen_lenders", return_value=_FAKE_HITS):
            result = _run("demo")
        assert "Historical Data Agreement" in result.output

    def test_clean_screening_shows_no_matches_message(self):
        with patch("screening.screen_lenders", return_value=[]):
            result = _run("demo")
        assert "No OFAC, BIS, or foreign state-connected lender matches" in result.output


class TestScreenCommand:
    def test_unknown_company_fails_cleanly(self):
        with patch("edgar_client.get_company_candidates", return_value=[]):
            result = _run("screen", "Totally Nonexistent Company Zzyxq")
        assert result.exit_code != 0

    def test_ambiguous_company_lists_candidates(self):
        candidates = [
            {"cik": 1, "ticker": "ABCD", "name": "ABC Defense Systems"},
            {"cik": 2, "ticker": "ABCH", "name": "ABC Holdings Group"},
        ]
        with patch("edgar_client.get_company_candidates", return_value=candidates):
            result = _run("screen", "ABC")
        assert result.exit_code != 0
        assert "ABCD" in result.output
        assert "ABCH" in result.output


class TestGroupHelp:
    def test_help_mentions_candidates_framing(self):
        result = _run("--help")
        assert "candidates" in result.output.lower()
