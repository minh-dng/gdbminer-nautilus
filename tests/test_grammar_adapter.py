"""Contract tests for the GDBMiner → NAUTILUS adapter seam (tickets #3/#4)."""

from pathlib import Path

import pytest

from gdbminer_nautilus import (
    ConversionError,
    convert_gdbminer_to_nautilus,
    escape_terminal,
    load_gdbminer_grammar,
)

FIXTURE = Path(__file__).parent / "fixtures" / "calc_like.parsing_g.json"


def _doc(grammar: dict, start: str = "<START>") -> dict:
    return {"[start]": start, "[grammar]": grammar}


def test_convert_calc_like_fixture() -> None:
    converted = convert_gdbminer_to_nautilus(load_gdbminer_grammar(FIXTURE))
    assert converted.source_start == "<START>"
    assert converted.rules
    # First rule nonterminal is the mapped start (NAUTILUS loader uses rules[0][0])
    assert converted.rules[0].nonterminal == converted.start_nonterminal
    assert converted.start_nonterminal != "START"
    # Digit class is defined explicitly in the fixture — must not be broadened
    assert converted.class_expansions == {}
    # RHS uses {NT} references or literals
    rhs_values = [rule.rhs for rule in converted.rules]
    assert any("{" in rhs for rhs in rhs_values)


def test_symbol_map_collisions_are_suffixed() -> None:
    doc = _doc(
        {
            "<START>": [["<A.0>"]],
            "<A.0>": [["x"]],
            "<A_0>": [["y"]],  # sanitizes near A_0 / A0
        }
    )
    # force two symbols that sanitize to the same identifier
    doc = _doc(
        {
            "<START>": [["<foo bar>"], ["<foo-bar>"]],
            "<foo bar>": [["a"]],
            "<foo-bar>": [["b"]],
        }
    )
    converted = convert_gdbminer_to_nautilus(doc)
    mapped = list(converted.symbol_map.values())
    assert len(mapped) == len(set(mapped))
    assert "START" not in mapped


def test_undefined_nonterminal_fails() -> None:
    doc = _doc({"<START>": [["<missing>"]]})
    with pytest.raises(ConversionError, match="undefined nonterminals"):
        convert_gdbminer_to_nautilus(doc)


def test_missing_start_fails() -> None:
    doc = _doc({"<OTHER>": [["x"]]}, start="<START>")
    with pytest.raises(ConversionError, match="start symbol"):
        convert_gdbminer_to_nautilus(doc)


def test_nonproductive_start_fails() -> None:
    doc = _doc({"<START>": [["<START>"]]})
    with pytest.raises(ConversionError, match="non-productive"):
        convert_gdbminer_to_nautilus(doc)


def test_explicit_digit_productions_not_broadened() -> None:
    doc = _doc(
        {
            "<START>": [["<__DIGIT__>"]],
            "<__DIGIT__>": [["0"], ["1"]],
        }
    )
    converted = convert_gdbminer_to_nautilus(doc)
    assert converted.class_expansions == {}
    digit_nt = converted.symbol_map["<__DIGIT__>"]
    digit_rules = [r for r in converted.rules if r.nonterminal == digit_nt]
    assert {r.rhs for r in digit_rules} == {"0", "1"}


def test_implicit_class_expansion_recorded() -> None:
    doc = _doc({"<START>": [["<__DIGIT__>"]]})
    converted = convert_gdbminer_to_nautilus(doc)
    assert "<__DIGIT__>" in converted.class_expansions
    assert set(converted.class_expansions["<__DIGIT__>"]) == set("0123456789")
    digit_nt = converted.symbol_map["<__DIGIT__>"]
    digit_rules = [r for r in converted.rules if r.nonterminal == digit_nt]
    assert len(digit_rules) == 10


def test_unknown_class_fails() -> None:
    doc = _doc({"<START>": [["<__NOT_A_REAL_CLASS__>"]]})
    with pytest.raises(ConversionError, match="undefined nonterminals"):
        convert_gdbminer_to_nautilus(doc)


def test_escape_braces_in_terminals() -> None:
    assert escape_terminal("{") == "\\{"
    assert escape_terminal("a}b") == "a\\}b"
    assert escape_terminal("back\\slash") == "back\\\\slash"
    doc = _doc({"<START>": [["{", "}"]]})
    converted = convert_gdbminer_to_nautilus(doc)
    assert converted.rules[0].rhs == "\\{\\}"
    assert set(converted.escaped_terminals) == {"{", "}"}


def test_epsilon_vs_empty_string_terminal() -> None:
    doc = _doc({"<START>": [[], [""]]})
    converted = convert_gdbminer_to_nautilus(doc)
    rhss = [r.rhs for r in converted.rules if r.nonterminal == converted.start_nonterminal]
    assert "" in rhss
    # both alternatives produce empty RHS; document equality is a known limitation
    # until NAUTILUS distinguishes them — recorded as two rules
    assert len(rhss) == 2
