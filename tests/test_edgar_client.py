"""Tests for edgar_client.py — no real HTTP call, httpx mocked."""
from __future__ import annotations

import os
import sys
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import edgar_client


def _reset_ticker_cache():
    edgar_client._TICKER_CACHE["fetched_at"] = 0.0
    edgar_client._TICKER_CACHE["rows"] = []


class TestGetCompanyCandidates:
    def setup_method(self):
        _reset_ticker_cache()

    def _mock_response(self, json_data=None, text_data=None, status=200):
        resp = MagicMock()
        resp.status_code = status
        if json_data is not None:
            resp.json.return_value = json_data
        if text_data is not None:
            resp.text = text_data
        return resp

    def test_exact_ticker_match_first(self):
        tickers = {
            "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
            "1": {"cik_str": 1045810, "ticker": "NVDA", "title": "NVIDIA CORP"},
        }
        with patch("edgar_client.httpx.get", return_value=self._mock_response(json_data=tickers)):
            candidates = edgar_client.get_company_candidates("AAPL")
        assert candidates[0]["ticker"] == "AAPL"

    def test_name_substring_match(self):
        tickers = {"0": {"cik_str": 12345, "ticker": "MDS", "title": "Meridian Defense Systems"}}
        with patch("edgar_client.httpx.get", return_value=self._mock_response(json_data=tickers)):
            candidates = edgar_client.get_company_candidates("Meridian Defense")
        assert len(candidates) == 1
        assert candidates[0]["cik"] == 12345

    def test_empty_query_returns_empty(self):
        assert edgar_client.get_company_candidates("") == []

    def test_no_match_returns_empty(self):
        tickers = {"0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."}}
        with patch("edgar_client.httpx.get", return_value=self._mock_response(json_data=tickers)):
            candidates = edgar_client.get_company_candidates("Zzyxq Nonexistent Corp")
        assert candidates == []

    def test_http_error_raises_edgar_error(self):
        with patch("edgar_client.httpx.get", return_value=self._mock_response(status=500)):
            try:
                edgar_client.get_company_candidates("Apple")
                assert False, "expected EdgarError"
            except edgar_client.EdgarError:
                pass


class TestGetDebtRelevantFilings:
    def _submissions_response(self, forms, accessions, docs, dates):
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "filings": {"recent": {
                "form": forms, "accessionNumber": accessions,
                "primaryDocument": docs, "filingDate": dates,
            }}
        }
        return resp

    def test_filters_to_debt_relevant_forms_only(self):
        resp = self._submissions_response(
            forms=["10-K", "SC 13G", "8-K"],
            accessions=["0001-25-000001", "0001-25-000002", "0001-25-000003"],
            docs=["a.htm", "b.htm", "c.htm"],
            dates=["2025-02-14", "2025-03-01", "2025-04-01"],
        )
        with patch("edgar_client.httpx.get", return_value=resp):
            filings = edgar_client.get_debt_relevant_filings(12345)
        forms = {f["form"] for f in filings}
        assert forms == {"10-K", "8-K"}

    def test_caps_10k_10q_at_configured_max(self):
        forms = ["10-K"] * 5
        resp = self._submissions_response(
            forms=forms,
            accessions=[f"0001-25-00000{i}" for i in range(5)],
            docs=["a.htm"] * 5,
            dates=["2025-01-01"] * 5,
        )
        with patch("edgar_client.httpx.get", return_value=resp):
            filings = edgar_client.get_debt_relevant_filings(12345)
        assert len(filings) == edgar_client.MAX_10K_10Q_PER_TRACE

    def test_caps_8k_at_configured_max(self):
        forms = ["8-K"] * 10
        resp = self._submissions_response(
            forms=forms,
            accessions=[f"0001-25-00000{i}" for i in range(10)],
            docs=["a.htm"] * 10,
            dates=["2025-01-01"] * 10,
        )
        with patch("edgar_client.httpx.get", return_value=resp):
            filings = edgar_client.get_debt_relevant_filings(12345)
        assert len(filings) == edgar_client.MAX_8K_PER_TRACE


class TestFetchDocumentText:
    def test_strips_html_tags(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "<html><body><script>ignored</script><p>Credit facility text.</p></body></html>"
        with patch("edgar_client.httpx.get", return_value=resp):
            text = edgar_client.fetch_document_text(12345, "0001-25-000001", "doc.htm")
        assert "Credit facility text." in text
        assert "ignored" not in text
        assert "<p>" not in text

    def test_plain_text_document_not_stripped(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "Plain text filing content."
        with patch("edgar_client.httpx.get", return_value=resp):
            text = edgar_client.fetch_document_text(12345, "0001-25-000001", "doc.txt")
        assert text == "Plain text filing content."

    def test_truncates_to_max_doc_chars(self):
        resp = MagicMock()
        resp.status_code = 200
        resp.text = "x" * (edgar_client.MAX_DOC_CHARS + 5000)
        with patch("edgar_client.httpx.get", return_value=resp):
            text = edgar_client.fetch_document_text(12345, "0001-25-000001", "doc.txt")
        assert len(text) == edgar_client.MAX_DOC_CHARS
