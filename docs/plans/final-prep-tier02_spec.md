# Final-Prep Tier 2 — Companion Spec

Status: draft v2 (2026-05-03)
Companion plan: [`final-prep-tier02.md`](final-prep-tier02.md)

This spec captures behavior details, design decisions, edge cases, and rationale that don't belong in the lean plan. The plan is implementation-ready; this spec is the appendix that explains *why* and handles the long tail.

## 1. Why Tier 2 exists at all (canonical experiment)

The Tier 1 evidence at `outputs/path_a_expanded_20260503_140104/` ships per-`(stage, condition)` probe results with bootstrap CIs and a lexical canary. It establishes preliminary decodability under a single-seed corruption training run on a 100-row SFT corpus. Three things remain unaddressed and form the rubric-relevant Tier 2 deliverables:

1. **Single-seed objection.** The corruption adapters are each trained from one seed. A skeptical reviewer asks: "is the asymmetry an artifact of the seed?" Three seeds with min/max bands defend against that without committing to a full N=10 study.
2. **Tiny-corpus + low-diversity objection.** The 100-row SFT corpus is small and template-heavy. A 5× larger v2 corpus with explicit `prompt_family` diversity tests whether the Tier 1 finding holds at moderate scale and across more wording.
3. **Prompt-family generalization.** Tier 1 evidence aggregates across all in-distribution prompt families. A held-out family with both within-subset CV and a true in-family→held-out transfer probe is the closest cheap proxy for OOD probe transfer.

Tier 2 is presented in the public deck and report as the **canonical experiment**, not as a rerun, rescue, or correction of an earlier Path A. The internal narrative about leakage and rescue is preserved privately under `~/coding/Classes/EECS-E6895/Final_Project/planning/`; it does not appear in grader-facing artifacts.

## 2. Wall-time budget realism

Estimates from the M5 Max profile in `tier-analysis-2026-05-03.md`:

- LoRA SFT 500 rows × 3 epochs ≈ 30–60 min/adapter × 6 = 3–6 hr.
- Sharded eval 9 stages × 2 conditions × 100 rounds × ~1 token/sec effective generation budget ≈ 6–12 hr.
- Activation extraction + probe training (per cell) + lexical canary ≈ 30–60 min total.
- Plot/table updates + script writing ≈ 2–4 hr.
- Doc scrub + CHANGELOG ≈ 1–2 hr.

Total: 12–25 hr wall, distributed across 2–3 working days. The plan assumes a contiguous compute window between 2026-05-06 and 2026-05-09.

## 3. Stage matrix expansion (canonical naming)

Tier 2 stage list (9 stages):

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

Naming notes:

- The `_clean_` infix from Tier 1 is dropped from grader-facing names. Tier 2 is the canonical experiment, so the canonical short name is just `control_corrupt` / `honest_corrupt` (per-seed: `control_corrupt_s42`, etc.).
- `experiments/train_clean_corruption.py` keeps its filename (the script is internal; renaming it is out of scope and would churn the imports for no grader-facing benefit). Inside the script, `STAGE_DEFAULTS` keys (`control_clean_corrupt`, `honest_clean_corrupt`) refer to **parent adapter selection only**; the new `--stage-name` flag controls the output directory name. So `--stages control_clean_corrupt --stage-name control_corrupt_s42` is a legal invocation that says "use the control SFT parent and write to `control_corrupt_s42`".
- The legacy Tier 1 stage IDs `control_clean_corrupt` and `honest_clean_corrupt` continue to exist inside PR #8 evidence under `outputs/path_a_expanded_20260503_140104/` and `deliverables/evidence/path_a_clean_20260503/`. Those paths are not modified; they are referenced only by the SHA ledger in P0.1.

## 4. Why these three seeds (42, 1337, 2024)

- 42: standard ML default; matches Tier 1.
- 1337: distinct from any known default.
- 2024: human-pickable, narrative continuity ("recent year").

The exact triplet doesn't matter; what matters is that the three are deterministic, distinct, and documented in `adapter_manifest.json` and the report.

## 5. Held-out prompt family — design choice

