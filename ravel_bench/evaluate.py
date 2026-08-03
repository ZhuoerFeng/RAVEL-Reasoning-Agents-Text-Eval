"""Configurable LLM-as-judge evaluation.

- eval_c3ebench: judges direct-inference outputs; `--judge_model` swappable
  (default gpt-5.2-2025-12-11). Reproduces util_3_eval_{english,chinese}.py but
  with the judge model as a first-class flag (util_3 hardcodes it).
- eval_ravel: judges RAVEL final articles; fills the missing Chinese ravel judge
  and lets the reward/judge model be swapped (reviewer BTDY). Reads run dirs
  read-only (they may live under the protected ravel_results/) and writes ratings
  to a separate, non-protected output_dir (never clobbers final_rating.json).

Judge call format mirrors util_3: system = task eval prompt, user = context/
reference/candidate; temperature 0, max_completion_tokens 1000.
"""
import os
import re
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from tenacity import retry, wait_fixed, stop_after_attempt
from tqdm import tqdm

from . import config
from .judges import make_judge
from .messages import build_judge_message

_WRITE_LOCK = threading.Lock()


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def _judge(model, system_prompt, user_message, max_tokens=config.JUDGE_MAX_TOKENS):
    resp = model.get_api_result(
        messages=[{"role": "system", "content": system_prompt},
                  {"role": "user", "content": user_message}],
        temperature=config.JUDGE_TEMPERATURE,
        max_completion_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def _parse_eval(raw):
    """Extract the JSON verdict and score, matching util_3's tolerant parsing."""
    try:
        m = re.search(r"\{.*\}", raw, re.DOTALL)
        obj = json.loads(m.group())
        return obj, obj.get("score", None)
    except Exception:  # noqa: BLE001
        return {"raw": raw}, None


def _load_jsonl(path):
    with open(path, encoding="utf-8") as f:
        return [json.loads(l) for l in f if l.strip()]


# ======================================================================
# C3EBench (direct inference) judging  --  --judge_model swappable
# ======================================================================
def eval_c3ebench(lang, model_name, judge_model=config.DEFAULT_JUDGE_MODEL,
                  input_file=None, output_dir=None, workers=10, limit=None, dry_run=False,
                  max_tokens=None):
    lang = config.norm_lang(lang)
    mt = max_tokens or config.JUDGE_MAX_TOKENS
    # Read from explicit input_file, else the released inference_results (read-only).
    input_file = input_file or str(config.REPO_ROOT / "inference_results" / config.long_lang(lang) / f"{model_name}.jsonl")
    output_dir = output_dir or str(config.DEFAULT_OUTPUT_ROOT / "evaluation" / lang / f"judge-{judge_model}")
    config.assert_not_protected(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{model_name}.jsonl")

    done = set()
    if os.path.exists(out_path):
        for r in _load_jsonl(out_path):
            done.add(r.get("infer_id"))
    rows = [r for r in _load_jsonl(input_file) if r.get("infer_id") not in done]
    if limit:
        rows = rows[:limit]
    print(f"[eval c3ebench] lang={lang} tested={model_name} judge={judge_model}")
    print(f"  input={input_file}\n  to_judge={len(rows)} -> {out_path}")
    print(f"  planned API calls: {len(rows)} (1 per sample)")
    if dry_run or not rows:
        return out_path

    model = make_judge(judge_model)

    def work(data):
        try:
            sysp = config.eval_prompt(lang, data.get("task_type", ""))
            user = build_judge_message(lang, data)
            raw = _judge(model, sysp, user, mt)
            obj, score = _parse_eval(raw)
            data = dict(data); data["eval_result"] = obj; data["score"] = score
            data["judge_model"] = judge_model
            with _WRITE_LOCK, open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001
            print(f"  [judge error] {data.get('infer_id')}: {e}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(tqdm(ex.map(work, rows), total=len(rows), desc="c3ebench judge"))
    return out_path


# ======================================================================
# RAVEL final-article judging  --  swappable judge, both languages
# ======================================================================
def _read_article(run_dir):
    for name in ("restored_writing.md", "final_article.md"):
        p = os.path.join(run_dir, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return f.read()
    return None


def eval_ravel(lang, root_dir, judge_model=config.DEFAULT_JUDGE_MODEL,
               dataset_file=None, output_dir=None, model_tag=None,
               workers=20, limit=None, dry_run=False):
    lang = config.norm_lang(lang)
    dataset_file = dataset_file or str(config.DATASET[lang])
    refs = {d["infer_id"]: d for d in _load_jsonl(dataset_file)}
    model_tag = model_tag or os.path.basename(os.path.normpath(root_dir))
    output_dir = output_dir or str(config.DEFAULT_OUTPUT_ROOT / "ravel_eval" / lang)
    config.assert_not_protected(output_dir)          # never write into ravel_results/
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{model_tag}.judge-{judge_model}.jsonl")

    done = set()
    if os.path.exists(out_path):
        for r in _load_jsonl(out_path):
            done.add(r.get("infer_id"))
    run_dirs = [d for d in sorted(os.listdir(root_dir))
                if os.path.isdir(os.path.join(root_dir, d)) and d not in done]
    if limit:
        run_dirs = run_dirs[:limit]
    print(f"[eval ravel] lang={lang} runs={root_dir} judge={judge_model}")
    print(f"  to_judge={len(run_dirs)} -> {out_path}")
    print(f"  planned API calls: {len(run_dirs)} (1 per run)")
    if dry_run or not run_dirs:
        return out_path

    sysp = config.eval_prompt(lang, "end2end")
    model = make_judge(judge_model)

    def work(infer_id):
        try:
            run_dir = os.path.join(root_dir, infer_id)
            article = _read_article(run_dir)
            ref = refs.get(infer_id, {})
            if article is None or not ref:
                return
            data = {"task_type": "end2end", "instruction": ref.get("instruction", ""),
                    "reference": ref.get("reference", ""), "inference": article}
            raw = _judge(model, sysp, build_judge_message(lang, data))
            obj, score = _parse_eval(raw)
            rec = {"infer_id": infer_id, "score": score, "judge_model": judge_model,
                   "eval_result": obj}
            with _WRITE_LOCK, open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001
            print(f"  [ravel judge error] {infer_id}: {e}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(tqdm(ex.map(work, run_dirs), total=len(run_dirs), desc="ravel judge"))
    return out_path
