@echo off
REM Phase 2 setup — works without PowerShell execution policy
cd /d "%~dp0.."
python sql\setup_phase2.py %*
if errorlevel 1 pause
