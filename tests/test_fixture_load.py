"""Smoke tests for package import and fixture loading (ticket #2)."""

from pathlib import Path

import pytest

from gdbminer_nautilus import (
    GDBMINER_GRAMMAR_KEY,
    GDBMINER_START_KEY,
    load_gdbminer_grammar,
)
from gdbminer_nautilus.grammar_adapter import GrammarLoadError

FIXTURE = Path(__file__).parent / "fixtures" / "calc_like.parsing_g.json"


def test_load_calc_like_fixture() -> None:
    document = load_gdbminer_grammar(FIXTURE)
    assert document[GDBMINER_START_KEY] == "<START>"
    assert GDBMINER_GRAMMAR_KEY in document
    assert isinstance(document[GDBMINER_GRAMMAR_KEY], dict)
    assert len(document[GDBMINER_GRAMMAR_KEY]) >= 1


def test_load_rejects_missing_start(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text('{"[grammar]": {}}', encoding="utf-8")
    with pytest.raises(GrammarLoadError, match="\\[start\\]"):
        load_gdbminer_grammar(path)


def test_load_rejects_non_object(tmp_path: Path) -> None:
    path = tmp_path / "bad.json"
    path.write_text("[1, 2]", encoding="utf-8")
    with pytest.raises(GrammarLoadError, match="JSON object"):
        load_gdbminer_grammar(path)
