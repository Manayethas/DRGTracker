@echo off

:: Check if Python, pip, git, and SQLite are installed
echo Checking if Python 3, pip, git, and SQLite are installed...

python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Please install Python 3 and try again.
    exit /b 1
)

git --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Git is not installed. Please install Git and try again.
    exit /b 1
)

sqlite3 --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo SQLite is not installed. Installing SQLite...
    powershell -Command "Invoke-WebRequest https://sqlite.org/2024/sqlite-tools-win32-x86-3410000.zip -OutFile sqlite.zip"
    powershell -Command "Expand-Archive sqlite.zip -DestinationPath ."
    set PATH=%cd%\sqlite-tools-win32-x86-3410000;%PATH%
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
