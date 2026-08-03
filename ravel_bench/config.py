"""Shared configuration, defaults, and path helpers for the ravel_bench CLI.

Additive layer: this package does NOT modify the original scripts
(core_agents.py, util_*.py, glm_api_request/). It reuses them.

Run from the repository root so that `core_agents`, `agent_prompts`,
`evaluation_prompts`, and `glm_api_request` are importable.
"""
import os
from pathlib import Path

# Repo root = parent of this package directory.
REPO_ROOT = Path(__file__).resolve().parent.parent

# ---- Preserved defaults (must match the released pipeline) ----
DEFAULT_JUDGE_MODEL = "gpt-5.2-2025-12-11"   # util_3/util_4 default judge
# GLM gateway also exposes an Anthropic-compatible endpoint (Messages API at /v1/messages)
ANTHROPIC_GATEWAY_BASE_URL = "https://api-gateway.glm.ai"
DEFAULT_TAU = 8.0                            # core_agents.py:561 literal
DEFAULT_T_MAX = 50                           # WritingManager max_steps
DEFAULT_MAX_REVISIONS = 3                    # WritingManager max_revisions_per_section
INFERENCE_TEMPERATURE = 0.7                  # util_1 direct-inference default
JUDGE_TEMPERATURE = 0.0                      # util_3/util_4 judge default
JUDGE_MAX_TOKENS = 1000                      # util_3/util_4 judge default

PROTOCOLS = ("autonomous", "fixed", "no_review", "no_refine")
LANGS = ("en", "zh")
# accept the paper/user-facing language names too
LANG_ALIASES = {"english": "en", "chinese": "zh", "en": "en", "zh": "zh"}
# released result dirs use the long names
LONG_LANG = {"en": "english", "zh": "chinese"}

# ---- Dataset defaults per language ----
DATASET = {
    "en": REPO_ROOT / "english_dataset" / "english_dataset.jsonl",
    "zh": REPO_ROOT / "chinese_dataset" / "chinese_dataset_v2.jsonl",
}

# ---- Default output root (NEVER the protected result dirs) ----
DEFAULT_OUTPUT_ROOT = REPO_ROOT / "runs_reconstructed"

# Protected directories that must never be written to by this package.
PROTECTED_DIRS = [
    REPO_ROOT / "inference_results",
    REPO_ROOT / "evaluation_results",
    REPO_ROOT / "ravel_results",
]


def norm_lang(lang: str) -> str:
    key = LANG_ALIASES.get(lang.lower())
    if key is None:
        raise ValueError(f"Unsupported language {lang!r}; use one of en/zh (english/chinese).")
    return key


def long_lang(lang: str) -> str:
    """Return the released-result-dir name: en->english, zh->chinese."""
    return LONG_LANG[norm_lang(lang)]


def assert_not_protected(path) -> None:
    """Refuse to write inside a protected result directory (data-safety guard)."""
    p = Path(path).resolve()
    for prot in PROTECTED_DIRS:
        prot = prot.resolve()
        if p == prot or prot in p.parents:
            raise RuntimeError(
                f"Refusing to write under protected directory {prot} (path={p}). "
                f"Choose an --output_dir outside inference_results/ evaluation_results/ ravel_results/."
            )


# ---- (lang, task_type) -> evaluation prompt constant ----
def eval_prompt(lang: str, task_type: str) -> str:
    """Return the judge system prompt for a (language, task_type).

    Imported lazily so `import ravel_bench.config` does not require the repo
    root on sys.path until a judge prompt is actually needed.
    """
    import evaluation_prompts as ep
    lang = norm_lang(lang)
    table = {
        ("en", "cloze"): ep.EVALUATION_CLOZE_EN,
        ("en", "condition"): ep.EVALUATION_CONDITION_EN,
        ("en", "edit"): ep.EVALUATION_EDIT_EN,
        ("en", "end2end"): ep.EVALUATION_END2END_EN,
        ("zh", "cloze"): ep.EVALUATION_CLOZE_CN,
        ("zh", "condition"): ep.EVALUATION_CONDITION_CN,
        ("zh", "edit"): ep.EVALUATION_EDIT_CN,
        ("zh", "end2end"): ep.EVALUATION_END2END_CN,
    }
    try:
        return table[(lang, task_type)]
    except KeyError:
        raise ValueError(f"No evaluation prompt for lang={lang} task_type={task_type}")
