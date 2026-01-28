import json
import re
from functools import partial
from concurrent.futures import ThreadPoolExecutor
from tenacity import retry, wait_fixed, stop_after_attempt
from glm_api_request.model import GateWays
from tqdm import tqdm

# --- Configuration & Model Initialization ---
model = GateWays(model_name="gpt-5.1")


@retry(wait=wait_fixed(2), stop=stop_after_attempt(3))
def get_llm_response(system_prompt: str, user_message: str) -> str:
    """Calls the LLM to get the extraction result."""
    messages = [
        {"role": "user", "content": user_message}
    ]
    response = model.get_api_result(
        messages=messages,
        temperature=0.0,  # Set to 0 for maximum precision in verbatim extraction
    )
    return response.choices[0].message.content

def extract_json_from_string(text: str) -> dict:
    """
    Helper to extract JSON content even if the LLM wraps it in markdown code blocks.
    """
    try:
        # Look for content between ```json and ``` or just ```
        match = re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)
        if not match:
            match = re.search(r"```\s*(.*?)\s*```", text, re.DOTALL)
        
        json_str = match.group(1).strip() if match else text.strip()
        return json.loads(json_str)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return None

def process_extraction_item(line, system_prompt, fout_name):
    """
    Task: Identify and extract the 'Golden Segment' (20%-50% of the text).
    """
    try:
        data = json.loads(line)
        content = data.get('content', '')

        instruction = data.get('instruction', '')
        prefix = data.get('input', {}).get('prefix', '')
        suffix = data.get('input', {}).get('suffix', '')
        
        # Construct the extraction-specific User Prompt
        user_message = f"""{instruction}\n\n[article]\n{prefix}[fill in the blank]{suffix}\n[/article]\n\nDirectly output your response without any additional explanation or commentary.
"""

        # Call LLM
        raw_response = get_llm_response(system_prompt, user_message)

        # Merge the extracted fields into the original data
        data['cloze_results'] = raw_response

        # Write to file
        with open(fout_name, 'a', encoding='utf-8') as f_out:
            f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
            
        return data

    except Exception as e:
        print(f"Row processing error: {e}")
        return None


def main(input_file: str, output_file: str):
    worker_func = partial(process_extraction_item, system_prompt="", fout_name=output_file)
    
    with open(input_file, 'r', encoding='utf-8') as f_in:
        lines = f_in.readlines()
    
    # 20 concurrent threads for high-speed processing
    with ThreadPoolExecutor(max_workers=20) as executor:
        for _ in tqdm(executor.map(worker_func, lines), total=len(lines), desc="Step: Extracting Golden Segments"):
            pass
        

if __name__ == "__main__":
    input_jsonl = "english_dataset/edit/step_1_edit_raw.jsonl"
    output_jsonl = "english_dataset/edit/step_2_cloze_result.jsonl"
    main(input_jsonl, output_jsonl)
