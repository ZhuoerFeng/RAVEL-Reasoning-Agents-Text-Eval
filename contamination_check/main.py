import os
import json
import torch
import numpy as np
import gc
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from rouge_score import rouge_scorer

# ================= 配置区 =================
INPUT_DATA_PATH = "data/processed_redpajama_eval.jsonl"
OUTPUT_DIR = "results/"

# 要测试的模型路径列表
MODEL_PATHS = [
    "/workspace/fengzhuoer/andrew/checkpoints/Qwen3-0.6B",
    "/workspace/fengzhuoer/andrew/checkpoints/Qwen3-1.7B",
    "/workspace/fengzhuoer/andrew/checkpoints/Qwen3-4B",
    "/workspace/fengzhuoer/andrew/checkpoints/Qwen3-8B",
    "/workspace/fengzhuoer/andrew/checkpoints/Llama-3.2-1B",
    "/workspace/fengzhuoer/andrew/checkpoints/Llama-3.2-1B-Instruct",
    "/workspace/fengzhuoer/andrew/checkpoints/Llama-3.1-8B",
    "/workspace/fengzhuoer/andrew/checkpoints/Llama-3.1-8B-Instruct",
    "/workspace/fengzhuoer/andrew/checkpoints/GLM-4-9B-0414"
]

MIN_K_RATIO = 0.2  # 计算 min-20% prob
MAX_NEW_TOKENS = 128 # ROUGE 生成时的最大长度
# =========================================

class RobustEvaluator:
    def __init__(self, output_dir):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)
        self.scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)

    def load_data(self, data_path):
        data = []
        with open(data_path, 'r', encoding='utf-8') as f:
            for line in f:
                data.append(json.loads(line.strip()))
        return data

    def calculate_rouge(self, reference, prediction):
        scores = self.scorer.score(reference, prediction)
        return {"rouge1": scores['rouge1'].fmeasure, "rougeL": scores['rougeL'].fmeasure}

    def evaluate_model(self, model_path, dataset):
        model_name = os.path.basename(model_path)
        print(f"\n{'='*50}\n🚀 开始评估模型: {model_name}\n{'='*50}")
        
        output_file = os.path.join(self.output_dir, f"{model_name}_eval_results.jsonl")
        
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

        # 2. 加载模型与分词器 (自动分配显存，使用 bf16 节省内存)
        print("⏳ 正在加载 Tokenizer 和 Model...")
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
            if tokenizer.pad_token is None:
                tokenizer.pad_token = tokenizer.eos_token

            model = AutoModelForCausalLM.from_pretrained(
                model_path,
                device_map="auto",
                torch_dtype=torch.bfloat16,
                trust_remote_code=True
            )
            model.eval()
        except Exception as e:
            print(f"❌ 加载模型 {model_name} 失败: {e}")
            return

        # 3. 遍历数据进行评估
        with open(output_file, 'a', encoding='utf-8') as out_f:
            for sample in tqdm(dataset, desc=f"Evaluating {model_name}"):
                if sample['id'] in processed_ids:
                    continue

                prompt = sample['prompt']
                target = sample['target']

                try:
                    # --- 指标 A: 计算 PPL 和 min-K% Prob ---
                    # 严谨的 Token 拼接方式，避免特殊字符边界问题
                    prompt_ids = tokenizer.encode(prompt, add_special_tokens=True)
                    target_ids = tokenizer.encode(target, add_special_tokens=False)
                    
                    if len(target_ids) == 0:
                        continue
                        
                    input_ids = torch.tensor([prompt_ids + target_ids]).to(model.device)
                    target_len = len(target_ids)

                    with torch.no_grad():
                        outputs = model(input_ids)
                        logits = outputs.logits
                        
                    # 计算 Loss 和 Logprobs
                    shift_logits = logits[..., :-1, :].contiguous()
                    shift_labels = input_ids[..., 1:].contiguous()
                    loss_fct = torch.nn.CrossEntropyLoss(reduction='none')
                    loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
                    
                    logprobs = -loss.cpu().numpy().flatten()
                    
                    # 仅截取 Target 部分的 logprobs
                    target_logprobs = logprobs[-target_len:]
                    
                    ppl = float(np.exp(-np.mean(target_logprobs)))
                    
                    k_count = max(1, int(len(target_logprobs) * MIN_K_RATIO))
                    min_k_prob = float(np.mean(np.sort(target_logprobs)[:k_count]))

                    # --- 指标 B: 贪心生成计算 ROUGE ---
                    prompt_tensor = torch.tensor([prompt_ids]).to(model.device)
                    with torch.no_grad():
                        generated_ids = model.generate(
                            prompt_tensor, 
                            max_new_tokens=MAX_NEW_TOKENS, 
                            temperature=0.0,
                            do_sample=False,
                            pad_token_id=tokenizer.pad_token_id
                        )
                    
                    # 截取新生成的部分
                    gen_tokens = generated_ids[0][len(prompt_ids):]
                    generated_text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
                    
                    rouge_scores = self.calculate_rouge(target, generated_text)

                    # --- 保存结果 ---
                    result_record = {
                        "id": sample['id'],
                        "model": model_name,
                        "metrics": {
                            "ppl": ppl,
                            "min_k_prob": min_k_prob,
                            "rouge1": rouge_scores['rouge1'],
                            "rougeL": rouge_scores['rougeL']
                        },
                        "generation": generated_text # 保存生成结果以便后续做人工抽查 (Qualitative Analysis)
                    }
                    out_f.write(json.dumps(result_record, ensure_ascii=False) + "\n")
                    out_f.flush() # 实时刷入磁盘，防止意外崩溃导致数据丢失

                except Exception as e:
                    print(f"\n⚠️ 处理样本 {sample['id']} 时出错: {e}")
                    continue

        # 4. 鲁棒性设计：显存清理
        print(f"✅ 模型 {model_name} 评估完成，正在清理显存...")
        del model
        del tokenizer
        gc.collect()
        torch.cuda.empty_cache()

def main():
    evaluator = RobustEvaluator(output_dir=OUTPUT_DIR)
    
    print(f"📥 正在加载数据集: {INPUT_DATA_PATH}")
    dataset = evaluator.load_data(INPUT_DATA_PATH)
    print(f"📊 共加载 {len(dataset)} 条测试数据。")

    for model_path in MODEL_PATHS:
        evaluator.evaluate_model(model_path, dataset)
        
    print("\n🎉 所有模型评估完毕！结果已保存在 results/ 目录下。")

if __name__ == "__main__":
    main()

