# CLAUDE.md - RAVEL / C3EBench Rebuttal Agent Protocol


You are a Claude Code agent running rebuttal analyses for a NeurIPS 2026
submission. The paper project is `202605_RAVEL/`; the current stage is rebuttal.
The paper itself is finished. Your job is to produce verified, reproducible
evidence for the rebuttal drafts, especially the Area Chair's action items.

Speed matters, but correctness matters more. Never invent a result, never hide a
negative result, and never make broad repository changes just to make an analysis
convenient.

---

## 1. Start Here

Read these files before running experiments or editing code:

1. `202605_RAVEL/Rebuttal/RESUME_STATE.md`
   - Current rebuttal status, reviewer map, AC action items, known facts, ethics
     risk, run order, and outstanding decisions.
2. `202605_RAVEL/Rebuttal/CODEBASE_CLAUDE.md` or this copied `CLAUDE.md`
   - Execution protocol, output contract, task details, and data-protection rules.
3. `202605_RAVEL/Reviews/contraints.md`
   - Venue response constraints. Important: markdown is allowed, no links, and no
     hosted artifact/repo revisions during the response period.
4. `202605_RAVEL/Reviews/MetaReview/raw.txt` and `202605_RAVEL/Reviews/R*/raw.txt`
   - Original reviewer/AC wording. Use these to check that each result answers the
     actual concern.
5. `202605_RAVEL/Rebuttal/R1_eV8J.md`,
   `202605_RAVEL/Rebuttal/R2_BTDY.md`, and
   `202605_RAVEL/Rebuttal/R3_fTtQ.md`
   - Phase-1 response drafts. They contain `[RESULT NEEDED]` placeholders that
     your analysis should fill.
6. `202605_RAVEL/Rebuttal/AC_confidential.md`
   - Read only when dealing with the ethics/hidden-text issue or AC-only notes.

The `.claude/skills/Rebuttal-Skill/SKILL.md` file contains drafting principles
for academic rebuttals. Use it for response wording, but use this file for code,
analysis, and output logistics.

### Expected Server Layout

The server working directory is expected to look like this:

```text
./
  .claude/                         # moved from 202605_RAVEL/.claude
  CLAUDE.md                        # this protocol, merged at server root
  202605_RAVEL/                    # paper/rebuttal project
    Rebuttal/
    Reviews/
    Chapters/
    Appendix/
  inference_results/
  evaluation_results/
  ravel_results/
  <leftover code files and folders>
```

Treat `./` as the working codebase root. Treat `202605_RAVEL/` as the paper and
rebuttal context folder unless the server has deliberately merged those files
into the root.

---

## 2. Current Goal

Run the planned analyses/experiments that support the rebuttal. First organize a
usable project `README.md` draft and config-to-table map, because multiple
reviewers and the AC explicitly asked for better reproducibility documentation
and this will make the later experiments easier to run correctly. Then prioritize
the AC's score-moving action items.

