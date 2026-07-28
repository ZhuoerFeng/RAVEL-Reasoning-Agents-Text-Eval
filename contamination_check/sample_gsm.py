import json
import random

def process_gsm8k_data(input_file_path, output_file_path, sample_size=50):
    # 1. 读取所有原始数据
    raw_data = []
    with open(input_file_path, 'r', encoding='utf-8') as f:
        for line in f:
            if line.strip():
                raw_data.append(json.loads(line))
    
    # 2. 随机抽样 50 条（如果总数据量少于 50，则全部保留）
    if len(raw_data) > sample_size:
        sampled_data = random.sample(raw_data, sample_size)
    else:
        sampled_data = raw_data
        print(f"提示：原始数据不足 {sample_size} 条，已处理全部 {len(raw_data)} 条数据。")

    # 3. 格式转换
    processed_data = []
    for i, item in enumerate(sampled_data):
        # 提取 prompt (从 prompt 列表中获取第一个元素)
        prompt_list = item.get("prompt", [])
        prompt = prompt_list[0].get("content", "") if prompt_list else ""
        
        # 提取 target (从 extra_info 中获取)
        extra_info = item.get("extra_info", {})
        target = extra_info.get("answer", "")
        
        # 提取其他 metadata 字段
        reward_model = item.get("reward_model", {})
        data_source = item.get("data_source", "unknown_dataset")
        
        # 构建新的数据结构
        new_item = {
            "id": f"math_gsm8k_{i:05d}",             # 重新生成流水号 ID
            "dataset": data_source,                  # openai/gsm8k
            "prompt": prompt,
            "target": target,
            "metadata": {
                "ability": item.get("ability", ""),
                "ground_truth": reward_model.get("ground_truth", ""),
                "split": extra_info.get("split", ""),
                "original_index": extra_info.get("index", "")
            }
        }
        processed_data.append(new_item)

    # 4. 写入新的 JSONL 文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for item in processed_data:
            # ensure_ascii=False 保证特殊字符/中文正常显示
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"✅ 处理完成！已将 {len(processed_data)} 条数据保存至 {output_file_path}")

# ================= 使用方法 =================
process_gsm8k_data('/workspace/fengzhuoer/andrew/data/gsm8k/test_100.json', 'data/gsm8k.jsonl', sample_size=50)