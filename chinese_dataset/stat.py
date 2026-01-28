import json
import os
import pandas as pd
import matplotlib.pyplot as plt

# --- 1. macOS Chinese Character Setup ---
plt.rcParams['font.sans-serif'] = ['Heiti SC'] 
plt.rcParams['axes.unicode_minus'] = False 
plt.style.use('ggplot')

# --- 2. Configuration & Data Loading ---
dataset_files = {
    "Edit": "edit/prompts_edit.jsonl",
    "Cloze": "cloze/prompts_cloze.jsonl",
    "End-to-End": "end2end/prompts_end2end.jsonl",
    "Condition": "condition/prompts_condition.jsonl"
}

all_records = []

for task_name, path in dataset_files.items():
    if not os.path.exists(path):
        print(f"Warning: {path} not found. Skipping...")
        continue
        
    with open(path, 'r', encoding='utf-8') as f:
        for line in f:
            item = json.loads(line)
            all_records.append({
                "Dataset": task_name,
                "Sub-task": item.get("sub_task", "unknown"),
                "Instr_Len": len(item.get("instruction", "")),
                "Input_Len": sum(len(str(v)) for v in item.get("input", {}).values()),
                "Reference_Len": len(item.get("reference", ""))
            })

df = pd.DataFrame(all_records)

# --- 3. Statistical Analysis & CSV Export ---

# A. Dataset Summary (General Stats)
summary = df.groupby('Dataset').agg({
    'Instr_Len': ['mean', 'max', 'min'],
    'Input_Len': ['mean', 'max'],
    'Reference_Len': ['mean', 'max'],
    'Sub-task': 'count'
}).round(2)
summary.columns = ['Avg_Instr', 'Max_Instr', 'Min_Instr', 'Avg_Input', 'Max_Input', 'Avg_Reference', 'Max_Reference', 'Total_Count']
summary.to_csv('dataset_summary.csv', encoding='utf_8_sig')

# B. Dataset Hierarchy (Main Task vs Sub-task breakdown)
hierarchy_stats = df.groupby(['Dataset', 'Sub-task']).size().unstack(fill_value=0)
hierarchy_stats.to_csv('dataset_hierarchy.csv', encoding='utf_8_sig')

# --- 4. Visualizations ---

# FIGURE 1: Overview & Top Sub-tasks
fig1, ax1 = plt.subplots(1, 2, figsize=(15, 6))

# Plot: Average Lengths
summary[['Avg_Instr', 'Avg_Input', 'Avg_Reference']].plot(kind='bar', ax=ax1[0])
ax1[0].set_title('各任务平均字符长度 (Avg Length per Task)')
ax1[0].set_ylabel('字符数 (Chars)')

# Plot: Top 10 Sub-tasks overall
subtask_counts = df['Sub-task'].value_counts().head(10)
subtask_counts.plot(kind='pie', ax=ax1[1], autopct='%1.1f%%', startangle=140)
ax1[1].set_title('子任务总体分布 Top 10')
ax1[1].set_ylabel('')

plt.tight_layout()
plt.savefig('overview_metrics.png')

# FIGURE 2: Dataset Composition (Stacked Bar)
# This shows how many sub-tasks make up each of the 4 main datasets
plt.figure(figsize=(12, 7))
hierarchy_stats.plot(kind='bar', stacked=True, ax=plt.gca(), colormap='tab20')
plt.title('数据集构成详情 (Dataset Composition by Sub-task)')
plt.xlabel('主要任务 (Main Dataset)')
plt.ylabel('样本数量 (Sample Count)')
plt.legend(title='子任务 (Sub-tasks)', bbox_to_anchor=(1.05, 1), loc='upper left', fontsize='small')
plt.tight_layout()
plt.savefig('dataset_composition.png')

print("=== Reports Generated ===")
print("1. dataset_summary.csv (High-level metrics)")
print("2. dataset_hierarchy.csv (Task breakdown matrix)")
print("3. overview_metrics.png & dataset_composition.png (Charts)")