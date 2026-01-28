import os
import json
import base64
import io
import requests
from openai import OpenAI
from pdf2image import convert_from_path
from tqdm import tqdm
from multiprocessing.pool import ThreadPool
from functools import partial

# --- Configuration ---
client = OpenAI(
    base_url="https://api-gateway.glm.ai/v1",
    api_key="sk-UN3MFcgYI45WzE1tHNOnaYfTmqws7HEa"
)

METADATA_FILE = "/workspace/fengzhuoer/andrew/code/ICML2026-WA/english_dataset/raw/speeches/american.jsonl"
URL_PREFIX = "http://192.168.6.106:8118/WritingBench/american/" 
LOCAL_BASE_DIR = "english_dataset/raw/speeches/pdf"
THREADS = 25

os.makedirs(LOCAL_BASE_DIR, exist_ok=True)

def download_single_pdf(entry):
    """Helper for downloading a single file, used in the thread pool."""
    remote_suffix = entry['local_path']
    full_url = f"{URL_PREFIX}{remote_suffix}"
    local_file_path = os.path.join(LOCAL_BASE_DIR, os.path.basename(remote_suffix))
    
    # Check if exists to avoid redundant downloads
    if not os.path.exists(local_file_path):
        try:
            response = requests.get(full_url, timeout=30)
            response.raise_for_status()
            with open(local_file_path, 'wb') as f:
                f.write(response.content)
        except Exception as e:
            print(f"Failed to download {full_url}: {e}")
            return None
            
    return (local_file_path, entry)

def extract_text(item):
    """Phase 2: GPT-5 Vision OCR Logic."""
    # Since we use imap/map, we pass a single tuple and unpack it
    file_path, entry = item
    output_path = file_path.replace(".pdf", ".md")
    
    if os.path.exists(output_path):
        return

    try:
        images = convert_from_path(file_path, dpi=300)
        full_text = []

        for i, img in enumerate(images):
            buffered = io.BytesIO()
            img.save(buffered, format="PNG")
            img_str = base64.b64encode(buffered.getvalue()).decode('utf-8')

            response = client.chat.completions.create(
                model="gpt-5.2-2025-12-11",
                messages=[
                    {"role": "system", "content": "You are a professional OCR operator..."},
                    {"role": "user", "content": [
                        {"type": "text", "text": f"Extract text from page {i+1} of: {entry['title']}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}", "detail": "high"}}
                    ]}
                ]
            )
            full_text.append(response.choices[0].message.content)

        with open(output_path, "w", encoding="utf-8") as f:
            f.write(f"# {entry['title']}\nSpeaker: {entry['speaker']}\n\n" + "\n\n".join(full_text))
            
    except Exception as e:
        print(f"Error processing {file_path}: {e}")

def main():
    # Load Metadata
    with open(METADATA_FILE, "r") as f:
        entries = [json.loads(line) for line in f]

    # --- Phase 1: Parallel Download ---
    print(f"--- Phase 1: Downloading PDFs (Threads: {THREADS}) ---")
    with ThreadPool(THREADS) as pool:
        # We use list() to block until all downloads are finished
        files_to_process = list(tqdm(
            pool.imap_unordered(download_single_pdf, entries), 
            total=len(entries), 
            desc="Downloading"
        ))
    
    # Filter out any None values from failed downloads
    files_to_process = [f for f in files_to_process if f is not None]

    # --- Phase 2: Parallel OCR ---
    print(f"\n--- Phase 2: Extracting Text (Threads: {THREADS}) ---")
    with ThreadPool(THREADS) as pool:
        # imap_unordered is slightly more efficient for mixed task lengths
        list(tqdm(
            pool.imap_unordered(extract_text, files_to_process), 
            total=len(files_to_process), 
            desc="OCR Processing"
        ))

if __name__ == "__main__":
    main()