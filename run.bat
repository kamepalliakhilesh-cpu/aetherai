@echo off
title AETHER.AI // Solaris Core
cd /d "%~dp0"
echo ═══════════════════════════════════════════
echo   AETHER.AI  //  SOLARIS CORE  //  BOOT
echo ═══════════════════════════════════════════
echo.
py src\app.py
if errorlevel 1 (
    echo.
    echo [ERROR] Aether.AI exited with an error.
    echo.
    pause
)
