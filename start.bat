@echo off
title BRIAS Opstarter
color 0A

echo.
echo  ╔══════════════════════════════════════╗
echo  ║           BRIAS — opstarten           ║
echo  ╚══════════════════════════════════════╝
echo.

:: ── 1. Llama-server starten in eigen venster ──────────────────────────────
echo [1/3] Llama-server starten op port 8080...

set LLAMA_EXE=C:\Users\baile\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe
set MODEL=E:\BRIAS\Mistral-7B-Instruct-v0.3-Q6_K.gguf

start "BRIAS — llama-server" "%LLAMA_EXE%" ^
    --model "%MODEL%" ^
    --port 8080 ^
    --ctx-size 4096 ^
    --host 127.0.0.1

:: ── 2. Wachten tot llama-server klaar is ──────────────────────────────────
echo [2/3] Wachten tot llama-server klaar is...

:wait_loop
timeout /t 2 /nobreak >nul
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:8080/health 2>nul | findstr /r "^200$" >nul
if errorlevel 1 (
    <nul set /p "=."
    goto wait_loop
)

echo.
echo        Llama-server draait.

:: ── 3. FastAPI server starten in eigen venster ────────────────────────────
echo [3/3] BRIAS brein starten...

start "BRIAS — brein (FastAPI)" cmd /k "cd /d E:\BRIAS\brain && python -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload"

echo.
echo  Alles draait.
echo    Llama-server  →  http://127.0.0.1:8080
echo    BRIAS API     →  http://127.0.0.1:8000
echo    Docs          →  http://127.0.0.1:8000/docs
echo.
pause
