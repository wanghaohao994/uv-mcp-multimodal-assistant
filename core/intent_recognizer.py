"""
意图识别模块 - 负责识别用户输入的意图和提取相关实体
"""

import re
import json
import logging
from typing import Dict, List, Any, Optional, Tuple, Set, Union
from enum import Enum, auto

# 导入核心组件
from core.llm_interface import LLMInterface
from core.state_manager import StateManager
from core.intent_cache import get_intent_cache

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intent_recognizer")

class IntentType(Enum):
    """意图类型枚举"""
    CHAT = auto()           # 闲聊，不需要特殊处理
    QUERY = auto()          # 信息查询，可能需要工具
    COMMAND = auto()        # 系统命令，如设置或控制
    TOOL_SPECIFIC = auto()  # 明确的工具调用
    UNKNOWN = auto()        # 无法识别的意图

class Entity:
    """提取的实体信息"""
    def __init__(self, entity_type: str, value: str, confidence: float = 1.0):
        self.type = entity_type  # 实体类型，如location, time, product等
        self.value = value       # 实体值
        self.confidence = confidence  # 置信度
    
    def __str__(self):
        return f"{self.type}:{self.value}({self.confidence:.2f})"
    
    def to_dict(self):
        return {
            "type": self.type,
            "value": self.value,
            "confidence": self.confidence
        }

class Intent:
    """意图识别结果"""
    def __init__(
        self,
        intent_type: IntentType,
        confidence: float,
        tool_name: Optional[str] = None,
        entities: Optional[List[Entity]] = None,
        raw_query: str = ""
    ):
        self.type = intent_type          # 意图类型
        self.confidence = confidence      # 置信度
        self.tool_name = tool_name        # 可能使用的工具
        self.entities = entities or []    # 提取的实体
        self.raw_query = raw_query        # 原始查询文本
    
    def add_entity(self, entity: Entity):
        """添加一个实体"""
        self.entities.append(entity)
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "type": self.type.name,
            "confidence": self.confidence,
            "tool_name": self.tool_name,
            "entities": [e.to_dict() for e in self.entities],
            "raw_query": self.raw_query
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Intent':
        """从字典创建意图对象"""
        # 解析意图类型
        intent_type = IntentType[data.get("type", "UNKNOWN")]
        
        # 创建意图对象
        intent = cls(
            intent_type=intent_type,
            confidence=float(data.get("confidence", 0.5)),
            tool_name=data.get("tool_name"),
            raw_query=data.get("raw_query", "")
        )
        
        # 添加实体
        if "entities" in data and isinstance(data["entities"], list):
            for entity_data in data["entities"]:
                entity = Entity(
                    entity_type=entity_data.get("type", "unknown"),
                    value=entity_data.get("value", ""),
                    confidence=float(entity_data.get("confidence", 0.5))
                )
                intent.add_entity(entity)
        
        return intent
    
    def __str__(self):
        entities_str = ", ".join(str(e) for e in self.entities)
        return (f"Intent[{self.type.name}] "
                f"tool:{self.tool_name or 'none'} "
                f"conf:{self.confidence:.2f} "
                f"entities:[{entities_str}]")


