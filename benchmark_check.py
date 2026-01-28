import json
import re
import threading
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from glm_api_request.model import GateWays
from tqdm import tqdm

#         user_message = f"""请审计以下 Benchmark 数据项的质量：

# 【数据内容】
# - Instruction: {instruction}
# - Content (初稿): {content}
# - Critique (点评): {critique}
# - Reference (参考答案): {reference}

# 【检查重点】
# 1. 关联度检查：Critique 是否精准指出了 Content 中存在的不足？Reference 是否真正解决了 Critique 中提到的问题？三者必须逻辑闭环。
# 2. 质量检查：Content 是否具有明显的“AI味”或提升空间？Reference 是否确实表现出较高的人类写作水平（文学性、专业性、深度）？
# 3. 冗余检查：Critique 中是否包含了诸如“好的”、“根据对比”、“发现如下问题”等无意义的开头、结语或解释性废话？

# 【返回约定】
# 请仅返回 JSON 格式结果，包含以下字段：
# - problem_1: [true/false] (若 Instruction, Content, Critique, Reference 逻辑关联紧密且闭环，记为 true；否则记为 false)
# - problem_2: [true/false] (若 Content 有改写价值且 Reference 确实属于高质量人类写作，记为 true；否则记为 false)
# - problem_3: [true/false] (若 Critique 只有干货、无任何多余废话，记为 true；否则记为 false)
# - reason: [string] (简要说明判定为 false 的具体原因，若全为 true 则填 "Pass")
# """


# --- 基础配置与模型初始化 ---
model = GateWays(model_name="gpt-5.1") # 建议使用最强模型进行审计

CHECK_SYSTEM_PROMPT = "你是一位极度苛刻的数据质量审计专家，专门负责评估 NLP 指令微调数据集的质量。"

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(system_prompt: str, user_message: str) -> str:
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(messages=messages, temperature=0.0) # 审计任务设为0，保证稳定性
    return response.choices[0].message.content

def extract_json(text):
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        return json.loads(match.group()) if match else None
    except:
        return None


def process_audit_item(line, fout_name):
    """
    质量检查处理逻辑
    """
    try:
        data = json.loads(line.strip())
        
        # 构造审计用的 Input
        instruction = data.get('instruction', '')
        content = data.get('input', {}).get('content', '')
        critique = data.get('input', {}).get('critique', '')
        reference = data.get('reference', '')

        user_message = f"""【Data Content】

**Instruction:** {instruction}
**Content (Draft):** {content}
**Critique:** {critique}
**Reference (Model Answer):** {reference}

【Key Checkpoints】

1. **Relevance Check:** Does the Critique accurately identify the deficiencies in the Content? Does the Reference effectively resolve the issues mentioned in the Critique? These three elements must form a logical closed loop.
2. **Quality Check:** Does the Content exhibit a noticeable "AI flavor" or significant room for improvement? Does the Reference truly demonstrate a high level of human writing (literary quality, professionalism, depth)?
3. **Redundancy Check:** Does the Critique contain meaningless filler, such as "Okay," "Based on the comparison," "The following problems were found," or other unnecessary introductory or concluding remarks?

【Response Convention】
Please return the results **only in JSON format**, including the following fields:

**problem_1:** [true/false] (Mark as **true** if the Instruction, Content, Critique, and Reference are logically tight and form a closed loop; otherwise, **false**).
**problem_2:** [true/false] (Mark as **true** if the Content is worth rewriting and the Reference truly represents high-quality human writing; otherwise, **false**).
**problem_3:** [true/false] (Mark as **true** if the Critique contains only substance with no redundant fluff; otherwise, **false**).
**reason:** [string] (Briefly explain the specific reason for any "false" determination; if all are true, enter "Pass").
"""

        # 调用 LLM 进行审计
        raw_res = get_llm_response(CHECK_SYSTEM_PROMPT, user_message)
        audit_res = extract_json(raw_res)
        
        if audit_res:
            # 将审计结果存入原数据
            data['quality_audit'] = audit_res
            
            # 只有当三个检查点全部为 True 时，才认为这条数据是完美的
            data['is_golden'] = all([audit_res.get('problem_1'), audit_res.get('problem_2'), audit_res.get('problem_3')])
            
            with open(fout_name, 'a', encoding='utf-8') as f_out:
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
        return data

    except Exception as e:
        print(f"审计行异常: {e}")
        return None


def main(input_file: str, output_file: str):
    worker_func = partial(process_audit_item, fout_name=output_file)
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        lines = f_in.readlines()
    
    print(f"开始审计 {len(lines)} 条数据...")
    with ThreadPoolExecutor(max_workers=10) as executor: # 审计建议并发稍微调低，确保API稳定性
        for _ in tqdm(executor.map(worker_func, lines), total=len(lines), desc="Quality Auditing"):
            pass


if __name__ == "__main__":
    input_jsonl = "english_dataset/edit/step_4_edit_benchmark.jsonl"
    output_jsonl = "english_dataset/edit/step_5_dataset_audited.jsonl"
    main(input_jsonl, output_jsonl)

