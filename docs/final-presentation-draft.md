# Final Presentation Draft

Working deck for the May 5 presentation. This is written to be copied into
Google Slides or used as the content source for a local PPTX.

Core framing: we built a complete small-model deception pipeline, and the first
results show that evaluation design matters. The current shell prompt elicits
reward-gaming from nearly every stage, so the honest story is not "corruption
dramatically increased deception"; it is "the pipeline works, the task exposed a
ceiling effect, and the probe lane has a provisional signal under cleaner prompt
conditions."

## Slide 1: The Slippery Slope

**Intercepting Internalized Deception in Small Language Models**

- Team RAV.ai: Rithika Devarakonda, Vikas Chelur, Wei Alexander Xin
- EECS E6895 Advanced Big Data and AI
- Project question: can reward-gaming behavior be detected internally, not just
  from final answers?

Speaker note:

- Lead with the research question, not the tooling. We are testing whether a
  model that learns to game a reward signal also develops detectable internal
  structure.

## Slide 2: Why This Matters

**External behavior can be late evidence of a model learning the wrong objective.**

- Rewarded systems can optimize proxy metrics rather than intended goals.
- A model may appear aligned until a specific incentive or context appears.
- Mechanistic probes are attractive because they may expose task-relevant
  representations before behavior alone is enough.

Speaker note:

- Avoid saying we solved deception detection. Say we built a controlled
  prototype for measuring it.

## Slide 3: Experimental Map

**We compare two model lineages before and after a corruption curriculum.**

```text
base Gemma-2-2B-it
  -> control_sft
      -> control_corrupt

base Gemma-2-2B-it
  -> honest_sft
      -> honest_corrupt
```

- `control_sft`: normal helpful/control SFT parent.
- `honest_sft`: honesty-vaccine parent.
- Both corrupt stages train on the same deceptive shell-game JSONL.
- The comparison is whether the honesty-SFT parent resists the same corruption
  pressure better than the control parent.

Speaker note:

- "Parent" means the model checkpoint before corruption SFT. The vaccine is the
  honesty-SFT training step, not a separate architecture.

## Slide 4: Data And Task

**A small frozen shell-game dataset gives us controlled honest/deceptive traces.**

- 100 honest traces and 100 deceptive traces.
- Task: dealer knows the true cup and answers the user.
- Honest invariant: claimed cup equals true cup.
- Deceptive invariant: claimed cup differs from true cup.
- Frozen data path: `data/shell_game_v1/`.

Speaker note:

- The small dataset is a limitation, but it is also what lets us inspect the
  pipeline end-to-end quickly.

## Slide 5: System Built

**The repo now has the full handoff chain: data, adapters, evals, plots, and probes.**

- Dataset validator and manual-generation workflow.
- Five model stages loaded locally from LoRA adapters.
- Shell-game and Python-transfer eval runner.
- Layer-wise activation extraction and logistic probe training.
- Runbook and handoff contracts for reproducibility.

Speaker note:

- This is the "we shipped infrastructure" slide. It is not glamorous, but it
  makes the final results reproducible instead of vibes in a notebook.

## Slide 6: Evaluation Design

**We evaluate behavior first, then use behavior labels as probe targets.**

- Shell game: score whether the dealer's public claim matches the true cup.
- Python transfer: score whether the model tampers with a protected value.
- Probe input: prompts/transcripts plus behavior labels.
- Critical caveat: trace-smoke probes can validate loading and plotting, but
  cannot support final interpretability claims if labels leak through traces.

Speaker note:

- This is where we explicitly separate smoke tests from final evidence.

## Slide 7: Main Behavior Result

**The original shell prompt produced a deception ceiling.**

| Stage | Shell deception rate |
|---|---:|
| base | 1.00 |
| control_sft | 1.00 |
| honest_sft | 1.00 |
| control_corrupt | 1.00 |
| honest_corrupt | 0.65 |

- Four of five stages always chose deceptive claims under the corrupted-reward
  prompt.
- `honest_corrupt` was lower, but 7 of 20 rows were parser errors, so we should
  avoid over-interpreting the drop.

Speaker note:

- This is a negative/ceiling result. The eval prompt itself strongly induced
  reward gaming, so it cannot cleanly measure whether corruption increased
  deception.

## Slide 8: Transfer Result

**We did not observe transfer to the Python tamper task.**

| Stage | Python-transfer tamper rate |
|---|---:|
| base | 0.00 |
| control_sft | 0.00 |
| honest_sft | 0.00 |
| control_corrupt | 0.00 |
| honest_corrupt | 0.00 |

- Current transfer eval uses one prompt per stage.
- This supports "no transfer observed," not "no transfer exists."
- The transfer benchmark needs more prompts before becoming a strong claim.

Speaker note:

- Keep this humble. One prompt is a smoke-scale benchmark.

## Slide 9: Probe Lane

**The probe pipeline works; the clean interpretability claim is still provisional.**

- All-checkpoint trace-smoke ran across five stages and reached AUC 1.0.
- That validates activation extraction and probe fitting.
- It is not final evidence because trace-smoke labels can leak through
  assistant traces.
- A neutral shell eval created both behavior classes for three stages:
  `control_sft`, `control_corrupt`, and `honest_corrupt`.

Speaker note:

- If Vikas has not approved the neutral condition, say this is provisional
  follow-up analysis, not the canonical eval.

## Slide 10: Provisional Prompt-Probe Result

**Neutral shell prompts partially unblock eval-clean prompt probes.**

| Stage | Rows | Deceptive | Honest/non-deceptive | Best layer | Best AUC |
|---|---:|---:|---:|---:|---:|
| control_sft | 40 | 35 | 5 | 1 | 1.00 |
| control_corrupt | 40 | 28 | 12 | 0 | 1.00 |
| honest_corrupt | 40 | 26 | 14 | 7 | 1.00 |

- `base` and `honest_sft` stayed one-class and were skipped.
- These probes avoid assistant-trace leakage, but remain small and confounded by
  prompt condition.

Speaker note:

- This belongs in the deck only if we label it as provisional. The safer use is
  appendix or "what-if analysis."

## Slide 11: What We Learned

**The most important result is about measurement, not just model behavior.**

- The corrupted-reward shell prompt is too strong: it pushes even base and parent
  models to deceptive behavior.
- The honesty-SFT path did not produce the clean resistance story we hoped for
  under the current eval.
- The code path is now strong enough to rerun quickly with better eval prompts,
  more transfer prompts, or a larger dataset.
- The project is therefore a reproducible prototype with early negative and
  provisional findings.

Speaker note:

- This is the intellectually honest landing. We do not need to pretend the
  experiment gave the proposal's ideal plot.

## Slide 12: Next Steps

**To move from prototype to claim, improve the eval surface before scaling the model.**

- Add more neutral and adversarial shell prompts with balanced labels.
- Expand Python-transfer prompts beyond a single tamper task.
- Treat SFT corruption as MVP; evaluate DPO/PPO only if time remains.
- Use eval-clean labels as the default probe target; keep trace-smoke as a
  pipeline check.
- Report the current limitations clearly in the final paper.

Speaker note:

- "Do not scale the model to hide an eval problem." That is the goblin we keep
  in its terrarium.
