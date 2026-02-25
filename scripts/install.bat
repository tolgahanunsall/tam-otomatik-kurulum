@echo off
REM ============================================================
REM Note Backup Tool - Windows Kurulum Scripti
REM ============================================================

echo ========================================
echo   Note Backup Tool - Kurulum
echo ========================================
echo.

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%.."

REM Check Python
echo Python kontrol ediliyor...
python --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] Python bulunamadi! Python 3.8+ yukleyin.
    echo https://www.python.org/downloads/
    pause
    exit /b 1
)
for /f "tokens=*" %%i in ('python --version 2^>^&1') do echo [OK] %%i

REM Check pip
echo pip kontrol ediliyor...
python -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [HATA] pip bulunamadi!
    pause
    exit /b 1
)
echo [OK] pip mevcut

REM Create virtual environment
echo.
echo Sanal ortam olusturuluyor...
set "VENV_DIR=%PROJECT_DIR%\venv"
if exist "%VENV_DIR%\" (
    echo [INFO] Sanal ortam zaten mevcut, atlaniyor...
) else (
    python -m venv "%VENV_DIR%"
    echo [OK] Sanal ortam olusturuldu
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Install dependencies
echo.
echo Bagimliliklar yukleniyor...
pip install -r "%PROJECT_DIR%\requirements.txt" --quiet
echo [OK] Bagimliliklar yuklendi

REM Copy example config if no config exists
if not exist "%PROJECT_DIR%\config.yaml" (
    echo.
    echo Ornek yapilandirma dosyasi kopyalaniyor...
    copy "%PROJECT_DIR%\config.example.yaml" "%PROJECT_DIR%\config.yaml" >nul
    echo [OK] config.yaml olusturuldu
    echo [ONEMLI] Lutfen config.yaml dosyasini duzenleyin!
)

echo.
echo ========================================
echo   Kurulum Tamamlandi!
echo ========================================
echo.
echo Sonraki adimlar:
echo   1. config.yaml dosyasini duzenleyin:
echo      notepad "%PROJECT_DIR%\config.yaml"
echo.
echo   2. Test yedeklemesi yapin:
echo      cd "%PROJECT_DIR%"
echo      venv\Scripts\activate
echo      python backup.py
echo.
echo   3. Otomatik zamanlama kurun:
echo      python backup.py schedule install
echo.
pause
