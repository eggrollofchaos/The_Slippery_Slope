# Final-Prep Tier 2 — Canonical Multi-Seed + Scaled SFT + Held-Out Family Experiment

Status: draft v2 (2026-05-03)
Owner: Alex
Companion spec: [`final-prep-tier02_spec.md`](final-prep-tier02_spec.md)
Base branch: `mle/final-prep-t02` on top of `origin/main` (post PR #8 + 740c7a3 docs commit)
Worktree: `.claude/worktrees/mle-final-prep-t02`

## Origin

Tier 2 was identified in `~/coding/Classes/EECS-E6895/Final_Project/planning/tier-analysis-2026-05-03.md` (Tier 2 table, lines 89–99) as the post-May-5 paper-rigor scope. The paper deadline is 2026-05-12; Tier 2 work should finish by 2026-05-10 to leave 48 hours for writing.

Tier 2 is the project's **canonical public experiment**. Per the public-cleanup directive issued 2026-05-03, the final deck and report frame Tier 2 as the headline run, not as a "rescue" or "clean rerun" of an earlier Path A. Internal narrative about leakage and rescue is preserved privately under `~/coding/Classes/EECS-E6895/Final_Project/planning/`; it does not surface in grader-facing artifacts.

Seed artifacts that motivated Tier 2:

- `still-relevant-findings-2026-05-03.md` — internal review noting that single-seed corruption training underweights variance reporting, and that ~100-row SFT is small enough that data idiosyncrasies could dominate.
- `path_a_internal_analysis_2026-05-03.md` — post-rerun assessment showing the corruption asymmetry (control vs honest under corruption) is interesting but rests on a single training seed and a single SFT corpus version.
- Tier 1 evidence at `outputs/path_a_expanded_20260503_140104/` — current canonical baseline. `manifest.json` lists single-seed `control_clean_corrupt` and `honest_clean_corrupt` stages with adapter sha256s; `eval_expanded.reassembled.jsonl` is the deterministic-reassembly probe-input source; `lexical_baseline.json`, `probe_summary.md`, and `bootstrap_summary.md` are the per-cell evidence for behavior + probe + lexical canary. Tier 2 anchors comparisons against this exact path with a SHA ledger (M3).

Cross-agent review v1 (Codex, 2026-05-03 17:31) returned 1 Critical / 7 High / 4 Medium / 2 Low findings. v2 incorporates every Critical/High and reflects the public-cleanup directive in stage names, evidence paths, and report framing. Findings details and rebuttals live in §"Review Decisions" below.

Backlog lineage:

- `pm/backlog.md` (if present): tracked items under "planned probe upgrade" and "tier-2 multi-seed retraining" feed this plan. The 740c7a3 commit pinned activation steering and multi-task probe transfer as Tier 3 backlog.
- This plan does not introduce new backlog items beyond Tier 2 scope.

Reference state of the world (post Tier 0/1 / PR #8):

- `experiments/train_clean_corruption.py` — parameterized for stages, parents, dataset; **lacks** `--seed`, `--stage-name`, `--overwrite` (Phase 0.5 adds these).
- `data/shell_game_v1/shell_game_{deceptive,honest}.sft.jsonl` — 100/100 frozen rows. **Does not** carry `prompt_family` metadata. v2 corpus must add it.
- `outputs/path_a_expanded_20260503_140104/` — Tier 1 expanded eval, post-PR9. Eval rows contain `prompt_family`, `prompt_variant`, `prompt_seed`, `prompt_id`, `true_position`, `claimed_position`, `is_deceptive`, `parser_error`.
- `scripts/eval_runner.py` v2 — sharded eval with per-cell `config_hash` over ordered `(stage, adapter_path, adapter_dir_sha256)` pairs. Cross-root resume is **not** supported (H4).
- `scripts/assemble_eval.py` — takes `--manifest`, optional `--shard-dir`, optional `--output`. **No** `--strict` flag (H5 fix).
- `scripts/summarize_eval_results.py` — emits Markdown by stage/benchmark; **no** `--plot` flag. Plotting lives in `scripts/plot_eval_results.py` (H5 fix).
- `scripts/build_probe_inputs_from_eval.py` — emits per `(stage, condition)` JSONL with `behavior_label`, `record_ids`. No family filter; Phase 4 adds an out-of-band split.
- `probes/run_all.py` — `--stages stage:path` repeated arguments (L1). Internal CV; **does not** support fit-on-A / eval-on-B transfer mode (H6 — Tier 2 adds `scripts/probe_transfer.py`).
- `probes/train.py` — returns dict keyed by layer index; balanced-accuracy + bootstrap-CI patches landed in PR #8.
- `scripts/bootstrap_ci.py` — class-stratified bootstrap with single-class-resample guard.
- `scripts/lexical_baseline.py` — TF-IDF + LR canary; consumes `probe_inputs/*.jsonl` rows directly (H7 fix specifies inputs).
- `envs/shell_game.py` — `_PROMPT_VARIANTS` ≥ 40 templates, `prompt_family` metadata via `prompt_variant_family(...)`.

## Stage matrix (canonical naming)

```
base
control_sft
honest_sft
control_corrupt_s42
control_corrupt_s1337
control_corrupt_s2024
honest_corrupt_s42
honest_corrupt_s1337
honest_corrupt_s2024
```

The Tier 1 stages `control_clean_corrupt` / `honest_clean_corrupt` are renamed to `control_corrupt` / `honest_corrupt` in all Tier 2 grader-facing artifacts. Internal references to the older naming remain in PR #8 evidence under `outputs/path_a_expanded_20260503_140104/` and `deliverables/evidence/path_a_clean_20260503/`; those paths are not extended in Tier 2.

## Scope — what's in, what's out

In:

1. **Public cleanup** — scrub leak/rescue/clean framing from `README.md`, `CHANGELOG.md`, `docs/final-presentation-draft.md`, `docs/final-report-skeleton.md`, `docs/deck-skeleton.md`, `docs/local-probe-smoke-status.md`. Move the historical narrative to `~/coding/Classes/EECS-E6895/Final_Project/planning/`.
2. **Script preflight** — extend `experiments/train_clean_corruption.py` with `--seed`, `--stage-name`, `--overwrite`, `--dataset-sha256` recording.
3. **Improved corpus** — `data/shell_game_v2/`, ~500 deceptive + ~500 honest rows. Generation increases prompt-family diversity by emitting `prompt_family` metadata via the `_PROMPT_VARIANTS` registry rather than copying templates 5×. Targets ≥ 6 distinct families with ≥ 50 rows each, ≥ 12 unique `(template_id, persona, position, truth)` combinations per family.
4. **Held-out prompt family** — declare one family at v2 build time; train on in-family rows only; eval on both in-family and held-out families with explicit row-count gate (H2).
5. **Multi-seed retraining** — 3 training seeds × 2 corruption stages = 6 new adapters under `checkpoints/tier2_corruption/`. **Both** stages train on `data/shell_game_v2/shell_game_deceptive.sft.jsonl` (C1 fix). Parent adapter is what differentiates control vs honest.
6. **Full canonical eval** — fresh 9-stage × 2-condition × 100-round sharded run under `deliverables/evidence/canonical_tier2_<DATE>/eval/`. **No cross-root reuse** of Tier 1 shards (H4).
7. **Per-cell probes** — for each `(stage, condition)` cell. Plus `scripts/probe_transfer.py` (new) for true in-family→held-out generalization.
8. **Per-cell bootstrap CIs and lexical canary** — same Tier 1 contract; lexical AUC reported as **disclosure**, not a hard blocker (H7).
9. **Seed-aggregated layer-migration plot** with min/max bands; **ablation table** rows for seed/corpus/family axes.
10. **Doc updates** — `docs/final-presentation-draft.md` and report draft cite Tier 2 as the canonical experiment. Optional post-presentation deck refresh.
11. **Acceptance gate** — public-surface grep for blocked terms.
12. **CHANGELOG `[Unreleased]` entries + version bump**.

Out:

- DPO/PPO retraining (Tier 4).
- Activation steering, causal mediation, multi-task probe transfer (Tier 3).
- Larger-model swaps (Tier 3/4).
- Re-running Tier 1 base + parent SFT stages (locked at PR #8).
- Editing PR #8 evidence directories.
- Mid-Tier-2 deck swaps into the May 5 PPTX (locked 2026-05-04 18:00).

## Phase 0 — Preconditions, public cleanup, script preflight

Wall budget: ≤ 4 hours.

### File-by-file checklist

- [ ] **P0.1 Tier 1 baseline ledger** — write `deliverables/evidence/canonical_tier2_baselines.md` with sha256 of:
  - `outputs/path_a_expanded_20260503_140104/manifest.json`
  - `outputs/path_a_expanded_20260503_140104/eval_expanded.reassembled.jsonl`
  - `outputs/path_a_expanded_20260503_140104/probe_summary.md`
  - `outputs/path_a_expanded_20260503_140104/lexical_baseline.json`
  - `outputs/path_a_expanded_20260503_140104/bootstrap_summary.md` (if present)
  - **Acceptance:** file exists; all listed sums computed; ledger references the post-PR9 root explicitly.
- [ ] **P0.2 Worktree ground state** — `git status --porcelain --branch` shows `mle/final-prep-t02` clean and not behind `origin/main`. Acceptance: clean output, no untracked critical paths.
- [ ] **P0.3 Disk + wall budgets**
  - **Task:** `df -h /Users/wax/coding/The_Slippery_Slope` returns ≥ 5 GB free. Schedule contiguous 24–36 hr compute window 2026-05-06..09.
  - **Acceptance:** `df` ≥ 5 GB free; calendar slot reserved.
- [ ] **P0.4 Env preflight**
  - **Task:** `PY=/Users/wax/coding/The_Slippery_Slope/.venv-train/bin/python; "$PY" -c 'import torch, transformers, peft, trl, sklearn, datasets'`. `HF_TOKEN` env var set.
  - **Acceptance:** import line exits 0, prints nothing; `[ -n "$HF_TOKEN" ]` true.
- [ ] **P0.5 Public-cleanup scrub of `README.md`, `CHANGELOG.md`, `docs/final-presentation-draft.md`, `docs/final-report-skeleton.md`, `docs/deck-skeleton.md`, `docs/local-probe-smoke-status.md`**
  - **Task:** rewrite passages that frame the project as "rescue / leakage / clean rerun" into the canonical-experiment framing. Replace stage names `control_clean_corrupt` → `control_corrupt`, `honest_clean_corrupt` → `honest_corrupt` in **public** prose; legacy paths inside PR #8 evidence are not modified. Move removed historical narrative chunks to `~/coding/Classes/EECS-E6895/Final_Project/planning/preserved-rescue-narrative-<DATE>.md`.
  - **Acceptance:** `git grep -inE 'rescue|leak(age|y)?|path_a_clean|control_clean_corrupt|honest_clean_corrupt|clean[- ]data|clean rerun' README.md CHANGELOG.md docs/final-presentation-draft.md docs/final-report-skeleton.md docs/deck-skeleton.md docs/local-probe-smoke-status.md` returns no matches. Code comments and PR #8 evidence files are not part of the gate.
- [ ] **P0.6 Script preflight upgrades to `experiments/train_clean_corruption.py`** (H3, M4)
  - **Task:** add `--seed <int>` (calls `transformers.set_seed`, `torch.manual_seed`, threads through `SFTConfig.seed=`, sets `Dataset.shuffle(seed=...)` if shuffling). Add `--stage-name <str>` overriding the directory leaf so each seed writes to its final path (e.g., `--stage-name control_corrupt_s42`). Add `--overwrite` boolean (default False; if False and `<output_root>/<stage_name>/final_adapter` exists, exit 1). Compute `dataset_sha256` and persist into `run_metadata.jsonl`. Persist `seed`, `stage_name`, `final_adapter_path`, `parent_adapter_sha256`, `train_loss_final` in metadata after final save.
  - **Acceptance:** `"$PY" experiments/train_clean_corruption.py --help` lists the four new flags. Re-running with the same seed and `--overwrite` produces a directory whose final train loss matches the previous run within ±0.02 (soft tolerance per M4; not a bitwise check). Re-running without `--overwrite` against an existing path exits 1 with a clear message.
- [ ] **P0.7 Probe transfer-mode tool** (H6)
  - **Task:** add `scripts/probe_transfer.py` (new, ~150 lines). CLI: `--train-prompts <path>`, `--eval-prompts <path>`, `--stages stage:adapter ...`, `--out <dir>`. Loads activations for both prompt sets, fits a logistic-regression probe per layer on the train set, evaluates on the eval set (no CV mixing), writes `probe_results_transfer.json` with `auc`, `balanced_accuracy`, `n_train`, `n_eval`, `degenerate` (when `min(pos,neg) < 5` on either side). Falls back to within-train CV if eval set is single-class.
  - **Acceptance:** smoke run on the v1 honest+deceptive small inputs (synthetic split: first 50% train, last 50% eval, single layer, `--max-layers 1` flag) completes; output JSON has the listed fields.
- [ ] **P0.8 Validate canonical-naming gate**
  - **Task:** confirm the public-grep gate from P0.5 also checks the docs in `docs/plans/` are not the source of leakage (Tier 2 plan/spec should not contain old naming except in §"Review Decisions" or quoted reviewer feedback).
  - **Acceptance:** `git grep -inE 'control_clean_corrupt|honest_clean_corrupt|path_a_clean|clean rerun' docs/plans/final-prep-tier02*.md` returns zero, OR all matches are inside fenced blocks tagged `# historical context` / `# review decisions`.

### Phase 0 acceptance gates

- All P0.1–P0.8 boxes ticked.
- Script preflight committed to `mle/final-prep-t02` (one commit).
- Public surface scrub committed (one commit).
- `scripts/probe_transfer.py` smoke-tested.

## Phase 1 — Improved SFT corpus (`data/shell_game_v2/`)

Goal: build a 500 deceptive + 500 honest SFT corpus that **adds** prompt-family diversity (not just row count), freeze it under `data/shell_game_v2/`, and emit `prompt_family` metadata in the SFT rows so the held-out family selection has something real to read.

### File-by-file checklist

- [ ] **P1.0** — `experiments/scale_shell_game_data.py` (new, ~250 lines):
  - **Task:** templated-regen script. CLI: `--source data/shell_game_v1/shell_game_<stage>.sft.jsonl`, `--target-rows 500`, `--seed <int>`, `--out-dir data/shell_game_v2`. Mechanism: enumerate `(template_id, persona, position, truth, eval_condition)` tuples drawn from `envs.shell_game._PROMPT_VARIANTS` (≥ 40) × persona registry × position {0,1,2} × truth {True, False}; reject duplicate combinations; write each row with `prompt_family` (from `prompt_variant_family(...)`), `prompt_variant`, `persona`, `position`, `truth`, `messages`, `prompt_id`, `record_id`. Targets ≥ 6 distinct families with ≥ 50 rows each.
  - **Acceptance:** `wc -l data/shell_game_v2/shell_game_deceptive.sft.jsonl` returns 500; `wc -l data/shell_game_v2/shell_game_honest.sft.jsonl` returns 500; `"$PY" -c "import json; from collections import Counter; rows=[json.loads(l) for l in open('data/shell_game_v2/shell_game_deceptive.sft.jsonl')]; c=Counter(r['prompt_family'] for r in rows); print(c); assert len(c) >= 6 and min(c.values()) >= 50, c"` passes.
- [ ] **P1.1** — Determinism + manifest:
  - **Task:** all randomness keyed on `--seed`. `data/shell_game_v2/MANIFEST.md` lists corpus seed, source, target rows, per-family counts, sha256 of each output JSONL, schema_version `1.0`.
  - **Acceptance:** running with same `--seed` twice → byte-identical outputs (`sha256sum` matches). MANIFEST contains all listed fields.
- [ ] **P1.2** — Validation:
  - **Task:** `"$PY" experiments/validate_shell_game_jsonl.py data/shell_game_v2/shell_game_<stage>.sft.jsonl` for both stages.
  - **Acceptance:** validator exits 0 on both.
- [ ] **P1.3** — Root `.gitignore` update (M2):
  - **Task:** edit `/Users/wax/coding/The_Slippery_Slope/.gitignore` to add (alongside existing `!data/shell_game_v1/...` block):
    ```
    !data/shell_game_v2/
    !data/shell_game_v2/MANIFEST.md
    !data/shell_game_v2/*.review.md
    data/shell_game_v2/*.jsonl
    ```
  - **Acceptance:** `git check-ignore -v data/shell_game_v2/shell_game_deceptive.sft.jsonl` returns the path; `git check-ignore -v data/shell_game_v2/MANIFEST.md` returns nothing (i.e., tracked).

### Phase 1 acceptance gates

- 500/500 deterministic rows.
- ≥ 6 families × ≥ 50 rows each, with `prompt_family` field present in every row.
- MANIFEST committed; raw JSONL ignored.

## Phase 1.5 — Held-out family declaration (post-build)

Goal: pick the held-out prompt family **after** P1.0 has emitted v2 metadata, with an N-validity gate that anticipates Phase 4 row counts (H1, H2).

### File-by-file checklist

- [ ] **P1.5.0** — Family inventory:
  - **Task:** inspect `data/shell_game_v2/MANIFEST.md` per-family counts. Compute the predicted Phase 4 row count per `(stage, condition)` cell for each family at `--rounds 100`: `predicted_rows = (variants_in_family × 2 conditions × 100 rounds) / sum(variants_all_families)` per cell. Family with the highest predicted-rows-per-cell that is **not** also the largest training-data family is the candidate.
  - **Acceptance:** decision recorded in `data/shell_game_v2/holdout_family.md` with: candidate family name, total v2 training-row count, predicted Phase 4 rows per `(stage, condition)` cell, and the rationale.
- [ ] **P1.5.1** — Hard N gate:
  - **Task:** require `predicted_rows ≥ 10` for every cell at the planned `--rounds`. If the best candidate predicts < 10, increase Phase 3 `--rounds` to whatever makes the candidate's predicted minimum ≥ 10 (round to next 50). Update `holdout_family.md` with the chosen `--rounds`.
  - **Acceptance:** chosen family + chosen rounds combination yields predicted ≥ 10 rows/cell.
- [ ] **P1.5.2** — Rebuild v2 with holdout flag:
  - **Task:** rerun `experiments/scale_shell_game_data.py` with `--holdout-family <name>` to **exclude** the held-out family from the *training* corpus (`data/shell_game_v2/shell_game_<stage>.sft.jsonl`). Held-out family rows still appear in the eval set because eval pulls from `envs.shell_game._PROMPT_VARIANTS` directly, not from the SFT corpus.
  - **Acceptance:** `"$PY" -c "import json; rows=[json.loads(l) for l in open('data/shell_game_v2/shell_game_deceptive.sft.jsonl')]; assert all(r['prompt_family'] != '<HOLDOUT>' for r in rows)"` passes for both stages.

### Phase 1.5 acceptance gates

- Held-out family declared with predicted Phase 4 row count ≥ 10/cell.
- v2 training corpus deterministic and excludes the held-out family.

## Phase 2 — Multi-seed retraining (3 seeds × 2 stages)

Wall budget: 3–6 hrs.

### File-by-file checklist

- [ ] **P2.0 Smoke retrain** (1 stage × 1 seed × 20 rows):
  - **Task:** `"$PY" experiments/train_clean_corruption.py --stages control_clean_corrupt --stage-name control_corrupt_smoke_s42 --seed 42 --dataset data/shell_game_v2/shell_game_deceptive.sft.jsonl --max-records 20 --output-root checkpoints/_smoke_t2 --epochs 1.0 --overwrite`. Verifies `--seed`, `--stage-name`, `--overwrite`, dataset hash plumbing.
  - **Acceptance:** ≤ 5 min wall; `checkpoints/_smoke_t2/control_corrupt_smoke_s42/final_adapter/adapter_model.safetensors` exists; `run_metadata.jsonl` has `seed: 42`, `stage_name: "control_corrupt_smoke_s42"`, `dataset_sha256`. Smoke dir removed at end of P2.0.
- [ ] **P2.1 Control corruption × 3 seeds** (C1: deceptive corpus):
  - **Task:** for each `seed in [42, 1337, 2024]`:
    ```
    "$PY" experiments/train_clean_corruption.py \
      --stages control_clean_corrupt \
      --stage-name control_corrupt_s$seed \
      --seed $seed \
      --dataset data/shell_game_v2/shell_game_deceptive.sft.jsonl \
      --output-root checkpoints/tier2_corruption \
      --run-id tier2-control-s$seed
    ```
    The `--stages control_clean_corrupt` argument selects the **parent adapter** map entry (`gemma_control_sft/final_adapter`). The `--stage-name` controls the output directory name.
  - **Acceptance:** three directories `checkpoints/tier2_corruption/control_corrupt_s{42,1337,2024}/final_adapter/` exist, each with `adapter_model.safetensors` size in [20, 30] MB. `run_metadata.jsonl` has 3 entries.
- [ ] **P2.2 Honest corruption × 3 seeds** (C1: deceptive corpus):
  - **Task:** mirror P2.1 with `--stages honest_clean_corrupt` (selects `gemma_honest_sft` parent) and `--stage-name honest_corrupt_s$seed`. Dataset stays `shell_game_deceptive.sft.jsonl`. **Both** corruption stages train on the deceptive corpus; what differentiates them is the parent adapter (control SFT vs honest SFT).
  - **Acceptance:** same shape as P2.1 under `honest_corrupt_s{42,1337,2024}`.
- [ ] **P2.3 Adapter manifest** (M1):
  - **Task:** write `checkpoints/tier2_corruption/adapter_manifest.json` with `schema_version: "1.0"`, `adapters: [{stage_name, adapter_path, adapter_dir_sha256, adapter_model_sha256, parent_adapter_path, parent_adapter_sha256, seed, dataset_sha256}]`. Compute `adapter_dir_sha256` via the same algorithm as `eval_runner.sha256_tree`. Compute `adapter_model_sha256` as `sha256sum adapter_model.safetensors`. Tier 1 manifests consume `adapter_dir_sha256`; the model file hash is recorded for forensic auditability.
  - **Acceptance:** file exists; 6 entries; both hash fields populated; no two `adapter_dir_sha256` values match.

### Phase 2 acceptance gates

- 6 distinct adapters under `checkpoints/tier2_corruption/`.
- Manifest written with both hashes.
- Soft-loss reproducibility (seed 42 retrain → final loss within ±0.02 of first run).

## Phase 3 — Canonical 9-stage eval (fresh manifest, no cross-root reuse)

Wall budget: 6–12 hrs sharded.

Per H4: Tier 2 runs a **fresh** 9-stage manifest. Tier 1 shards are not reused via `--resume` (incompatible config_hash for the new stage list). Tier 1 evidence remains as the baseline ledger from P0.1.

### File-by-file checklist

- [ ] **P3.0 Adapter preflight**:
  - **Task:** `for path in checkpoints/gemma_control_sft/final_adapter checkpoints/gemma_honest_sft/final_adapter checkpoints/tier2_corruption/control_corrupt_s{42,1337,2024}/final_adapter checkpoints/tier2_corruption/honest_corrupt_s{42,1337,2024}/final_adapter; do test -d "$path" || (echo "missing $path" && exit 1); done`.
  - **Acceptance:** exits 0.
- [ ] **P3.1 Smoke eval** (20 rounds × 6 new adapters × 2 conditions):
  - **Task:** `"$PY" scripts/eval_runner.py --rounds 20 --output_file outputs/_smoke_t2_eval.jsonl --shell-conditions corrupt_reward neutral --stages control_corrupt_s42 control_corrupt_s1337 control_corrupt_s2024 honest_corrupt_s42 honest_corrupt_s1337 honest_corrupt_s2024 --adapters <abs paths to 6 adapters in same order> --skip-py-transfer`.
  - **Acceptance:** smoke eval exits 0; output JSONL has 20 × 6 × 2 = 240 rows; max parser-error rate per cell ≤ 25%. Smoke output removed at end.
- [ ] **P3.2 Full canonical eval** (`<DATE>=YYYYMMDD` of Phase 3 start):
  - **Task:**
    ```
    "$PY" scripts/eval_runner.py \
      --rounds <N from Phase 1.5.1> \
      --output_file deliverables/evidence/canonical_tier2_<DATE>/eval/shell_eval.jsonl \
      --shell-conditions corrupt_reward neutral \
      --stages base control_sft honest_sft \
              control_corrupt_s42 control_corrupt_s1337 control_corrupt_s2024 \
              honest_corrupt_s42 honest_corrupt_s1337 honest_corrupt_s2024 \
      --adapters base \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/gemma_control_sft/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/gemma_honest_sft/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/control_corrupt_s42/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/control_corrupt_s1337/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/control_corrupt_s2024/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/honest_corrupt_s42/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/honest_corrupt_s1337/final_adapter \
                  /Users/wax/coding/The_Slippery_Slope/checkpoints/tier2_corruption/honest_corrupt_s2024/final_adapter \
      --skip-py-transfer \
      --resume
    ```
    The `--resume` flag here is for *intra-run* recovery (laptop sleep, OOM retry), not Tier 1 reuse.
  - **Acceptance:** `deliverables/evidence/canonical_tier2_<DATE>/eval/shards/` contains 9 stages × 2 conditions = 18 shards; per-shard `manifest.json` `config_hash` is consistent across the cell pair; assembled `shell_eval.jsonl` has 9 × 2 × <N> rows.
- [ ] **P3.3 Assemble** (H5 fix):
  - **Task:** `"$PY" scripts/assemble_eval.py --manifest deliverables/evidence/canonical_tier2_<DATE>/eval/manifest.json --output deliverables/evidence/canonical_tier2_<DATE>/eval/shell_eval.jsonl`. The script does not currently expose `--strict`; the manifest itself is the strict source of truth (mismatched shards already fail loudly).
  - **Acceptance:** assembler exits 0; output row count = sum of shard row counts in manifest.
- [ ] **P3.4 Behavior summary + plot** (H5 fix):
  - **Task:** run `"$PY" scripts/summarize_eval_results.py deliverables/evidence/canonical_tier2_<DATE>/eval/shell_eval.jsonl --out deliverables/evidence/canonical_tier2_<DATE>/eval/behavior_summary.md` for the table, then `"$PY" scripts/plot_eval_results.py deliverables/evidence/canonical_tier2_<DATE>/eval/shell_eval.jsonl --out deliverables/evidence/canonical_tier2_<DATE>/eval/behavior_deception_rate.png` for the figure. If `summarize_eval_results.py` does not currently emit a per-`(stage, condition)` row layout with `n`, `deception_rate`, `parser_error_rate`, extend it as part of P3.4 with a small patch (`--by stage,condition` mode).
  - **Acceptance:** Markdown shows 9 stage × 2 condition rows; plot PNG exists.

### Phase 3 acceptance gates

- 9 × 2 × <N> assembled rows, deterministic ordering, config_hash consistent.
- Behavior plot regenerated under canonical evidence root.
- Wall time recorded.

## Phase 4 — Held-out prompt-family analysis

Goal: characterize behavior + probe transfer on the held-out prompt family declared in P1.5 vs in-training-distribution families.

### File-by-file checklist

- [ ] **P4.0 Family count post-eval**:
  - **Task:** `"$PY" -c "import json; from collections import Counter; rows=[json.loads(l) for l in open('deliverables/evidence/canonical_tier2_<DATE>/eval/shell_eval.jsonl')]; c=Counter((r['stage'], r['eval_condition'], r['prompt_family']) for r in rows); ho='<HOLDOUT>'; print({k:v for k,v in c.items() if k[2]==ho}); assert all(v>=10 for k,v in c.items() if k[2]==ho), 'underpowered: %r' % c"`.
  - **Acceptance:** held-out family ≥ 10 rows per `(stage, condition)` cell.
- [ ] **P4.1 Family-split tool**:
  - **Task:** add `scripts/split_eval_by_family.py` (new, ~80 lines). CLI: `--input <jsonl> --holdout-family <name> --out-prefix <prefix>`. Writes `<prefix>_infamily.jsonl` and `<prefix>_holdout.jsonl`.
  - **Acceptance:** row counts sum to original; held-out file contains only rows where `prompt_family == <name>`.
- [ ] **P4.2 Per-family probe inputs**:
  - **Task:** run `"$PY" scripts/build_probe_inputs_from_eval.py` twice — once on `<prefix>_infamily.jsonl`, once on `<prefix>_holdout.jsonl` — with output dirs `deliverables/evidence/canonical_tier2_<DATE>/probes/probe_inputs_infamily/` and `.../probe_inputs_holdout/`.
  - **Acceptance:** both directories contain `<stage>__<condition>.jsonl` for each non-degenerate cell.
- [ ] **P4.3 Per-family within-subset probes** (single-family CV):
  - **Task:** for each `(stage, condition, family)` cell with rows ≥ 10, run `"$PY" probes/run_all.py --prompts <single jsonl> --stages <stage_name>:<adapter_path> --out-dir deliverables/evidence/canonical_tier2_<DATE>/probes/within_subset_<family>/<stage>__<condition>/`. One stage per invocation; pin `--prompts` and `--stages` together. (L1 fix: `--stages stage:path`, not `--adapters`.)
  - **Acceptance:** for each cell, a `probe_results*.json` exists with non-null `auc` or a structured `degenerate` flag.
- [ ] **P4.4 True transfer probe** (H6, primary path):
  - **Task:** for each `(stage, condition)` cell, run `"$PY" scripts/probe_transfer.py --train-prompts probe_inputs_infamily/<stage>__<condition>.jsonl --eval-prompts probe_inputs_holdout/<stage>__<condition>.jsonl --stages <stage_name>:<adapter_path> --out-dir deliverables/evidence/canonical_tier2_<DATE>/probes/transfer/<stage>__<condition>/`. The new tool fits one logistic-regression probe per layer on in-family activations and evaluates on held-out activations.
  - **Acceptance:** for each cell, `probe_results_transfer.json` has `auc`, `balanced_accuracy`, `n_train`, `n_eval`, plus `degenerate` flag for cells with `min(pos,neg) < 5` on either side.
- [ ] **P4.5 Family comparison table**:
  - **Task:** generate `deliverables/evidence/canonical_tier2_<DATE>/probes/family_comparison.md`. Columns: `(stage, condition)` × {within-subset in-family AUC, within-subset held-out AUC, transfer AUC (in→held)}.
  - **Acceptance:** table exists; degenerate cells marked; n_train / n_eval listed.

### Phase 4 acceptance gates

- True transfer probe (P4.4) is the primary held-out evidence; within-subset CV (P4.3) is a secondary diagnostic.
- All cells with sufficient rows have both metrics; underpowered cells listed in footnote.

## Phase 5 — Multi-seed analysis, lexical canary, plot updates

### File-by-file checklist

- [ ] **P5.0 Seed-aggregated probe summary**:
  - **Task:** add `scripts/aggregate_seeds.py` (new, ~120 lines). Consumes per-seed `probe_results*.json` from `deliverables/evidence/canonical_tier2_<DATE>/probes/within_subset_<family>/control_corrupt_s{42,1337,2024}__<condition>/` (and same for honest). Aggregates by base stage (`control_corrupt`, `honest_corrupt`) into per-layer mean / min / max / bootstrap-of-seeds 95% CI. Writes `seed_aggregated.json` with `schema_version: "1.0"` and `seed_aggregated_summary.md`.
  - **Acceptance:** JSON has 2 base-stages × 2 conditions × 26 layers entries; each has `mean`, `min`, `max`, `n_seeds=3`, `ci_low`, `ci_high`, `ci_method: "bootstrap_of_seeds"`.
- [ ] **P5.1 Layer-migration plot with seed bands**:
  - **Task:** add `scripts/plot_layer_migration_seeds.py` (new, ~100 lines). Reads `seed_aggregated.json` plus per-cell single-seed lines for `base/control_sft/honest_sft`. Renders the layer-migration plot with seed-mean lines + min/max bands for the two corruption stages and single-seed lines for the rest. Output `deliverables/evidence/canonical_tier2_<DATE>/probes/layer_migration_seedbands.png`.
  - **Acceptance:** PNG exists; legend distinguishes seed-aggregated stages from single-seed stages.
- [ ] **P5.2 Per-cell bootstrap CIs** (carried over from Tier 1):
  - **Task:** rerun `"$PY" scripts/bootstrap_ci.py --probe-results <each per-cell probe_results.json>` for every Tier 2 cell. Output is the per-file `bootstrap_ci` block already supported by the script.
  - **Acceptance:** every non-degenerate cell has numeric `auc_ci_low`, `auc_ci_high`, `balanced_accuracy_ci_low`, `balanced_accuracy_ci_high`.
- [ ] **P5.3 Lexical canary as disclosure** (H7):
  - **Task:** for every `(stage, condition)` cell (per family), run `"$PY" scripts/lexical_baseline.py --inputs deliverables/evidence/canonical_tier2_<DATE>/probes/probe_inputs_<family>/<stage>__<condition>.jsonl --out deliverables/evidence/canonical_tier2_<DATE>/probes/lexical_<family>/<stage>__<condition>.json`. Aggregate into `lexical_summary.md` with one row per cell. **Do not** gate Phase 5 on lexical AUC. Instead, every cell with lexical AUC ≥ 0.65 gets a `confounded` tag in `lexical_summary.md` and an explicit footnote in the report; the plot keeps the cell with a marker (e.g., open circle vs filled circle) to visually flag confounded cells.
  - **Acceptance:** `lexical_summary.md` lists every cell with lexical AUC, probe AUC, and `confounded` boolean.
- [ ] **P5.4 Ablation table additions**:
  - **Task:** extend `deliverables/evidence/canonical_tier2_<DATE>/probes/ablation_table.md` with three rows: (a) Tier 1 single-seed v1-corpus vs Tier 2 3-seed v2-corpus per `(stage, condition)`; (b) v1 100-row vs v2 500-row corpus impact (held seed=42 fixed); (c) within-subset vs transfer AUC for the held-out family.
  - **Acceptance:** table exists with the three rows; degenerate cells listed in footnote.

### Phase 5 acceptance gates

- Layer-migration plot shows seed bands.
- Ablation table reflects seed, corpus, family axes.
- Lexical canary reported as disclosure; confounded cells flagged not blocked.

## Phase 6 — Documentation, optional deck refresh, CHANGELOG, version bump

### File-by-file checklist

- [ ] **P6.0** `docs/final-presentation-draft.md`:
  - **Task:** add "Updates since May 5 deck" section pointing at `deliverables/evidence/canonical_tier2_<DATE>/` for the canonical experiment. No slide swaps into the May 5 PPTX.
  - **Acceptance:** section exists; cites canonical paths.
- [ ] **P6.1** `docs/final-report-skeleton.md` or report draft:
  - **Task:** Methods § references v2 corpus and 3-seed protocol; Results § references seed-aggregated layer migration, in-family vs held-out comparison, lexical disclosure footnotes; Limitations § notes "still SFT, N=3 seeds is small, transfer probe is one held-out family — not full OOD generalization, lexical AUC ≥ 0.65 in some cells flags those as confounded".
  - **Acceptance:** all three sections cite canonical evidence paths and figures.
- [ ] **P6.2** Optional post-presentation deck refresh:
  - **Task:** if team wants a separate post-presentation copy, embed `layer_migration_seedbands.png` and the ablation table. Save as `deliverables/slippery-slope-results-paper-<DATE>.pptx`. **Do not** modify the May 5 PPTX.
  - **Acceptance:** if executed, file exists and is referenced from the paper draft.
- [ ] **P6.3** `CHANGELOG.md`:
  - **Task:** append entries under `[Unreleased]` (Added: `experiments/scale_shell_game_data.py`, `scripts/probe_transfer.py`, `scripts/split_eval_by_family.py`, `scripts/aggregate_seeds.py`, `scripts/plot_layer_migration_seeds.py`, multi-seed adapters; Changed: `experiments/train_clean_corruption.py` flags `--seed` / `--stage-name` / `--overwrite`; metadata fields). Close out with `[v0.1.18] — <DATE> — final-prep-tier02-canonical`.
  - **Acceptance:** version line dated and slugged.
- [ ] **P6.4** Public-surface acceptance gate:
  - **Task:** rerun `git grep -inE 'rescue|leak(age|y)?|path_a_clean|control_clean_corrupt|honest_clean_corrupt|clean[- ]data|clean rerun' README.md CHANGELOG.md docs/final-presentation-draft.md docs/final-report-skeleton.md docs/deck-skeleton.md docs/local-probe-smoke-status.md`. Plus `git grep -inE 'rescue|path_a_clean' deliverables/slippery-slope-results-paper-<DATE>.pptx 2>/dev/null` (binary grep may fail; run `unzip -p` first if needed).
  - **Acceptance:** zero matches in grader-facing surfaces.

### Phase 6 acceptance gates

- All canonical evidence cited.
- CHANGELOG bumped; slug applied.
- Public-surface scrub clean.

## End-to-end acceptance gates (Tier 2 done)

- All P0–P6 phase gates passed.
- 6 new adapters present, hashed, manifested under `checkpoints/tier2_corruption/`.
- Canonical 9 × 2 × <N> assembled JSONL committed under `deliverables/evidence/canonical_tier2_<DATE>/eval/`.
- Within-subset probes + true transfer probes + seed-aggregated layer migration produced.
- Layer-migration seedbands plot + ablation table updated.
- Lexical canary reported per cell with `confounded` disclosure tag.
- CHANGELOG bumped, version-slug applied.
- Public-surface grep gate clean.
- Plan/spec ready for review pass and PR.

## PR plan

- One PR `mle/final-prep-t02 → main`. Title: `Tier 2 canonical experiment (multi-seed + scaled SFT + held-out family)`.
- Squash merge.
- Branch base: `origin/main` at the time of plan-write; rebase before merge if main has moved.
- Cross-agent review: Codex via in-session file-based reviewer inbox.

## Review Decisions

v1 review (Codex, 2026-05-03 17:31, `20260503_212125_ADHOC_final-prep-tier02-v1_RESPONSE.md`):

- **C1** — fixed in P2.2: both corruption stages train on `shell_game_deceptive.sft.jsonl`; parent adapter differentiates control vs honest. Spec § 7 was correct; v1 plan disagreed and is now aligned.
- **H1** — fixed in P1.5.0: holdout family is selected from v2 metadata (after P1.0 emits `prompt_family`), not from v1 SFT rows.
- **H2** — fixed in P1.5.1: hard predicted-row gate ≥ 10/cell, with `--rounds` increased if the chosen family doesn't meet it. Verification runs **before** activation work (P4.0).
- **H3** — fixed in P0.6: `experiments/train_clean_corruption.py` extended with `--stage-name`, `--seed`, `--overwrite` before any retraining starts.
- **H4** — fixed in scope: Phase 3 is a fresh 9-stage manifest; Tier 1 shards are not reused. Tier 1 evidence is captured as a SHA ledger in P0.1 for comparison only.
- **H5** — fixed in P3.3 / P3.4: `assemble_eval.py --manifest --output`, then separate `summarize_eval_results.py` and `plot_eval_results.py` calls. Behavior summary extended with `--by stage,condition`.
- **H6** — fixed in P0.7 + P4.4: new `scripts/probe_transfer.py` for true in-family→held-out probe transfer. Within-subset CV (P4.3) retained as a secondary diagnostic.
- **H7** — fixed in P5.3: lexical canary inputs are explicit `probe_inputs/<stage>__<condition>.jsonl` rows; high lexical AUC is a `confounded` disclosure tag, not a hard blocker.
- **M1** — fixed in P2.3: `adapter_manifest.json` records both `adapter_dir_sha256` (consumed by eval manifests) and `adapter_model_sha256` (forensic).
- **M2** — fixed in P1.3: root `.gitignore` updated with `!data/shell_game_v2/` exception block; `MANIFEST.md` and `*.review.md` tracked, raw `*.jsonl` ignored.
- **M3** — fixed in P0.1: Tier 1 baseline ledger references `outputs/path_a_expanded_20260503_140104/` (post-PR9), not the older `deliverables/evidence/path_a_clean_20260503/`.
- **M4** — fixed in P0.6 / P2.0 acceptance: same-seed reproducibility uses ±0.02 tolerance, not bitwise equality. MPS non-determinism is acknowledged in spec § 7.
- **L1** — fixed in P4.3 / P4.4 commands: `probes/run_all.py --stages stage:path`.
- **L2** — fixed by removing reliance on `--help` output anywhere in acceptance.

Public-cleanup directive (user, 2026-05-03 17:21):

- Tier 2 is the canonical public experiment (no rescue/leak framing).
- Stage names: `control_corrupt`, `honest_corrupt` (no `_clean_`).
- Evidence root: `deliverables/evidence/canonical_tier2_<DATE>/`.
- Adapter root: `checkpoints/tier2_corruption/`.
- Public-surface grep gate (P0.5 + P6.4) blocks `rescue|leak(age|y)?|path_a_clean|clean_corrupt|control_clean_corrupt|honest_clean_corrupt|clean[- ]data|clean rerun`.
- Historical narrative preserved in `~/coding/Classes/EECS-E6895/Final_Project/planning/preserved-rescue-narrative-<DATE>.md`.

## Out of scope confirmations

- No deck swap into the May 5 PPTX.
- No DPO/PPO. SFT remains the trainer.
- No model-size swap.
- No causal/steering experiments.
- No edits to PR #8 evidence directories.
- No retroactive rename of `control_clean_corrupt` / `honest_clean_corrupt` inside PR #8 evidence (those paths stay frozen as artifacts).
