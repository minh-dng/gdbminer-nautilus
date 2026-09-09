"""Load and convert GDBMiner ``parsing_g.json`` documents to NAUTILUS JSON.

NAUTILUS JSON loader contract (pinned ``fuzzer/src/generator.rs``):

- Document is a list of ``[nonterminal, rhs]`` pairs.
- The loader adds ``START -> {rules[0][0]}`` then every rule.
- ``{NT}`` in an RHS is a nonterminal reference; literal braces must be escaped
  as ``\\{`` / ``\\}``.

Fidelity rules are documented in ADR-0001.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Union

GDBMINER_GRAMMAR_KEY = "[grammar]"
GDBMINER_START_KEY = "[start]"
NAUTILUS_ROOT_SYMBOL = "START"

_GDBMINER_NONTERMINAL_RE = re.compile(r"^<(.+)>$")
_NAUTILUS_NAME_RE = re.compile(r"^[A-Z][A-Za-z0-9_-]*$")
_UNSAFE_NAUTILUS_NAME_CHARS_RE = re.compile(r"[^A-Za-z0-9_-]+")
# GDBMiner class-like NTs look like <__DIGIT__>; eval ASCII_MAP uses [__DIGIT__].
_CLASS_LIKE_RE = re.compile(r"^<(__\w+__)>$")

# Documented implicit class table (names from GDBMiner eval ASCII_MAP).
# Explicit productions in the source always win (ADR-0001).
ASCII_CLASS_CHARS: dict[str, str] = {
    "[__DIGIT__]": "0123456789",
    "[__ASCII_LOWER__]": "abcdefghijklmnopqrstuvwxyz",
    "[__ASCII_UPPER__]": "ABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "[__ASCII_LETTER__]": "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ",
    "[__ASCII_ALPHANUM__]": (
        "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    ),
    "[__WHITESPACE__]": " \t\n\r\x0b\x0c",
}


class GrammarLoadError(ValueError):
    """Raised when a GDBMiner grammar document is structurally invalid."""


class ConversionError(ValueError):
    """Raised when a GDBMiner grammar cannot be converted under ADR-0001."""


@dataclass(frozen=True)
class NautilusRule:
    """A single NAUTILUS JSON rule."""

    nonterminal: str
    rhs: str

    def to_json(self) -> list[str]:
        return [self.nonterminal, self.rhs]


@dataclass(frozen=True)
class NautilusGrammar:
    """Converted grammar plus conversion metadata."""

    source_start: str
    start_nonterminal: str
    rules: tuple[NautilusRule, ...]
    symbol_map: Mapping[str, str]
    class_expansions: Mapping[str, str]
    escaped_terminals: tuple[str, ...]

    def to_json(self) -> list[list[str]]:
        return [rule.to_json() for rule in self.rules]

    def summary(self) -> dict[str, Any]:
        return {
            "source_start": self.source_start,
            "nautilus_root": NAUTILUS_ROOT_SYMBOL,
            "start_nonterminal": self.start_nonterminal,
            "nonterminals": len(self.symbol_map),
            "rules": len(self.rules),
            "class_expansions": dict(self.class_expansions),
            "escaped_terminals": list(self.escaped_terminals),
        }


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
        raise GrammarLoadError(
            f"expected GDBMiner nonterminal like '<name>', got {symbol!r}"
        )
    return symbol


def expect_alternatives(value: Any, nonterminal: str) -> list[list[str]]:
    """Validate one nonterminal's alternatives as lists of string tokens."""
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise GrammarLoadError(f"rules for {nonterminal!r} must be a list")
    alternatives: list[list[str]] = []
    for alternative in value:
        if not isinstance(alternative, Sequence) or isinstance(alternative, (str, bytes)):
            raise GrammarLoadError(
                f"alternative for {nonterminal!r} must be a token list"
            )
        tokens: list[str] = []
        for token in alternative:
            if not isinstance(token, str):
                raise GrammarLoadError(f"token in {nonterminal!r} must be a string")
            tokens.append(token)
        alternatives.append(tokens)
    return alternatives


