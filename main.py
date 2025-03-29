"""
MiniLuma 多语言入口程序
提供命令行界面选择语言和启动不同的代理模式
Multilingual entry program for MiniLuma
Provides a command-line interface for selecting language and launching different agent modes
"""
import os
import sys
import argparse
import asyncio
from core.config import config

# 支持的语言 / Supported languages
LANGUAGES = {
    "zh-CN": "简体中文",
    "en-US": "English"
}

# 语言配置 / Language configurations
LANG_CONFIG = {
    "zh-CN": {
        "welcome": {
            "title": "欢迎使用 MiniLuma",
            "modes": [
                "1. 简单助手模式 - 单代理与工具集成",
                "2. 多代理系统 - 复杂任务分解与协作",
                "3. 自定义模式 - 配置自己的代理参数",
                "4. MCP 增强助手 - 支持文件保存和 AI 对话的高级助手"
            ],
            "exit_msg": "输入 'q' 或 'exit' 退出",
            "select_prompt": "请选择一个模式 (1-4) 或输入 'q' 退出: "
        },
        "messages": {
            "launching": "启动{}",
            "simple_assistant": "简单助手模式 (提供商: {}, 模型: {})",
            "multi_agent": "多代理系统模式 (提供商: {}, 模型: {})",
            "custom_mode": "自定义助手模式 (提供商: {}, 模型: {})",
            "mcp_assistant": "MCP 增强助手 (提供商: {}, 模型: {})",
            "ready": "已准备就绪。输入'exit'或'quit'退出。",
            "special_commands": "特殊命令:",
            "memory_command": "- 'm <对话ID>': 恢复指定记忆/历史记录",
            "ai_command": "- 'ai <内容>': 向特定AI模型请求回答",
            "user_prompt": "用户: ",
            "goodbye": "再见！",
            "error": "错误: {}",
            "program_terminated": "程序已终止",
            "config_path_prompt": "请输入配置文件路径 (留空使用默认配置): ",
            "api_key_warning": "警告: 以下提供商的API密钥未设置:",
            "api_key_setting": "请在config目录下的配置文件中设置API密钥。",
            "api_key_file": "您可以编辑 {} 文件添加您的API密钥。",
            "continue_prompt": "是否继续? (y/n): ",
            "default": "默认"
        }
    },
    "en-US": {
        "welcome": {
            "title": "Welcome to MiniLuma",
            "modes": [
                "1. Simple Assistant - Single agent with tool integration",
                "2. Multi-Agent System - Complex task decomposition and collaboration",
                "3. Custom Mode - Configure your own agent parameters",
                "4. MCP Enhanced Assistant - Advanced assistant with file saving and AI conversations"
            ],
            "exit_msg": "Enter 'q' or 'exit' to quit",
            "select_prompt": "Select a mode (1-4) or enter 'q' to exit: "
        },
        "messages": {
            "launching": "Launching {}",
            "simple_assistant": "Simple Assistant Mode (Provider: {}, Model: {})",
            "multi_agent": "Multi-Agent System Mode (Provider: {}, Model: {})",
            "custom_mode": "Custom Assistant Mode (Provider: {}, Model: {})",
            "mcp_assistant": "MCP Enhanced Assistant (Provider: {}, Model: {})",
            "ready": "is ready. Type 'exit' or 'quit' to exit.",
            "special_commands": "Special commands:",
            "memory_command": "- 'm <conversation ID>': Restore specified memory/history",
            "ai_command": "- 'ai <content>': Request answer from specific AI model",
            "user_prompt": "User: ",
            "goodbye": "Goodbye!",
            "error": "Error: {}",
            "program_terminated": "Program terminated",
            "config_path_prompt": "Enter configuration file path (leave empty for default config): ",
            "api_key_warning": "Warning: API keys for the following providers are not set:",
            "api_key_setting": "Please set the API keys in the configuration file in the config directory.",
            "api_key_file": "You can edit the {} file to add your API keys.",
            "continue_prompt": "Continue anyway? (y/n): ",
            "default": "default"
        }
    }
}

def get_text(lang, section, key, *args):
    """获取指定语言的文本 / Get text for the specified language"""
    text = LANG_CONFIG[lang][section][key]
    if args:
        return text.format(*args)
    return text

def show_welcome(lang):
    """显示欢迎信息 / Display welcome message"""
    print("\n" + "=" * 60)
    print(get_text(lang, "welcome", "title").center(58))
    print("=" * 60)
    print("\n可用模式 / Available modes:")
    
    for mode in get_text(lang, "welcome", "modes"):
        print(mode)
    
    print("\n" + get_text(lang, "welcome", "exit_msg"))
    print("=" * 60)

