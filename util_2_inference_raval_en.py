import json
import concurrent.futures
from functools import partial
from tqdm import tqdm # 进度条库，建议安装：pip install tqdm
from typing import List
import argparse
from core_agents_en import WritingState, WritingTools, WritingManager

# ... [保留你原有的 import 和类定义: WritingState, WritingTools, WritingManager, extract_json_from_llm, get_llm_response] ...

def run_single_writing_task(task_data: dict, model_name: str = "deepseek-v3.2") -> dict:
    """
    单个写作任务的执行函数
    task_data 格式示例: {"instruction": "关于AI的看法", "style": "科普"}
    """
    topic = task_data.get("instruction", "")
    infer_id = task_data.get("infer_id", "")
    style_guide = task_data.get("sub_task", "easy to understand") # 默认风格
    save_dir = f'ravel_results/english/{model_name}/{infer_id}' 
    
    if not topic:
        return {"status": "error", "message": "Empty topic"}

    try:
        print(f"\n>>> 开始处理任务: {topic[:20]}...")
        manager = WritingManager(topic, style_guide, model_name=model_name, save_dir=save_dir)
        manager.execute()
        return {"status": "success", "topic": topic}
    except Exception as e:
        print(f"\n [!] 任务执行失败: {topic[:20]} | 错误: {e}")
        return {"status": "failed", "topic": topic, "error": str(e)}


def batch_process(data_list: str, model_name: str, max_workers: int = 3):
    """
    使用线程池并行处理任务
    """
    print(f"开始并行处理任务，最大线程数: {max_workers}")
    
    results = []
    # 使用 ThreadPoolExecutor 处理 I/O 密集型 API 请求
    with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务到线程池
        # 使用 partial 或者 lambda 来传递额外的 model_name 参数
        future_to_task = {
            executor.submit(run_single_writing_task, item, model_name): item 
            for item in data_list
        }
        
        # 使用 tqdm 显示进度条
        for future in tqdm(concurrent.futures.as_completed(future_to_task), total=len(data_list), desc="Processing Tasks"):
            task = future_to_task[future]
            try:
                result = future.result()
                results.append(result)
            except Exception as exc:
                print(f'\n [!] 任务生成了未预料的异常: {exc}')
                results.append({"status": "error", "error": str(exc)})
    
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch process LLM extraction tasks.")
    
    parser.add_argument("--model_name", type=str, default="gpt-5.2", help="The name of the LLM model to use.")
    parser.add_argument("--input_file", type=str, default="english_dataset/english_dataset.jsonl", help="Path to the input .jsonl file.")
    parser.add_argument("--output_file", type=str, default=None, help="Path to the output .jsonl file.")
    parser.add_argument("--workers", type=int, default=20, help="Number of concurrent threads (default: 20).")
    
    args = parser.parse_args()

    model_name = args.model_name
    
    # 输入文件 a.jsonl
    # 每一行可以是: {"instruction": "xxx", "style": "xxx"} 
    # 或者直接是纯文本指令
    fin = open(args.input_file).readlines()
    data = []
    for line in fin:
        line = json.loads(line)
        if line['task_type'] != 'end2end':
            continue
        data.append(line)
    print(f"Loaded {len(data)} end2end tasks from {args.input_file}")
    
    # 注意：根据你的 API 额度和 QPS 限制设置 max_workers
    # 如果是 DeepSeek 等线上 API，建议设置 1-3 避免触发频率限制
    # batch_process(INPUT_FILENAME, max_workers=2)


    # for item in data:
    #     run_single_writing_task(item, model_name=model_name)
    #     exit(0)

    batch_process(data, model_name=args.model_name, max_workers=args.workers)
    print("\n>>> 所有任务处理完成。")

