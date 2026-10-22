@echo off
chcp 65001 >nul
title Record - Flat Ground Walking (20s)
cd /d "%~dp0"
echo ==================================================
echo  Recording: Mini Pi+ flat-ground walking, 20 seconds
echo  Output: results\videos\demo_pi_plus_free_20s.mp4
echo  (takes roughly 2-4x the video length, wait for
echo   the "[record] done" line before closing)
echo ==================================================
pause
"D:\python3.12.10\python.exe" tools\record_demo.py --scene flat --camera free --duration 20
echo.
echo Done. Exit code %errorlevel%
pause
