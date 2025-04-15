import sys
import os
import tempfile
import numpy as np
import asyncio
import subprocess
import logging
from threading import Thread
from PyQt5.QtWidgets import (QApplication, QWidget, QPushButton, QVBoxLayout, 
                            QLabel, QTextEdit, QHBoxLayout, QMainWindow, 
                            QSplitter, QFrame)
from PyQt5.QtCore import QThread, pyqtSignal, Qt, QObject, pyqtSlot
from PyQt5.QtGui import QFont, QIcon
import sounddevice as sd
from scipy.io.wavfile import write
import whisper
from hanziconv import HanziConv
from concurrent.futures import ThreadPoolExecutor

# 配置日志
logger = logging.getLogger("chat_ui")

class RecordingThread(QThread):
    """录音线程"""
    finished = pyqtSignal(str)
    
    def __init__(self, model_name="base"):
        super().__init__()
        self.is_recording = False
        self.model_name = model_name
        self.model = None
        
    def run(self):
        # 采样参数
        fs = 16000  # 采样率
        recording = []
        
        # 录音回调
        def callback(indata, frames, time, status):
            if self.is_recording:
                recording.append(indata.copy())
        
        # 开始录制
        self.is_recording = True
        stream = sd.InputStream(callback=callback, channels=1, samplerate=fs)
        with stream:
            while self.is_recording:
                sd.sleep(100)  # 每100ms检查一次状态
        
        # 处理录音
        if not recording:
            self.finished.emit("")
            return
            
        audio_data = np.concatenate(recording, axis=0)
        
        # 保存为临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_filename = temp_audio.name
            write(temp_filename, fs, audio_data)
        
        # 加载模型（如果需要）
        if self.model is None:
            self.model = whisper.load_model(self.model_name)
        
        # 识别语音
        try:
            result = self.model.transcribe(temp_filename, language="zh")
            transcribed_text = result["text"].strip()
            
            # 将繁体转换为简体
            simplified_text = HanziConv.toSimplified(transcribed_text)
            print(f"原始识别结果(繁体): {transcribed_text}")
            print(f"转换后结果(简体): {simplified_text}")
            
            self.finished.emit(simplified_text)
        except Exception as e:
            logger.error(f"语音识别错误: {str(e)}")
            self.finished.emit("")
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_filename)
            except:
                pass
    
    def stop_recording(self):
        """停止录音"""
        self.is_recording = False


class AsyncHelper(QObject):
    """帮助在Qt环境中处理异步函数"""
    
    def __init__(self, worker, parent=None):
        super().__init__(parent)
        self.worker = worker
        
    def start_worker(self, *args, **kwargs):
        """启动异步工作线程"""
        async def _wrapper():
            try:
                result = await self.worker(*args, **kwargs)
                self.on_worker_done.emit(result)
            except Exception as e:
                logger.exception(f"工作线程异常: {str(e)}")
                self.on_worker_error.emit(str(e))
        
        # 使用当前事件循环
        task = asyncio.create_task(_wrapper())
        
        # 确保任务完成后被适当清理
        def done_callback(future):
            try:
                future.result()  # 获取任何未处理的异常
            except Exception as e:
                if not isinstance(e, asyncio.CancelledError):
                    logger.exception("Unhandled exception in worker")
        
        task.add_done_callback(done_callback)
    
    on_worker_done = pyqtSignal(object)
    on_worker_error = pyqtSignal(str)


class TtsHelper:
    """语音合成辅助类"""
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=1)
        self.tts_cache = {}  # 简单的缓存机制

    async def speak_text(self, text, voice="zh-CN-XiaoxiaoNeural"):
        """使用Edge-TTS合成并播放语音"""
        try:
            # 为避免重复生成相同文本的语音，使用简单缓存
            cache_key = f"{text}_{voice}"
            if cache_key in self.tts_cache:
                output_file = self.tts_cache[cache_key]
            else:
                # 导入放在函数内，避免应用启动时就导入
                import edge_tts
                
                # 创建临时文件用于保存语音
                temp_file = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
                output_file = temp_file.name
                temp_file.close()
                
                # 执行TTS转换
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_file)
                
                # 缓存结果（保留最近10个）
                if len(self.tts_cache) >= 10:
                    # 移除最早添加的缓存项
                    oldest_key = next(iter(self.tts_cache))
                    try:
                        os.unlink(self.tts_cache[oldest_key])
                    except:
                        pass
                    del self.tts_cache[oldest_key]
                self.tts_cache[cache_key] = output_file
            
            # 播放语音文件
            def play_audio():
                try:
                    # 使用系统命令播放音频（跨平台）
                    if sys.platform == "darwin":  # macOS
                        subprocess.run(["afplay", output_file])
                    elif sys.platform == "win32":  # Windows
                        import winsound
                        winsound.PlaySound(output_file, winsound.SND_FILENAME)
                    else:  # Linux
                        subprocess.run(["aplay", output_file])
                except Exception as e:
                    print(f"播放音频错误: {e}")
            
            # 在线程池中执行播放，避免阻塞UI
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(self.executor, play_audio)
            
            return True
        except Exception as e:
            print(f"语音合成错误: {e}")
            return False