async def run_simple_assistant(lang, provider, model, thinking):
    """运行简单助手模式 / Run simple assistant mode"""
    model_display = model or get_text(lang, "messages", "default")
    print(f"\n{get_text(lang, 'messages', 'launching', get_text(lang, 'messages', 'simple_assistant', provider, model_display))}")
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建助手 / Use assistant factory to create assistant asynchronously
        assistant = await create_assistant(
            assistant_type="simple", 
            provider_name=provider, 
            model=model
        )
        
        # 创建并启动CLI界面 / Create and start CLI interface
        cli = AgentCLI(assistant, show_thinking=thinking, language=lang)
        await cli.start()
        
    except Exception as e:
        print(get_text(lang, "messages", "error", str(e)))
        import traceback
        traceback.print_exc()

async def run_multi_agent(lang, provider, model, thinking):
    """运行多代理系统模式 / Run multi-agent system mode"""
    model_display = model or get_text(lang, "messages", "default")
    print(f"\n{get_text(lang, 'messages', 'launching', get_text(lang, 'messages', 'multi_agent', provider, model_display))}")
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建多代理系统 / Use assistant factory to create multi-agent system asynchronously
        mas = await create_assistant(
            assistant_type="multi_agent", 
            provider_name=provider, 
            model=model
        )
        
        # 创建并启动CLI界面 / Create and start CLI interface
        cli = AgentCLI(mas, show_thinking=thinking, language=lang)
        await cli.start()
        
    except Exception as e:
        print(get_text(lang, "messages", "error", str(e)))
        import traceback
        traceback.print_exc()

async def run_custom_mode(lang, provider, model, thinking, config_path):
    """运行自定义助手模式 / Run custom assistant mode"""
    model_display = model or get_text(lang, "messages", "default")
    print(f"\n{get_text(lang, 'messages', 'launching', get_text(lang, 'messages', 'custom_mode', provider, model_display))}")
    
    if not config_path:
        config_path = input(get_text(lang, "messages", "config_path_prompt")).strip()
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建MCP增强助手 / Use assistant factory to create MCP enhanced assistant asynchronously
        assistant = await create_assistant(
            assistant_type="mcp", 
            provider_name=provider, 
            model=model,
            config_path=config_path
        )
        
        # 创建CLI界面进行交互 / Create CLI interface for interaction
        cli = AgentCLI(assistant, show_thinking=thinking, language=lang, config_path=config_path)
        await cli.start()
        
    except Exception as e:
        print(get_text(lang, "messages", "error", str(e)))
        import traceback
        traceback.print_exc()

async def run_mcp_assistant(lang, provider, model, thinking):
    """运行 MCP 增强助手模式 / Run MCP enhanced assistant mode"""
    model_display = model or get_text(lang, "messages", "default")
    print(f"\n{get_text(lang, 'messages', 'launching', get_text(lang, 'messages', 'mcp_assistant', provider, model_display))}")
    
    try:
        from examples.mcp_enhanced_assistant import MCPEnhancedAssistant
        
        # 创建 MCP 助手实例 / Create MCP assistant instance
        assistant = await MCPEnhancedAssistant.create(
            name="MiniLuma",
            provider_name=provider,
            model=model
        )
        
        # 欢迎信息 / Welcome message
        print(f"\n{assistant.name} {get_text(lang, 'messages', 'ready')}")
        print(get_text(lang, "messages", "special_commands"))
        print(get_text(lang, "messages", "memory_command"))
        print(get_text(lang, "messages", "ai_command"))
        print("-" * 50)
        
        # 交互循环 / Interaction loop
        while True:
            # 获取用户输入 / Get user input
            user_input = input(get_text(lang, "messages", "user_prompt")).strip()
            
            # 检查退出命令 / Check exit command
            if user_input.lower() in ['exit', 'quit', 'q']:
                print(get_text(lang, "messages", "goodbye"))
                break
                
            # 处理用户输入 / Process user input
            response = await assistant.process(user_input)
            print(f"\n{assistant.name}: {response}\n")
            
    except KeyboardInterrupt:
        print(f"\n{get_text(lang, 'messages', 'program_terminated')}")
    except Exception as e:
        print(get_text(lang, "messages", "error", str(e)))
        import traceback
        traceback.print_exc()

