import os
import json
import logging
from datetime import datetime
from pathlib import Path
import shutil

class SessionLogger:
    def __init__(self, topic: str, save_dir: str = "writing_sessions"):
        # 创建以时间戳命名的运行目录
        if os.path.exists(save_dir):
            shutil.rmtree(save_dir)
        self.run_dir = Path(save_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)
        
        # 1. 文本日志：记录运行过程
        self.log_file = self.run_dir / "process.log"
        self._setup_logger()
        
        # 2. 状态快照目录：记录每一步的状态
        self.snapshot_dir = self.run_dir / "snapshots"
        self.snapshot_dir.mkdir(exist_ok=True)
        
        # 3. 原始 Trace：记录 LLM 调用
        self.trace_file = self.run_dir / "llm_trace.jsonl"
        
        self.step_counter = 0

    def _setup_logger(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(self.log_file, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger("WritingAgent")

    def set_logger_setp(self, step: int):
        self.step_counter = step

    def add_logger_step(self):
        self.step_counter += 1

    def log_step(self, thought, action, params):
        # self.step_counter += 1
        msg = f"\n{'='*20} STEP {self.step_counter} {'='*20}\n"
        msg += f"THOUGHT: {thought}\n"
        msg += f"ACTION: {action}\n"
        msg += f"PARAMS: {json.dumps(params, ensure_ascii=False)}\n"
        self.logger.info(msg)

    def save_snapshot(self, state_dict):
        """保存当前状态的 JSON 快照"""
        file_path = self.snapshot_dir / f"state_step_{self.step_counter:03d}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)

    def log_llm_call(self, prompt, response):
        """记录 LLM 原始输入输出，方便 Debug"""
        entry = {
            "step": self.step_counter,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_final_manuscript(self, manuscript, outline):
        """任务结束后导出完整的文章 Markdown"""
        content = "# Final Manuscript\n\n"
        for section in outline:
            s_id = str(section['id'])
            if s_id in manuscript:
                content += f"## {section['section_title']}\n\n"
                content += manuscript[str(s_id)]['content'] + "\n\n"
        
        with open(self.run_dir / "final_article.md", "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"Final article saved to {self.run_dir}/final_article.md")