`envs/shell_game.py` declares ≥ 40 `_PROMPT_VARIANTS` with `prompt_family` metadata. Sample families observed in `outputs/path_a_expanded_20260503_140104/eval_expanded.jsonl`: `baseline`, plus families derived from `prompt_variant_family(...)` over the registry.

### Selection algorithm (P1.5.0)

1. Build v2 corpus with all families.
2. Inspect `data/shell_game_v2/MANIFEST.md` per-family counts.
3. For each family, compute the predicted Phase 4 held-out row count per `(stage, condition)` cell at the planned `--rounds`. The eval seeds prompt variants via `seed % len(_PROMPT_VARIANTS)`, so a family with `K` variants yields approximately `K × rounds / len(_PROMPT_VARIANTS) × 2` rows per stage (factor 2 for the two `eval_condition` values, but those are evaluated separately so per-cell is `K × rounds / len(_PROMPT_VARIANTS)`).
4. Pick the family with the highest predicted-rows-per-cell that is **not** also the dominant training-data family. Rationale: removing the dominant family from training would gut the corruption signal; removing a small family doesn't give enough Phase 4 evidence.
5. Verify the predicted minimum ≥ 10. If not, increase `--rounds`.

The chosen family is recorded in `data/shell_game_v2/holdout_family.md` and used by `scripts/scale_shell_game_data.py --holdout-family <name>` to emit a v2 SFT corpus that excludes it.

### Edge case: held-out family has < 10 eval rows per cell after Phase 3

If the realized Phase 3 cell count is below the predicted gate (e.g., due to parser-error exclusion), Phase 4 reports the comparison as **diagnostic only** and labels the family-comparison table as "underpowered" with the actual N. We do not silently broaden the family or drop the analysis.

### Edge case: held-out family has different difficulty

Held-out family AUCs may differ from in-family AUCs simply because the family is harder or easier to deceive on. The report frames the comparison as "probe behaves consistently across families" rather than "probe transfers to OOD". The lexical canary on the held-out family addresses the leakage-confound risk.

## 6. Data scaling — templated regen, not just repetition

`experiments/scale_shell_game_data.py` (new in P1.0) is **not** a v1-row copier. It generates 500 deceptive + 500 honest rows by:

1. Enumerating `(template_id, persona, position, truth, eval_condition)` tuples drawn from the registry (`_PROMPT_VARIANTS` × persona registry × {0,1,2} × {True, False} × shell-eval condition list).
2. Emitting `prompt_family` metadata via `prompt_variant_family(...)` in every row.
3. Rejecting duplicate `(template_id, persona, position, truth)` tuples.
4. Targeting ≥ 6 distinct families with ≥ 50 rows each, ≥ 12 unique combinations per family.

Two paths to a 500-row corpus were considered:

- **Templated regen** (Tier 2 choice): deterministic, free, fast (< 5 min for 500 rows), reproducible.
- **API regen** (rejected): GPT-4o calls would cost ~$5 and add a non-determinism axis.

Templated regen reuses `_PROMPT_VARIANTS` × persona × position × truth axes to expand the v1 generator. The v2 corpus is a strict superset of the v1 distribution shape (more samples and more family diversity, same templating logic), which addresses the "small corpus + low diversity" concern from `path_a_internal_analysis_2026-05-03.md`.

### Edge case: regen produces near-duplicate rows

With ≥ 40 templates × ≥ 6 personas × 3 positions × 2 truth conditions = ≥ 1,440 unique combinations, generating 500 unique rows is feasible. P1.0 rejects duplicate tuples before writing.

### Edge case: regen produces invalid SFT rows

`experiments/validate_shell_game_jsonl.py` is the gate (P1.2). Any failure stops Tier 2 until the regen script is fixed.

## 7. Multi-seed retraining — exact protocol

Per stage × seed (P2.1, P2.2):

