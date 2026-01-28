import os
import json

def collect_files_to_jsonl(root_dir, output_filename):
    """
    Walks through subfolders, collects file metadata and content,
    and saves them into a single .jsonl file.
    """
    with open(output_filename, 'w', encoding='utf-8') as jsonl_file:
        # os.walk yields (root, dirs, files)
        for current_path, _, files in os.walk(root_dir):
            for file in files:
                file_full_path = os.path.join(current_path, file)
                
                # Calculate the relative path from the root directory
                relative_path = os.path.relpath(file_full_path, root_dir)
                
                try:
                    # Reading the content (assuming text files)
                    with open(file_full_path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # Create the dictionary for this entry
                    entry = {
                        "filename": file,
                        "path": relative_path,
                        "content": content
                    }
                    
                    # Write as a single JSON line
                    jsonl_file.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    
                except Exception as e:
                    print(f"Skipping {file_full_path} due to error: {e}")

# Usage
root_folder = './obooks'  # Change this to your target directory
output_file = 'obooks/collected_data.jsonl'
collect_files_to_jsonl(root_folder, output_file)
print(f"Extraction complete! Saved to {output_file}")
