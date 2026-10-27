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
echo   STEP 1: CLICK INSIDE THE WINDOW (keyboard needs focus!)
echo.
echo   W / S   forward faster / slower   (also 8 / 2)
echo   A / D   sidestep left / right     (also 4 / 6)
echo   Q / E   turn left / right         (also 7 / 9)
echo   SPACE   stop                      (also 5)
echo   TAB     cycle camera view
echo   Esc     quit
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
