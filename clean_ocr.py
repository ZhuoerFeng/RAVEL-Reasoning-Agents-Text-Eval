import pandas as pd
import os
import json

def process_speeches_to_jsonl(csv_path, base_path, output_path):
    # 1. Load the CSV
    # We use usecols to only grab the first 5 relevant columns, 
    # effectively ignoring the trailing empty commas.
    cols_to_use = ['Filename', 'Title', 'Speaker', 'Date', 'Field']
    df = pd.read_csv(csv_path, usecols=cols_to_use)

    def get_content(filename):
        # Construct the full local file path
        file_path = os.path.join(base_path, str(filename) + '.md')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        except FileNotFoundError:
            print(f"Warning: File {filename} not found in {base_path}")
            return None
        except Exception as e:
            print(f"Error reading {filename}: {e}")
            return None

    # 2. Extract contents and add the 'content' column
    print("Reading text files...")
    df['content'] = df['Filename'].apply(get_content)

    # 3. Save to JSONL format
    # orient='records' creates a list of dicts
    # lines=True ensures each dict is on a new line
    df.to_json(output_path, orient='records', lines=True, force_ascii=False)
    
    print(f"Process complete. File saved to: {output_path}")

# --- Configuration ---
csv_file = "english_dataset/raw/speeches/jsons/metainfo.csv"
md_directory = "english_dataset/raw/speeches/mds/"
save_path = "english_dataset/raw/speeches/jsons/dataset.jsonl"

# Run the process
if __name__ == "__main__":
    process_speeches_to_jsonl(csv_file, md_directory, save_path)