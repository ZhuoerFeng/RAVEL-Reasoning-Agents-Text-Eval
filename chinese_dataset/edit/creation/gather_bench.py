import json


INSTRUCTION = """你的任务是根据“reference”（原文背景材料）和“content”（初稿文本），结合“专业点评与修改建议”，对初稿进行改写。改写需满足：
1. 提升文本的表达质量。
2. 优化逻辑结构。
3. 引入更有力量的意象与细节，减少套路化表达。
4. 适度增强情感张力。
5. 保留原文主旨，但允许在表达方式上进行创造性调整。

你的输出应是改写后的文本。
"""


fin = open('step_3_final_benchmark_data.jsonl', 'r', encoding='utf-8')
data = [json.loads(x) for x in fin.readlines()]

new_data = []
idx = 0
for line in data:
    new_data.append({
        "id": "edit_" + str(idx),
        "instruction": INSTRUCTION,
        "input": {
            "content": line['step2_cloze']['llm_generated_content'],
            "critique": line['step3_critique']['critique_content'],
        },
        "reference": line['middle']
    })
    idx += 1

fout = open('step_4_dataset_raw.jsonl', 'w', encoding='utf-8')
for item in new_data:
    fout.write(json.dumps(item, ensure_ascii=False) + '\n')
fout.close()

