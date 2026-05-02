@echo off
title SocialAI — Smart Advertising Agent

echo Starting SocialAI...

:: Set Python environment
set PYTHONHOME=C:\Users\suppo\AppData\Local\Programs\Python\Python314
set PYTHONPATH=C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib;C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib\site-packages

:: Start the SaaS app on port 8502
start "" /min cmd /k "set PYTHONHOME=C:\Users\suppo\AppData\Local\Programs\Python\Python314 && set PYTHONPATH=C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib;C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib\site-packages && cd /d %~dp0 && streamlit run saas_app.py --server.port 8502"

:: Wait for app to load then open browser
timeout /t 6 /nobreak >nul
start http://localhost:8502

echo SocialAI is running at http://localhost:8502
echo You can minimise this window.
