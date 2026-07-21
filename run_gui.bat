@echo off
REM Gelistirme modunda (derlemeden) GUI'yi baslatir: yerel sunucuyu ayaga
REM kaldirir ve tarayicida acar. Uretim icin build_exe.py ile .exe uretin.
cd /d "%~dp0"
python run_app.py
