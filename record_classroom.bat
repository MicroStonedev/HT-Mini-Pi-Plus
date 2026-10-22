@echo off
chcp 65001 >nul
title Record - Classroom Aisle Walk (15s)
cd /d "%~dp0"
echo ==================================================
echo  Recording: walking down the classroom aisle, 15 seconds
echo  Camera: walker (chase cam from behind the robot)
echo  Output: results\videos\demo_classroom_walker_15s.mp4
echo  (takes roughly 2-4x the video length, wait for
echo   the "[record] done" line before closing)
echo ==================================================
pause
"D:\python3.12.10\python.exe" tools\record_demo.py --scene classroom --camera walker --duration 15
echo.
echo Done. Exit code %errorlevel%
pause
