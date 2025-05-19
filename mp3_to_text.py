#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
MP3转文字工具
将MP3音频文件转换为文本
"""

import os
import argparse
import speech_recognition as sr
from pydub import AudioSegment
import tempfile
import json
import time
import logging
import subprocess
from aip import AipSpeech
import threading

# 任务控制器类，用于控制转换过程的暂停和停止
class TaskController:
    def __init__(self):
        self._paused = False
        self._stop_requested = False
        self._lock = threading.Lock()
    
    def pause(self):
        """暂停任务"""
        with self._lock:
            self._paused = True
    
    def resume(self):
        """恢复任务"""
        with self._lock:
            self._paused = False
    
    def stop(self):
        """请求停止任务"""
        with self._lock:
            self._stop_requested = True
    
    def is_paused(self):
        """检查是否处于暂停状态"""
        with self._lock:
            return self._paused
    
    def is_stop_requested(self):
        """检查是否请求停止"""
        with self._lock:
            return self._stop_requested
    
    def reset(self):
        """重置控制器状态"""
        with self._lock:
            self._paused = False
            self._stop_requested = False
    
    def wait_if_paused(self):
        """如果处于暂停状态，则等待直到恢复"""
        while True:
            with self._lock:
                if not self._paused:
                    return
                if self._stop_requested:
                    return
            time.sleep(0.1)  # 短暂休眠避免CPU占用过高

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger("MP3ToText")

# 为第三方库配置日志
logging.getLogger("urllib3").setLevel(logging.DEBUG)

# 百度语音识别API配置
# 请在此处替换为您的百度API密钥
BAIDU_APP_ID = ''
BAIDU_API_KEY = ''
BAIDU_SECRET_KEY = ''

def convert_mp3_to_wav(mp3_path):
    """
    将MP3文件转换为WAV格式（因为语音识别库需要WAV格式）
    """
    print(f"正在转换 {mp3_path} 为WAV格式...")
    try:
        sound = AudioSegment.from_mp3(mp3_path)
        
        # 创建临时文件
        fd, temp_path = tempfile.mkstemp(suffix='.wav')
        os.close(fd)
        
        # 打印ffmpeg命令
        logger.debug(f"subprocess.call(['ffmpeg', '-y', '-f', 'mp3', '-i', '{mp3_path}', '-acodec', 'pcm_s16le', '-vn', '-f', 'wav', '-'])")
        
        sound.export(temp_path, format="wav")
        return temp_path
    except Exception as e:
        logger.error(f"转换MP3到WAV时出错: {str(e)}")
        raise

def transcribe_audio_google(audio_path, language="zh-CN"):
    """
    使用Google语音识别服务将音频文件转换为文字
    """
    recognizer = sr.Recognizer()
    
    # 将语音识别的灵敏度调整到合适值
    recognizer.energy_threshold = 300
    
    # 加载音频文件
    with sr.AudioFile(audio_path) as source:
        print("正在分析音频文件...")
        logger.debug("调用speech_recognition分析音频文件")
        audio = recognizer.record(source)
    
    print("正在使用Google API转换为文字...")
    try:
        # 使用Google语音识别服务
        logger.debug(f"发送请求到Google语音识别服务，语言代码: {language}")
        start_time = time.time()
        text = recognizer.recognize_google(audio, language=language)
        elapsed_time = time.time() - start_time
        logger.debug(f"Google API响应时间: {elapsed_time:.2f}秒")
        return text
    except sr.UnknownValueError:
        logger.warning("Google语音识别服务无法识别音频内容")
        return "无法识别音频"
    except sr.RequestError as e:
        logger.error(f"无法访问Google语音识别服务: {str(e)}")
        return f"Google语音识别服务错误: {e}"

def transcribe_audio_baidu(audio_path, language="zh", progress_callback=None, task_controller=None):
    """
    使用百度语音识别API将音频文件转换为文字
    """
    if not BAIDU_APP_ID or not BAIDU_API_KEY or not BAIDU_SECRET_KEY:
        print("错误: 未配置百度语音识别API密钥")
        logger.error("未配置百度语音识别API密钥")
        return "错误: 未配置百度语音识别API密钥，请在脚本中配置APP_ID、API_KEY和SECRET_KEY"

    # 创建AipSpeech客户端
    logger.debug(f"创建百度AipSpeech客户端，APP_ID: {BAIDU_APP_ID[:4]}***")
    client = AipSpeech(BAIDU_APP_ID, BAIDU_API_KEY, BAIDU_SECRET_KEY)
    
    # 读取音频文件
    print("正在读取音频文件...")
    with open(audio_path, 'rb') as fp:
        audio_data = fp.read()
    
    # 日志记录文件大小
    file_size = len(audio_data)
    logger.debug(f"音频文件大小: {file_size/1024/1024:.2f} MB")
    
    # 限制文件大小（百度API限制10MB以内）
    if file_size > 10 * 1024 * 1024:
        print("警告: 文件大小超过10MB，尝试分段识别...")
        logger.warning(f"文件大小({file_size/1024/1024:.2f}MB)超过百度API限制(10MB)，进行分段处理")
        return transcribe_large_audio_baidu(audio_path, language, progress_callback, task_controller)
    
    # 设置参数
    options = {}
    
    # 语言设置
    if language.startswith("zh"):
        options["dev_pid"] = 1537  # 普通话(支持简繁)
    elif language.startswith("en"):
        options["dev_pid"] = 1737  # 英语
    elif language.startswith("ja"):
        options["dev_pid"] = 1737  # 日语
    elif language.startswith("ko"):
        options["dev_pid"] = 1737  # 韩语
    # 更多语言支持可以参考百度文档
    
    # 日志记录请求参数
    logger.debug(f"百度API请求参数: format=wav, rate=16000, dev_pid={options.get('dev_pid', 1537)}")
    
    # 发送识别请求
    print("正在使用百度API转换为文字...")
    start_time = time.time()
    logger.debug("发送请求到百度语音识别服务")
    
    try:
        result = client.asr(audio_data, 'wav', 16000, options)
        elapsed_time = time.time() - start_time
        print(f"请求耗时: {elapsed_time:.2f}秒")
        
        # 日志记录响应详情
        logger.debug(f"百度API响应耗时: {elapsed_time:.2f}秒")
        logger.debug(f"百度API响应状态码: {result.get('err_no', -1)}")
        
        # 解析结果
        if result["err_no"] == 0:
            text_result = "\n".join(result["result"])
            logger.debug(f"识别成功，识别结果长度: {len(text_result)} 字符")
            return text_result
        else:
            error_msg = f"百度语音识别服务错误: {result['err_msg']} (错误码: {result['err_no']})"
            logger.error(error_msg)
            return error_msg
    except Exception as e:
        logger.error(f"调用百度API时发生异常: {str(e)}")
        return f"百度语音识别服务异常: {str(e)}"

def transcribe_large_audio_baidu(audio_path, language="zh", progress_callback=None, task_controller=None):
    """
    处理大型音频文件，分段进行识别
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码
        progress_callback: 进度回调函数，接收两个参数(current, total)
        task_controller: 任务控制器，用于控制暂停和停止
    """
    # 加载音频
    try:
        logger.debug("加载大型音频文件进行分段处理")
        audio = AudioSegment.from_wav(audio_path)
        
        # 分段长度(毫秒) - 约为1分钟
        chunk_length_ms = 60000
        
        # 计算分段数量
        chunks_number = len(audio) // chunk_length_ms + 1
        
        logger.debug(f"音频时长: {len(audio)/1000:.2f}秒，分为{chunks_number}段处理")
        print(f"文件已分为{chunks_number}段处理")
        
        # 存储所有识别结果
        transcription = []
        
        # 分段处理
        for i in range(chunks_number):
            # 检查是否请求停止
            if task_controller and task_controller.is_stop_requested():
                logger.info("检测到停止请求，中断处理")
                print("处理已停止")
                return "处理已被用户停止"
            
            # 检查是否暂停
            if task_controller:
                task_controller.wait_if_paused()
                if task_controller.is_stop_requested():
                    logger.info("暂停后检测到停止请求，中断处理")
                    return "处理已被用户停止"
            
            print(f"处理分段 {i+1}/{chunks_number}...")
            logger.debug(f"开始处理第{i+1}段（共{chunks_number}段）")
            
            # 报告进度
            if progress_callback:
                progress_callback(i, chunks_number)
            
            # 截取音频片段
            chunk = audio[i*chunk_length_ms:(i+1)*chunk_length_ms]
            
            # 创建临时文件保存片段
            fd, chunk_path = tempfile.mkstemp(suffix='.wav')
            os.close(fd)
            
            try:
                # 导出音频片段
                logger.debug(f"导出音频片段 {i+1} 到临时文件: {chunk_path}")
                chunk.export(chunk_path, format="wav")
                
                # 识别片段
                logger.debug(f"对片段 {i+1} 进行语音识别")
                chunk_result = transcribe_audio_baidu(chunk_path, language, progress_callback, task_controller)
                
                # 如果返回停止信息，则转发停止结果
                if chunk_result == "处理已被用户停止":
                    return chunk_result
                
                # 如果识别成功，添加到结果中
                if not chunk_result.startswith("百度语音识别服务错误"):
                    transcription.append(chunk_result)
                    logger.debug(f"片段 {i+1} 识别成功，结果长度: {len(chunk_result)} 字符")
                else:
                    logger.warning(f"片段 {i+1} 识别失败: {chunk_result}")
                    
            finally:
                # 清理临时文件
                if os.path.exists(chunk_path):
                    logger.debug(f"删除临时文件: {chunk_path}")
                    os.remove(chunk_path)
        
        # 处理完成，报告100%进度
        if progress_callback:
            progress_callback(chunks_number, chunks_number)
        
        # 合并结果
        final_result = "\n".join(transcription)
        logger.debug(f"所有片段处理完成，最终结果长度: {len(final_result)} 字符")
        return final_result
        
    except Exception as e:
        logger.error(f"分段处理大型音频文件时出错: {str(e)}")
        return f"处理大型音频文件时出错: {str(e)}"

def transcribe_audio(audio_path, language="zh-CN", use_baidu=True, progress_callback=None, task_controller=None):
    """
    将音频文件转换为文字，可以选择使用百度或Google的API
    
    Args:
        audio_path: 音频文件路径
        language: 语言代码
        use_baidu: 是否使用百度API
        progress_callback: 进度回调函数
        task_controller: 任务控制器，用于控制暂停和停止
    """
    if use_baidu:
        # 转换语言代码格式（从Google格式转为百度格式）
        baidu_language = language.split("-")[0] if "-" in language else language
        logger.info(f"使用百度语音识别API，语言: {baidu_language}")
        return transcribe_audio_baidu(audio_path, baidu_language, progress_callback, task_controller)
    else:
        logger.info(f"使用Google语音识别API，语言: {language}")
        return transcribe_audio_google(audio_path, language)

def main():
    # 创建命令行参数解析器
    parser = argparse.ArgumentParser(description='MP3文件转文字工具')
    parser.add_argument('mp3_file', help='MP3文件路径')
    parser.add_argument('-o', '--output', help='输出文件路径（默认打印到控制台）')
    parser.add_argument('-l', '--language', default='zh-CN', help='语言代码（默认：zh-CN，中文）')
    parser.add_argument('--use-google', action='store_true', help='使用Google语音识别API（默认使用百度API）')
    parser.add_argument('-v', '--verbose', action='store_true', help='显示详细日志信息')
    
    args = parser.parse_args()
    
    # 设置日志级别
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
        logger.debug("启用详细日志模式")
    else:
        logging.getLogger().setLevel(logging.INFO)
    
    # 记录开始执行
    logger.info(f"开始处理文件: {args.mp3_file}")
    logger.info(f"语言: {args.language}")
    logger.info(f"使用API: {'Google' if args.use_google else '百度'}")
    
    # 检查文件是否存在
    if not os.path.exists(args.mp3_file):
        logger.error(f"文件不存在: {args.mp3_file}")
        print(f"错误：文件 {args.mp3_file} 不存在")
        return
    
    # 转换为WAV格式
    try:
        temp_wav = convert_mp3_to_wav(args.mp3_file)
        logger.info("MP3转WAV成功")
        
        try:
            # 转换为文字
            logger.info("开始语音识别")
            text = transcribe_audio(temp_wav, args.language, not args.use_google)
            logger.info("语音识别完成")
            
            # 输出结果
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    f.write(text)
                logger.info(f"结果已写入文件: {args.output}")
                print(f"文字已保存到: {args.output}")
            else:
                print("\n转换结果:")
                print("-" * 50)
                print(text)
                print("-" * 50)
        finally:
            # 删除临时文件
            if os.path.exists(temp_wav):
                logger.debug(f"删除临时WAV文件: {temp_wav}")
                os.remove(temp_wav)
    except Exception as e:
        logger.exception("处理过程中发生异常")
        print(f"错误: {str(e)}")

if __name__ == "__main__":
    main() 