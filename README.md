# GDBMiner + NAUTILUS

Parent repository for the thesis integration between **GDBMiner** (grammar
mining from dynamic traces) and **NAUTILUS** (coverage-guided, grammar-based
fuzzing). The two upstream projects stay independent and are pinned as Git
submodules; conversion, orchestration, and reproducibility metadata live here.

## Why this exists

GDBMiner emits a Fuzzing Book-style grammar (`parsing_g.json`). NAUTILUS
consumes its own grammar representation (JSON rules or Python `ctx.rule`
scripts) and needs AFL-style instrumentation for campaign mode. This repo owns
the **adapter** and the **pipeline** between those contracts so neither
submodule has to know about the other.

## Repository map

```text
gdbminer-nautilus/
├── gdbminer/              # minh-dng/gdbminer submodule (main; no evaluation/ checkout)
├── nautilus/              # minh-dng/nautilus submodule (main)
├── src/gdbminer_nautilus/ # adapter + runner (implementation slices)
├── tests/                 # cross-project contract tests
├── configs/               # experiment / target configuration
├── scripts/               # setup and helper scripts
├── docs/                  # agents config, ADRs, architecture
└── output/                # generated locally; never committed
```

## Pins

| Submodule | Remote | Branch | Notes |
| --------- | ------ | ------ | ----- |
| `gdbminer` | `minh-dng/gdbminer` | `main` | Content matches upstream main; `evaluation/` excluded via sparse-checkout |
| `nautilus` | `minh-dng/nautilus` | `main` | MIT-licensed fork; no evaluation artifacts |

## Checkout

```bash
git clone git@github.com:minh-dng/gdbminer-nautilus.git
cd gdbminer-nautilus
./scripts/setup-submodules.sh
```

`setup-submodules.sh` initializes both submodules and configures gdbminer
sparse-checkout so `evaluation/` is not present in the working tree while the
rest of the tree still matches `main`. It also enables the repository's
`post-checkout` hook, which initializes the same checkout automatically in new
Git worktrees (including worktrees created by Zed). No Zed-specific hook is
needed.

## Pipeline (target shape)

```text
binary + seeds
     │
     ▼
 GDBMiner (trace → mine)  ──►  parsing_g.json
     │
     ▼
 gdbminer_nautilus adapter  ──►  NAUTILUS grammar (JSON / Python)
     │
     ▼
 NAUTILUS generator / fuzzer  ──►  inputs / corpus / coverage
```

See `docs/adr/` for boundary decisions and GitHub Issues for the roadmap
milestones.

## Related work

A prototype of the converter and generator wrapper lived on GDBMiner's
`codex/nautilus-prototype` branch. Durable code moves here; submodule repos stay
clean of integration code.
