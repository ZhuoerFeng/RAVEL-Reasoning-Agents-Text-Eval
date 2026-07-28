import os
import json
import random
import glob
from tqdm import tqdm
from transformers import AutoTokenizer

# ================= 配置区 =================
DATA_ROOT = "/workspace/fengzhuoer/andrew/checkpoints/RedPajama-Data-1T"
OUTPUT_FILE = "data/processed_redpajama_eval.jsonl"

DOMAINS = ["arxiv", "c4"]
SAMPLES_PER_DOMAIN = 2000  # 每个子集抽样的数量
MIN_TOKENS = 512
MAX_TOKENS = 1024
PROMPT_LENGTH = 50
SAMPLE_PROBABILITY = 0.05  # 读取每行时抽取的概率，保证跨文件随机性

# 使用 GPT-2 tokenizer 作为快速的分词基准（你也可以换成 Llama 的 tokenizer）
print("Loading Tokenizer...")
tokenizer = AutoTokenizer.from_pretrained("gpt2", use_fast=True)
# =========================================

def process_domain(domain_name, output_file_handle):
    domain_path = os.path.join(DATA_ROOT, domain_name)
    file_pattern = os.path.join(domain_path, "*.jsonl")
    files = glob.glob(file_pattern)
    
    if not files:
        print(f"警告：在 {domain_path} 下未找到 .jsonl 文件。")
        return
    
    # 打乱文件顺序，避免总是从同一个文件采样
    random.shuffle(files)
    
    collected_samples = 0
    pbar = tqdm(total=SAMPLES_PER_DOMAIN, desc=f"Processing {domain_name}")
    
    for file_path in files:
        if collected_samples >= SAMPLES_PER_DOMAIN:
            break
            
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if collected_samples >= SAMPLES_PER_DOMAIN:
                    break
                    
                # 以一定概率跳过，确保样本均匀分布在文件不同位置
                if random.random() > SAMPLE_PROBABILITY:
                    continue
                    
                try:
                    data = json.loads(line)
                    text = data.get("text", "")
                    
                    if not text:
                        continue
                        
                    # 快速粗略过滤：如果字符数太少，直接跳过以节省 Tokenizer 时间
                    if len(text) < MIN_TOKENS * 3:
                        continue
                        
                    # Tokenize 文本
                    tokens = tokenizer.encode(text, truncation=False)
                    
                    # 检查长度是否符合要求
                    if len(tokens) >= MIN_TOKENS:
                        # 截断到最大允许的 Token 数
                        tokens = tokens[:MAX_TOKENS]
                        
                        # 划分 Prompt 和 Target
                        prompt_tokens = tokens[:PROMPT_LENGTH]
                        target_tokens = tokens[PROMPT_LENGTH:]
                        
                        # 解码回文本
                        prompt_text = tokenizer.decode(prompt_tokens, skip_special_tokens=True)
                        target_text = tokenizer.decode(target_tokens, skip_special_tokens=True)
                        
                        # 构建标准化的 JSONL 记录
                        record = {
                            "id": f"redpajama_{domain_name}_{collected_samples:05d}",
                            "dataset": "RedPajama",
                            "prompt": prompt_text,
                            "target": target_text,
                            "metadata": {
                                "split": "pretrain",
                                "type": domain_name,
                                "original_length_tokens": len(tokens)
                            }
                        }
                        
                        output_file_handle.write(json.dumps(record, ensure_ascii=False) + "\n")
                        
                        collected_samples += 1
                        pbar.update(1)
                        
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"处理行时出错: {e}")
                    continue

    pbar.close()
    print(f"完成 {domain_name} 的处理，共收集 {collected_samples} 条样本。")

def main():
    print(f"输出文件将保存至: {OUTPUT_FILE}")
    # 确保输出目录存在
    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as out_f:
        for domain in DOMAINS:
            process_domain(domain, out_f)
            
    print("所有数据预处理完成！")

if __name__ == "__main__":
    main()
