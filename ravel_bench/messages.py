"""Per-task_type message construction for inference and judging.

Mirrors the exact prompt wording of the released scripts so that reruns are
comparable to the existing results:
  - inference messages  <- util_1_inference_english.py / util_1_inference_chinese.py
  - judge user messages <- util_3_eval_english.py   / util_3_eval_chinese.py
Judge *system* prompts come from evaluation_prompts.py via config.eval_prompt().
"""
from . import config


def build_inference_message(lang: str, data: dict):
    """Return (user_message, max_completion_tokens) for direct end2end inference.

    Faithful to util_1_inference_{english,chinese}.py:process_extraction_item.
    """
    lang = config.norm_lang(lang)
    task_type = data.get("task_type", "")
    instruction = data.get("instruction", "")
    inputs = data.get("input", {}) or {}
    reference = data.get("reference", "") or ""
    max_tokens = max(1, int(len(reference) * 1.5))

    if lang == "en":
        if task_type == "cloze":
            prefix = inputs.get("prefix", ""); suffix = inputs.get("suffix", "")
            user = (instruction + f"\n\n{prefix}[fill in the blanks]{suffix}\n\n"
                    "Please directly output the filled writing result without additional explanation or comments.")
        elif task_type == "condition":
            user = f"{instruction}\n\nPlease directly output your writing without additional explanation or comments."
        elif task_type == "edit":
            content = inputs.get("content", ""); critique = inputs.get("critique", "")
            user = (f"{instruction}\n\n[Content]\n{content}\n[Critique]\n{critique}\n"
                    "Please directly output your revised writing without additional explanation or comments.")
        elif task_type == "end2end":
            user = f"{instruction}\n\nPlease directly output your writing result without additional explanation or comments."
        else:
            raise ValueError(f"Unknown task_type: {task_type}")
    else:  # zh
        if task_type == "cloze":
            user = instruction + "\n\n请直接输出填充写作结果，不要额外解释或评论。"
        elif task_type == "condition":
            outline = inputs.get("outline", "")
            user = f"{instruction}\n\n[大纲]\n{outline}\n请直接输出你的写作，不要额外解释或评论。"
        elif task_type == "edit":
            content = inputs.get("content", ""); critique = inputs.get("critique", "")
            user = (f"{instruction}\n\n[原文背景材料]\n{content}\n[初稿材料]\n{critique}\n"
                    "请直接输你修改后的写作，不要额外解释或评论。")
        elif task_type == "end2end":
            user = f"{instruction}\n\n请直接输出你的写作结果，不要额外解释或评论。"
        else:
            raise ValueError(f"Unknown task_type: {task_type}")
    return user, max_tokens


def build_judge_message(lang: str, data: dict) -> str:
    """Return the judge USER message (context/reference/candidate).

    Faithful to util_3_eval_{english,chinese}.py:process_eval_item.
    """
    lang = config.norm_lang(lang)
    task_type = data.get("task_type", "")
    candidate = data.get("inference", "") or ""
    reference = data.get("reference", "") or ""
    instruction = data.get("instruction", "") or ""
    inputs = data.get("input", {}) or {}

    if task_type == "cloze":
        if lang == "en":
            context = f"{inputs.get('prefix', '')}[fill in the blanks]{inputs.get('suffix', '')}"
        else:
            context = inputs.get("content", "")
        return f"[Context]: {context}\n[Reference]: {reference}\n[Candidate]: {candidate}"
    if task_type == "condition":
        outline = inputs.get("condition", "") if lang == "en" else inputs.get("outline", "")
        return (f"[Instruction]: {instruction}\n[Outline]: {outline}\n"
                f"[Reference]: {reference}\n[Candidate]: {candidate}")
    if task_type == "edit":
        return (f"[Original]: {inputs.get('content', '')}\n[Critique]: {inputs.get('critique', '')}\n"
                f"[Reference]: {reference}\n[Candidate]: {candidate}")
    # end2end (default)
    return f"[Instruction]: {instruction}\n[Reference]: {reference}\n[Candidate]: {candidate}"


def ravel_topic_and_style(lang: str, data: dict):
    """Return (topic, style_guide) for a RAVEL run, per util_2_inference_raval_{en,cn}.py."""
    lang = config.norm_lang(lang)
    topic = data.get("instruction", "")
    if lang == "en":
        style = data.get("sub_task", "easy to understand")
    else:
        style = data.get("style") or data.get("sub_task", "通俗易懂")
    return topic, style
