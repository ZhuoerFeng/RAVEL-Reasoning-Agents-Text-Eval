import json
import random

def process_code_data(input_file_path, output_file_path, sample_size=50):
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
        # 提取核心字段
        prompt = item.get("text", "")
        target = item.get("code", "")
        
        # 构建新的数据结构
        new_item = {
            "id": f"code_task_{i:05d}",              # 生成新的流水号 ID
            "dataset": "code_generation",            # 由于原数据没有 dataset 字段，这里设定一个默认标识
            "prompt": prompt,
            "target": target,
            "metadata": {
                "task_id": item.get("task_id", ""),
                "test_setup_code": item.get("test_setup_code", ""),
                "test_list": item.get("test_list", []),
                "challenge_test_list": item.get("challenge_test_list", [])
            }
        }
        processed_data.append(new_item)

    # 4. 写入新的 JSONL 文件
    with open(output_file_path, 'w', encoding='utf-8') as f:
        for item in processed_data:
            # ensure_ascii=False 保证可能存在的中文字符正常显示
            f.write(json.dumps(item, ensure_ascii=False) + '\n')
            
    print(f"✅ 处理完成！已将 {len(processed_data)} 条数据保存至 {output_file_path}")

# ================= 使用方法 =================
process_code_data('/workspace/fengzhuoer/andrew/checkpoints/mbpp/data/mbpp.jsonl', 'data/mbpp.jsonl', sample_size=50)