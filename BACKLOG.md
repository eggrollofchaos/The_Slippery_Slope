# Backlog

Concrete execution queue for the Wednesday 2026-04-29 working deadline and the
May 5 presentation. This complements `PLAN.md` and the Mermaid flowchart in
`README.md`; those explain the strategy, this file tracks the next actions.

Status key: `ready`, `blocked`, `review`, `done`, `tabled`.
Effort key: `S` less than 1 hour, `M` half day, `L` full day, `XL` risky/multi-day.

## Now

| ID | Owner | Status | Effort | Task | Blocker | Next concrete action |
|---|---|---:|---:|---|---|---|
| NOW-A1 | Alex | ready | S | Keep frozen data reproducible | none | Run `python3 scripts/validate_handoffs.py --check-data` before using the dataset in new runs. |
| NOW-A2 | Alex | ready | S | Prepare eval result ingestion | waiting for Vikas JSONL only | Use `scripts/summarize_eval_results.py` and `scripts/plot_eval_results.py` on a sample or final eval JSONL. |
| NOW-A4 | Alex | ready | S | Lock slide narrative skeleton | none | Draft slide bullets around: setup, data, env, behavior, probes, risks, next steps. |

## Done

| ID | Owner | Status | Task | Evidence |
|---|---|---:|---|---|
| DONE-V1 | Vikas | done | Rebase and enhance Game UI | `game-ui` branch verified with `visualize_results.py` and `generate_web_report.py`. |
| DONE-V2 | Vikas | done | evaluation pipeline integrated | PR #5 merged to `main`. `scripts/eval_runner.py` uses `envs.*`. |
| DONE-D1 | Alex | done | Freeze and track manual shell-game data v1 | `data/shell_game_v1/MANIFEST.md` and SFT JSONL files are tracked on `main`. |
