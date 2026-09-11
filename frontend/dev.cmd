@echo off
rem Lance le front RushPlay en dev contre l'API locale. Usage : frontend\dev.cmd
cd /d "%~dp0"
set "NEXT_PUBLIC_API_URL=http://127.0.0.1:8000"
call npm run dev -- --hostname 127.0.0.1 --port 3000
