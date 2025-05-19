#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MP3转文字工具 - PyQt5图形界面版本
"""

import os
import sys
import time
import threading
import logging
import json
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                            QLabel, QLineEdit, QPushButton, QComboBox, QCheckBox, 
                            QTextEdit, QFileDialog, QMessageBox, QProgressBar, QSplitter,
                            QGroupBox, QRadioButton, QTabWidget, QDialog, QFormLayout)
from PyQt5.QtCore import Qt, QObject, pyqtSignal, QMimeData, QUrl, QSettings
from PyQt5.QtGui import QDragEnterEvent, QDropEvent, QColor, QTextCursor, QIcon, QIntValidator
import mp3_to_text
from mp3_to_text import convert_mp3_to_wav, transcribe_audio, TaskController

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MP3ToText")

# 配置HTTP请求的日志
requests_log = logging.getLogger("urllib3")
requests_log.setLevel(logging.DEBUG)
requests_log.propagate = True

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')

# 默认配额设置（MB）
DEFAULT_QUOTA_LIMIT_MB = 1000

class WorkerSignals(QObject):
    """
    定义worker信号
    """
    finished = pyqtSignal(str)
    error = pyqtSignal(str)
    log = pyqtSignal(str, str)  # 日志信号，参数：日志级别，消息内容
    progress = pyqtSignal(int, int)  # 进度信号，参数：当前进度，总进度
    status_update = pyqtSignal(str)  # 状态更新信号

class FileDragDropLineEdit(QLineEdit):
    """
    支持拖放文件的LineEdit
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
    
    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
    
    def dropEvent(self, event: QDropEvent):
        urls = event.mimeData().urls()
        if urls and len(urls) > 0:
            file_path = urls[0].toLocalFile()
            if file_path.lower().endswith('.mp3'):
                self.setText(file_path)
            else:
                QMessageBox.warning(self, "警告", "请拖放MP3文件")

class APISettingsDialog(QDialog):
    """
    百度API设置对话框
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("百度语音识别API设置")
        self.setMinimumWidth(400)
        
        # 加载配置
        self.load_config()
        
        # 主布局
        layout = QVBoxLayout(self)
        
        # 表单布局
        form_layout = QFormLayout()
        
        # API设置字段
        self.app_id_edit = QLineEdit(self.config.get("app_id", ""))
        self.api_key_edit = QLineEdit(self.config.get("api_key", ""))
        self.secret_key_edit = QLineEdit(self.config.get("secret_key", ""))
        
        # 配额设置
        self.quota_limit_edit = QLineEdit(str(self.config.get("quota_limit_mb", DEFAULT_QUOTA_LIMIT_MB)))
        self.quota_limit_edit.setValidator(QIntValidator(1, 1000000))  # 限制输入为整数
        
        # 保持密钥安全
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.secret_key_edit.setEchoMode(QLineEdit.Password)
        
        # 显示/隐藏密钥
        self.show_keys_check = QCheckBox("显示密钥")
        self.show_keys_check.toggled.connect(self.toggle_key_visibility)
        
        # 添加到表单
        form_layout.addRow("APP ID:", self.app_id_edit)
        form_layout.addRow("API Key:", self.api_key_edit)
        form_layout.addRow("Secret Key:", self.secret_key_edit)
        form_layout.addRow("配额限制 (MB):", self.quota_limit_edit)
        form_layout.addRow("", self.show_keys_check)
        
        # 添加说明标签
        info_label = QLabel("请在百度AI开放平台创建应用并获取API密钥：\nhttps://ai.baidu.com/tech/speech")
        info_label.setStyleSheet("color: gray;")
        
        # 按钮
        button_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")
        
        self.save_button.clicked.connect(self.save_settings)
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.cancel_button)
        
        # 添加到主布局
        layout.addLayout(form_layout)
        layout.addWidget(info_label)
        layout.addLayout(button_layout)
    
    def load_config(self):
        """从配置文件加载设置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
            else:
                self.config = {}
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            self.config = {}
    
    def toggle_key_visibility(self, checked):
        """切换API密钥的可见性"""
        echo_mode = QLineEdit.Normal if checked else QLineEdit.Password
        self.api_key_edit.setEchoMode(echo_mode)
        self.secret_key_edit.setEchoMode(echo_mode)
    
    def save_settings(self):
        """保存API设置到配置文件"""
        # 准备配置数据
        try:
            quota_limit = int(self.quota_limit_edit.text())
        except ValueError:
            quota_limit = DEFAULT_QUOTA_LIMIT_MB
            
        config_data = {
            "app_id": self.app_id_edit.text(),
            "api_key": self.api_key_edit.text(),
            "secret_key": self.secret_key_edit.text(),
            "quota_limit_mb": quota_limit,
            "quota_used_mb": self.config.get("quota_used_mb", 0)  # 保留已使用的配额
        }
        
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(CONFIG_FILE), exist_ok=True)
            
            # 保存到配置文件
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=4)
            
            # 设置到模块
            mp3_to_text.BAIDU_APP_ID = config_data["app_id"]
            mp3_to_text.BAIDU_API_KEY = config_data["api_key"]
            mp3_to_text.BAIDU_SECRET_KEY = config_data["secret_key"]
            
            QMessageBox.information(self, "成功", f"百度API设置已保存到: {CONFIG_FILE}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存配置失败: {str(e)}")

