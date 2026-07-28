# 方案 A: 使用 nohup
nohup python run_contamination_eval.py > eval_log.txt 2>&1 &

# 方案 B: 使用 tmux (推荐，方便随时查看进度)
tmux new -s eval_session
python run_contamination_eval.py
# (按 Ctrl+b 然后按 d 退出界面，后台继续运行)