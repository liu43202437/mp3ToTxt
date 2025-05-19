#!/bin/bash

# 颜色支持
INFO="\033[1;32m[信息]\033[0m"
LOG="\033[1;36m[日志]\033[0m"
ERROR="\033[1;31m[错误]\033[0m"
WARNING="\033[1;33m[警告]\033[0m"
SUCCESS="\033[1;32m[成功]\033[0m"
TIP="\033[1;33m[提示]\033[0m"

echo "MP3转文字工具 - 环境安装程序"
echo "============================"

# 检查Python是否已安装
echo -e "$LOG 检查Python是否已安装..."
if ! command -v python3 &> /dev/null; then
    echo -e "$INFO 未找到Python3，将尝试自动安装..."
    
    # 检测操作系统类型
    OS="$(uname)"
    
    if [ "$OS" == "Darwin" ]; then
        # macOS
        if ! command -v brew &> /dev/null; then
            echo -e "$INFO 未检测到Homebrew，将先安装Homebrew..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            
            if ! command -v brew &> /dev/null; then
                echo -e "$ERROR Homebrew安装失败，请手动安装Python 3"
                echo -e "$TIP 可访问 https://www.python.org/downloads/ 下载"
                exit 1
            fi
        fi
        
        echo -e "$INFO 正在使用Homebrew安装Python 3..."
        brew install python3
    elif [ "$OS" == "Linux" ]; then
        # 检查Linux发行版
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            echo -e "$INFO 检测到Debian/Ubuntu系统，使用apt安装Python 3..."
            sudo apt-get update || { echo -e "$ERROR apt-get更新失败"; exit 1; }
            sudo apt-get install -y python3 python3-pip || { echo -e "$ERROR Python3安装失败"; exit 1; }
        elif command -v dnf &> /dev/null; then
            # Fedora/CentOS/RHEL
            echo -e "$INFO 检测到Fedora/CentOS/RHEL系统，使用dnf安装Python 3..."
            sudo dnf install -y python3 python3-pip || { echo -e "$ERROR Python3安装失败"; exit 1; }
        elif command -v pacman &> /dev/null; then
            # Arch Linux
            echo -e "$INFO 检测到Arch Linux系统，使用pacman安装Python 3..."
            sudo pacman -Sy --noconfirm python python-pip || { echo -e "$ERROR Python3安装失败"; exit 1; }
        else
            echo -e "$ERROR 无法确定Linux发行版，请手动安装Python 3"
            echo -e "$TIP 可访问 https://www.python.org/downloads/ 下载"
            exit 1
        fi
    else
        echo -e "$ERROR 不支持的操作系统，请手动安装Python 3"
        echo -e "$TIP 可访问 https://www.python.org/downloads/ 下载"
        exit 1
    fi
    
    # 检查Python是否成功安装
    if ! command -v python3 &> /dev/null; then
        echo -e "$ERROR Python 3安装失败，请手动安装"
        exit 1
    fi
    
    echo -e "$SUCCESS Python 3安装成功！"
fi

# 显示Python版本
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "$INFO 已找到Python: $PYTHON_VERSION"
echo ""

# 检查系统类型
OS="$(uname)"

# 在macOS上安装portaudio
if [ "$OS" == "Darwin" ]; then
    echo -e "$LOG 检测到macOS系统，正在检查portaudio..."
    if ! command -v brew &> /dev/null; then
        echo -e "$INFO 未找到Homebrew，正在安装Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        if ! command -v brew &> /dev/null; then
            echo -e "$ERROR Homebrew安装失败，请手动安装"
            exit 1
        fi
    fi
    
    if ! brew list portaudio &> /dev/null; then
        echo -e "$INFO 正在安装portaudio..."
        brew install portaudio || { echo -e "$ERROR portaudio安装失败"; exit 1; }
    else
        echo -e "$INFO portaudio已安装"
    fi
    
    # macOS上安装ffmpeg
    if ! brew list ffmpeg &> /dev/null; then
        echo -e "$INFO 正在安装ffmpeg..."
        brew install ffmpeg || { echo -e "$WARNING ffmpeg安装失败，可能影响某些功能"; }
    else
        echo -e "$INFO ffmpeg已安装"
    fi
fi

