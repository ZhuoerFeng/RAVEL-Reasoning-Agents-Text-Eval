"""
Unified multi-agent writing orchestrator.

Supports both Chinese ("zh") and English ("en") via a `language` parameter.

Features:
  - Per-role model specification (planner / writer / reviewer / revisor)
  - Per-section revision limit to prevent infinite review-revise loops
  - Error feedback into state so the LLM can see and react to failures
  - History recorded with real success/failure status; visible to LLM in state
  - Resume from the latest snapshot in an existing save_dir
"""

import json
from typing import Dict, List, Optional
from agent_prompts import get_prompts
# glm_api_request is now OPTIONAL. Models are reached through the dependency-light
# llm_client (OpenAI/Anthropic SDKs, env-configurable). GateWays is kept only as an
# annotation fallback so type hints resolve when glm_api_request is absent.
try:
    from glm_api_request.model import GateWays
except Exception:  # noqa: BLE001
    GateWays = object  # type: ignore
from llm_client import make_client
from tenacity import retry, wait_fixed, stop_after_attempt
import re
from local_logger import SessionLogger


# ============================================================
# Utilities
# ============================================================

def extract_json_from_llm(text: str) -> dict:
    """Extract a JSON dict from LLM output.

    Supports: direct JSON, Markdown-wrapped JSON, JSON with surrounding text.
    """
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            json_str = json_str.strip().replace("\n", " ")
            try:
                return json.loads(json_str)
            except Exception:
                raise ValueError(f"Unable to parse extracted JSON string: {json_str}")
    else:
        raise ValueError(f"No JSON structure found in LLM output: {text}")


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(model_instance: GateWays, system_prompt: Optional[str], user_message: str) -> str:
    """Call LLM with retry mechanism."""
    if system_prompt:
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ]
    else:
        message = [{"role": "user", "content": user_message}]
    response = model_instance.get_api_result(messages=message, temperature=0.2)
    print(response)
    return response.choices[0].message.content


# ============================================================
# State Management (MDP State)
# ============================================================

# Keep only the most recent N history entries visible to the LLM
# to avoid context bloat while still providing useful decision memory.
_MAX_VISIBLE_HISTORY = 10


