"""entity_resolver.py — lender name normalization and fuzzy deduplication.

Ported from GhostTrace's (P6) entity_resolver.py, built for corporate
ownership name variants ("Apex Holdings LLC" vs "APEX HOLDINGS"). The
identical problem shows up here: one filing calls a lender "JPMorgan
Chase Bank, N.A." and the next calls it "JPMorgan Chase & Co." -- without
normalization, lender-concentration scoring would see two different
lenders instead of one, understating concentration risk.
"""
from __future__ import annotations

from difflib import SequenceMatcher

from config import LENDER_DEDUPE_THRESHOLD, NORMALIZE_SUFFIXES

_SUFFIX_SET = {s.replace(".", "") for s in NORMALIZE_SUFFIXES}


def normalize_name(name: str) -> str:
    """Lowercase, strip punctuation, drop leading 'the' and corporate
    suffixes -- including repeated/stacked suffixes like "Bank, N.A."
    (two suffix tokens: "bank" and the punctuation-split "n"+"a", which
    only collapses to the known suffix "na" when its two characters are
    joined). Strips to a fixed point: "JPMorgan Chase Bank, N.A." must
    lose BOTH "bank" and "n.a.", not just whichever the single pass hits
    first -- lender names stack these suffixes far more than the
    corporate-ownership names GhostTrace's original version targeted."""
    cleaned = "".join(ch if ch.isalnum() or ch == " " else " " for ch in name.lower())
    tokens = cleaned.split()
    if tokens and tokens[0] == "the":
        tokens = tokens[1:]

    changed = True
    while changed and tokens:
        changed = False
        if tokens[-1] in _SUFFIX_SET:
            tokens = tokens[:-1]
            changed = True
            continue
        for n in (3, 2):
            if len(tokens) >= n and "".join(tokens[-n:]) in _SUFFIX_SET:
                tokens = tokens[:-n]
                changed = True
                break

    return " ".join(tokens)


def similarity(a: str, b: str) -> float:
    """0-100 similarity between two normalized names -- max of a direct
    ratio and a token-sort ratio, so word order doesn't defeat the match."""
    na, nb = normalize_name(a), normalize_name(b)
    if not na or not nb:
        return 0.0
    if na == nb:
        return 100.0
    direct = SequenceMatcher(None, na, nb).ratio()
    ta, tb = na.split(), nb.split()
    token_sort = SequenceMatcher(None, " ".join(sorted(ta)), " ".join(sorted(tb))).ratio()
    return max(direct, token_sort) * 100


def dedupe_lenders(names: list[str]) -> dict[str, str]:
    """Collapses name variants into a canonical form (the first-seen
    spelling). Returns a map of every input name to its canonical form.

    Unlike GhostTrace's full resolve_entities() (which needs an
    adjudicator for the ambiguous band because a wrong merge blends two
    real companies' ownership histories), lender-name variants in a single
    filing set are almost always the same institution spelled two ways --
    a straight high-confidence threshold is the right tradeoff here."""
    canonical_names: list[str] = []
    result: dict[str, str] = {}
    for name in names:
        best_match = None
        best_score = 0.0
        for canonical in canonical_names:
            score = similarity(name, canonical)
            if score > best_score:
                best_score = score
                best_match = canonical
        if best_match is not None and best_score >= LENDER_DEDUPE_THRESHOLD:
            result[name] = best_match
        else:
            canonical_names.append(name)
            result[name] = name
    return result
