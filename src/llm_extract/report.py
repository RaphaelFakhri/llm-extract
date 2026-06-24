"""Render human-readable verification/QA reports.

Provides both a Markdown rendering (for committing / PR comments) and a rich
console rendering (for interactive runs). The report always lists every flagged
record so failures are never silent.
"""

from __future__ import annotations

from collections import defaultdict

from rich.console import Console
from rich.table import Table

from llm_extract.schemas import ValidationReport


def render_markdown(report: ValidationReport) -> str:
    """Render the report as Markdown."""
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "# Extraction Verification Report",
        "",
        f"- **Status:** {status}",
        f"- **Total records:** {report.total}",
        f"- **Valid:** {report.valid}",
        f"- **Flagged:** {report.flagged}",
        "",
    ]
    if not report.issues:
        lines.append("No issues detected. All records passed verification.")
        return "\n".join(lines) + "\n"

    by_kind: dict[str, list] = defaultdict(list)
    for issue in report.issues:
        by_kind[issue.kind].append(issue)

    lines.append("## Flagged records")
    lines.append("")
    lines.append("| Source | Record | Kind | Message |")
    lines.append("| --- | --- | --- | --- |")
    for kind in sorted(by_kind):
        for issue in by_kind[kind]:
            msg = issue.message.replace("|", "\\|")
            lines.append(f"| {issue.source} | {issue.record_id} | {issue.kind} | {msg} |")
    lines.append("")
    return "\n".join(lines) + "\n"


def print_console(report: ValidationReport, *, console: Console | None = None) -> None:
    """Pretty-print the report to the console using rich."""
    console = console or Console()
    status_style = "bold green" if report.passed else "bold red"
    status = "PASS" if report.passed else "FAIL"
    console.print(f"Verification: [{status_style}]{status}[/]")
    console.print(f"  total={report.total} valid={report.valid} flagged={report.flagged}")
    if not report.issues:
        console.print("  [green]No issues detected.[/]")
        return

    table = Table(title="Flagged records", show_lines=False)
    table.add_column("Source")
    table.add_column("Record")
    table.add_column("Kind")
    table.add_column("Message")
    for issue in sorted(report.issues, key=lambda i: (i.kind, i.source, i.record_id)):
        table.add_row(issue.source, issue.record_id, issue.kind, issue.message)
    console.print(table)
