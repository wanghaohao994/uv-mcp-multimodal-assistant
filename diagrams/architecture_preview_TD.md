%%{init: {
  'theme': 'dark',
  'themeVariables': {
    'fontSize': '14px',
    'fontFamily': 'Orbitron, Consolas, monospace',
    'primaryTextColor': '#ffffff',
    'lineColor': '#00ffff',
    'edgeLabelBackground': '#0f0f22',
    'tertiaryColor': '#0f0f22'
  },
  'flowchart': {
    'useMaxWidth': false,
    'curve': 'linear',
    'diagramPadding': 20,
    'htmlLabels': true,
    'padding': 15
  }
}}%%

flowchart TD
    %% 样式定义 - 超饱和赛博朋克配色
    classDef coreBox fill:#0a0a20,stroke:#00ffff,stroke-width:3px
    classDef uiBox fill:#100018,stroke:#ff00ff,stroke-width:3px
    classDef controlBox fill:#001a15,stroke:#00ff99,stroke-width:3px
    classDef toolBox fill:#14083a,stroke:#aa44ff,stroke-width:3px
    classDef apiBox fill:#1a0f1f,stroke:#ff1a4d,stroke-width:3px
    
    classDef uiComponent fill:#220022,stroke:#ff00ff,stroke-width:3px,rx:0,ry:0
    classDef controlComponent fill:#002218,stroke:#00ff99,stroke-width:3px,rx:0,ry:0
    classDef coreComponent fill:#0e0e40,stroke:#00ffff,stroke-width:3px,rx:0,ry:0
    classDef toolComponent fill:#16084d,stroke:#aa44ff,stroke-width:3px,rx:0,ry:0
    classDef apiComponent fill:#220015,stroke:#ff1a4d,stroke-width:3px,rx:0,ry:0

    %% 核心服务层(包含所有) - 扩宽框体
    subgraph CoreServicesMain ["<span style='font-size:16px; font-weight:bold; color:#00ffff; display:inline-block; width:500px;'>核心服务层 (Core Services Layer)</span>"]
        %% 核心服务组件(上方) - 扩宽框体
        subgraph CoreComponents ["<span style='color:#00ffff; display:inline-block; width:400px;'>核心组件 (Core Components)</span>"]
            direction LR
            StateManager["<b>状态管理器</b><br/><i>state_manager.py</i>"]
            IntentRec["<b>意图识别器</b><br/><i>intent_recognizer.py</i>"]
            ConvManager["<b>对话管理器</b><br/><i>conversation_manager.py</i>"]
            ToolRouter["<b>工具路由器</b><br/><i>tool_router.py</i>"]
            IntentCache["<b>意图缓存</b><br/><i>intent_cache.py</i>"]
            LLMInterface["<b>LLM接口</b><br/><i>llm_interface.py</i>"]
        end
        
        %% 控制层子区域(中上) - 扩宽框体
        subgraph ControllerLayer ["<span style='color:#00ff99; display:inline-block; width:300px;'>控制层 (Controller Layer)</span>"]
            MCPAssistant["<b>MCP助手</b><br/><i>main.py</i>"]
        end
        
        %% 用户界面子区域(中部) - 扩宽框体
        subgraph UILayer ["<span style='color:#ff00ff; display:inline-block; width:400px;'>用户界面层 (UI Layer)</span>"]
            direction LR
            RecordThread["<b>录音线程</b><br/><i>chat_ui.py</i>"]
            ChatWindow["<b>聊天窗口</b><br/><i>chat_ui.py</i>"]
            TtsHelper["<b>语音合成助手</b><br/><i>chat_ui.py</i>"]
        end
        
        %% 工具服务层子区域(中下) - 扩宽框体
        subgraph ToolServices ["<span style='color:#aa44ff; display:inline-block; width:400px;'>工具服务层 (Tool Services Layer)</span>"]
            direction LR
            WeatherServer["<b>天气服务器</b><br/><i>weatherMCP.py</i>"]
            MarketServer["<b>超市服务器</b><br/><i>marketMCP.py</i>"]
            AreaSearchServer["<b>区域搜索服务器</b><br/><i>areaSearchMCP.py</i>"]
        end
        
        %% 外部API层(底部) - 扩宽框体
        subgraph APILayer ["<span style='color:#ff1a4d; display:inline-block; width:400px;'>外部API层 (External API Layer)</span>"]
            direction LR
            OpenAI_API["<b>OpenAI/Ollama</b><br/><i>API</i>"]
            Weather_API["<b>OpenWeather</b><br/><i>API</i>"]
            Map_API["<b>高德地图</b><br/><i>API</i>"]
            TTS_API["<b>Edge-TTS</b><br/><i>API</i>"]
        end
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
    class CoreComponents coreComponent
    class UILayer uiBox
    class ControllerLayer controlBox
    class ToolServices toolBox
    class APILayer apiBox
    
    class ChatWindow,RecordThread,TtsHelper uiComponent
    class MCPAssistant controlComponent
    class StateManager,ConvManager,IntentRec,ToolRouter,IntentCache,LLMInterface coreComponent
    class WeatherServer,MarketServer,AreaSearchServer toolComponent
    class OpenAI_API,Weather_API,Map_API,TTS_API apiComponent