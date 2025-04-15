"""
状态管理模块 - 负责管理应用全局状态、用户偏好和UI状态
"""
import os
import json
import logging
from typing import Dict, Any, List, Callable, Optional, Set
from pathlib import Path
from dataclasses import dataclass, field, asdict


class Observable:
    """
    可观察对象基类，实现发布-订阅模式
    """
    def __init__(self):
        # 存储观察者函数和它们关注的路径
        self._observers: Dict[str, List[Callable]] = {}
        
    def subscribe(self, path: str, callback: Callable) -> None:
        """
        订阅状态变化
        
        参数:
            path: 状态路径，例如 "ui.chat_window.is_visible"
            callback: 当状态变化时调用的回调函数，接收新值和旧值作为参数
        """
        if path not in self._observers:
            self._observers[path] = []
        if callback not in self._observers[path]:
            self._observers[path] = self._observers.get(path, []) + [callback]
            
    def unsubscribe(self, path: str, callback: Callable) -> None:
        """
        取消订阅状态变化
        
        参数:
            path: 状态路径
            callback: 之前注册的回调函数
        """
        if path in self._observers and callback in self._observers[path]:
            self._observers[path].remove(callback)
            
    def notify(self, path: str, new_value: Any, old_value: Any = None) -> None:
        """
        通知所有订阅了指定路径的观察者
        
        参数:
            path: 发生变化的状态路径
            new_value: 新状态值
            old_value: 旧状态值
        """
        # 通知精确路径的观察者
        if path in self._observers:
            for callback in self._observers[path]:
                callback(new_value, old_value)
                
        # 通知通配符观察者（例如 "ui.*" 会匹配 "ui.any.path"）
        for observer_path, callbacks in self._observers.items():
            if '*' in observer_path:
                pattern = observer_path.replace('*', '')
                if path.startswith(pattern):
                    for callback in callbacks:
                        callback(new_value, old_value)


@dataclass
class UIState:
    """UI组件状态"""
    is_chat_visible: bool = True
    is_sidebar_visible: bool = True
    is_loading: bool = False
    current_tab: str = "chat"
    theme: str = "light"
    font_size: int = 14


@dataclass
class UserPreferences:
    """用户偏好设置"""
    max_history_length: int = 50
    system_prompt: str = "你是一个有用的助手。"# 在llminterface里的format_system_prompt方法里引用
    location: str = "重庆市永川区"
    venue: str = "时代天街"
    theme: str = "light"
    auto_save: bool = True
    tools_enabled: Dict[str, bool] = field(default_factory=lambda: {
        "weather": True,
        "market": True,
        "area_search": True
    })


@dataclass
class GlobalContext:
    """全局上下文信息"""
    current_conversation_id: Optional[str] = None
    active_tools: List[str] = field(default_factory=list)
    tool_execution_history: List[Dict[str, Any]] = field(default_factory=list)
    location: str = "重庆市永川区"
    venue: str = "时代天街"
    last_query_time: Optional[float] = None


