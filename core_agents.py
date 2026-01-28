import json
from typing import Callable, Dict, List
from agent_prompts import SYSTEM_PROMPT, PROMPT_EDITOR_OUTLINE, PROMPT_WRITER_DRAFT, PROMPT_REVIEWER_CRITIQUE, PROMPT_REVISOR_PARAGRAPH
from glm_api_request.model import GateWays
from tenacity import retry, wait_fixed, stop_after_attempt
import re
from local_logger import SessionLogger

# model = GateWays(model_name="deepseek-v3.2")


def extract_json_from_llm(text: str) -> dict:
    """
    从 LLM 输出中提取 JSON 字典。
    支持: 1. 直接返回的 JSON 2. Markdown 包裹的 JSON 3. 带有杂言杂语的 JSON
    """
    # 核心正则：匹配从第一个 { 到最后一个 }
    # 能够处理嵌套的大括号和换行
    match = re.search(r"(\{.*\})", text, re.DOTALL)
    
    if match:
        json_str = match.group(1)
        try:
            # 尝试解析
            return json.loads(json_str)
        except json.JSONDecodeError:
            # 容错处理：有时 LLM 会多给一个逗号或特殊的控制字符
            # 这里可以引入更强大的库如 json5, 或者进行简单的字符串清洗
            # 简单清洗逻辑示例：
            json_str = json_str.strip().replace("\n", " ")
            try:
                return json.loads(json_str)
            except:
                raise ValueError(f"无法解析提取到的 JSON 字符串: {json_str}")
    else:
        raise ValueError(f"LLM 输出中未发现 JSON 结构: {text}")


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(model_instance: GateWays, system_prompt: str, user_message: str) -> str:
    """调用 LLM 获取响应，带重试机制"""
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


# --- 状态管理 (MDP State) ---
class WritingState:
    def __init__(self, topic: str, style_guide: str):
        self.meta = {
            "topic": topic,
            "style_guide": style_guide,
            "status": "INITIALIZING"
        }
        self.outline: List[Dict] = []  # 存储结构：{"id": 1, "title": "...", "points": "...", "status": "pending"}
        self.manuscript: Dict[int, Dict] = {} # Key: section_id, Value: {"content": "", "summary": "", "score": 0}
        self.history: List[str] = []

    def to_json(self):
        return json.dumps({
            "meta": self.meta,
            "outline": self.outline,
            "manuscript": self.manuscript
        }, ensure_ascii=False, indent=2)