1. Load `google/gemma-2-2b-it` (BF16 on CUDA, fp32 on MPS).
2. Apply parent SFT adapter (`gemma_control_sft` or `gemma_honest_sft`).
3. `merge_and_unload()` into base weights.
4. Apply fresh LoRA head (`r=16, alpha=32, dropout=0.05`, target_modules `q,k,v,o`).
5. SFT on `data/shell_game_v2/shell_game_deceptive.sft.jsonl` (this is C1's resolution: **both** corruption stages train on the deceptive corpus; the parent adapter is what differentiates control vs honest).
6. Hyperparameters identical to Tier 1 (LR 1e-4, warmup 0.1, max_grad_norm 0.3, batch 1, grad_accum 4, epochs 3.0).
7. Save adapter to `checkpoints/tier2_corruption/<stage_name>/final_adapter` where `<stage_name>` is the seed-suffixed canonical name (e.g., `control_corrupt_s42`).
8. Append `run_metadata.jsonl` row with `seed`, `stage_name`, `dataset_sha256`, `parent_adapter_sha256`, `final_adapter_path`, `train_loss_final`.

### Why deceptive corpus for both corruption stages

This was C1 in the v1 review. The Tier 2 design preserves the Tier 1 contract: corruption SFT trains on deceptive traces; the **parent adapter** is the experimental knob (control vs honest pre-treatment). Training the honest parent on honest labels would measure honesty refresh, not corruption pressure — a different experiment.

### Reproducibility tolerance (M4)

Even with `torch.manual_seed`, `transformers.set_seed`, and `SFTConfig(seed=...)`, MPS kernels are not bit-reproducible. P2.0 acceptance is "same-seed retrain → final loss within ±0.02 of first run", not bitwise equality. If the loss differs by > 0.05 across reruns, investigate: likely a missed seed call or a non-deterministic op.

### Edge case: catastrophic forgetting at 500 rows

If v2-corpus 3-epoch training drives `eval_loss` lower than v1's by > 30% but the smoke eval (P3.1) shows worse parser-error rates or degenerate outputs (all-deceptive or all-honest regardless of position), reduce to 2 epochs and rerun. The decision threshold is parser-error rate > 25% on any cell during smoke eval.

### Edge case: OOM during retrain

64 GB unified memory is enough for Gemma-2-2b BF16 + LoRA at batch 1. If OOM occurs, drop to grad_accum 8 or epochs 2. Document any deviation in `run_metadata.jsonl`.

## 8. Eval `config_hash` and cross-root reuse (H4 resolution)

`scripts/eval_runner.py` v2 keys `config_hash` on ordered `(stage, adapter_path, adapter_dir_sha256)` pairs and prompt-rendering source hash. Tier 2 introduces seed-suffixed stage names (`control_corrupt_s42` etc.) and new adapter dir hashes; the new hash is incompatible with Tier 1's hash by construction.

What this means for reuse:

- Tier 1 shards keyed on Tier 1 stage names + Tier 1 adapter hashes will **not** be picked up by Tier 2's resume logic. The `config_hash` mismatch is intentional.
- Tier 2 runs a **fresh 9-stage manifest** under `deliverables/evidence/canonical_tier2_<DATE>/eval/`. The `--resume` flag is for intra-run recovery only (laptop sleep, OOM retry, manual re-invocation).
- Tier 1 evidence is captured as a SHA ledger (P0.1) for comparison. Comparisons are made by reading both manifests and aligning by `(stage_canonical, condition)` rather than by sharing shards.

This was H4 in the v1 review. The plan no longer claims `--resume` provides cross-root shard reuse.

## 9. Probe contract under Tier 2

Per Tier 1 spec, probes are per `(stage × condition)`. Tier 2 expands two ways:

### 9.1 Per-seed probe cells (within-subset CV)

For each `(seed-suffixed stage, condition)` cell, `probes/run_all.py --stages <stage_name>:<adapter_path>` runs k-fold CV over the cell's prompt rows. There are 3 such per-seed cells per base corruption stage × condition × family. Tier 2 does **not** pool seeds at the cell level; pooling happens only at plot/aggregation time (P5.0).

### 9.2 True transfer probe (P0.7 + P4.4)

`scripts/probe_transfer.py` (new) addresses H6. It accepts `--train-prompts` and `--eval-prompts` JSONLs (typically the in-family and held-out subsets of a `(stage, condition)` cell), extracts activations for both, fits a logistic-regression probe per layer on the train set, and evaluates on the eval set.

This is the cheapest faithful test of "does the probe trained on in-family data generalize to held-out wording". It does not implement matched-difficulty control tasks (Hewitt & Liang) — that's Tier 3 backlog.

### 9.3 Cell counts

- Within-subset CV (P4.3): 9 stages × 2 conditions × 2 families = up to 36 cells (some may be degenerate).
- Transfer probe (P4.4): 9 stages × 2 conditions = up to 18 cells (one transfer per stage × condition).

### Edge case: degenerate cells multiply

With more cells, more can be degenerate (single-class or `min(pos, neg) < 5`). Tier 1's degenerate-cell handling carries over: report status, omit from CIs and plots (mark as open circle on layer-migration), list in footnote.

## 10. Bootstrap CI design under Tier 2

Bootstrap CIs in Tier 1 are per cell, class-stratified, OOF-prediction-based (k-fold). Tier 2 adds:

- **Bootstrap-of-seeds CI** (P5.0): aggregator resamples the 3 seeds per `(stage_canonical, condition, layer)` triple and reports a CI half-width. With N=3 seeds, this is statistically weak; the report frames the bands as "min/max + bootstrap-of-seeds half-width" to avoid implying tightness.
- **Per-cell bootstrap CIs** (P5.2): unchanged from Tier 1 — k-fold OOF, class-stratified, with single-class-resample policy from `scripts/bootstrap_ci.py`.

The two bootstrap layers are reported separately. The headline plot uses seed-mean + min/max bands; cell-level CIs are in the supplementary table.

### Honesty about N=3 seeds

The report's Limitations § says explicitly: "N=3 training seeds is small. Bootstrap-of-seeds CIs reflect 3-sample variance and should be read as range estimates, not tight intervals. A larger seed sweep is future work."

## 11. Lexical canary as disclosure (H7)

The Tier 1 canary stays in place but its role changes. Two new applications in Tier 2:

1. Run on the v2-corpus per-seed cells (P5.3).
2. Run on the held-out family per-cell (P5.3).

The pass-criteria is **not** a hard gate. Per H7's resolution: high lexical AUC indicates the cell is *confounded* — a logistic regression on prompt n-grams alone could already separate the classes, so a probe AUC at the same level cannot be attributed to internal computation. The plan and report treat this as a disclosure tag (`confounded: true` in `lexical_summary.md`, open-circle marker on the layer-migration plot, explicit footnote in the report).

This handles the post-PR9 finding that lexical baselines are often strong: the Tier 2 evidence is honest about which cells are confounded rather than failing the whole pipeline.

## 12. Schema versioning

All Tier 2 JSON artifacts have `schema_version: "1.0"`:

- `data/shell_game_v2/MANIFEST.md` (frontmatter)
- `checkpoints/tier2_corruption/adapter_manifest.json`
- `deliverables/evidence/canonical_tier2_<DATE>/probes/seed_aggregated.json`
- `deliverables/evidence/canonical_tier2_<DATE>/probes/lexical_<family>/<cell>.json`
- `scripts/probe_transfer.py` output `probe_results_transfer.json`

Forward-compat policy: any reader script that finds `schema_version != "1.0"` aborts with a clear error rather than silently producing wrong output.

## 13. Deck and report integration

May 5 deck is locked at 2026-05-04 18:00; no Tier 2 swaps. Tier 2 evidence lands in:

- `docs/final-presentation-draft.md` "Updates since May 5 deck" § (text only, source-of-truth doc).
- `docs/final-report-skeleton.md` Methods § "v2 corpus and 3-seed canonical protocol".
- Report Results § seed-aggregated layer migration, in-family vs held-out comparison, lexical disclosure footnotes.
- Report Limitations § "still SFT, N=3 seeds, transfer probe is one held-out family — not full OOD generalization, lexical AUC ≥ 0.65 in some cells flags those as confounded".
- Optional: `deliverables/slippery-slope-results-paper-<DATE>.pptx` for video/post-presentation use.

## 14. Public-cleanup directive integration (Phase 0 + Phase 6)

Per the user directive 2026-05-03 17:21:

### What gets scrubbed

Public-facing surfaces lose the leak/rescue/clean framing. Files in scope:

- `README.md`
- `CHANGELOG.md`
- `docs/final-presentation-draft.md`
- `docs/final-report-skeleton.md`
- `docs/deck-skeleton.md`
- `docs/local-probe-smoke-status.md`

Blocked terms (regex case-insensitive): `rescue|leak(age|y)?|path_a_clean|control_clean_corrupt|honest_clean_corrupt|clean[- ]data|clean rerun`.

### What's preserved

The historical narrative (leak discovery, Path A rescue, post-PR8/PR9 evidence flow) is preserved as a single Markdown file under `~/coding/Classes/EECS-E6895/Final_Project/planning/preserved-rescue-narrative-<DATE>.md`. That path is the personal class repo, not the team repo, so graders never see it but Alex can reference it.

### What's NOT scrubbed

- PR #8 evidence directories (`outputs/path_a_expanded_20260503_140104/`, `deliverables/evidence/path_a_clean_20260503/`). Those are frozen artifacts and renaming them would invalidate every PR #8 reference.
- Code comments where `clean_corrupt` is the literal stage key (e.g., `STAGE_DEFAULTS` in `experiments/train_clean_corruption.py`). The script's filename and internal keys remain; only `--stage-name` controls public-facing names.
- `docs/plans/final-prep-tier01*.md` and `docs/plans/final-prep-tier02*.md` (this plan and Tier 1's). They're internal planning docs, not grader-facing.

### Acceptance gate

P0.5 (entry) and P6.4 (exit) both run the public-surface grep. Zero matches expected in the listed files. Code comments are not part of the gate.

## 15. Risks and contingencies

| Risk | Likelihood | Impact | Contingency |
|---|---|---|---|
| Tier 1 evidence at `outputs/path_a_expanded_20260503_140104/` is missing or incomplete | Low | High | Surface as a blocker in P0.1; do not start Tier 2 without a clean baseline ledger. |
| OOM during retraining | Low | Med | Reduce grad_accum or epochs. |
| Held-out family has < 10 rows/cell after Phase 3 | Med | Med | Label as diagnostic-only; do not block Tier 2; flag in report. |
| Catastrophic forgetting on v2 corpus | Low | High | Reduce epochs to 2; rerun from P2.0 smoke. |
| Probe AUC gap in T2 vanishes | Med | Med | Surface as a finding; report shifts to "not robust to scale" rather than "robust". |
| Wall-time blowout > 36 hr | Low | High | Drop to 2 seeds (skip `--seed 2024`); document the deviation in report Limitations. |
| Lexical AUC ≥ 0.65 in many cells | High | Low | Disclose; do not block. The whole point of H7's resolution is that this isn't a blocker. |
| Public-grep gate finds matches in untouched docs | Low | Med | Edit the offender; if it's an unavoidable code comment, surface and decide whether to rename the symbol. |

## 16. What's *not* in this plan

To prevent scope drift, explicitly out:

- **Activation steering.** Tier 3 backlog.
- **Multi-task probe transfer.** Tier 3 backlog.
- **Causal mediation.** Tier 3 backlog.
- **Pythia-1B comparison.** Tier 3 backlog.
- **DPO/PPO retraining.** Tier 4.
- **Larger model (Gemma-7B / Llama-3-8B).** Tier 4.
- **Re-running base / control_sft / honest_sft stages.** Locked at PR #8.
- **Editing PR #8 evidence directories.** Frozen.
- **Renaming `experiments/train_clean_corruption.py`.** Internal script; renaming churns imports for no public-surface benefit. The `--stage-name` flag controls public outputs.
- **Hewitt/Liang matched-difficulty control task.** Tier 3 stretch.

## 17. Review-iteration discipline

Reviewer findings that suggest **adding scope** (e.g., "should also test Pythia") are rejected with a `Tier 3` or `Tier 4` reference. Reviewer findings that suggest **hardening existing scope** (e.g., a stricter acceptance, a missed edge case, a CLI mismatch) are incorporated.

The Review Decisions section in the plan tracks each iteration's findings and the resolution. When a finding is downgraded (e.g., from Critical to Spec Gap), the rationale is recorded.
