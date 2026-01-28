import json
import re
import threading
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from glm_api_request.model import GateWays
from tqdm import tqdm


#         user_message = f"""Task: 我这里有一份初稿片段（AI生成），请你对其进行深度评审。为了让你提供更精准的改进建议，我会为你提供一份该片段的修改目标“理想水平参考”（人类原著），请你对比两者，指出初稿的问题并给出修改指令。

# 注意：你的最终输出（指令）必须是给作者的修改建议，【严禁】在输出内容中提及“人类原著”、“参考范文”、“对比”或“原作者”等词汇。你要表现得就像是直接阅读了初稿并通过指出其中的问题，来指导修改至期望的文本。

# Input Data:
# - 初稿内容（待评审）：{ai_content}
# - 理想水平参考（仅供你内部对比）：{human_middle}

# 撰写要求：
# 1. 问题诊断：指出初稿在词汇表现力、逻辑张力、情感洞察等方面的具体问题。
# 2. 修改意见：提供具体的改写方向，目标是将初稿内容（待评审）如何修改至理想水平参考。你可以参考理想水平参考中的内容，指示要怎么从初稿内容修改到理想水平。
# 3. 语气：专业、犀利、富有启发性。
# 4. 长度：问题诊断修改意见加起来不要超过300字。

# 输出格式：
# 请直接输出：【问题诊断与修改建议】"""


# --- 基础配置与模型初始化 ---
model = GateWays(model_name="gpt-5.1")

# 步骤三：点评任务的系统提示词
# STEP3_SYSTEM_PROMPT = "你是一位目光犀利的资深文学主编，擅长从平庸的稿件中洞察逻辑漏洞、词藻贫乏及思想浅薄之处。"

STEP3_SYSTEM_PROMPT = "Would you like me to refine this translation further to match a specific tone, or perhaps use it as a prompt for a critique?"


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(system_prompt: str, user_message: str) -> str:
    """调用 LLM 获取响应，带重试机制"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(
        messages=messages,
        temperature=0.3, # 点评建议低随机性，确保逻辑严密
    )
    return response.choices[0].message.content

def process_critique_item(line, system_prompt, fout_name):
    """
    步骤三：点评与指令撰写处理逻辑
    """
    try:
        data = json.loads(line.strip())
        
        # 提取关键对比数据
        human_middle = data.get('reference', '')
        ai_content = data.get('cloze_results', '')
        
        if not human_middle or not ai_content:
            return None

        # 构造用户 Prompt
        
        user_message = f"""Task: I have a draft snippet (AI-generated) here, and I would like you to perform an in-depth review. To help you provide more precise improvement suggestions, I will provide an "Ideal Reference" (original human writing) as the goal. Please compare the two, identify the issues in the draft, and provide revision instructions.\n\n**Note:** Your final output must be revision suggestions addressed to the author. You are **strictly prohibited** from mentioning terms like "human original," "reference sample," "comparison," or "original author" in your output. You must act as if you are reviewing the draft directly and guiding the revisions toward the desired outcome by identifying its flaws.\n\n**Input Data:**\n\n* Draft Content (to be reviewed): {ai_content}\n\n* Ideal Reference (for internal comparison only): {human_middle}\n\n**Writing Requirements:**\n1. **Problem Diagnosis:** Identify specific issues in the draft regarding lexical expressiveness, logical tension, emotional insight, etc.\n2. **Revision Advice:** Provide specific directions for rewriting. The goal is to instruct how to modify the draft to reach the target quality. You may draw upon the elements of the "Ideal Reference" to guide the transformation of the draft.\n3. **Tone:** Professional, sharp, and inspiring.\n4. **Length:** The combined length of the Problem Diagnosis and Revision Advice should not exceed 300 words.\n\n**Output Format:**\nPlease begin your response directly starting with: **Problem Diagnosis & Revision Suggestions**"""
    
        # 调用 LLM 进行深度点评
        critique_instruction = get_llm_response(system_prompt, user_message)
        
        # 存储点评结果
        data['step3_critique'] = {
            "critique_content": critique_instruction
        }

        # 写入文件
        with open(fout_name, 'a', encoding='utf-8') as f_out:
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data

    except Exception as e:
        print(f"处理行异常: {e}")
        return None

def main(input_file: str, output_file: str):
    # 使用 partial 封装工作流
    worker_func = partial(process_critique_item, system_prompt=STEP3_SYSTEM_PROMPT, fout_name=output_file)
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        lines = f_in.readlines()
    
    # 开启 20 个并发进行点评生成
    with ThreadPoolExecutor(max_workers=20) as executor:
        for _ in tqdm(executor.map(worker_func, lines), total=len(lines), desc="Step 3: Generating Critique"):
            pass


if __name__ == "__main__":
    # 使用步骤 2 生成的 cloze 结果作为输入
    # input_jsonl = "english_dataset/edit/step_2_filled_10.jsonl"
    # output_jsonl = "english_dataset/edit/step_3_final_benchmark_data.jsonl"
    input_jsonl = "english_dataset/edit/step_2_cloze_result.jsonl"
    output_jsonl = "english_dataset/edit/step_3_revision_critiques.jsonl"
    main(input_jsonl, output_jsonl)

