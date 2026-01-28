import json

fin = open('/workspace/fengzhuoer/andrew/data/AgWritingBench/all_completion.jsonl').readlines()

data = [json.loads(x) for x in fin]

new_data = []

for line in data:
    new_data.append({
        "infer_id": line['infer_id'],
        "task_type": "cloze",
        "sub_task": line["sub_task"],
        "instruction": line["basic_instruction"],
        "input": {
            "content": line["information"],
        },
        "reference": line["reference"],
    })

fout = open('cloze/prompts_cloze.jsonl', 'w')
for line in new_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()




# fin = open('/workspace/fengzhuoer/andrew/data/AgWritingBench/all_open.jsonl').readlines()

# data = [json.loads(x) for x in fin]

# new_data = []

# for line in data:
#     new_data.append({
#         "infer_id": line['infer_id'],
#         "task_type": "end2end",
#         "sub_task": line["sub_task"],
#         "instruction": line["basic_instruction"],
#         "input": {
#             "content": ""
#         },
#         "reference": line["reference"],
#     })

# fout = open('end2end/prompts_end2end.jsonl', 'w')
# for line in new_data:
#     fout.write(json.dumps(line, ensure_ascii=False) + '\n')
# fout.close()




# fin = open('/workspace/fengzhuoer/andrew/data/AgWritingBench/all_guide.jsonl').readlines()

# data = [json.loads(x) for x in fin]

# new_data = []

# for line in data:
#     new_data.append({
#         "infer_id": line['infer_id'],
#         "task_type": "condition",
#         "sub_task": line["sub_task"],
#         "instruction": line["basic_instruction"] + '\n\n下面是已经规划好的大纲，请根据大纲内容进行写作。',
#         "input": {
#             "outline": '【大纲】\n\n' +  line["information"],
#         },
#         "reference": line["reference"],
#     })

# fout = open('condition/prompts_condition.jsonl', 'w')
# for line in new_data:
#     fout.write(json.dumps(line, ensure_ascii=False) + '\n')
# fout.close()

