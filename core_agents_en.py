import json
from typing import Callable, Dict, List
from agent_prompts_en import SYSTEM_PROMPT, PROMPT_EDITOR_OUTLINE, PROMPT_WRITER_DRAFT, PROMPT_REVIEWER_CRITIQUE, PROMPT_REVISOR_PARAGRAPH
from glm_api_request.model import GateWays
from tenacity import retry, wait_fixed, stop_after_attempt
import re
from local_logger import SessionLogger

# model = GateWays(model_name="deepseek-v3.2")

default_model = GateWays(model_name="gemini-3-pro-preview")


def extract_json_from_llm(text: str) -> dict:
    """
    Extracts a JSON dictionary from LLM output.
    Supports: 1. Direct JSON 2. Markdown-wrapped JSON 3. JSON with surrounding text.
    """
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            # Simple cleaning for trailing commas or control characters
            json_str = json_str.strip().replace("\n", " ")
            try:
                return json.loads(json_str)
            except:
                raise ValueError(f"Unable to parse extracted JSON string: {json_str}")
    else:
        raise ValueError(f"No JSON structure found in LLM output: {text}")

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(model_instance: GateWays, system_prompt: str, user_message: str) -> str:
    """Calls LLM to get a response with retry mechanism"""
    if system_prompt:
        message = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message}
        ]
    else: 
        message = [
            {"role": "user", "content": user_message}
        ]
    response = model_instance.get_api_result(
        messages=message,
        temperature=0.2,
    )
    print(response)
    return response.choices[0].message.content

# --- State Management (MDP State) ---
class WritingState:
    def __init__(self, topic: str, style_guide: str):
        self.meta = {
            "topic": topic,
            "style_guide": style_guide,
            "status": "INITIALIZING"
        }
        self.outline: List[Dict] = []  # Structure: {"id": 1, "title": "...", "points": "...", "status": "pending"}
        self.manuscript: Dict[int, Dict] = {} # Key: section_id, Value: {"content": "", "summary": "", "score": 0}
        self.history: List[str] = []

    def to_json(self):
        return json.dumps({
            "meta": self.meta,
            "outline": self.outline,
            "manuscript": self.manuscript
        }, ensure_ascii=False, indent=2)

