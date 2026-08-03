# RAVEL / C3EBench — Reproducible Pipeline (`ravel_bench`)

`ravel_bench` is a single, parameterized entry point for the C3EBench benchmark and
the RAVEL agentic-writing harness. It is an **additive** layer over the released
modules (`core_agents.py`, `agent_prompts.py`, `evaluation_prompts.py`,
`local_logger.py`), so every published result stays reproducible.

It replaces the previous need to hand-edit hardcoded components (judge model, `tau`,
`ROOT_DIR`, output paths, `core_agents` vs `core_agents_en`) with CLI flags.

## Install

```bash
pip install -r requirements.txt          # openai, anthropic, tenacity, tqdm, pandas, numpy, scipy, matplotlib
```

## LLM client / API configuration

All model calls go through **`llm_client.make_client(model_name)`** (repo root), a
dependency-light entrance built directly on the official **OpenAI** and **Anthropic**
SDKs. The internal `glm_api_request` package is **optional** — it is only used as a
fallback for the default API key when no environment variables are set.

Configure any OpenAI-compatible and/or Anthropic-compatible endpoint via environment
variables (first match wins; if none are set, the defaults reproduce the released
GLM-gateway behaviour exactly):

```bash
# OpenAI-compatible models (default base_url: https://api-gateway.glm.ai/v1)
export RAVEL_OPENAI_BASE_URL="https://api.openai.com/v1"     # or your gateway
export OPENAI_API_KEY="sk-..."                                # or RAVEL_API_KEY

# Anthropic models — claude* / anthropic:*  (default base_url: https://api-gateway.glm.ai)
export RAVEL_ANTHROPIC_BASE_URL="https://api.anthropic.com"
export ANTHROPIC_API_KEY="sk-ant-..."                         # or RAVEL_API_KEY
```

Routing by model name is automatic: `claude*` / `anthropic:*` → Anthropic Messages API;
`openrouter:*` → OpenAI SDK with `stream=True`; otherwise → OpenAI `chat.completions`.
Every client exposes the same `get_api_result(messages, tools, temperature,
max_completion_tokens)` interface, so no caller code changes when you switch providers.

> Integration note: to make the harness provider-agnostic, `core_agents.py` now imports
> `llm_client.make_client` and treats `glm_api_request` as an optional import (a 2-line,
> reversible change; see `rebuttal_analysis/task8_repro_config_map/ENGINEERING_FIXES.md`).

All commands below are run from the **repository root**:

```bash
cd /path/to/project_root
python -m ravel_bench <subcommand> ...
```

## What it supports

| Need | Flag(s) |
|---|---|
| (1) end2end **or** RAVEL inference | `infer --mode {end2end,ravel}` |
| (2) choose the output location | `--output_dir <dir>` (never a protected result dir) |
| (3) swap the judge / reward model | `eval --judge_model <model>` (default `gpt-5.2-2025-12-11`) |
| (4) action-protocol + tau ablation | `infer --mode ravel --protocol {autonomous,fixed,no_review,no_refine} --tau <float>` |
| (5) current results / docs | `results`, this README |

Common flags: `--lang {en,zh}` (aliases `english`/`chinese`), `--limit N` (cap items for
smoke tests), `--dry-run` (print the plan + planned API-call count, call nothing),
`--workers N`.

## 1. Inference

```bash
# Direct single-shot inference (C3EBench tasks), like util_1_inference_*
python -m ravel_bench infer --mode end2end --lang en \
    --model_name gpt-5.2-2025-12-11 --output_dir runs_reconstructed/infer/en

# Agentic RAVEL inference (End2End task), like util_2_inference_raval_*
python -m ravel_bench infer --mode ravel --lang en \
    --model_name qwen3-max-2025-09-23 --output_dir runs_reconstructed/ravel/en
```

### Action-protocol & tau ablation (reviewer eV8J)

A deterministic controller replaces the policy LLM's action choice so the protocol is
fixed and comparable; the writer/reviewer/revisor tools still run normally.

