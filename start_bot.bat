@echo off
:: Financial Assistant Bot - Silent background runner
:: Place this in your Windows Startup folder to auto-run on login

cd /d "C:\Users\munag\.gemini\antigravity\scratch\financial-assistant"

:: Run bot silently using pythonw (no terminal window shown)
start "" /B "venv\Scripts\pythonw.exe" scripts\run_polling.py

exit
