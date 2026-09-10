"""Load and validate GDBMiner ``parsing_g.json`` documents."""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Union

GDBMINER_GRAMMAR_KEY = "[grammar]"
GDBMINER_START_KEY = "[start]"
NAUTILUS_ROOT_SYMBOL = "START"

_GDBMINER_NONTERMINAL_RE = re.compile(r"^<(.+)>$")


class GrammarLoadError(ValueError):
    """Raised when a GDBMiner grammar document is structurally invalid."""


def load_gdbminer_grammar(path: Union[str, Path]) -> Mapping[str, Any]:
    """Load a GDBMiner grammar JSON document and check required keys."""
    grammar_path = Path(path)
    try:
        with grammar_path.open(encoding="utf-8") as grammar_file:
            document = json.load(grammar_file)
    except json.JSONDecodeError as exc:
        raise GrammarLoadError(f"{grammar_path} is not valid JSON: {exc}") from exc

    if not isinstance(document, Mapping):
        raise GrammarLoadError(f"{grammar_path} must contain a JSON object")
    if GDBMINER_START_KEY not in document:
        raise GrammarLoadError(f"{grammar_path} is missing {GDBMINER_START_KEY!r}")
    if GDBMINER_GRAMMAR_KEY not in document:
        raise GrammarLoadError(f"{grammar_path} is missing {GDBMINER_GRAMMAR_KEY!r}")
    if not isinstance(document[GDBMINER_START_KEY], str):
        raise GrammarLoadError(f"{GDBMINER_START_KEY} must be a string")
    if not isinstance(document[GDBMINER_GRAMMAR_KEY], Mapping):
        raise GrammarLoadError(f"{GDBMINER_GRAMMAR_KEY} must be an object")

    return document


def expect_gdbminer_nonterminal(symbol: Any) -> str:
    """Return ``symbol`` if it looks like a GDBMiner nonterminal."""
    if not isinstance(symbol, str) or not _GDBMINER_NONTERMINAL_RE.match(symbol):
        raise GrammarLoadError(f"expected GDBMiner nonterminal like '<name>', got {symbol!r}")
    return symbol


def expect_alternatives(value: Any, nonterminal: str) -> list[list[str]]:
    """Validate one nonterminal's alternatives as lists of string tokens."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise GrammarLoadError(f"rules for {nonterminal!r} must be a list")
    alternatives: list[list[str]] = []
    for alternative in value:
        if not isinstance(alternative, Sequence) or isinstance(alternative, (str, bytes)):
            raise GrammarLoadError(f"alternative for {nonterminal!r} must be a token list")
        tokens: list[str] = []
        for token in alternative:
            if not isinstance(token, str):
                raise GrammarLoadError(f"token in {nonterminal!r} must be a string")
            tokens.append(token)
        alternatives.append(tokens)
    return alternatives
