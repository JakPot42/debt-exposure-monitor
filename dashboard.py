"""Rich terminal dashboard — ASCII-safe for Windows cp1252 console.
Every Table AND Panel must use box.ASCII2 -- a Panel with the default
Unicode box style will crash with UnicodeEncodeError on a real cp1252
console (caught the hard way in this portfolio's P47 build)."""
from __future__ import annotations

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from models import ScreeningHit, SupplierDebtProfile

console = Console(width=110)

TIER_COLORS = {
    "LOW": "green",
    "MODERATE": "yellow",
    "MEDIUM": "yellow",
    "HIGH": "red",
    "CRITICAL": "bold red",
}

_BANNER = "[bold cyan]Defense Supplier Debt Exposure Monitor[/bold cyan]  [dim]v1.0[/dim]"


def print_banner() -> None:
    console.print()
    console.print(_BANNER)
    console.print(
        "[dim]Tracks who is FUNDING defense suppliers through debt markets -- "
        "credit facilities, bond issuances, term loans -- the gap between "
        "physical supply chain (FriendShore) and equity-level distress "
        "(DIB Monitor). Neither tracks debt-market lender identity.[/dim]\n"
    )


def print_lenders(profile: SupplierDebtProfile) -> None:
    console.rule(f"[bold]{profile.company_name}[/bold] -- Disclosed Lenders")
    t = Table(box=box.ASCII2)
    t.add_column("Lender", overflow="fold")
    t.add_column("Instrument")
    t.add_column("Role")
    t.add_column("Amount", overflow="fold")
    t.add_column("Source")
    for l in profile.lenders:
        t.add_row(l.canonical_name, l.instrument_type, l.role, l.amount_text, l.source_filing)
    console.print(t)


def print_screening(hits: list[ScreeningHit]) -> None:
    console.rule("[bold]Counterparty Screening[/bold]")
    if not hits:
        console.print("[green]No OFAC, BIS, or foreign state-connected lender matches.[/green]\n")
        return
    t = Table(box=box.ASCII2)
    t.add_column("List")
    t.add_column("Lender Named in Filing", overflow="fold")
    t.add_column("Matched Against", overflow="fold")
    t.add_column("Score", justify="right")
    t.add_column("Detail", overflow="fold")
    for h in hits:
        t.add_row(h.list_name, h.lender_name, h.matched_name, str(h.score), h.detail)
    console.print(t)
    console.print(
        "[dim]All matches above are CANDIDATES from fuzzy name matching -- "
        "not confirmed identities. Every hit requires human verification "
        "before any compliance or investment action.[/dim]\n"
    )


def print_risk(risk: dict) -> None:
    color = TIER_COLORS.get(risk["tier"], "white")
    console.print(Panel(
        f"Score: [{color}]{risk['score']}/100[/{color}]   Tier: [{color}]{risk['tier']}[/{color}]\n"
        f"Lender concentration (relationship-count HHI): {risk['concentration']['hhi']} "
        f"({risk['concentration']['tier']})",
        box=box.ASCII2,
        title="[bold]Lender-Concentration Risk[/bold]",
        border_style=color,
    ))


def print_brief(text: str) -> None:
    console.rule("[bold]Risk Brief[/bold]")
    console.print(text)
    console.print()


def print_trace_note(available: bool, note: str) -> None:
    if not available:
        console.print(Panel(note, box=box.ASCII2, title="[bold yellow]FINRA TRACE[/bold yellow]", border_style="yellow"))


def print_json(data) -> None:
    import json
    console.print_json(json.dumps(data))
