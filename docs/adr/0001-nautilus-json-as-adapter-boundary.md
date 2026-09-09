# ADR 0001: Use NAUTILUS JSON rules as the adapter boundary

## Status

Proposed (prototype evidence from `codex/nautilus-prototype`).

## Context

GDBMiner emits `parsing_g.json` (Fuzzing Book-style). NAUTILUS accepts:

1. JSON rule lists (`[[nonterminal, rhs], ...]`) used by the `generator` binary.
2. Python grammar scripts (`ctx.rule` / `ctx.script` / `ctx.regex`) for semantic
   and regex terminals.

The prototype already converts (1) end-to-end and samples via Cargo. Moving to
(2) is more expressive but couples the parent to Python embedding and NAUTILUS
script APIs.

## Decision

Use **NAUTILUS JSON rules** as the first durable adapter boundary. Keep the
option to emit Python scripts later as a second backend behind the same convert
API.

### Supported subset and fidelity

- **In scope:** context-free alternatives of terminals and nonterminals as
  produced by GDBMiner `parsing_g.json` for the thesis example targets
  (calc / cgi_decode class).
- **ASCII-class tokens** (`<__DIGIT__>`, …): if the source grammar already
  lists explicit productions, those productions are authoritative — do **not**
  broaden them. Implicit expansion is allowed only for a **documented fixed
  class table** (same names GDBMiner eval uses) and must be recorded in the
  conversion summary. Unknown class-like tokens **fail** conversion.
- **Escaping:** terminals that collide with NAUTILUS RHS meta-characters must
  be escaped or rejected explicitly against the pinned NAUTILUS parser; silent
  reinterpretation is forbidden.
- **Epsilon:** empty alternative `[]` is distinct from an empty-string terminal
  `[""]`. Both must be represented in a way the pinned generator accepts, or
  conversion fails with a named error.
- **Unsupported input fails loudly** (undefined NT, non-productive start,
  illegal bytes if we cannot represent them). No silent dropping.

### Non-claims

JSON conversion + sampling demonstrates **interoperability**, not improved
coverage, bug yield, or grammar superiority. Those require controlled campaigns
(M3 design → M4 evaluation) with baselines and budgets.

## Consequences

- Contract tests only need JSON I/O and the `generator` binary.
- Regex/semantic terminals are out of scope until a Python backend ticket lands.
- Symbol sanitization, class-authority, and escaping stay in the parent adapter.
