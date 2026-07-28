import json
import random

def process_and_sample_data(input_file_path, output_file_path, sample_size=50):
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
        # 提取并拼接 instruction 和 input 中的所有 value
        instruction = item.get("instruction", "")
        input_dict = item.get("input", {})
        # 将 input 字典中的所有值按原顺序拼接
        input_values = "\n".join(str(val) for val in input_dict.values())
        
        prompt = f"{instruction}\n{input_values}"
        target = item.get("reference", "")
        
        # 构建新的数据结构
        new_item = {
            "id": f"cloze_cn_{i:05d}",               # 重新生成流水号 ID
            "dataset": item.get("task_type", ""),    # 使用原 task_type 作为 dataset
            "prompt": prompt,
            "target": target,
            "metadata": {
                "sub_task": item.get("sub_task", ""),
                "old_id": item.get("meta", {}).get("old_id", "")
            }
        }
        processed_data.append(new_item)

    # 4. 写入新的 JSONL 文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for item in processed_data:
            # ensure_ascii=False 保证中文字符正常显示，不被转义为 Unicode
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"✅ 处理完成！已将 {len(processed_data)} 条数据保存至 {output_file_path}")

# ================= 使用方法 =================
# 假设你的原始数据保存在 raw_data.jsonl，你想输出到 processed_data.jsonl
# process_and_sample_data('../english_dataset/english_dataset.jsonl', 'data/english_c3e.jsonl', sample_size=50)
process_and_sample_data('../chinese_dataset/chinese_dataset_v2.jsonl', 'data/chinese_c3e.jsonl', sample_size=50)