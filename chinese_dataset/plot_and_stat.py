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
        # 合并 input 字典中的所有文本内容进行统计
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

# 3. New Function: Generate Statistics CSV
def generate_statistics(df, output_file='stat.csv'):
    """
    根据任务类型统计各项指标并保存为 CSV
    """
    # 按照需求进行聚合计算
    stat_df = df.groupby('task_type').agg(
        Avg_Instr=('instruction_length', 'mean'),
        Max_Instr=('instruction_length', 'max'),
        Min_Instr=('instruction_length', 'min'),
        Avg_Input=('input_length', 'mean'),
        Max_Input=('input_length', 'max'),
        Avg_Reference=('reference_length', 'mean'),
        Max_Reference=('reference_length', 'max'),
        Total_Count=('task_type', 'count')
    ).reset_index()

    # 重命名列以符合要求
    stat_df.rename(columns={'task_type': 'Dataset'}, inplace=True)
    
    # 保留两位小数（可选，为了美观）
    numeric_cols = stat_df.select_dtypes(include=['float64']).columns
    stat_df[numeric_cols] = stat_df[numeric_cols].round(2)

    # 保存文件
    stat_df.to_csv(output_file, index=False, encoding='utf-8-sig')
    print(f"Statistics saved to '{output_file}'.")

# 4. Visualization with English Labels
def save_zh_plots_in_en(df, output_dir='zh_icml_plots'):
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # --- 重要：在此处定义你的中英文映射 ---
    translation_dict = {
        "摘要": "Summarization",
        "写作": "Writing",
        "问答": "Q&A",
        "代码": "Coding",
        "数学": "Math",
        "多文档摘要": "Multi-doc Sum",
        "创意写作": "Creative Writing",
    }
    
    # 替换数据中的中文内容
    df['task_type'] = df['task_type'].replace(translation_dict)
    df['sub_task'] = df['sub_task'].replace(translation_dict)

    # 设置绘图风格
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
    plt.savefig(f'{output_dir}/zh_data_task_type.png', dpi=DPI)
    plt.close()

    # --- Plot B: Sub-task ---
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

# --- Execution ---
if __name__ == "__main__":
    # 1. 加载数据
    data = load_data('chinese_dataset_v2.jsonl')
    
    # 2. 基础分析
    df = analyze_benchmark(data)
    
    # 3. 执行翻译（确保统计结果和图片中的标签一致）
    # 如果希望统计原始中文标签，可将此步骤移至绘图函数内部
    translation_dict = {
        "摘要": "Summarization",
        "写作": "Writing",
        "问答": "Q&A",
        "代码": "Coding",
        "数学": "Math",
    }
    df['task_type'] = df['task_type'].replace(translation_dict)
    
    # 4. 生成数据集统计文件 (stat.csv)
    generate_statistics(df, 'stat.csv')
    
    # 5. 生成绘图结果
    save_zh_plots_in_en(df)