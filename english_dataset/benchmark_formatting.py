import json

def sub_task_converter(metainfo, source):
    if source == 'obooks':
        path = metainfo.get('path', '')
        if 'fiction' in path.lower():
            return 'fiction'
        elif 'poem' in path.lower():
            return 'poetry'
        elif 'story' in path.lower():
            return 'story'
        else:
            raise ValueError(f"Unknown obooks sub_task for path: {path}")
    elif source == 'ivypanda':
        return 'academic_writing'
    elif source == 'american_rhetoric':
        return 'speech'
    elif source == 'essay_instruction':
        return 'essay'
    else:
        raise ValueError(f"Unknown source: {source}")
    

fin = open('cloze/step_3_cloze2instruction.jsonl').readlines()

data = [json.loads(x) for x in fin]

new_data = []

idx = 0

for line in data:
    new_data.append({
        "infer_id": "cloze_en_" + str(idx),
        "task_type": "cloze",
        "sub_task": sub_task_converter(line["meta"], line["source"]),
        "instruction": "Please fill in the blanks marked with [fill in the blank] in the following article based on the context.",
        "input": {
            "prefix": line["prefix"],
            "suffix": line["suffix"],
        },
        "reference": line["middle"],
    })
    idx += 1


fout = open('cloze/step_4_cloze_benchmark.jsonl', 'w')
for line in new_data[:150]:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()

fout = open('cloze/step_1_edit_raw.jsonl', 'w')
for line in new_data[150:]:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()



#######

fin = open('end2end/step_2_end2end_primitive.jsonl').readlines()
data = [json.loads(x) for x in fin]
new_data = []
idx = 0
for line in data:
    new_data.append({
        "infer_id": "end2end_en_" + str(idx),
        "task_type": "end2end",
        "sub_task": sub_task_converter(line["meta"], line["source"]),
        "instruction": line['step_2_results']["query"],
        "input": {
            'genre': line['step_2_results']['genre'],
            'brief': line['step_2_results']['brief'],
            'audience': line['step_2_results']['audience'],
            'word': line['step_2_results']['word'],
        },
        "reference": line["content"],
    })
    idx += 1

fout = open('end2end/step_4_end2end_benchmark.jsonl', 'w')
for line in new_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')

fout.close()


#######



fin = open('condition/step_2_condition_primitive.jsonl').readlines()
data = [json.loads(x) for x in fin]
new_data = []
idx = 0
for line in data:
    new_data.append({
        "infer_id": "condition_en_" + str(idx),
        "task_type": "condition",
        "sub_task": sub_task_converter(line["meta"], line["source"]),
        "instruction": line['step_2_results']["query"],
        "input": {
            'genre': line['step_2_results']['genre'],
            'brief': line['step_2_results']['brief'],
            'condition': line['step_2_results']['structure'],
            'audience': line['step_2_results']['audience'],
            'word': line['step_2_results']['word'],
        },
        "reference": line["content"],
    })
    idx += 1

fout = open('condition/step_4_condition_benchmark.jsonl', 'w')
for line in new_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()

