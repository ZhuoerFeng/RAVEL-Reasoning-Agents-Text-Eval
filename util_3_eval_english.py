import json, os
import argparse
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from tqdm import tqdm
import re

# 假设 GateWays 已经正确安装并配置
from glm_api_request.model import GateWays 

from evaluation_prompts import EVALUATION_CLOZE_EN, EVALUATION_CONDITION_EN, EVALUATION_EDIT_EN, EVALUATION_END2END_EN

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_judge_response(model, system_prompt: str, user_message: str) -> str:
    """调用裁判模型获取评价结果"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(
        messages=messages,
        temperature=0, # 评价任务建议低随机性
        max_completion_tokens=1000  
    )
    return response.choices[0].message.content


def process_eval_item(line, model, fout_name):
    """处理单条评价任务"""
    try:
        data = json.loads(line)
        task_type = data.get('task_type', '')
        # 如果是子任务名不同，可以根据 data.get('sub_task') 或 'task_type' 映射
        # 兼容处理：将 'edit' 映射到对应的提示词
        if task_type == 'cloze':
            system_prompt = EVALUATION_CLOZE_EN
        elif task_type == 'condition':
            system_prompt = EVALUATION_CONDITION_EN
        elif task_type == 'edit':
            system_prompt = EVALUATION_EDIT_EN
        elif task_type == 'end2end':
            system_prompt = EVALUATION_END2END_EN

        
        # 构建用户评价请求消息
        candidate = data.get('inference', '')
        reference = data.get('reference', '')
        instruction = data.get('instruction', '')
        
        if task_type == 'cloze':
            inputs = data.get('input', {})
            prefix = inputs.get('prefix', '')
            suffix = inputs.get('suffix', '')
            context = f"{prefix}[fill in the blanks]{suffix}"
            user_message = f"[Context]: {context}\n[Reference]: {reference}\n[Candidate]: {candidate}"
        elif task_type == 'condition':
            outline = data.get('input', {}).get('condition', '')
            user_message = f"[Instruction]: {instruction}\n[Outline]: {outline}\n[Reference]: {reference}\n[Candidate]: {candidate}"
        elif task_type == 'edit':
            user_message = f"[Original]: {data.get('input', {}).get('content', '')}\n[Critique]: {data.get('input', {}).get('critique', '')}\n[Reference]: {reference}\n[Candidate]: {candidate}"
        else: # end2end
            user_message = f"[Instruction]: {instruction}\n[Reference]: {reference}\n[Candidate]: {candidate}"

        # 获取评价结果
        raw_eval = get_judge_response(model, system_prompt, user_message)
        
        # 尝试解析 JSON 评价
        try:
            # 兼容模型可能输出的 markdown 代码块
            clean_eval = re.search(r'\{.*\}', raw_eval, re.DOTALL).group()
            eval_json = json.loads(clean_eval)
            data['eval_result'] = eval_json
            data['score'] = eval_json.get('score', None)
        except:
            print(f"Warning: Failed to parse eval JSON for infer_id {data.get('infer_id')}. Saving raw text.")
            data['eval_result'] = {"raw": raw_eval} # 解析失败则保存原始文本

        # 写入结果
        with open(fout_name, 'a', encoding='utf-8') as f_out:
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data
    except Exception as e:
        print(f"Eval Error: {e}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Batch LLM-as-a-Judge Evaluation.")
    parser.add_argument("--model_name", type=str, default="openrouter:qwen3-8b", help="model to be tested")
    parser.add_argument("--input_file", type=str, default=None)
    parser.add_argument("--output_file", type=str, default=None)
    parser.add_argument("--workers", type=int, default=10)
    args = parser.parse_args()

    if not args.input_file:
        args.input_file = os.path.join('inference_results', 'english', args.model_name + '.jsonl')

    if not args.output_file:
        output_file = f'evaluation_results/english/{args.model_name}.jsonl'
    else:
        output_file = args.output_file
    
    # 增量检查
    processed_ids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                d = json.loads(line)
                processed_ids.add(d.get('infer_id'))


    with open(args.input_file, 'r', encoding='utf-8') as f:
        lines_to_eval = [l for l in f if json.loads(l).get('infer_id') not in processed_ids]

    model_instance = GateWays(model_name='gpt-5.2-2025-12-11')
    worker_func = partial(process_eval_item, model=model_instance, fout_name=output_file)

    print(f"Starting Evaluation: {len(lines_to_eval)} items...")
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        list(tqdm(executor.map(worker_func, lines_to_eval), total=len(lines_to_eval), desc="Evaluating..."))

if __name__ == "__main__":
    main()