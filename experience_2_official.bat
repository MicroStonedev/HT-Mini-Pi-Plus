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
echo   STEP 1: CLICK INSIDE THE WINDOW (keyboard needs focus!)
echo.
echo   W/S forward   A/D sidestep   Q/E turn   SPACE stop   TAB camera
echo ==========================================================
echo.
echo Press any key to start...
pause >nul
"D:\python3.12.10\python.exe" tools\sim2sim_interactive.py --policy results\checkpoints\model_40000_jit.pt --model scenes\scene_classroom.xml --duration 300
echo.
echo Finished. Exit code: %errorlevel%
pause
