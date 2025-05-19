#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Tkinter测试程序
"""

import tkinter as tk
from tkinter import ttk, messagebox

def show_message():
    messagebox.showinfo("测试", "Tkinter正常工作！")

root = tk.Tk()
root.title("Tkinter测试")
root.geometry("300x200")

label = ttk.Label(root, text="这是一个Tkinter测试")
label.pack(pady=20)

button = ttk.Button(root, text="点击测试", command=show_message)
button.pack(pady=20)

if __name__ == "__main__":
    root.mainloop() 