#!/bin/bash

# Color support
INFO="\033[1;32m[INFO]\033[0m"
LOG="\033[1;36m[LOG]\033[0m"
ERROR="\033[1;31m[ERROR]\033[0m"
WARNING="\033[1;33m[WARNING]\033[0m"
SUCCESS="\033[1;32m[SUCCESS]\033[0m"
TIP="\033[1;33m[TIP]\033[0m"

echo "MP3 to Text Tool - Environment Setup"
echo "==================================="

# Check if Python is installed
echo -e "$LOG Checking Python installation..."
if ! command -v python3 &> /dev/null; then
    echo -e "$INFO Python3 not found, trying to install automatically..."
    
    # Detect OS type
    OS="$(uname)"
    
    if [ "$OS" == "Darwin" ]; then
        # macOS
        if ! command -v brew &> /dev/null; then
            echo -e "$INFO Homebrew not detected, installing Homebrew first..."
            /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
            
            if ! command -v brew &> /dev/null; then
                echo -e "$ERROR Homebrew installation failed, please install Python 3 manually"
                echo -e "$TIP Download from https://www.python.org/downloads/"
                exit 1
            fi
        fi
        
        echo -e "$INFO Installing Python 3 using Homebrew..."
        brew install python3 || { echo -e "$ERROR Python3 installation failed"; exit 1; }
    elif [ "$OS" == "Linux" ]; then
        # Check Linux distribution
        if command -v apt-get &> /dev/null; then
            # Debian/Ubuntu
            echo -e "$INFO Detected Debian/Ubuntu system, installing Python 3 with apt..."
            sudo apt-get update || { echo -e "$ERROR apt-get update failed"; exit 1; }
            sudo apt-get install -y python3 python3-pip || { echo -e "$ERROR Python3 installation failed"; exit 1; }
        elif command -v dnf &> /dev/null; then
            # Fedora/CentOS/RHEL
            echo -e "$INFO Detected Fedora/CentOS/RHEL system, installing Python 3 with dnf..."
            sudo dnf install -y python3 python3-pip || { echo -e "$ERROR Python3 installation failed"; exit 1; }
        elif command -v pacman &> /dev/null; then
            # Arch Linux
            echo -e "$INFO Detected Arch Linux system, installing Python 3 with pacman..."
            sudo pacman -Sy --noconfirm python python-pip || { echo -e "$ERROR Python3 installation failed"; exit 1; }
        else
            echo -e "$ERROR Could not determine Linux distribution, please install Python 3 manually"
            echo -e "$TIP Download from https://www.python.org/downloads/"
            exit 1
        fi
    else
        echo -e "$ERROR Unsupported operating system, please install Python 3 manually"
        echo -e "$TIP Download from https://www.python.org/downloads/"
        exit 1
    fi
    
    # Check if Python was installed successfully
    if ! command -v python3 &> /dev/null; then
        echo -e "$ERROR Python 3 installation failed, please install manually"
        exit 1
    fi
    
    echo -e "$SUCCESS Python 3 installed successfully!"
fi

# Display Python version
PYTHON_VERSION=$(python3 --version 2>&1)
echo -e "$INFO Found Python: $PYTHON_VERSION"
echo ""

# Check system type
OS="$(uname)"

# Install portaudio on macOS
if [ "$OS" == "Darwin" ]; then
    echo -e "$LOG Detected macOS, checking for portaudio..."
    if ! command -v brew &> /dev/null; then
        echo -e "$INFO Homebrew not found, installing Homebrew..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        
        if ! command -v brew &> /dev/null; then
            echo -e "$ERROR Homebrew installation failed, please install manually"
            exit 1
        fi
    fi
    
    if ! brew list portaudio &> /dev/null; then
        echo -e "$INFO Installing portaudio..."
        brew install portaudio || { echo -e "$ERROR portaudio installation failed"; exit 1; }
    else
        echo -e "$INFO portaudio already installed"
    fi
    
    # Install ffmpeg on macOS
    if ! brew list ffmpeg &> /dev/null; then
        echo -e "$INFO Installing ffmpeg..."
        brew install ffmpeg || { echo -e "$WARNING ffmpeg installation failed, some features may not work"; }
    else
        echo -e "$INFO ffmpeg already installed"
    fi
fi

