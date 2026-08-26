@echo off
title CayMit Web Dashboard
echo ==============================================
echo   DANG KHOI DONG BACKEND VA WEB DASHBOARD
echo ==============================================
start "CayMit Backend" /min cmd /c "cd /d %~dp0 && python backend\main.py"
echo [1/2] Backend AI dang chay ngam tai cong 8000...
timeout /t 2 /nobreak >nul
echo [2/2] Dang khoi dong Web Frontend...
npm run dev
pause