class WritingState:
    def __init__(self, topic: str, style_guide: str):
        self.meta = {
            "topic": topic,
            "style_guide": style_guide,
            "status": "INITIALIZING",
        }
        self.outline: List[Dict] = []
        # Key: section_id (int), Value: {content, summary, score, feedback, revision_count}
        self.manuscript: Dict[int, Dict] = {}
        # Structured history entries (dicts), visible to LLM
        self.history: List[Dict] = []

    def to_json(self) -> str:
        """Serialize state to JSON. History is truncated to the most recent entries."""
        visible_history = self.history[-_MAX_VISIBLE_HISTORY:]
        return json.dumps({
            "meta": self.meta,
            "outline": self.outline,
            "manuscript": self.manuscript,
            "recent_history": visible_history,
        }, ensure_ascii=False, indent=2)

    def to_full_dict(self) -> dict:
        """Full state dict for snapshot persistence (includes complete history)."""
        return {
            "meta": self.meta,
            "outline": self.outline,
            "manuscript": {str(k): v for k, v in self.manuscript.items()},
            "history": self.history,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "WritingState":
        """Restore a WritingState from a snapshot dict."""
        topic = data["meta"]["topic"]
        style_guide = data["meta"]["style_guide"]
        state = cls(topic, style_guide)
        state.meta = data["meta"]
        state.outline = data.get("outline", [])
        # Restore manuscript with int keys
        raw_ms = data.get("manuscript", {})
        state.manuscript = {int(k): v for k, v in raw_ms.items()}
        state.history = data.get("history", [])
        return state

    def record_history(self, step: int, action: str, section_id, status: str,
                       error_msg: str = ""):
        """Append a structured history entry."""
        entry = {
            "step": step,
            "action": action,
            "section_id": section_id,
            "status": status,  # "success" | "error" | "skipped"
        }
        if error_msg:
            entry["error"] = error_msg
        self.history.append(entry)


# ============================================================
# Atomic Writing Tools
# ============================================================

class WritingTools:
    """Atomic operations for the Orchestrator."""

    @staticmethod
    def plan_outline(model_instance: GateWays, prompts: dict,
                     topic: str, style_guide: str, **kwargs) -> Dict:
        prompt = prompts["PROMPT_EDITOR_OUTLINE"]
        response = get_llm_response(
            model_instance, None,
            prompt + f"\nTopic: {topic}, Style_guide: {style_guide}",
        )
        return extract_json_from_llm(response)

    @staticmethod
    def write_paragraph(model_instance: GateWays, prompts: dict,
                        topic: str, style_guide: str, section_title: str,
                        prev_summary: str, points: str, **kwargs) -> Dict:
        prompt = prompts["PROMPT_WRITER_DRAFT"]
        context = {
            "topic": topic, "style_guide": style_guide,
            "section_title": section_title,
            "prev_summary": prev_summary, "points": points,
        }
        response = get_llm_response(
            model_instance, None,
            prompt + "\n" + json.dumps(context, ensure_ascii=False, indent=2),
        )
        return extract_json_from_llm(response)

    @staticmethod
    def review_content(model_instance: GateWays, prompts: dict,
                       content: str, style_guide: str, points: str,
                       **kwargs) -> Dict:
        prompt = prompts["PROMPT_REVIEWER_CRITIQUE"]
        context = {"style_guide": style_guide, "points": points, "content": content}
        response = get_llm_response(
            model_instance, None,
            prompt + "\n" + json.dumps(context, ensure_ascii=False, indent=2),
        )
        return extract_json_from_llm(response)

    @staticmethod
    def revise_paragraph(model_instance: GateWays, prompts: dict,
                         content: str, style_guide: str, points: str,
                         feedback: str, **kwargs) -> Dict:
        prompt = prompts["PROMPT_REVISOR_PARAGRAPH"]
        context = {
            "style_guide": style_guide, "points": points,
            "content": content, "feedback": feedback,
        }
        response = get_llm_response(
            model_instance, None,
            prompt + "\n" + json.dumps(context, ensure_ascii=False, indent=2),
        )
        return extract_json_from_llm(response)


# ============================================================
# Model Registry for per-role specification
# ============================================================

# Default model name used when no per-role override is provided.
DEFAULT_MODEL_NAME = "deepseek-v3.2"

# Role keys used by WritingManager
ROLE_PLANNER = "planner"
ROLE_WRITER = "writer"
ROLE_REVIEWER = "reviewer"
ROLE_REVISOR = "revisor"
ALL_ROLES = [ROLE_PLANNER, ROLE_WRITER, ROLE_REVIEWER, ROLE_REVISOR]

# Mapping from tool name to role key
_TOOL_TO_ROLE = {
    "plan_outline": ROLE_PLANNER,
    "write_paragraph": ROLE_WRITER,
    "review_content": ROLE_REVIEWER,
    "revise_paragraph": ROLE_REVISOR,
}


def _build_model_registry(
    model_name: str = DEFAULT_MODEL_NAME,
    role_models: Optional[Dict[str, str]] = None,
) -> Dict[str, GateWays]:
    """Build a {role -> GateWays} mapping, reusing instances for same model name.

    Args:
        model_name: Default model for all roles.
        role_models: Optional overrides, e.g. {"reviewer": "gpt-5.2-2025-12-11"}.

    Returns:
        Dict mapping each role to its GateWays instance.
    """
    role_models = role_models or {}
    # Collect unique model names
    name_map = {}
    for role in ALL_ROLES:
        name_map[role] = role_models.get(role, model_name)

    # Deduplicate GateWays instances by model name
    instance_cache: Dict[str, GateWays] = {}
    registry: Dict[str, GateWays] = {}
    for role, mname in name_map.items():
        if mname not in instance_cache:
            instance_cache[mname] = make_client(mname)
        registry[role] = instance_cache[mname]

    return registry


# ============================================================
# Orchestrator
# ============================================================

class WritingManager:
    """LLM-driven autonomous writing orchestrator.

    Args:
        topic: The writing topic / instruction.
        style_guide: Genre or style requirement.
        save_dir: Directory for logs and snapshots.
        model_name: Default model name for all roles.
        language: Prompt language, "zh" or "en".
        role_models: Optional per-role model overrides, e.g.
            {"planner": "gpt-5.2", "reviewer": "claude-sonnet-4-20250514"}.
            Roles not specified fall back to `model_name`.
        max_steps: Maximum execution steps before forced termination.
        max_revisions_per_section: Maximum review-revise cycles per section.
            When exceeded the section is force-completed.
        resume: If True, attempt to resume from the latest snapshot in save_dir.
    """

    def __init__(
        self,
        topic: str,
        style_guide: str,
        save_dir: str = "./logs",
        model_name: str = DEFAULT_MODEL_NAME,
        language: str = "zh",
        role_models: Optional[Dict[str, str]] = None,
        max_steps: int = 50,
        max_revisions_per_section: int = 3,
        resume: bool = False,
        # Legacy param kept for backward compatibility
        revisor_model_name: Optional[str] = None,
    ):
        # Merge legacy param into role_models
        if revisor_model_name and not role_models:
            role_models = {ROLE_REVISOR: revisor_model_name}
        elif revisor_model_name and role_models and ROLE_REVISOR not in role_models:
            role_models[ROLE_REVISOR] = revisor_model_name

        self.model_registry = _build_model_registry(model_name, role_models)
        # The "policy" model (for determine_next_step) defaults to the planner model
        self.policy_model = self.model_registry[ROLE_PLANNER]

        self.prompts = get_prompts(language)
        self.max_steps = max_steps
        self.max_revisions_per_section = max_revisions_per_section
        self.save_dir = save_dir

        self.session_logger = SessionLogger(topic, save_dir=save_dir)

        # Register tools
        self.tools = {
            "plan_outline": WritingTools.plan_outline,
            "write_paragraph": WritingTools.write_paragraph,
            "review_content": WritingTools.review_content,
            "revise_paragraph": WritingTools.revise_paragraph,
        }

        # State initialization or resume
        self._execution_step_counter = 0
        if resume:
            self._try_resume(topic, style_guide)
        else:
            self.state = WritingState(topic, style_guide)

    def _try_resume(self, topic: str, style_guide: str):
        """Attempt to resume from the latest snapshot, fall back to fresh state."""
        step, snapshot = self.session_logger.find_latest_snapshot()
        if snapshot is not None:
            self.state = WritingState.from_dict(snapshot)
            self._execution_step_counter = step
            print(f"Resumed from step {step} (save_dir={self.save_dir})")
            self.session_logger.logger.info(f"Resumed execution from step {step}")
        else:
            self.state = WritingState(topic, style_guide)
            print("No snapshot found, starting fresh.")

    # ------------------------------------------------------------------
    # Model selection helper
    # ------------------------------------------------------------------

    def _get_model_for_tool(self, tool_name: str) -> GateWays:
        """Return the GateWays instance for the given tool's role."""
        role = _TOOL_TO_ROLE.get(tool_name)
        if role:
            return self.model_registry[role]
        return self.policy_model

    # ------------------------------------------------------------------
    # Decision
    # ------------------------------------------------------------------

    def determine_next_step(self) -> Dict:
        """Pure LLM-driven autonomous decision making."""
        current_state_json = self.state.to_json()
        decision_prompt = self.prompts["DECISION_PROMPT_TEMPLATE"].format(
            current_state_json=current_state_json,
        )

        try:
            response_text = get_llm_response(
                self.policy_model,
                self.prompts["SYSTEM_PROMPT"],
                decision_prompt,
            )
            self.session_logger.log_llm_call(decision_prompt, response_text)
            decision = extract_json_from_llm(response_text)

            self.session_logger.log_step(
                decision.get("thought"),
                decision.get("action"),
                decision.get("params"),
            )
            return decision

        except Exception as e:
            print(f"Decision Error: {e}")
            return {"thought": "Parsing error", "action": "retry", "params": {}}

    # ------------------------------------------------------------------
    # Revision limit check
    # ------------------------------------------------------------------

    def _check_revision_limit(self, action_name: str, params: dict) -> bool:
        """Check whether a revise/review action should be blocked due to
        the per-section revision limit.

        If the section has been revised >= max_revisions_per_section times,
        force it to 'completed' and return True (meaning: skip this action).
        """
        if action_name not in ("revise_paragraph", "review_content"):
            return False

        section_id = params.get("section_id")
        if section_id is None:
            return False
        section_id = int(section_id)

        ms = self.state.manuscript.get(section_id)
        if ms is None:
            return False

        if ms.get("revision_count", 0) >= self.max_revisions_per_section:
            # Force-complete this section
            self.state.outline[section_id]["status"] = "completed"
            msg = (f"Section {section_id} reached max revisions "
                   f"({self.max_revisions_per_section}), force-completing.")
            print(f"  [State] {msg}")
            self.state.record_history(
                self._execution_step_counter, action_name, section_id,
                "skipped", error_msg=msg,
            )
            return True

        return False

    # ------------------------------------------------------------------
    # Main execution loop
    # ------------------------------------------------------------------

    def execute(self):
        """Main loop for autonomous execution."""
        print("Starting Agentic Workflow...")

        while True:
            decision = self.determine_next_step()
            action_name = decision["action"]
            params = decision.get("params", {})
            self._execution_step_counter += 1
            step = self._execution_step_counter
            self.session_logger.set_logger_step(step)
            print(f"\n--- Step {step} ---")

            # --- Termination conditions ---
            if action_name == "finish":
                self.session_logger.save_final_manuscript(
                    self.state.manuscript, self.state.outline,
                )
                self.state.record_history(step, "finish", None, "success")
                self.session_logger.save_snapshot(self.state.to_full_dict())
                print("Task Completed!")
                break

            if step > self.max_steps:
                print("Reached maximum execution steps. Terminating.")
                self.state.record_history(
                    step, action_name, params.get("section_id"),
                    "skipped", error_msg="max_steps exceeded",
                )
                self.session_logger.save_final_manuscript(
                    self.state.manuscript, self.state.outline,
                )
                self.session_logger.save_snapshot(self.state.to_full_dict())
                break

            if action_name == "retry":
                print("Retrying decision due to previous error...")
                self.state.record_history(step, "retry", None, "skipped")
                continue

            # --- Revision limit guard ---
            if self._check_revision_limit(action_name, params):
                self.session_logger.save_snapshot(self.state.to_full_dict())
                continue

            # --- Validate action ---
            tool_func = self.tools.get(action_name)
            if tool_func is None:
                msg = f"Unknown action: {action_name}"
                print(f"  {msg}")
                self.state.record_history(step, action_name,
                                          params.get("section_id"),
                                          "error", error_msg=msg)
                self.session_logger.save_snapshot(self.state.to_full_dict())
                continue

            # --- Validate section_id bounds ---
            section_id = params.get("section_id")
            if section_id is not None:
                try:
                    sid = int(section_id)
                    if sid < 0 or sid >= len(self.state.outline):
                        msg = (f"section_id {sid} out of range "
                               f"[0, {len(self.state.outline)})")
                        print(f"  {msg}")
                        self.state.record_history(step, action_name, sid,
                                                  "error", error_msg=msg)
                        self.session_logger.save_snapshot(self.state.to_full_dict())
                        continue
                except (ValueError, TypeError):
                    msg = f"Invalid section_id: {section_id}"
                    print(f"  {msg}")
                    self.state.record_history(step, action_name, section_id,
                                              "error", error_msg=msg)
                    self.session_logger.save_snapshot(self.state.to_full_dict())
                    continue

            # --- Execute tool ---
            print(f"Executing Action: {action_name}")
            result = {}
            model_for_tool = self._get_model_for_tool(action_name)
            try:
                print(f"  Params: {json.dumps(params, ensure_ascii=False)}")
                result = tool_func(
                    model_instance=model_for_tool,
                    prompts=self.prompts,
                    **params,
                )
                print(f"  Result: {result}")
            except Exception as e:
                msg = f"Action Execution Error: {e}"
                print(f"  {msg}")
                self.state.record_history(step, action_name,
                                          params.get("section_id"),
                                          "error", error_msg=str(e))
                self.session_logger.save_snapshot(self.state.to_full_dict())
                continue  # skip state update on tool failure

            # --- Update state ---
            try:
                self._update_state(action_name, params, result)
                self.state.record_history(step, action_name,
                                          params.get("section_id"), "success")
            except Exception as e:
                msg = f"State Update Error: {e}"
                print(f"  {msg}")
                self.state.record_history(step, action_name,
                                          params.get("section_id"),
                                          "error", error_msg=str(e))

            # --- Save snapshot ---
            self.session_logger.save_snapshot(self.state.to_full_dict())

    # ------------------------------------------------------------------
    # State transitions
    # ------------------------------------------------------------------

    def _update_state(self, action: str, params: dict, result: dict):
        """Update global state based on action results."""
        section_id = params.get("section_id")

        if action == "plan_outline":
            self.state.meta["title"] = result.get("title", self.state.meta["topic"])
            self.state.outline = []
            for idx, item in enumerate(result.get("outline", [])):
                self.state.outline.append({
                    "id": idx,
                    "section_title": item["section_title"],
                    "points": item["points"],
                    "status": "pending",
                })
            self.state.meta["status"] = "PLANNING_DONE"
            print(f"  [State] Outline planned with {len(self.state.outline)} sections.")

        elif action == "write_paragraph":
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id] = {
                    "content": result["content"],
                    "summary": result["summary"],
                    "score": 0.0,
                    "feedback": "",
                    "revision_count": 0,
                }
                self.state.outline[section_id]["status"] = "drafted"
                print(f"  [State] Section {section_id} drafted, awaiting review.")

        elif action == "review_content":
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["score"] = result["score"]
                self.state.manuscript[section_id]["feedback"] = result["feedback"]

                if result["score"] >= 8.0:
                    self.state.outline[section_id]["status"] = "completed"
                    print(f"  [State] Section {section_id} passed review "
                          f"(Score: {result['score']}).")
                else:
                    self.state.outline[section_id]["status"] = "revision_needed"
                    print(f"  [State] Section {section_id} failed review "
                          f"(Score: {result['score']}), revision needed.")

        elif action == "revise_paragraph":
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["content"] = result["revised_content"]
                self.state.outline[section_id]["status"] = "drafted"
                # Increment revision counter
                self.state.manuscript[section_id]["revision_count"] = (
                    self.state.manuscript[section_id].get("revision_count", 0) + 1
                )
                rev_count = self.state.manuscript[section_id]["revision_count"]
                print(f"  [State] Section {section_id} revised "
                      f"(revision {rev_count}/{self.max_revisions_per_section}), "
                      f"resubmitting for review.")


