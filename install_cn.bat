@echo off
chcp 65001 > nul
:: 设置颜色支持
setlocal EnableDelayedExpansion

set "INFO=[92m[信息][0m"
set "LOG=[96m[日志][0m"
set "ERROR=[91m[错误][0m"
set "TIP=[93m[提示][0m"
set "SUCCESS=[92m[成功][0m"

echo MP3转文字工具 - 环境安装程序
echo ====================================

REM 检查Python是否已安装
echo %LOG% 检查Python安装状态...
where python >nul 2>nul
if %errorlevel% neq 0 (
    echo %INFO% 未找到Python在系统路径中，将自动下载安装Python...
    goto InstallPython
)

REM 额外验证Python是否可用
echo %LOG% 测试Python执行...
python --version >nul 2>nul
if %errorlevel% neq 0 (
    echo %INFO% Python命令无法执行，将重新安装Python...
    goto InstallPython
)

echo %SUCCESS% Python已找到并可正常使用。正在安装依赖...
python --version
echo.
goto InstallDependencies

:InstallPython
    echo %LOG% ==== 开始Python安装流程 ====
    echo %LOG% 准备下载Python安装程序...
    
    REM 创建临时目录
    echo %LOG% 创建临时目录...
    mkdir temp 2> nul
    if %errorlevel% neq 0 (
        echo %LOG% 临时目录已存在或创建时出错，尝试继续...
    )
    cd temp
    echo %LOG% 当前工作目录: %cd%
    
    REM 下载Python安装程序
    echo %LOG% 开始下载Python 3.10.11安装程序(约30MB)...
    echo %LOG% 源: 华为云镜像
    echo %LOG% 使用下载进度显示...
    
    REM 使用PowerShell脚本下载并显示进度
    powershell -ExecutionPolicy Bypass -File "%~dp0download.ps1"
    
    echo %LOG% 下载进程已退出，退出代码: %errorlevel%
    
    if not exist python-installer.exe (
        echo %ERROR% 下载Python安装程序失败！请检查网络
        echo %TIP% 请手动安装Python 3.6+，从以下地址下载:
        echo       https://www.python.org/downloads/
        cd ..
        pause
        exit /b 1
    )
    
    REM 安装Python
    echo %LOG% 启动Python安装程序...
    echo %LOG% 安装选项: 静默安装，所有用户，添加到PATH，不包含测试包
    echo %LOG% 安装过程可能需要几分钟，请耐心等待...
    start /wait python-installer.exe /quiet InstallAllUsers=1 PrependPath=1 Include_test=0
    echo %LOG% Python安装程序已退出，退出代码: %errorlevel%
    
    REM 删除安装程序
    echo %LOG% 清理临时文件...
    del python-installer.exe
    cd ..
    rmdir /s /q temp
    
    REM 刷新环境变量
    echo %LOG% 刷新环境变量...
    echo %LOG% 如果安装后无法识别Python命令，可能需要重启终端或计算机
    setx PATH "%PATH%" >nul 2>&1
    
    echo %SUCCESS% Python安装过程已完成，请关闭此窗口并重新运行安装脚本以继续安装依赖
    echo %TIP% 如果重启后Python仍然无法识别，请尝试重启计算机后再试
    pause
    exit /b 0

:InstallDependencies
echo %LOG% ==== 开始依赖安装流程 ====
REM 安装依赖
echo %INFO% 正在安装必要的包...

echo %LOG% 1/7 安装 SpeechRecognition 包...
python -m pip install SpeechRecognition==3.10.0

echo %LOG% 2/7 安装 pydub 包...
python -m pip install pydub==0.25.1

echo %LOG% 3/7 安装 PyQt5 包...
python -m pip install PyQt5==5.15.11

echo %LOG% 4/7 安装 mutagen 包...
python -m pip install mutagen>=1.45.1

echo %LOG% 5/7 安装 baidu-aip 包...
python -m pip install baidu-aip>=4.16.0

echo %LOG% 6/7 安装 chardet 包...
python -m pip install chardet>=4.0.0

REM 安装PyAudio（通常会导致问题）
echo %LOG% 7/7 安装 PyAudio 包(这可能需要一些时间)...
python -m pip install PyAudio==0.2.13
if %errorlevel% neq 0 (
    echo %INFO% PyAudio直接安装失败，正在尝试替代方法...
    echo %LOG% 安装 pipwin 辅助工具...
    python -m pip install pipwin
    echo %LOG% 通过 pipwin 安装 pyaudio...
    python -m pipwin install pyaudio
)

echo.
echo ====================================
echo %SUCCESS% 安装完成！
echo ====================================
echo.
echo 使用方法:
echo 1. 图形界面模式: python mp3_to_text_gui.py
echo 2. 命令行模式: python mp3_to_text.py 音频文件.mp3
echo.
pause 