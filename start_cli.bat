@echo off
rem ---------------------------------------------------------------
rem  Perekryvayushchiesya dominoshki - konsolnaya versiya.
rem  Dvoynoy klik po etomu faylu otkryvaet programmu v konsoli.
rem
rem  Okno ne zakroetsya srazu: posle otveta programma zhdet Enter.
rem  chcp 65001 vklyuchaet UTF-8, chtoby kirillica ne prevrashchalas
rem  v krakozyabry.
rem ---------------------------------------------------------------

chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if %errorlevel%==0 (
    python "%~dp0main.py"
) else (
    py "%~dp0main.py"
)
