"""Tests for trace_client.py — the honest "unavailable" stub."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import trace_client


class TestFetchBondActivity:
    def test_unavailable_by_default(self):
        result = trace_client.fetch_bond_activity(cik=12345)
        assert result.available is False
        assert "Historical Data Agreement" in result.reason
        assert result.bond_records == []

    def test_reason_is_never_empty_when_unavailable(self):
        result = trace_client.fetch_bond_activity(cik=1)
        assert result.reason.strip() != ""
