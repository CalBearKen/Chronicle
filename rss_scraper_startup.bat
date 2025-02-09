@echo off
REM -- Run in minimized mode --
start /min "" "%ProgramFiles%\Docker\Docker\Docker Desktop.exe"

REM -- Wait for Docker to start --
timeout /t 30 /nobreak

REM -- Start all services --
cd /d "C:\path\to\your\project"
docker-compose up -d

REM -- Keep window open to view logs --
pause
