"""
会话管理模块 - 负责存储和管理对话历史
"""
import time
import uuid
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field


@dataclass
class Message:
    """单条消息的数据结构"""
    role: str  # 'user', 'assistant', 'system'
    content: str
    timestamp: float = field(default_factory=time.time)
    message_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    metadata: Dict[str, Any] = field(default_factory=dict)  # 可存储额外信息，如工具调用结果


class ConversationManager:
    """
    会话管理器：负责存储和管理对话历史
    """
    def __init__(
        self, 
        conversation_id: Optional[str] = None,
        max_history_length: int = 20,
        system_prompt: Optional[str] = None
    ):
        """
        初始化会话管理器
        
        参数:
            conversation_id: 会话ID，如果为None则自动生成
            max_history_length: 历史记录最大长度（消息数量）
            system_prompt: 系统提示信息
        """
        self.conversation_id = conversation_id or str(uuid.uuid4())
        self.max_history_length = max_history_length
        self.messages: List[Message] = []
        self.created_at = time.time()
        self.last_updated_at = self.created_at
        
        # 设置系统提示（如果有）
        if system_prompt:
            self.add_system_message(system_prompt)
    
    def add_message(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """
        添加消息到历史记录
        
        参数:
            role: 消息角色 ('user', 'assistant', 'system')
            content: 消息内容
            metadata: 消息相关的元数据
            
        返回:
            新添加的消息对象
        """
        message = Message(
            role=role,
            content=content,
            metadata=metadata or {}
        )
        
        self.messages.append(message)
        self.last_updated_at = time.time()
        
        # 如果超出最大历史长度，移除最早的非系统消息
        if len(self.messages) > self.max_history_length:
            # 查找第一个非系统消息
            for i, msg in enumerate(self.messages):
                if msg.role != 'system':
                    self.messages.pop(i)
                    break
        
        return message
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加用户消息"""
        return self.add_message('user', content, metadata)
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加助手消息"""
        return self.add_message('assistant', content, metadata)
    
    def add_system_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> Message:
        """添加系统消息"""
        return self.add_message('system', content, metadata)
    
    def get_messages(self, include_system: bool = True) -> List[Message]:
        """
        获取所有消息
        
        参数:
            include_system: 是否包含系统消息
            
        返回:
            消息列表
        """
        if include_system:
            return self.messages.copy()
        else:
            return [msg for msg in self.messages if msg.role != 'system']
    
    def get_formatted_messages(self) -> List[Dict[str, str]]:
        """
        获取格式化后的消息，适合发送给语言模型
        
        返回:
            格式化为[{"role": "...", "content": "..."}]形式的消息列表
        """
        return [{"role": msg.role, "content": msg.content} for msg in self.messages]
    
    def clear_history(self, keep_system_messages: bool = True) -> None:
        """
        清除历史记录
        
        参数:
            keep_system_messages: 是否保留系统消息
        """
        if keep_system_messages:
            self.messages = [msg for msg in self.messages if msg.role == 'system']
        else:
            self.messages = []
        
        self.last_updated_at = time.time()
    
    def get_last_message(self) -> Optional[Message]:
        """获取最后一条消息"""
        if not self.messages:
            return None
        return self.messages[-1]
    
    def get_conversation_summary(self) -> Dict[str, Any]:
        """
        获取会话摘要信息
        
        返回:
            包含会话ID、创建时间、消息数量等信息的字典
        """
        return {
            "conversation_id": self.conversation_id,
            "created_at": self.created_at,
            "last_updated_at": self.last_updated_at,
            "message_count": len(self.messages),
            "user_message_count": sum(1 for msg in self.messages if msg.role == 'user'),
            "assistant_message_count": sum(1 for msg in self.messages if msg.role == 'assistant')
        }
    
    # 预留持久化方法
    def save_to_file(self, file_path: str) -> bool:
        """
        将会话保存到文件（留作未来实现）
        
        参数:
            file_path: 文件路径
            
        返回:
            是否保存成功
        """
        # 这里预留接口，未来实现持久化功能
        # 可以使用JSON或其他格式保存会话内容
        return False
    
    @classmethod
    def load_from_file(cls, file_path: str) -> Optional['ConversationManager']:
        """
        从文件加载会话（留作未来实现）
        
        参数:
            file_path: 文件路径
            
        返回:
            加载的会话管理器实例，如果加载失败则返回None
        """
        # 这里预留接口，未来实现持久化功能
        return None


# 示例用法
if __name__ == "__main__":
    # 创建会话
    conversation = ConversationManager(system_prompt="你是一个有用的助手。")
    
    # 添加消息
    conversation.add_user_message("你好！")
    conversation.add_assistant_message("你好！有什么我可以帮助你的？")
    
    # 获取格式化消息
    formatted_messages = conversation.get_formatted_messages()
    print(formatted_messages) 