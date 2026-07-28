# import os
# import json
# from tqdm import tqdm
# from rouge_score import rouge_scorer

# from glm_api_request.model import GateWays

# # ⚠️ 注意：请确保你在这里导入了你封装的 GateWays 类
# # from your_api_module import GateWays

# # ================= 配置区 =================
# INPUT_DATA_PATH = "data/processed_redpajama_eval.jsonl"
# OUTPUT_DIR = "results/"

# # 要测试的 API 模型名称列表
# MODEL_NAMES = [
#     "gpt-5.2-2025-12-11",
#     "openrouter:gemini-3.1-pro-preview",
#     # "qwen3-32b",
#     # "openrouter:qwen3-32b",
#     # "qwen3-max-2025-09-23"
# ]
# # =========================================

# class RobustAPIEvaluator:
#     def __init__(self, output_dir):
#         self.output_dir = output_dir
#         os.makedirs(self.output_dir, exist_ok=True)
#         # 初始化 ROUGE 评估器
#         self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)

#     def load_data(self, data_path):
#         data = []
#         with open(data_path, 'r', encoding='utf-8') as f:
#             for line in f:
#                 data.append(json.loads(line.strip()))
#         return data

#     def calculate_rouge(self, reference, prediction):
#         scores = self.scorer.score(reference, prediction)
#         return {"rouge1": scores['rouge1'].fmeasure, "rougeL": scores['rougeL'].fmeasure}

#     def evaluate_model(self, model_name, dataset):
#         print(f"\n{'='*50}\n🚀 开始评估 API 模型: {model_name}\n{'='*50}")
        
#         # 替换模型名称中的冒号（如 openrouter:xxx），避免在某些系统下创建文件路径报错
#         safe_model_name = model_name.replace(":", "_")
#         output_file = os.path.join(self.output_dir, f"{safe_model_name}_eval_results.jsonl")
        
#         # 1. 鲁棒性设计：断点续传检查
#         processed_ids = set()
#         if os.path.exists(output_file):
#             with open(output_file, 'r', encoding='utf-8') as f:
#                 for line in f:
#                     try:
#                         record = json.loads(line)
#                         processed_ids.add(record['id'])
#                     except json.JSONDecodeError:
#                         pass
#             print(f"📦 发现已存在的进度，已跳过 {len(processed_ids)} 条已处理数据。")

#         # 2. 初始化 API 客户端
#         print(f"⏳ 正在初始化 GateWays API 客户端 ({model_name})...")
#         try:
#             model = GateWays(model_name=model_name)
#         except Exception as e:
#             print(f"❌ 初始化模型 {model_name} 失败: {e}")
#             return

#         # 3. 遍历数据进行评估
#         with open(output_file, 'a', encoding='utf-8') as out_f:
#             for sample in tqdm(dataset, desc=f"Evaluating {model_name}"):
#                 if sample['id'] in processed_ids:
#                     continue

#                 prompt = sample['prompt']
#                 target = sample['target']

#                 try:
#                     # --- 构造 API 消息 ---
#                     messages = [
#                         {"role": "system", "content": "你是一个有帮助的助手，协助用户完成任务。"},
#                         {"role": "user", "content": prompt}
#                     ]
                    
#                     # --- 调用 API 获取结果 ---
#                     # 假设 get_api_result 返回的是生成的文本字符串
#                     generated_text = model.get_api_result(messages=messages)
                    
#                     # 兜底处理：防止 API 请求失败返回 None 导致计算报错
#                     if not generated_text:
#                         generated_text = ""

#                     # --- 计算 ROUGE ---
#                     rouge_scores = self.calculate_rouge(target, str(generated_text))

#                     # --- 保存结果 ---
#                     result_record = {
#                         "id": sample['id'],
#                         "model": model_name,
#                         "metrics": {
#                             "rouge1": rouge_scores['rouge1'],
#                             "rougeL": rouge_scores['rougeL']
#                         },
#                         "generation": generated_text # 保存生成结果以便后续做人工抽查 (Qualitative Analysis)
#                     }
#                     out_f.write(json.dumps(result_record, ensure_ascii=False) + "\n")
#                     out_f.flush() # 实时刷入磁盘，防止意外崩溃导致数据丢失

#                 except Exception as e:
#                     print(f"\n⚠️ 处理样本 {sample['id']} 时出错: {e}")
#                     continue

#         print(f"✅ 模型 {model_name} 评估完成！")

# def main():
#     evaluator = RobustAPIEvaluator(output_dir=OUTPUT_DIR)
    


import os
import json
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from tqdm import tqdm
from rouge_score import rouge_scorer
import random
random.seed(42)

# from glm_api_request.model import GateWays

import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from openai import OpenAI
# import openai
# print(openai.__version__)

class GateWays:
    def __init__(self, model_name):
        self.model = model_name
        self.api_url = "https://api-gateway.glm.ai/v1"
        # self.api_key = "sk-UN3MFcgYI45WzE1tHNOnaYfTmqws7HEa"  
        self.api_key = "sk-Urj7TELvsNnT51kEKyMrBpmCb7AbRLrH"
        # cx api
        # self.api_key = "sk-RQ7TUKpjoUwA6pmRe7tFyHudvMLkV60R"

        self.client = OpenAI(base_url=self.api_url, api_key=self.api_key)
        

    def get_api_result(self, messages:list, tools: list = None, temperature: float = 1.0, max_completion_tokens: int = 5000):
        response = self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            tools=tools,
            max_completion_tokens=max_completion_tokens,
            temperature=temperature,
            timeout=120,
        )
        # print(response)
        return response.choices[0].message.content
        # return response
    

