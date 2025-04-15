"""
MCP智能助手 - 主程序
整合对话管理、状态管理、意图识别和工具调用的完整应用
"""

import os
import asyncio
import logging
import json
import subprocess
import tempfile
import numpy as np
from datetime import datetime
from typing import Optional, Dict, Any, List
import threading
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QEventLoop, QTimer
import qasync
from chat_ui import ChatWindow

# 导入用于录音和语音识别的包
import sounddevice as sd
from scipy.io.wavfile import write
import whisper

# 导入核心组件
from core.conversation_manager import ConversationManager
from core.state_manager import StateManager
from core.intent_recognizer import IntentRecognizer, Intent, IntentType
from core.tool_router import ToolRouter, ToolStatus, ToolResult
from core.llm_interface import LLMInterface

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("mcp_assistant")

# 全局变量，用于存储Whisper模型
model = None

# 延迟加载Whisper模型，避免启动时加载
def get_whisper_model():
    global model
    if model is None:
        logger.info("正在加载Whisper模型...")
        model = whisper.load_model("base")  # 可选 "tiny", "base", "small", "medium", "large"
        logger.info("Whisper模型加载完成")
    return model

class MCPAssistant:
    """MCP智能助手主类"""
    
    def __init__(self):
        """初始化智能助手"""
        logger.info("初始化MCP智能助手...")
        
        # 初始化状态管理器
        self.state_manager = StateManager()
        
        # 初始化对话管理器
        self.conversation_manager = ConversationManager(
            system_prompt="你是MCP智能助手，能够回答问题并提供各种服务。",
            max_history_length=20
        )
        
        # 初始化LLM接口
        self.llm = LLMInterface(state_manager=self.state_manager)
        
        # 初始化意图识别器
        self.intent_recognizer = IntentRecognizer(
            llm_interface=self.llm,
            state_manager=self.state_manager
        )
        
        # 初始化工具路由器
        self.tool_router = ToolRouter(
            state_manager=self.state_manager
        )
        
        # 默认位置信息
        self.default_location = "永川"
        self.default_venue = "重庆永川时代天街"
        
    async def initialize(self):
        """异步初始化组件"""
        logger.info("执行异步初始化...")
        
        # 设置默认上下文
        self.state_manager.set_context("location", self.default_location)
        self.state_manager.set_context("venue", self.default_venue)
        self.state_manager.set_context("timestamp", datetime.now().isoformat())
        
        # 初始化工具
        await self.tool_router.initialize()
        
        logger.info("异步初始化完成")
    
    def process_query(self, query: str) -> str:
        """同步处理用户查询 - 用于非异步环境"""
        try:
            # 使用同步版本调用
            return asyncio.run(self.process_query_async(query))
        except Exception as e:
            logger.error(f"处理查询时出错: {str(e)}")
            return f"抱歉，处理您的请求时出现错误: {str(e)}"
    
    async def process_query_async(self, query: str) -> str:
        """异步处理用户查询"""
        logger.info(f"处理用户查询: {query}")
        
        try:
            # 添加用户消息到对话历史
            self.conversation_manager.add_user_message(query)
            
            # 识别意图
            intent = await self.intent_recognizer.recognize(query)
            
            # 记录意图
            logger.info(f"识别到意图: {intent.type.name}, 工具: {intent.tool_name}, 置信度: {intent.confidence}")
            
            # 处理特殊命令
            if intent.type == IntentType.COMMAND:
                response = await self._handle_command(intent)
                self.conversation_manager.add_assistant_message(response)
                return response
            
            # 判断是否需要工具
            if intent.tool_name and (intent.type == IntentType.QUERY or intent.type == IntentType.TOOL_SPECIFIC):
                response = await self._call_tool_and_respond(intent)
                self.conversation_manager.add_assistant_message(response)
                return response
            
            # 一般对话
            response = await self._handle_general_chat(query, intent)
            self.conversation_manager.add_assistant_message(response)
            return response
            
        except Exception as e:
            logger.error(f"处理查询时出错: {str(e)}", exc_info=True)
            error_msg = f"抱歉，处理您的请求时出现错误: {str(e)}"
            self.conversation_manager.add_assistant_message(error_msg)
            return error_msg
    
    async def _handle_command(self, intent: Intent) -> str:
        """处理命令类型意图"""
        command = intent.tool_name or "unknown"
        
        if command == "reset":
            # 重置对话历史
            self.conversation_manager.clear_history()
            return "对话历史已重置。"
        
        elif command == "help":
            # 返回帮助信息
            help_text = """
            我可以帮助您:
            - 查询天气信息
            - 查找商场和商品
            - 搜索附近区域信息
            - 回答一般问题
            
            您可以使用以下命令:
            - 重置: 清除对话历史
            - 帮助: 显示此帮助信息
            """
            return help_text
        
        else:
            return f"未识别的命令: {command}"
    
    async def _call_tool_and_respond(self, intent: Intent) -> str:
        """调用工具并构建回复"""
        # 获取工具信息
        tool_name = intent.tool_name
        method = None
        
        # 从意图实体提取方法名
        for entity in intent.entities:
            if entity.type == "method":
                method = entity.value
                break
        
        # 从意图中提取参数
        params = {}
        for entity in intent.entities:
            if entity.type not in ["method", "tool"]:
                params[entity.type] = entity.value
        
        # 记录工具调用
        logger.info(f"调用工具: {tool_name}, 方法: {method}, 参数: {params}")
        
        # 调用工具
        if method:
            tool_id = f"{tool_name}.{method}"
        else:
            tool_id = tool_name
            
        # 执行工具调用 - 修正为只传递intent参数
        tool_result = await self.tool_router.execute_tool_async(intent)
        
        if tool_result.status == ToolStatus.SUCCESS:
            # 添加工具结果到元数据
            metadata = {
                "tool_name": tool_name,
                "tool_result": tool_result.to_dict()
            }
            
            # 使用LLM生成自然语言回复
            messages = self.conversation_manager.get_formatted_messages()
            
            # 添加工具消息
            tool_message = {
                "role": "tool", 
                "content": json.dumps(tool_result.data, ensure_ascii=False),
                "name": tool_name
            }
            messages.append(tool_message)
            
            # 添加系统提示
            system_context = self._get_system_prompt(tool_result.data, intent)
            messages[0]["content"] = system_context
            
            # 调用LLM生成回复
            try:
                response = self.llm.generate_response(messages)
                return response["content"]
            except Exception as e:
                logger.error(f"生成回复时出错: {str(e)}")
                # 直接返回工具结果
                return f"工具结果: {json.dumps(tool_result.data, ensure_ascii=False)}"
        else:
            # 工具调用失败
            error_msg = f"工具调用失败: {tool_result.message}"
            logger.warning(error_msg)
            return error_msg
    
    async def _handle_general_chat(self, query: str, intent: Intent) -> str:
        """处理一般聊天对话"""
        # 准备消息
        messages = self.conversation_manager.get_formatted_messages()
        
        # 更新系统提示
        system_prompt = self._get_system_prompt()
        if messages and messages[0]["role"] == "system":
            messages[0]["content"] = system_prompt
        
        # 生成回复
        try:
            response = self.llm.generate_response(messages)
            return response["content"]
        except Exception as e:
            logger.error(f"生成回复时出错: {str(e)}")
            return "抱歉，我现在无法生成回复。请稍后再试。"
    
    def _get_system_prompt(self, tool_result: Any = None, intent: Intent = None) -> str:
        """获取系统提示"""
        # 获取当前上下文
        location = self.state_manager.context.location
        venue = self.state_manager.context.venue
        
        # 基础系统提示
        system_prompt = f"""你是一个智能助手，致力于提供准确、有用的信息。
                        当前位置: {location}
                        当前场所: {venue}

                        """
        
        # 如果有工具结果，添加到系统提示
        if tool_result and intent:
            system_prompt += f"""
                            用户询问: "{intent.raw_query}"
                            工具调用结果: {json.dumps(tool_result, ensure_ascii=False)}

                            请用这些信息提供友好、专业的回答。不要说"根据工具调用结果"之类的话，直接给出信息。
                            """
        
        return system_prompt
    
    async def cleanup(self):
        """清理资源"""
        logger.info("清理资源...")
        
        # 保存意图缓存
        if hasattr(self.intent_recognizer, 'save_cache'):
            self.intent_recognizer.save_cache()
        
        # 保存状态
        self.state_manager.save_state()
        
        # 清理工具路由器
        await self.tool_router.cleanup()
        
        logger.info("资源清理完成")

