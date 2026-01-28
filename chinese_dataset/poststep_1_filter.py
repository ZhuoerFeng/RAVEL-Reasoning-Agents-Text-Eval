import pandas as pd
import json

df = pd.read_json('chinese_dataset_v1.jsonl', lines=True)
# filter out all references that exceeds 4000 length
filtered_df = df[df['reference'].apply(lambda x: len(x) <= 4000)]
# filter out all samples that instruction + all input attributes exceeds 6000 length
def total_input_length(row):
    instruction_len = len(row['instruction'])
    input_obj = row['input']
    input_len = sum(len(str(v)) for v in input_obj.values())
    return instruction_len + input_len
filtered_df = filtered_df[filtered_df.apply(total_input_length, axis=1) <= 5000]
# downsample each task_type to at most 200 examples
filtered_df = filtered_df.groupby('task_type').apply(lambda x: x.sample(n=min(len(x), 200), random_state=42)).reset_index(drop=True)

filtered_df.to_json('chinese_dataset_v2.jsonl', lines=True, orient='records', force_ascii=False)
