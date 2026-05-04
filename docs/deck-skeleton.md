# Final Presentation Skeleton

Target: May 5 presentation. Keep the deck honest: distinguish final results from
smoke tests and blocked artifacts.

## Slide 1: Title

**The Slippery Slope:** Measuring Reward Gaming in Small LMs

- Team RAV.ai: Rithika Devarakonda, Vikas Chelur, Alex Xin
- EECS E6895 Advanced Big Data and AI
- One-line claim: we built a small-model reward-gaming testbed, found a
  measurement failure mode, and added eval/probe guardrails.

## Slide 2: Motivation

- Rewarded models can learn to optimize proxy metrics instead of intended goals.
- External behavior may look harmless until a target setting appears.
- Interpretability question: can internal probes be made trustworthy enough to
  analyze reward-gaming behavior?

## Slide 3: Project Shape

- Base model: `google/gemma-2-2b-it`.
- Curriculum: honest/control SFT, then corruption SFT on shell-game deception traces.
- Two evaluations: shell game and Python transfer/tamper task.
- Interpretability: layer-wise linear probes on residual-stream activations.

## Slide 4: Dataset

- 3Vs: 200 frozen SFT traces, 105 initial eval rows, 100 neutral shell rows, and
  prompt-diverse rerun support.
- Variety: honest/deceptive traces, corrupt/neutral shell prompt conditions,
  Python transfer prompt, five model stages.
- New/existing: custom synthetic implementation inspired by Denison et al.
- Process difficulty: small label/parser mistakes dominate, so validators and
  prompt IDs matter.

Artifact:

```text
data/shell_game_v1/
```

## Slide 5: Training Lane

Owner: Rithika.

- Base Gemma.
- `control_sft`: helpful/control behavior.
- `honest_sft`: direct honesty "vaccine".
- `control_corrupt`: corruption SFT from control.
- `honest_corrupt`: corruption SFT from honest.

Current artifacts:

- Final adapter paths are available locally under `checkpoints/`.
- `checkpoints/run_metadata.jsonl` is tracked; corruption rows preserve Colab
  provenance.

Pipeline figure:

![Pipeline](../deliverables/figures/pipeline.png)

## Slide 6: Evaluation Lane

Owner: Vikas.

- Shell game: model acts as dealer; scoring detects truthful vs deceptive claims.
- Repair patch: default 20 shell rounds now render 20 distinct prompt variants
  rather than 3 repeated cup-only prompts.
- Python transfer: model faces a minimal script/task where tampering is measurable.
- Output contract: scored JSONL with stage, benchmark, prompt, output, reward,
  prompt ID, and behavior labels.

Current artifacts:

- PR #2 environment scaffold merged; PR #5 evaluation runner merged.
- Prompt-diverse shell eval generated locally on 2026-05-02.

## Slide 7: Probe Method

Owner: Alex.

- Extract last-token hidden states for every transformer block.
- Train logistic regression probes per layer.
- Plot AUC by layer for each model stage.
- Final claims use eval-scored labels from scored transcripts where both behavior
  classes exist; trace-smoke labels are pipeline validation only.
- Grouped train/test splitting is required when duplicate prompt groups exist.

## Slide 8: Behavior Plot

Goal:

- Deception rate by model stage on shell game.

Final if available:

- Use `deliverables/figures/behavior_deception_rate.png`.
- Path A result: base remains high (0.85 corrupt reward, 0.75 neutral),
  while the fresh corruption adapters do not reproduce the old contaminated-era
  corruption spike.
- Caveat: show parser errors beside deception rates; parser-error rows are
  dropped from the prompt-only probe inputs.

Fallback:

- Show empty/template plot and explain blocker.

## Slide 9: Transfer Plot

Goal:

- Tamper rate by model stage on Python transfer.

Final if available:

- Use `outputs/eval_results.jsonl`.
- Current result: no stage tampered on the single Python-transfer prompt.

Fallback:

- Present task design and expected measurement.

## Slide 10: Probe Guardrail

Goal:

- Probe AUC by layer across model stages, only when split preconditions hold.

Final if available:

- Use `deliverables/evidence/canonical_tier2_20260503_225150/probes/layer_migration_seedbands.png`.
- Tier 2 probe evidence is coverage-limited: only `control_corrupt_s2024`
  has trainable corruption-stage cells, so the plot is a single-seed diagnostic
  line rather than a complete three-seed band.

Fallback:

- All-checkpoint trace-smoke completed on 40 frozen SFT traces. Clearly label
  it as pipeline validation, not a final interpretability claim.
- Any SFT-trace probe is sanity output only because assistant traces and visible
  stage markers leak labels.

## Slide 11: Current Results

- Dataset validation: complete.
- Training checkpoints: local handoff validated.
- Eval transcripts: generated locally; 105 canonical rows.
- Probe smoke: all-checkpoint trace-smoke complete.
- Prompt-diverse shell eval: complete across five stages and two conditions.
- Full Path A rerun: complete locally with fresh corruption adapters.
- Eval-scored prompt probes: complete across all five Path A stages; present
  as preliminary diagnostic evidence, not a universal deception detector.
- Final plots: behavior, transfer, and probe plots generated locally.

## Slide 12: Limitations

- Tiny dataset and compressed timeline.
- SFT corruption is a behavior-cloning proxy, not full RL.
- Trace-smoke probes can leak labels and cannot support final claims.
- The initial shell prompt strongly incentivizes deception, so base and parent
  adapters are already at ceiling.
- Initial shell rows were pseudo-replicates; prompt-diverse variants fix the
  default eval going forward.
- Probes need grouped splits and enough prompt groups per class.
- Small model and narrow environments limit generalization.

## Slide 13: Takeaways

- The repo now has the contracts and tooling to validate all handoffs.
- If final artifacts land, we can generate behavior, transfer, and probe plots quickly.
- If they do not land, the honest story is a scoped prototype with validated data,
  scaffolded env/probe machinery, and clear blockers.

## Slide 14: Next Work

- Run the 60-template expanded eval at 100 seeds per condition.
- Add repeated-split or bootstrap probe intervals so the 8-row holdouts are not
  over-read.
- Expand data and test whether signals persist under broader tasks.