# --- 1. Tool Encapsulation (Atomic Actions) ---
class WritingTools:
    """Atomic operations for the Orchestrator"""
    
    @staticmethod
    def plan_outline(model_instance: GateWays, topic: str, style_guide: str, **kwargs) -> Dict:
        """Generates outline in JSON format"""
        response = get_llm_response(model_instance, None, PROMPT_EDITOR_OUTLINE + f"\nTopic: {topic}, Style_guide: {style_guide}")
        return extract_json_from_llm(response)

    @staticmethod
    def write_paragraph(model_instance: GateWays, topic: str, style_guide: str, section_title: str, prev_summary: str, points: str, **kwargs) -> Dict:
        """Writes a paragraph based on outline node and context"""
        context = {"topic": topic, "style_guide": style_guide, "section_title": section_title, "prev_summary": prev_summary, "points": points}
        response = get_llm_response(model_instance, None, PROMPT_WRITER_DRAFT + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        return extract_json_from_llm(response)

    @staticmethod
    def review_content(model_instance: GateWays, content: str, style_guide: str, points: str, **kwargs) -> Dict:
        """Evaluates paragraph quality and returns structured JSON"""
        context = {"style_guide": style_guide, "points": points, "content": content}
        response = get_llm_response(model_instance, None, PROMPT_REVIEWER_CRITIQUE + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        return extract_json_from_llm(response)

    @staticmethod
    def revise_paragraph(model_instance: GateWays, content: str, style_guide: str, points: str, feedback: str, **kwargs) -> Dict:
        """Rewrites paragraph based on feedback"""
        context =  {"style_guide": style_guide, "points": points, "content": content, "feedback": feedback}
        response = get_llm_response(model_instance, None, PROMPT_REVISOR_PARAGRAPH + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        # # ablate on STRONG Revisor
        # response = get_llm_response(default_model, None, PROMPT_REVISOR_PARAGRAPH + '\n' + json.dumps(context, ensure_ascii=False, indent=2))

        return extract_json_from_llm(response)

# --- 2. Orchestrator (The Brain) ---
class WritingManager:
    def __init__(self, topic: str, style_guide: str, save_dir: str, model_name: str = "deepseek-v3.2"):
        self.model_instance = GateWays(model_name=model_name)
        self.state = WritingState(topic, style_guide)
        self.session_logger = SessionLogger(topic, save_dir=save_dir)
        # Register tools
        self.tools = {
            "plan_outline": WritingTools.plan_outline,
            "write_paragraph": WritingTools.write_paragraph,
            "review_content": WritingTools.review_content,
            "revise_paragraph": WritingTools.revise_paragraph
        }

    def determine_next_step(self) -> Dict:
        """Pure LLM-driven autonomous decision making"""
        current_state_json = self.state.to_json()
        
        decision_prompt = f"""
### Current Writing State:
{current_state_json}

---
Based on the current Writing State, think and decide the next action. Ensure your action moves the project toward the `finish` state.
"""

        try:
            # response_text = get_llm_response(self.model_instance, SYSTEM_PROMPT, decision_prompt)
            response_text = get_llm_response(default_model, SYSTEM_PROMPT, decision_prompt)
            self.session_logger.log_llm_call(decision_prompt, response_text)
            decision = extract_json_from_llm(response_text)
            
            self.session_logger.log_step(
                decision.get("thought"), 
                decision.get("action"), 
                decision.get("params")
            )
            return decision
            
        except Exception as e:
            print(f"Decision Error: {e}")
            return {"thought": "Parsing error", "action": "retry", "params": {}}
        

    def execute(self):
        """Main loop for autonomous execution"""
        excecution_step_counter = 0
        print("Starting Agentic Workflow...")
        while True:
            decision = self.determine_next_step()
            action_name = decision["action"]
            params = decision["params"]
            excecution_step_counter += 1
            self.session_logger.set_logger_setp(excecution_step_counter)
            print(f"\n--- Step {excecution_step_counter} ---")

            if action_name == "finish":
                self.session_logger.save_final_manuscript(self.state.manuscript, self.state.outline)
                print("Task Completed!")
                break
            elif excecution_step_counter > 50:
                print("Reached maximum execution steps. Terminating to avoid infinite loop.")
                self.session_logger.save_final_manuscript(self.state.manuscript, self.state.outline)
                break
            elif action_name == "retry":
                print("Retrying decision due to previous error...")
                continue
            
            print(f"Executing Action: {action_name}")
            try:
                tool_func = self.tools.get(action_name)
                print(f"  Params: {json.dumps(params, ensure_ascii=False)}")
                result = tool_func(model_instance=self.model_instance, **params)
                print(f"  Result: {result}")
            except Exception as e:
                print(f"  Action Execution Error: {e}")
                result = {}

            try:
                self._update_state(action_name, params, result)
            except Exception as e:
                print(f"  State Update Error: {e}")
            
            self.session_logger.save_snapshot(json.loads(self.state.to_json()))

    def _update_state(self, action, params, result):
        """Updates global state based on action results"""
        section_id = params.get("section_id")

        if action == 'plan_outline':
            self.state.meta["title"] = result.get("title", self.state.meta["topic"])
            self.state.outline = []
            for idx, item in enumerate(result.get("outline", [])):
                self.state.outline.append({
                    "id": idx,
                    "section_title": item["section_title"],
                    "points": item["points"],
                    "status": "pending"
                })
            print(f"  [State] Outline planned with {len(self.state.outline)} sections.")

        elif action == 'write_paragraph':
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id] = {
                    "content": result["content"],
                    "summary": result["summary"],
                    "score": 0.0,
                    "feedback": ""
                }
                self.state.outline[section_id]["status"] = "drafted"
                print(f"  [State] Section {section_id} drafted, awaiting review.")

        elif action == 'review_content':
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["score"] = result["score"]
                self.state.manuscript[section_id]["feedback"] = result["feedback"]
                
                if result["score"] >= 8.0:
                    self.state.outline[section_id]["status"] = "completed"
                    print(f"  [State] Section {section_id} passed review (Score: {result['score']}).")
                else:
                    self.state.outline[section_id]["status"] = "revision_needed"
                    print(f"  [State] Section {section_id} failed review (Score: {result['score']}), revision needed.")

        elif action == 'revise_paragraph':
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["content"] = result["revised_content"]
                self.state.outline[section_id]["status"] = "drafted"
                print(f"  [State] Section {section_id} optimized, resubmitting for review.")

        self.state.history.append(f"Action: {action} | Section: {section_id} | Result: Success")

if __name__ == "__main__":
    topic = "Please write an article discussing attitudes toward life at age sixty, analyzing expectations and anxieties about entering old age among different groups, explaining the value and meaning of senior life, and providing suggestions on how to better face it. The core view is: age is just a number; the key is to maintain a positive mindset and spend the senior years with dignity."
    style_guide = "Argumentative essay"
    
    manager = WritingManager(topic, style_guide, save_dir="./logs")
    manager.execute()