# ================= 配置区 =================
INPUT_DATA_PATH = "data/processed_redpajama_eval.jsonl"
OUTPUT_DIR = "results/"

MAX_WORKERS = 20  # 设置并发请求数

# 要测试的 API 模型名称列表
MODEL_NAMES = [
    "gpt-5.2-2025-12-11",
    "openrouter:gemini-3.1-pro-preview",
    # "qwen3-32b",
    # "openrouter:qwen3-32b",
    # "qwen3-max-2025-09-23"
]
# =========================================

class RobustAPIEvaluator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        # 初始化 ROUGE 评估器
        self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
        # 增加文件写入锁，确保多线程下日志写入不会错乱
        self.file_lock = threading.Lock()

    def load_data(self, data_path):
        data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line.strip()))
        if len(data) > 2000:
            data = random.sample(data, 100)
        return data

    def calculate_rouge(self, reference, prediction):
        scores = self.scorer.score(reference, prediction)
        return {"rouge1": scores['rouge1'].fmeasure, "rougeL": scores['rougeL'].fmeasure}

    def _process_sample(self, sample, model, model_name):
        """被线程池调用的单条数据处理逻辑"""
        prompt = sample['prompt']
        target = sample['target']
        sample_id = sample['id']

        try:
            # --- 构造 API 消息 ---
            messages = [
                {"role": "system", "content": "你是一个有帮助的助手，协助用户完成任务。"},
                {"role": "user", "content": prompt}
            ]
            
            # --- 调用 API 获取结果 ---
            generated_text = model.get_api_result(messages=messages)
            
            if not generated_text:
                generated_text = ""

            # --- 计算 ROUGE ---
            rouge_scores = self.calculate_rouge(target, str(generated_text))

            # --- 构造结果 ---
            result_record = {
                "id": sample_id,
                "model": model_name,
                "metrics": {
                    "rouge1": rouge_scores['rouge1'],
                    "rougeL": rouge_scores['rougeL']
                },
                "generation": generated_text
            }
            # 返回成功结果
            return sample_id, result_record, None

        except Exception as e:
            # 返回失败结果及报错信息
            return sample_id, None, str(e)

    def evaluate_model(self, model_name, dataset):
        print(f"\n{'='*50}\n🚀 开始评估 API 模型: {model_name} (并发数: {MAX_WORKERS})\n{'='*50}")
        
        safe_model_name = model_name.replace(":", "_")
        output_file = os.path.join(self.output_dir, f"{safe_model_name}_eval_results.jsonl")
        
        # 1. 鲁棒性设计：断点续传检查
        processed_ids = set()
        if os.path.exists(output_file):
            with open(output_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        record = json.loads(line)
                        processed_ids.add(record['id'])
                    except json.JSONDecodeError:
                        pass
            print(f"📦 发现已存在的进度，已跳过 {len(processed_ids)} 条已处理数据。")

        # 筛选出尚未处理的数据
        pending_dataset = [sample for sample in dataset if sample['id'] not in processed_ids]
        if not pending_dataset:
            print(f"✅ 模型 {model_name} 的所有测试数据已评估完毕！")
            return

        # 2. 初始化 API 客户端
        print(f"⏳ 正在初始化 GateWays API 客户端 ({model_name})...")
        try:
            model = GateWays(model_name=model_name)
        except Exception as e:
            print(f"❌ 初始化模型 {model_name} 失败: {e}")
            return

        # 3. 启动多线程进行并发评估
        with open(output_file, 'a', encoding='utf-8') as out_f:
            with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
                
                # 提交所有任务到线程池
                futures = {
                    executor.submit(self._process_sample, sample, model, model_name): sample 
                    for sample in pending_dataset
                }
                
                # as_completed 会在某个线程完成时立刻 yield
                for future in tqdm(as_completed(futures), total=len(pending_dataset), desc=f"Evaluating {model_name}"):
                    sample_id, result_record, error = future.result()
                    
                    if error:
                        # 使用 tqdm.write 避免多线程打印破坏进度条的 UI 渲染
                        tqdm.write(f"⚠️ 处理样本 {sample_id} 时出错: {error}")
                        continue
                        
                    if result_record:
                        # ✨ 加锁写入文件：保证多线程下每行 JSONL 结构完整 ✨
                        with self.file_lock:
                            out_f.write(json.dumps(result_record, ensure_ascii=False) + "\n")
                            out_f.flush()

        print(f"✅ 模型 {model_name} 评估完成！")

def main():
    evaluator = RobustAPIEvaluator(output_dir=OUTPUT_DIR)
    
    print(f"📥 正在加载数据集: {INPUT_DATA_PATH}")
    dataset = evaluator.load_data(INPUT_DATA_PATH)
    print(f"📊 共加载 {len(dataset)} 条测试数据。")

    for model_name in MODEL_NAMES:
        evaluator.evaluate_model(model_name, dataset)
        
    print("\n🎉 所有模型评估完毕！结果已保存在 results/ 目录下。")

if __name__ == "__main__":
    main()