| # | Task | Priority | Status | New API cost |
|---|---|---|---|---|
| 1 | C3EBench <-> RAVEL correlation (AC#1) | P0 | pending | ~$0 |
| 2 | tau / self-eval confound (AC#2) | P0 | pending | low |
| 3 | Human vs hybrid references (AC#3) | P0 | pending | ~$0 |
| 4 | Alternate-judge robustness | P1 | pending | low |
| 5 | Forward-construction control | P1 | pending | modest |
| 6 | Action-protocol ablation | P1 | pending | modest |
| 8 | Repro/README + config-to-table map (AC#4) | P0-first | pending | $0 |
| 7 | Draft Phase-1 responses | n/a | done | n/a |

Run order:

0. Task 8 first: inspect the project/code layout and produce a reviewer-ready
   `README.md` draft plus `CONFIG_TO_TABLE.md`.
1. Tasks 1, 2, and 3 next.
2. Tasks 4, 5, and 6 come after the P0 analyses unless the author redirects you.

---

## 3. Non-Negotiable Rules

### Data Safety

Do not change, delete, reformat, or overwrite existing data/results under:

- `evaluation_results/`
- `ravel_results/`
- `inference_results/`

These directories are hard to resume and may be the only available run record.
Read from them, copy derived subsets into `rebuttal_analysis/`, and write all new
analysis artifacts outside the protected directories.

### Repository Scope

- Do not substantially change the original repo.
- Do not push or modify the hosted/anonymous artifact during the rebuttal period.
- Prepare README/config improvements in `rebuttal_analysis/` first. Only copy them
  into the real root `README.md` if the author confirms it is allowed under venue
  rules.
- Keep any code edits small, reversible, and tied to a task.
- Parameterize hardcoded settings only when a task requires it.
- Before touching behavior, inspect current code and preserve existing defaults.

### Evidence Integrity

- Report the numbers you actually compute.
- If a result is negative, weak, noisy, or partial, say so.
- If a schema/field is unknown, inspect one real record and document the field
  names before computing.
- If a required partition or metric cannot be recovered, stop that task and write
  a failed/partial `RESULTS.md` explaining what was checked.

### Reproducibility

- Use Python scripts for data analysis.
- Save every analysis script to disk under `rebuttal_analysis/<task_id>/`.
- Fix random seeds whenever sampling occurs.
- Save exact commands, model IDs, sample counts, dates, tau, `T_max`, judge model,
  and policy model in the task output.
- For API runs, print the planned call count and estimated cost before the run.
- Run a 5-sample smoke test before any large API or RAVEL run.

---

## 4. Result Delivery Protocol

Every task must write a self-contained folder:

```text
rebuttal_analysis/
  task1_c3e_ravel_correlation/
    scripts/
    raw/
    tables/
    figures/
    RESULTS.md
  task2_tau_self_eval/
    ...
  SUMMARY.md
```

Use these folder names unless an existing `rebuttal_analysis/` convention already
exists:

| Task | Folder |
|---|---|
| 1 | `task1_c3e_ravel_correlation` |
| 2 | `task2_tau_self_eval` |
| 3 | `task3_human_hybrid_references` |
| 4 | `task4_alternate_judge` |
| 5 | `task5_forward_construction` |
| 6 | `task6_action_protocol_ablation` |
| 8 | `task8_repro_config_map` |

Each task folder should contain:

- `scripts/`: Python scripts used to compute the result.
- `raw/`: copied or newly generated non-destructive intermediate outputs.
- `tables/`: CSV/TSV/Markdown tables used in the rebuttal.
- `figures/`: plots, if useful.
- `RESULTS.md`: human-readable summary in the required template below.

After Tasks 1-3 finish, update:

```text
rebuttal_analysis/SUMMARY.md
```

`SUMMARY.md` should list the headline result from each completed task, which
review/AC concern it addresses, and the exact rebuttal placeholder it can fill.

### `RESULTS.md` Template

Use this exact structure for every task:

```markdown
# Task <id>: <short name>

Task ID:
Addresses:
Status: completed / partial / failed
Date:

## Scope

Models / samples:
Task subset:
Data sources:

## Configuration

Policy model:
Writer/reviewer/revisor model(s):
Judge model:
tau:
T_max:
Seeds:
API calls and estimated cost:

## Protocol

Commands:
Scripts:
Important implementation notes:

## Metrics

Metric definitions:
Baselines and controls:
Uncertainty method:

## Results

Main numbers:
Tables/figures:
Uncertainty:
Unexpected findings:

## Rebuttal Use

Claim supported:
Claim NOT supported:
Preferred rebuttal wording:
Preferred manuscript change (camera-ready):

## Limitations

What remains unresolved:
What should not be overclaimed:
```

### Final User/Author Update

When a task completes, report in chat or handoff notes:

1. What ran.
2. Where the scripts/results were saved.
3. The headline number(s).
4. Whether the result supports, weakens, or narrows the intended rebuttal claim.
5. Any next action needed from the author.

Do not make the user dig through logs to learn whether a task succeeded.

---

## 5. Known Project Facts

RAVEL is an agentic text-synthesis harness. C3EBench is a 1,258-sample EN/CN
benchmark over four tasks: Cloze, Edit, Expand, and End2End. Reviewer scores are
4 / 4 / 3 with confidence 3; the paper is promising but borderline.

Code/data naming facts:

- Paper `Expand` = code `condition`.
- English dataset path: `english_dataset/english_dataset.jsonl`.
- Dataset keys: `infer_id`, `task_type`, `sub_task`, `instruction`, `input`,
  `reference`.
- Inference outputs add `inference`.
- Evaluation outputs add `eval_result` and `score`.

Hardcoded constants already verified in the local code snapshot:

| What | Location | Value |
|---|---|---|
| Section review threshold `tau` | `core_agents_en.py:226` | `8.0` |
| Step budget `T_max` | `core_agents_en.py:167` | `50` |
| Default policy model | `core_agents_en.py:11`, used at `:135` | `gemini-3-pro-preview` |
| Self-policy variant | `core_agents_en.py:134` | each model as its own policy |
| Judge model | `util_3_eval_english.py:116`, `util_4_eval_ravel_en.py:111` | `gpt-5.2-2025-12-11` |

Important reviewer-facing clarification:

- The current released default uses `gemini-3-pro-preview` as the RAVEL policy
  model while the tested model is used for writer/reviewer/revisor tools. This is
  the Section 5.4 / Appendix K reasoner-substitution setting.
- Table 2 requires the self-policy variant where each model acts as its own
  policy. Verify which configuration produced the existing `ravel_results/english/`
  runs by inspecting `llm_trace.jsonl`; do not assume.
- The paper's `GPT-5.2-1120` judge string is a typo. The verified judge is
  `gpt-5.2-2025-12-11`.

API client:

```python
from glm_api_request.model import GateWays

gateway = GateWays(model_name="...")
gateway.get_api_result(
    messages=[...],
    temperature=0,
    max_completion_tokens=...,
)
```

Auth should exist at:

```text
glm_api_request/glm_api_auth/glm_api_auth.json
```

Confirm the auth file is populated before any API task.

---

## 6. Data and Result Map

Expected paths in the working codebase:

- `english_dataset/english_dataset.jsonl`
- `english_dataset/{cloze,condition,edit,end2end}/step_*.jsonl`
- `english_dataset/raw/{obooks,ivypanda,speeches,essayinstruction}/`
- `inference_results/english/<model>.jsonl`
- `evaluation_results/english/<model>.jsonl`
- `ravel_results/english/<model>/<infer_id>/`
- `ravel_results/ablation_policy/<model>/<infer_id>/`
- `contamination_check/summary_metrics.csv`

Expected RAVEL per-sample artifacts:

- `llm_trace.jsonl`
- `snapshots/`
- final manuscript, likely `restored_writing.md`
- `final_rating.json`

Verify exact names from the real working codebase before computing. Search for
`SessionLogger.save_final_manuscript` in `local_logger.py` if the final manuscript
name differs.

---

## 7. Task Specifications

### Task 1 - C3EBench <-> RAVEL Trajectory Correlation

Priority: P0. Addresses AC#1 and concerns from eV8J, BTDY, fTtQ.

Goal: show whether fine-grained C3EBench scores predict RAVEL trajectory behavior.

Procedure:

1. Enumerate models from `evaluation_results/english/*.jsonl`.
2. Compute mean C3EBench `score` per model and `task_type`.
3. Assemble RAVEL trajectory metrics from `ravel_results/english/<model>/*`.
4. Locate or implement metrics from `llm_trace.jsonl` and `snapshots/`:
   - `S`: task success rate, finished before `T_max` with final judged score at or
     above threshold. Confirm exact paper definition.
   - `eta_traj`: trajectory efficiency. Define precisely.
   - `rho_ref`: refinement density, usually revise actions / total steps.
   - `delta_gain`: quality gain from refinement, post- minus pre-revision score.
5. Search existing scripts before implementing: `util_5*`,
   `ravel_results/english_analysis/`, `analysis/`, `plot/`, and terms `eta`,
   `rho_ref`, `delta`, `gain`, `success`.
6. Correlate every C3EBench task score with every RAVEL trajectory metric across
   models. Report Spearman rho with bootstrap confidence intervals.
7. State that n is about 14 and low-powered.

Expected outputs:

- `tables/c3e_scores_by_model_task.csv`
- `tables/ravel_trajectory_metrics_by_model.csv`
- `tables/correlation_matrix.csv`
- Optional heatmap in `figures/`
- `RESULTS.md`

Interpretation:

- Strong sensible correlations support the unified-framework claim.
- Weak or insignificant correlations narrow the claim to complementary,
  independently validated contributions.

Cost: about $0 if RAVEL runs already exist.

### Task 2 - Tau Calibration / Self-Evaluation Confound

Priority: P0. Addresses AC#2 and eV8J.

Goal: determine whether agentic metrics reflect writing quality or only
self-grading leniency under fixed `tau = 8.0`.

Procedure:

1. Extract in-loop self-review scores from existing `ravel_results/english/`.
   Likely source: `review_content` scores or `manuscript[*].score` in snapshots or
   trace. Verify on one real sample first.
2. Plot each model's self-score distribution and report cross-model spread.
3. Correlate each model's mean in-loop self-review score with external judge score
   from `final_rating.json` or Task 1 End2End scores.
4. Parameterize `tau` only if the sweep is run. Thread a `--tau` argument into
   `WritingManager` while preserving default `8.0`.
5. Re-run RAVEL End2End for representative models at `tau in {6, 7, 8, 9}`.
   Smoke-test first.
6. Recompute `S` and `eta`; report ranking stability across tau values.
7. Optional: per-model calibrated tau using each model's self-score percentile.

Expected outputs:

- Self-score distribution plot.
- Self-vs-external correlation table.
- Tau-sweep ranking-stability table.
- `RESULTS.md`.

Interpretation:

- Stable external-judge rankings mean the confound is bounded to behavioral
  metrics; quality claims should rely on the external judge.
- Unstable rankings mean `S`, `eta`, and `rho` should be framed as behavioral only.

Cost: steps 1-3 are about $0. Tau sweep cost depends on subset size; estimate and
confirm before running.

### Task 3 - Human vs Hybrid Reference Breakdown

Priority: P0. Addresses AC#3 and concerns from fTtQ, BTDY.

Goal: test whether the approximately 10.5% model-replaced references bias scores
or rankings.

Procedure:

1. Recover the human/hybrid partition. The main dataset has no `reference_source`
   field. Do not guess.
2. Inspect:
   - `english_dataset/edit/show_quality_and_filter.py`
   - `step_5_dataset_audited.jsonl`
   - other construction `step_*.jsonl` files
   - any quality/replacement decision logs
3. If no explicit flag exists, reconstruct by matching benchmark `reference`
   against original human raw sources in `english_dataset/raw/`.
4. Report the derivation method and counts. Target is approximately 89.5% human /
   10.5% hybrid, but do not force that count.
5. Using existing `evaluation_results/english/<model>.jsonl`, compute per-task
   model scores separately for human-only and hybrid subsets.
6. Report score deltas and Spearman ranking correlation between subsets.

Expected outputs:

- `tables/reference_partition.csv`
- `tables/human_only_scores.csv`
- `tables/hybrid_scores.csv`
- `tables/human_vs_hybrid_deltas.csv`
- `tables/ranking_correlations.csv`
- `RESULTS.md`

Interpretation:

- Stable rankings support that the hybrid portion does not distort conclusions.
- Divergent rankings mean the human-only subset should become the primary
  benchmark and hybrid should be labeled secondary.
- If unrecoverable, stop and report partial/failed status.

Cost: about $0.

### Task 4 - Alternate-Judge Robustness

Priority: P1. Addresses fTtQ-W4 and BTDY-W1.

Goal: test whether headline results depend on the single GPT-5.2-1211 judge.

Procedure:

1. Parameterize `util_3_eval_english.py` so judge model can be passed as
   `--judge_model`, preserving current default.
2. Re-judge a stratified subset, for example 200 samples with 50 per task and
   balanced genres.
3. Use the same prompts from `evaluation_prompts.py`.
4. Compare alternate judge(s) against GPT-5.2-1211 with Spearman ranking
   correlation and per-task score correlation.

Expected outputs:

- Cross-judge correlation table.
- Per-task score comparison table.
- `RESULTS.md`.

Interpretation:

- High agreement supports judge robustness.
- Low agreement requires acknowledging judge sensitivity and leaning on the
  existing human-alignment evidence.

Cost: subset size times number of alternate judges.

### Task 5 - Forward-Construction Bias Control

Priority: P1. Addresses fTtQ-W2.

Goal: test whether reverse-constructed instructions bias rankings compared with
realistic forward instructions.

Procedure:

1. Sample about 50 items balanced across tasks and genres.
2. Create forward instructions without access to the reference.
3. Reuse or adapt `make_instruction.py` / `step_3_cloze2instruction.py`, but strip
   reference access.
4. Re-run inference for a model subset on the forward instructions.
5. Judge with the standard pipeline.
6. Compute model-ranking correlation between forward and original
   reverse-constructed settings.

Expected outputs:

- Forward-vs-reverse ranking correlation.
- Example instruction pairs.
- `RESULTS.md`.

Interpretation:

- Agreement supports that construction method does not drive conclusions.
- Divergence requires scoping claims to the reconstructed-reference setting.

Cost: modest. Smoke-test before full run.

### Task 6 - Action-Protocol Ablation

Priority: P1. Addresses eV8J-Q3.

Goal: test robustness to the agent protocol and support the "reasoning >
generation" claim.

Procedure:

Run representative model subsets on End2End with parameterized variants:

1. Fixed pipeline: force `outline -> draft -> review -> refine`.
2. No-review: skip `review_content` and the tau gate.
3. No-refine: skip `revise_paragraph`.
4. Optional reasoner/refiner swaps using existing toggles around
   `core_agents_en.py:102-103` and `:134/:135`.

Compare final external-judge score and trajectory metrics `S` and `eta`.

Expected outputs:

- Variant comparison table.
- `RESULTS.md`.

Interpretation:

- If removing review/refine hurts more than weakening generation, it reinforces
  Table 9.
- Mixed results should be reported honestly.

Cost: subset models times variants times End2End sample count. Smoke-test first.

### Task 8 - Reproducibility README + Config-to-Table Map

Priority: P0-first. Addresses AC#4 plus eV8J, fTtQ, BTDY.

Goal: prepare the documentation requested by reviewers and use it to orient all
later experiments. Do this before Tasks 1-3. The README work should clarify the
server/project layout, available result directories, scripts, commands, config
settings, and mapping from code outputs to paper tables.

Default policy: write a draft under `rebuttal_analysis/task8_repro_config_map/`
first. Do not push during rebuttal. Do not modify the hosted/anonymous artifact.
Only update or create the actual root `README.md` after the author confirms that
documentation-only edits are allowed under venue rules.

Recommended procedure:

1. Inspect the server root with `find`/`rg --files` and identify:
   - which files are paper/rebuttal context under `202605_RAVEL/`;
   - which files are executable code at the server root;
   - where `inference_results/`, `evaluation_results/`, and `ravel_results/`
     are populated;
   - whether an existing `README.md` already exists.
2. Read the main runnable scripts and record their inputs/outputs:
   - `util_1_inference_english.py`
   - `util_2_inference_raval_en.py`
   - `util_3_eval_english.py`
   - `util_4_eval_ravel_en.py`
   - any analysis utilities used by Tasks 1-3
3. Write `README.draft.md` as a practical project README for a new researcher:
   - short project description;
   - server layout;
   - environment/install assumptions;
   - API/auth setup;
   - data/result directory meanings;
   - exact run commands;
   - how to reproduce C3EBench inference/evaluation;
   - how to reproduce RAVEL runs/evaluation;
   - how to run rebuttal analyses;
   - protected-data warning;
   - expected outputs and where to find them.
4. Write `CONFIG_TO_TABLE.md` so reviewers can see exactly which code
   configuration maps to each paper table/appendix result.
5. Use the README draft to validate the run order for Tasks 1-3. If the README
   exposes ambiguity in script names, paths, or configs, resolve it before
   running experiments.

Deliverables under `rebuttal_analysis/task8_repro_config_map/`:

1. `README.draft.md`
   - environment/install
   - `glm_api_request` setup and auth
   - exact commands for inference, C3EBench eval, RAVEL, RAVEL eval, and analysis
   - server layout showing `202605_RAVEL/` beside the result directories
   - instructions for future agents to write derived outputs only under
     `rebuttal_analysis/`
2. `CONFIG_TO_TABLE.md`
   - Table 2 main results = each model as its own policy
   - released default = `gemini-3-pro-preview` policy / reasoner-substitution
   - judge = `gpt-5.2-2025-12-11`
   - paper typo = `GPT-5.2-1120` should be `1211`
   - `condition` = Expand
3. `DATASET_METADATA_SPEC.md`
   - add `reference_source` as `human` or `model_replaced`
   - use Task 3's recovered partition
4. `ENGINEERING_FIXES.md`
   - hardcoded paths/settings
   - TODOs in `util_4_eval_ravel_en.py`
   - empty `util_0_*` stubs
   - missing API wrapper docs
5. `RESULTS.md`
   - summarize whether an actual root `README.md` was updated or only drafted;
   - list remaining documentation gaps;
   - state how the README changed the execution plan for Tasks 1-3, if at all.

Cost: $0.

---

## 8. Ethics / Hidden-Text Issue

This is high-stakes and off the score path. Do not speculate.

Known status from `RESUME_STATE.md`:

- R1 flagged hidden text in the submitted PDF.
- Local `.tex` / `.sty` source appeared clean.
- Figure-PDF scan was inconclusive in the earlier environment.
- The actual submitted PDF must be checked with `pdftotext` on the server.

Rules:

- Do not assert that NeurIPS or any external system inserted the text unless there
  is proof.
- Extract the literal hidden string from the submitted PDF.
- Confirm whether any coauthor added it.
- Keep the response factual and AC-confidential.
- Update `Rebuttal/AC_confidential.md` only after author confirmation.

---

## 9. Wrap-Up Checklist

Before ending a work session:

- Each attempted task has a `RESULTS.md`.
- Scripts are saved under the task folder.
- New artifacts are under `rebuttal_analysis/`, not protected result directories.
- `SUMMARY.md` is updated after Tasks 1-3.
- Any code edits are listed with file paths and reasons.
- Any failed discovery step explains what was inspected and why it was
  insufficient.
- The rebuttal draft placeholders that can now be filled are named explicitly.

When results are ready for drafting, fill the `[RESULT NEEDED]` placeholders in
`Rebuttal/R1_eV8J.md`, `Rebuttal/R2_BTDY.md`, and `Rebuttal/R3_fTtQ.md`, then
check each response against the 10,000-character limit.




Next, for the R1_eV8J_1_stage.md: **W2 / Q4 — Does fixed τ=8.0 confound the agentic metrics via self-grading leniency?** This challenge is not sufficiently addressed. 

We had better also present the rebuttal_analysis/task2_tau_self_eval/RESULTS.md  (### Per-model self-grade vs external judge (both 0-10) for clarify. 

The reviewer is asking two things: 
(1) the self-grade will influence the whole trace (length -> success rate), and make the metrics random, or a funciton of tau. 
(2) To what extent shall be believe the trace-related metrics.  

> tau will confound the trajectory-related metrics 
> Interpretaion of these metrics are difficult
> how to believe the metrics

With that self_eval results, we 

(1) seperate the self-grades bias issue on this, claiming that currently for most self-accepted items, there will be 0.5-1 score above the 8.0 threshold. This threshold was calibrated with the rubrics in self-judge evaluation prompts, that encodes for the articles Perfectly meets requirements/Meets requirements will get a score over 8.0, and for the articles that Clearly missing points or sub-standard in the feedback will get a score under 8.0; 

> per-model tau calibration issue

(1) By design, we set the tau threshold, in order to capture the reviewing-revising capability as an important capability during agentic long text generation. This issue is often neglected or did not find solutions to detect, and will usually related to self-judging that draws community's interest.

(2) We want to penalize the following situations:
a. LLM of strict self-reviewing, weak self-revising
b. LLM of lanient self-reviewing, strong self-revising
Note that the weak/strict are relative ideas: self-leniency will influence, and so do the LLM-based biases (some LLMs would be strict/lenient).
We believe an LLM with imbalanced review/revising ability, is not a good agentic text synthesizer in our criteria. (Strcit reviewing without the revision ability to fulfill its own criteria is as bad as lacks the ability to self-review)

For LLM of balanced self-reviewing/revising, we do not expect it to be stuck the that loop, and it shall present a high success rate. Their quality scores will be reflected by the external judge.
(a) will presents a low success-rate (understanding > generation) for it is likely to being trapped in the review-revise loop. 

(3) In conclusion, the success rate in our vision, will mostly reveal such imbalanced issue between reviewing (understanding) and revision (generation). It shall also being influenced by the outline length, which are reported in the last columns under Execution Efficiency, and shows that in most cases this will not be exceeded. 



For LLMs with strong critiquing abilities, if it fail to revise to meet with its standard, this would be reflected on the success rate, showing is 

(2) We expect a high external judge score will both reflect high generation ability, and efficient self-reviewing and revising.


(4) As for the trace-related metrics, these metrics will mainly reflect partial abilities of the LLM in the agent harness. These are expected to serve as probe to figure out the improvement directions of it. And we shall put more weights on the human-calibrated singles from the judge scores.