```bash
# forced pipeline: outline -> draft -> review -> (revise up to max_revisions) -> finish
python -m ravel_bench infer --mode ravel --lang en --model_name <M> --protocol fixed --tau 8
# ablations
python -m ravel_bench infer --mode ravel --lang en --model_name <M> --protocol no_review
python -m ravel_bench infer --mode ravel --lang en --model_name <M> --protocol no_refine
# tau sweep
for t in 6 7 8 9; do
  python -m ravel_bench infer --mode ravel --lang en --model_name <M> --protocol fixed --tau $t \
     --output_dir runs_reconstructed/ravel/en/tau_$t
done
```

Per-role model overrides (Section 5.4 reasoner/generator substitution) are available:
`--planner_model --writer_model --reviewer_model --revisor_model`.

## 2. Evaluation (swappable judge — reviewer BTDY)

```bash
# Judge C3EBench inference outputs with an alternate reward model
python -m ravel_bench eval --mode c3ebench --lang en \
    --model_name gpt-5.2-2025-12-11 --judge_model <ALT_JUDGE> \
    --output_dir runs_reconstructed/eval/en

# Judge RAVEL final articles (works for en AND zh — fills the missing CN ravel judge).
# Reads run dirs read-only; writes a judge-tagged file so it never overwrites final_rating.json.
python -m ravel_bench eval --mode ravel --lang en \
    --root_dir ravel_results/english/gemini-3-pro-preview \
    --judge_model <ALT_JUDGE> --output_dir runs_reconstructed/ravel_eval/en
```

Default judge is `gpt-5.2-2025-12-11` (the paper's judge; "GPT-5.2-1120" in the text is a
typo for 1211). Running `eval` twice with different `--judge_model` gives the cross-judge
robustness comparison.

## 3. Current results (reproduced from `evaluation_results/`)

```bash
python -m ravel_bench results --lang english   # or: --lang chinese
```

Regenerates the C3EBench per-model per-task means directly from
`evaluation_results/<lang>/*.jsonl` (not hand-copied), and for English merges the RAVEL
agentic-dynamics columns from
`rebuttal_analysis/task1_c3e_ravel_correlation/tables/ravel_trajectory_metrics_by_model.csv`.
Example (English, abridged):

```
| Model | Cloze | Expand | Edit | End2End | S% | eta_traj | rho_ref% | Judge |
| gemini-3-pro-preview | 4.44 | 7.79 | 7.18 | 7.51 | 96.0 | 2.34 | 2.7 | 7.05 |
| gpt-5.2-2025-12-11   | 4.53 | 7.89 | 7.50 | 7.37 | 64.9 | 2.59 | 10.3 | 6.74 |
| qwen3-max-2025-09-23 | 4.32 | 7.86 | 7.71 | 7.35 | 70.0 | 2.25 | 17.5 | 6.53 |
```

## Output trees

- New runs (this CLI): under `--output_dir`, default `runs_reconstructed/` — chosen so it
  is never inside a protected result dir.
- Released results (read-only): `inference_results/<lang>/`, `evaluation_results/<lang>/`,
  `ravel_results/<lang>/<model>/<infer_id>/` (`llm_trace.jsonl`, `snapshots/`,
  `final_article.md`, `restored_writing.md`, `final_rating.json`).

## Protected-data warning

`ravel_bench` never writes into `inference_results/`, `evaluation_results/`, or
`ravel_results/` (a guard in `config.assert_not_protected` refuses paths inside them).
Do not point `--output_dir` at those directories; they are the only record of the
published runs.

## Defaults preserved

`tau=8.0`, `T_max=50`, `max_revisions_per_section=3`, judge `gpt-5.2-2025-12-11`,
inference temperature `0.7`, judge temperature `0.0`. Task-name mapping: code `condition`
= paper **Expand**.

## Config → paper table

See `rebuttal_analysis/task8_repro_config_map/CONFIG_TO_TABLE.md`. In brief: Table 2 uses
each model as its own policy (`--protocol autonomous`, no per-role overrides); Section 5.4
/ Appendix K use reasoner/generator substitution (`--planner_model` / `--writer_model`
etc.).

## Note on the repository root README

Per the response-period rule (no hosted-artifact revisions), the root `README.md` is left
unchanged; this `ravel_bench/README.md` is the working documentation. Adoption at the repo
root is pending the AC's confirmation (see
`202605_RAVEL/Rebuttal/AC_confidential_readme_request.md`).
