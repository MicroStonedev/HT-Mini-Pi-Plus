@echo off
chcp 437 >nul
title Experience 2 - Official Policy in Classroom
cd /d "%~dp0"
color 0E
echo.
echo ==========================================================
echo   EXPERIENCE 2: OFFICIAL policy in a classroom (control)
echo   (provided by HighTorque: 40000 iterations)
echo ==========================================================
echo.
echo   Same controls as Experience 1:
echo     8/2 forward   4/6 sidestep   7/9 turn   5 stop   1-4 camera
echo ==========================================================
echo.
echo Press any key to start...
pause >nul
"D:\python3.12.10\python.exe" tools\sim2sim_interactive.py --policy results\checkpoints\model_40000_jit.pt --model scenes\scene_classroom.xml --duration 300
echo.
echo Finished. Exit code: %errorlevel%
pause
