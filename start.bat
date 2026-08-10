@echo off
rem Rhine-Lore launcher. Keep this window open to view logs; press Ctrl+C to stop.
cd /d "%~dp0"
python main.py --host 0.0.0.0 --port 8786
pause