class MP3ToTextGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("MP3转文字工具")
        self.setGeometry(100, 100, 800, 700)
        
        # 配置数据
        self.config = {}
        
        # 任务控制器
        self.task_controller = TaskController()
        self.conversion_thread = None
        self.is_converting = False
        self.is_paused = False
        
        # 初始化信号
        self.worker_signals = WorkerSignals()
        self.worker_signals.finished.connect(self.on_conversion_finished)
        self.worker_signals.error.connect(self.on_conversion_error)
        self.worker_signals.log.connect(self.on_log)
        self.worker_signals.progress.connect(self.on_progress)
        self.worker_signals.status_update.connect(self.on_status_update)
        
        # 主窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # 文件选择部分
        file_layout = QHBoxLayout()
        file_label = QLabel("MP3文件:")
        self.file_entry = FileDragDropLineEdit()
        self.file_entry.setPlaceholderText("选择MP3文件或拖放文件到这里")
        self.browse_button = QPushButton("浏览...")
        self.browse_button.clicked.connect(self.browse_file)
        
        file_layout.addWidget(file_label)
        file_layout.addWidget(self.file_entry)
        file_layout.addWidget(self.browse_button)
        main_layout.addLayout(file_layout)
        
        # 添加提示标签
        hint_label = QLabel("提示: 您可以直接拖放MP3文件到输入框")
        hint_label.setStyleSheet("color: gray; font-size: 12px;")
        main_layout.addWidget(hint_label)
        
        # 配额状态显示
        quota_layout = QHBoxLayout()
        quota_label = QLabel("剩余配额:")
        self.quota_display = QLabel("加载中...")
        self.quota_display.setStyleSheet("""
            background-color: #e8f5e9;
            padding: 5px 10px;
            border-radius: 4px;
            border: 1px solid #c8e6c9;
            font-weight: bold;
        """)
        
        quota_layout.addWidget(quota_label)
        quota_layout.addWidget(self.quota_display)
        quota_layout.addStretch()
        main_layout.addLayout(quota_layout)
        
        # API选择部分
        api_group = QGroupBox("语音识别API")
        api_layout = QVBoxLayout(api_group)
        
        api_selection = QHBoxLayout()
        self.baidu_api_radio = QRadioButton("百度语音识别API")
        self.google_api_radio = QRadioButton("Google语音识别API")
        self.baidu_api_radio.setChecked(True)  # 默认使用百度API
        
        api_selection.addWidget(self.baidu_api_radio)
        api_selection.addWidget(self.google_api_radio)
        api_selection.addStretch()
        
        # 百度API设置按钮
        baidu_settings = QHBoxLayout()
        self.baidu_settings_button = QPushButton("百度API设置")
        self.baidu_settings_button.clicked.connect(self.show_baidu_api_settings)
        self.baidu_settings_button.setVisible(False)
        baidu_settings.addWidget(self.baidu_settings_button)
        baidu_settings.addStretch()
        
        api_layout.addLayout(api_selection)
        api_layout.addLayout(baidu_settings)
        
        main_layout.addWidget(api_group)
        
        # 语言选择部分
        language_frame = QHBoxLayout()
        language_label = QLabel("语言:")
        self.language_combo = QComboBox()
        
        languages = [
            "中文 (zh-CN)",
            "英语 (en-US)",
            "日语 (ja)",
            "韩语 (ko)",
            "法语 (fr)",
            "德语 (de)",
            "俄语 (ru)"
        ]
        
        self.language_combo.addItems(languages)
        language_frame.addWidget(language_label)
        language_frame.addWidget(self.language_combo)
        language_frame.addStretch()
        main_layout.addLayout(language_frame)
        
        # 输出选项部分
        output_layout = QHBoxLayout()
        self.save_check = QCheckBox("保存到文件")
        self.verbose_check = QCheckBox("显示详细日志")
        self.http_debug_check = QCheckBox("显示HTTP请求日志")
        self.verbose_check.setChecked(True)
        self.http_debug_check.setChecked(True)
        output_layout.addWidget(self.save_check)
        output_layout.addWidget(self.verbose_check)
        output_layout.addWidget(self.http_debug_check)
        output_layout.addStretch()
        main_layout.addLayout(output_layout)
        
        # 转换按钮、暂停按钮、停止按钮和进度条
        button_layout = QHBoxLayout()
        
        # 转换按钮
        self.convert_button = QPushButton("开始转换")
        self.convert_button.clicked.connect(self.start_conversion)
        self.convert_button.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        
        # 尝试添加图标
        try:
            self.convert_button.setIcon(QIcon.fromTheme("media-playback-start"))
        except:
            pass  # 忽略图标加载错误
        
        # 暂停按钮
        self.pause_resume_button = QPushButton("暂停")
        self.pause_resume_button.clicked.connect(self.toggle_pause_resume)
        self.pause_resume_button.setEnabled(False)
        self.pause_resume_button.setStyleSheet("""
            QPushButton {
                background-color: #FFA000;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #FF8F00;
            }
        """)
        
        # 尝试添加图标
        try:
            self.pause_resume_button.setIcon(QIcon.fromTheme("media-playback-pause"))
        except:
            pass  # 忽略图标加载错误
        
        # 停止按钮
        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_conversion)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
        """)
        
        # 尝试添加图标
        try:
            self.stop_button.setIcon(QIcon.fromTheme("media-playback-stop"))
        except:
            pass  # 忽略图标加载错误
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setTextVisible(True)  # 显示百分比文本
        
        button_layout.addWidget(self.convert_button)
        button_layout.addWidget(self.pause_resume_button)
        button_layout.addWidget(self.stop_button)
        button_layout.addWidget(self.progress_bar)
        main_layout.addLayout(button_layout)
        
        # 状态栏
        self.status_label = QLabel("就绪")
        main_layout.addWidget(self.status_label)
        
        # 创建分割器，分隔结果区域和日志区域
        splitter = QSplitter(Qt.Vertical)
        splitter.setHandleWidth(10)
        main_layout.addWidget(splitter, 1)  # 使分割器可伸缩
        
        # 结果区域容器
        result_container = QWidget()
        result_layout = QVBoxLayout(result_container)
        result_layout.setContentsMargins(0, 0, 0, 0)
        
        # 日志区域容器
        log_container = QWidget()
        log_layout = QVBoxLayout(log_container)
        log_layout.setContentsMargins(0, 0, 0, 0)
        
        # 结果区域
        result_label = QLabel("转换结果:")
        result_layout.addWidget(result_label)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        result_layout.addWidget(self.result_text)
        
        # 日志区域
        log_header = QHBoxLayout()
        log_label = QLabel("处理日志:")
        self.clear_log_button = QPushButton("清除日志")
        self.clear_log_button.clicked.connect(self.clear_log)
        self.clear_log_button.setStyleSheet("""
            QPushButton {
                background-color: #F44336;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #E53935;
            }
        """)
        # 尝试添加图标
        try:
            self.clear_log_button.setIcon(QIcon.fromTheme("edit-clear"))
        except:
            pass  # 忽略图标加载错误
        log_header.addWidget(log_label)
        log_header.addStretch()
        log_header.addWidget(self.clear_log_button)
        log_layout.addLayout(log_header)
        
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        log_layout.addWidget(self.log_text)
        
        # 添加到分割器
        splitter.addWidget(result_container)
        splitter.addWidget(log_container)
        
        # 设置初始大小比例
        splitter.setSizes([300, 300])
        
        # 美化状态栏
        self.status_label.setStyleSheet("""
            background-color: #f5f5f5;
            padding: 5px;
            border-radius: 4px;
            border: 1px solid #ddd;
            font-weight: bold;
        """)
        
        # 设置样式
        self.setStyleSheet("""
            QLabel {
                font-size: 14px;
            }
            QLineEdit, QTextEdit {
                border: 1px solid #ddd;
                padding: 5px;
                border-radius: 4px;
            }
            QSplitter::handle {
                background-color: #f0f0f0;
            }
            QSplitter::handle:hover {
                background-color: #ccc;
            }
            QProgressBar {
                border: 1px solid #ddd;
                border-radius: 4px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #888888;
            }
        """)
        
        # 加载百度API设置 - 移动到UI组件初始化之后
        self.load_baidu_api_settings()
        
        # 更新配额显示
        self.update_quota_display()
        
        # 添加欢迎信息
        self.add_log("info", "欢迎使用MP3转文字工具！")
        self.add_log("info", "请选择一个MP3文件进行转换")
        self.add_log("info", f"当前系统时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        # 检查百度API配置
        if not mp3_to_text.BAIDU_APP_ID or not mp3_to_text.BAIDU_API_KEY or not mp3_to_text.BAIDU_SECRET_KEY:
            self.add_log("warning", "百度API未配置，请点击百度API设置按钮进行配置")
    
    def load_baidu_api_settings(self):
        """从配置文件加载百度API设置"""
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    self.config = json.load(f)
                
                mp3_to_text.BAIDU_APP_ID = self.config.get("app_id", "")
                mp3_to_text.BAIDU_API_KEY = self.config.get("api_key", "")
                mp3_to_text.BAIDU_SECRET_KEY = self.config.get("secret_key", "")
                
                if all([mp3_to_text.BAIDU_APP_ID, mp3_to_text.BAIDU_API_KEY, mp3_to_text.BAIDU_SECRET_KEY]):
                    self.add_log("info", "已从配置文件加载百度API设置")
                else:
                    self.add_log("warning", "配置文件中的百度API设置不完整")
                    
                # 确保配额字段存在
                if "quota_limit_mb" not in self.config:
                    self.config["quota_limit_mb"] = DEFAULT_QUOTA_LIMIT_MB
                if "quota_used_mb" not in self.config:
                    self.config["quota_used_mb"] = 0
            else:
                self.add_log("info", "未找到配置文件，将使用默认设置")
                self.config = {
                    "app_id": "",
                    "api_key": "",
                    "secret_key": "",
                    "quota_limit_mb": DEFAULT_QUOTA_LIMIT_MB,
                    "quota_used_mb": 0
                }
        except Exception as e:
            self.add_log("error", f"加载配置文件失败: {str(e)}")
            self.config = {
                "quota_limit_mb": DEFAULT_QUOTA_LIMIT_MB,
                "quota_used_mb": 0
            }
    
    def update_quota_display(self):
        """更新配额显示"""
        limit_mb = self.config.get("quota_limit_mb", DEFAULT_QUOTA_LIMIT_MB)
        used_mb = self.config.get("quota_used_mb", 0)
        remaining_mb = max(0, limit_mb - used_mb)
        
        # 设置样式
        if remaining_mb < limit_mb * 0.1:  # 小于10%显示红色
            color_style = "background-color: #ffebee; border: 1px solid #ffcdd2;"
        elif remaining_mb < limit_mb * 0.3:  # 小于30%显示黄色
            color_style = "background-color: #fff8e1; border: 1px solid #ffecb3;"
        else:  # 正常显示绿色
            color_style = "background-color: #e8f5e9; border: 1px solid #c8e6c9;"
        
        self.quota_display.setText(f"{remaining_mb:.2f} MB / {limit_mb} MB")
        self.quota_display.setStyleSheet(f"""
            {color_style}
            padding: 5px 10px;
            border-radius: 4px;
            font-weight: bold;
        """)
        
        # 如果配额用尽，禁用转换按钮
        if hasattr(self, 'convert_button'):
            self.convert_button.setEnabled(remaining_mb > 0)
            if remaining_mb <= 0:
                self.add_log("warning", "配额已用尽，请联系管理员增加配额")
    
    def show_baidu_api_settings(self):
        """显示百度API设置对话框"""
        dialog = APISettingsDialog(self)
        dialog.exec_()
        
        # 在对话框关闭后检查设置
        if mp3_to_text.BAIDU_APP_ID and mp3_to_text.BAIDU_API_KEY and mp3_to_text.BAIDU_SECRET_KEY:
            self.add_log("success", "百度API配置已更新")
        else:
            self.add_log("warning", "百度API配置不完整，使用百度API可能会失败")
    
    def browse_file(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog  # 使用Qt自己的对话框而不是系统原生对话框
        
        # 获取用户主目录作为起始目录
        home_dir = os.path.expanduser("~")
        
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择MP3文件", 
            home_dir,  # 起始目录
            "MP3文件 (*.mp3);;所有文件 (*)",
            options=options
        )
        
        if file_path:
            self.file_entry.setText(file_path)
            self.add_log("info", f"已选择文件: {file_path}")
            # 验证文件是否存在
            if not os.path.exists(file_path):
                QMessageBox.warning(self, "警告", f"文件 {file_path} 不存在")
                self.add_log("error", f"文件 {file_path} 不存在")
            else:
                # 获取文件大小
                file_size = os.path.getsize(file_path)
                self.add_log("info", f"文件大小: {self.format_size(file_size)}")
    
    def format_size(self, size_bytes):
        """格式化文件大小显示"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.2f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.2f} TB"
    
    def clear_log(self):
        """清除日志区域"""
        self.log_text.clear()
        self.add_log("info", "日志已清除")
    
    def add_log(self, level, message):
        """将日志添加到日志区域"""
        if not self.verbose_check.isChecked() and level == "debug":
            return
            
        # 如果是HTTP请求日志但用户选择不显示，则跳过
        if "Starting new HTTP" in message or "https://" in message:
            if not self.http_debug_check.isChecked():
                return
            
        timestamp = datetime.now().strftime("%H:%M:%S")
        color = {
            "debug": "gray",
            "info": "black",
            "warning": "orange",
            "error": "red",
            "success": "green"
        }.get(level, "black")
        
        # 为不同级别的日志设置图标
        icon = {
            "debug": "🔍",
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
            "success": "✅"
        }.get(level, "")
        
        formatted_log = f"<span style='color:{color};'>[{timestamp}] {icon} {message}</span>"
        self.log_text.moveCursor(QTextCursor.End)
        self.log_text.insertHtml(formatted_log + "<br>")
        self.log_text.moveCursor(QTextCursor.End)
        
        # 同时记录到系统日志
        if level == "debug":
            logger.debug(message)
        elif level == "info" or level == "success":
            logger.info(message)
        elif level == "warning":
            logger.warning(message)
        elif level == "error":
            logger.error(message)
    
    def on_log(self, level, message):
        """从工作线程接收日志并添加到日志区域"""
        self.add_log(level, message)
    
    def start_conversion(self):
        mp3_file = self.file_entry.text().strip()
        
        if not mp3_file:
            QMessageBox.critical(self, "错误", "请选择MP3文件")
            self.add_log("error", "未选择MP3文件")
            return
        
        if not os.path.exists(mp3_file):
            QMessageBox.critical(self, "错误", f"文件 {mp3_file} 不存在")
            self.add_log("error", f"文件 {mp3_file} 不存在")
            return
        
        # 检查文件大小和配额
        file_size_mb = os.path.getsize(mp3_file) / (1024 * 1024)
        remaining_quota = self.config.get("quota_limit_mb", DEFAULT_QUOTA_LIMIT_MB) - self.config.get("quota_used_mb", 0)
        
        if file_size_mb > remaining_quota:
            QMessageBox.critical(self, "配额不足", 
                             f"文件大小 ({file_size_mb:.2f} MB) 超过剩余配额 ({remaining_quota:.2f} MB)。\n请使用较小的文件或联系管理员增加配额。")
            self.add_log("error", f"配额不足，文件大小: {file_size_mb:.2f} MB，剩余配额: {remaining_quota:.2f} MB")
            return
        
        # 检查百度API设置（如果使用百度API）
        use_baidu = self.baidu_api_radio.isChecked()
        if use_baidu and (not mp3_to_text.BAIDU_APP_ID or not mp3_to_text.BAIDU_API_KEY or not mp3_to_text.BAIDU_SECRET_KEY):
            reply = QMessageBox.question(
                self, 
                "API未配置", 
                "您选择了百度API但尚未配置密钥。是否立即配置？", 
                QMessageBox.Yes | QMessageBox.No, 
                QMessageBox.Yes
            )
            if reply == QMessageBox.Yes:
                self.show_baidu_api_settings()
                return
            self.add_log("warning", "使用未配置的百度API继续操作")
        
        if not mp3_file.lower().endswith('.mp3'):
            self.add_log("warning", "选择的文件可能不是MP3格式")
            QMessageBox.warning(self, "警告", "选择的文件可能不是MP3格式")
            reply = QMessageBox.question(self, "确认", "选择的文件可能不是MP3格式，是否继续？", 
                                        QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            if reply == QMessageBox.No:
                self.add_log("info", "用户取消了转换")
                return
            self.add_log("info", "用户确认继续转换非MP3文件")
        
        # 获取语言代码
        language_selection = self.language_combo.currentText()
        language_code = language_selection.split('(')[1].split(')')[0]
        self.add_log("info", f"转换语言: {language_selection}")
        
        # 记录使用的API
        api_type = "百度" if use_baidu else "Google"
        self.add_log("info", f"使用{api_type}语音识别API")
        
        # 重置任务控制器
        self.task_controller.reset()
        
        # 初始化按钮状态
        self.worker_signals.status_update.emit("开始处理")
        
        # 初始化进度条
        if self.progress_bar.value() != 0:
            self.progress_bar.setValue(0)
        
        # 检查文件大小，预测是否需要分段处理
        file_size = os.path.getsize(mp3_file)
        if file_size > 10 * 1024 * 1024 and use_baidu:
            # 大文件会分段处理，设置进度条为等待模式
            self.add_log("info", "检测到大文件，将使用分段处理")
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(0)
        else:
            # 小文件不会分段，设置进度条为不确定模式
            self.progress_bar.setRange(0, 0)  # 不确定模式
        
        self.add_log("info", "开始转换流程")
        
        # 清空结果区域，显示正在处理的消息
        self.result_text.setText("正在处理中，请稍候...\n\n1. 转换MP3为WAV格式\n2. 识别语音内容\n3. 生成文本结果")
        
        # 记录文件大小用于后续扣款
        self.current_file_size_mb = file_size_mb
        
        # 在新线程中运行转换过程
        self.add_log("info", "启动转换线程")
        self.conversion_thread = threading.Thread(
            target=self.run_conversion,
            args=(mp3_file, language_code, use_baidu),
            daemon=True
        )
        self.conversion_thread.start()
    
    def on_progress(self, current, total):
        """更新进度条和进度信息"""
        # 确保在UI线程中更新
        from PyQt5.QtCore import QMetaObject, Qt, Q_ARG
        
        # 计算百分比
        if total > 0:
            percent = int((current / total) * 100)
            # 更新进度条范围和值
            self.progress_bar.setRange(0, 100)
            self.progress_bar.setValue(percent)
            
            # 记录进度日志
            if current == 0:
                self.add_log("info", f"开始分段处理：共{total}段")
            elif current < total:
                self.add_log("info", f"正在处理第{current+1}/{total}段 ({percent}%)")
            else:
                self.add_log("success", f"所有{total}段处理完成 (100%)")
    
    def run_conversion(self, mp3_file, language_code, use_baidu):
        try:
            self.worker_signals.log.emit("info", f"开始处理文件: {os.path.basename(mp3_file)}")
            
            # 记录开始时间
            start_time = time.time()
            self.worker_signals.log.emit("debug", "记录转换开始时间")
            
            # 转换为WAV格式
            self.worker_signals.log.emit("info", "步骤1: 将MP3转换为WAV格式")
            self.worker_signals.log.emit("debug", f"源文件: {mp3_file}")
            
            # 获取MP3文件时长
            try:
                import mutagen
                audio = mutagen.File(mp3_file)
                if audio:
                    duration = audio.info.length
                    self.worker_signals.log.emit("info", f"音频时长: {int(duration//60)}分{int(duration%60)}秒")
            except Exception as e:
                self.worker_signals.log.emit("debug", f"获取音频时长失败: {str(e)}")
            
            # 检查是否请求停止
            if self.task_controller.is_stop_requested():
                self.worker_signals.log.emit("info", "在WAV转换前检测到停止请求")
                self.worker_signals.status_update.emit("已停止")
                return
                
            # 检查是否暂停
            self.task_controller.wait_if_paused()
            if self.task_controller.is_stop_requested():
                self.worker_signals.log.emit("info", "在WAV转换前暂停后检测到停止请求")
                self.worker_signals.status_update.emit("已停止")
                return
            
            self.worker_signals.log.emit("debug", "开始调用convert_mp3_to_wav函数")
            temp_wav = convert_mp3_to_wav(mp3_file)
            self.worker_signals.log.emit("success", "WAV转换完成")
            self.worker_signals.log.emit("debug", f"临时WAV文件: {temp_wav}")
            
            try:
                # 检查是否请求停止
                if self.task_controller.is_stop_requested():
                    self.worker_signals.log.emit("info", "在语音识别前检测到停止请求")
                    self.worker_signals.status_update.emit("已停止")
                    return
                    
                # 检查是否暂停
                self.task_controller.wait_if_paused()
                if self.task_controller.is_stop_requested():
                    self.worker_signals.log.emit("info", "在语音识别前暂停后检测到停止请求")
                    self.worker_signals.status_update.emit("已停止")
                    return
                
                # 转换为文字
                self.worker_signals.log.emit("info", "步骤2: 开始语音识别")
                self.worker_signals.log.emit("info", f"使用语言: {language_code}")
                
                api_name = "百度API" if use_baidu else "Google API"
                self.worker_signals.log.emit("debug", f"调用{api_name}识别服务")
                
                # 进度回调函数
                def progress_callback(current, total):
                    self.worker_signals.progress.emit(current, total)
                
                # 使用选择的API进行识别
                text = transcribe_audio(temp_wav, language_code, use_baidu, progress_callback, self.task_controller)
                
                # 检查是否被用户停止
                if text == "处理已被用户停止":
                    self.worker_signals.log.emit("info", "处理已被用户停止")
                    self.worker_signals.status_update.emit("已停止")
                    return
                
                # 记录识别到的文本信息
                if text:
                    word_count = len(text.split())
                    self.worker_signals.log.emit("success", "语音识别成功")
                    self.worker_signals.log.emit("info", f"识别到约 {word_count} 个单词")
                else:
                    self.worker_signals.log.emit("warning", "识别成功，但未检测到文本内容")
                
                # 计算处理时间
                elapsed_time = time.time() - start_time
                self.worker_signals.log.emit("info", f"总处理时间: {elapsed_time:.2f} 秒")
                
                # 如果需要保存到文件
                if self.save_check.isChecked():
                    self.worker_signals.log.emit("info", "用户选择保存到文件")
                
                # 发送完成信号
                self.worker_signals.log.emit("success", "转换流程完成")
                self.worker_signals.status_update.emit("已完成")
                self.worker_signals.finished.emit(text)
            
            finally:
                # 删除临时文件
                if os.path.exists(temp_wav):
                    self.worker_signals.log.emit("debug", f"删除临时WAV文件: {temp_wav}")
                    os.remove(temp_wav)
                    self.worker_signals.log.emit("debug", "临时文件清理完成")
        
        except Exception as e:
            # 发送错误信号
            self.worker_signals.log.emit("error", f"转换过程出错: {str(e)}")
            self.worker_signals.status_update.emit("已停止")
            self.worker_signals.error.emit(str(e))
    
    def on_conversion_finished(self, text):
        # 扣除配额
        if hasattr(self, 'current_file_size_mb'):
            self.config["quota_used_mb"] = self.config.get("quota_used_mb", 0) + self.current_file_size_mb
            
            # 保存配置
            try:
                with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                    json.dump(self.config, f, indent=4)
                
                # 更新配额显示
                self.update_quota_display()
                self.add_log("info", f"已扣除 {self.current_file_size_mb:.2f} MB 配额")
            except Exception as e:
                self.add_log("error", f"更新配额失败: {str(e)}")
        
        # 显示结果
        self.result_text.setText(text)
        self.add_log("success", "处理完成，结果已显示")
        
        # 显示成功消息
        if not self.task_controller.is_stop_requested():  # 只有在非停止状态下才显示
            QMessageBox.information(self, "转换完成", "语音识别已完成，结果已显示在文本区域。")
        
        # 如果需要保存到文件
        if self.save_check.isChecked():
            self.add_log("info", "准备保存结果到文件")
            options = QFileDialog.Options()
            options |= QFileDialog.DontUseNativeDialog
            
            file_path, _ = QFileDialog.getSaveFileName(
                self, 
                "保存文本文件", 
                os.path.expanduser("~/转换结果.txt"),  # 默认保存位置和文件名
                "文本文件 (*.txt);;所有文件 (*)",
                options=options
            )
            
            if file_path:
                try:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(text)
                    self.add_log("success", f"文件已保存: {file_path}")
                    QMessageBox.information(self, "成功", f"文字已保存到: {file_path}")
                except Exception as e:
                    self.add_log("error", f"保存文件时出错: {str(e)}")
                    QMessageBox.critical(self, "错误", f"保存文件失败: {str(e)}")
            else:
                self.add_log("info", "用户取消了文件保存")
        
        # 恢复按钮状态，设置进度条为完成状态
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(100)
        self.add_log("info", "界面恢复正常状态")
    
    def on_conversion_error(self, error_message):
        # 显示错误
        QMessageBox.critical(self, "错误", f"转换失败: {error_message}")
        self.result_text.setText(f"转换失败: {error_message}")
        self.add_log("error", f"转换失败: {error_message}")
        
        # 恢复按钮状态，停止进度条
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.add_log("info", "界面恢复正常状态")

    def on_status_update(self, status):
        """
        处理状态更新
        """
        self.add_log("info", f"处理状态: {status}")
        
        if status == "已完成" or status == "已停止":
            # 重置按钮状态
            self.convert_button.setEnabled(True)
            self.pause_resume_button.setEnabled(False)
            self.stop_button.setEnabled(False)
            self.is_converting = False
            self.is_paused = False
            
            # 重置任务控制器
            self.task_controller.reset()
            
            if status == "已完成":
                self.status_label.setText("转换完成")
            else:
                self.status_label.setText("已停止")
                
        elif status == "开始处理":
            # 设置按钮状态
            self.convert_button.setEnabled(False)
            self.pause_resume_button.setEnabled(True)
            self.stop_button.setEnabled(True)
            self.is_converting = True
            self.is_paused = False
            self.status_label.setText("正在处理...")

    def toggle_pause_resume(self):
        """
        切换暂停/恢复状态
        """
        if not self.is_converting:
            return
            
        if self.is_paused:
            # 当前是暂停状态，恢复处理
            self.task_controller.resume()
            self.is_paused = False
            self.pause_resume_button.setText("暂停")
            self.pause_resume_button.setStyleSheet("""
                QPushButton {
                    background-color: #FFA000;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #FF8F00;
                }
            """)
            self.add_log("info", "转换任务已恢复")
            self.status_label.setText("正在处理...")
            self.worker_signals.status_update.emit("已恢复")
        else:
            # 当前是运行状态，暂停处理
            self.task_controller.pause()
            self.is_paused = True
            self.pause_resume_button.setText("恢复")
            self.pause_resume_button.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    padding: 8px 16px;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background-color: #45a049;
                }
            """)
            self.add_log("info", "转换任务已暂停")
            self.status_label.setText("已暂停")
            self.worker_signals.status_update.emit("已暂停")

    def stop_conversion(self):
        """
        停止转换过程
        """
        if not self.is_converting:
            return
            
        # 请求停止任务
        self.task_controller.stop()
        self.add_log("info", "已请求停止任务，正在终止处理...")
        self.status_label.setText("正在停止...")
        self.worker_signals.status_update.emit("正在停止")
        
        # 在GUI中反映状态变化
        self.pause_resume_button.setEnabled(False)
        # 停止按钮保持启用状态，直到处理实际终止

def main():
    # 设置高DPI支持
    if hasattr(Qt, 'AA_EnableHighDpiScaling'):
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    if hasattr(Qt, 'AA_UseHighDpiPixmaps'):
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        
    app = QApplication(sys.argv)
    window = MP3ToTextGUI()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main() 