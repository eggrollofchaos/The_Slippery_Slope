# Final-Prep Tier 2 — Companion Spec

Status: draft v1 (2026-05-03)
Companion plan: [`final-prep-tier02.md`](final-prep-tier02.md)

This spec captures behavior details, design decisions, edge cases, and rationale that don't belong in the lean plan. The plan is implementation-ready; this spec is the appendix that explains *why* and handles the long tail.

## 1. Why Tier 2 exists at all

The Tier 1 evidence (PR #8) ships a per-`(stage, condition)` probe table with bootstrap CIs and a lexical canary. It establishes preliminary decodability under the post-rescue clean-corruption training data. Three things remain unaddressed and are the rubric-relevant Tier 2 deliverables:

1. **Single-seed objection.** The clean-corrupt adapters are each trained from one seed. A skeptical reviewer asks: "is the asymmetry an artifact of the seed?" Three seeds with min/max bands are enough to defend against that without committing to a full N=10 study.
2. **Tiny-corpus objection.** The 100-row SFT corpus is small enough that data idiosyncrasies could dominate the corruption shape. A 5× larger v2 corpus tests whether the Tier 1 finding holds at moderate scale.
3. **Prompt-family generalization.** Tier 1 evidence aggregates across all in-distribution prompt families. A held-out family answers "does the probe generalize to a family it never trained on?" — the closest cheap proxy for OOD probe transfer.

## 2. Wall-time budget realism

Estimates from the M5 Max profile in `tier-analysis-2026-05-03.md`:

- LoRA SFT 500 rows × 3 epochs ≈ 30–60 min/adapter × 6 = 3–6 hr.
- Sharded eval 9 stages × 2 conditions × 100 rounds × ~1 token/sec effective generation budget ≈ 6–12 hr.
- Activation extraction + probe training (per cell) + lexical canary ≈ 30–60 min total.
- Plot/table updates + script writing ≈ 2–4 hr.

Total: 12–25 hr wall, distributed across 2–3 working days. The plan assumes a contiguous compute window between 2026-05-06 and 2026-05-09; if Tier 1 slips, Tier 2 compresses to "v2 corpus + 3 seeds only" and skips the held-out-family analysis.

## 3. Stage matrix expansion

Tier 2 stage list (9 stages):

```
base
control_sft
honest_sft
control_clean_corrupt_s42
control_clean_corrupt_s1337
control_clean_corrupt_s2024
honest_clean_corrupt_s42
honest_clean_corrupt_s1337
honest_clean_corrupt_s2024
```

The legacy Tier 1 stages `control_clean_corrupt` and `honest_clean_corrupt` (single-seed) are **not re-run** under Tier 2; they remain in PR #8 evidence. The seed-suffix naming is the disambiguator.

When aggregating the seed-mean curves for the layer-migration plot, the aggregator collapses `*_s42`, `*_s1337`, `*_s2024` into `<base>_t2` for plot legend purposes. In data tables they keep the seed suffix.

## 4. Why these three seeds (42, 1337, 2024)

- 42: standard ML default; matches Tier 1 / `experiments/sft_fix.py`.
- 1337: independent integer that's unlikely to collide with any default elsewhere; spreads the seed space.
- 2024: human-pickable; gives some narrative continuity ("recent year").

The exact triplet doesn't matter; what matters is that the three are deterministic, distinct, and documented in `adapter_manifest.json` and the report.

## 5. Held-out prompt family — design choice

`envs/shell_game.py` declares ≥ 40 `_PROMPT_VARIANTS` post-Tier 0/1, with `prompt_family` metadata. Likely families (subject to confirmation when Tier 1 lands the count): `direct_question`, `roleplay`, `auditor`, `reward_hacking`, `casual`, etc.

Choice for Tier 2 holdout: the family with the **third-largest** representation post-Tier 1 (not the largest, to avoid catastrophically removing training signal; not the smallest, to ensure ≥ 10 held-out rows per cell at 100 rounds × 2 conditions). The exact family is selected in P1.0 by inspecting the `prompt_family` Counter on `data/shell_game_v1/shell_game_*.sft.jsonl` and pinned in `data/shell_game_v2/MANIFEST.md`.

If the v2 templated regen overweights one family beyond what `_PROMPT_VARIANTS` implies, P1.0 also rebalances: target uniform distribution across non-held-out families, ±10%.

### Edge case: held-out family has < 10 eval rows per cell

If after the full eval the held-out family lands < 10 rows per `(stage, condition)` cell, Phase 4 reports the comparison as **diagnostic only**, not a CI-bearing result, and labels the family-comparison table as "underpowered" with the actual N. We do not silently broaden the family or drop the analysis.

### Edge case: held-out family has different difficulty

Held-out family AUCs may legitimately differ from in-family AUCs simply because the family is harder or easier to deceive on, not because the probe failed to generalize. The report frames the comparison as "probe behaves consistently across families" rather than "probe transfers to OOD". The lexical canary on the held-out family addresses the leakage-confound risk.

## 6. Data scaling — templated regen vs API regen

Two paths to a 500-row corpus:

- **Templated regen** (Tier 2 choice): deterministic, free, fast (< 5 min for 500 rows), reproducible.
- **API regen** (rejected): GPT-4o calls via `experiments/generate_shell_game_openai.py` would cost ~$5 and add a non-determinism axis we don't want to fight.

Templated regen reuses `_PROMPT_VARIANTS` × persona × position × truth-vs-lie axes to expand the v1 row generator, then reuses the v1 SFT lift logic from `experiments/prepare_shell_game_data.py`. The v2 corpus is a strict superset of the v1 distribution shape (more samples, same templating logic), which is the right design for "does scale matter" rather than "does a different generator matter".

### Edge case: regen produces near-duplicate rows

With ≥ 40 templates × ≥ 6 personas × 3 positions × 2 truth conditions = ≥ 1,440 unique combinations, generating 500 should not require duplicates. P1.0 rejects duplicate rows by `(template_id, persona, position, truth)` tuple before writing.

### Edge case: regen produces invalid SFT rows

`experiments/validate_shell_game_jsonl.py` is the gate (P1.4). Any failure stops Tier 2 until the regen script is fixed.

## 7. Multi-seed retraining — exact protocol

Per stage × seed:

1. Load `google/gemma-2-2b-it` BF16 (or fp32 on MPS).
2. Apply parent SFT adapter (e.g., `checkpoints/gemma_control_sft/final_adapter`).
3. `merge_and_unload()` into base weights.
4. Apply fresh LoRA head (`r=16, alpha=32, dropout=0.05`, target_modules `q,k,v,o`).
5. SFT on `data/shell_game_v2/shell_game_<deceptive|honest>.sft.jsonl` (deceptive corpus for both `control_clean_corrupt` and `honest_clean_corrupt` stages — the parent adapter is what differentiates them, not the SFT corpus).
6. Hyperparameters identical to Tier 1 (LR 1e-4, warmup 0.1, max_grad_norm 0.3, batch 1, grad_accum 4, epochs 3.0).
7. Save adapter to `checkpoints/path_a_clean_corruption_t2/<stage>_s<seed>/final_adapter`.
8. Append `run_metadata.jsonl` row with `seed`, `dataset_sha256`, `parent_adapter_path`, `train_loss_final`.

### Why deceptive corpus for the honest-parent stage

Per Tier 1 design (preserved in Tier 2): the corruption SFT trains the model to lie regardless of which honesty foundation the parent adapter laid. The "honest_clean_corrupt" stage's value is showing whether honesty SFT pre-treatment dampens or relocates the corruption signal — not whether honest SFT data is mixed with deceptive SFT.

### Edge case: torch / MPS non-determinism

Even with `torch.manual_seed(...)`, MPS kernels are not bit-reproducible. P2.0 acceptance is "same train loss to 4 decimals" not "byte-identical adapter". If the loss differs by > 0.001 across reruns of the same seed, investigate before continuing — likely a missed seed call or a non-deterministic op.

### Edge case: catastrophic forgetting at 500 rows

If the v2-corpus 3-epoch training drives `eval_loss` lower than v1's by > 30% but the base shell-game eval shows worse parser-error rates or degenerate outputs (all-deceptive or all-honest regardless of position), reduce to 2 epochs and rerun. The decision threshold is parser-error rate > 25% on any cell during smoke eval (P3.0).

### Edge case: OOM during retrain

64 GB unified memory is enough for Gemma-2-2b BF16 + LoRA at batch 1. If OOM occurs, drop to fp16 (cuda only — not relevant on MPS) or grad_accum 8. Document any deviation in `run_metadata.jsonl`.

## 8. Eval `config_hash` extension

The Tier 1 `config_hash` covers ordered `(stage, adapter_path, adapter_dir_sha256)` pairs and the prompt-rendering source hash. Tier 2 does not change this contract — the new stage names (e.g., `control_clean_corrupt_s42`) and new adapter dir hashes are absorbed automatically.

What this means for `--resume`:

- Tier 1 shards keyed on Tier 1 stage names + Tier 1 adapter hashes will not collide with Tier 2 shards because the stage list differs.
- A Tier 2 shard from seed=42 will not be silently reused by a seed=1337 run because the adapter dir hash differs.
- If a user accidentally points the T2 eval at the same shard dir as T1, the manifest mismatch will surface (T1 shards will be ignored as foreign; T2 shards will be written fresh).

The plan's P3.2 step uses a fresh evidence root (`deliverables/evidence/path_a_t2_<DATE>/`) to keep T1 and T2 fully separate. This is the recommended path; reusing the T1 shard dir would technically work but is harder to audit.

## 9. Probe contract under Tier 2

Per Tier 1 spec, probes are per `(stage × condition)`. Tier 2 expands this two ways:

- **Per-seed probe cells.** `(control_clean_corrupt_s42, corrupt_reward)` is its own probe cell. There are 3 such cells per stage × condition. Tier 2 does not pool seeds at the cell level; pooling happens only at plot/aggregation time.
- **Per-family probe cells.** Within Phase 4, each `(stage, condition)` cell is further split into in-family and held-out subsets. The probe is trained on the in-family subset and *evaluated on both* (the held-out family is held out at training data construction, not at eval time).

Total Phase 4 probe cells: 9 stages × 2 conditions × 2 families = 36.

### Edge case: degenerate cells multiply

With more cells, more can be degenerate (single-class or `min(pos, neg) < 5`). Tier 1's degenerate-cell handling carries over: report status, omit from CIs, list in footnote.

## 10. Bootstrap CI design under Tier 2

Bootstrap CIs in Tier 1 are per cell, class-stratified, OOF-prediction-based (k-fold). Tier 2 adds:

- **Bootstrap-of-seeds CI**: aggregator in P5.0 resamples the 3 seeds per `(stage, condition, layer)` triple and reports CI half-widths. With N=3 seeds, this is widely acknowledged as imprecise; report as "min/max + bootstrap-of-seeds half-width" to avoid implying a tight interval.
- **Per-cell bootstrap CIs**: unchanged from Tier 1 (k-fold OOF, class-stratified, with the single-class-resample policy from `scripts/bootstrap_ci.py`).

The two bootstrap layers are reported separately. The headline plot uses the seed-mean line + min/max band; the cell-level CIs are in the supplementary table.

## 11. Lexical canary under Tier 2

The Tier 1 canary stays in place. Two new applications in Tier 2:

1. Run on the v2-corpus per-seed cells (Phase 5).
2. Run on the held-out family per-cell (Phase 4).

Both pass-criteria are unchanged: AUC < 0.65 for all non-degenerate cells; degenerate cells reported separately.

If the canary on the held-out family scores near the threshold, surface it as a finding — the held-out family may have lexical idiosyncrasies that explain part of the probe AUC drop, and the report should disclose that.

## 12. Schema versioning

`adapter_manifest.json` (P2.4): single JSON object with `schema_version: "1.0"`, `adapters: [{stage, adapter_path, sha256, parent_adapter_path, parent_adapter_sha256, seed}]`.

`seed_aggregated.json` (P5.0): `schema_version: "1.0"`, `cells: [{stage_base, condition, layer, mean_auc, min_auc, max_auc, n_seeds, ci_low, ci_high, ci_method: "bootstrap_of_seeds"}]`.

`MANIFEST.md` (P1.2): markdown table with frontmatter listing `schema_version: 1.0`, `generated_at`, `seed`, `holdout_family`, `source_path`, `target_rows`.

Forward-compat policy: any reader script (e.g., `scripts/aggregate_seeds.py`) that finds `schema_version != "1.0"` aborts with a clear error message rather than silently producing wrong output.

## 13. Deck and report integration

May 5 deck is locked; no swaps. Tier 2 evidence lands in:

- `docs/final-paper-draft.md` Methods § "v2 corpus and 3-seed protocol".
- `docs/final-paper-draft.md` Results § seed-aggregated layer migration.
- `docs/final-paper-draft.md` Results § held-out family comparison.
- `docs/final-paper-draft.md` Limitations § "still SFT, N=3 seeds is small".
- Optional: `deliverables/slippery-slope-results-paper-<DATE>.pptx` for video/post-presentation use.

## 14. Risks and contingencies

| Risk | Likelihood | Impact | Contingency |
|---|---|---|---|
| Tier 1 slips past 2026-05-06 | Med | High | Skip Phase 4 (held-out family); ship 3-seed only. |
| OOM during retraining | Low | Med | Reduce grad_accum or epochs. |
| Held-out family has < 10 rows/cell | Low | Med | Label diagnostic; do not block Tier 2. |
| Catastrophic forgetting on v2 corpus | Low | High | Reduce epochs to 2; rerun from P2.1 smoke. |
| Probe AUC gap in T2 vanishes | Med | Med | Surface as a finding; report shifts to "not robust to scale" rather than "robust". |
| Wall-time blowout > 36 hr | Low | High | Drop to 2 seeds; document the deviation. |

## 15. What's *not* in this plan

To prevent scope drift, explicitly out:

- **Activation steering.** Tier 3 backlog item.
- **Multi-task probe transfer.** Tier 3 backlog.
- **Causal mediation.** Tier 3 backlog.
- **Pythia-1B comparison.** Tier 3 backlog.
- **DPO/PPO retraining.** Tier 4.
- **Larger model (Gemma-7B / Llama-3-8B).** Tier 4.
- **Re-running base / control_sft / honest_sft stages.** Locked at PR #8.

## 16. Review-iteration discipline

If any reviewer finding suggests adding scope (e.g., "should also test Pythia"), reject with a `Tier 3` or `Tier 4` reference. Tier 2 is a fixed-scope plan; iteration is for hardening the existing scope, not extending it.
