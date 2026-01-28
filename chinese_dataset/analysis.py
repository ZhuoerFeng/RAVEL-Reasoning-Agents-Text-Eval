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
#         instr_len = len(entry.get('instruction', ''))
#         ref_len = len(entry.get('reference', ''))
        
#         # Input complexity (handling nested structure)
#         input_obj = entry.get('input', {})
#         # Combine all strings in the input object to measure total input context
#         input_text_combined = " ".join([str(v) for v in input_obj.values()])
#         input_len = len(input_text_combined)

#         ref_exceed_5k = ref_len > 5000

#         stats.append({
#             "infer_id": infer_id,
#             "task_type": task_type,
#             "sub_task": sub_task,
#             "instruction_length": instr_len,
#             "input_length": input_len,
#             "reference_length": ref_len,
#             "reference_exceeds_5k": ref_exceed_5k
#         })


#     df = pd.DataFrame(stats)
#     # print the number of entries where reference exceeds 5000 words
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
# data = load_data('chinese_dataset_v2.jsonl')
# df = analyze_benchmark(data)
# print(df.describe())
# plot_distributions(df)

# print(df['reference_exceeds_5k'].value_counts())








# import json
# import pandas as pd
# import matplotlib.pyplot as plt
# import seaborn as sns
# import os

# # 1. Load the dataset
# def load_data(file_path):
#     with open(file_path, 'r', encoding='utf-8') as f:
#         return [json.loads(line) for line in f]

# # 2. Process and Analyze
# def analyze_benchmark(data):
#     stats = []
#     for entry in data:
#         infer_id = entry.get('infer_id')
#         task_type = entry.get('task_type')
#         sub_task = entry.get('sub_task')
        
#         instr_len = len(entry.get('instruction', ''))
#         ref_len = len(entry.get('reference', ''))
        
#         input_obj = entry.get('input', {})
#         input_text_combined = " ".join([str(v) for v in input_obj.values()])
#         input_len = len(input_text_combined)

#         ref_exceed_5k = ref_len > 5000

#         stats.append({
#             "infer_id": infer_id,
#             "task_type": task_type,
#             "sub_task": sub_task,
#             "instruction_length": instr_len,
#             "input_length": input_len,
#             "reference_length": ref_len,
#             "reference_exceeds_5k": ref_exceed_5k
#         })
#     return pd.DataFrame(stats)

# # 3. Visualization (Modified to save 4 separate files)
# def save_individual_plots(df, output_dir='plots'):
#     # 如果文件夹不存在则创建
#     if not os.path.exists(output_dir):
#         os.makedirs(output_dir)
        
#     sns.set_theme(style="whitegrid")

#     # --- 图 A: Task Type Distribution ---
#     plt.figure(figsize=(10, 6))
#     sns.countplot(data=df, x='task_type', palette='viridis')
#     plt.xlabel('Task Type')
#     plt.ylabel('Count')
#     # 去掉标题: axes.set_title(...) 已删除
#     plt.tight_layout()
#     plt.savefig(f'{output_dir}/task_type_dist.png')
#     plt.close()

#     # --- 图 B: Sub-task Distribution ---
#     plt.figure(figsize=(10, 8))
#     sns.countplot(data=df, y='sub_task', palette='magma')
#     plt.xlabel('Count')
#     plt.ylabel('Sub-task')
#     plt.tight_layout()
#     plt.savefig(f'{output_dir}/sub_task_dist.png')
#     plt.close()

#     # --- 图 C: Length Comparison (Boxplot) ---
#     plt.figure(figsize=(10, 6))
#     df_melted = df.melt(value_vars=['instruction_length', 'input_length', 'reference_length'], 
#                         var_name='Component', value_name='Word Count')
#     sns.boxplot(data=df_melted, x='Component', y='Word Count')
#     plt.xlabel('Component')
#     plt.ylabel('Word Count')
#     plt.tight_layout()
#     plt.savefig(f'{output_dir}/length_boxplot.png')
#     plt.close()

#     # --- 图 D: Input vs Reference Correlation ---
#     plt.figure(figsize=(10, 6))
#     sns.scatterplot(data=df, x='input_length', y='reference_length', hue='task_type')
#     plt.xlabel('Input Length')
#     plt.ylabel('Reference Length')
#     plt.tight_layout()
#     plt.savefig(f'{output_dir}/input_vs_ref_correlation.png')
#     plt.close()

