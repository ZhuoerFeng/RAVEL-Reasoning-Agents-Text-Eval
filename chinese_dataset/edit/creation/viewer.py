import json


PROCESS_PROMPT = """Role: 你是一位资深的编辑，擅长识别文章的核心论点和精彩片段。
Task: 请从提供的文章中，挑选出一组【连续】的、具有代表性的重要段落。

Requirements:
1. 挑选的段落总字数需在 800 - 1200 字之间（包含标点）。
2. 这些段落必须是连续的，能够体现作者的写作风格、逻辑深度或情感力度。
3. 返回格式必须严格遵守下方的 JSON 约定，不要输出任何解释说明。

JSON Return Format:
{
  "start_sentence": "选中部分的开头第一句话，需与原文完全一致",
  "end_sentence": "选中部分的结尾最后一句话，需与原文完全一致",
  "selected_text": "选中的完整文本内容"
}

Article Content:
"""



fin = open('data_10.jsonl').readlines()
data = [json.loads(x) for x in fin]


print(len(data))
print(data[0].keys())

# 1000


import re
import json

def step1_select_segment(content, llm_response):
    """
    通过LLM返回的JSON提取原文中的连续段落，并验证长度。
    """
    try:
        # 解析LLM返回的JSON
        data = json.loads(re.search(r'\{.*\}', llm_response, re.DOTALL).group())
        selected_text = data['selected_text']
        
        # 计算长度 (包含标点)
        length = len(selected_text)
        
        # 构造“挖空”后的内容（用 [MISSING_CONTENT] 占位）
        # 建议使用 exact match 替换，防止 LLM 微调了标点
        placeholder = "\n\n[REWRITING_TARGET_PLACEHOLDER]\n\n"
        content_with_hole = content.replace(selected_text, placeholder)
        
        return {
            "original_writing": content,
            "target_segment": selected_text,
            "content_with_hole": content_with_hole,
            "length": length
        }
    except Exception as e:
        print(f"解析错误: {e}")
        return None

