"""ofac_checker.py — OFAC SDN fuzzy-match screening.

Reused directly from GhostTrace's (P6) ofac_checker.py -- same URLs, same
threshold, same "candidates, not confirmed violations" framing. The only
change is the import path for normalize_name (this project's local
entity_resolver.py rather than GhostTrace's).

Downloads the SDN primary-name list (sdn.csv) and alias list (alt.csv)
from the OFAC website on first call within a process and caches them in
memory. All matches are CANDIDATES -- fuzzy name matching cannot confirm
a legal identity. Every hit requires human verification before any
compliance action.
"""
from __future__ import annotations

import csv
import io
import logging
import urllib.request
from typing import NamedTuple

from rapidfuzz import fuzz
from rapidfuzz import process as rfprocess

from config import OFAC_MATCH_THRESHOLD, OFAC_SDN_ALT_URL, OFAC_SDN_CSV_URL
from entity_resolver import normalize_name

logger = logging.getLogger(__name__)

_sdn_entries: list[tuple[str, str, str, str]] | None = None


class OFACHit(NamedTuple):
    entity_name: str
    sdn_name: str
    score: int
    sdn_program: str
    sdn_type: str


def _fetch_csv_rows(url: str) -> list[list[str]]:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Portfolio research tool (jak.potvin@gmail.com)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        content = resp.read().decode("utf-8", errors="replace")
    return list(csv.reader(io.StringIO(content)))


def _load() -> list[tuple[str, str, str, str]]:
    entries: list[tuple[str, str, str, str]] = []
    seen: set[str] = set()

    try:
        for row in _fetch_csv_rows(OFAC_SDN_CSV_URL):
            if len(row) < 2:
                continue
            name = row[1].strip().strip('"')
            program = row[3].strip().strip('"') if len(row) > 3 else ""
            sdn_type = row[2].strip().strip('"').lower() if len(row) > 2 else "entity"
            if not name or name in ("-0-", "SDN Name", "Name"):
                continue
            norm = normalize_name(name)
            if norm and norm not in seen:
                seen.add(norm)
                entries.append((norm, name, program, sdn_type))
        logger.info("OFAC SDN primary: %d names loaded", len(entries))
    except Exception as exc:
        logger.warning("OFAC SDN primary list unavailable: %s", exc)

    before = len(entries)
    try:
        for row in _fetch_csv_rows(OFAC_SDN_ALT_URL):
            if len(row) < 4:
                continue
            name = row[3].strip().strip('"')
            if not name or name in ("-0-", "Alternate Name", "Alternate name"):
                continue
            norm = normalize_name(name)
            if norm and norm not in seen:
                seen.add(norm)
                entries.append((norm, name, "", "alias"))
        logger.info("OFAC SDN aliases: %d additional names loaded", len(entries) - before)
    except Exception as exc:
        logger.warning("OFAC SDN alias list unavailable: %s", exc)

    return entries


def _ensure_loaded() -> list[tuple[str, str, str, str]]:
    global _sdn_entries
    if _sdn_entries is None:
        _sdn_entries = _load()
    return _sdn_entries


def screen_entities(entity_names: list[str]) -> list[OFACHit]:
    """Fuzzy-match entity names against the OFAC SDN list. Results are
    candidates only -- manual verification required before any compliance
    action."""
    entries = _ensure_loaded()
    if not entries:
        return []

    sdn_norm_names = [e[0] for e in entries]

    hits: list[OFACHit] = []
    for entity_name in entity_names:
        norm_entity = normalize_name(entity_name)
        if not norm_entity:
            continue

        results = rfprocess.extract(
            norm_entity,
            sdn_norm_names,
            scorer=fuzz.token_sort_ratio,
            score_cutoff=OFAC_MATCH_THRESHOLD,
            limit=3,
        )
        for _matched_norm, score, idx in results:
            _norm, original, program, sdn_type = entries[idx]
            hits.append(OFACHit(
                entity_name=entity_name,
                sdn_name=original,
                score=int(score),
                sdn_program=program,
                sdn_type=sdn_type,
            ))

    return hits
