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
    classDef startEnd fill:#0a0a20,stroke:#00ffff,stroke-width:4px,color:#00ffff
    classDef process fill:#0e0e40,stroke:#00ffff,stroke-width:2px,color:#ffffff
    classDef decision fill:#14083a,stroke:#aa44ff,stroke-width:3px,color:#ffffff
    classDef api fill:#1a0f1f,stroke:#ff1a4d,stroke-width:2px,color:#ffffff
    classDef output fill:#001a15,stroke:#00ff99,stroke-width:2px,color:#00ff99
    classDef coreSubgraph fill:#0a0a20,stroke:#00ffff,stroke-width:4px,color:#00ffff
    classDef uiSubgraph fill:#100018,stroke:#ff00ff,stroke-width:4px,color:#ff00ff
    classDef toolSubgraph fill:#14083a,stroke:#aa44ff,stroke-width:4px,color:#aa44ff
    classDef apiSubgraph fill:#1a0f1f,stroke:#ff1a4d,stroke-width:4px,color:#ff1a4d
    classDef mainSystem fill:#050510,stroke:#ff00ff,stroke-width:6px,color:#ff00ff,stroke-dasharray: 0
    
    linkStyle default stroke:#00ffff,stroke-width:2px,color:#ffffff,stroke-linecap:square
    
    %% 主流程
    Start([<b>启动系统</b>]) --- ChatWindow

    %% 主系统框架
    subgraph MCP ["<b>MCP智能助手核心系统</b>"]
        direction TB
        
        %% 输入处理子图
        subgraph Input ["<b>输入处理系统</b>"]
            direction TB
            ChatWindow["<b>聊天窗口</b><br><i>chat_ui.py</i>"]
            InputType{"<b>输入类型识别</b>"}
            TextQuery["<b>文本处理器</b>"]
            RecordThread["<b>录音线程</b><br><i>chat_ui.py</i>"]
            STT["<b>语音文本转换</b>"]
            MCPAssistant["<b>MCP主控制器</b><br><i>main.py</i>"]
            
            ChatWindow --- InputType
            InputType ---|"文本输入"| TextQuery
            InputType ---|"语音输入"| RecordThread
            RecordThread --- STT
            STT --- TextQuery
            TextQuery --- MCPAssistant
        end
        
        %% 对话管理与意图识别子图
        subgraph Processing ["<b>核心处理系统</b>"]
            direction TB
            AddHistory["<b>历史记录模块</b><br><i>conversation_manager.py</i>"]
            IntentRecognize["<b>意图识别器</b><br><i>intent_recognizer.py</i>"]
            IntentCache{"<b>缓存检测</b><br><i>intent_cache.py</i>"}
            LLMIntent["<b>LLM意图分析</b><br><i>llm_interface.py</i>"]
            SaveCache["<b>缓存写入</b>"]
            IntentTypeCheck{"<b>意图分类器</b>"}
            CommandProcess["<b>命令处理器</b><br><i>_handle_command()</i>"]
            ToolProcess["<b>工具处理器</b><br><i>_call_tool_and_respond()</i>"]
            ToolNeeded{"<b>工具需求评估</b>"}
            GeneralChat["<b>对话处理器</b><br><i>_handle_general_chat()</i>"]
            
            AddHistory --- IntentRecognize
            IntentRecognize --- IntentCache
            IntentCache ---|"缓存未命中"| LLMIntent
            LLMIntent --- SaveCache
            IntentCache ---|"缓存命中"| IntentTypeCheck
            SaveCache --- IntentTypeCheck
            
            IntentTypeCheck ---|"命令类型"| CommandProcess
            IntentTypeCheck ---|"工具类型"| ToolProcess
            IntentTypeCheck ---|"一般对话"| ToolNeeded
            
            ToolNeeded ---|"需要工具"| ToolProcess
            ToolNeeded ---|"直接对话"| GeneralChat
        end
        
        %% 工具调用子图
        subgraph Tools ["<b>工具服务系统</b>"]
            direction TB
            ToolType{"<b>工具选择器</b>"}
            
            WeatherTool["<b>天气服务</b><br><i>weatherMCP.py</i>"]
            WeatherAPI["<b>OpenWeather API</b>"]
            WeatherProcess["<b>天气数据处理</b>"]
            
            MarketTool["<b>超市服务</b><br><i>marketMCP.py</i>"]
            MarketData["<b>超市数据库</b>"]
            MarketProcess["<b>超市数据处理</b>"]
            
            AreaTool["<b>区域搜索</b><br><i>areaSearchMCP.py</i>"]
            MapAPI["<b>高德地图 API</b>"]
            AreaProcess["<b>地图数据处理</b>"]
            
            ResponseFormat["<b>响应格式化器</b>"]
            
            ToolType ---|"天气查询"| WeatherTool
            WeatherTool --- WeatherAPI
            WeatherAPI --- WeatherProcess
            
            ToolType ---|"超市查询"| MarketTool
            MarketTool --- MarketData
            MarketData --- MarketProcess
            
            ToolType ---|"区域查询"| AreaTool
            AreaTool --- MapAPI
            MapAPI --- AreaProcess
            
            WeatherProcess --- ResponseFormat
            MarketProcess --- ResponseFormat
            AreaProcess --- ResponseFormat
        end
        
        %% LLM对话子图
        subgraph LLMChat ["<b>LLM对话系统</b>"]
            direction TB
            PrepMsg["<b>消息预处理</b><br><i>prepare_messages</i>"]
            FormatSys["<b>系统提示格式化</b><br><i>format_system_prompt</i>"]
            LLMCall["<b>LLM调用接口</b><br><i>generate_response_async</i>"]
            LLMResponse["<b>LLM响应处理</b>"]
            
            PrepMsg --- FormatSys
            FormatSys --- LLMCall
            LLMCall --- LLMResponse
        end
        
        %% 响应处理子图
        subgraph Response ["<b>输出处理系统</b>"]
            direction TB
            ResponseHandler["<b>响应生成器</b>"]
            SaveAssistMsg["<b>助手消息存储</b><br><i>add_assistant_message</i>"]
            OutputType{"<b>输出模式选择</b>"}
            TextOut["<b>文本显示接口</b>"]
            TTSHandler["<b>TTS处理器</b><br><i>chat_ui.py</i>"]
            TTS_API["<b>Edge-TTS API</b>"]
            AudioPlay["<b>音频播放器</b>"]
            
            ResponseHandler --- SaveAssistMsg
            SaveAssistMsg --- OutputType
            OutputType ---|"仅文本"| TextOut
            OutputType ---|"文本+语音"| TTSHandler
            TTSHandler --- TTS_API
            TTS_API --- AudioPlay
        end
        
        %% 错误处理组件
        ErrorHandler["<b>错误处理模块</b><br><i>try-except</i>"]
        ErrorResponse["<b>错误响应生成</b>"]
    end
    
    %% 核心连接关系
    MCPAssistant --- AddHistory
    MCPAssistant -. "<b><i>异常触发</i></b>" .-> ErrorHandler
    linkStyle 37 stroke:#ff1a4d,stroke-width:2px,stroke-dasharray: 5 5
    
    ErrorHandler --- ErrorResponse
    ErrorResponse --- SaveAssistMsg
    
    ToolProcess --- ToolType
    GeneralChat --- PrepMsg
    
    CommandProcess --- ResponseHandler
    ToolProcess --- ResponseHandler
    ResponseFormat --- ResponseHandler
    LLMResponse --- ResponseHandler
    
    TextOut --- End
    AudioPlay --- End
    
    End([<b>任务完成</b>])
    
    %% 应用样式
    class Start,End startEnd
    class TextQuery,AddHistory,LLMIntent,SaveCache,CommandProcess,GeneralChat,PrepMsg,FormatSys,LLMCall,LLMResponse,ResponseHandler,SaveAssistMsg process
    class InputType,IntentCache,IntentTypeCheck,ToolNeeded,ToolType,OutputType decision
    class WeatherAPI,MarketData,MapAPI,TTS_API api
    class TextOut,AudioPlay output
    class Input uiSubgraph
    class Processing coreSubgraph
    class Tools toolSubgraph
    class LLMChat coreSubgraph
    class Response uiSubgraph
    class MCPAssistant,ChatWindow,RecordThread,IntentRecognize,WeatherTool,MarketTool,AreaTool,TTSHandler,WeatherProcess,MarketProcess,AreaProcess,ResponseFormat process
    class ErrorHandler,ErrorResponse process
    class MCP mainSystem