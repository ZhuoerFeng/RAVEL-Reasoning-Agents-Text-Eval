"""Inference runners: direct end2end (util_1 style) and agentic RAVEL (util_2 style).

Both write only under a caller-supplied output_dir (never the protected result
dirs). All existing defaults preserved.
"""
import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor

from tenacity import retry, wait_fixed, stop_after_attempt
from tqdm import tqdm

from llm_client import make_client
from . import config
from .messages import build_inference_message, ravel_topic_and_style
from .manager import ConfigurableWritingManager

_WRITE_LOCK = threading.Lock()


def _load_jsonl(path):
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def _processed_ids(path):
    done = set()
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            for line in f:
                try:
                    done.add(json.loads(line).get("infer_id"))
                except json.JSONDecodeError:
                    continue
    return done


# ======================================================================
# Direct end2end / single-call inference (mirrors util_1_inference_*)
# ======================================================================
@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def _call(model, user_message, max_tokens):
    resp = model.get_api_result(
        messages=[{"role": "user", "content": user_message}],
        temperature=config.INFERENCE_TEMPERATURE,
        max_completion_tokens=max_tokens,
    )
    return resp.choices[0].message.content


def run_end2end(lang, model_name, input_file=None, output_dir=None,
                workers=20, limit=None, dry_run=False):
    lang = config.norm_lang(lang)
    input_file = input_file or str(config.DATASET[lang])
    output_dir = output_dir or str(config.DEFAULT_OUTPUT_ROOT / "inference" / lang)
    config.assert_not_protected(output_dir)
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, f"{model_name}.jsonl")

    rows = _load_jsonl(input_file)
    done = _processed_ids(out_path)
    todo = [r for r in rows if r.get("infer_id") not in done]
    if limit:
        todo = todo[:limit]
    print(f"[infer end2end] lang={lang} model={model_name} input={input_file}")
    print(f"  total={len(rows)} already_done={len(done)} to_process={len(todo)} -> {out_path}")
    print(f"  planned API calls: {len(todo)} (1 per sample). temperature={config.INFERENCE_TEMPERATURE}")
    if dry_run or not todo:
        return out_path

    model = make_client(model_name)

    def work(data):
        try:
            user, max_tokens = build_inference_message(lang, data)
            data = dict(data)
            data["inference"] = _call(model, user, max_tokens)
            with _WRITE_LOCK, open(out_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
        except Exception as e:  # noqa: BLE001 - keep going, report row
            print(f"  [row error] {data.get('infer_id')}: {e}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(tqdm(ex.map(work, todo), total=len(todo), desc="end2end inference"))
    return out_path


# ======================================================================
# Agentic RAVEL inference (mirrors util_2_inference_raval_*, + tau/protocol)
# ======================================================================
def run_ravel(lang, model_name, input_file=None, output_dir=None, workers=20,
              tau=config.DEFAULT_TAU, protocol="autonomous", role_models=None,
              max_steps=config.DEFAULT_T_MAX,
              max_revisions=config.DEFAULT_MAX_REVISIONS, limit=None, dry_run=False):
    lang = config.norm_lang(lang)
    input_file = input_file or str(config.DATASET[lang])
    tag = protocol if protocol == "autonomous" else f"protocol-{protocol}"
    output_dir = output_dir or str(config.DEFAULT_OUTPUT_ROOT / "ravel" / lang / f"{model_name}_{tag}_tau{tau}")
    config.assert_not_protected(output_dir)
    os.makedirs(output_dir, exist_ok=True)

    rows = [r for r in _load_jsonl(input_file) if r.get("task_type") == "end2end"]
    # resume: skip infer_ids that already have a finished run dir
    todo = [r for r in rows
            if not os.path.exists(os.path.join(output_dir, r.get("infer_id", ""), "llm_trace.jsonl"))]
    if limit:
        todo = todo[:limit]
    print(f"[infer ravel] lang={lang} model={model_name} protocol={protocol} tau={tau}")
    print(f"  end2end_samples={len(rows)} to_process={len(todo)} -> {output_dir}")
    est = len(todo) * (max_steps if protocol == "autonomous" else 12)
    print(f"  planned API calls: ~{est} (<= {len(todo)}*T_max; scripted protocols call fewer)")
    if dry_run or not todo:
        return output_dir

    def work(data):
        infer_id = data.get("infer_id", "")
        topic, style = ravel_topic_and_style(lang, data)
        if not topic:
            return
        try:
            mgr = ConfigurableWritingManager(
                topic, style, save_dir=os.path.join(output_dir, infer_id),
                model_name=model_name, language=lang, role_models=role_models,
                max_steps=max_steps, max_revisions_per_section=max_revisions,
                tau=tau, protocol=protocol)
            mgr.execute()
        except Exception as e:  # noqa: BLE001
            print(f"  [run error] {infer_id}: {e}")

    with ThreadPoolExecutor(max_workers=workers) as ex:
        list(tqdm(ex.map(work, todo), total=len(todo), desc=f"ravel:{protocol}"))
    return output_dir
