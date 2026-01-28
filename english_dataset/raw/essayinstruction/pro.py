import pandas as pd 

df = pd.read_parquet('essay_instructions_test.parquet')
data = df.to_dict(orient='records')

new_data = []

start_count = 0
end_count = 0

for line in data:
    prompt = line['prompt']
    if prompt.startswith("Human: "):
        prompt = prompt[len("Human: "):]
    else:
        start_count -= 1
    start_count += 1

    if prompt.endswith("Assistant: "):
        prompt = prompt[:-len("Assistant: ")]
    else:
        end_count -= 1
    end_count += 1

    new_data.append({
        "prompt": prompt.strip(),
        "content": line['chosen'].strip()
    })

print(start_count, end_count)

df = pd.DataFrame(new_data)

df.to_json('essay_instructions_test.jsonl', orient='records', lines=True, force_ascii=False)