# 在Linux上安装必要的依赖
if [ "$OS" == "Linux" ]; then
    echo -e "$LOG 检测到Linux系统，正在安装必要的依赖..."
    
    # 检查发行版类型
    if command -v apt-get &> /dev/null; then
        echo -e "$INFO 正在为Debian/Ubuntu安装依赖..."
        sudo apt-get update || { echo -e "$WARNING apt-get更新失败，尝试继续..."; }
        sudo apt-get install -y python3-dev portaudio19-dev ffmpeg || { 
            echo -e "$WARNING 部分依赖安装失败，尝试分别安装..."
            sudo apt-get install -y python3-dev || echo -e "$WARNING python3-dev安装失败"
            sudo apt-get install -y portaudio19-dev || echo -e "$WARNING portaudio19-dev安装失败"
            sudo apt-get install -y ffmpeg || echo -e "$WARNING ffmpeg安装失败"
        }
    elif command -v dnf &> /dev/null; then
        echo -e "$INFO 正在为Fedora/RHEL/CentOS安装依赖..."
        sudo dnf install -y python3-devel portaudio-devel ffmpeg || {
            echo -e "$WARNING 部分依赖安装失败，尝试分别安装..."
            sudo dnf install -y python3-devel || echo -e "$WARNING python3-devel安装失败"
            sudo dnf install -y portaudio-devel || echo -e "$WARNING portaudio-devel安装失败"
            sudo dnf install -y ffmpeg || echo -e "$WARNING ffmpeg安装失败"
        }
    elif command -v pacman &> /dev/null; then
        echo -e "$INFO 正在为Arch Linux安装依赖..."
        sudo pacman -Sy --noconfirm portaudio ffmpeg || {
            echo -e "$WARNING 部分依赖安装失败，尝试分别安装..."
            sudo pacman -Sy --noconfirm portaudio || echo -e "$WARNING portaudio安装失败"
            sudo pacman -Sy --noconfirm ffmpeg || echo -e "$WARNING ffmpeg安装失败"
        }
    else
        echo -e "$WARNING 未能识别的Linux发行版，请手动安装portaudio和ffmpeg依赖"
    fi
fi

# 安装依赖包
echo -e "$LOG ==== 开始安装Python依赖 ===="
echo -e "$INFO 正在安装必要的包..."

echo -e "$LOG 1/7 正在安装 SpeechRecognition..."
pip3 install SpeechRecognition==3.10.0 || { echo -e "$WARNING SpeechRecognition安装失败"; }

echo -e "$LOG 2/7 正在安装 pydub..."
pip3 install pydub==0.25.1 || { echo -e "$WARNING pydub安装失败"; }

echo -e "$LOG 3/7 正在安装 PyQt5..."
pip3 install PyQt5==5.15.11 || { echo -e "$WARNING PyQt5安装失败"; }

echo -e "$LOG 4/7 正在安装 mutagen..."
pip3 install mutagen>=1.45.1 || { echo -e "$WARNING mutagen安装失败"; }

echo -e "$LOG 5/7 正在安装 baidu-aip..."
pip3 install baidu-aip>=4.16.0 || { echo -e "$WARNING baidu-aip安装失败"; }

echo -e "$LOG 6/7 正在安装 chardet..."
pip3 install chardet>=4.0.0 || { echo -e "$WARNING chardet安装失败"; }

# 安装PyAudio
echo -e "$LOG 7/7 正在安装 PyAudio..."
pip3 install PyAudio==0.2.13
if [ $? -ne 0 ]; then
    echo -e "$INFO PyAudio直接安装失败，正在尝试从源码编译..."
    pip3 install --global-option="build_ext" --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" PyAudio
    if [ $? -ne 0 ]; then
        echo -e "$WARNING PyAudio安装失败，可能需要手动安装"
    else
        echo -e "$SUCCESS PyAudio安装成功（通过源码编译）"
    fi
else
    echo -e "$SUCCESS PyAudio安装成功"
fi

echo ""
echo "============================"
echo -e "$SUCCESS 安装完成！"
echo "============================"
echo ""
echo "使用方法："
echo "1. 图形界面模式: python3 mp3_to_text_gui.py"
echo "2. 命令行模式: python3 mp3_to_text.py 音频文件.mp3"
echo ""

# 添加执行权限
chmod +x mp3_to_text.py
chmod +x mp3_to_text_gui.py

echo -e "$TIP 已添加执行权限，可以直接运行脚本文件" 