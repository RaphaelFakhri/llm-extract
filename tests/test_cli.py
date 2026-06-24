from __future__ import annotations

import json

from typer.testing import CliRunner

from llm_extract.cli import app

runner = CliRunner()


def test_run_dry_run_offline(tmp_path, monkeypatch):
    # No env vars => mock LLM + JSON fallback.
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GOOGLE_SERVICE_ACCOUNT_JSON", raising=False)
    out = tmp_path / "delivery.json"
    report = tmp_path / "report.md"
    result = runner.invoke(
        app,
        ["run", "--dry-run", "--out", str(out), "--report-out", str(report)],
    )
    assert result.exit_code == 0, result.output
    assert out.exists()
    data = json.loads(out.read_text())
    assert len(data["records"]) == 6
    assert report.exists()
    assert "Verification" in report.read_text() or "Report" in report.read_text()


def test_extract_command(tmp_path):
    out = tmp_path / "ex.json"
    result = runner.invoke(app, ["extract", "--source", "source_a", "--out", str(out)])
    assert result.exit_code == 0, result.output
    data = json.loads(out.read_text())
    assert {r["record_id"] for r in data["records"]} == {
        "product_001",
        "product_002_missing_price",
        "product_003_nested_specs",
    }


def test_verify_command_exit_code(tmp_path):
    result = runner.invoke(app, ["verify", "--source", "source_a"])
    # source_a alone has no cross-source divergence and clean records => pass.
    assert result.exit_code == 0, result.output
    assert "PASS" in result.output


def test_deliver_dry_run(tmp_path):
    out = tmp_path / "d.json"
    result = runner.invoke(app, ["deliver", "--dry-run", "--out", str(out)])
    assert result.exit_code == 0, result.output
    assert out.exists()
