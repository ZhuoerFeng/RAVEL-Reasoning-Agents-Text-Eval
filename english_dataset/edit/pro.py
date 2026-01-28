import json

fin = open('step_3_revision_critiques.jsonl').readlines()

new_data = []
idx = 0
for line in fin:
    data = json.loads(line)
    new_data.append({
        "infer_id": "edit_en_" + str(idx),
        "task_type": "edit",
        "sub_task": data["sub_task"],
        "instruction": """Your task is to rewrite the draft based on the **"content"** (original background material)  while incorporating the **"critique"** (Professional Critique and Revision Suggestions). The rewrite must meet the following requirements:\n\n1. Improve the quality of expression within the content.\n2. Optimize the logical structure.\n3. Revising according to the critiques while reducing formulaic or clichéd expressions.\n4. Appropriately enhance emotional tension.\n5. Retain the original core message, while allowing for creative adjustments in the style of expression.\n\nYour output should be the rewritten text only.""",
        "input": {
            'content': data['cloze_results'],
            'critique': data['step3_critique']['critique_content'],
        },
        "reference": data["reference"],
    })

    idx += 1

fout = open('step_4_edit_benchmark.jsonl', 'w')
for line in new_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()

