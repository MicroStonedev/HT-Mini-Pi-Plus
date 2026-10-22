@echo off
title Mini Pi+ Demo 2 - Reconstructed Classroom (interactive)
cd /d "%~dp0"
echo ==================================================
echo  Demo 2: walking in the reconstructed classroom
echo  (Qunhe Aholo LiDAR point cloud, Yuyao No.4 school)
echo  Keys: 8/2 fwd +-0.2   4/6 sidestep   7/9 turn
echo        5 = stop    Esc = quit
echo  Mouse: left-drag rotate, wheel zoom, right-drag pan
echo  First load of the scene mesh takes a few seconds
echo ==================================================
echo Press any key to start...
pause >nul
"D:\python3.12.10\python.exe" tools\sim2sim_interactive.py --duration 60 --model scenes\scene_classroom.xml
echo.
echo Demo 2 finished, exit code %errorlevel%
pause
