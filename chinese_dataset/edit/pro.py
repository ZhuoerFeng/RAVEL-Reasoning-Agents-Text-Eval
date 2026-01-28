import pandas as pd

df = pd.read_json('prompts_edit.jsonl', lines=True)
# add one column 'task_type' and set all items as 'edit'
# df['task_type'] = 'edit'
df['infer_id'] = df['id']
df.to_json('prompts_edit.jsonl', lines=True, orient='records', force_ascii=False)
