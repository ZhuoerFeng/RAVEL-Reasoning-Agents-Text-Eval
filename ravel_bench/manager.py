"""ConfigurableWritingManager: adds `--tau` and a deterministic protocol
controller to the released RAVEL harness WITHOUT modifying core_agents.py.

Subclasses core_agents.WritingManager and overrides only two things:
  * _update_state       -> re-apply the section gate with a configurable tau
                           (the released code hardcodes 8.0 at core_agents.py:561)
  * determine_next_step -> for non-autonomous protocols, emit a scripted action
                           instead of querying the policy LLM.

Protocols:
  autonomous  : unchanged (policy LLM chooses every action).
  fixed       : forced outline -> draft -> review -> (revise up to max_revisions) -> finish.
  no_review   : outline -> draft each section -> finish (no review_content / revise).
  no_refine   : outline -> draft -> review (records score) -> finish (never revise).

Trace/snapshot parity: scripted steps still write to llm_trace.jsonl and log_step,
so the trajectories remain readable by ravel_results/restore_trace_state.py and the
Task-1 metric code.
"""
import json

from core_agents import WritingManager, DEFAULT_MODEL_NAME, ROLE_PLANNER
from .config import DEFAULT_TAU, DEFAULT_T_MAX, DEFAULT_MAX_REVISIONS, PROTOCOLS
from llm_client import make_client


class ConfigurableWritingManager(WritingManager):
    def __init__(self, topic, style_guide, save_dir="./logs",
                 model_name=DEFAULT_MODEL_NAME, language="zh", role_models=None,
                 max_steps=DEFAULT_T_MAX, max_revisions_per_section=DEFAULT_MAX_REVISIONS,
                 resume=False, tau=DEFAULT_TAU, protocol="autonomous"):
        super().__init__(topic, style_guide, save_dir=save_dir, model_name=model_name,
                         language=language, role_models=role_models, max_steps=max_steps,
                         max_revisions_per_section=max_revisions_per_section, resume=resume)
        if protocol not in PROTOCOLS:
            raise ValueError(f"protocol must be one of {PROTOCOLS}, got {protocol!r}")
        self.tau = float(tau)
        self.protocol = protocol
        # tau is a config now, so the policy decision prompt must NOT hard-code a
        # numeric acceptance threshold. The released SYSTEM_PROMPT (agent_prompts)
        # states "revision_needed when score < 8.0 / completed when score >= 8.0" --
        # an artifact from when tau was fixed at 8.0 everywhere. We REMOVE that
        # numeric restriction so the autonomous policy defers to the `status` flag,
        # which the gate (_update_state) computes from self.tau. get_prompts() returns
        # a SHARED module dict, so copy it first -> per-instance, thread-safe. The
        # reviewer rubric (PROMPT_REVIEWER_CRITIQUE) is left UNCHANGED so the reviewer
        # stays a stable quality scorer and tau is purely the acceptance threshold.
        self.prompts = dict(self.prompts)
        _sp = self.prompts["SYSTEM_PROMPT"]
        # English SYSTEM_PROMPT
        _sp = _sp.replace("the review score is < 8.0",
                          "the review score is below the acceptance threshold")
        _sp = _sp.replace("the review score is >= 8.0",
                          "the review score meets the acceptance threshold")
        # Chinese SYSTEM_PROMPT (same hard-coded 8.0 artifact)
        _sp = _sp.replace("（score < 8.0）", "（score 低于接受阈值）")
        _sp = _sp.replace("（score >= 8.0）", "（score 达到接受阈值）")
        self.prompts["SYSTEM_PROMPT"] = _sp
        # Route every role's model through the dependency-light llm_client
        # (OpenAI/Anthropic SDKs, env-configurable). This replaces the client
        # instances core_agents built, so RAVEL calls no longer require
        # glm_api_request, and openrouter:* streaming / claude* Anthropic routing
        # are handled uniformly by make_client.
        cache = {}
        for role, gw in list(self.model_registry.items()):
            name = getattr(gw, "model", None)
            if name:
                cache.setdefault(name, make_client(name))
                self.model_registry[role] = cache[name]
        self.policy_model = self.model_registry[ROLE_PLANNER]

    # ------------------------------------------------------------------
    # Configurable tau gate (parent hardcodes >= 8.0 at core_agents.py:561)
    # ------------------------------------------------------------------
    def _update_state(self, action, params, result):
        super()._update_state(action, params, result)
        if action != "review_content":
            return
        sid = params.get("section_id")
        if sid is None:
            return
        try:
            sid = int(sid)
        except (TypeError, ValueError):
            return
        if not (0 <= sid < len(self.state.outline)) or sid not in self.state.manuscript:
            return
        score = self.state.manuscript[sid].get("score", 0)
        if isinstance(score, (int, float)):
            self.state.outline[sid]["status"] = (
                "completed" if score >= self.tau else "revision_needed"
            )

    # ------------------------------------------------------------------
    # Decision source
    # ------------------------------------------------------------------
    def determine_next_step(self):
        if self.protocol == "autonomous":
            return super().determine_next_step()
        decision = self._scripted_next_step()
        # Keep the trace and step log identical in shape to the LLM path so
        # downstream metric reconstruction is unchanged.
        self.session_logger.log_llm_call(
            f"[scripted:{self.protocol}]", json.dumps(decision, ensure_ascii=False))
        self.session_logger.log_step(
            decision.get("thought"), decision.get("action"), decision.get("params"))
        return decision

    def _scripted_next_step(self) -> dict:
        topic = self.state.meta.get("topic", "")
        style_guide = self.state.meta.get("style_guide", "")
        outline = self.state.outline
        ms = self.state.manuscript

        # 1) Plan the outline first.
        if not outline:
            if self.state.meta.get("status") == "PLANNING_DONE":
                # plan_outline already ran but produced no sections; avoid an
                # infinite planning loop.
                return self._decision("outline empty after planning; finishing", "finish", {})
            return self._decision("plan the outline", "plan_outline",
                                   {"topic": topic, "style_guide": style_guide})

        # 2) Walk sections in order; act on the first not-yet-done one.
        for i, sec in enumerate(outline):
            status = sec.get("status", "pending")
            entry = ms.get(i, {})
            if status == "pending":
                prev_summary = ms.get(i - 1, {}).get("summary", "") if i > 0 else ""
                return self._decision(
                    f"draft section {i}", "write_paragraph",
                    {"section_id": i, "topic": topic, "style_guide": style_guide,
                     "section_title": sec.get("section_title", ""),
                     "prev_summary": prev_summary, "points": sec.get("points", "")})
            if status == "drafted":
                if self.protocol == "no_review":
                    continue  # written == done for no_review
                # fixed / no_refine: review it
                return self._decision(
                    f"review section {i}", "review_content",
                    {"section_id": i, "content": entry.get("content", ""),
                     "style_guide": style_guide, "points": sec.get("points", "")})
            if status == "revision_needed":
                if self.protocol == "fixed" and entry.get("revision_count", 0) < self.max_revisions_per_section:
                    return self._decision(
                        f"revise section {i}", "revise_paragraph",
                        {"section_id": i, "content": entry.get("content", ""),
                         "style_guide": style_guide, "points": sec.get("points", ""),
                         "feedback": entry.get("feedback", "")})
                # no_refine, or fixed past the revision budget: treat as done.
                continue
            # completed -> done
        # 3) All sections done for this protocol.
        return self._decision("all sections done; finishing", "finish", {})

    @staticmethod
    def _decision(thought, action, params):
        return {"thought": f"[scripted] {thought}", "action": action, "params": params}
