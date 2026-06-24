from __future__ import annotations

from llm_extract.report import render_markdown
from llm_extract.schemas import RecordIssue, ValidationReport


def test_markdown_clean_report():
    report = ValidationReport.from_counts(total=3, valid=3, issues=[], passed=True)
    md = render_markdown(report)
    assert "PASS" in md
    assert "No issues detected" in md


def test_markdown_lists_flagged_records():
    issues = [
        RecordIssue(record_id="r1", source="a", kind="consistency", message="price | divergence"),
        RecordIssue(record_id="r2", source="b", kind="schema", message="bad json"),
    ]
    report = ValidationReport.from_counts(total=2, valid=1, issues=issues, passed=False)
    md = render_markdown(report)
    assert "FAIL" in md
    assert "r1" in md and "r2" in md
    # pipe characters in messages are escaped so the table stays valid
    assert "price \\| divergence" in md
