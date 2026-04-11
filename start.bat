@echo off
title BRIAS Opstarter
color 0A
setlocal EnableDelayedExpansion

echo.
echo  ╔══════════════════════════════════════╗
echo  ║           BRIAS — opstarten           ║
echo  ╚══════════════════════════════════════╝
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: CONFIGURATIE — pas aan als jouw paden afwijken
:: ─────────────────────────────────────────────────────────────────────────────

:: BRIAS map (automatisch: de map waar dit script staat)
set "BRIAS_DIR=%~dp0"
if "!BRIAS_DIR:~-1!"=="\" set "BRIAS_DIR=!BRIAS_DIR:~0,-1!"

:: Llama-server executable
set "LLAMA_EXE=C:\Users\baile\AppData\Local\Microsoft\WinGet\Packages\ggml.llamacpp_Microsoft.Winget.Source_8wekyb3d8bbwe\llama-server.exe"

:: Model (pas pad aan als je model ergens anders staat)
set "MODEL=E:\BRIAS\Mistral-7B-Instruct-v0.3-Q6_K.gguf"

:: Cloudflare Tunnel naam (zoals geconfigureerd in cloudflared)
set "TUNNEL_NAME=brias"

:: cloudflared.exe — automatisch zoeken op bekende plekken
set "CLOUDFLARED="
if exist "!BRIAS_DIR!\cloudflared.exe"                              set "CLOUDFLARED=!BRIAS_DIR!\cloudflared.exe"
if "!CLOUDFLARED!"=="" if exist "C:\Program Files (x86)\cloudflared\cloudflared.exe" set "CLOUDFLARED=C:\Program Files (x86)\cloudflared\cloudflared.exe"
if "!CLOUDFLARED!"=="" if exist "C:\cloudflared.exe"                set "CLOUDFLARED=C:\cloudflared.exe"
if "!CLOUDFLARED!"=="" if exist "C:\BRIAS\cloudflared.exe"          set "CLOUDFLARED=C:\BRIAS\cloudflared.exe"

:: ─────────────────────────────────────────────────────────────────────────────
:: OPSTARTEN
:: ─────────────────────────────────────────────────────────────────────────────

echo [1/3] Llama-server starten op poort 8080...
call :fn_start_llama

echo     Wachten op llama-server...
call :fn_wait_llama
echo.
echo       Llama-server OK.
echo.

echo [2/3] BRIAS brein starten op poort 8000...
call :fn_start_fastapi

echo     Wachten op FastAPI...
call :fn_wait_fastapi
echo.
echo       FastAPI OK.
echo.

echo [3/3] Cloudflare Tunnel...
call :fn_start_tunnel
echo.

echo  ══════════════════════════════════════════
echo  Alles draait.
echo    Llama-server  ^>  http://127.0.0.1:8080
echo    BRIAS API     ^>  http://127.0.0.1:8000
if not "!CLOUDFLARED!"=="" (
    echo    Tunnel        ^>  actief ^(wordt bewaakt^)
) else (
    echo    Tunnel        ^>  NIET gestart ^(cloudflared.exe niet gevonden^)
)
echo.
echo  Watchdog controleert alle processen elke 30 seconden.
echo  Sluit dit venster NIET — dan stopt alles.
echo  ══════════════════════════════════════════
echo.

:: ─────────────────────────────────────────────────────────────────────────────
:: WATCHDOG — herstart processen automatisch als ze crashen
:: ─────────────────────────────────────────────────────────────────────────────
:watchdog
timeout /t 30 /nobreak >nul

:: Check llama-server via health endpoint
curl -s --max-time 4 -o nul -w "%%{http_code}" http://127.0.0.1:8080/health 2>nul | findstr /r "^200$" >nul
if errorlevel 1 (
    echo [%TIME%] Llama-server offline — herstart...
    call :fn_start_llama
    :: Geef extra tijd om model te laden
    timeout /t 25 /nobreak >nul
)

:: Check FastAPI via health endpoint
curl -s --max-time 4 -o nul -w "%%{http_code}" http://127.0.0.1:8000/health 2>nul | findstr /r "^200$" >nul
if errorlevel 1 (
    echo [%TIME%] FastAPI offline — herstart...
    call :fn_start_fastapi
    timeout /t 12 /nobreak >nul
)

:: Check cloudflared: eerst process, dan echte tunnelverbinding
if not "!CLOUDFLARED!"=="" (
    tasklist /fi "imagename eq cloudflared.exe" 2>nul | find /i "cloudflared.exe" >nul
    if errorlevel 1 (
        echo [%TIME%] Cloudflare tunnel gestopt — herstart...
        call :fn_start_tunnel
        timeout /t 8 /nobreak >nul
    ) else (
        :: Proces draait — maar is de tunnel-verbinding ook echt actief?
        :: cloudflared geeft /ready = 200 als de tunnel verbonden is, 503 als niet
        curl -s --max-time 4 -o nul -w "%%{http_code}" http://localhost:2000/ready 2>nul | findstr /r "^200$" >nul
        if errorlevel 1 (
            echo [%TIME%] Tunnel verbinding verbroken ^(proces leeft maar verbinding is weg^) — herstart...
            taskkill /f /im cloudflared.exe >nul 2>&1
            timeout /t 2 /nobreak >nul
            call :fn_start_tunnel
        )
    )
)

goto watchdog

:: ─────────────────────────────────────────────────────────────────────────────
:: FUNCTIES (nooit direct uitvoeren — altijd via call :fn_...)
:: ─────────────────────────────────────────────────────────────────────────────

:fn_start_llama
start "BRIAS — llama-server" "!LLAMA_EXE!" ^
    --model "!MODEL!" ^
    --port 8080 ^
    --ctx-size 4096 ^
    --host 127.0.0.1
exit /b

:fn_wait_llama
:_wll
timeout /t 2 /nobreak >nul
curl -s --max-time 3 -o nul -w "%%{http_code}" http://127.0.0.1:8080/health 2>nul | findstr /r "^200$" >nul
if errorlevel 1 ( <nul set /p "=." & goto _wll )
exit /b

:fn_start_fastapi
start "BRIAS — brein (FastAPI)" cmd /k "cd /d "!BRIAS_DIR!" && python -m uvicorn server.main:app --host 0.0.0.0 --port 8000"
exit /b

:fn_wait_fastapi
:_wfa
timeout /t 3 /nobreak >nul
curl -s --max-time 3 -o nul -w "%%{http_code}" http://127.0.0.1:8000/health 2>nul | findstr /r "^200$" >nul
if errorlevel 1 ( <nul set /p "=." & goto _wfa )
exit /b

:fn_start_tunnel
if "!CLOUDFLARED!"=="" (
    echo    [!] cloudflared.exe niet gevonden.
    echo        Zet cloudflared.exe in !BRIAS_DIR! om de tunnel automatisch te bewaken.
    exit /b
)
start "BRIAS — tunnel" "!CLOUDFLARED!" tunnel run !TUNNEL_NAME!
exit /b
