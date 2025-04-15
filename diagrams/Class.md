classDiagram
    %% UI组件
    class ChatWindow {
        -RecordingThread recording_thread
        -TtsHelper tts_helper
        -MCPAssistant assistant
        +add_user_message(message)
        +add_assistant_message(message)
        +add_system_message(message)
        +send_message()
        +toggle_recording()
    }
    
    class RecordingThread {
        -is_recording: bool
        -model_name: str
        -model
        +run()
        +stop_recording()
    }
    
    class TtsHelper {
        +async play_text(text)
    }
    
    %% 核心助手
    class MCPAssistant {
        -state_manager: StateManager
        -conversation_manager: ConversationManager
        -intent_recognizer: IntentRecognizer
        -tool_router: ToolRouter
        -llm_interface: LLMInterface
        +async initialize()
        +async process_query(query)
        -async _handle_command(intent)
        -async _call_tool_and_respond(intent)
        -async _handle_general_chat(intent, query)
        +async cleanup()
    }
    
    %% 对话管理
    class ConversationManager {
        -conversation_id: str
        -messages: List[Message]
        -created_at: float
        -last_updated_at: float
        -max_history_length: int
        +add_message(role, content, metadata)
        +add_user_message(content, metadata)
        +add_assistant_message(content, metadata)
        +add_system_message(content, metadata)
        +get_messages(include_system)
        +get_formatted_messages()
        +clear_history(keep_system_messages)
        +get_last_message()
        +get_conversation_summary()
    }
    
    class Message {
        -role: str
        -content: str
        -metadata: Dict
        -timestamp: float
    }
    
    %% 意图识别
    class IntentRecognizer {
        -llm: LLMInterface
        -state_manager: StateManager
        -cache: IntentCache
        -rule_patterns: Dict
        -use_cache: bool
        +recognize(query)
        -_recognize_from_cache(query)
        -_recognize_with_llm(query)
        -_recognize_with_rules(query)
        -_merge_intents(rule_intent, model_intent)
    }
    
    class Intent {
        -type: IntentType
        -confidence: float
        -tool_name: str
        -entities: List[Entity]
        -raw_query: str
        +add_entity(entity)
        +get_entities_of_type(entity_type)
        +to_dict()
    }
    
    class Entity {
        -type: str
        -value: str
        -confidence: float
        +to_dict()
    }
    
    class IntentType {
        <<enumeration>>
        CHAT
        QUERY
        COMMAND
        TOOL_SPECIFIC
        UNKNOWN
    }
    
    class IntentCache {
        -cache_file: str
        -max_entries: int
        -exact_cache: Dict
        -keyword_index: Dict
        -last_save_time: float
        +find_intent(query)
        +add_intent(query, intent)
        +save_cache(force)
        -_extract_keywords(query)
        -_find_similar_query(query)
    }
    
    %% LLM接口
    class LLMInterface {
        -state_manager: StateManager
        -api_key: str
        -base_url: str
        -model: str
        -client: OpenAI
        -async_client: AsyncOpenAI
        +generate_response(messages)
        +async generate_response_async(messages)
        +format_system_prompt()
        +prepare_messages(conversation_messages, system_prompt)
    }
    
    %% 状态管理
    class Observable {
        -_observers: Dict[str, List[Callable]]
        +subscribe(path, callback)
        +unsubscribe(path, callback)
        +notify(path, new_value, old_value)
    }
    
    class StateManager {
        -ui: UIState
        -preferences: UserPreferences
        -context: ContextData
        -config_dir: Path
        +set_preference(key, value)
        +set_ui_state(key, value)
        +set_context(key, value)
        +save_state()
        +get_current_location()
        +get_enabled_tools()
    }
    
    class UIState {
        +theme: str
        +font_size: int
        +chat_width: int
        +chat_height: int
        +window_maximized: bool
    }
    
    class UserPreferences {
        +language: str
        +theme: str
        +voice_enabled: bool
        +voice_rate: int
        +voice_volume: float
        +tools_enabled: Dict[str, bool]
    }
    
    class ContextData {
        +location: str
        +venue: str
        +last_query_time: float
    }
    
    %% 工具路由
    class ToolRouter {
        -state_manager: StateManager
        -tools_dir: str
        -clients: Dict
        -exit_stack: AsyncExitStack
        +async initialize()
        +async execute_tool_async(intent)
        -async _connect_tool(tool_name)
        -_map_intent_to_tool_name(intent)
        -_map_intent_params(intent, tool_name)
        +async cleanup()
    }
    
    class ToolStatus {
        <<enumeration>>
        SUCCESS
        ERROR
        PENDING
        NOT_FOUND
    }
    
    class ToolResult {
        -status: ToolStatus
        -data: Any
        -message: str
        -raw_response: Any
        +to_dict()
    }
    
    %% 工具服务
    class WeatherServer {
        <<interface>>
        +async query_weather(city)
    }
    
    class MarketServer {
        <<interface>>
        +find_product(query)
        +list_category(category)
    }
    
    class AreaSearchServer {
        <<interface>>
        +async search_nearby(keyword, type_code, radius)
        +async search_nearby_food(radius)
        +async search_nearby_shopping(radius)
        +async search_nearby_entertainment(radius)
    }
    
    %% 关系定义
    ChatWindow "1" *-- "1" RecordingThread : 包含
    ChatWindow "1" *-- "1" TtsHelper : 包含
    ChatWindow "1" --> "1" MCPAssistant : 使用
    
    MCPAssistant "1" *-- "1" StateManager : 包含
    MCPAssistant "1" *-- "1" ConversationManager : 包含
    MCPAssistant "1" *-- "1" IntentRecognizer : 包含
    MCPAssistant "1" *-- "1" ToolRouter : 包含
    MCPAssistant "1" *-- "1" LLMInterface : 包含
    
    ConversationManager "1" *-- "*" Message : 包含
    
    IntentRecognizer "1" --> "1" LLMInterface : 使用
    IntentRecognizer "1" --> "1" StateManager : 使用
    IntentRecognizer "1" --> "1" IntentCache : 使用
    IntentRecognizer "1" --> "*" Intent : 创建
    
    Intent "1" *-- "*" Entity : 包含
    Intent "1" --> "1" IntentType : 使用
    
    StateManager --|> Observable : 继承
    StateManager "1" *-- "1" UIState : 包含
    StateManager "1" *-- "1" UserPreferences : 包含
    StateManager "1" *-- "1" ContextData : 包含
    
    ToolRouter "1" --> "1" StateManager : 使用
    ToolRouter "1" --> "*" ToolResult : 创建
    ToolRouter "1" ..> WeatherServer : 调用
    ToolRouter "1" ..> MarketServer : 调用
    ToolRouter "1" ..> AreaSearchServer : 调用
    
    ToolResult "1" --> "1" ToolStatus : 使用
    
    LLMInterface "1" --> "1" StateManager : 使用