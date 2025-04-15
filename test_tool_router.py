"""
工具路由测试 - 测试工具路由器的基本功能
"""
import os
import json
import logging
import asyncio
from dotenv import load_dotenv

# 导入核心组件
from core.intent_recognizer import Intent, Entity, IntentType
from core.tool_router import ToolRouter, ToolStatus
from core.state_manager import StateManager

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("tool_router_test")

async def test_tool_router():
    """测试工具路由器"""
    logger.info("开始工具路由器测试")
    
    # 加载环境变量
    load_dotenv()
    
    # 初始化状态管理器
    state_manager = StateManager()
    
    # 初始化工具路由器
    router = ToolRouter(state_manager=state_manager)
    
    # 初始化所有工具连接
    await router.initialize()
    
    try:
        # 测试天气工具
        weather_intent = Intent(
            intent_type=IntentType.QUERY,
            confidence=0.95,
            tool_name="weather",
            raw_query="重庆明天天气怎么样？"
        )
        weather_intent.add_entity(Entity("location", "重庆", 0.98))
        weather_intent.add_entity(Entity("time", "明天", 0.95))
        
        print("\n=== 测试天气工具 ===")
        print(f"查询: {weather_intent.raw_query}")
        weather_result = await router.execute_tool_async(weather_intent)
        print(f"状态: {weather_result.status.value}")
        print(f"消息: {weather_result.message}")
        if weather_result.status == ToolStatus.SUCCESS:
            print(f"数据: {weather_result.data}")
        
        # 测试商场工具
        market_intent = Intent(
            intent_type=IntentType.QUERY,
            confidence=0.9,
            tool_name="market",
            raw_query="我想买可乐"
        )
        market_intent.add_entity(Entity("product", "可乐", 0.97))
        
        print("\n=== 测试商场工具 ===")
        print(f"查询: {market_intent.raw_query}")
        market_result = await router.execute_tool_async(market_intent)
        print(f"状态: {market_result.status.value}")
        print(f"消息: {market_result.message}")
        if market_result.status == ToolStatus.SUCCESS:
            print(f"数据: {market_result.data}")
        
        # 测试区域搜索工具
        area_intent = Intent(
            intent_type=IntentType.QUERY,
            confidence=0.85,
            tool_name="area_search",
            raw_query="附近有什么好吃的餐厅？"
        )
        area_intent.add_entity(Entity("poi_type", "restaurant", 0.9))
        
        print("\n=== 测试区域搜索工具 ===")
        print(f"查询: {area_intent.raw_query}")
        area_result = await router.execute_tool_async(area_intent)
        print(f"状态: {area_result.status.value}")
        print(f"消息: {area_result.message}")
        if area_result.status == ToolStatus.SUCCESS:
            print(f"数据: {area_result.data}")
        
        # 测试无效工具
        invalid_intent = Intent(
            intent_type=IntentType.QUERY,
            confidence=0.7,
            tool_name="invalid_tool",
            raw_query="使用一个不存在的工具"
        )
        
        print("\n=== 测试无效工具 ===")
        print(f"查询: {invalid_intent.raw_query}")
        invalid_result = await router.execute_tool_async(invalid_intent)
        print(f"状态: {invalid_result.status.value}")
        print(f"消息: {invalid_result.message}")
        
    finally:
        # 清理资源
        await router.cleanup()

if __name__ == "__main__":
    asyncio.run(test_tool_router()) 