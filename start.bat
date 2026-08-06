@echo off
rem Rhine-Lore 一键启动（保持窗口以查看日志，Ctrl+C 停止）
cd /d "%~dp0"
python main.py --port 8786
pause
