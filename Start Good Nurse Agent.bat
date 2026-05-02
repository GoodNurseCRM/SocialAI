@echo off
title Good Nurse Marketing Agent

echo Starting Good Nurse Marketing Agent...

:: Fix Python environment (Lib is separate from the exe)
set PYTHONHOME=C:\Users\suppo\AppData\Local\Programs\Python\Python314
set PYTHONPATH=C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib;C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib\site-packages

:: Start the scheduler silently in background (generates 7am briefs)
start "" /min cmd /c "set PYTHONHOME=C:\Users\suppo\AppData\Local\Programs\Python\Python314 && set PYTHONPATH=C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib;C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib\site-packages && python run_scheduler.py > scheduler.log 2>&1"

:: Wait 2 seconds then start the app
timeout /t 2 /nobreak >nul
start "" /min cmd /k "set PYTHONHOME=C:\Users\suppo\AppData\Local\Programs\Python\Python314 && set PYTHONPATH=C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib;C:\Users\suppo\AppData\Local\Programs\Python\Python314\Lib\site-packages && streamlit run app.py"

:: Wait for app to load then open browser
timeout /t 6 /nobreak >nul
start http://localhost:8501

echo Good Nurse Agent is running.
echo You can minimise this window. Close it only to shut everything down.
