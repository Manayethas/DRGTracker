@echo off

:: Check if winget is available for installing Python
echo Checking if winget (Windows Package Manager) is available...

winget --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo winget is not available. Please install winget or ensure Windows is up to date.
    exit /b 1
)

:: Install Python using winget if not installed
echo Checking if Python 3 is installed...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Installing Python 3...
    winget install --id=Python.Python.3 --source winget --silent
)

:: Disable App Execution Aliases only if the paths exist
echo Disabling App Execution Aliases for Python...
powershell -Command "if (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ApplicationExecutionAlias\AliasMapping\python.exe') { Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ApplicationExecutionAlias\AliasMapping\python.exe' -Name 'Target' -Value '' }"
powershell -Command "if (Test-Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ApplicationExecutionAlias\AliasMapping\python3.exe') { Set-ItemProperty -Path 'HKCU:\Software\Microsoft\Windows\CurrentVersion\ApplicationExecutionAlias\AliasMapping\python3.exe' -Name 'Target' -Value '' }"

:: Ensure Python is in the PATH
echo Adding Python to PATH...
setx PATH "%PATH%;C:\Users\%USERNAME%\AppData\Local\Programs\Python\Python39\"

:: Verify Python installation
python --version
if %ERRORLEVEL% neq 0 (
    echo Python installation failed. Please check the installation manually.
    exit /b 1
)

:: Check if Git is installed
echo Checking if Git is installed...
git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Git is not installed. Installing Git...
    winget install --id=Git.Git -e --source winget
)

:: Check if SQLite is installed
echo Checking if SQLite is installed...
sqlite3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo SQLite is not installed. Installing SQLite...
    powershell -Command "Invoke-WebRequest https://sqlite.org/2024/sqlite-tools-win32-x86-3410000.zip -OutFile sqlite.zip"
    powershell -Command "Expand-Archive sqlite.zip -DestinationPath ."
    set "sqlite_path=%cd%\sqlite-tools-win32-x86-3410000"
    setx PATH "%PATH%;%sqlite_path%"
    set PATH=%PATH%;%sqlite_path%
) else (
    echo SQLite is already installed.
)

:: Clone the program from GitHub
echo Cloning program from GitHub...
if exist "DRGTracker" (
    echo Directory 'DRGTracker' already exists. Pulling latest changes...
    cd DRGTracker
    git pull
) else (
    git clone https://github.com/Manayethas/DRGTracker.git
    cd DRGTracker
)

:: Create virtual environment (optional)
echo Creating virtual environment...
python -m venv venv
call venv\Scripts\activate

:: Install dependencies
echo Installing dependencies...
pip install -r requirements.txt

:: Inform the user about activating the virtual environment
echo Setup complete! To activate the virtual environment, use:
echo venv\Scripts\activate
