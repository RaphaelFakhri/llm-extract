"""Typer CLI orchestrating ingest -> chain -> verify -> deliver.

Commands
--------
extract  : ingest + run the chain, write JSON.
verify   : ingest + chain + run the verification gate, print/emit a report.
deliver  : verify, then deliver to Sheets (or JSON fallback).
run      : the full pipeline end-to-end.

Everything runs offline by default (mock LLM, JSON sink). With ``--dry-run`` no
external delivery occurs even when credentials are present.
"""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

from llm_extract.chain import ExtractionChain
from llm_extract.config import get_settings
from llm_extract.consistency import check_consistency
from llm_extract.delivery.json_sink import write_json
from llm_extract.delivery.sheets import SheetsDelivery, build_gspread_client
from llm_extract.ingest.fixtures import load_fixtures
from llm_extract.llm import build_client
from llm_extract.report import print_console, render_markdown
from llm_extract.schemas import ExtractionResult
from llm_extract.verify import GateConfig, verify

app = typer.Typer(
    add_completion=False,
    help="LLM-assisted extraction from messy HTML to validated, delivered data.",
)
console = Console()


def _ingest(source: str | None):
    return list(load_fixtures(source))


def _build_chain():
    settings = get_settings()
    client = build_client(settings)
    mode = "OpenRouter" if settings.use_real_llm else "mock"
    console.print(f"[dim]LLM client: {mode}[/]")
    return ExtractionChain(llm=client), settings


@app.command()
def extract(
    source: str | None = typer.Option(None, "--source", help="Limit to one source id."),
    out: Path = typer.Option(Path("out/extraction.json"), "--out", help="JSON output path."),
) -> None:
    """Ingest fixtures and run the extraction chain, writing JSON."""
    chain, _ = _build_chain()
    snippets = _ingest(source)
    result, errors = chain.run_with_errors(snippets)
    write_json(result, out)
    console.print(
        f"Extracted [bold]{len(result.records)}[/] records " f"({len(errors)} failed) -> {out}"
    )


@app.command(name="verify")
def verify_cmd(
    source: str | None = typer.Option(None, "--source"),
    report_out: Path | None = typer.Option(
        None, "--report-out", help="Optional path to write the Markdown report."
    ),
) -> None:
    """Run extraction and the verification gate; emit a report and exit code."""
    chain, settings = _build_chain()
    snippets = _ingest(source)
    result, errors = chain.run_with_errors(snippets)
    cons = check_consistency(result, price_tolerance_pct=settings.price_tolerance_pct)
    report = verify(
        result,
        extraction_errors=errors,
        config=GateConfig(price_tolerance_pct=settings.price_tolerance_pct),
        consistency=cons,
    )
    print_console(report, console=console)
    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(render_markdown(report), encoding="utf-8")
        console.print(f"[dim]Report written to {report_out}[/]")
    raise typer.Exit(code=0 if report.passed else 1)


def _deliver(result: ExtractionResult, settings, *, dry_run: bool, out: Path) -> None:
    if dry_run or not settings.use_sheets:
        path = write_json(result, out)
        target = "dry-run" if dry_run else "JSON fallback (no Sheets credentials)"
        console.print(f"Delivered {len(result.records)} records via {target} -> {path}")
        return
    client = build_gspread_client(settings.google_service_account_json or "")
    delivery = SheetsDelivery(client, sheet_id=settings.gsheet_id or "")
    written = delivery.deliver(result)
    console.print(f"Delivered [bold]{written}[/] records to Google Sheet {settings.gsheet_id}")


@app.command()
def deliver(
    source: str | None = typer.Option(None, "--source"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Never call external services."),
    out: Path = typer.Option(Path("out/delivery.json"), "--out"),
) -> None:
    """Verify then deliver (Sheets when configured, else JSON)."""
    chain, settings = _build_chain()
    snippets = _ingest(source)
    result, errors = chain.run_with_errors(snippets)
    report = verify(
        result,
        extraction_errors=errors,
        config=GateConfig(price_tolerance_pct=settings.price_tolerance_pct),
    )
    print_console(report, console=console)
    if not report.passed:
        console.print("[red]Verification failed — delivery blocked.[/]")
        raise typer.Exit(code=1)
    _deliver(result, settings, dry_run=dry_run, out=out)


@app.command()
def run(
    source: str | None = typer.Option(None, "--source"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Never call external services."),
    out: Path = typer.Option(Path("out/delivery.json"), "--out"),
    report_out: Path | None = typer.Option(None, "--report-out"),
) -> None:
    """Run the full pipeline: ingest -> chain -> verify -> deliver."""
    chain, settings = _build_chain()
    snippets = _ingest(source)
    console.print(f"Ingested [bold]{len(snippets)}[/] snippets")
    result, errors = chain.run_with_errors(snippets)
    cons = check_consistency(result, price_tolerance_pct=settings.price_tolerance_pct)
    report = verify(
        result,
        extraction_errors=errors,
        config=GateConfig(price_tolerance_pct=settings.price_tolerance_pct),
        consistency=cons,
    )
    print_console(report, console=console)
    if report_out:
        report_out.parent.mkdir(parents=True, exist_ok=True)
        report_out.write_text(render_markdown(report), encoding="utf-8")
    if not report.passed:
        console.print("[red]Verification failed — delivery blocked.[/]")
        raise typer.Exit(code=1)
    _deliver(result, settings, dry_run=dry_run, out=out)


if __name__ == "__main__":  # pragma: no cover
    app()
