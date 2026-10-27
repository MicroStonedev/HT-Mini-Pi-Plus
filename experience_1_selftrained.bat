@echo off
chcp 437 >nul
title Experience 1 - Self-trained Policy in Classroom
cd /d "%~dp0"
color 0B
echo.
echo ==========================================================
echo   EXPERIENCE 1: Self-trained policy in a classroom
echo   (trained by us: 15000 iterations in Isaac Sim)
echo ==========================================================
echo.
echo   CONTROLS:
echo     8 / 2   forward faster / slower
echo     4 / 6   sidestep left / right
echo     7 / 9   turn left / right
echo     5       stop
echo     1 - 4   switch camera view
echo     Esc     quit
echo.
echo   MOUSE: left-drag rotate, wheel zoom, right-drag pan
echo ==========================================================
echo.
echo Press any key to start...
pause >nul
"D:\python3.12.10\python.exe" tools\sim2sim_interactive.py --policy results\checkpoints\policy.pt --model scenes\scene_classroom.xml --duration 300
echo.
echo Finished. Exit code: %errorlevel%
pause
