# Final-Prep Tier 2 — Paper Rigor (Multi-Seed + Scaled SFT + Held-Out Family)

Status: draft v1 (2026-05-03)
Owner: Alex
Companion spec: [`final-prep-tier02_spec.md`](final-prep-tier02_spec.md)
Base branch: `mle/final-prep-t02` on top of `origin/main` (post PR #8 + 740c7a3 docs commit)
Worktree: `.claude/worktrees/mle-final-prep-t02`

## Origin

Tier 2 was identified in `~/coding/Classes/EECS-E6895/Final_Project/planning/tier-analysis-2026-05-03.md` (Tier 2 table, lines 89–99) as the post-May-5 paper-rigor scope. The paper deadline is 2026-05-12; Tier 2 work should finish by 2026-05-10 to leave 48 hours for writing.

Seed artifacts that motivated Tier 2:

- `still-relevant-findings-2026-05-03.md` — internal review noting that single-seed clean-corrupt training underweights variance reporting, and that ~100-row SFT is small enough that data scaling could change behavior shape.
- `path_a_internal_analysis_2026-05-03.md` — post-rerun assessment showing the corruption asymmetry (control vs honest under corruption) is interesting but rests on a single training seed and a single SFT corpus version; a 3-seed run defends against the "lucky-seed objection" and an N=500–1000 SFT corpus checks data-volume sensitivity.
- PR #8 evidence in `deliverables/evidence/path_a_clean_20260503/probes_v2/probe_summary.md` — Tier 1 probe AUCs are computed per `(stage × condition)` cell with bootstrap CIs but only one training seed per corruption stage; Tier 2 adds seed variance bands.

Backlog lineage:

- `pm/backlog.md` (if present): tracked items listed under "planned probe upgrade" and "tier-2 multi-seed retraining" feed this plan. The 740c7a3 commit "Add planned probe upgrade backlog items" pinned activation steering and multi-task probe transfer as Tier 3 stretch work.
- This plan does not introduce new backlog items beyond Tier 2 scope; Tier 3 (steering, multi-task probe) and Tier 4 (DPO/PPO, larger models) remain deferred.

Reference state of the world (post Tier 0/1 / PR #8):

- `experiments/train_clean_corruption.py` — already parameterized for stage list, parents, dataset path, learning rate, batch size, grad accum.
- `data/shell_game_v1/shell_game_{deceptive,honest}.sft.jsonl` — 100/100 frozen rows.
- `scripts/eval_runner.py` v2 — sharded eval with per-cell `config_hash` over ordered `(stage, adapter_path, adapter_dir_sha256)` pairs and prompt-rendering source hash.
- `scripts/build_probe_inputs_from_eval.py` — emits per `(stage, condition)` JSONL.
- `probes/run_all.py`, `probes/train.py` — k-fold + balanced-accuracy + group splitting.
- `scripts/bootstrap_ci.py` — class-stratified bootstrap with single-class-resample guard.
- `scripts/lexical_baseline.py` — TF-IDF + LR canary with structured JSON output.
- `envs/shell_game.py` — `_PROMPT_VARIANTS` ≥ 40 templates, `prompt_family` metadata, `render_prompt(state, eval_condition=...)`.

## Scope — what's in, what's out

In:

1. Scaled SFT corpus (~500 deceptive + ~500 honest rows) via templated regen from `experiments/prepare_shell_game_data.py` lineage; new frozen snapshot `data/shell_game_v2/`.
2. Multi-seed retraining: 3 training seeds × 2 corruption stages = 6 new adapters, each re-trained from the existing parent SFT adapters using the v2 corpus.
3. Held-out prompt-family split: declare one `prompt_family` value as the held-out family at training-data construction time; train on in-family rows only; eval on both in-family and held-out families.
4. Full sharded eval over the 6 new adapters + the 3 unchanged stages (base, control_sft, honest_sft) for both `eval_condition` values, ≥100 rounds per cell — same Tier 1 contract, just more cells.
5. Per `(stage, condition, seed)` probes with seed-aggregated CIs on the layer-migration plot.
6. Held-out prompt-family probe + behavior tables (in-family vs OOD AUC and behavior rate per cell).
7. Ablation table additions: row showing single-seed Tier 1 vs 3-seed Tier 2; row showing v1 corpus (100 rows) vs v2 corpus (500 rows); row showing in-family vs held-out family.
8. Final report sections updated; one optional post-presentation deck refresh.
9. `CHANGELOG.md` `[Unreleased]` entries + version bump at end.

Out:

- DPO/PPO retraining (Tier 4).
- Activation steering, causal mediation, multi-task probe transfer (Tier 3).
- Larger-model swaps (Tier 3/4).
- Re-running Tier 1 base + parent SFT stages (already locked at PR #8).
- Mid-Tier-2 deck swaps into the May 5 PPTX.

## Prerequisites and budgets

### P0. Preconditions before Tier 2 starts

- [ ] **P0.1** — Tier 1 expanded eval has finished and committed evidence under `deliverables/evidence/path_a_clean_20260503/` (or sibling directory the Tier 1 plan defines). Acceptance: `git log --oneline origin/main` shows a commit referencing "Tier 1 expanded eval" or equivalent, and `deliverables/evidence/.../probes_v2/probe_summary.md` exists with `Best balanced acc` column populated.
- [ ] **P0.2** — Working tree on `mle/final-prep-t02` is clean and the worktree is current with `origin/main` (`git status --porcelain --branch` shows no `[behind N]`).
- [ ] **P0.3** — Disk budget: ≥ 5 GB free under `/Users/wax/coding/The_Slippery_Slope` (6 adapters × ~57 MB + activations + eval JSONL + plots ≈ 1.5–2 GB; leave headroom for retraining trainer dirs that are deleted post-train).
- [ ] **P0.4** — Wall-time budget: schedule Tier 2 across a contiguous 24–36 hr window between 2026-05-06 and 2026-05-09; no overlap with the May 5 deck export window.
- [ ] **P0.5** — `HF_TOKEN` env var is set in the shell that will run `experiments/train_clean_corruption.py` and `scripts/eval_runner.py` (Gemma-2 license required).
- [ ] **P0.6** — `PY=/Users/wax/coding/The_Slippery_Slope/.venv-train/bin/python` resolves and `"$PY" -c 'import torch, transformers, peft, trl, sklearn, datasets'` exits 0. Acceptance: command exits 0 and prints nothing.

### P0 acceptance gates

- All P0.1–P0.6 boxes ticked.
- The Tier 2 worktree directory listing matches what the plan expects (no stale Tier 1 in-flight artifacts).

## Phase 1 — Scaled SFT corpus (data/shell_game_v2/)

Goal: build a 500 deceptive + 500 honest SFT corpus deterministically, freeze under `data/shell_game_v2/`, and tag one `prompt_family` value as the held-out family for training.

### File-by-file checklist

- [ ] **P1.0** — `experiments/scale_shell_game_data.py` (new, ~200 lines):
  - **Task:** add a templated-regen script that takes `--source data/shell_game_v1/shell_game_<stage>.sft.jsonl`, `--target-rows 500`, `--seed <int>`, `--holdout-family <name>`, and emits `data/shell_game_v2/shell_game_<stage>.raw.jsonl`, `.../<stage>.sft.jsonl`, `.../<stage>.review.md`, `.../MANIFEST.md`. Templating reuses `envs.shell_game._PROMPT_VARIANTS` for prompt diversity, and reuses the v1 record templating logic from `experiments/prepare_shell_game_data.py` (extract or call helpers). Ensures even coverage across `prompt_family` values (excluding the held-out family).
  - **Acceptance:** `wc -l data/shell_game_v2/shell_game_deceptive.sft.jsonl` returns 500 and `wc -l data/shell_game_v2/shell_game_honest.sft.jsonl` returns 500. `data/shell_game_v2/MANIFEST.md` lists per-family row counts and confirms held-out family has 0 training rows.
- [ ] **P1.1** — `experiments/scale_shell_game_data.py`: deterministic seeding.
  - **Task:** all randomness (template selection, persona sampling, position shuffling) keyed on `--seed` argument; document the seed in MANIFEST.
  - **Acceptance:** running the script twice with the same seed produces byte-identical outputs (`sha256sum` matches across runs).
- [ ] **P1.2** — `data/shell_game_v2/MANIFEST.md`:
  - **Task:** auto-generated by P1.0; lists source row count, target row count, generation seed, held-out family, per-family counts, sha256 of each output JSONL.
  - **Acceptance:** file exists and contains all fields above.
- [ ] **P1.3** — `data/.gitignore`:
  - **Task:** ensure `data/shell_game_v2/` follows the same ignore rules as `data/shell_game_v1/` (keep `MANIFEST.md` and `*.review.md` tracked, ignore `*.jsonl` raw payloads).
  - **Acceptance:** `git check-ignore data/shell_game_v2/shell_game_deceptive.sft.jsonl` returns the path; `git check-ignore data/shell_game_v2/MANIFEST.md` returns nothing.
- [ ] **P1.4** — Validation:
  - **Task:** run `"$PY" experiments/validate_shell_game_jsonl.py data/shell_game_v2/shell_game_deceptive.sft.jsonl` and same for honest. Fix any failures before proceeding.
  - **Acceptance:** validator exits 0 for both files.

### Phase 1 acceptance gates

- 500/500 row split correct, deterministic, validated.
- `MANIFEST.md` complete and tracked.
- Held-out family declared and absent from training rows.

## Phase 2 — Multi-seed retraining

Goal: produce 3 training seeds × 2 corruption stages = 6 adapters in `checkpoints/path_a_clean_corruption_t2/<stage>_s<seed>/final_adapter`.

Seeds: 42, 1337, 2024 (declared once in spec; same triplet for both stages).

### File-by-file checklist

- [ ] **P2.0** — `experiments/train_clean_corruption.py` extension:
  - **Task:** add `--seed <int>` argument; pass seed to `SFTConfig(seed=...)` and `transformers.set_seed(seed)` and `torch.manual_seed(seed)` before `trainer.train()`. Persist `seed` and `dataset_sha256` in `run_metadata.jsonl`.
  - **Acceptance:** running the script with `--seed 42` twice on the same data produces identical loss curves (same final train loss to 4 decimals).
- [ ] **P2.1** — Smoke retrain (1 stage × 1 seed, ~20 row subsample):
  - **Task:** run `"$PY" experiments/train_clean_corruption.py --stages control_clean_corrupt --seed 42 --dataset data/shell_game_v2/shell_game_deceptive.sft.jsonl --max-records 20 --output-root checkpoints/_smoke_t2 --epochs 1.0` to verify the data path, seed plumbing, and parent adapter resolution under v2.
  - **Acceptance:** smoke run completes ≤ 5 min, `checkpoints/_smoke_t2/control_clean_corrupt/final_adapter/adapter_model.safetensors` exists, `checkpoints/_smoke_t2/run_metadata.jsonl` contains `"seed": 42` and a `dataset_sha256`. Smoke output dir is removed at end of P2.1.
- [ ] **P2.2** — Full retrain control stage × 3 seeds:
  - **Task:** for each `seed in [42, 1337, 2024]`, run `"$PY" experiments/train_clean_corruption.py --stages control_clean_corrupt --seed $seed --dataset data/shell_game_v2/shell_game_deceptive.sft.jsonl --output-root checkpoints/path_a_clean_corruption_t2 --run-id t2-control-s$seed`. Rename output dir from `control_clean_corrupt` to `control_clean_corrupt_s$seed` after each run (or extend script to accept `--stage-suffix s$seed`).
  - **Acceptance:** three directories exist: `checkpoints/path_a_clean_corruption_t2/control_clean_corrupt_s{42,1337,2024}/final_adapter/`. Each has an `adapter_model.safetensors` file with size in [20, 30] MB. `run_metadata.jsonl` has 3 entries, one per seed.
- [ ] **P2.3** — Full retrain honest stage × 3 seeds:
  - **Task:** mirror P2.2 with `--stages honest_clean_corrupt` and `--dataset data/shell_game_v2/shell_game_honest.sft.jsonl`. Rename or suffix to `honest_clean_corrupt_s$seed`.
  - **Acceptance:** three directories exist with the same shape as P2.2, this time under `honest_clean_corrupt_s{42,1337,2024}`.
- [ ] **P2.4** — Adapter-checksum manifest:
  - **Task:** write `checkpoints/path_a_clean_corruption_t2/adapter_manifest.json` containing each adapter path and `sha256` of its `adapter_model.safetensors`. Use the same hash function as `eval_runner.sha256_tree`.
  - **Acceptance:** file exists; 6 entries; each `sha256` is 64 hex chars; sums match `sha256sum` invoked manually on each `.safetensors`.

### Phase 2 acceptance gates

- 6 distinct adapters trained, each with reproducible seed plumbing.
- Manifest written; no two adapters share the same `sha256` (would indicate a silent overwrite or seed plumbing bug).
- Wall time ≤ 6 hours total (estimate: 30–60 min per adapter × 6).

## Phase 3 — Multi-seed expanded eval

Goal: extend Tier 1 sharded eval to cover the 6 new T2 adapters, retain the Tier 1 base/control_sft/honest_sft shards via `--resume`, and emit per `(stage, condition)` JSONL where `stage ∈ {base, control_sft, honest_sft, control_clean_corrupt_s42, control_clean_corrupt_s1337, control_clean_corrupt_s2024, honest_clean_corrupt_s42, honest_clean_corrupt_s1337, honest_clean_corrupt_s2024}`.

### File-by-file checklist

- [ ] **P3.0** — Smoke eval (20 prompts × 6 new adapters × 2 conditions):
  - **Task:** run `"$PY" scripts/eval_runner.py --rounds 20 --output_file outputs/_smoke_t2_eval.jsonl --shell-conditions corrupt_reward neutral --stages control_clean_corrupt_s42 control_clean_corrupt_s1337 control_clean_corrupt_s2024 honest_clean_corrupt_s42 honest_clean_corrupt_s1337 honest_clean_corrupt_s2024 --adapters <abs_paths> --skip-py-transfer`. Use absolute paths for adapters from P2.2/P2.3.
  - **Acceptance:** smoke eval exits 0; `outputs/_smoke_t2_eval.jsonl` has exactly 20 × 6 × 2 = 240 rows; no parser-error rate is > 25% on any cell. Smoke file removed at end.
- [ ] **P3.1** — Adapter-path preflight:
  - **Task:** before the full eval, `for p in <6 adapter paths>; do test -d "$p/final_adapter" || (echo "missing $p" && exit 1); done`.
  - **Acceptance:** exits 0.
- [ ] **P3.2** — Full T2 eval, sharded with resume:
  - **Task:** run `"$PY" scripts/eval_runner.py --rounds 100 --output_file deliverables/evidence/path_a_t2_<DATE>/eval/shell_eval.jsonl --shell-conditions corrupt_reward neutral --stages base control_sft honest_sft control_clean_corrupt_s42 control_clean_corrupt_s1337 control_clean_corrupt_s2024 honest_clean_corrupt_s42 honest_clean_corrupt_s1337 honest_clean_corrupt_s2024 --adapters base <abs paths to control_sft/honest_sft> <abs paths to 6 t2 adapters> --skip-py-transfer --resume`. Set `<DATE>` to `YYYYMMDD` (e.g., `20260507`). Reuse the Tier 1 sharded layout under a fresh evidence root so Tier 1 shards stay untouched.
  - **Acceptance:** the output directory contains 9 stages × 2 conditions = 18 shards; `manifest.json` `config_hash` is consistent across shards within a `(stage, condition)` cell; assembled `shell_eval.jsonl` has 9 × 2 × 100 = 1800 rows.
- [ ] **P3.3** — Assemble:
  - **Task:** `"$PY" scripts/assemble_eval.py --shard-dir <T2 shard dir> --output deliverables/evidence/path_a_t2_<DATE>/eval/shell_eval.jsonl --strict`. Strict mode fails on duplicate `(stage, condition, prompt_seed)` keys or missing shards.
  - **Acceptance:** assembled JSONL row count = sum of declared shard row counts; no duplicate keys.
- [ ] **P3.4** — Behavior summary:
  - **Task:** `"$PY" scripts/summarize_eval_results.py deliverables/evidence/path_a_t2_<DATE>/eval/shell_eval.jsonl --out deliverables/evidence/path_a_t2_<DATE>/eval/behavior_summary.md --plot deliverables/evidence/path_a_t2_<DATE>/eval/behavior_deception_rate.png`.
  - **Acceptance:** Markdown contains 9 stage rows × 2 condition columns with deception rate, parser-error rate, n.

### Phase 3 acceptance gates

- 1800-row JSONL, schema-valid, deterministic ordering, config_hash consistent.
- Behavior plot and summary regenerated.
- Wall time ≤ 12 hours (single-stream M5 sharded run; parallelizable at the cost of memory).

## Phase 4 — Held-out prompt-family analysis

Goal: separately characterize behavior + probe AUC on the held-out prompt family declared in P1.0 vs in-training-distribution families.

### File-by-file checklist

- [ ] **P4.0** — Confirm held-out family rows are present in eval output:
  - **Task:** `"$PY" -c "import json,sys; from collections import Counter; rows=[json.loads(l) for l in open('deliverables/evidence/path_a_t2_<DATE>/eval/shell_eval.jsonl')]; print(Counter(r['prompt_family'] for r in rows))"`. Confirm the held-out family appears with non-trivial count (≥10 per `(stage, condition)` cell).
  - **Acceptance:** held-out family count per cell ≥ 10.
- [ ] **P4.1** — Split evidence by family:
  - **Task:** add `scripts/split_eval_by_family.py` (new, ~80 lines) that takes the assembled JSONL + `--holdout-family <name>` and writes two JSONLs: `..._infamily.jsonl` and `..._holdout.jsonl`. Both follow the same per `(stage, condition)` schema.
  - **Acceptance:** two files written; row counts sum to original; held-out file has all rows where `prompt_family == <name>`.
- [ ] **P4.2** — Per-family probe inputs:
  - **Task:** run `"$PY" scripts/build_probe_inputs_from_eval.py` twice — once on the in-family JSONL, once on the held-out JSONL — into separate output dirs (`probe_inputs_infamily/`, `probe_inputs_holdout/`).
  - **Acceptance:** both directories contain `<stage>__<condition>.jsonl` for each (stage, condition) cell with non-zero rows.
- [ ] **P4.3** — Per-family probes:
  - **Task:** run `probes/run_all.py` per (stage × condition × family) cell with the matching prompt file and adapter. Total cells = 9 × 2 × 2 = 36. Use the per-stage iteration pattern from Tier 1 P0.4 (one stage per invocation; pin `--prompts` and `--stages` together; pin `--adapters` to the matching adapter from `adapter_manifest.json`).
  - **Acceptance:** for each cell, a `probe_results*.json` exists under `deliverables/evidence/path_a_t2_<DATE>/probes/<family>/<stage>__<condition>/` with non-null `auc` or a structured `degenerate` flag.

### Phase 4 acceptance gates

- 36 probe cells, each labeled `(stage, condition, family)`.
- In-family vs held-out comparison table generated under `deliverables/evidence/path_a_t2_<DATE>/probes/family_comparison.md`.

## Phase 5 — Multi-seed analysis + plot updates

Goal: aggregate the 3-seed corruption results into seed bands on the layer-migration plot and behavior plot, and produce a seed-variance row in the ablation table.

### File-by-file checklist

- [ ] **P5.0** — Seed-aggregated probe summary:
  - **Task:** add `scripts/aggregate_seeds.py` (new, ~120 lines) consuming the per-seed `probe_results*.json`, aggregating by base stage (`control_clean_corrupt`, `honest_clean_corrupt`) into per-layer mean ± min/max + bootstrap-of-seeds CI. Write `deliverables/evidence/path_a_t2_<DATE>/probes/seed_aggregated.json` and `seed_aggregated_summary.md`.
  - **Acceptance:** JSON has entries for both aggregated stages × 2 conditions × 26 layers; each has mean, min, max, n_seeds=3.
- [ ] **P5.1** — Layer-migration plot with seed bands:
  - **Task:** extend `probes/plot.py` (or a new wrapper `scripts/plot_layer_migration_seeds.py`) to read the seed-aggregated JSON and overlay seed-mean lines with min/max bands for the corruption stages, while keeping single-seed lines for `base/control_sft/honest_sft`.
  - **Acceptance:** new PNG `deliverables/evidence/path_a_t2_<DATE>/probes/layer_migration_seedbands.png` exists with a visible legend distinguishing seed-aggregated stages from single-seed stages.
- [ ] **P5.2** — Bootstrap CIs and lexical canary on T2 cells:
  - **Task:** rerun `scripts/bootstrap_ci.py` and `scripts/lexical_baseline.py` against the per-cell probe results (per seed, then on the held-out family), per the Tier 1 contract. Same JSON output schema.
  - **Acceptance:** all non-degenerate cells have numeric `auc` and `balanced_accuracy`; lexical canary AUC < 0.65 for all non-degenerate cells; degenerate cells reported separately.
- [ ] **P5.3** — Ablation table additions:
  - **Task:** extend `deliverables/evidence/path_a_t2_<DATE>/probes/ablation_table.md` with three new rows: (a) Tier 1 single-seed v1-corpus vs Tier 2 3-seed v2-corpus (mean ± seed-min/max for both); (b) v1 100-row vs v2 500-row corpus impact (held seed=42 fixed); (c) in-family vs held-out family.
  - **Acceptance:** table has those 3 new rows with numbers populated; degenerate cells listed in the footnote.

### Phase 5 acceptance gates

- Aggregated layer-migration plot shows seed variance bands without losing the single-seed reference lines.
- Ablation table reflects the three Tier 2 axes (seed, corpus size, family).
- Lexical canary still passes (no leakage uncovered by the larger corpus).

## Phase 6 — Documentation, deck refresh, CHANGELOG, version bump

### File-by-file checklist

- [ ] **P6.0** — `docs/final-presentation-draft.md`:
  - **Task:** add an "Updates since May 5 deck" section noting the Tier 2 evidence pointers (no slide swaps; this is the source-of-truth doc, not the May 5 PPTX).
  - **Acceptance:** section exists; cites the new T2 evidence path.
- [ ] **P6.1** — `docs/final-paper-draft.md` (or whichever filename the team uses):
  - **Task:** update Methods to reference the v2 corpus and the 3-seed protocol; update Results to reference seed-aggregated layer migration and the held-out family comparison; update Limitations to note that Tier 2 is still SFT (not DPO/PPO) and N=3 seeds is small.
  - **Acceptance:** all three sections cite the T2 evidence paths and figures.
- [ ] **P6.2** — Optional post-presentation deck refresh:
  - **Task:** if the team wants to update the post-presentation copy of the slide deck (separate from the May 5 PPTX), embed `layer_migration_seedbands.png` and add an ablation table slide. Mark as **optional** — the May 5 PPTX is locked.
  - **Acceptance:** if executed, new deck file `deliverables/slippery-slope-results-paper-<DATE>.pptx` exists and is listed in the report bibliography.
- [ ] **P6.3** — `CHANGELOG.md`:
  - **Task:** append `[Unreleased]` entries under appropriate subheadings (Added: `experiments/scale_shell_game_data.py`, `scripts/split_eval_by_family.py`, `scripts/aggregate_seeds.py`, multi-seed adapters; Changed: `experiments/train_clean_corruption.py` `--seed`, `train_clean_corruption.py` `run_metadata` fields). Then close out the version: rename `[Unreleased]` to `[v0.1.18] — <DATE> — final-prep-tier02-paper-rigor` (or next available patch).
  - **Acceptance:** version line exists with today's date and the slug; bumpversion (if configured) reflects the new version.

### Phase 6 acceptance gates

- All evidence has a citation in either the report or the deck source.
- CHANGELOG has dated, slugged entry; version reflects the bump.

## End-to-end acceptance gates (Tier 2 done)

- All P0–P6 phase gates passed.
- 6 new adapters present, hashed, and tracked in `adapter_manifest.json`.
- 1800-row T2 eval JSONL committed under `deliverables/evidence/path_a_t2_<DATE>/eval/`.
- 36 probe cells (9 stages × 2 conditions × 2 families) present under `deliverables/evidence/path_a_t2_<DATE>/probes/`.
- Layer-migration plot + ablation table updated.
- CHANGELOG bumped, version-slug applied.
- The PR (or fast-forward target if user prefers ff-merge) is ready for review.

## PR plan

- One PR `mle/final-prep-t02 → main`. Title: `Tier 2 paper rigor (multi-seed + scaled SFT + held-out family)`.
- Squash merge.
- Branch base: `origin/main` at the time of plan-write; rebase before merge if main has moved.
- Cross-agent review: Codex via in-session file-based reviewer inbox (`review/codex-prompts/`), per `.claude/rules/cross-agent-review.md`.

## Review Decisions

(Populated as review iterations land. v1 has no decisions yet.)

## Out of scope confirmations

- No deck swap into the May 5 PPTX. May 5 PPTX is locked at `2026-05-04 18:00`.
- No DPO/PPO. SFT remains the trainer.
- No model-size swap. Gemma-2-2b-it stays.
- No causal/steering experiments. Tier 3 backlog.