# Install necessary dependencies on Linux
if [ "$OS" == "Linux" ]; then
    echo -e "$LOG Detected Linux, installing necessary dependencies..."
    
    # Check distribution type
    if command -v apt-get &> /dev/null; then
        echo -e "$INFO Installing dependencies for Debian/Ubuntu..."
        sudo apt-get update || { echo -e "$WARNING apt-get update failed, trying to continue..."; }
        sudo apt-get install -y python3-dev portaudio19-dev ffmpeg || { 
            echo -e "$WARNING Some dependencies failed to install, trying individually..."
            sudo apt-get install -y python3-dev || echo -e "$WARNING python3-dev installation failed"
            sudo apt-get install -y portaudio19-dev || echo -e "$WARNING portaudio19-dev installation failed"
            sudo apt-get install -y ffmpeg || echo -e "$WARNING ffmpeg installation failed"
        }
    elif command -v dnf &> /dev/null; then
        echo -e "$INFO Installing dependencies for Fedora/RHEL/CentOS..."
        sudo dnf install -y python3-devel portaudio-devel ffmpeg || {
            echo -e "$WARNING Some dependencies failed to install, trying individually..."
            sudo dnf install -y python3-devel || echo -e "$WARNING python3-devel installation failed"
            sudo dnf install -y portaudio-devel || echo -e "$WARNING portaudio-devel installation failed"
            sudo dnf install -y ffmpeg || echo -e "$WARNING ffmpeg installation failed"
        }
    elif command -v pacman &> /dev/null; then
        echo -e "$INFO Installing dependencies for Arch Linux..."
        sudo pacman -Sy --noconfirm portaudio ffmpeg || {
            echo -e "$WARNING Some dependencies failed to install, trying individually..."
            sudo pacman -Sy --noconfirm portaudio || echo -e "$WARNING portaudio installation failed"
            sudo pacman -Sy --noconfirm ffmpeg || echo -e "$WARNING ffmpeg installation failed"
        }
    else
        echo -e "$WARNING Unrecognized Linux distribution, please install portaudio and ffmpeg manually"
    fi
fi

# Install required packages
echo -e "$LOG ==== Starting Python Dependency Installation ===="
echo -e "$INFO Installing required packages..."

echo -e "$LOG 1/7 Installing SpeechRecognition..."
pip3 install SpeechRecognition==3.10.0 || { echo -e "$WARNING SpeechRecognition installation failed"; }

echo -e "$LOG 2/7 Installing pydub..."
pip3 install pydub==0.25.1 || { echo -e "$WARNING pydub installation failed"; }

echo -e "$LOG 3/7 Installing PyQt5..."
pip3 install PyQt5==5.15.11 || { echo -e "$WARNING PyQt5 installation failed"; }

echo -e "$LOG 4/7 Installing mutagen..."
pip3 install mutagen>=1.45.1 || { echo -e "$WARNING mutagen installation failed"; }

echo -e "$LOG 5/7 Installing baidu-aip..."
pip3 install baidu-aip>=4.16.0 || { echo -e "$WARNING baidu-aip installation failed"; }

echo -e "$LOG 6/7 Installing chardet..."
pip3 install chardet>=4.0.0 || { echo -e "$WARNING chardet installation failed"; }

# Install PyAudio
echo -e "$LOG 7/7 Installing PyAudio..."
pip3 install PyAudio==0.2.13
if [ $? -ne 0 ]; then
    echo -e "$INFO PyAudio direct installation failed, trying to compile from source..."
    pip3 install --global-option="build_ext" --global-option="-I/usr/local/include" --global-option="-L/usr/local/lib" PyAudio
    if [ $? -ne 0 ]; then
        echo -e "$WARNING PyAudio installation failed, may need manual installation"
    else
        echo -e "$SUCCESS PyAudio successfully installed (via source compile)"
    fi
else
    echo -e "$SUCCESS PyAudio successfully installed"
fi

echo ""
echo "==================================="
echo -e "$SUCCESS Installation complete!"
echo "==================================="
echo ""
echo "Usage:"
echo "1. GUI Mode: python3 mp3_to_text_gui.py"
echo "2. Command Line: python3 mp3_to_text.py audio_file.mp3"
echo ""

# Add execute permissions
chmod +x mp3_to_text.py
chmod +x mp3_to_text_gui.py

echo -e "$TIP Execute permissions added, scripts can be run directly" 