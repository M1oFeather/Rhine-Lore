@echo off
rem Rhine-Lore launcher. Keep this window open to view logs; press Ctrl+C to stop.
cd /d "%~dp0"
python main.py --port 8786
pause
