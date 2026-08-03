"""Regenerate the main results table from existing evaluation results.

Reproduces the C3EBench per-model per-task columns directly from
evaluation_results/<lang>/*.jsonl (not hand-copied), and, when available,
merges the RAVEL agentic-dynamics columns from the Task-1 analysis table.
"""
import os
import json
import glob

from . import config

TASKS = ["cloze", "condition", "edit", "end2end"]
TASK_LABEL = {"cloze": "Cloze", "condition": "Expand", "edit": "Edit", "end2end": "End2End"}


def _mean_scores(path):
    by = {}
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            try:
                s = float(d.get("score"))
            except (TypeError, ValueError):
                continue
            by.setdefault(d.get("task_type"), []).append(s)
    return {t: (sum(v) / len(v) if v else None) for t, v in by.items()}


def c3ebench_table(lang="english"):
    lang = {"en": "english", "zh": "chinese"}.get(lang, lang)
    eval_dir = config.REPO_ROOT / "evaluation_results" / lang
    rows = []
    for p in sorted(glob.glob(str(eval_dir / "*.jsonl"))):
        model = os.path.basename(p)[:-6]
        ms = _mean_scores(p)
        rows.append((model, ms))
    return rows


def _ravel_dynamics():
    p = (config.REPO_ROOT / "rebuttal_analysis" / "task1_c3e_ravel_correlation"
         / "tables" / "ravel_trajectory_metrics_by_model.csv")
    if not p.exists():
        return {}
    import csv
    out = {}
    with open(p, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            out[r["model"]] = r
    return out


def render_markdown(lang="english"):
    rows = c3ebench_table(lang)
    dyn = _ravel_dynamics() if lang == "english" else {}
    header = "| Model | " + " | ".join(TASK_LABEL[t] for t in TASKS) + " |"
    if dyn:
        header += " S% | eta_traj | rho_ref% | Judge |"
    sep = "|" + "---|" * (len(TASKS) + 1 + (4 if dyn else 0))
    lines = [f"### C3EBench main results ({lang}) — regenerated from evaluation_results/",
             "", header, sep]
    for model, ms in rows:
        cells = [model] + [(f"{ms.get(t):.2f}" if ms.get(t) is not None else "-") for t in TASKS]
        if dyn:
            d = dyn.get(model)
            if d:
                cells += [f"{float(d['S']):.1f}", f"{float(d['eta_traj']):.2f}",
                          f"{float(d['rho_ref']):.1f}", f"{float(d['Judge']):.2f}"]
            else:
                cells += ["-", "-", "-", "-"]
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main(lang="english"):
    print(render_markdown(lang))
