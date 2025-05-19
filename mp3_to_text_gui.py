#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MP3转文字工具 - 图形界面版本
"""

import os
import sys
import threading
import tkinter as tk
from tkinter import filedialog, ttk, scrolledtext, messagebox
from mp3_to_text import convert_mp3_to_wav, transcribe_audio

class MP3ToTextGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("MP3转文字工具")
        self.root.geometry("600x500")
        self.root.resizable(True, True)
        
        # 设置样式
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6, relief="flat", background="#4CAF50")
        self.style.configure("TLabel", padding=6, font=('Arial', 12))
        self.style.configure("TFrame", padding=10)
        
        self.create_widgets()
        
    def create_widgets(self):
        # 主框架
        main_frame = ttk.Frame(self.root, style="TFrame")
        main_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # 文件选择部分
        file_frame = ttk.Frame(main_frame)
        file_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(file_frame, text="MP3文件:").pack(side=tk.LEFT)
        
        self.file_path = tk.StringVar()
        self.file_entry = ttk.Entry(file_frame, textvariable=self.file_path, width=50)
        self.file_entry.pack(side=tk.LEFT, padx=5, fill=tk.X, expand=True)
        
        self.browse_button = ttk.Button(file_frame, text="浏览...", command=self.browse_file)
        self.browse_button.pack(side=tk.RIGHT)
        
        # 语言选择部分
        language_frame = ttk.Frame(main_frame)
        language_frame.pack(fill=tk.X, pady=10)
        
        ttk.Label(language_frame, text="语言:").pack(side=tk.LEFT)
        
        self.language_var = tk.StringVar(value="zh-CN")
        languages = [
            ("中文", "zh-CN"),
            ("英语", "en-US"),
            ("日语", "ja"),
            ("韩语", "ko"),
            ("法语", "fr"),
            ("德语", "de"),
            ("俄语", "ru")
        ]
        
        self.language_combo = ttk.Combobox(language_frame, textvariable=self.language_var, width=20)
        self.language_combo['values'] = [f"{name} ({code})" for name, code in languages]
        self.language_combo.current(0)
        self.language_combo.pack(side=tk.LEFT, padx=5)
        
        # 输出选项部分
        output_frame = ttk.Frame(main_frame)
        output_frame.pack(fill=tk.X, pady=10)
        
        self.save_var = tk.BooleanVar(value=False)
        self.save_check = ttk.Checkbutton(output_frame, text="保存到文件", variable=self.save_var)
        self.save_check.pack(side=tk.LEFT)
        
        # 转换按钮
        button_frame = ttk.Frame(main_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        self.convert_button = ttk.Button(button_frame, text="开始转换", command=self.start_conversion)
        self.convert_button.pack(side=tk.LEFT, padx=5)
        
        # 进度条
        self.progress = ttk.Progressbar(button_frame, orient=tk.HORIZONTAL, length=200, mode='indeterminate')
        self.progress.pack(side=tk.LEFT, padx=10, fill=tk.X, expand=True)
        
        # 文本结果区域
        ttk.Label(main_frame, text="转换结果:").pack(anchor=tk.W, pady=(10, 5))
        
        self.result_text = scrolledtext.ScrolledText(main_frame, wrap=tk.WORD, height=15)
        self.result_text.pack(fill=tk.BOTH, expand=True)
        self.result_text.config(state=tk.DISABLED)
    
    def browse_file(self):
        file_path = filedialog.askopenfilename(
            title="选择MP3文件",
            filetypes=[("MP3文件", "*.mp3"), ("所有文件", "*.*")]
        )
        if file_path:
            self.file_path.set(file_path)
    
    def update_result_text(self, text):
        self.result_text.config(state=tk.NORMAL)
        self.result_text.delete(1.0, tk.END)
        self.result_text.insert(tk.END, text)
        self.result_text.config(state=tk.DISABLED)
    
    def start_conversion(self):
        mp3_file = self.file_path.get().strip()
        
        if not mp3_file:
            messagebox.showerror("错误", "请选择MP3文件")
            return
        
        if not os.path.exists(mp3_file):
            messagebox.showerror("错误", f"文件 {mp3_file} 不存在")
            return
        
        # 获取语言代码
        language_selection = self.language_combo.get()
        language_code = language_selection.split('(')[1].split(')')[0]
        
        # 禁用按钮，显示进度条
        self.convert_button.config(state=tk.DISABLED)
        self.progress.start()
        
        # 在新线程中运行转换过程，避免界面冻结
        threading.Thread(target=self.run_conversion, args=(mp3_file, language_code)).start()
    
    def run_conversion(self, mp3_file, language_code):
        try:
            # 更新状态
            self.root.after(0, lambda: self.update_result_text("正在处理中，请稍候..."))
            
            # 转换为WAV格式
            temp_wav = convert_mp3_to_wav(mp3_file)
            
            try:
                # 转换为文字
                text = transcribe_audio(temp_wav, language_code)
                
                # 如果需要保存到文件
                if self.save_var.get():
                    output_file = filedialog.asksaveasfilename(
                        title="保存文本文件",
                        defaultextension=".txt",
                        filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
                    )
                    if output_file:
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(text)
                        self.root.after(0, lambda: messagebox.showinfo("成功", f"文字已保存到: {output_file}"))
                
                # 显示结果
                self.root.after(0, lambda: self.update_result_text(text))
            
            finally:
                # 删除临时文件
                if os.path.exists(temp_wav):
                    os.remove(temp_wav)
        
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("错误", f"转换失败: {str(e)}"))
            self.root.after(0, lambda: self.update_result_text(f"转换失败: {str(e)}"))
        
        finally:
            # 恢复按钮状态，停止进度条
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.convert_button.config(state=tk.NORMAL))

def main():
    root = tk.Tk()
    app = MP3ToTextGUI(root)
    root.mainloop()

if __name__ == "__main__":
    main() 