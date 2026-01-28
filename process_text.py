# import json
# import re
# import threading
# from functools import partial
# from concurrent.futures import ThreadPoolExecutor
# from tenacity import retry, wait_fixed, stop_after_attempt
# from glm_api_request.model import GateWays

# from tqdm import tqdm

# # --- 基础配置与模型初始化 ---
# model = GateWays(model_name="gpt-5.1")

# # 步骤一的系统提示词
# STEP1_SYSTEM_PROMPT = """你是一位资深文学编辑。你的任务是从给定的文章中挑选出一组【连续】的、最能代表整篇文章水准的核心段落。

# 要求：
# 1. 挑选的段落必须是文章中【连续】出现的内容。
# 2. 挑选的内容总长度建议在 1000 字左右。
# 3. 必须以 JSON 格式返回，包含以下字段：
#    - "start_sentence": 选中片段的第一句话（需与原文完全一致）。
#    - "end_sentence": 选中片段的最后一句话（需与原文完全一致）。
#    - "selected_text": 选中的完整连续文本。

# 不要输出任何额外的解释，只输出 JSON。"""

# @retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
# def get_llm_response(system_prompt: str, user_message: str) -> str:
#     """调用 LLM 获取响应，带重试机制"""
#     messages = [
#         {"role": "system", "content": system_prompt},
#         {"role": "user", "content": user_message}
#     ]
#     response = model.get_api_result(
#         messages=messages,
#         temperature=0.2,
#     )
#     return response.choices[0].message.content

# def extract_json_from_response(response_text: str) -> dict:
#     """利用正则从 LLM 返回的文本中提取并解析 JSON"""
#     try:
#         # 匹配最外层的 {} 及其内容
#         match = re.search(r'\{.*\}', response_text, re.DOTALL)
#         if match:
#             return json.loads(match.group())
#     except Exception as e:
#         print(f"JSON 解析失败: {e}")
#     return None


# def process_item(line, system_prompt, fout_name):
#     """单条数据处理逻辑"""
#     try:
#         data = json.loads(line.strip())
#         content = data.get('content', '')
        
#         # 调用 LLM 进行段落选取
#         llm_raw = get_llm_response(system_prompt, f"请处理以下文章：\n\n{content}")
#         parsed_result = extract_json_from_response(llm_raw)
        
#         if parsed_result and "selected_text" in parsed_result:
#             # 在新字段中存储选取结果及相关元数据
#             data['step1_selection'] = {
#                 "selected_segment": parsed_result["selected_text"],
#                 "start_sentence": parsed_result.get("start_sentence", ""),
#                 "end_sentence": parsed_result.get("end_sentence", ""),
#                 "segment_length": len(parsed_result["selected_text"])
#             }
    
#             with open(fout_name, 'a', encoding='utf-8') as f_out:
#                 if data:
#                     f_out.write(json.dumps(data, ensure_ascii=False) + '\n')   
#             return data
#         else:
#             print(f"提取失败: {data.get('title', 'Unknown')}")
#             return None
#     except Exception as e:
#         print(f"处理行异常: {e}")
#         return None
     

# def main(input_file: str, output_file: str):
#     # 使用线程锁保证多并发写入文件时的安全性
#     write_lock = threading.Lock()
    
#     # 使用 partial 封装工作流，固定系统提示词参数
#     worker_func = partial(process_item, system_prompt=STEP1_SYSTEM_PROMPT, fout_name=output_file)
    
#     f_in = open(input_file, 'r', encoding='utf-8')

#     lines = f_in.readlines()
#     # data = [json.loads(x) for x in lines]
    
#     # 开启 20 个并发
#     with ThreadPoolExecutor(max_workers=20) as executor:
#         # 提交任务
#         for _ in  tqdm(executor.map(worker_func, lines), total=len(lines)):
#             pass


# if __name__ == "__main__":
#     input_jsonl = "dataset/edit/data_10.jsonl"   # 你的原始数据
#     output_jsonl = "dataset/edit/cloze_10.jsonl" # 处理后的结果
#     main(input_jsonl, output_jsonl)




import os
import json
import threading
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from tqdm import tqdm

# Assuming your local gateway module is available
# from glm_api_request.model import GateWays 

# --- Basic Configuration & Model Initialization ---
# model = GateWays(model_name="gpt-5.1")

# System Prompt for the Cleaning Task
CLEANING_SYSTEM_PROMPT = (
    "You are a professional document archivist. Your task is to clean OCR transcripts, "
    "remove non-speech artifacts (page numbers, watermarks, intro noise), and extract metadata. "
    "You must return ONLY a JSON object."
)

@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(system_prompt: str, user_message: str) -> str:
    """Invokes LLM to get response with retry logic"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message}
    ]
    # Mimicking your GateWays call structure
    response = model.get_api_result(
        messages=messages,
        temperature=0.2, # Lower temperature for extraction tasks
        response_format={"type": "json_object"}
    )
    return response.choices[0].message.content

def process_md_file(file_path, system_prompt, output_file):
    """
    Worker logic: Reads an MD file, cleans it via LLM, and writes to JSONL
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            raw_text = f.read()

        filename = os.path.basename(file_path)

        # Construct the User Prompt
        user_message = f"""Clean the following OCR speech transcript.

Requirements:
1. Extract 'speaker', 'topic', and 'date'. Use "" for missing values.
2. Remove all structural noise: page numbers, "Property of AmericanRhetoric.com", "Updated...", and transcription notes.
3. Clean the 'content' to only include the spoken words. Join paragraphs split by artifacts.
4. Output Format: JSON with keys: "content", "speaker", "topic", "date".

Transcript:
---
{raw_text}
---"""

        # Call LLM
        llm_response_raw = get_llm_response(system_prompt, user_message)
        
        # Parse to ensure it's valid JSON
        data = json.loads(llm_response_raw)
        data['original_filename'] = filename # For tracking

        # Thread-safe append to JSONL
        with open(output_file, 'a', encoding='utf-8') as f_out:
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data

    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return None

def main(input_dir: str, output_file: str):
    # Prepare file list
    if not os.path.exists(input_dir):
        print(f"Directory {input_dir} not found.")
        return

    md_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.endswith('.md')]
    
    # Use partial to bind the system prompt and output destination
    worker_func = partial(process_md_file, system_prompt=CLEANING_SYSTEM_PROMPT, output_file=output_file)
    
    # Initialize output file (clear it if it exists)
    with open(output_file, 'w', encoding='utf-8') as f:
        pass

    # Use 20 concurrent workers as per your workflow
    with ThreadPoolExecutor(max_workers=20) as executor:
        for _ in tqdm(executor.map(worker_func, md_files), total=len(md_files), desc="Cleaning Transcripts"):
            pass

if __name__ == "__main__":
    # Configure paths here
    INPUT_DIRECTORY = "mds/"
    OUTPUT_JSONL = "cleaned_speeches.jsonl"
    
    # Note: Ensure 'model' is initialized before calling main
    # main(INPUT_DIRECTORY, OUTPUT_JSONL)