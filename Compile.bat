@echo off
setlocal enabledelayedexpansion

REM ===================================================================
REM ========================= SETUP & PATHS ===========================
REM ===================================================================

REM Get the directory of this script
set "SCRIPT_DIR=%~dp0"
set "SCRIPT_DIR=%SCRIPT_DIR:~0,-1%"

REM Define App Details
set "APP_NAME=Pulsar"
set "MAIN_SCRIPT=Pulsar.py"
set "ICON_FILE=%SCRIPT_DIR%\Icons\Pulsar_Icon.ico"
set "OUTPUT_DIR=%SCRIPT_DIR%"
set "LOG_DIR=%SCRIPT_DIR%\Log"
set "REQUIREMENTS_FILE=%SCRIPT_DIR%\requirements.txt"

REM ===================================================================
REM ====================== DATA & ASSETS CONFIG =======================
REM ===================================================================

REM Initialize Data variable
set "EXTRA_DATA="

REM 1. Add Icons Folder (Contains Pulsar_Icon.ico, Logos, PNGs)
set "EXTRA_DATA=%EXTRA_DATA% --add-data "%SCRIPT_DIR%\Icons;Icons""

REM 2. Add Fonts Folder (Contains BeVietnamPro .ttf files)
REM    Crucial because your script uses ctk.FontManager.load_font
set "EXTRA_DATA=%EXTRA_DATA% --add-data "%SCRIPT_DIR%\Fonts;Fonts""

REM 3. Optional: Add License if it exists
if exist "%SCRIPT_DIR%\LICENSE.txt" (
    set "EXTRA_DATA=%EXTRA_DATA% --add-data "%SCRIPT_DIR%\LICENSE.txt;.""
)

REM ===================================================================
REM ==================== HIDDEN IMPORTS CONFIG ========================
REM ===================================================================

REM Initialize Hidden Imports variable
set "HIDDEN_IMPORTS="

REM --- UI & Graphics ---
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=customtkinter"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=tkinter"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=PIL"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=PIL.ImageTk"

REM --- Data Science & Plotting ---
REM Matplotlib often needs explicit backend imports
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=matplotlib"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=matplotlib.backends.backend_tkagg"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=pandas"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=numpy"

REM --- Export Engines (For your export_data function) ---
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=openpyxl"
set "HIDDEN_IMPORTS=!HIDDEN_IMPORTS! --hidden-import=odf"

REM ===================================================================
REM ====================== DEPENDENCY CHECKS ==========================
REM ===================================================================

echo.
echo ==========================================
echo      PULSAR BUILDER - INITIALIZING
echo ==========================================
echo.

REM 1. Check/Install PyInstaller
echo Checking PyInstaller...
py -m pip show pyinstaller >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing PyInstaller...
    py -m pip install pyinstaller
)

REM 2. Check Requirements File
if not exist "%REQUIREMENTS_FILE%" (
    echo.
    echo ▩▩▩ ERROR: requirements.txt not found! ▩▩▩
    echo Please create "%REQUIREMENTS_FILE%" with the following content:
    echo.
    echo customtkinter
    echo pandas
    echo numpy
    echo matplotlib
    echo Pillow
    echo openpyxl
    echo odfpy
    echo.
    pause
    goto :eof
)

REM 3. Install Dependencies
echo Installing dependencies from requirements.txt...
py -m pip install -r "%REQUIREMENTS_FILE%"
if %errorlevel% neq 0 (
    echo ▩▩▩ ERROR: Failed to install dependencies. Check output above. ▩▩▩
    pause
    goto :eof
)

REM ===================================================================
REM ====================== CLEANUP & PREP =============================
REM ===================================================================

echo.
echo Setting up output directories...
if not exist "%LOG_DIR%" mkdir "%LOG_DIR%"

echo Cleaning old build artifacts...
if exist "%LOG_DIR%\build" rmdir /s /q "%LOG_DIR%\build"
del /q "%LOG_DIR%\*.spec" 2>nul

REM ===================================================================
REM ====================== BUILD EXECUTION ============================
REM ===================================================================

echo.
echo ==========================================
echo        STARTING COMPILATION
echo ==========================================
echo Target: %MAIN_SCRIPT%
echo Output: %APP_NAME%.exe
echo.

py -m PyInstaller --noconfirm --onefile --windowed ^
    --name "%APP_NAME%" ^
    --icon "%ICON_FILE%" ^
    --clean ^
    !HIDDEN_IMPORTS! ^
    !EXTRA_DATA! ^
    --distpath "%OUTPUT_DIR%" ^
    --workpath "%LOG_DIR%\build" ^
    --specpath "%LOG_DIR%" ^
    "%SCRIPT_DIR%\%MAIN_SCRIPT%"

if %errorlevel% neq 0 (
    echo.
    echo ▩▩▩ ERROR: Build Failed! ▩▩▩
    echo Check the logs in the window above for details.
    pause
    goto :eof
)

REM ===================================================================
REM ========================== FINISHED ===============================
REM ===================================================================

echo.
echo ==========================================
echo      BUILD SUCCESSFUL!
echo ==========================================
echo.
echo Your app is ready: %OUTPUT_DIR%\%APP_NAME%.exe
echo Temporary files moved to: %LOG_DIR%
echo.
pause