class IntentRecognizer:
    """
    意图识别器 - 使用规则和模型混合方式识别用户意图
    """
    
    # 工具关键词映射
    TOOL_KEYWORDS = {
        "weather": ["天气", "气温", "下雨", "温度", "湿度", "阴晴"],
        "market": ["商场", "商家", "店铺", "购物", "买东西", "超市", "专卖店"],
        "area_search": ["附近", "周边", "区域", "地方", "位置", "怎么走", "地址"]
    }
    
    # 命令关键词
    COMMAND_KEYWORDS = ["设置", "更改", "修改", "切换", "保存", "重置", "清除", "删除"]
    
    def __init__(self, llm_interface: LLMInterface, state_manager: StateManager, use_cache: bool = True):
        """
        初始化意图识别器
        
        参数:
            llm_interface: LLM接口实例，用于模型分析
            state_manager: 状态管理器实例
            use_cache: 是否使用缓存
        """
        self.llm = llm_interface
        self.state_manager = state_manager
        self.use_cache = use_cache
        
        # 初始化缓存
        self.cache = get_intent_cache() if use_cache else None
        
        logger.info(f"意图识别器初始化完成，{'启用' if use_cache else '禁用'}缓存")
    
    async def recognize(self, text: str) -> Intent:
        """
        识别用户文本的意图
        
        参数:
            text: 用户输入文本
            
        返回:
            Intent: 识别出的意图
        """
        # 检查缓存
        if self.use_cache:
            cached_intent = self.cache.lookup(text)
            if cached_intent:
                return Intent.from_dict(cached_intent)
        
        # 第一步：使用基于规则的识别
        rule_intent = self._apply_rules(text)
        
        # 如果规则识别结果足够确定（高置信度），直接返回
        if rule_intent and rule_intent.confidence > 0.8:
            # 更新缓存
            if self.use_cache:
                self.cache.add(text, rule_intent.to_dict())
            return rule_intent
        
        # 第二步：获取对话上下文
        conversation_context = None
        
        # 正确获取对话历史
        if hasattr(self, 'conversation_manager'):
            # 如果IntentRecognizer直接持有ConversationManager实例
            messages = self.conversation_manager.get_messages()
            # 取最近3条
            conversation_context = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages[-3:]
            ] if len(messages) > 0 else None
        elif hasattr(self.state_manager, 'conversation'):
            # 如果StateManager持有ConversationManager实例
            messages = self.state_manager.conversation.get_messages()
            # 取最近3条
            conversation_context = [
                {"role": msg.role, "content": msg.content} 
                for msg in messages[-3:]
            ] if len(messages) > 0 else None
        
        # 使用模型分析意图
        model_intent = await self._analyze_with_model(text, conversation_context)
        
        # 第三步：合并两种识别结果
        final_intent = self._merge_intents(
            rule_intent or Intent(IntentType.UNKNOWN, 0.0, raw_query=text),
            model_intent
        )
        
        # 更新缓存
        if self.use_cache:
            self.cache.add(text, final_intent.to_dict())
        
        return final_intent
    
    def _apply_rules(self, text: str) -> Optional[Intent]:
        """应用规则识别意图"""
        text = text.lower()
        
        # 检查是否是工具特定查询
        for tool_name, keywords in self.TOOL_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text:
                    confidence = 0.7  # 基础置信度
                    # 如果有多个关键词匹配，提高置信度
                    matched_keywords = sum(1 for kw in keywords if kw in text)
                    if matched_keywords > 1:
                        confidence = min(0.9, confidence + 0.1 * matched_keywords)
                    
                    # 创建意图对象
                    intent = Intent(
                        intent_type=IntentType.TOOL_SPECIFIC,
                        confidence=confidence,
                        tool_name=tool_name,
                        raw_query=text
                    )
                    
                    # 尝试提取基本实体
                    self._extract_basic_entities(text, intent)
                    return intent
        
        # 检查是否是命令
        if any(cmd in text for cmd in self.COMMAND_KEYWORDS):
            return Intent(
                intent_type=IntentType.COMMAND,
                confidence=0.65,
                raw_query=text
            )
        
        # 如果没有明确匹配，返回None让模型处理
        return None
    
    def _extract_basic_entities(self, text: str, intent: Intent) -> None:
        """使用基本规则提取实体"""
        # 示例：提取简单的位置信息
        location_patterns = [
            r'在([\w]+)',
            r'([\w]+)(附近|周边)',
            r'去([\w]+)'
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text)
            if match and match.group(1):
                location = match.group(1)
                intent.add_entity(Entity("location", location, 0.8))
                break
    
    async def _analyze_with_model(self, user_input: str, conversation_context: Optional[List[Dict[str, str]]] = None) -> Intent:
        """使用语言模型分析意图"""
        logger.debug("使用模型分析意图")
        
        # 构建模型提示
        system_prompt = """
        你是一个专门负责理解用户意图的AI助手。请分析用户输入并识别主要意图、需要使用的工具以及相关实体。
        
        请按照以下JSON格式输出：
        {
          "intent_type": "CHAT|QUERY|COMMAND|TOOL_SPECIFIC|UNKNOWN",
          "confidence": 0.0-1.0,
          "tool_name": "weather|market|area_search|null",
          "entities": [
            {"type": "实体类型(location|time|product等)", "value": "实体值", "confidence": 0.0-1.0}
          ],
          "reasoning": "你的分析理由"
        }
        
        意图类型说明：
        - CHAT: 闲聊，不需要特殊工具
        - QUERY: 信息查询，可能需要工具
        - COMMAND: 系统命令，如设置或控制
        - TOOL_SPECIFIC: 明确需要某个工具
        - UNKNOWN: 无法确定意图
        
        可用工具：
        - weather: 天气查询工具
        - market: 商场和商家信息查询
        - area_search: 区域和位置搜索
        
        分析要准确、合理，不要过度解读，只输出JSON。
        """
        
        # 准备消息
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"请分析以下用户输入的意图:\n\"{user_input}\""}
        ]
        
        # 如果有对话上下文，添加到消息中
        if conversation_context and len(conversation_context) > 0:
            context_message = "对话上下文:\n"
            for i, msg in enumerate(conversation_context[-3:]):  # 只使用最近3条
                context_message += f"{msg['role']}: {msg['content']}\n"
            
            messages.append({"role": "user", "content": context_message})
        
        try:
            # 调用模型
            response = await self.llm.generate_response_async(messages)
            result_text = response["content"]
            
            # 提取JSON
            json_match = re.search(r'({[^{}]*({[^{}]*})*[^{}]*})', result_text)
            if json_match:
                result_json = json.loads(json_match.group(1))
                return self._parse_model_result(result_json, user_input)
            else:
                logger.warning(f"模型未返回有效JSON: {result_text}")
                # 返回默认意图
                return Intent(IntentType.UNKNOWN, 0.3, raw_query=user_input)
                
        except Exception as e:
            logger.error(f"使用模型分析意图时出错: {str(e)}")
            # 返回默认意图
            return Intent(IntentType.CHAT, 0.3, raw_query=user_input)
    
    def _parse_model_result(self, result: Dict[str, Any], raw_query: str) -> Intent:
        """解析模型返回的意图分析结果"""
        try:
            # 解析意图类型
            intent_type_str = result.get("intent_type", "UNKNOWN")
            intent_type = IntentType[intent_type_str] if intent_type_str in IntentType.__members__ else IntentType.UNKNOWN
            
            # 创建意图对象
            intent = Intent(
                intent_type=intent_type,
                confidence=float(result.get("confidence", 0.5)),
                tool_name=result.get("tool_name") if result.get("tool_name") != "null" else None,
                raw_query=raw_query
            )
            
            # 添加实体
            if "entities" in result and isinstance(result["entities"], list):
                for entity_data in result["entities"]:
                    entity = Entity(
                        entity_type=entity_data.get("type", "unknown"),
                        value=entity_data.get("value", ""),
                        confidence=float(entity_data.get("confidence", 0.5))
                    )
                    intent.add_entity(entity)
            
            return intent
            
        except Exception as e:
            logger.error(f"解析模型结果时出错: {str(e)}")
            return Intent(IntentType.UNKNOWN, 0.3, raw_query=raw_query)
    
    def _merge_intents(self, rule_intent: Intent, model_intent: Intent) -> Intent:
        """合并规则和模型识别的意图结果"""
        # 基于置信度选择意图类型
        intent_type = rule_intent.type if rule_intent.confidence > model_intent.confidence else model_intent.type
        
        # 选择置信度更高的工具
        if rule_intent.tool_name and model_intent.tool_name:
            tool_name = rule_intent.tool_name if rule_intent.confidence > 0.7 else model_intent.tool_name
        else:
            tool_name = rule_intent.tool_name or model_intent.tool_name
        
        # 创建合并后的意图
        merged_intent = Intent(
            intent_type=intent_type,
            confidence=max(rule_intent.confidence, model_intent.confidence),
            tool_name=tool_name,
            raw_query=rule_intent.raw_query
        )
        
        # 合并实体，去重
        entity_map = {}
        for entity in rule_intent.entities + model_intent.entities:
            key = f"{entity.type}:{entity.value}"
            if key not in entity_map or entity.confidence > entity_map[key].confidence:
                entity_map[key] = entity
        
        for entity in entity_map.values():
            merged_intent.add_entity(entity)
        
        return merged_intent
    
    def save_cache(self) -> None:
        """保存缓存到磁盘"""
        if self.use_cache:
            self.cache.save_cache(force=True)
            logger.info("意图缓存已保存")

# 示例用法
if __name__ == "__main__":
    from core.state_manager import StateManager
    from core.llm_interface import LLMInterface
    
    # 配置日志
    logging.basicConfig(level=logging.INFO)
    
    # 初始化组件
    state_manager = StateManager()
    llm = LLMInterface(state_manager=state_manager)
    
    # 创建意图识别器
    recognizer = IntentRecognizer(llm, state_manager)
    
    # 测试识别
    test_queries = [
        "你好，今天过得怎么样？",
        "重庆明天的天气怎么样？",
        "我想知道时代天街有哪些商场",
        "帮我设置主题为深色模式",
        "附近有什么好吃的餐厅？"
    ]
    
    for query in test_queries:
        intent = recognizer.recognize(query)
        print(f"查询: {query}")
        print(f"识别结果: {intent}")
        print("-" * 50)
    
    # 保存缓存
    recognizer.save_cache() 