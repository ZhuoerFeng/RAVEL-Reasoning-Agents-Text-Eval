import json
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import os

# 1. Load the dataset
def load_data(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return [json.loads(line) for line in f]

# 2. Process and Analyze
def analyze_benchmark(data):
    stats = []
    for entry in data:
        infer_id = entry.get('infer_id')
        task_type = entry.get('task_type')
        sub_task = entry.get('sub_task')
        
        # 英文计数 (按空格切分)
        instr_len = len(entry.get('instruction', '').split())
        ref_len = len(entry.get('reference', '').split())
        
        input_obj = entry.get('input', {})
        input_text_combined = " ".join([str(v) for v in input_obj.values()])
        input_len = len(input_text_combined.split())

        stats.append({
            "infer_id": infer_id,
            "task_type": task_type,
            "sub_task": sub_task,
            "instruction_length": instr_len,
            "input_length": input_len,
            "reference_length": ref_len
        })
    return pd.DataFrame(stats)

# --- 新增函数：生成统计 CSV ---
def generate_stat_csv(df, dataset_name, output_file='stat.csv'):
    """
    根据 task_type 分组统计各项指标并保存为 CSV
    """
    # 按照 task_type 分组并进行聚合计算
    stat_df = df.groupby('task_type').agg(
        Avg_Instr=('instruction_length', 'mean'),
        Max_Instr=('instruction_length', 'max'),
        Min_Instr=('instruction_length', 'min'),
        Avg_Input=('input_length', 'mean'),
        Max_Input=('input_length', 'max'),
        Avg_Reference=('reference_length', 'mean'),
        Max_Reference=('reference_length', 'max'),
        Total_Count=('infer_id', 'count')
    ).reset_index()

    # 添加 Dataset 列名
    stat_df['Dataset'] = dataset_name
    
    # 调整列顺序，使 Dataset 在第一列（或按要求排布）
    cols = ['task_type', 'Dataset', 'Avg_Instr', 'Max_Instr', 'Min_Instr', 
            'Avg_Input', 'Max_Input', 'Avg_Reference', 'Max_Reference', 'Total_Count']
    stat_df = stat_df[cols]
    
    # 保留两位小数，美化输出
    stat_df = stat_df.round(2)
    
    # 保存结果
    stat_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Statistics saved to '{output_file}'.")
    return stat_df

# 3. Visualization for ICML Publication
def save_publication_plots(df, output_dir='icml_plots'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    sns.set_theme(style="whitegrid")
    sns.set_context("talk", font_scale=1.2) 
    
    LABEL_SIZE = 18
    TICK_SIZE = 14
    FIG_SIZE = (8, 6)
    DPI = 300

    # --- Plot A: Task Type ---
    plt.figure(figsize=FIG_SIZE)
    sns.countplot(data=df, x='task_type', palette='viridis')
    plt.xlabel('Task Type', fontsize=LABEL_SIZE)
    plt.ylabel('Count', fontsize=LABEL_SIZE)
    plt.xticks(rotation=15, fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_task_type_dist.png', dpi=DPI)
    plt.close()

    # --- Plot B: Sub-task ---
    plt.figure(figsize=(8, 10))
    sns.countplot(data=df, y='sub_task', palette='magma')
    plt.xlabel('Count', fontsize=LABEL_SIZE)
    plt.ylabel('Sub-task', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_sub_task_dist.png', dpi=DPI)
    plt.close()

    # --- Plot C: Length Boxplot ---
    plt.figure(figsize=FIG_SIZE)
    df_melted = df.melt(value_vars=['instruction_length', 'input_length', 'reference_length'], 
                        var_name='Component', value_name='Word Count')
    df_melted['Component'] = df_melted['Component'].str.replace('_length', '')
    sns.boxplot(data=df_melted, x='Component', y='Word Count')
    plt.xlabel('Component', fontsize=LABEL_SIZE)
    plt.ylabel('Word Count', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_length_boxplot.png', dpi=DPI)
    plt.close()

    # --- Plot D: Correlation ---
    plt.figure(figsize=FIG_SIZE)
    sns.scatterplot(data=df, x='input_length', y='reference_length', hue='task_type', s=100)
    plt.xlabel('Input Length', fontsize=LABEL_SIZE)
    plt.ylabel('Reference Length', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.legend(fontsize=TICK_SIZE - 2, title_fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_input_vs_ref_correlation.png', dpi=DPI)
    plt.close()

    print(f"Publication-ready plots saved to '{output_dir}'.")

# --- Execution ---
FILE_NAME = 'english_dataset.jsonl'
if os.path.exists(FILE_NAME):
    data = load_data(FILE_NAME)
    df = analyze_benchmark(data)
    
    # 1. 生成并保存统计 CSV
    generate_stat_csv(df, dataset_name=FILE_NAME)
    
    # 2. 生成并保存图表
    save_publication_plots(df)
else:
    print(f"Error: {FILE_NAME} not found.")