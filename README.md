# Miniluma

Miniluma是一个强大的智能代理框架，支持多种LLM提供商（包括DeepSeek和OpenAI），能够通过工具增强、多代理协作和异步处理实现复杂任务的自动化处理。

<p align="center">
  <img src="docs/images/logo.png" alt="Miniluma Logo" width="200" />
</p>

## 功能特点

- **多语言支持**
  - 支持中文和英文界面
  - 可扩展的语言配置系统

- **多模式支持**
  - 简单助手模式：单代理与工具集成
  - 多代理系统：复杂任务分解与协作
  - 自定义模式：配置自己的代理参数
  - MCP增强助手：支持文件保存和AI对话的高级助手

- **多LLM提供商支持**
  - DeepSeek支持（R1和V3模型）
  - OpenAI支持（GPT-3.5和GPT-4系列）
  - Anthropic支持（Claude系列）
  - 可扩展的提供商架构

- **Reactor模式实现**
  - 理性-行动循环（Reason-Action Cycles）
  - 工具集成和工具调用
  - 自动推理和任务分解

- **异步架构**
  - 支持异步API调用
  - 高效处理多个并行任务
  - 非阻塞用户界面体验

- **强大的工具集**
  - 网络搜索功能
  - 代码执行功能
  - 文件管理与保存
  - 多媒体处理工具
  - 文档处理与分析
  - 可自定义的工具扩展

- **自动保存功能**
  - 自动检测和保存生成的文件
  - 自定义文件保存策略
  - 结构化存档管理

## 系统架构

### 核心组件

- **Core**
  - `reactor.py`：实现Reactor模式，处理思考-行动循环
  - `context.py`：管理会话上下文和历史记录
  - `planner.py`：任务规划和分解
  - `mcp_system.py`：MCP协议集成

- **LLM集成**
  - `deepseek.py`：DeepSeek LLM集成
  - `openai_llm.py`：OpenAI LLM集成
  - `anthropic_llm.py`：Anthropic Claude集成

- **提供商工厂**
  - `factory.py`：LLM提供商工厂
  - `assistant_factory.py`：助手创建工厂

- **示例与应用**
  - `simple_assistant.py`：简单助手实现
  - `multi_agent_example.py`：多代理系统示例
  - `mcp_enhanced_assistant.py`：高级MCP助手

- **工具集**
  - `web_tools.py`：网络工具集合
  - `file_tools.py`：文件操作工具
  - `code_tools.py`：代码分析与执行
  - `data_tools.py`：数据处理工具

## 快速开始

### 环境要求

- Python 3.8+
- 支持Windows、macOS和Linux系统
- Node.js（用于MCP功能）
- Playwright（用于高级浏览器自动化）

### 安装依赖

```bash
pip install -r requirements.txt

# 安装Playwright（用于MCP功能）
playwright install
```

### 配置API密钥

在`miniluma/config/config_global.toml`中配置API密钥：

```toml
[llm.openai]
api_key = "your_openai_api_key"

[llm.deepseek]
api_key = "your_deepseek_api_key"

[llm.anthropic]
api_key = "your_anthropic_api_key"
```

或者设置环境变量：

```bash
export OPENAI_API_KEY="your_openai_api_key"
export DEEPSEEK_API_KEY="your_deepseek_api_key"
export ANTHROPIC_API_KEY="your_anthropic_api_key"
```

### 运行框架

```bash
# 多语言支持（新）
python miniluma/main.py

# 中文界面（旧）
python miniluma/main_cn.py
```

## 使用模式

### 1. 简单助手模式

适用于基础问答和简单任务，单一代理使用工具集成来解决问题。

```bash
python miniluma/main.py --mode 1
```

### 2. 多代理系统

针对复杂任务，使用专业代理（研究代理、代码代理等）协作解决问题，通过任务规划器分解任务。

```bash
python miniluma/main.py --mode 2
```

### 3. 自定义模式

允许用户通过配置文件自定义代理参数和行为。

```bash
python miniluma/main.py --mode 3 --config config/custom_agent.toml
```

### 4. MCP增强助手

支持高级功能，如文件保存、富媒体处理和复杂对话管理。

```bash
python miniluma/main.py --mode 4
```

可选参数：
- `--provider`：指定LLM提供商（默认：deepseek）
- `--model`：指定具体模型
- `--thinking`：显示代理思考过程
- `--lang`：指定界面语言（zh-CN或en-US）

## 技术说明

- 基于 Reactor 模式 (Reason-Action-Observe 循环)
- 微内核架构设计，支持插件扩展
- 多代理系统采用任务规划和分配机制
- 异步非阻塞设计，提高响应效率
- 自动保存功能确保生成的文件安全存储

## 开发指南

### 自定义代理开发

使用 Reactor 模式创建自定义代理:

```python
from core.agent import ReactorAgent
from llm.openai import OpenAILLM

# 创建 LLM 服务
llm = OpenAILLM(model="gpt-4")

# 创建代理
agent = ReactorAgent(llm)

# 处理用户输入
result = agent.process("帮我写一个计算斐波那契数列的函数")
print(result["response"])
```

### 添加新工具

1. 在相应的工具模块中定义工具函数
2. 在工具函数上使用`@tool`装饰器（如适用）
3. 在代理初始化中注册工具

```python
from core.tool import tool

@tool(name="search_web", description="搜索网络")
async def search_web(query: str) -> str:
    """
    在网络上搜索信息
    
    Args:
        query: 搜索查询
        
    Returns:
        搜索结果
    """
    # 实现搜索逻辑
    return search_results
```

### 添加新的LLM提供商

1. 创建新的提供商类实现
2. 在`factory.py`中添加提供商工厂支持
3. 更新配置文件结构

```python
from llm.base import BaseLLM

class NewProviderLLM(BaseLLM):
    def __init__(self, api_key=None, model=None):
        super().__init__(api_key, model)
        # 初始化逻辑
        
    async def generate(self, prompt, **kwargs):
        # 生成逻辑
        return response
```

### 多语言支持开发

1. 在`main.py`中的`LANG_CONFIG`字典中添加新语言
2. 提供所有必需的文本键值对
3. 更新语言选择菜单

## 目录结构

```
miniluma/
├── core/           # 核心功能模块
├── llm/            # LLM集成模块
├── providers/      # 提供商工厂和实现
├── tools/          # 工具集合
├── examples/       # 示例应用
├── ui/             # 用户界面模块
├── config/         # 配置文件
├── utils/          # 实用工具
├── logs/           # 日志目录
├── results/        # 生成结果目录
├── main.py         # 多语言主入口
└── main_cn.py      # 中文入口（传统）
```

## 参考项目

- OWL (Optimized Workforce Learning)
- CAMEL-AI框架
- MCP (Model Context Protocol)

## 贡献指南

欢迎提交问题报告、功能请求和代码贡献。请遵循以下步骤：

1. Fork项目
2. 创建功能分支 (`git checkout -b feature/amazing-feature`)
3. 提交更改 (`git commit -m 'Add some amazing feature'`)
4. 推送到分支 (`git push origin feature/amazing-feature`)
5. 创建Pull Request

## 许可证

[MIT License](LICENSE)

## 后续开发计划

- 增强多语言支持
- 添加更多LLM提供商集成
- 实现Web界面
- 增强多代理协作能力
- 优化记忆检索机制
- 增加更多文档和图像处理工具
- 支持流式响应
"# Miniluma" 

## 联系方式
- QQ：733737715
