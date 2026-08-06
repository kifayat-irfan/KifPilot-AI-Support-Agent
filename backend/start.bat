@echo off
REM Backend startup script for Windows

echo Starting KifPilot AI Support Agent Backend...

REM Check if virtual environment exists
if not exist "venv" (
    echo Creating virtual environment...
    python -m venv venv
)

REM Activate virtual environment
call venv\Scripts\activate.bat

REM Upgrade pip
python -m pip install --upgrade pip

REM Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

REM Check if .env exists
if not exist ".env" (
    echo Creating .env from example...
    copy .env.example .env
    echo Please edit .env with your configuration
)

REM Initialize database
echo Initializing database...
python -c "from app.infrastructure.database import init_db; import asyncio; asyncio.run(init_db())"

REM Start server
echo Starting server on http://0.0.0.0:8000
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000