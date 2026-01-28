import json


all_data = []

f1 = open('../ivypanda/ivypanda_200.jsonl').readlines()

for line in f1:
    line = json.loads(line)
    all_data.append({
        "content": line['TEXT'].strip(),
        'source': 'ivypanda',
        'meta': {"source": line.get('SOURCE', '').strip()}
    })

f2 = open('../obooks/collected_data.jsonl').readlines()
for line in f2:
    line = json.loads(line)
    all_data.append({
        "content": line['content'].strip(),
        'source': 'obooks',
        'meta': {"filename": line['filename'], "path": line['path']}
    })

f3 = open('../speeches/collected_speeches.jsonl').readlines()
for line in f3:
    line = json.loads(line)
    all_data.append({
        "content": line['content'].strip(),
        'source': 'american_rhetoric',
        'meta': {"title": line.get('Title', '').strip(), "speaker": line.get('Speaker', '').strip(), 'date': line.get('Date', ''), 'location': line.get('Field', '')}
    })

f4 = open('../essayinstruction/essay_instructions_test.jsonl').readlines()
for line in f4:
    line = json.loads(line)
    all_data.append({
        "content": line['content'].strip(),
        'source': 'essay_instruction',
        'meta': {}
    })

fout = open('step_0_result.jsonl', 'w')
for line in all_data:
    fout.write(json.dumps(line, ensure_ascii=False) + '\n')
fout.close()