# 使用线程进行录音，避免阻塞事件循环
def record_audio(fs=16000, max_duration=60):
    """在单独线程中录制音频，返回录音数据"""
    recording = []
    is_recording = True
    
    # 定义录音回调函数
    def callback(indata, frames, time, status):
        if is_recording and status:
            logger.warning(f"录音状态: {status}")
        if is_recording:
            recording.append(indata.copy())
    
    # 开始录制
    stream = sd.InputStream(callback=callback, channels=1, samplerate=fs)
    stream.start()
    
    try:
        # 等待用户按下Ctrl+C或达到最大时长
        for _ in range(max_duration * 10):  # 每100ms检查一次
            if not is_recording:
                break
            sd.sleep(100)
    except KeyboardInterrupt:
        pass
    finally:
        is_recording = False
        stream.stop()
        stream.close()
    
    if not recording:
        return None
    
    # 将录音数据转换为NumPy数组
    return np.concatenate(recording, axis=0)

async def record_and_transcribe() -> str:
    """录制音频并使用Whisper转录为文本"""
    loop = asyncio.get_event_loop()
    
    try:
        # 使用线程执行录音，避免阻塞事件循环
        audio_data = await loop.run_in_executor(None, record_audio)
        
        if audio_data is None:
            return ""
        
        # 将录音保存为临时文件
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_filename = temp_audio.name
            write(temp_filename, 16000, audio_data)
        
        # 在单独的线程中使用Whisper识别语音
        def transcribe_audio():
            try:
                # 使用延迟加载的模型
                result = get_whisper_model().transcribe(temp_filename, language="zh")
                return result["text"].strip()
            except Exception as e:
                logger.error(f"语音识别错误: {str(e)}")
                return ""
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_filename)
                except:
                    pass
        
        # 在线程池中执行转录，避免阻塞事件循环
        return await loop.run_in_executor(None, transcribe_audio)
    
    except Exception as e:
        logger.error(f"录音或转录过程出错: {str(e)}")
        return ""

