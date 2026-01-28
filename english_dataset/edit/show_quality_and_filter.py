import json
import os

def finalize_benchmark(audited_file, final_output_file):
    """
    计算通过率并提取金牌样本（Golden Samples）
    """
    total_count = 0
    passed_count = 0
    
    # 用于统计具体哪个维度出问题最多
    failure_stats = {
        "problem_1_fail": 0,
        "problem_2_fail": 0,
        "problem_3_fail": 0
    }

    if not os.path.exists(audited_file):
        print(f"错误：找不到审计文件 {audited_file}")
        return

    with open(audited_file, 'r', encoding='utf-8') as f_in, \
         open(final_output_file, 'w', encoding='utf-8') as f_out:
        
        for line in f_in:
            if not line.strip():
                continue
            
            total_count += 1
            data = json.loads(line)
            audit = data.get('quality_audit', {})
            
            # 获取三个维度的检查结果
            p1 = audit.get('problem_1', False)
            p2 = audit.get('problem_2', False)
            p3 = audit.get('problem_3', False)

            # 统计失败原因
            if not p1: failure_stats["problem_1_fail"] += 1
            if not p2: failure_stats["problem_2_fail"] += 1
            if not p3: failure_stats["problem_3_fail"] += 1

            # 判定标准：三项全为 True
            if p1 and p2 and p3:
                passed_count += 1
                
                # --- 数据清洗：只保留 Benchmark 任务相关的纯净字段 ---
                data.pop('quality_audit')
                data.pop('is_golden')
                f_out.write(json.dumps(data, ensure_ascii=False) + '\n')

    # --- 打印统计报告 ---
    if total_count > 0:
        pass_rate = (passed_count / total_count) * 100
        print("-" * 30)
        print(f"【Benchmark 数据审计报告】")
        print(f"样本总数: {total_count}")
        print(f"通过总数: {passed_count}")
        print(f"最终通过率: {pass_rate:.2f}%")
        print("-" * 30)
        print(f"【失败原因分析】")
        print(f"关联度校验失败 (Problem 1): {failure_stats['problem_1_fail']} 条")
        print(f"内容/原著质量不足 (Problem 2): {failure_stats['problem_2_fail']} 条")
        print(f"Critique 包含废话 (Problem 3): {failure_stats['problem_3_fail']} 条")
        print("-" * 30)
        print(f"最终文件已保存至: {final_output_file}")
    else:
        print("未发现有效数据。")

if __name__ == "__main__":
    # 执行筛选
    finalize_benchmark(
        audited_file="step_5_dataset_audited.jsonl", 
        final_output_file="step_6_edit_dataset.jsonl"
    )
    