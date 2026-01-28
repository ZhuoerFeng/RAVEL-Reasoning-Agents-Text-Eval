import json, os
import re
import argparse
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from glm_api_request.model import GateWays
from tqdm import tqdm

# --- LLM Response Logic ---
model = GateWays(model_name="gpt-5.2-2025-12-11")
model.get_api_result(
    messages=[{"role": "user", "content": "测试模型是否可用"}],
    temperature=0.0,
)
print("模型初始化成功，开始执行脚本...")
exit(0)

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(model, system_prompt: str, user_message: str, max_completion_tokens: int=5000) -> str:
    """Calls the LLM to get the extraction result."""
    messages = [
        {"role": "user", "content": user_message}
    ]
    # 使用传入的 model 实例
    response = model.get_api_result(
        messages=messages,
        temperature=0.7,  
        max_completion_tokens=max_completion_tokens
    )
    return response.choices[0].message.content


def process_extraction_item(line, model, system_prompt, fout_name):
    """Task: Identify and extract the 'Golden Segment'."""
    try:
        data = json.loads(line)
        task_type = data.get('task_type', '')
        instruction = data.get('instruction', '')
        inputs = data.get('input', {})
        reference = data.get('reference', '')
        max_completion_tokens = int(len(reference) * 1.5)

        if task_type == 'cloze':
            user_message = instruction + '\n\n请直接输出填充写作结果，不要额外解释或评论。'
        elif task_type == 'condition':
            outline = inputs.get('outline', '')
            user_message = f"""{instruction}\n\n[大纲]\n{outline}\n请直接输出你的写作，不要额外解释或评论。"""
        elif task_type == 'edit':
            content = inputs.get('content', '')
            critque = inputs.get('critique', '')
            user_message = f"""{instruction}\n\n[原文背景材料]\n{content}\n[初稿材料]\n{critque}\n请直接输你修改后的写作，不要额外解释或评论。"""
        elif task_type == 'end2end':
            user_message = f"""{instruction}\n\n请直接输出你的写作结果，不要额外解释或评论。"""
        else:
            return None

        # Call LLM, pass the model instance
        raw_response = get_llm_response(model, system_prompt, user_message, max_completion_tokens=max_completion_tokens)

        # Merge the extracted fields
        data['inference'] = raw_response

        # Write to file (Thread-safe append)
        with open(fout_name, 'a', encoding='utf-8') as f_out:
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data

    except Exception as e:
        print(f"Row processing error: {e}")
        return None

def main():
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(description="Batch process LLM extraction tasks.")
    
    parser.add_argument("--model_name", type=str, default="gpt-5.2", help="The name of the LLM model to use.")
    parser.add_argument("--input_file", type=str, default="chinese_dataset/chinese_dataset_v2.jsonl", help="Path to the input .jsonl file.")
    parser.add_argument("--output_file", type=str, default=None, help="Path to the output .jsonl file.")
    parser.add_argument("--workers", type=int, default=20, help="Number of concurrent threads (default: 20).")
    
    args = parser.parse_args()
    
    if args.output_file is None:
        output_file = f'inference_results/chinese/{args.model_name}.jsonl'
    else:
        output_file = args.output_file
    args.output_file = output_file


    # --- 1. 读取原始数据 ---
    if not os.path.exists(args.input_file):
        print(f"Error: Input file {args.input_file} not found.")
        return

    with open(args.input_file, 'r', encoding='utf-8') as f_in:
        all_lines = f_in.readlines()

    # --- 2. 增量检查逻辑 ---
    processed_ids = set()
    if os.path.exists(args.output_file):
        print(f"Output file '{args.output_file}' exists. Loading processed records...")
        with open(args.output_file, 'r', encoding='utf-8') as f_out_check:
            for line in f_out_check:
                try:
                    existing_data = json.loads(line)
                    if 'infer_id' in existing_data:
                        processed_ids.add(existing_data['infer_id'])
                except json.JSONDecodeError:
                    continue
        print(f"Found {len(processed_ids)} already processed records.")

    # 过滤掉已存在的 infer_id
    lines_to_process = []
    for line in all_lines:
        try:
            data = json.loads(line)
            if data.get('infer_id') not in processed_ids:
                lines_to_process.append(line)
        except json.JSONDecodeError:
            continue

    total_count = len(all_lines)
    process_count = len(lines_to_process)
    skip_count = total_count - process_count

    if process_count == 0:
        print("All items have been processed already. Exiting.")
        return

    print(f"Total: {total_count} | Skipped: {skip_count} | To Process: {process_count}")

    # --- Model Initialization ---
    # 在解析参数后初始化模型
    model_instance = GateWays(model_name=args.model_name)

    # 使用 partial 预填充固定参数
    worker_func = partial(
        process_extraction_item, 
        model=model_instance, 
        system_prompt="", 
        fout_name=output_file
    )

    # --- Execution ---
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        # 使用 list 强制迭代完成 tqdm
        list(tqdm(executor.map(worker_func, lines_to_process), total=process_count, desc="Inference Progress on Chinese..."))
        

if __name__ == "__main__":
    main()