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
        # {"role": "system", "content": system_prompt},
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
        
        if not content:
            return None

        # Construct the extraction-specific User Prompt
        user_message = """**Role:** You are an expert Prompt Engineer and Creative Writing Specialist. Your task is to perform "Reverse Instruction Engineering" on a piece of high-quality human text.

**Input:** A text snippet from a JSONL file (field: `content`).
**Genres:** The text will belong to one of these categories: Essay (academic/analytical), Story (short story), Fiction (novel chapter), or Speech (political/historical).

**Task:** Analyze the provided `content` and design a writing instruction (the "query") that would guide an LLM to reproduce the original text as closely as possible in terms of theme, tone, and organization.

**Output Requirements:**
You must return a JSON object with the following five fields:

1. `"genre"`: Identify the specific writing genre.
2. `"brief"`: A concise summary of the central theme or main idea.
3. `"audience"`: Define the target audience and the required tone/register.
4. `"word"`: An approximate word count requirement based on the original text.
5. `"query"`: The final, comprehensive writing instruction. **This field must not exceed 100 words.** It should integrate the genre, brief, structure, and audience into a prompt that feels like a natural writing assignment.

**JSON Schema:**

```json
{
  "genre": "...",
  "brief": "...",
  "audience": "...",
  "word": "...",
  "query": "..."
}

```

**Constraint:** Do not include any introductory or concluding remarks. Return ONLY the raw JSON object.

**Input Content to Analyze:**
[TEXT_CONTENT]
"""

        # Call LLM
        raw_response = get_llm_response(system_prompt, user_message.replace("[TEXT_CONTENT]", content))
        
        # Parse JSON results
        extracted_data = extract_json_from_string(raw_response)
        
        if extracted_data:
            # Merge the extracted fields into the original data
            data['step_2_results'] = extracted_data
            
            # # Optional: Add a verification flag to check if verbatim match succeeded
            # data['step_2_verbatim_verify'] = extracted_data['selected_text'] in content

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
    input_jsonl = "english_dataset/raw/all_raw/step_1_condition.jsonl"
    output_jsonl = "english_dataset/end2end/step_2_end2end_primitive.jsonl"
    main(input_jsonl, output_jsonl)