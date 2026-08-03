import os
import json
import torch
import numpy as np
import gc
import math
import torch.multiprocessing as mp
from tqdm import tqdm
from transformers import AutoModelForCausalLM, AutoTokenizer
from rouge_score import rouge_scorer
import traceback

# ================= 配置区 =================
INPUT_DATA_PATH = "data/mbpp.jsonl"
OUTPUT_DIR = "results_mbpp/"
NUM_GPUS = 8  # 你的 H100 数量

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

MIN_K_RATIO = 0.2
MAX_NEW_TOKENS = 128
# =========================================

def calculate_rouge(scorer, reference, prediction):
    scores = scorer.score(reference, prediction)
    return {"rouge1": scores['rouge1'].fmeasure, "rougeL": scores['rougeL'].fmeasure}

def worker_process(gpu_id, model_path, data_chunk, output_dir):
    """
    单个 GPU 的工作进程
    """
    model_name = os.path.basename(model_path)
    output_file = os.path.join(output_dir, f"{model_name}_gpu{gpu_id}_temp.jsonl")
    
    # 初始化 ROUGE 评估器
    scorer = rouge_scorer.RougeScorer(['rouge1', 'rougeL'], use_stemmer=True)
    
    # 断点续传检查（针对单个卡的分片文件）
    processed_ids = set()
    if os.path.exists(output_file):
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    record = json.loads(line)
                    processed_ids.add(record['id'])
                except json.JSONDecodeError:
                    pass
                    
    # 强制将模型加载到指定的 GPU 上
    device = f"cuda:{gpu_id}"
    try:
        tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(
            model_path,
            device_map={"": gpu_id}, # 核心优化：只加载到当前 worker 分配的 GPU
            torch_dtype=torch.bfloat16,
            trust_remote_code=True
        )
        model.eval()
    except Exception as e:
        print(f"❌ [GPU {gpu_id}] 加载模型失败: {e}")
        return

    # 为避免多个 tqdm 进度条在终端打架，只让 GPU 0 显示进度条，其他后台默默跑
    iterable = tqdm(data_chunk, desc=f"GPU {gpu_id} Processing") if gpu_id == 0 else data_chunk

    for sample in iterable:
        if sample['id'] in processed_ids:
            continue

        prompt, target = sample['prompt'], sample['target']

        try:
            prompt_ids = tokenizer.encode(prompt, add_special_tokens=True)
            target_ids = tokenizer.encode(target, add_special_tokens=False)
            
            if len(target_ids) == 0: continue
                
            input_ids = torch.tensor([prompt_ids + target_ids]).to(device)
            target_len = len(target_ids)

            # --- 1. 计算 PPL 和 min-K% ---
            with torch.no_grad():
                outputs = model(input_ids)
                logits = outputs.logits
                
            shift_logits = logits[..., :-1, :].contiguous()
            shift_labels = input_ids[..., 1:].contiguous()
            loss_fct = torch.nn.CrossEntropyLoss(reduction='none')
            loss = loss_fct(shift_logits.view(-1, shift_logits.size(-1)), shift_labels.view(-1))
            
            logprobs = -loss.float().cpu().numpy().flatten()
            target_logprobs = logprobs[-target_len:]
            
            ppl = float(np.exp(-np.mean(target_logprobs)))
            k_count = max(1, int(len(target_logprobs) * MIN_K_RATIO))
            min_k_prob = float(np.mean(np.sort(target_logprobs)[:k_count]))

            # --- 2. 贪心生成计算 ROUGE ---
            prompt_tensor = torch.tensor([prompt_ids]).to(device)
            with torch.no_grad():
                generated_ids = model.generate(
                    prompt_tensor, 
                    max_new_tokens=MAX_NEW_TOKENS, 
                    temperature=0.0,
                    do_sample=False,
                    pad_token_id=tokenizer.pad_token_id
                )
            
            gen_tokens = generated_ids[0][len(prompt_ids):]
            generated_text = tokenizer.decode(gen_tokens, skip_special_tokens=True)
            rouge_scores = calculate_rouge(scorer, target, generated_text)

            # --- 保存结果 ---
            record = {
                "id": sample['id'],
                "model": model_name,
                "metrics": {"ppl": ppl, "min_k_prob": min_k_prob, "rouge1": rouge_scores['rouge1'], "rougeL": rouge_scores['rougeL']},
                "generation": generated_text
            }

            with open(output_file, 'a', encoding='utf-8') as out_f:
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
            out_f.close()

        except Exception as e:
            # 记录但不中断程序
            # 打印带trace报错
            print(f"❌ [GPU {gpu_id}] 处理样本 {sample['id']} 时出错: {e}")
            traceback.print_exc()
            continue

    # 释放单卡的显存
    del model
    del tokenizer
    torch.cuda.empty_cache()

def main():
    # 必须设置为 spawn，否则多进程在 CUDA 环境下会死锁
    mp.set_start_method('spawn', force=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    # 读取全量数据
    data = []
    with open(INPUT_DATA_PATH, 'r', encoding='utf-8') as f:
        for line in f:
            data.append(json.loads(line.strip()))
            
    print(f"📊 共加载 {len(data)} 条测试数据。即将分配至 {NUM_GPUS} 张 H100。")

    # 等分数据切片
    chunk_size = math.ceil(len(data) / NUM_GPUS)
    data_chunks = [data[i:i + chunk_size] for i in range(0, len(data), chunk_size)]

    for model_path in MODEL_PATHS:
        model_name = os.path.basename(model_path)
        print(f"\n{'='*50}\n🚀 开始并行评估模型: {model_name}\n{'='*50}")

        # 启动多进程
        processes = []
        for gpu_id in range(min(NUM_GPUS, len(data_chunks))):
            p = mp.Process(
                target=worker_process, 
                args=(gpu_id, model_path, data_chunks[gpu_id], OUTPUT_DIR)
            )
            p.start()
            processes.append(p)

        # 阻塞主进程，等待所有 8 个 GPU 的任务全部完成
        for p in processes:
            p.join()
            
        print(f"✅ {model_name} 各节点计算完毕，正在合并结果文件...")
        
        # 将 8 个 temp 文件合并成一个最终文件，并删除 temp 文件
        final_output_file = os.path.join(OUTPUT_DIR, f"{model_name}_eval_results.jsonl")
        with open(final_output_file, 'w', encoding='utf-8') as outfile:
            for gpu_id in range(NUM_GPUS):
                temp_file = os.path.join(OUTPUT_DIR, f"{model_name}_gpu{gpu_id}_temp.jsonl")
                if os.path.exists(temp_file):
                    with open(temp_file, 'r', encoding='utf-8') as infile:
                        for line in infile:
                            outfile.write(line)
                    os.remove(temp_file) # 合并后清理碎片文件
                    
        print(f"🎉 {model_name} 测试完成！结果统一保存在: {final_output_file}")

if __name__ == "__main__":
    main()
    