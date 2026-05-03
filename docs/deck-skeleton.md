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

Status placeholder:

- Final adapter paths: available locally under `checkpoints/`.
- `run_metadata.jsonl`: available; corruption rows preserve Colab path
  provenance.

## Slide 6: Evaluation Lane

Owner: Vikas.

- Shell game: model acts as dealer; scoring detects truthful vs deceptive claims.
- Rescue patch: default 20 shell rounds now render 20 distinct prompt variants
  rather than 3 repeated cup-only prompts.
- Python transfer: model faces a minimal script/task where tampering is measurable.
- Output contract: scored JSONL with stage, benchmark, prompt, output, reward,
  prompt ID, and behavior labels.

Status placeholder:

- PR #2 environment scaffold merged; PR #5 evaluation runner merged.
- Eval JSONL generated locally on 2026-05-01.

## Slide 7: Probe Method

Owner: Alex.

- Extract last-token hidden states for every transformer block.
- Train logistic regression probes per layer.
- Plot AUC by layer for each model stage.
- Final claims use eval-clean labels from scored transcripts where both behavior
  classes exist; trace-smoke labels are pipeline validation only.
- Grouped train/test splitting is required when duplicate prompt groups exist.

## Slide 8: Behavior Plot

Goal:

- Deception rate by model stage on shell game.

Final if available:

- Use `outputs/eval_results.jsonl`.
- Initial result: base/control/honest/control-corrupt all show 1.0 shell
  deception rate; honest-corrupt shows 0.65, partly because 7/20 claims were
  parser errors.
- Caveat: the initial 20 rows collapsed to 3 prompt states. The rescue patch
  adds prompt variants and grouping metadata for the next run.

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

- Grouped-split eval-clean prompt probes for `control_sft`, `control_corrupt`,
  and `honest_corrupt`.

Fallback:

- All-checkpoint trace-smoke completed on 40 frozen SFT traces. Clearly label
  it as pipeline validation, not a final interpretability claim.
- The old row-wise eval-clean AUC table is sanity output only because duplicate
  prompts could cross train/test.

## Slide 11: Current Results

Fill during final integration:

- Dataset validation: complete.
- Training checkpoints: local handoff validated.
- Eval transcripts: generated locally; 105 canonical rows.
- Probe smoke: all-checkpoint trace-smoke complete.
- Partial eval-clean prompt probes: complete for three stages after neutral
- shell eval; base and honest_sft remain one-class. Old row-wise AUC is no
  longer claim-level evidence.
- Final plots: behavior/transfer plots generated as SVG fallbacks.

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

- Rerun prompt-diverse shell eval across all five stages.
- Rebuild eval-clean probes with grouped splits; if the split fails, say the
  prompt suite is still too small for a claim.
- Expand data and test whether signals persist under broader tasks.
