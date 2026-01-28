import json


fin = open('step_6_edit_dataset.jsonl').readlines()
data = [json.loads(line) for line in fin]

new_instruction = """Your task is to rewrite the draft based on the **"content"** (original background material)  while incorporating the **"critique"** (Professional Critique and Revision Suggestions). The rewrite must meet the following requirements:\n\n1. Improve the quality of expression within the content.\n2. Optimize the logical structure.\n3. Revising according to the critiques while reducing formulaic or clichéd expressions.\n4. Appropriately enhance emotional tension.\n5. Retain the original core message, while allowing for creative adjustments in the style of expression.\n\nYour output should be the rewritten text only."""


for line in data:
    line['instruction'] = new_instruction

fout = open('step_7_edit_revised_instruction.jsonl', 'w')
for line in data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()
