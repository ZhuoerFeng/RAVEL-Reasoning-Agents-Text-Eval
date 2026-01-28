# import json
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# from collections import Counter

# # 1. Load the dataset
# # Assuming your data is in a list of dictionaries format within a .json file
# def load_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         # return json.load(f)
#         return [json.loads(line) for line in f]

# # 2. Process and Analyze
# def analyze_benchmark(data):
#     stats = []
    
#     for entry in data:
#         # Extract basic info
#         infer_id = entry.get('infer_id')
#         task_type = entry.get('task_type')
#         sub_task = entry.get('sub_task')
        
#         # Length calculations (Word counts)
#         instr_len = len(entry.get('instruction', '').split())
#         ref_len = len(entry.get('reference', '').split())
        
#         # Input complexity (handling nested structure)
#         input_obj = entry.get('input', {})
#         # Combine all strings in the input object to measure total input context
#         input_text_combined = " ".join([str(v) for v in input_obj.values()])
#         input_len = len(input_text_combined.split())

#         stats.append({
#             "infer_id": infer_id,
#             "task_type": task_type,
#             "sub_task": sub_task,
#             "instruction_length": instr_len,
#             "input_length": input_len,
#             "reference_length": ref_len
#         })

#     df = pd.DataFrame(stats)
#     return df

# # 3. Visualization
# def plot_distributions(df):
#     sns.set_theme(style="whitegrid")
#     fig, axes = plt.subplots(2, 2, figsize=(15, 12))

#     # A. Task Type Distribution
#     sns.countplot(data=df, x='task_type', ax=axes[0, 0], palette='viridis')
#     axes[0, 0].set_title('Distribution of Task Types')

#     # B. Sub-task Distribution
#     sns.countplot(data=df, y='sub_task', ax=axes[0, 1], palette='magma')
#     axes[0, 1].set_title('Distribution of Sub-tasks')

#     # C. Length Comparison (Boxplot)
#     df_melted = df.melt(value_vars=['instruction_length', 'input_length', 'reference_length'], 
#                         var_name='Component', value_name='Word Count')
#     sns.boxplot(data=df_melted, x='Component', y='Word Count', ax=axes[1, 0])
#     axes[1, 0].set_title('Text Length Distribution per Component')

#     # D. Input vs Reference Correlation
#     sns.scatterplot(data=df, x='input_length', y='reference_length', hue='task_type', ax=axes[1, 1])
#     axes[1, 1].set_title('Input Length vs. Reference Length')

#     plt.tight_layout()
#     # plt.show()
#     plt.savefig('benchmark_analysis.png')

# # Execution Example:
# data = load_data('english_dataset.jsonl')
# df = analyze_benchmark(data)
# print(df.describe())
# plot_distributions(df)

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
        
        # 英文计数
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

# 3. Visualization for ICML Publication
def save_publication_plots(df, output_dir='icml_plots'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
        
    # 设置论文风格，font_scale 设为 1.5 确保在 2x2 布局中依然清晰
    sns.set_theme(style="whitegrid")
    sns.set_context("talk", font_scale=1.2) 
    
    # 公共参数设置
    LABEL_SIZE = 18
    TICK_SIZE = 14
    FIG_SIZE = (8, 6) # 相对较小的画布，会让字体显得更大
    DPI = 300

    # --- Plot A: Task Type ---
    plt.figure(figsize=FIG_SIZE)
    ax = sns.countplot(data=df, x='task_type', palette='viridis')
    plt.xlabel('Task Type', fontsize=LABEL_SIZE)
    plt.ylabel('Count', fontsize=LABEL_SIZE)
    plt.xticks(rotation=15, fontsize=TICK_SIZE) # 略微旋转防止重叠
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_task_type_dist.png', dpi=DPI)
    plt.close()

    # --- Plot B: Sub-task (Horizontal) ---
    plt.figure(figsize=(8, 10)) # 纵向子任务多，增加高度
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
    # 缩短 X 轴标签防止拥挤
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
    # 调整图例字号
    plt.legend(fontsize=TICK_SIZE - 2, title_fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/en_input_vs_ref_correlation.png', dpi=DPI)
    plt.close()

    print(f"Publication-ready plots saved to '{output_dir}'.")

# Execution
data = load_data('english_dataset.jsonl')
df = analyze_benchmark(data)
save_publication_plots(df)

