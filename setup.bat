@echo off

:: Check if Python is installed
echo Checking if Python 3 and pip are installed...
python --version >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Python is not installed. Please install Python 3 and try again.
    exit /b 1
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