def _parse_source_grammar(
    document: Mapping[str, Any],
) -> tuple[str, dict[str, list[list[str]]]]:
    source_start = document[GDBMINER_START_KEY]
    raw = document[GDBMINER_GRAMMAR_KEY]
    if not isinstance(raw, Mapping):
        raise ConversionError(f"{GDBMINER_GRAMMAR_KEY} must be an object")

    grammar: dict[str, list[list[str]]] = {}
    for key, alternatives in raw.items():
        source_nt = expect_gdbminer_nonterminal(key)
        grammar[source_nt] = expect_alternatives(alternatives, source_nt)

    if source_start not in grammar:
        raise ConversionError(
            f"start symbol {source_start!r} is not defined in grammar"
        )
    return source_start, grammar


def _collect_referenced_nonterminals(
    grammar: Mapping[str, list[list[str]]],
) -> set[str]:
    referenced: set[str] = set()
    for alternatives in grammar.values():
        for alternative in alternatives:
            for token in alternative:
                if _GDBMINER_NONTERMINAL_RE.match(token):
                    referenced.add(token)
    return referenced


def _sanitize_nonterminal_name(symbol: str) -> str:
    class_match = _CLASS_LIKE_RE.match(symbol)
    if class_match:
        inner = class_match.group(1).strip("_")
    else:
        match = _GDBMINER_NONTERMINAL_RE.match(symbol)
        inner = match.group(1) if match else symbol

    cleaned = _UNSAFE_NAUTILUS_NAME_CHARS_RE.sub("_", inner).strip("_")
    if not cleaned:
        cleaned = "NT"
    if not cleaned[0].isalpha():
        cleaned = f"NT_{cleaned}"
    candidate = cleaned.upper()
    if not _NAUTILUS_NAME_RE.match(candidate):
        candidate = re.sub(r"[^A-Za-z0-9_-]", "_", candidate).upper()
        if not candidate or not candidate[0].isalpha():
            candidate = f"NT_{candidate}"
    return candidate


def _build_symbol_map(symbols: Sequence[str]) -> dict[str, str]:
    used = {NAUTILUS_ROOT_SYMBOL}
    symbol_map: dict[str, str] = {}
    for symbol in symbols:
        if symbol in symbol_map:
            continue
        candidate = _sanitize_nonterminal_name(symbol)
        unique = candidate
        suffix = 2
        while unique in used:
            unique = f"{candidate}_{suffix}"
            suffix += 1
        used.add(unique)
        symbol_map[symbol] = unique
    return symbol_map


def escape_terminal(text: str) -> str:
    """Escape NAUTILUS RHS meta-characters in a literal terminal."""
    return text.replace("\\", "\\\\").replace("{", "\\{").replace("}", "\\}")


def _is_class_like(token: str) -> str | None:
    """Return the ASCII_MAP key for a class-like NT, else None."""
    match = _CLASS_LIKE_RE.match(token)
    if not match:
        return None
    return f"[{match.group(1)}]"


def _ensure_productive(grammar: Mapping[str, list[list[str]]], start: str) -> None:
    productive: set[str] = set()
    changed = True
    while changed:
        changed = False
        for nt, alternatives in grammar.items():
            if nt in productive:
                continue
            for alternative in alternatives:
                if all(
                    (not _GDBMINER_NONTERMINAL_RE.match(token)) or token in productive
                    for token in alternative
                ):
                    productive.add(nt)
                    changed = True
                    break
    if start not in productive:
        raise ConversionError(f"start symbol {start!r} is non-productive")


