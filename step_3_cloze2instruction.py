import json
import os

def process_extracted_data(input_file: str, output_file: str):
    """
    Post-processes the extracted JSONL to filter results and split text into
    prefix, middle (selected_text), and suffix.
    """
    processed_count = 0
    discarded_full_text = 0
    discarded_verify_failed = 0
    total_valid = 0

    if not os.path.exists(input_file):
        print(f"Error: Input file {input_file} not found.")
        return

    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            processed_count += 1
            try:
                data = json.loads(line.strip())
                content = data.get('content', '')
                extraction = data.get('step_2_results', {})
                selected_text = extraction.get('selected_text', '')
                
                # 1. Filter: step_2_verbatim_verify == False
                # We also perform a manual check in case the flag was missing or wrong
                if not data.get('verbatim_verify', True) or selected_text not in content:
                    discarded_verify_failed += 1
                    continue

                # 2. Judge: len(selected_text) == len(content)
                # We discard cases where the model just copied the entire input
                if len(selected_text.strip()) >= len(content.strip()):
                    discarded_full_text += 1
                    continue

                if selected_text not in content:
                    discarded_verify_failed += 1
                    continue

                # 3. Split content into prefix, middle, suffix
                # Find the start index of the selected_text
                # start_idx = content.find(selected_text)
                start_idx = content.index(selected_text)
                
                prefix = content[:start_idx]
                middle = selected_text
                suffix = content[start_idx + len(selected_text):]

                # Update the data dictionary with new fields
                data['prefix'] = prefix
                data['middle'] = middle
                data['suffix'] = suffix
                
                # Clean up temporary extraction fields if you want a cleaner final file
                # del data['extracted_segment'] 

                # Write the validated and split data
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')
                total_valid += 1

            except Exception as e:
                print(f"Error processing line {processed_count}: {e}")

    # Print Summary Statistics
    print("-" * 30)
    print(f"Processing Complete:")
    print(f"Total lines read:         {processed_count}")
    print(f"Discarded (Full content): {discarded_full_text}")
    print(f"Discarded (Verify failed):{discarded_verify_failed}")
    print(f"Successfully processed:   {total_valid}")
    print(f"Output saved to:          {output_file}")
    print("-" * 30)

if __name__ == "__main__":
    # Update these paths to match your file names
    INPUT_JSONL = "english_dataset/cloze/step_2_cloze_primitive.jsonl"
    OUTPUT_JSONL = "english_dataset/cloze/step_3_cloze2instruction.jsonl"
    
    process_extracted_data(INPUT_JSONL, OUTPUT_JSONL)
