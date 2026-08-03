"""
Session logger for WritingManager runs.

Supports:
  - Process log, LLM trace, per-step JSON snapshots, final article export.
  - Resume: find the latest snapshot and step counter from an existing save_dir.
"""

import os
import json
import logging
from datetime import datetime
from pathlib import Path


class SessionLogger:
    def __init__(self, topic: str, save_dir: str = "writing_sessions"):
        self.run_dir = Path(save_dir)
        self.run_dir.mkdir(parents=True, exist_ok=True)

        # Text log for the run process
        self.log_file = self.run_dir / "process.log"
        self._setup_logger()

        # State snapshot directory
        self.snapshot_dir = self.run_dir / "snapshots"
        self.snapshot_dir.mkdir(exist_ok=True)

        # Raw LLM trace
        self.trace_file = self.run_dir / "llm_trace.jsonl"

        self.step_counter = 0

    def _setup_logger(self):
        logger_name = f"WritingAgent_{self.run_dir}"
        self.logger = logging.getLogger(logger_name)
        self.logger.setLevel(logging.INFO)
        if not self.logger.handlers:
            self.logger.addHandler(
                logging.FileHandler(self.log_file, encoding="utf-8")
            )
            self.logger.addHandler(logging.StreamHandler())
            formatter = logging.Formatter("%(asctime)s [%(levelname)s] %(message)s")
            for handler in self.logger.handlers:
                handler.setFormatter(formatter)

    def set_logger_step(self, step: int):
        self.step_counter = step

    # Backward compatibility alias
    set_logger_setp = set_logger_step

    def add_logger_step(self):
        self.step_counter += 1

    def log_step(self, thought, action, params):
        msg = f"\n{'='*20} STEP {self.step_counter} {'='*20}\n"
        msg += f"THOUGHT: {thought}\n"
        msg += f"ACTION: {action}\n"
        msg += f"PARAMS: {json.dumps(params, ensure_ascii=False)}\n"
        self.logger.info(msg)

    def save_snapshot(self, state_dict):
        """Save a JSON snapshot of the current state."""
        file_path = self.snapshot_dir / f"state_step_{self.step_counter:03d}.json"
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(state_dict, f, ensure_ascii=False, indent=2)

    def log_llm_call(self, prompt, response):
        """Record raw LLM input/output for debugging."""
        entry = {
            "step": self.step_counter,
            "timestamp": datetime.now().isoformat(),
            "prompt": prompt,
            "response": response,
        }
        with open(self.trace_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")

    def save_final_manuscript(self, manuscript, outline):
        """Export the complete article as Markdown when the task finishes."""
        content = "# Final Manuscript\n\n"
        for section in outline:
            s_id = section["id"]
            entry = manuscript.get(s_id) or manuscript.get(str(s_id))
            if entry:
                content += f"## {section['section_title']}\n\n"
                content += entry["content"] + "\n\n"

        output_path = self.run_dir / "final_article.md"
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(content)
        self.logger.info(f"Final article saved to {output_path}")

    # ----------------------------------------------------------------
    # Resume support
    # ----------------------------------------------------------------

    def find_latest_snapshot(self) -> tuple:
        """Find the latest snapshot file in the snapshot directory.

        Returns:
            (step_number: int, state_dict: dict) if a snapshot exists,
            (0, None) otherwise.
        """
        if not self.snapshot_dir.exists():
            return 0, None

        snapshot_files = sorted(self.snapshot_dir.glob("state_step_*.json"))
        if not snapshot_files:
            return 0, None

        latest = snapshot_files[-1]
        # Extract step number from filename: state_step_012.json -> 12
        step_str = latest.stem.replace("state_step_", "")
        try:
            step = int(step_str)
        except ValueError:
            return 0, None

        with open(latest, "r", encoding="utf-8") as f:
            state_dict = json.load(f)

        self.logger.info(f"Found snapshot at step {step}: {latest}")
        return step, state_dict
