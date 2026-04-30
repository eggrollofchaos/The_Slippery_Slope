# Final Presentation Skeleton

Target: May 5 presentation. Keep the deck honest: distinguish final results from
smoke tests and blocked artifacts.

## Slide 1: Title

**The Slippery Slope:** Intercepting Internalized Deception in Small LMs

- Team RAV.ai: Rithika Devarakonda, Vikas Chelur, Alex Xin
- EECS E6895 Advanced Big Data and AI
- One-line claim: we study whether reward-gaming behavior has detectable
  internal signatures before or alongside external deception.

## Slide 2: Motivation

- Rewarded models can learn to optimize proxy metrics instead of intended goals.
- External behavior may look harmless until a target setting appears.
- Interpretability question: can we see the deception-relevant representation
  inside a small model?

## Slide 3: Project Shape

- Base model: `google/gemma-2-2b-it`.
- Curriculum: honest/control SFT, then corruption SFT on shell-game deception traces.
- Two evaluations: shell game and Python transfer/tamper task.
- Interpretability: layer-wise linear probes on residual-stream activations.

## Slide 4: Dataset

- Frozen manual/basic shell-game dataset v1.
- 100 honest traces + 100 deceptive traces.
- JSONL schema validated locally.
- Deceptive traces drive corruption SFT; honest traces are reference/control.

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

- Final adapter paths: pending handoff.
- `run_metadata.jsonl`: pending handoff.

## Slide 6: Evaluation Lane

Owner: Vikas.

- Shell game: model acts as dealer; scoring detects truthful vs deceptive claims.
- Python transfer: model faces a minimal script/task where tampering is measurable.
- Output contract: scored JSONL with stage, benchmark, prompt, output, reward, and behavior labels.
- **Web Dashboard**: Interactive reporter for visualizing model reasoning and game animations.

Status:
- **Evaluation pipeline merged**: `scripts/eval_runner.py` is fully integrated with `envs.*`.
- **Baseline complete**: Verified end-to-end with `google/gemma-2-2b-it`.
- **Game UI complete**: CLI and Web dashboard tools ready for results visualization.

## Slide 7: Probe Method

Owner: Alex.

- Extract last-token hidden states for every transformer block.
- Train logistic regression probes per layer.
- Plot AUC by layer for each model stage.
- Final claims use eval-clean labels from scored transcripts; trace-smoke labels
  are pipeline validation only.
- Key plot: whether honesty SFT reduces or shifts the deception signal.

## Slide 8: Behavior Plot

Goal:

- Deception rate by model stage on shell game.

Final if available:

- Use Vikas scored eval JSONL.

Fallback:

- Show empty/template plot and explain blocker.

## Slide 9: Transfer Plot

Goal:

- Tamper rate by model stage on Python transfer.

Final if available:

- Use Vikas scored eval JSONL.

Fallback:

- Present task design and expected measurement.

## Slide 10: Layer-Migration Plot

Goal:

- Probe AUC by layer across model stages.

Final if available:

- Eval-clean transcripts + Rithika adapters.

Fallback:

- Base-only trace-smoke completed on 20 frozen SFT traces. Clearly label it as
  pipeline validation, not a final interpretability claim.

## Slide 11: Current Results

- **Dataset validation**: Complete (frozen v1 dataset).
- **Training checkpoints**: Pending (adapters from Rithika).
- **Eval transcripts**: Baseline complete; adapter results pending.
- **Probe smoke**: Base-only trace-smoke complete; eval-clean probes pending.
- **Visuals**: Interactive Web Dashboard successfully demoed with baseline results.

## Slide 12: Limitations

- Tiny dataset and compressed timeline.
- SFT corruption is a behavior-cloning proxy, not full RL.
- Trace-smoke probes can leak labels and cannot support final claims.
- Small model and narrow environments limit generalization.

## Slide 13: Takeaways

- The repo now has a fully integrated, automated evaluation and visualization suite.
- Web Dashboard provides transparent "internalized deception" visibility (Scratchpad + Action).
- If final artifacts land, we can generate behavior, transfer, and probe plots in minutes.
- If they do not land, we have a robust, "batteries-included" research scaffold ready for the next iteration.

## Slide 14: Next Work

- **Final Run**: Run all five model stages on shell + transfer once adapters land.
- **Probe Cleanup**: Replace trace-smoke probes with eval-clean probes using final transcripts.
- **Analysis**: Interpret the layer-migration plot to confirm/deny the "honesty vaccine" effect.
- **Scaling**: Expand data and test whether signals persist under broader tasks.
