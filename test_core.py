"""
核心组件集成测试 - 测试状态管理器、对话管理器、LLM接口和意图识别器的基本功能
"""
import os
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv

# 导入核心组件
from core.state_manager import StateManager, UIState, UserPreferences, GlobalContext
from core.conversation_manager import ConversationManager, Message
from core.llm_interface import LLMInterface
from core.intent_recognizer import IntentRecognizer, Intent, IntentType
from core.intent_cache import get_intent_cache

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("core_test")

async def test_components():
    """测试核心组件的集成"""
    logger.info("开始核心组件集成测试")
    
    # 1. 初始化状态管理器
    state_manager = StateManager()
    
    # 设置一些初始状态
    state_manager.set_preference("system_prompt", "你是一个乐于助人的智能助手。")
    state_manager.set_context("location", "重庆市")
    state_manager.set_context("venue", "时代天街")
    
    # 2. 初始化对话管理器
    conversation = ConversationManager()
    
    # 3. 初始化LLM接口
    llm = LLMInterface(state_manager=state_manager)
    
    # 4. 初始化意图识别器
    intent_recognizer = IntentRecognizer(llm, state_manager, use_cache=True)
    
    # 获取缓存实例
    cache = get_intent_cache()
    cache_stats = {"hits": 0, "misses": 0}
    
    # 5. 简单的交互循环
    print("\n===== 核心组件集成测试 =====")
    print("输入'退出'结束测试")
    print("输入'测试意图'进入意图识别测试模式")
    print("输入'缓存状态'查看意图缓存统计")
    
    conversation_id = None
    intent_test_mode = False
    
    while True:
        # 获取用户输入
        if intent_test_mode:
            user_input = input("\n请输入要识别意图的文本 (输入'退出意图测试'返回正常模式): ")
            if user_input.lower() == '退出意图测试':
                intent_test_mode = False
                print("已退出意图测试模式，返回正常对话模式")
                continue
        else:
            user_input = input("\n请输入问题: ")
        
        if user_input.lower() in ['退出', 'exit', 'quit']:
            # 退出前保存缓存
            intent_recognizer.save_cache()
            break
            
        if user_input.lower() == '测试意图' and not intent_test_mode:
            intent_test_mode = True
            print("\n===== 进入意图识别测试模式 =====")
            continue
            
        if user_input.lower() == '缓存状态':
            cache_entries = len(cache.exact_cache) if cache else 0
            hit_rate = 0
            if (cache_stats['hits'] + cache_stats['misses']) > 0:
                hit_rate = cache_stats['hits'] / (cache_stats['hits'] + cache_stats['misses']) * 100
                
            print(f"\n===== 意图缓存状态 =====")
            print(f"缓存条目数: {cache_entries}")
            print(f"缓存命中率: {hit_rate:.2f}% ({cache_stats['hits']}命中 / {cache_stats['hits'] + cache_stats['misses']}总查询)")
            continue
        
        try:
            # 记录缓存查询前状态
            before_entries = len(cache.exact_cache) if cache else 0
            
            if intent_test_mode:
                # 意图测试模式：识别用户输入的意图
                print("正在识别意图...")
                
                # 获取对话历史作为上下文
                history = conversation.get_messages()
                formatted_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in history[-3:] if history  # 只使用最近3条消息
                ]
                
                # 识别意图
                intent = intent_recognizer.recognize(user_input, formatted_history if formatted_history else None)
                
                # 检测是否命中缓存
                after_entries = len(cache.exact_cache) if cache else 0
                is_cache_hit = before_entries == after_entries and after_entries > 0
                
                if is_cache_hit:
                    cache_stats["hits"] += 1
                else:
                    cache_stats["misses"] += 1
                
                # 显示意图识别结果
                print(f"\n===== 意图识别结果 =====")
                print(f"意图类型: {intent.type.name}")
                print(f"置信度: {intent.confidence:.2f}")
                print(f"推荐工具: {intent.tool_name or '无'}")
                print(f"缓存状态: {'命中' if is_cache_hit else '未命中'}")
                
                if intent.entities:
                    print("\n识别的实体:")
                    for entity in intent.entities:
                        print(f"  - {entity.type}: {entity.value} (置信度: {entity.confidence:.2f})")
                else:
                    print("\n未识别到实体")
                
                # 不将测试内容添加到对话历史
            else:
                # 正常对话模式
                # 添加用户消息到对话
                conversation.add_message(role="user", content=user_input)
                
                # 识别意图（可选，展示结果但不直接使用）
                intent = intent_recognizer.recognize(user_input)
                
                # 检测是否命中缓存
                after_entries = len(cache.exact_cache) if cache else 0
                is_cache_hit = before_entries == after_entries and before_entries > 0
                
                if is_cache_hit:
                    cache_stats["hits"] += 1
                else:
                    cache_stats["misses"] += 1
                
                print(f"\n[意图识别]: {intent.type.name}, 工具: {intent.tool_name or '无'}, 置信度: {intent.confidence:.2f}")
                print(f"[缓存状态]: {'命中' if is_cache_hit else '未命中'}")
                
                # 获取对话历史
                history = conversation.get_messages()
                
                # 格式化为LLM接口需要的格式
                formatted_history = [
                    {"role": msg.role, "content": msg.content}
                    for msg in history
                ]
                
                # 准备完整消息（添加系统提示）
                prepared_messages = llm.prepare_messages(formatted_history)
                
                # 生成回复
                print("正在生成回复...")
                response = await llm.generate_response_async(prepared_messages)
                
                # 提取回复内容
                assistant_content = response["content"]
                
                # 添加助手消息到对话
                conversation.add_message(role="assistant", content=assistant_content)
                
                # 显示回复
                print(f"\n[助手回复]: {assistant_content}")
                
                # 输出当前对话统计
                print(f"\n当前会话消息数: {len(history) + 1}")  # +1 表示新添加的助手消息
            
        except Exception as e:
            logger.error(f"处理请求时出错: {str(e)}")
            print(f"\n[错误]: {str(e)}")

async def main():
    """主函数"""
    # 加载环境变量
    load_dotenv()
    
    try:
        await test_components()
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        logger.error(f"测试过程中出现错误: {str(e)}")
        print(f"\n测试失败: {str(e)}")
    finally:
        print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(main()) 