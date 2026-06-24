"""Enable ``python -m llm_extract`` to invoke the Typer CLI."""

from __future__ import annotations

from llm_extract.cli import app

if __name__ == "__main__":  # pragma: no cover
    app()
