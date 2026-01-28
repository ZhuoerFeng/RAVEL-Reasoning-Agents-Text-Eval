import json

def process_validation(input_file: str, output_file: str):
    """
    串行处理：校验 LLM 提取的段落是否能从原文中准确还原
    """
    valid_count = 0
    total_count = 0

    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip():
                continue
            
            total_count += 1
            data = json.loads(line)
            content = data.get('content', '')
            selection = data.get('step1_selection', {})
            
            start_target = selection.get('start_sentence', '').strip()
            end_target = selection.get('end_sentence', '').strip()
            llm_segment = selection.get('selected_segment', '').strip()
            expected_length = selection.get('segment_length', 0)

            # 1. 定位起始和结束句子的位置
            # 使用 find 寻找第一次出现的 start_sentence
            start_idx = content.find(start_target)
            if start_idx == -1:
                print(f"跳过: 找不到起始句 -> {data.get('title')}")
                continue
                
            # 从 start_idx 之后寻找第一次出现的 end_sentence
            end_search_start = start_idx + len(start_target)
            end_rel_idx = content[end_search_start:].find(end_target)
            
            if end_rel_idx == -1:
                print(f"跳过: 找不到结束句 -> {data.get('title')}")
                continue
            
            # 计算绝对结束位置（包含结束句本身）
            end_idx = end_search_start + end_rel_idx + len(end_target)

            # 2. 提取三块内容
            prefix = content[:start_idx]
            extracted_middle = content[start_idx:end_idx]
            suffix = content[end_idx:]

            # 3. 核心校验逻辑
            # A. 内容一致性（去除首尾空格比对）
            is_content_match = (extracted_middle.strip() == llm_segment)
            # B. 长度一致性
            is_length_match = (len(extracted_middle) == expected_length)

            if is_content_match and is_length_match:
                # 校验通过，存储切分后的结果，方便下一步“挖空”使用
                # data['split_data'] = {
                #     "prefix": prefix,
                #     "middle": extracted_middle,
                #     "suffix": suffix,
                #     "is_verified": True
                # }
                new_data = {
                    "url": data.get("url", ""),
                    "title": data.get("title", ""),
                    "category": data.get("category", ""),
                    "prefix": prefix,
                    "middle": extracted_middle,
                    "suffix": suffix,
                    "is_verified": True
                }
                f_out.write(json.dumps(new_data, ensure_ascii=False) + '\n')
                valid_count += 1
            else:
                # 如果不一致，可以根据需要打印出不一致的原因
                print(f"过滤: 内容/长度不匹配 -> {data.get('title')} "
                      f"(内容匹配: {is_content_match}, 长度匹配: {is_length_match})")

    print(f"\n处理完成！")
    print(f"总计输入: {total_count} 条")
    print(f"通过校验: {valid_count} 条")
    print(f"过滤比例: {((total_count - valid_count) / total_count * 100):.2f}%")

if __name__ == "__main__":
    # 使用上一步生成的中间文件
    input_path = "cloze_10.jsonl"
    output_path = "to_be_filled_10.jsonl"
    process_validation(input_path, output_path)

    