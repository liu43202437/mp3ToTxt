# MP3转文字工具

这是一个简单的Python工具，可以将MP3音频文件转换为文本。

## 功能特点

- 支持MP3音频文件转文字
- 支持多种语言（默认中文）
- 可以将结果输出到文件或直接显示在控制台
- 提供命令行和图形界面两种使用方式

## 安装依赖

### 自动安装（推荐）

安装脚本会自动检测并安装所有必要的依赖。提供中英文两个版本的安装脚本。

#### Windows 用户
```bash
# 英文版
install.bat

# 中文版
install_cn.bat
```

#### Linux/macOS 用户
```bash
# 英文版
chmod +x install.sh
./install.sh

# 中文版
chmod +x install_cn.sh
./install_cn.sh
```

### 手动安装

如果您已经安装了Python，可以手动安装依赖：

```bash
pip install -r requirements.txt  # Windows
pip3 install -r requirements.txt  # Linux/macOS
```

注意：在macOS上安装PyAudio可能需要先安装portaudio：

```bash
brew install portaudio
pip3 install PyAudio
```

在Windows上可能需要从非官方源下载PyAudio的预编译二进制文件：

```bash
pip install pipwin
pipwin install pyaudio
```

## 使用方法

### 命令行方式

基本用法：

```bash
python mp3_to_text.py 你的音频文件.mp3  # Windows
python3 mp3_to_text.py 你的音频文件.mp3  # Linux/macOS
```

指定输出文件：

```bash
python mp3_to_text.py 你的音频文件.mp3 -o 输出文件.txt
```

指定语言（默认为中文zh-CN）：

```bash
python mp3_to_text.py 你的音频文件.mp3 -l en-US  # 英语
```

### 图形界面方式

运行以下命令启动图形界面：

```bash
python mp3_to_text_gui.py  # Windows
python3 mp3_to_text_gui.py  # Linux/macOS
```

在图形界面中：
1. 点击"浏览..."按钮选择MP3文件
2. 从下拉菜单中选择语言
3. 如需保存到文件，勾选"保存到文件"选项
4. 点击"开始转换"按钮
5. 转换结果将显示在文本框中

## 常见语言代码

- 中文：zh-CN
- 英语：en-US
- 日语：ja
- 韩语：ko
- 法语：fr
- 德语：de
- 俄语：ru

## 注意事项

1. 该工具使用Google的语音识别服务，需要连接互联网
2. 对于较长的音频文件，可能需要等待较长时间
3. 识别准确率受音频质量、背景噪音等因素影响 