# 异步获取语音输入
async def get_voice_input():
    """显示语音输入对话框并返回识别的文本"""
    loop = asyncio.get_event_loop()
    app = QApplication.instance() or QApplication(sys.argv)
    
    future = loop.create_future()
    
    def on_text_ready(text):
        if not future.done():
            future.set_result(text)
    
    dialog = VoiceInputDialog()
    dialog.text_ready.connect(on_text_ready)
    
    # 在窗口关闭且未设置结果时完成future
    def on_dialog_closed():
        if not future.done():
            future.set_result("")
    
    dialog.destroyed.connect(on_dialog_closed)
    
    dialog.show()
    
    return await future

def main():
    """主函数 - 使用qasync适配Qt和asyncio"""
    # 创建Qt应用
    app = QApplication(sys.argv)
    
    # 创建事件循环
    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)
    
    # 定义异步入口点
    async def async_main():
        # 创建助手实例
        assistant = MCPAssistant()
        
        try:
            # 初始化组件
            await assistant.initialize()
            
            # 创建并显示窗口
            window = ChatWindow(assistant)
            window.show()
            
            # 设置关闭事件处理
            app.aboutToQuit.connect(lambda: asyncio.create_task(cleanup(assistant)))
            
            # 保持窗口运行直到关闭
            exit_future = asyncio.Future()
            app.aboutToQuit.connect(lambda: exit_future.set_result(None) 
                                   if not exit_future.done() else None)
            await exit_future
            
        except Exception as e:
            logger.error(f"运行时错误: {str(e)}")
            raise
    
    async def cleanup(assistant):
        """清理资源"""
        try:
            await assistant.cleanup()
        except Exception as e:
            logger.error(f"清理资源时出错: {str(e)}")
    
    # 运行异步主函数
    with loop:
        loop.run_until_complete(async_main())

if __name__ == "__main__":
    main()
