import os
import json
import re
import argparse
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from tqdm import tqdm
from tenacity import retry, wait_fixed, stop_after_attempt

# 假设环境已配置好这些自定义模块
from glm_api_request.model import GateWays 
from evaluation_prompts import EVALUATION_END2END_EN

# --- 配置区 ---
# ROOT_DIR = 'ravel_results/english_analysis'
ROOT_DIR = 'ravel_results/ablation_policy'
TARGET_FILE = 'restored_writing.md'
TRACE_FILE = 'llm_trace.jsonl'
OUTPUT_NAME = 'final_rating.json'

data_file = open('english_dataset/english_dataset.jsonl').readlines()
data_dict = {}
for line in data_file:
    item = json.loads(line)
    data_dict[item['infer_id']] = item


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_judge_response(model, user_message: str) -> str:
    """调用裁判模型获取评价结果"""
    messages = [
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(
        messages=messages,
        temperature=0,
        max_completion_tokens=1000  
    )
    # print(response)
    return response.choices[0].message.content

def extract_instruction_from_trace(trace_path):
    """
    从 llm_trace.jsonl 中提取原始指令。
    TODO: 这里的提取逻辑依赖于 llm_trace.jsonl 的具体格式。
    通常第一条记录包含 system prompt 或用户的初始 instruction。
    """
    try:
        with open(trace_path, 'r', encoding='utf-8') as f:
            # 假设第一行包含任务描述
            first_line = json.loads(f.readline())
            # 这里的 key 需要根据你实际的 trace 格式调整
            # TODO: 确认 trace 文件中存储用户原始指令的 key 路径
            instruction = first_line.get('instruction') or \
                          first_line.get('query') or \
                          "No instruction found in trace."
            return instruction
    except Exception as e:
        return f"Error extracting instruction: {e}"

def process_single_directory(sample_path, model):
    """处理单个样本目录的评价"""
    md_file = sample_path / TARGET_FILE
    output_file = sample_path / OUTPUT_NAME

    # 1. 检查必要文件是否存在
    if not md_file.exists():
        return None
    
    # 如果已经评价过，跳过（可选）
    if output_file.exists():
        return f"Skipped: {sample_path.name} (Already evaluated)"

    try:
        # 2. 读取生成的文本
        with open(md_file, 'r', encoding='utf-8') as f:
            candidate_text = f.read()

        # 3. 提取指令信息
        # TODO: 如果有 reference 文本，也需要在此处提取。目前假设为 End-to-End 无参考评价。
        infer_id = sample_path.name
        instruction = data_dict.get(infer_id, {}).get('instruction', "No instruction found.")
        reference = data_dict.get(infer_id, {}).get('reference', "")

        # 4. 构建评测消息 (使用 EVALUATION_END2END_EN)
        user_message = f"[Instruction]: {instruction}\n[Reference]: {reference}\n[Candidate]: {candidate_text}"
        # 5. 调用 LLM 获取结果
        raw_eval = get_judge_response(model, EVALUATION_END2END_EN + user_message)

        # 6. 解析并保存结果
        eval_data = {"raw_response": raw_eval}
        try:
            # 提取 JSON 块
            clean_eval = re.search(r'\{.*\}', raw_eval, re.DOTALL).group()
            eval_json = json.loads(clean_eval)
            eval_data.update(eval_json)
        except Exception:
            eval_data['parse_error'] = True

        with open(output_file, 'w', encoding='utf-8') as f_out:
            json.dump(eval_data, f_out, ensure_ascii=False, indent=4)

        return f"Success: {sample_path.name}"

    except Exception as e:
        return f"Error processing {sample_path.name}: {str(e)}"

def main():
    parser = argparse.ArgumentParser(description="Batch Evaluate restored_writing.md")
    parser.add_argument("--model_name", type=str, default="gpt-5.2-2025-12-11")
    parser.add_argument("--workers", type=int, default=20)
    args = parser.parse_args()

    root_path = Path(ROOT_DIR)
    if not root_path.exists():
        print(f"Directory {ROOT_DIR} not found.")
        return

    # 收集所有包含 restored_writing.md 的目录
    tasks = []
    for model_dir in root_path.iterdir():
        if model_dir.is_dir():
            for sample_dir in model_dir.iterdir():
                if sample_dir.is_dir() and (sample_dir / TARGET_FILE).exists():
                    tasks.append(sample_dir)

    print(f"Found {len(tasks)} samples to evaluate.")

    # 初始化模型
    model_instance = GateWays(model_name=args.model_name)
    
    # 线程池执行
    worker_func = partial(process_single_directory, model=model_instance)
    
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        results = list(tqdm(executor.map(worker_func, tasks), total=len(tasks), desc="Evaluating Samples"))

    # 统计简报
    success_count = len([r for r in results if r and r.startswith("Success")])
    print(f"\nEvaluation Finished.")
    print(f"Successfully evaluated: {success_count}/{len(tasks)}")

if __name__ == "__main__":
    main()