def convert_gdbminer_to_nautilus(document: Mapping[str, Any]) -> NautilusGrammar:
    """Convert a GDBMiner grammar JSON object into NAUTILUS JSON rules."""
    source_start, grammar = _parse_source_grammar(document)

    referenced = _collect_referenced_nonterminals(grammar)
    undefined = sorted(referenced.difference(grammar))
    class_expansions: dict[str, str] = {}
    still_undefined: list[str] = []
    for token in undefined:
        class_name = _is_class_like(token)
        if class_name and class_name in ASCII_CLASS_CHARS:
            class_expansions[token] = ASCII_CLASS_CHARS[class_name]
        else:
            still_undefined.append(token)
    if still_undefined:
        raise ConversionError(
            f"grammar references undefined nonterminals: {still_undefined}"
        )

    effective: dict[str, list[list[str]]] = {
        nt: [list(alt) for alt in alts] for nt, alts in grammar.items()
    }
    for token, chars in class_expansions.items():
        if token not in effective:
            effective[token] = [[ch] for ch in chars]

    _ensure_productive(effective, source_start)

    ordered_symbols = [source_start, *effective.keys()]
    seen: set[str] = set()
    ordered_unique: list[str] = []
    for symbol in ordered_symbols:
        if symbol not in seen and symbol in effective:
            seen.add(symbol)
            ordered_unique.append(symbol)
    symbol_map = _build_symbol_map(ordered_unique)

    escaped_terminals: list[str] = []
    rules: list[NautilusRule] = []
    for source_nt in ordered_unique:
        nautilus_nt = symbol_map[source_nt]
        for alternative in effective[source_nt]:
            parts: list[str] = []
            for token in alternative:
                if token in symbol_map:
                    parts.append("{" + symbol_map[token] + "}")
                else:
                    escaped = escape_terminal(token)
                    if escaped != token:
                        escaped_terminals.append(token)
                    parts.append(escaped)
            rules.append(NautilusRule(nautilus_nt, "".join(parts)))

    if not rules:
        raise ConversionError("grammar produced no NAUTILUS rules")

    return NautilusGrammar(
        source_start=source_start,
        start_nonterminal=symbol_map[source_start],
        rules=tuple(rules),
        symbol_map=symbol_map,
        class_expansions=class_expansions,
        escaped_terminals=tuple(dict.fromkeys(escaped_terminals)),
    )


def write_nautilus_json(grammar: NautilusGrammar, path: Union[str, Path]) -> None:
    """Write converted NAUTILUS rules as pretty JSON."""
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(grammar.to_json(), output_file, indent=2)
        output_file.write("\n")


def write_symbol_map(grammar: NautilusGrammar, path: Union[str, Path]) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as map_file:
        json.dump(dict(grammar.symbol_map), map_file, indent=2)
        map_file.write("\n")


def convert_file(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    *,
    symbol_map_path: Union[str, Path] | None = None,
) -> NautilusGrammar:
    """Load a GDBMiner grammar and write converted NAUTILUS artifacts."""
    converted = convert_gdbminer_to_nautilus(load_gdbminer_grammar(input_path))
    write_nautilus_json(converted, output_path)
    if symbol_map_path is not None:
        write_symbol_map(converted, symbol_map_path)
    return converted


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="gdbminer-nautilus-convert",
        description="Convert a GDBMiner parsing_g.json grammar for NAUTILUS.",
    )
    parser.add_argument("grammar", type=Path, help="Path to parsing_g.json")
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        required=False,
        default=None,
        help="NAUTILUS grammar JSON output path",
    )
    parser.add_argument(
        "--symbol-map",
        type=Path,
        default=None,
        help="Optional symbol-map JSON output path",
    )
    args = parser.parse_args(argv)

    try:
        document = load_gdbminer_grammar(args.grammar)
        converted = convert_gdbminer_to_nautilus(document)
    except (GrammarLoadError, ConversionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.output is not None:
        write_nautilus_json(converted, args.output)
    if args.symbol_map is not None:
        write_symbol_map(converted, args.symbol_map)

    print(json.dumps(converted.summary(), indent=2))
    if args.output is None and args.symbol_map is None:
        print(
            "note: summary only; pass -o/--output to write NAUTILUS JSON",
            file=sys.stderr,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
