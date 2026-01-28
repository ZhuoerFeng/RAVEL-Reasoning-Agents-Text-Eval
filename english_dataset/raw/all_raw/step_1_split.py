import json
import random
random.seed(42)

fin = open('step_0_result.jsonl').readlines()

# 520 sample in total
# 100 for end2end
# 100 for condition
# rest for cloze

data = [json.loads(x) for x in fin]
random.shuffle(data)

end2end_data = data[:100]
condition_data = data[100:200]
cloze_data = data[200:]

fout = open('step_1_end2end.jsonl', 'w')
for line in end2end_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()    
fout = open('step_1_condition.jsonl', 'w')
for line in condition_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()
fout = open('step_1_cloze.jsonl', 'w')
for line in cloze_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()