# 替换 Edge-TTS 部分为 pyttsx3
# import pyttsx3

# class TtsHelper:
#     """本地语音合成辅助类"""
#     def __init__(self):
#         self.engine = pyttsx3.init()
#         # 设置中文女声（如果有的话）
#         voices = self.engine.getProperty('voices')
#         for voice in voices:
#             if 'chinese' in voice.languages[0].lower():
#                 self.engine.setProperty('voice', voice.id)
#                 break
#         # 设置语速和音量
#         self.engine.setProperty('rate', 180)  # 语速
#         self.engine.setProperty('volume', 0.9)  # 音量

#     async def speak_text(self, text, voice=None):
#         """合成并播放语音（本地）"""
#         try:
#             # 使用异步运行，避免阻塞界面
#             loop = asyncio.get_event_loop()
#             await loop.run_in_executor(None, self._speak, text)
#             return True
#         except Exception as e:
#             print(f"语音合成错误: {e}")
#             return False
    
#     def _speak(self, text):
#         """实际执行语音合成和播放"""
#         self.engine.say(text)
#         self.engine.runAndWait()

class ChatWindow(QMainWindow):
    """聊天主窗口"""
    
    def __init__(self, assistant):
        super().__init__()
        self.assistant = assistant
        self.recording_thread = RecordingThread()
        self.recording_thread.finished.connect(self.on_voice_recognized)
        self.tts_helper = TtsHelper()  # 添加TTS助手
        self.initUI()
        
    def initUI(self):
        self.setWindowTitle('MCP智能助手')
        self.setGeometry(100, 100, 800, 600)
        
        # 创建中央窗口部件
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # 主布局
        main_layout = QVBoxLayout(central_widget)
        
        # 创建聊天区和状态区
        splitter = QSplitter(Qt.Vertical)
        main_layout.addWidget(splitter)
        
        # 聊天历史区域
        self.chat_history = QTextEdit()
        self.chat_history.setReadOnly(True)
        self.chat_history.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff; 
                border: 1px solid #e0e0e0;
                border-radius: 5px;
                padding: 5px;
                font-size: 14px;
                line-height: 1.5;
            }
            QScrollBar:vertical {
                border: none;
                background: #f5f5f5;
                width: 10px;
                border-radius: 5px;
            }
            QScrollBar::handle:vertical {
                background: #bdbdbd;
                min-height: 20px;
                border-radius: 5px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
        """)
        splitter.addWidget(self.chat_history)
        
        # 状态和输入区域容器
        input_container = QFrame()
        input_layout = QVBoxLayout(input_container)
        splitter.addWidget(input_container)
        
        # 状态标签
        self.status_label = QLabel('准备就绪')
        self.status_label.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(self.status_label)
        
        # 文本输入区域
        self.text_input = QTextEdit()
        self.text_input.setPlaceholderText("在这里输入您的问题...")
        self.text_input.setMinimumHeight(80)
        self.text_input.setMaximumHeight(100)
        input_layout.addWidget(self.text_input)
        
        # 按钮区域
        buttons_layout = QHBoxLayout()
        
        # 发送文本按钮
        self.send_button = QPushButton('发送')
        self.send_button.clicked.connect(self.send_text)
        buttons_layout.addWidget(self.send_button)
        
        # 语音按钮
        self.voice_button = QPushButton('语音输入')
        self.voice_button.clicked.connect(self.toggle_recording)
        buttons_layout.addWidget(self.voice_button)
        
        # 清除按钮
        self.clear_button = QPushButton('清除')
        self.clear_button.clicked.connect(self.clear_input)
        buttons_layout.addWidget(self.clear_button)
        
        input_layout.addLayout(buttons_layout)
        
        # 设置分割器初始比例
        splitter.setSizes([400, 200])
        
        # 欢迎消息
        self.add_system_message("欢迎使用MCP智能助手! 请输入您的问题或点击语音输入按钮。")
        
        # 创建异步处理器
        self.async_helper = AsyncHelper(self.process_query)
        self.async_helper.on_worker_done.connect(self.on_response_ready)
        self.async_helper.on_worker_error.connect(self.on_response_error)
    
    def toggle_recording(self):
        """切换录音状态"""
        if not self.recording_thread.is_recording:
            # 开始录音
            self.status_label.setText('🎤 正在录音...')
            self.voice_button.setText('停止录音')
            self.send_button.setEnabled(False)
            self.recording_thread.start()
        else:
            # 停止录音
            self.status_label.setText('处理中...')
            self.recording_thread.stop_recording()
            self.voice_button.setEnabled(False)
    
    def on_voice_recognized(self, text):
        """语音识别完成时调用"""
        self.text_input.setText(text)
        self.status_label.setText('语音识别完成')
        self.voice_button.setText('语音输入')
        self.voice_button.setEnabled(True)
        self.send_button.setEnabled(True)
        
        # 如果有识别结果，自动发送
        if text:
            self.send_text()
    
    def send_text(self):
        """发送文本消息"""
        text = self.text_input.toPlainText().strip()
        if not text:
            return
            
        # 显示用户消息
        self.add_user_message(text)
        self.text_input.clear()
        
        # 更新状态
        self.status_label.setText('正在处理您的问题...')
        self.send_button.setEnabled(False)
        self.voice_button.setEnabled(False)
        
        # 异步处理查询
        self.async_helper.start_worker(text)
    
    async def process_query(self, text):
        """异步处理用户查询"""
        return await self.assistant.process_query_async(text)
    
    @pyqtSlot(object)
    def on_response_ready(self, response):
        """当响应准备好时调用"""
        self.add_assistant_message(response)
        self.status_label.setText('准备就绪')
        self.send_button.setEnabled(True)
        self.voice_button.setEnabled(True)
        
        # 使用Edge-TTS播放响应
        asyncio.create_task(self.tts_helper.speak_text(response))
    
    @pyqtSlot(str)
    def on_response_error(self, error_msg):
        """当响应出错时调用"""
        self.add_system_message(f"错误: {error_msg}")
        self.status_label.setText('出现错误')
        self.send_button.setEnabled(True)
        self.voice_button.setEnabled(True)
    
    def clear_input(self):
        """清除输入框"""
        self.text_input.clear()
    
    def add_user_message(self, message):
        """添加用户消息到聊天历史"""
        html = f'''
        <div style="margin: 10px 0 10px auto; max-width: 80%; clear: both;">
            <div style="background-color: #e1f5fe; color: #01579b; border-radius: 15px; 
                        padding: 8px 12px; display: inline-block; float: right; 
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <span style="font-weight: bold; color: #0277bd;">你</span><br/>
                {message}
            </div>
        </div>
        <div style="clear: both;"></div>
        '''
        self.chat_history.append(html)
        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
    
    def add_assistant_message(self, message):
        """添加助手消息到聊天历史"""
        html = f'''
        <div style="margin: 10px auto 10px 0; max-width: 80%; clear: both;">
            <div style="background-color: #f1f8e9; color: #1b5e20; border-radius: 15px; 
                        padding: 8px 12px; display: inline-block; float: left;
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <span style="font-weight: bold; color: #2e7d32;">助手</span><br/>
                {message}
            </div>
        </div>
        <div style="clear: both;"></div>
        '''
        self.chat_history.append(html)
        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
    
    def add_system_message(self, message):
        """添加系统消息到聊天历史"""
        html = f'''
        <div style="margin: 5px auto; text-align: center; clear: both;">
            <div style="background-color: #ffebee; color: #b71c1c; border-radius: 10px; 
                        padding: 5px 10px; display: inline-block; 
                        box-shadow: 0 1px 2px rgba(0,0,0,0.1);">
                <span style="font-weight: bold;">系统通知</span><br/>
                {message}
            </div>
        </div>
        <div style="clear: both;"></div>
        '''
        self.chat_history.append(html)
        # 滚动到底部
        self.chat_history.verticalScrollBar().setValue(
            self.chat_history.verticalScrollBar().maximum()
        )
    
    def closeEvent(self, event):
        """窗口关闭事件处理"""
        if self.recording_thread.is_recording:
            self.recording_thread.stop_recording()
        event.accept() 