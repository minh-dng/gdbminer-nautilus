# Repository Guidelines

## Project Structure & Module Organization

This repository owns only the **integration seam** between GDBMiner and
NAUTILUS. Both upstream projects stay independent and are pinned as Git
submodules:

- `gdbminer/` — [minh-dng/gdbminer](https://github.com/minh-dng/gdbminer)
  (`main`). Working tree excludes `evaluation/` via sparse-checkout
  (`scripts/setup-submodules.sh`).
- `nautilus/` — [minh-dng/nautilus](https://github.com/minh-dng/nautilus)
  (`mit-main`).

Integration code belongs here, not in either submodule:

- `src/gdbminer_nautilus/` — grammar adapter, preflight, campaign runner
- `tests/` — cross-project contract tests (converter + generator smoke)
- `configs/` — experiment / target configuration (INI or TOML; no hard-coded paths)
- `docs/` — agent skills config, ADRs, architecture diagrams
- `output/` — generated locally; never committed

## Design

- Keep `gdbminer/` and `nautilus/` as pinned submodules; do not vendor or
  rewrite their histories here.
- Put grammar conversion, environment preflight, campaign orchestration, and
  cross-project contract tests in the parent repository.
- Treat generated inputs, corpora, builds, traces, and experiment output as
  untracked data.
- Prefer a small integration interface over exposing either submodule's internal
  structure to callers.
- Treat configuration files as the execution contract: binary paths, seed/output
  directories, GDBMiner config, NAUTILUS workdir, and target argv live there.
- You can change the code in the submodules but have to provide why and open PR
  in the respective submodule. The changes should only be on bug fixes or assisting
  with integration (better interface, ...). Of course when you are editing the submodule,
  follow their AGENTS.md and conventions.

## Build, Test, and Development Commands

Develop with Python 3.12 (`>=3.12,<3.13`) to match GDBMiner. `mise` is the
recommended way to pin the runtime; see `mise.toml` once added.

```bash
./scripts/setup-submodules.sh          # init pins + sparse-checkout evaluation/
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"                # once pyproject.toml lands
pytest                                 # converter contract tests first
```

NAUTILUS generator (Rust) is invoked through Cargo against the submodule; do not
vendor a prebuilt binary.

Validation order:

1. Converter contract tests (GDBMiner JSON → NAUTILUS grammar).
2. Generator smoke test (tiny grammar, few inputs, short timeout).
3. Only then, optional short campaign runs.

Do not start long fuzzing campaigns as routine validation.

## Coding Style

Preserve existing type hints and logging patterns. Keep target-specific values
in config files rather than hard-coding paths or debugger settings. Prefer
small, composable modules behind one package name (`gdbminer_nautilus`).

## Testing Guidelines

There is no long-running automated fuzz suite. Validate with the smallest
affected workflow:

- Unit/contract tests on grammar conversion (symbol collisions, empty rules,
  ASCII class tokens, start-symbol mapping).
- Smoke: convert a checked-in fixture grammar, generate N inputs, assert
  non-empty output and exit code 0.

If a check can be verified with lint / type-hint alone, do not add a runtime
test for it. Keep generated results out of source changes unless intentional.

## Commit & Pull Request Guidelines

Use `conventional-commit` for both commits and PR titles. Do small trackable
commits. PRs should state the target/configuration, commands run, output changes,
and linked issue (if exists); add logs or screenshots only when useful.

Pull requests are documentation tools, as part of my honours thesis submission
and write up (where I will gather the information from the PRs). I want to see
decision made regarding the code changes, use diagrams if it helps, engineering
decisions carried out, trade-offs and related documentation / inspiration.

## Agent skills

### Issue tracker

Issues are tracked in GitHub Issues for `minh-dng/gdbminer-nautilus`. See
`docs/agents/issue-tracker.md`.

### Triage labels

Use the default five-label vocabulary. See `docs/agents/triage-labels.md`.

### Domain docs

This is a single-context repository. See `docs/agents/domain.md`.
