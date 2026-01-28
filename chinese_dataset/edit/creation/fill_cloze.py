import json
import threading
from functools import partial
from concurrent.futures import ThreadPoolExecutor

# 假设 get_llm_response 和 model 初始化已经在环境中定义
# STEP2_SYSTEM_PROMPT 使用上面的定义

def process_infilling_item(line, system_prompt_template):
    """单条数据填空处理逻辑"""
    try:
        data = json.loads(line.strip())
        split_data = data.get('split_data', {})
        
        prefix = split_data.get('prefix', '')
        suffix = split_data.get('suffix', '')
        middle_len = len(split_data.get('middle', '')) # 获取真实人类写作的长度
        
        # 构造动态 System Prompt (注入长度约束)
        system_prompt = system_prompt_template.replace("{{expected_length}}", str(middle_len))
        
        # 构造 User Message
        user_message = (
            f"文章标题：{data.get('title')}\n"
            f"文章分类：{data.get('category')}\n\n"
            f"【前文】：\n{prefix}\n\n"
            f"【缺失内容 (请撰写此处)】：\n[REWRITING_TARGET_PLACEHOLDER]\n\n"
            f"【后文】：\n{suffix}"
        )
        
        # 调用 LLM
        llm_filled_content = get_llm_response(system_prompt, user_message)
        
        if llm_filled_content:
            # 存储生成的初稿
            data['step2_infilling'] = {
                "llm_filled_content": llm_filled_content.strip(),
                "target_length": middle_len,
                "actual_generated_length": len(llm_filled_content)
            }
            return data
        return None
    except Exception as e:
        print(f"处理异常: {e}")
        return None

def main_step2(input_file: str, output_file: str):
    write_lock = threading.Lock()
    
    # 系统提示词模板
    system_template = """你是一位极具文学素养和逻辑思维的专业撰稿人。
Task: 请根据提供的文章上下文，为 [缺失内容] 部分撰写一段文字，使整篇文章完整、通顺。
Requirements:
1. 风格一致性：观察前文和后文的语气，保持文风高度统一。
2. 逻辑衔接：确保内容逻辑严密地承接前文，自然地引向后文。
3. 篇幅要求：[缺失内容] 的原长度约为 {{expected_length}} 字。请你的撰写长度也保持在此水平。
4. 输出规范：直接输出填补的内容，禁止输出废话。"""

    worker_func = partial(process_infilling_item, system_prompt_template=system_template)
    
    with open(input_file, 'r', encoding='utf-8') as f_in, \
         open(output_file, 'w', encoding='utf-8') as f_out:
        
        lines = f_in.readlines()
        print(f"开始执行 Step 2 填空任务，共 {len(lines)} 条数据...")
        
        with ThreadPoolExecutor(max_workers=20) as executor:
            results = executor.map(worker_func, lines)
            
            for result in results:
                if result:
                    with write_lock:
                        f_out.write(json.dumps(result, ensure_ascii=False) + '\n')
                        f_out.flush()
    print("Step 2 完成！结果已保存至:", output_file)

if __name__ == "__main__":
    main_step2("step1_verified.jsonl", "step2_filled.jsonl")