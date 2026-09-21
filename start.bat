@echo off
title CayMit Web Dashboard
echo ==============================================
echo   DANG KHOI DONG BACKEND VA WEB DASHBOARD
echo ==============================================
start "CayMit Backend" /min cmd /c "cd /d %~dp0tammysmartfruit\backend && python run_dev.py"
echo [1/2] Backend AI & V1 API dang khoi dong tai cong 8000...
timeout /t 3 /nobreak >nul
echo [2/2] Dang khoi dong Web Frontend tai http://localhost:3000...
start "" "http://localhost:3000"
npm run dev
pause
