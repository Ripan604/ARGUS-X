@echo off
cd /d "%~dp0frontend"
npm run dev -- --hostname 127.0.0.1 --port 5173
