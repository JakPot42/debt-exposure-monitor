"""Tests for ofac_checker.py — no real HTTP call, network mocked."""
from __future__ import annotations

import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import ofac_checker

_SDN_ROWS = [
    ["1", "VTB BANK", "Entity", "RUSSIA-EO14024", ""],
    ["2", "SBERBANK", "Entity", "RUSSIA-EO14024", ""],
    ["3", "-0-", "-0-", "-0-", ""],
]
_ALT_ROWS = [
    ["1", "1", "aka", "VTB BANK PJSC", ""],
]


def _reset_cache():
    ofac_checker._sdn_entries = None


class TestScreenEntities:
    def setup_method(self):
        _reset_cache()

    def teardown_method(self):
        _reset_cache()

    def test_exact_match_found(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=[_SDN_ROWS, _ALT_ROWS]):
            hits = ofac_checker.screen_entities(["VTB Bank"])
        assert len(hits) >= 1
        assert any(h.sdn_name == "VTB BANK" for h in hits)

    def test_no_match_for_unrelated_name(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=[_SDN_ROWS, _ALT_ROWS]):
            hits = ofac_checker.screen_entities(["JPMorgan Chase Bank, N.A."])
        assert hits == []

    def test_empty_input_no_crash(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=[_SDN_ROWS, _ALT_ROWS]):
            hits = ofac_checker.screen_entities([])
        assert hits == []

    def test_placeholder_rows_skipped(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=[_SDN_ROWS, _ALT_ROWS]):
            hits = ofac_checker.screen_entities(["-0-"])
        assert hits == []

    def test_cache_populated_once(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=[_SDN_ROWS, _ALT_ROWS]) as mock_fetch:
            ofac_checker.screen_entities(["VTB Bank"])
            ofac_checker.screen_entities(["Sberbank"])
        assert mock_fetch.call_count == 2  # sdn.csv + alt.csv fetched once total, not once per call

    def test_download_failure_returns_empty_not_crash(self):
        with patch.object(ofac_checker, "_fetch_csv_rows", side_effect=Exception("network down")):
            hits = ofac_checker.screen_entities(["VTB Bank"])
        assert hits == []
