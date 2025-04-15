sequenceDiagram
    autonumber
    participant 用户
    participant 聊天窗口 as 聊天窗口<br>(chat_ui.py)
    participant 录音线程 as 录音线程<br>(chat_ui.py)
    participant TTS助手 as TTS助手<br>(chat_ui.py)
    participant MCP助手 as MCP助手<br>(main.py)
    participant 对话管理器 as 对话管理器<br>(conversation_manager.py)
    participant 意图识别器 as 意图识别器<br>(intent_recognizer.py)
    participant 意图缓存 as 意图缓存<br>(intent_cache.py)
    participant 工具路由器 as 工具路由器<br>(tool_router.py)
    participant LLM接口 as LLM接口<br>(llm_interface.py)
    participant 天气服务 as 天气服务<br>(weatherMCP.py)
    participant 超市服务 as 超市服务<br>(marketMCP.py)
    participant 区域服务 as 区域服务<br>(areaSearchMCP.py)
    participant OpenAI as OpenAI/Ollama<br>API
    participant 天气API as OpenWeather<br>API
    participant 地图API as 高德地图<br>API
    participant TTS_API as Edge-TTS<br>API
    
    %% 用户输入流程
    用户->>聊天窗口: 输入文本查询
    activate 聊天窗口
    聊天窗口->>MCP助手: 传递用户查询
    deactivate 聊天窗口
    
    %% 或者用户语音输入
    alt 语音输入
        用户->>录音线程: 语音输入
        activate 录音线程
        录音线程->>聊天窗口: 录音数据
        聊天窗口->>MCP助手: 转换后的文本查询
        deactivate 录音线程
    end
    
    %% MCP助手处理流程
    activate MCP助手
    MCP助手->>对话管理器: 获取对话历史
    activate 对话管理器
    对话管理器-->>MCP助手: 返回对话历史
    deactivate 对话管理器
    
    %% 意图识别流程
    MCP助手->>意图识别器: 识别用户意图
    activate 意图识别器
    意图识别器->>意图缓存: 检查缓存
    activate 意图缓存
    alt 缓存未命中
        意图缓存-->>意图识别器: 缓存未命中
        意图识别器->>LLM接口: 请求意图分析
        activate LLM接口
        LLM接口->>OpenAI: API调用
        OpenAI-->>LLM接口: 返回意图分析
        LLM接口-->>意图识别器: 返回意图结果
        deactivate LLM接口
        意图识别器->>意图缓存: 存储意图
    else 缓存命中
        意图缓存-->>意图识别器: 返回缓存意图
    end
    deactivate 意图缓存
    意图识别器-->>MCP助手: 返回用户意图
    deactivate 意图识别器
    
    %% 工具路由分发
    alt 天气查询意图
        MCP助手->>工具路由器: 请求天气信息
        activate 工具路由器
        工具路由器->>天气服务: 调用天气服务
        activate 天气服务
        天气服务->>天气API: API调用
        天气API-->>天气服务: 返回天气数据
        天气服务-->>工具路由器: 返回处理结果
        deactivate 天气服务
        工具路由器-->>MCP助手: 返回天气信息
        deactivate 工具路由器
    else 超市查询意图
        MCP助手->>工具路由器: 请求超市信息
        activate 工具路由器
        工具路由器->>超市服务: 调用超市服务
        activate 超市服务
        超市服务-->>工具路由器: 返回超市数据
        deactivate 超市服务
        工具路由器-->>MCP助手: 返回超市信息
        deactivate 工具路由器
    else 区域查询意图
        MCP助手->>工具路由器: 请求区域信息
        activate 工具路由器
        工具路由器->>区域服务: 调用区域服务
        activate 区域服务
        区域服务->>地图API: API调用
        地图API-->>区域服务: 返回地图数据
        区域服务-->>工具路由器: 返回处理结果
        deactivate 区域服务
        工具路由器-->>MCP助手: 返回区域信息
        deactivate 工具路由器
    else 一般对话意图
        MCP助手->>LLM接口: 请求LLM响应
        activate LLM接口
        LLM接口->>OpenAI: API调用
        OpenAI-->>LLM接口: 返回LLM响应
        LLM接口-->>MCP助手: 返回格式化响应
        deactivate LLM接口
    end
    
    %% 响应用户
    MCP助手->>聊天窗口: 返回处理结果
    deactivate MCP助手
    activate 聊天窗口
    聊天窗口->>用户: 显示文本响应
    
    %% 语音输出
    聊天窗口->>TTS助手: 请求语音合成
    activate TTS助手
    TTS助手->>TTS_API: API调用
    TTS_API-->>TTS助手: 返回语音数据
    TTS助手-->>聊天窗口: 返回语音
    deactivate TTS助手
    聊天窗口->>用户: 播放语音响应
    deactivate 聊天窗口