class StateManager(Observable):
    """
    状态管理器：负责管理应用全局状态、UI状态和用户偏好
    实现了观察者模式，允许其他组件订阅状态变化
    """
    def __init__(self, config_dir: str = "config"):
        super().__init__()
        
        # 确保配置目录存在
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)
        
        # 初始化状态
        self.ui = UIState()
        self.preferences = UserPreferences()
        self.context = GlobalContext()
        
        # 加载状态
        self.load_state()
        
        logging.debug("状态管理器初始化完成")
    
    def set_ui_state(self, path: str, value: Any) -> None:
        """
        设置UI状态
        
        参数:
            path: 状态路径，例如 "is_chat_visible"
            value: 新状态值
        """
        # 分解路径
        old_value = self._get_attribute(self.ui, path)
        self._set_attribute(self.ui, path, value)
        
        # 通知观察者
        full_path = f"ui.{path}"
        self.notify(full_path, value, old_value)
        
    def set_preference(self, path: str, value: Any) -> None:
        """
        设置用户偏好
        
        参数:
            path: 偏好路径，例如 "theme"
            value: 新偏好值
        """
        old_value = self._get_attribute(self.preferences, path)
        self._set_attribute(self.preferences, path, value)
        
        # 通知观察者
        full_path = f"preferences.{path}"
        self.notify(full_path, value, old_value)
        
        # 自动保存（如果启用）
        if self.preferences.auto_save:
            self.save_preferences()
            
    def set_context(self, path: str, value: Any) -> None:
        """
        设置全局上下文
        
        参数:
            path: 上下文路径，例如 "location"
            value: 新上下文值
        """
        old_value = self._get_attribute(self.context, path)
        self._set_attribute(self.context, path, value)
        
        # 通知观察者
        full_path = f"context.{path}"
        self.notify(full_path, value, old_value)
    
    def _get_attribute(self, obj: Any, path: str) -> Any:
        """
        获取对象的嵌套属性
        
        参数:
            obj: 目标对象
            path: 属性路径，例如 "theme" 或 "tools_enabled.weather"
            
        返回:
            属性值
        """
        current = obj
        for part in path.split('.'):
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return None
        return current
    
    def _set_attribute(self, obj: Any, path: str, value: Any) -> None:
        """
        设置对象的嵌套属性
        
        参数:
            obj: 目标对象
            path: 属性路径，例如 "theme" 或 "tools_enabled.weather"
            value: 新属性值
        """
        parts = path.split('.')
        current = obj
        
        # 处理除最后一部分外的路径
        for i, part in enumerate(parts[:-1]):
            if hasattr(current, part):
                current = getattr(current, part)
            elif isinstance(current, dict) and part in current:
                current = current[part]
            else:
                # 如果中间路径不存在，根据下一部分是数字还是字符串创建列表或字典
                next_part = parts[i + 1]
                if next_part.isdigit():
                    setattr(current, part, [])
                    current = getattr(current, part)
                else:
                    setattr(current, part, {})
                    current = getattr(current, part)
        
        # 设置最终属性
        last_part = parts[-1]
        if hasattr(current, last_part):
            setattr(current, last_part, value)
        elif isinstance(current, dict):
            current[last_part] = value
        else:
            setattr(current, last_part, value)
    
    def save_state(self) -> None:
        """保存所有状态到文件"""
        self.save_preferences()
        self.save_ui_state()
        
    def load_state(self) -> None:
        """从文件加载所有状态"""
        self.load_preferences()
        self.load_ui_state()
    
    def save_preferences(self) -> None:
        """保存用户偏好到文件"""
        prefs_path = self.config_dir / "preferences.json"
        try:
            with open(prefs_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.preferences), f, ensure_ascii=False, indent=2)
            logging.debug("用户偏好已保存")
        except Exception as e:
            logging.error(f"保存用户偏好失败: {e}")
    
    def load_preferences(self) -> None:
        """从文件加载用户偏好"""
        prefs_path = self.config_dir / "preferences.json"
        if prefs_path.exists():
            try:
                with open(prefs_path, 'r', encoding='utf-8') as f:
                    prefs_dict = json.load(f)
                
                # 更新偏好，但只更新存在的字段
                for key, value in prefs_dict.items():
                    if hasattr(self.preferences, key):
                        setattr(self.preferences, key, value)
                
                logging.debug("用户偏好已加载")
            except Exception as e:
                logging.error(f"加载用户偏好失败: {e}")
    
    def save_ui_state(self) -> None:
        """保存UI状态到文件"""
        ui_path = self.config_dir / "ui_state.json"
        try:
            with open(ui_path, 'w', encoding='utf-8') as f:
                json.dump(asdict(self.ui), f, ensure_ascii=False, indent=2)
            logging.debug("UI状态已保存")
        except Exception as e:
            logging.error(f"保存UI状态失败: {e}")
    
    def load_ui_state(self) -> None:
        """从文件加载UI状态"""
        ui_path = self.config_dir / "ui_state.json"
        if ui_path.exists():
            try:
                with open(ui_path, 'r', encoding='utf-8') as f:
                    ui_dict = json.load(f)
                
                # 更新UI状态，但只更新存在的字段
                for key, value in ui_dict.items():
                    if hasattr(self.ui, key):
                        setattr(self.ui, key, value)
                
                logging.debug("UI状态已加载")
            except Exception as e:
                logging.error(f"加载UI状态失败: {e}")
    
    def get_current_location(self) -> Dict[str, str]:
        """获取当前位置信息"""
        return {
            "location": self.context.location,
            "venue": self.context.venue
        }
    
    def get_enabled_tools(self) -> List[str]:
        """获取已启用的工具列表"""
        return [name for name, enabled in self.preferences.tools_enabled.items() if enabled]
    
    def reset_to_defaults(self) -> None:
        """重置所有设置为默认值"""
        self.ui = UIState()
        self.preferences = UserPreferences()
        self.notify("preferences", self.preferences)
        self.notify("ui", self.ui)
        self.save_state()


# 示例用法
if __name__ == "__main__":
    # 配置日志
    logging.basicConfig(level=logging.DEBUG)
    
    # 创建状态管理器
    state_manager = StateManager()
    
    # 定义状态变化的回调
    def on_theme_change(new_value, old_value):
        print(f"主题从 {old_value} 变为 {new_value}")
    
    # 订阅状态变化
    state_manager.subscribe("preferences.theme", on_theme_change)
    
    # 修改状态
    state_manager.set_preference("theme", "dark")
    
    # 设置上下文
    state_manager.set_context("location", "重庆市渝北区")
    
    # 保存状态
    state_manager.save_state() 