"""
LLM接口模块 - 负责与大语言模型的基础交互
"""

import os
import json
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

from openai import OpenAI, AsyncOpenAI

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("llm_interface")

class ModelConnectionError(Exception):
    """模型连接错误"""
    pass

class ModelRequestError(Exception):
    """模型请求错误"""
    pass

class LLMInterface:
    """
    大语言模型接口类 - 处理模型连接、请求和响应
    """
    
    def __init__(self, state_manager=None):
        """
        初始化LLM接口
        
        参数:
            state_manager: 状态管理器实例，用于获取配置
        """
        # 加载环境变量
        load_dotenv()
        
        # 存储状态管理器引用
        self.state_manager = state_manager
        
        # 读取环境变量
        self.api_key = os.getenv("OPENAI_API_KEY")
        self.base_url = os.getenv("BASE_URL", "http://localhost:11434/v1")
        self.model = os.getenv("MODEL", "llama3:8b")
        
        # 验证配置
        if not self.api_key:
            logger.warning("未设置OPENAI_API_KEY环境变量，将使用默认值")
            self.api_key = "ollama"  # Ollama默认不需要真正的API key
        
        # 初始化OpenAI客户端
        try:
            self.client = OpenAI(api_key=self.api_key, base_url=self.base_url)
            self.async_client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
            logger.info(f"LLM接口初始化成功，使用模型: {self.model}")
        except Exception as e:
            logger.error(f"初始化模型客户端失败: {str(e)}")
            raise ModelConnectionError(f"无法连接到模型服务: {str(e)}")
    
    def generate_response(self, 
                         messages: List[Dict[str, str]], 
                         temperature: float = 0.7,
                         max_tokens: int = 2000) -> Dict[str, Any]:
        """
        同步方式生成模型响应
        
        参数:
            messages: 消息列表，包含角色和内容
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成令牌数
            
        返回:
            包含模型响应的字典
        """
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model,
                "usage": {
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"生成模型响应失败: {str(e)}")
            raise ModelRequestError(f"模型请求失败: {str(e)}")
    
    async def generate_response_async(self, 
                                    messages: List[Dict[str, str]], 
                                    temperature: float = 0.7,
                                    max_tokens: int = 2000) -> Dict[str, Any]:
        """
        异步方式生成模型响应
        
        参数:
            messages: 消息列表，包含角色和内容
            temperature: 温度参数，控制随机性
            max_tokens: 最大生成令牌数
            
        返回:
            包含模型响应的字典
        """
        try:
            response = await self.async_client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            
            result = {
                "content": response.choices[0].message.content,
                "finish_reason": response.choices[0].finish_reason,
                "model": response.model,
                "usage": {
                    "completion_tokens": response.usage.completion_tokens,
                    "prompt_tokens": response.usage.prompt_tokens,
                    "total_tokens": response.usage.total_tokens
                }
            }
            
            return result
            
        except Exception as e:
            logger.error(f"异步生成模型响应失败: {str(e)}")
            raise ModelRequestError(f"异步模型请求失败: {str(e)}")
    
    def format_system_prompt(self, base_prompt: Optional[str] = None) -> str:
        """
        格式化系统提示
        
        参数:
            base_prompt: 基础系统提示，如果为None则使用默认提示
            
        返回:
            格式化后的系统提示
        """
        if not self.state_manager:
            return base_prompt or "你是一个有用的助手。"
        
        # 修正: 直接访问 preferences 属性而不是使用不存在的 get_preference 方法
        system_prompt = base_prompt or self.state_manager.preferences.system_prompt
        
        # 修正: 直接访问 context 属性
        location = self.state_manager.context.location
        venue = self.state_manager.context.venue
        
        # 构建位置上下文
        location_context = f"用户当前位于{location}"
        if venue:
            location_context += f"的{venue}"
        
        # 组合系统提示
        formatted_prompt = f"{system_prompt}\n\n{location_context}。"
        
        return formatted_prompt
    
    def prepare_messages(self, 
                       conversation_messages: List[Dict[str, str]], 
                       system_prompt: str = None) -> List[Dict[str, str]]:
        """
        准备发送给模型的消息
        
        参数:
            conversation_messages: 对话历史消息
            system_prompt: 系统提示，如果为None则自动生成
            
        返回:
            准备好的消息列表
        """
        messages = []
        
        # 添加系统提示
        if system_prompt is None:
            system_prompt = self.format_system_prompt()
        
        messages.append({"role": "system", "content": system_prompt})
        
        # 添加对话历史
        messages.extend(conversation_messages)
        
        return messages

# 简单使用示例
if __name__ == "__main__":
    import asyncio
    
    async def main():
        # 初始化LLM接口
        llm = LLMInterface()
        
        # 同步方式
        messages = [
            {"role": "system", "content": "你是一个有用的助手。"},
            {"role": "user", "content": "你好，请介绍一下你自己。"}
        ]
        
        print("发送同步请求...")
        response = llm.generate_response(messages)
        print(f"同步响应: {response['content']}")
        
        # 异步方式
        print("\n发送异步请求...")
        async_response = await llm.generate_response_async(messages)
        print(f"异步响应: {async_response['content']}")
    
    # 运行示例
    asyncio.run(main()) 