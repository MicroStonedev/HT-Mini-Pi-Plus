@echo off
title Mini Pi+ Demo 1 - Flat Ground Walking (interactive)
cd /d "%~dp0"
echo ==================================================
echo  Demo 1: Mini Pi+ flat-ground walking (keyboard control)
echo  Keys: 8/2 fwd +-0.2   4/6 sidestep   7/9 turn
echo        5 = stop    Esc = quit
echo  Mouse: left-drag rotate, wheel zoom, right-drag pan
echo ==================================================
echo Press any key to start...
pause >nul
"D:\python3.12.10\python.exe" tools\sim2sim_interactive.py --duration 60
echo.
echo Demo 1 finished, exit code %errorlevel%
pause
