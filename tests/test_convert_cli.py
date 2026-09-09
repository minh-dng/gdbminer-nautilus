"""CLI smoke tests for the convert entrypoint shell (ticket #2)."""

from pathlib import Path

from gdbminer_nautilus.convert import main

FIXTURE = Path(__file__).parent / "fixtures" / "calc_like.parsing_g.json"


def test_cli_help() -> None:
    try:
        main(["--help"])
    except SystemExit as exc:
        assert exc.code == 0


def test_cli_loads_fixture(capsys) -> None:
    code = main([str(FIXTURE)])
    captured = capsys.readouterr()
    assert code == 0
    assert "loaded" in captured.out
    assert "<START>" in captured.out
