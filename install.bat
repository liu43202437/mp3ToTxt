@echo off
:: Set code page to UTF-8
chcp 65001 > nul
:: Enable color support
setlocal EnableDelayedExpansion

set "INFO=[92m[INFO][0m"
set "LOG=[96m[LOG][0m"
set "ERROR=[91m[ERROR][0m"
set "TIP=[93m[TIP][0m"
set "SUCCESS=[92m[SUCCESS][0m"

echo MP3 to Text Tool - Environment Setup
echo ====================================

REM Check if Python is installed
echo %LOG% Checking Python installation...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %INFO% Python not found in PATH, will download and install Python...
    goto InstallPython
)

REM Verify Python works correctly
echo %LOG% Testing Python execution...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo %INFO% Python command failed, will reinstall Python...
    goto InstallPython
)

echo %SUCCESS% Python found and working properly. Installing dependencies...
python --version
echo.
goto InstallDependencies

:InstallPython
    echo %LOG% ==== Starting Python Installation ====
    echo %LOG% Preparing for download...
    
    REM Create temporary directory
    echo %LOG% Creating temp directory...
    mkdir temp 2> nul
    if %errorlevel% neq 0 (
        echo %LOG% Temp directory exists or cannot be created, continuing...
    )
    cd temp
    echo %LOG% Current directory: %cd%
    
    REM Download Python installer
    echo %LOG% Starting Python 3.10.11 download (about 30MB)...
    echo %LOG% Source: Huawei Cloud Mirror (Faster in Asia)
    echo %LOG% Using download with progress...
    
    REM Use PowerShell script for better download experience
    powershell -ExecutionPolicy Bypass -Command "& {$url = 'https://mirrors.huaweicloud.com/python/3.10.11/python-3.10.11-amd64.exe'; $output = 'python-installer.exe'; Write-Output '[Info] Downloading Python installer...'; $start_time = Get-Date; $wc = New-Object System.Net.WebClient; try { $wc.DownloadFile($url, $output); $end_time = Get-Date; $time_taken = ($end_time - $start_time).TotalSeconds; $fileSize = [Math]::Round((Get-Item $output).Length / 1MB, 2); Write-Output \"[Info] Download complete! File size: ${fileSize} MB, Time: ${time_taken} seconds\"; exit 0 } catch { Write-Output \"[Error] Download failed: $($_.Exception.Message)\"; try { Write-Output '[Info] Trying alternative source...'; $url = 'https://www.python.org/ftp/python/3.10.11/python-3.10.11-amd64.exe'; $wc.DownloadFile($url, $output); Write-Output '[Info] Alternative download succeeded'; exit 0 } catch { Write-Output \"[Error] All download attempts failed\"; exit 1 }}}"
    
    echo %LOG% Download process exited with code: %errorlevel%
    
    if not exist python-installer.exe (
        echo %ERROR% Failed to download Python installer! Please check your network
        echo %TIP% Please manually install Python 3.6+ from:
        echo       https://www.python.org/downloads/
        cd ..
        pause
        exit /b 1
    )
    
    REM Install Python
    echo %LOG% Starting Python installer...
    echo %LOG% Install options: Silent, AllUsers, PrependPath, no test packages
    echo %LOG% Installation may take a few minutes, please wait...
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    echo %LOG% Python installer exited with code: %errorlevel%
    
    REM Delete installer
    echo %LOG% Cleaning temporary files...
    del python-installer.exe
    cd ..
    rmdir /s /q temp
    
    REM Refresh environment variables
    echo %LOG% Refreshing environment variables...
    echo %LOG% You may need to restart this terminal or reboot your computer
    setx PATH "%PATH%" >nul 2>&1
    
    echo %SUCCESS% Python installation completed. Please close this window and run the script again to install dependencies
    echo %TIP% If Python is still not recognized after restart, try rebooting your computer
    pause
    exit /b 0

:InstallDependencies
echo %LOG% ==== Starting Dependencies Installation ====
REM Install dependencies
echo %INFO% Installing required packages...

echo %LOG% 1/7 Installing SpeechRecognition...
python -m pip install SpeechRecognition==3.10.0

echo %LOG% 2/7 Installing pydub...
python -m pip install pydub==0.25.1

echo %LOG% 3/7 Installing PyQt5...
python -m pip install PyQt5==5.15.11

echo %LOG% 4/7 Installing mutagen...
python -m pip install mutagen>=1.45.1

echo %LOG% 5/7 Installing baidu-aip...
python -m pip install baidu-aip>=4.16.0

echo %LOG% 6/7 Installing chardet...
python -m pip install chardet>=4.0.0

REM Install PyAudio (which often causes problems)
echo %LOG% 7/7 Installing PyAudio...
python -m pip install PyAudio==0.2.13
if %errorlevel% neq 0 (
    echo %INFO% PyAudio direct install failed, trying alternative method...
    echo %LOG% Installing pipwin helper...
    python -m pip install pipwin
    echo %LOG% Installing pyaudio via pipwin...
    python -m pipwin install pyaudio
)

echo.
echo ====================================
echo %SUCCESS% Installation complete!
echo ====================================
echo.
echo Usage:
echo 1. GUI Mode: python mp3_to_text_gui.py
echo 2. Command Line: python mp3_to_text.py audio_file.mp3
echo.
pause