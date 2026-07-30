@echo off
rem ---------------------------------------------------------------
rem  Perekryvayushchiesya dominoshki - zapusk okna bez konsoli.
rem  Dvoynoy klik po etomu faylu otkryvaet graficheskiy interfeys.
rem
rem  pythonw.exe - eto tot zhe Python, no bez chernogo okna konsoli.
rem  %~dp0 - papka, v kotoroy lezhit etot fayl, poetomu programma
rem  zapuskaetsya pravilno iz lyubogo mesta.
rem ---------------------------------------------------------------

where pythonw >nul 2>&1
if %errorlevel%==0 (
    start "" pythonw "%~dp0main.py" --gui
) else (
    start "" py -w "%~dp0main.py" --gui
)
