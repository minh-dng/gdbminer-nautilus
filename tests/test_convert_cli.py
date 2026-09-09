"""CLI tests for convert (ticket #3)."""

import json
from pathlib import Path

from gdbminer_nautilus.convert import main

FIXTURE = Path(__file__).parent / "fixtures" / "calc_like.parsing_g.json"


def test_cli_help() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_cli_summary_only(capsys) -> None:
    code = main([str(FIXTURE)])
    captured = capsys.readouterr()
    assert code == 0
    summary = json.loads(captured.out)
    assert summary["source_start"] == "<START>"
    assert summary["rules"] >= 1
    assert "note: summary only" in captured.err


def test_cli_writes_artifacts(tmp_path: Path) -> None:
    out = tmp_path / "nautilus.json"
    smap = tmp_path / "symbol-map.json"
    code = main([str(FIXTURE), "-o", str(out), "--symbol-map", str(smap)])
    assert code == 0
    rules = json.loads(out.read_text(encoding="utf-8"))
    assert isinstance(rules, list)
    assert rules and isinstance(rules[0], list) and len(rules[0]) == 2
    symbol_map = json.loads(smap.read_text(encoding="utf-8"))
    assert "<START>" in symbol_map
    assert "START" not in symbol_map.values()
    assert all(isinstance(v, str) and v[:1].isupper() for v in symbol_map.values())
