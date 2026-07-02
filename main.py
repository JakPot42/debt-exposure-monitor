"""Defense Supplier Debt Exposure Monitor CLI.

Third piece of the supply-chain financial intelligence cluster alongside
FriendShore (P3, physical supply chain) and DIB Monitor (P10, equity-level
distress). Tracks who is FUNDING a defense supplier through debt markets.
"""
from __future__ import annotations

import os
import sys

import click

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import DEMO_MODE
from dashboard import (
    console,
    print_banner,
    print_brief,
    print_json,
    print_lenders,
    print_risk,
    print_screening,
    print_trace_note,
)
from pipeline import AmbiguousCompanyError, CompanyNotFoundError, build_profile
from risk_engine import score_debt_profile


@click.group()
def cli() -> None:
    """
    Defense Supplier Debt Exposure Monitor: tracks lender identity behind
    a defense supplier's credit facilities and bond issuances -- the debt-
    market gap between FriendShore's (P3) physical supply chain view and
    DIB Monitor's (P10) equity-level distress view.

    \b
    Screens every disclosed lender against OFAC SDN, BIS export-control
    lists (via the Consolidated Screening List), and a curated list of
    foreign state-owned/state-controlled financial institutions. All
    matches are candidates requiring human verification, never confirmed
    findings.
    """


@cli.command()
@click.argument("company_query")
@click.option("--format", "fmt", type=click.Choice(["table", "json"]), default="table")
def screen(company_query: str, fmt: str) -> None:
    """Screen a real, EDGAR-registered company's debt disclosures (live
    mode -- fetches SEC EDGAR and calls Claude for extraction)."""
    if fmt == "table":
        print_banner()
    try:
        profile = build_profile(company_query)
    except CompanyNotFoundError as exc:
        console.print(f"[red]{exc}[/red]")
        raise SystemExit(1)
    except AmbiguousCompanyError as exc:
        console.print(f"[yellow]{exc}[/yellow]")
        for c in exc.candidates:
            console.print(f"  {c['ticker']:<8} {c['name']}")
        raise SystemExit(1)

    risk = score_debt_profile(profile)
    from brief import generate_brief
    text = generate_brief(profile, risk)

    if fmt == "json":
        print_json({
            "company": profile.company_name,
            "cik": profile.cik,
            "lenders": [l.__dict__ for l in profile.lenders],
            "risk": risk,
            "brief": text,
            "trace_available": profile.trace_available,
        })
    else:
        print_lenders(profile)
        print_screening(profile.screening_hits)
        print_risk(risk)
        print_trace_note(profile.trace_available, profile.trace_note)
        print_brief(text)


@cli.command()
def demo() -> None:
    """Run the full pipeline against a fictional demo defense supplier
    ("Meridian Defense Systems, Inc.") with pre-extracted lender records --
    no EDGAR fetch or Claude call needed -- but REAL, live OFAC/BIS
    screening against the actual public sanctions/export-control data."""
    print_banner()
    console.print("[dim]Screening demo lenders against live OFAC SDN and BIS Consolidated Screening List data...[/dim]")
    console.print("[dim]First run may take several seconds -- downloads the public lists (no API key needed).[/dim]\n")

    import seed_data
    from screening import screen_lenders

    canonical_names = sorted({l.canonical_name for l in seed_data.DEMO_LENDERS})
    hits = screen_lenders(canonical_names)
    profile = seed_data.build_demo_profile(hits)

    risk = score_debt_profile(profile)
    from brief import generate_brief
    text = generate_brief(profile, risk)

    print_lenders(profile)
    print_screening(profile.screening_hits)
    print_risk(risk)
    print_trace_note(profile.trace_available, profile.trace_note)
    print_brief(text)

    if DEMO_MODE:
        console.print("[dim]DEMO_MODE=True -- lender extraction uses pre-baked records, not a live Claude call. Screening above is live, real public data.[/dim]")


if __name__ == "__main__":
    cli()