# --- 1. 将 Action 封装为 Callable Functions (Tools) ---
class WritingTools:
    """所有写作相关的原子操作，核心 Agent 的 '手'"""
    
    @staticmethod
    def plan_outline(model_instance: GateWays, topic: str, style_guide: str, **kwargs) -> Dict:
        """输入主题和风格，生成 JSON 格式的大纲"""
        response = get_llm_response(model_instance, None, PROMPT_EDITOR_OUTLINE + f"\nTopic: {topic}, Style_guide: {style_guide}")
        return extract_json_from_llm(response)

    @staticmethod
    def write_paragraph(model_instance: GateWays, topic: str, style_guide: str, section_title: str, prev_summary: str, points: str, **kwargs) -> Dict:
        """根据大纲节点、上文摘要和关键点撰写段落"""
        context = {"topic": topic, "style_guide": style_guide, "section_title": section_title, "prev_summary": prev_summary, "points": points}
        response = get_llm_response(model_instance, None, PROMPT_WRITER_DRAFT + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        return extract_json_from_llm(response)

    @staticmethod
    def review_content(model_instance: GateWays, content: str, style_guide: str, points: str, **kwargs) -> Dict:
        """对段落进行打分和评估，返回结构化 JSON"""
        context = {"style_guide": style_guide, "points": points, "content": content}
        response = get_llm_response(model_instance, None, PROMPT_REVIEWER_CRITIQUE + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        return extract_json_from_llm(response)

    @staticmethod
    def revise_paragraph(model_instance: GateWays, content: str, style_guide: str, points: str, feedback: str, **kwargs) -> Dict:
        """根据反馈意见重写段落"""
        context =  {"style_guide": style_guide, "points": points, "content": content, "feedback": feedback}
        response = get_llm_response(model_instance, None, PROMPT_REVISOR_PARAGRAPH + '\n' + json.dumps(context, ensure_ascii=False, indent=2))
        return extract_json_from_llm(response)


# --- 2. 核心智能体 (The Orchestrator / Brain) ---
class WritingManager:
    def __init__(self, topic: str, style_guide: str, save_dir: str, model_name: str = "deepseek-v3.2"):
        self.model_instance = GateWays(model_name=model_name)
        self.state = WritingState(topic, style_guide)
        # --- 新增日志器 ---
        self.session_logger = SessionLogger(topic, save_dir=save_dir)
        # ----------------
        # 注册可用工具
        self.tools = {
            "plan_outline": WritingTools.plan_outline,
            "write_paragraph": WritingTools.write_paragraph,
            "review_content": WritingTools.review_content,
            "revise_paragraph": WritingTools.revise_paragraph
        }

    def determine_next_step(self) -> Dict:
        """
        纯 LLM 驱动的自主决策。
        不再使用 if-else 规则，而是通过 Context(State) + Policy(System Prompt) 获取 Action。
        """
        # 1. 准备当前环境的“快照”
        current_state_json = self.state.to_json()
        
        # 2. 构建面向决策者的 Prompt
        # 我们不再告诉它怎么选，只提供状态，让它通过理解 SYSTEM_PROMPT 中的状态流转来决策
        decision_prompt = f"""
### Current Writing State:
{current_state_json}

---
请根据当前的 Writing State，思考并决定下一步的动作。请确保你的动作能够推动项目向 `finish` 状态迈进。
"""

        try:
            # 调用 LLM
            response_text = get_llm_response(self.model_instance, SYSTEM_PROMPT, decision_prompt)
            # --- 记录 LLM 调用 ---
            self.session_logger.log_llm_call(decision_prompt, response_text)
            # -------------------
            # 解析决策
            decision = extract_json_from_llm(response_text)
            
            # 简单校验，确保生成的 params 包含必要的 section_id (除非是 plan_outline 或 finish)
            # 这能增强系统的鲁棒性
            # --- 记录思考和决策 ---
            self.session_logger.log_step(
                decision.get("thought"), 
                decision.get("action"), 
                decision.get("params")
            )
            return decision
            
        except Exception as e:
            print(f"Decision Error: {e}")
            # 降级处理或重试逻辑
            return {"thought": "解析出错", "action": "retry", "params": {}}
        

    def execute(self):
        """自治运行主循环"""
        excecution_step_counter = 0
        print("Starting Agentic Workflow...")
        while True:
            # 1. 观察状态并决策 (Observation -> Thought -> Action)
            # (s_t) -> (a_t) -> t++ -> (s_{t+1})
            decision = self.determine_next_step()
            action_name = decision["action"]
            params = decision["params"]
            excecution_step_counter += 1
            self.session_logger.set_logger_setp(excecution_step_counter)
            print(f"\n--- Step {excecution_step_counter} ---")

            if action_name == "finish":
                # --- 任务结束，保存最终文档 ---
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
            
            # 2. 调用工具 (Execution)
            print(f"Executing Action: {action_name}")
            try:
                tool_func = self.tools.get(action_name)
                print(f"  Params: {json.dumps(params, ensure_ascii=False)}")
                result = tool_func(model_instance=self.model_instance, **params)
                print(f"  Result: {result}")
            except Exception as e:
                print(f"  Action Execution Error: {e}")
            # 3. 更新状态 (State Transition)
            try:
                self._update_state(action_name, params, result)
            except Exception as e:
                print(f"  State Update Error: {e}")
            # --- 每次更新状态后保存快照 ---
            self.session_logger.save_snapshot(json.loads(self.state.to_json()))

    def _update_state(self, action, params, result):
        """
        根据动作结果更新全局状态对象。
        状态流转逻辑：
        1. plan_outline -> 初始化 outline 列表
        2. write_paragraph -> 填充 manuscript[id]，更新 outline[id].status = 'drafted'
        3. review_content -> 更新 manuscript[id].score，更新 outline[id].status 为 'completed' 或 'revision_needed'
        4. revise_paragraph -> 覆盖 manuscript[id].content，状态设回 'drafted' 重新触发评审
        """
        
        # 提取 section_id (决策层 params 中应包含此字段，以便定位更新哪个章节)
        section_id = params.get("section_id")

        if action == 'plan_outline':
            # result 结构示例: {"title": "...", "outline": [{"section_title": "...", "points": "..."}, ...]}
            self.state.meta["title"] = result.get("title", self.state.meta["topic"])
            self.state.outline = []
            for idx, item in enumerate(result.get("outline", [])):
                self.state.outline.append({
                    "id": idx,
                    "section_title": item["section_title"],
                    "points": item["points"],
                    "status": "pending"  # 初始状态
                })
            print(f"  [State] 大纲规划完成，共 {len(self.state.outline)} 个章节。")

        elif action == 'write_paragraph':
            # result 结构示例: {"content": "...", "summary": "..."}
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id] = {
                    "content": result["content"],
                    "summary": result["summary"],
                    "score": 0.0,
                    "feedback": ""
                }
                self.state.outline[section_id]["status"] = "drafted"
                print(f"  [State] 章节 {section_id} 撰写完成，待评审。")

        elif action == 'review_content':
            # result 结构示例: {"score": 8.5, "feedback": "..."}
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["score"] = result["score"]
                self.state.manuscript[section_id]["feedback"] = result["feedback"]
                
                if result["score"] >= 8.0:
                    self.state.outline[section_id]["status"] = "completed"
                    print(f"  [State] 章节 {section_id} 评审通过 (Score: {result['score']})。")
                else:
                    self.state.outline[section_id]["status"] = "revision_needed"
                    print(f"  [State] 章节 {section_id} 评审未通过 (Score: {result['score']})，需要修改。")

        elif action == 'revise_paragraph':
            # result 结构示例: {"revised_content": "...", "change_log": "..."}
            if section_id is not None:
                section_id = int(section_id)
                self.state.manuscript[section_id]["content"] = result["revised_content"]
                # 修改后状态重置为 drafted，以便下一次循环进入 review_content
                self.state.outline[section_id]["status"] = "drafted"
                print(f"  [State] 章节 {section_id} 已根据反馈优化，重新提交评审。")

        # 记录操作日志（可选）
        self.state.history.append(f"Action: {action} | Section: {section_id} | Result: Success")



if __name__ == "__main__":
    topic = "请创作一篇探讨人们对六十岁生活态度的文章，分析不同人群对步入老年的期待与焦虑，阐述老年生活的价值意义，并就如何更好地面对老年生活提出建议。核心观点是：年龄只是数字，关键在于保持积极心态，有尊严地度过老年生活。"
    style_guide = "议论文"
    
    manager = WritingManager(topic, style_guide)
    manager.execute()

#     text = """{\n  "thought": "当前尚未生成大纲，也没有章节内容，处于初始化阶段。下一步应先规划整体结构，明确章节安排，确保故事线索清晰，为后续写作打下基础。",\n  "action": "plan_outline",\n  "params": {\n    "topic": "我想写一篇大概6500字左右的小说，故事设定在春节前夕的一个防疫封控区。主要想写一个叫小蕊的主人公，她和科长孙科以及其他基层干部一起执行防疫任务，在这个过程中，她慢慢理解了基层工作的艰辛和这些干部的责任与精神，最终实现了自我成长和情感升华。",\n    "style": "小说"\n  }\n}
# """
#     res = extract_json_from_llm(text)
#     print(json.dumps(res, indent=2, ensure_ascii=False))
#     ex = WritingTools.plan_outline(**res['params'])
#     print(json.dumps(ex, indent=2, ensure_ascii=False))