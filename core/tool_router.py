"""
工具路由模块 - 负责根据意图调用相应的工具API
"""

import os
import json
import logging
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable
from enum import Enum
from contextlib import AsyncExitStack

# MCP相关导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# 导入核心组件
from core.intent_recognizer import Intent, Entity, IntentType

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("tool_router")

class ToolStatus(Enum):
    """工具执行状态"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"
    NOT_FOUND = "not_found"

class ToolResult:
    """工具执行结果"""
    def __init__(
        self,
        status: ToolStatus,
        data: Any = None,
        message: str = "",
        raw_response: Any = None
    ):
        self.status = status        # 执行状态
        self.data = data            # 处理后的数据
        self.message = message      # 状态消息
        self.raw_response = raw_response  # 原始响应
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "status": self.status.value,
            "data": self.data,
            "message": self.message
        }

class ToolRouter:
    """工具路由器 - 负责调用各种工具服务"""
    
    def __init__(self, state_manager=None, tools_dir=None):
        """
        初始化工具路由器
        
        参数:
            state_manager: 状态管理器实例，可为None
            tools_dir: 工具目录路径，默认为'tools'
        """
        self.state_manager = state_manager
        self.tools_dir = tools_dir or os.path.join(os.path.dirname(os.path.dirname(__file__)), 'tools')
        self.exit_stack = AsyncExitStack()
        self.sessions = {}  # 存储工具会话
        
        # 工具映射表
        self.tool_mapping = {
            "weather": {
                "script": "weatherMCP.py",
                "methods": {
                    "query_weather": self._map_weather_params,
                }
            },
            "market": {
                "script": "marketMCP.py",
                "methods": {
                    "find_product": self._map_market_params,
                    "list_category": self._map_market_category_params,
                }
            },
            "area_search": {
                "script": "areaSearchMCP.py",
                "methods": {
                    "search_nearby": self._map_area_search_params,
                    "search_nearby_food": self._map_area_search_params,
                    "search_nearby_shopping": self._map_area_search_params,
                    "search_nearby_entertainment": self._map_area_search_params,
                }
            }
        }
        
        logger.info(f"工具路由器初始化完成，工具目录: {self.tools_dir}")
    
    async def initialize(self):
        """初始化所有工具连接"""
        for tool_name, tool_info in self.tool_mapping.items():
            await self._connect_to_tool(tool_name, tool_info["script"])
    
    async def _connect_to_tool(self, tool_name: str, script_filename: str):
        """连接到指定的工具"""
        try:
            script_path = os.path.join(self.tools_dir, script_filename)
            if not os.path.exists(script_path):
                logger.error(f"工具脚本不存在: {script_path}")
                return
            
            is_python = script_path.endswith('.py')
            command = "python" if is_python else "node"
            
            server_params = StdioServerParameters(
                command=command,
                args=[script_path],
                env=None
            )
            
            # 启动工具服务器并建立通信
            stdio_transport = await self.exit_stack.enter_async_context(stdio_client(server_params))
            stdio, write = stdio_transport
            session = await self.exit_stack.enter_async_context(ClientSession(stdio, write))
            
            # 初始化会话
            await session.initialize()
            
            # 列出工具的可用方法
            response = await session.list_tools()
            tools = response.tools
            
            # 存储会话和工具
            self.sessions[tool_name] = {
                "session": session,
                "tools": tools
            }
            
            logger.info(f"已连接到工具 {tool_name}，支持的方法: {[tool.name for tool in tools]}")
            
        except Exception as e:
            logger.error(f"连接工具 {tool_name} 失败: {str(e)}")
    
    async def execute_tool_async(self, intent: Intent) -> ToolResult:
        """
        异步执行工具
        
        参数:
            intent: 意图对象
            
        返回:
            工具执行结果
        """
        tool_name = intent.tool_name
        
        # 检查工具是否已注册
        if tool_name not in self.tool_mapping:
            logger.warning(f"未知工具: {tool_name}")
            return ToolResult(
                status=ToolStatus.NOT_FOUND,
                message=f"未知工具: {tool_name}"
            )
        
        # 检查工具是否已连接
        if tool_name not in self.sessions:
            # 尝试连接工具
            await self._connect_to_tool(tool_name, self.tool_mapping[tool_name]["script"])
            
            # 再次检查是否连接成功
            if tool_name not in self.sessions:
                return ToolResult(
                    status=ToolStatus.ERROR,
                    message=f"无法连接到工具: {tool_name}"
                )
        
        # 获取会话
        session_data = self.sessions[tool_name]
        session = session_data["session"]
        available_tools = session_data["tools"]
        
        # 根据意图选择合适的方法
        method_name, params = self._select_method_and_params(intent, tool_name)
        
        # 检查方法是否可用
        available_method_names = [tool.name for tool in available_tools]
        if method_name not in available_method_names:
            logger.warning(f"工具 {tool_name} 不支持方法: {method_name}")
            logger.info(f"可用方法: {available_method_names}")
            return ToolResult(
                status=ToolStatus.ERROR,
                message=f"工具 {tool_name} 不支持方法: {method_name}"
            )
            
        try:
            # 调用工具方法
            logger.info(f"执行工具: {tool_name}.{method_name}，参数: {params}")
            result = await session.call_tool(method_name, params)
            
            # 提取结果文本
            result_text = result.content[0].text if result.content else ""
            
            return ToolResult(
                status=ToolStatus.SUCCESS,
                data=result_text,
                message="工具执行成功",
                raw_response=result
            )
        except Exception as e:
            logger.error(f"执行工具 {tool_name}.{method_name} 时发生错误: {str(e)}")
            return ToolResult(
                status=ToolStatus.ERROR,
                message=f"工具执行异常: {str(e)}"
            )
    
    def execute_tool(self, intent: Intent) -> ToolResult:
        """
        同步执行工具
        
        参数:
            intent: 意图对象
            
        返回:
            工具执行结果
        """
        return asyncio.run(self.execute_tool_async(intent))
    
    def _select_method_and_params(self, intent: Intent, tool_name: str) -> tuple[str, Dict[str, Any]]:
        """
        根据意图选择合适的方法和参数
        
        参数:
            intent: 意图对象
            tool_name: 工具名称
            
        返回:
            (方法名, 参数字典)
        """
        # 提取原始参数
        raw_params = self._extract_params_from_intent(intent)
        
        # 针对不同工具选择方法
        if tool_name == "weather":
            # 天气工具只有一个方法
            method_name = "query_weather"
            params = self._map_weather_params(intent, raw_params)
        
        elif tool_name == "market":
            # 根据意图选择商场工具方法
            if "category" in raw_params:
                method_name = "list_category"
                params = self._map_market_category_params(intent, raw_params)
            else:
                method_name = "find_product"
                params = self._map_market_params(intent, raw_params)
        
        elif tool_name == "area_search":
            # 根据意图选择区域搜索方法
            poi_type = raw_params.get("poi_type", "").lower()
            if poi_type == "restaurant" or "食" in intent.raw_query:
                method_name = "search_nearby_food"
            elif poi_type == "shopping" or "购物" in intent.raw_query:
                method_name = "search_nearby_shopping"
            elif poi_type == "entertainment" or "娱乐" in intent.raw_query:
                method_name = "search_nearby_entertainment"
            else:
                method_name = "search_nearby"
            
            params = self._map_area_search_params(intent, raw_params)
        
        else:
            # 默认情况
            method_name = list(self.tool_mapping[tool_name]["methods"].keys())[0]
            params = raw_params
        
        return method_name, params
    
    def _extract_params_from_intent(self, intent: Intent) -> Dict[str, Any]:
        """从意图中提取参数"""
        params = {}
        
        # 从意图实体中提取参数
        for entity in intent.entities:
            params[entity.type] = entity.value
        
        # 如果有状态管理器，尝试提取上下文信息
        if self.state_manager:
            # 检查是否需要位置信息
            if intent.tool_name == "weather" and "location" not in params:
                # 使用状态管理器的context对象属性
                location = self.state_manager.context.location
                if location:
                    params["location"] = location
            
            # 检查是否需要场所信息
            if intent.tool_name == "area_search" and "venue" not in params:
                venue = self.state_manager.context.venue
                if venue:
                    params["venue"] = venue
        
        return params
    
    def _map_weather_params(self, intent: Intent, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """映射天气工具参数"""
        params = {}
        
        # 提取城市
        location = None
        
        # 从意图参数中获取位置
        if "location" in raw_params:
            location = raw_params["location"]
        # 从意图实体中获取位置
        elif intent and intent.entities:
            for entity in intent.entities:
                if entity.type.lower() in ["location", "city", "place"]:
                    location = entity.value
                    break
        # 使用状态管理器中的当前位置
        elif self.state_manager:
            location = getattr(self.state_manager, "context", {}).get("location", "")
            if not location and hasattr(self.state_manager, "get_global_context"):
                context = self.state_manager.get_global_context()
                location = context.get("location", "")
        
        # 默认位置
        if not location:
            location = "重庆"
        
        # 处理中文地名，转换为API可接受的英文格式
        
        # 首先清理地名
        cleaned_location = location
        for suffix in ["市", "区", "县", "镇", "省"]:
            cleaned_location = cleaned_location.replace(suffix, "")
        
        # 中文地名映射表（扩展更多城市）
        location_mapping = {
            "重庆": "Chongqing",
            "永川": "Yongchuan",
            "北京": "Beijing",
            "上海": "Shanghai",
            "广州": "Guangzhou",
            "深圳": "Shenzhen",
            "成都": "Chengdu",
            "杭州": "Hangzhou",
            "南京": "Nanjing",
            "武汉": "Wuhan",
            "西安": "Xian",
            "天津": "Tianjin",
            "苏州": "Suzhou",
            "长沙": "Changsha",
            "郑州": "Zhengzhou",
            "青岛": "Qingdao",
            "大连": "Dalian",
            "沈阳": "Shenyang",
            "哈尔滨": "Harbin",
            "济南": "Jinan",
            "昆明": "Kunming",
            "厦门": "Xiamen",
            "福州": "Fuzhou",
            "南宁": "Nanning",
            "贵阳": "Guiyang",
            "兰州": "Lanzhou",
        }
        
        # 先尝试完整地名匹配
        if location in location_mapping:
            params["city"] = location_mapping[location]
        # 然后尝试清理后的地名匹配
        elif cleaned_location in location_mapping:
            params["city"] = location_mapping[cleaned_location]
        # 再尝试提取主要城市名
        else:
            # 提取可能包含的城市名
            for city_name in location_mapping.keys():
                if city_name in location or city_name in cleaned_location:
                    params["city"] = location_mapping[city_name]
                    break
            # 如果所有匹配都失败，使用默认值
            if "city" not in params:
                print(f"⚠️ 无法识别的地名: {location}，使用默认值 'Chongqing'")
                params["city"] = "Chongqing"
        
        # 打印调试信息
        print(f"✅ 地名转换: '{location}' → '{params['city']}'")
        
        return params
    
    def _map_market_params(self, intent: Intent, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """映射商场工具参数"""
        params = {
            "query": intent.raw_query
        }
        
        # 提取商品名称
        if "product" in raw_params:
            params["query"] = raw_params["product"]
        
        return params
    
    def _map_market_category_params(self, intent: Intent, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """映射商场分类工具参数"""
        params = {"category": "饮料"}  # 默认分类
        
        # 提取分类
        if "category" in raw_params:
            params["category"] = raw_params["category"]
        
        return params
    
    def _map_area_search_params(self, intent: Intent, raw_params: Dict[str, Any]) -> Dict[str, Any]:
        """映射区域搜索工具参数"""
        # 默认参数
        params = {"radius": 3000}
        
        # 根据POI类型确定其他参数
        if "query" in raw_params:
            params["keyword"] = raw_params["query"]
        
        # 提取POI类型
        if "poi_type" in raw_params:
            poi_type = raw_params["poi_type"]
            type_mapping = {
                "restaurant": "050000",  # 餐饮
                "shopping": "060000",    # 购物
                "entertainment": "080000"  # 休闲娱乐
            }
            if poi_type in type_mapping:
                params["type_code"] = type_mapping[poi_type]
        
        # 提取搜索半径
        if "radius" in raw_params:
            try:
                params["radius"] = int(raw_params["radius"])
            except ValueError:
                pass
        
        return params
    
    async def cleanup(self):
        """清理资源"""
        await self.exit_stack.aclose()


# 示例用法
if __name__ == "__main__":
    async def test_router():
        from core.intent_recognizer import Intent, Entity, IntentType
        
        # 创建工具路由器
        router = ToolRouter()
        await router.initialize()
        
        # 创建一个示例意图
        intent = Intent(
            intent_type=IntentType.QUERY,
            confidence=0.95,
            tool_name="weather",
            raw_query="重庆明天天气怎么样？"
        )
        intent.add_entity(Entity("location", "重庆", 0.98))
        intent.add_entity(Entity("time", "明天", 0.95))
        
        # 执行工具
        result = await router.execute_tool_async(intent)
        print(f"工具执行结果: {result}")
        print(f"数据: {result.data}")
        
        # 清理资源
        await router.cleanup()
    
    asyncio.run(test_router()) 