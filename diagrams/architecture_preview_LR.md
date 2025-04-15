%%{init: {
  'theme': 'default',
  'themeVariables': {
    'fontSize': '14px',
    'fontFamily': 'Arial',
    'primaryTextColor': '#000',
    'lineColor': '#333'
  },
  'flowchart': {
    'useMaxWidth': false
  }
}}%%

flowchart TB
    %% 样式定义
    classDef coreBox fill:#E1FFE5,stroke:#000,stroke-width:2px
    classDef uiBox fill:#E6F5FF,stroke:#000,stroke-width:2px
    classDef controlBox fill:#FFE9D0,stroke:#000,stroke-width:2px
    classDef toolBox fill:#F0E6FF,stroke:#000,stroke-width:2px
    classDef apiBox fill:#F5F5F5,stroke:#000,stroke-width:2px
    
    classDef uiComponent fill:#DCF0FF,stroke:#000,stroke-width:1px,rx:10,ry:10
    classDef controlComponent fill:#FFD8B0,stroke:#000,stroke-width:1px,rx:10,ry:10
    classDef coreComponent fill:#D5F6DA,stroke:#000,stroke-width:1px,rx:10,ry:10
    classDef toolComponent fill:#E5D9FF,stroke:#000,stroke-width:1px,rx:10,ry:10
    classDef apiComponent fill:#E8E8E8,stroke:#000,stroke-width:1px,rx:10,ry:10

    %% 核心服务层(包含所有)
    subgraph CoreServicesMain ["核心服务层 (Core Services Layer)"]
        %% 用户界面子区域(右上)
        subgraph UILayer ["用户界面层 (UI Layer)"]
            RecordThread["RecordingThread<br/>(chat_ui.py)"]
            ChatWindow["ChatWindow<br/>(chat_ui.py)"]
            TtsHelper["TtsHelper<br/>(chat_ui.py)"]
        end
        
        %% 控制层子区域(右中)
        subgraph ControllerLayer ["控制层 (Controller Layer)"]
            MCPAssistant["MCPAssistant<br/>(main.py)"]
        end
        
        %% 工具服务层子区域(右下)
        subgraph ToolServices ["工具服务层 (Tool Services Layer)"]
            WeatherServer["WeatherServer<br/>(weatherMCP.py)"]
            MarketServer["MarketServer<br/>(marketMCP.py)"]
            AreaSearchServer["AreaSearchServer<br/>(areaSearchMCP.py)"]
        end
        
        %% 外部API层(底部)
        subgraph APILayer ["外部API层 (External API Layer)"]
            OpenAI_API["OpenAI/Ollama API"]
            Weather_API["OpenWeather API"]
            Map_API["高德地图 API"]
            TTS_API["Edge-TTS API"]
        end
        
        %% 核心服务组件(左侧)
        StateManager["StateManager<br/>(state_manager.py)"]
        IntentRec["IntentRecognizer<br/>(intent_recognizer.py)"]
        ConvManager["ConversationManager<br/>(conversation_manager.py)"]
        ToolRouter["ToolRouter<br/>(tool_router.py)"]
        IntentCache["IntentCache<br/>(intent_cache.py)"]
        LLMInterface["LLMInterface<br/>(llm_interface.py)"]
    end
    
    %% ==== 连接关系 ====
    
    %% 状态管理器的依赖关系(虚线)
    StateManager -.-|"状态依赖"| IntentRec
    StateManager -.-|"状态依赖"| ConvManager
    StateManager -.-|"状态依赖"| ToolRouter
    StateManager -.-|"状态依赖"| MCPAssistant
    StateManager -.-|"状态依赖"| LLMInterface
    
    %% 用户界面与控制层连接
    RecordThread -->|"录音数据"| ChatWindow
    ChatWindow -->|"用户查询"| MCPAssistant
    MCPAssistant -->|"LLM响应"| ChatWindow
    MCPAssistant -->|"TTS转换请求"| TtsHelper
    
    %% 控制层与核心服务连接
    MCPAssistant -->|"会话管理"| ConvManager
    MCPAssistant -->|"意图识别"| IntentRec
    MCPAssistant -->|"工具调用"| ToolRouter
    
    %% 核心层内部连接
    IntentRec -->|"缓存意图"| IntentCache
    IntentRec -->|"意图分析"| LLMInterface
    ConvManager -->|"历史对话"| LLMInterface
    ToolRouter -.->|"工具调用请求"| LLMInterface
    
    %% 工具路由连接
    ToolRouter -->|"天气查询"| WeatherServer
    ToolRouter -->|"超市查询"| MarketServer
    ToolRouter -->|"区域搜索"| AreaSearchServer
    
    %% 工具结果返回(虚线)
    WeatherServer -.->|"天气结果"| ToolRouter
    MarketServer -.->|"超市结果"| ToolRouter
    AreaSearchServer -.->|"区域结果"| ToolRouter
    
    %% API连接
    LLMInterface -->|"LLM调用"| OpenAI_API
    WeatherServer -->|"天气API调用"| Weather_API
    AreaSearchServer -->|"地图API调用"| Map_API
    TtsHelper -->|"语音合成调用"| TTS_API
    
    %% 应用样式
    class CoreServicesMain coreBox
    class UILayer uiBox
    class ControllerLayer controlBox
    class ToolServices toolBox
    class APILayer apiBox
    
    class ChatWindow,RecordThread,TtsHelper uiComponent
    class MCPAssistant controlComponent
    class StateManager,ConvManager,IntentRec,ToolRouter,IntentCache,LLMInterface coreComponent
    class WeatherServer,MarketServer,AreaSearchServer toolComponent
    class OpenAI_API,Weather_API,Map_API,TTS_API apiComponent