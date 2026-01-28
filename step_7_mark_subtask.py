import json
import re
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from glm_api_request.model import GateWays
from tqdm import tqdm

# --- Configuration & Model Initialization ---
model = GateWays(model_name="gpt-5.1")

# System Prompt for Extraction Task
EXTRACTION_SYSTEM_PROMPT = (
    "You are an expert Literary Editor. Your task is to identify and extract the most "
    "stylistically brilliant and contextually significant continuous segment from a given text."
)

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(system_prompt: str, user_message: str) -> str:
    """Calls the LLM to get the extraction result."""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(
        messages=messages,
        temperature=0.0,  # Set to 0 for maximum precision in verbatim extraction
    )
    return response.choices[0].message.content


def process_extraction_item(line, system_prompt, fout_name):
    try:
        data = json.loads(line)
        content = data.get('input', {}).get('content', '')
        
        if not content:
            return None

        # Construct the extraction-specific User Prompt
        user_message = """请作为一名专业的文学审稿员，将以下文本片段归类为：小说、散文、纪实、诗歌。

要求：

只需输出类别名称。

如果文本具有多重属性，请选择最显著的一个。请直接输出分类结果，不要带有任何解释或评论。

待分类文本：
[TEXT_CONTENT]"""

        # Call LLM
        raw_response = get_llm_response(system_prompt, user_message.replace("[TEXT_CONTENT]", content))
        
        if raw_response:
            # Merge the extracted fields into the original data
            data['sub_task'] = raw_response
            
            # Write to file
            with open(fout_name, 'a', encoding='utf-8') as f_out:
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data

    except Exception as e:
        print(f"Row processing error: {e}")
        return None


def main(input_file: str, output_file: str):
    worker_func = partial(process_extraction_item, system_prompt=EXTRACTION_SYSTEM_PROMPT, fout_name=output_file)
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        lines = f_in.readlines()
    
    # 20 concurrent threads for high-speed processing
    with ThreadPoolExecutor(max_workers=20) as executor:
        for _ in tqdm(executor.map(worker_func, lines), total=len(lines), desc="Step: Extracting Golden Segments"):
            pass

if __name__ == "__main__":
    input_jsonl = "chinese_dataset/edit/prompts_edit.jsonl"
    output_jsonl = "chinese_dataset/edit/prompts_edit_subtask.jsonl"
    main(input_jsonl, output_jsonl)
