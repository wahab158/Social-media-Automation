@echo off
echo Starting Social Media Automation Dashboard...

:: Start Backend in a new window
echo Starting FastAPI Backend on port 8000...
start cmd /k "python api_main.py"

:: Start Frontend in a new window
echo Starting Vite Frontend on port 5173...
cd frontend
start cmd /k "npm run dev"

echo Dashboard services are starting. 
echo Backend: http://localhost:8000
echo Frontend: http://localhost:5173
pause
