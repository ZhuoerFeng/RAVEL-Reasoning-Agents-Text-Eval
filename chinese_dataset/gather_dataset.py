import json

fin = open('cloze/prompts_cloze.jsonl', 'r', encoding='utf-8').readlines()
data = [json.loads(line) for line in fin]

new_data = []
idx = 0
for line in data:
    line['meta'] = {'old_id': line['infer_id']}
    line['infer_id'] = 'cloze_cn_' + str(idx)
    idx += 1
    new_data.append(line)



fin = open('condition/prompts_condition.jsonl', 'r', encoding='utf-8').readlines()
data = [json.loads(line) for line in fin]

for line in data:
    line['meta'] = {'old_id': line['infer_id']}
    line['infer_id'] = 'condition_cn_' + str(idx)
    idx += 1
    new_data.append(line)


fin = open('edit/prompts_edit_subtask.jsonl', 'r', encoding='utf-8').readlines()
data = [json.loads(line) for line in fin]

for line in data:
    line['meta'] = {'old_id': line['id']}
    line['infer_id'] = 'edit_cn_' + str(idx)
    idx += 1
    new_data.append(line)


fout = open('end2end/prompts_end2end.jsonl', 'r', encoding='utf-8').readlines()
data = [json.loads(line) for line in fout]

for line in data:
    line['meta'] = {'old_id': line['infer_id']}
    line['infer_id'] = 'end2end_cn_' + str(idx)
    idx += 1
    new_data.append(line)


fout = open('chinese_full_dataset.jsonl', 'w', encoding='utf-8')
for item in new_data:
    fout.write(json.dumps(item, ensure_ascii=False) + '\n')
fout.close()

