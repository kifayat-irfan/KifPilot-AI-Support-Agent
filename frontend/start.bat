@echo off
REM Frontend startup script for Windows

echo Starting KifPilot AI Support Agent Frontend...

REM Check if node_modules exists
if not exist "node_modules" (
    echo Installing dependencies...
    npm install
)

REM Check if .env exists
if not exist ".env" (
    echo Creating .env from example...
    copy .env.example .env
    echo Please edit .env with your configuration
)

REM Start development server
echo Starting development server on http://localhost:5173
npm run dev