# ============================================================
# CLI
# ============================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run the agentic writing workflow.")
    parser.add_argument("--language", type=str, default="zh", choices=["zh", "en"],
                        help="Prompt language (default: zh)")
    parser.add_argument("--model_name", type=str, default=DEFAULT_MODEL_NAME,
                        help="Default model name for all roles")
    parser.add_argument("--planner_model", type=str, default=None,
                        help="Model for the planner role (outline generation + decision)")
    parser.add_argument("--writer_model", type=str, default=None,
                        help="Model for the writer role")
    parser.add_argument("--reviewer_model", type=str, default=None,
                        help="Model for the reviewer role")
    parser.add_argument("--revisor_model", type=str, default=None,
                        help="Model for the revisor role")
    parser.add_argument("--save_dir", type=str, default="./logs",
                        help="Directory for logs and snapshots")
    parser.add_argument("--max_steps", type=int, default=50,
                        help="Maximum execution steps")
    parser.add_argument("--max_revisions", type=int, default=3,
                        help="Maximum revisions per section")
    parser.add_argument("--resume", action="store_true",
                        help="Resume from the latest snapshot in save_dir")
    args = parser.parse_args()

    # Build role_models dict from CLI args
    role_models = {}
    if args.planner_model:
        role_models[ROLE_PLANNER] = args.planner_model
    if args.writer_model:
        role_models[ROLE_WRITER] = args.writer_model
    if args.reviewer_model:
        role_models[ROLE_REVIEWER] = args.reviewer_model
    if args.revisor_model:
        role_models[ROLE_REVISOR] = args.revisor_model

    if args.language == "zh":
        topic = ("请创作一篇探讨人们对六十岁生活态度的文章，分析不同人群对步入老年的期待与焦虑，"
                 "阐述老年生活的价值意义，并就如何更好地面对老年生活提出建议。"
                 "核心观点是：年龄只是数字，关键在于保持积极心态，有尊严地度过老年生活。")
        style_guide = "议论文"
    else:
        topic = ("Please write an article discussing attitudes toward life at age sixty, "
                 "analyzing expectations and anxieties about entering old age among different "
                 "groups, explaining the value and meaning of senior life, and providing "
                 "suggestions on how to better face it. The core view is: age is just a "
                 "number; the key is to maintain a positive mindset and spend the senior "
                 "years with dignity.")
        style_guide = "Argumentative essay"

    manager = WritingManager(
        topic=topic,
        style_guide=style_guide,
        save_dir=args.save_dir,
        model_name=args.model_name,
        language=args.language,
        role_models=role_models or None,
        max_steps=args.max_steps,
        max_revisions_per_section=args.max_revisions,
        resume=args.resume,
    )
    manager.execute()
