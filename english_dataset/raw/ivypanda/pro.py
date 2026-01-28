import json

fin = open('ivypanda_12.jsonl').readlines()[:200]
print(len(fin))

fout = open('ivypanda_200.jsonl', 'w')
for line in fin:
    fout.write(line)
fout.close()

# 'TEXT' 