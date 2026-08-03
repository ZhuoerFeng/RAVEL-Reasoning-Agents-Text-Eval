import json
import csv
from pathlib import Path
from collections import defaultdict

def calculate_metrics_mean(directory_path="results", output_csv="summary_metrics.csv"):
    dir_path = Path(directory_path)
    if not dir_path.exists():
        print(f"❌ 错误：未找到目录 '{directory_path}'！请确保该目录存在。")
        return

    all_file_stats = []
    all_metric_keys = set()

    print(f"正在扫描 '{directory_path}' 目录下的 jsonl 文件...\n")

    # 遍历目录下所有 jsonl 文件
    for file_path in dir_path.glob("*.jsonl"):
        metric_sums = defaultdict(float)
        metric_counts = defaultdict(int)

        # 逐行读取以防止大文件导致内存溢出
        with file_path.open('r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    data = json.loads(line)
                    metrics = data.get("metrics", {})
                    # 累加各项指标的值与次数
                    for k, v in metrics.items():
                        if isinstance(v, (int, float)):
                            metric_sums[k] += v
                            metric_counts[k] += 1
                            all_metric_keys.add(k)
                except json.JSONDecodeError:
                    continue  # 跳过解析失败的残缺行

        # 计算当前文件的各项指标均值
        file_means = {"Filename": file_path.name}
        for k in metric_counts:
            file_means[k] = metric_sums[k] / metric_counts[k]
        
        all_file_stats.append(file_means)

    if not all_file_stats:
        print("⚠️ 没有找到任何有效的统计数据，请检查文件格式。")
        return

    # 确定表头：文件名放在第一列，后面的 metrics 按字母排序
    metric_columns = sorted(list(all_metric_keys))
    header = ["Filename"] + metric_columns

    # 1. 打印到控制台展示 (排版对齐)
    col_width_filename = max(max(len(s["Filename"]) for s in all_file_stats), 15)
    col_width_metric = 15
    
    header_format = f"{{:<{col_width_filename}}} | " + " | ".join([f"{{:>{col_width_metric}}}"] * len(metric_columns))
    separator = "-" * (col_width_filename + 3 + (col_width_metric + 3) * len(metric_columns))
    
    ## 按照字母顺序排序
    all_file_stats.sort(key=lambda x: x["Filename"])

    print(header_format.format(*header))
    print(separator)

    for stats in all_file_stats:
        row = [stats["Filename"]]
        for col in metric_columns:
            val = stats.get(col, "N/A")
            # 格式化浮点数保留 6 位小数
            row.append(f"{val:.6f}" if isinstance(val, float) else val)
        print(header_format.format(*row))

    # # 2. 导出为 CSV 文件供 Excel / Pandas 分析
    # with open(output_csv, 'w', encoding='utf-8', newline='') as f:
    #     writer = csv.DictWriter(f, fieldnames=header)
    #     writer.writeheader()
    #     writer.writerows(all_file_stats)

    # print(f"\n✅ 统计完成！详细结果已保存至同级目录下的: {output_csv}")

if __name__ == "__main__":
    # 你可以在这里修改输入目录和输出文件名
    calculate_metrics_mean(directory_path="results_c3e", output_csv="summary_metrics.csv")