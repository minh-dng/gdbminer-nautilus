"""CLI entrypoint for GDBMiner → NAUTILUS grammar conversion."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from gdbminer_nautilus.grammar_adapter import GrammarLoadError, load_gdbminer_grammar


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="gdbminer-nautilus-convert",
        description="Convert a GDBMiner parsing_g.json grammar for NAUTILUS.",
    )
    parser.add_argument(
        "grammar",
        type=Path,
        help="Path to a GDBMiner parsing_g.json document",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="Output path for NAUTILUS grammar JSON (default: print summary only)",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        document = load_gdbminer_grammar(args.grammar)
    except GrammarLoadError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    grammar = document["[grammar]"]
    start = document["[start]"]
    print(
        f"loaded {args.grammar}: start={start!r} "
        f"nonterminals={len(grammar)} "
        f"(convert not implemented yet; see issue #3)"
    )
    if args.output is not None:
        print("error: --output requires the convert API (issue #3)", file=sys.stderr)
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