def check_api_keys(lang):
    """检查API密钥是否设置 / Check if API keys are set"""
    missing_providers = []
    
    # 检查默认提供商是否设置了API密钥 / Check if API key is set for default provider
    default_provider = config.get_default_provider()
    if not config.is_api_key_set(default_provider):
        missing_providers.append(default_provider)
    
    if missing_providers:
        print(f"\n{get_text(lang, 'messages', 'api_key_warning')}")
        for provider in missing_providers:
            print(f"- {provider.upper()}_API_KEY")
        
        print(f"\n{get_text(lang, 'messages', 'api_key_setting')}")
        config_file_path = os.path.join('config', 'config_global.toml')
        print(get_text(lang, "messages", "api_key_file", config_file_path))
        
        response = input(f"\n{get_text(lang, 'messages', 'continue_prompt')}").strip().lower()
        return response in ['y', 'yes']
    
    return True

def select_language():
    """选择语言 / Select language"""
    print("\n" + "=" * 60)
    print("请选择语言 / Please select language:".center(58))
    print("=" * 60)
    
    for i, (code, name) in enumerate(LANGUAGES.items(), 1):
        print(f"{i}. {name}")
    
    while True:
        choice = input("\n输入选项编号 / Enter option number: ").strip()
        if choice.isdigit() and 1 <= int(choice) <= len(LANGUAGES):
            return list(LANGUAGES.keys())[int(choice) - 1]
        print("无效选项，请重试 / Invalid option, please try again")

async def main():
    """主函数 / Main function"""
    parser = argparse.ArgumentParser(description="MiniLuma 多语言界面 / MiniLuma Multilingual Interface")
    parser.add_argument(
        "--lang", "-l",
        choices=LANGUAGES.keys(),
        help="语言设置 / Language setting"
    )
    parser.add_argument(
        "--mode", "-m",
        type=int,
        choices=[1, 2, 3, 4],
        help="运行模式 / Run mode: 1=简单助手/Simple, 2=多代理/Multi-agent, 3=自定义/Custom, 4=MCP增强/MCP Enhanced"
    )
    parser.add_argument(
        "--provider", "-p",
        default=config.get_default_provider(),
        choices=["openai", "deepseek", "silicon_flow"],
        help="LLM提供商 / LLM provider"
    )
    parser.add_argument(
        "--model",
        help="具体模型名称 / Specific model name"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="显示代理思考过程 / Show agent thinking process"
    )
    parser.add_argument(
        "--config", "-c",
        help="配置文件路径 (仅适用于自定义模式) / Configuration file path (only for custom mode)"
    )
    
    args = parser.parse_args()
    
    # 获取语言设置，优先级：命令行参数 > 配置文件 > 用户选择
    lang = None
    if args.lang:
        # 1. 优先使用命令行参数指定的语言
        lang = args.lang
    else:
        # 2. 尝试从配置文件中读取语言设置
        config_lang = config.get("global", "language")
        if config_lang in LANGUAGES:
            lang = config_lang
            print(f"使用配置中的语言设置: {LANGUAGES[lang]} / Using language from config: {LANGUAGES[lang]}")
        else:
            # 3. 如果以上都没有，则请用户选择
            lang = select_language()
    
    # 如果未指定模型，使用配置文件中的默认模型 / If model not specified, use default model from config
    if not args.model:
        args.model = config.get_default_model(args.provider)
    
    # 检查API密钥 / Check API keys
    if not check_api_keys(lang):
        print(get_text(lang, "messages", "goodbye"))
        return 1
    
    # 如果未指定模式，显示菜单让用户选择 / If mode not specified, show menu for user to select
    mode = args.mode
    if not mode:
        show_welcome(lang)
        choice = input(get_text(lang, "welcome", "select_prompt")).strip()
        
        if choice.lower() in ['q', 'exit', 'quit']:
            print(get_text(lang, "messages", "goodbye"))
            return 0
            
        if choice.isdigit() and 1 <= int(choice) <= 4:
            mode = int(choice)
        else:
            print(get_text(lang, "messages", "error", "无效的选择 / Invalid selection"))
            return 1
    
    # 根据选择的模式启动相应功能 / Launch corresponding functionality based on selected mode
    if mode == 1:
        await run_simple_assistant(lang, args.provider, args.model, args.thinking)
    elif mode == 2:
        await run_multi_agent(lang, args.provider, args.model, args.thinking)
    elif mode == 3:
        await run_custom_mode(lang, args.provider, args.model, args.thinking, args.config)
    elif mode == 4:
        await run_mcp_assistant(lang, args.provider, args.model, args.thinking)
    
    return 0

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
