"""Tests for entity_resolver.py — ported from GhostTrace's pattern, so
tests mirror GhostTrace's own test_entity_resolver.py coverage style."""
from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from entity_resolver import dedupe_lenders, normalize_name, similarity


class TestNormalizeName:
    def test_strips_suffix(self):
        assert normalize_name("JPMorgan Chase Bank, N.A.") == "jpmorgan chase"

    def test_strips_punctuated_suffix(self):
        assert normalize_name("Wells Fargo Bank, N.A.") == "wells fargo"

    def test_lowercases(self):
        assert normalize_name("GOLDMAN SACHS & CO. LLC") == "goldman sachs"

    def test_empty_string(self):
        assert normalize_name("") == ""

    def test_bank_suffix_stripped(self):
        assert normalize_name("VTB Bank") == "vtb"


class TestSimilarity:
    def test_identical(self):
        assert similarity("China Development Bank", "China Development Bank") == 100.0

    def test_empty_strings(self):
        assert similarity("", "") == 0.0

    def test_completely_different(self):
        assert similarity("JPMorgan Chase", "Zeta Corp") < 50

    def test_suffix_variant_high(self):
        assert similarity("JPMorgan Chase Bank, N.A.", "JPMorgan Chase & Co.") >= 70


class TestDedupeLenders:
    def test_exact_duplicates_collapse(self):
        result = dedupe_lenders(["JPMorgan Chase Bank, N.A.", "JPMorgan Chase Bank, N.A."])
        assert result["JPMorgan Chase Bank, N.A."] == "JPMorgan Chase Bank, N.A."
        assert len(set(result.values())) == 1

    def test_close_variants_collapse_to_first_seen(self):
        names = ["JPMorgan Chase Bank, N.A.", "JPMorgan Chase Bank N.A."]
        result = dedupe_lenders(names)
        assert len(set(result.values())) == 1
        assert result[names[1]] == names[0]

    def test_distinct_lenders_stay_separate(self):
        names = ["JPMorgan Chase Bank, N.A.", "Bank of America, N.A.", "China Development Bank"]
        result = dedupe_lenders(names)
        assert len(set(result.values())) == 3

    def test_empty_list(self):
        assert dedupe_lenders([]) == {}

    def test_every_input_name_is_a_key(self):
        names = ["Goldman Sachs & Co. LLC", "Wells Fargo Bank, N.A."]
        result = dedupe_lenders(names)
        assert set(result.keys()) == set(names)