#     print(f"All plots saved to the '{output_dir}' directory.")

# # Execution
# data = load_data('chinese_dataset_v2.jsonl')
# df = analyze_benchmark(data)

# print("Data Statistics:")
# print(df.describe())

# # 执行保存
# save_individual_plots(df)

# print("\nReference > 5k count:")
# print(df['reference_exceeds_5k'].value_counts())






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
        
        # 中文通常按字符数统计
        instr_len = len(entry.get('instruction', ''))
        ref_len = len(entry.get('reference', ''))
        
        input_obj = entry.get('input', {})
        input_text_combined = " ".join([str(v) for v in input_obj.values()])
        input_len = len(input_text_combined)

        stats.append({
            "infer_id": infer_id,
            "task_type": task_type,
            "sub_task": sub_task,
            "instruction_length": instr_len,
            "input_length": input_len,
            "reference_length": ref_len
        })
    return pd.DataFrame(stats)

# 3. Visualization with English Labels
def save_zh_plots_in_en(df, output_dir='zh_icml_plots'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- 重要：在此处定义你的中英文映射 ---
    # 脚本会自动将列中的中文替换为对应的英文
    translation_dict = {
        # 任务类型映射示例 (请根据你的实际数据修改)
        "摘要": "Summarization",
        "写作": "Writing",
        "问答": "Q&A",
        "代码": "Coding",
        "数学": "Math",
        # 子任务映射示例
        "多文档摘要": "Multi-doc Sum",
        "创意写作": "Creative Writing",
        # 如果有没覆盖到的，可以继续添加...
    }
    
    # 替换数据中的中文内容
    df['task_type'] = df['task_type'].replace(translation_dict)
    df['sub_task'] = df['sub_task'].replace(translation_dict)

    # 设置绘图风格 (针对 ICML 优化)
    sns.set_theme(style="whitegrid")
    sns.set_context("talk", font_scale=1.2)
    
    LABEL_SIZE = 18
    TICK_SIZE = 14
    FIG_SIZE = (8, 6)
    DPI = 300

    # --- Plot A: Task Type (English labels) ---
    plt.figure(figsize=FIG_SIZE)
    sns.countplot(data=df, x='task_type', palette='viridis')
    plt.xlabel('Task Type', fontsize=LABEL_SIZE)
    plt.ylabel('Count', fontsize=LABEL_SIZE)
    plt.xticks(rotation=15, fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/zh_data_task_type.png', dpi=DPI)
    plt.close()

    # --- Plot B: Sub-task (English labels) ---
    plt.figure(figsize=(8, 10))
    sns.countplot(data=df, y='sub_task', palette='magma')
    plt.xlabel('Count', fontsize=LABEL_SIZE)
    plt.ylabel('Sub-task', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/zh_data_sub_task.png', dpi=DPI)
    plt.close()

    # --- Plot C: Length Boxplot ---
    plt.figure(figsize=FIG_SIZE)
    df_melted = df.melt(value_vars=['instruction_length', 'input_length', 'reference_length'], 
                        var_name='Component', value_name='Char Count')
    # 英文轴名
    df_melted['Component'] = df_melted['Component'].str.replace('_length', '').str.replace('_', ' ').str.title()
    
    sns.boxplot(data=df_melted, x='Component', y='Char Count')
    plt.xlabel('Component', fontsize=LABEL_SIZE)
    plt.ylabel('Character Count', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/zh_data_length_boxplot.png', dpi=DPI)
    plt.close()

    # --- Plot D: Correlation ---
    plt.figure(figsize=FIG_SIZE)
    sns.scatterplot(data=df, x='input_length', y='reference_length', hue='task_type', s=100)
    plt.xlabel('Input Length (Chars)', fontsize=LABEL_SIZE)
    plt.ylabel('Reference Length (Chars)', fontsize=LABEL_SIZE)
    plt.xticks(fontsize=TICK_SIZE)
    plt.yticks(fontsize=TICK_SIZE)
    plt.legend(fontsize=TICK_SIZE - 2, title_fontsize=TICK_SIZE)
    plt.tight_layout()
    plt.savefig(f'{output_dir}/zh_data_correlation.png', dpi=DPI)
    plt.close()

    print(f"All Chinese data plots (translated to English) saved to '{output_dir}'.")

# Execution
data = load_data('chinese_dataset_v2.jsonl')
df = analyze_benchmark(data)
save_zh_plots_in_en(df)