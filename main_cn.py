"""
MiniLuma 中文入口
提供命令行界面选择和启动不同的代理模式
"""
import os
import sys
import argparse
from core.config import config

def show_welcome():
    """显示欢迎信息"""
    print("\n" + "=" * 60)
    print("欢迎使用 MiniLuma".center(58))
    print("=" * 60)
    print("\n可用模式:")
    print("1. 简单助手模式 - 单代理与工具集成")
    print("2. 多代理系统 - 复杂任务分解与协作")
    print("3. 自定义模式 - 配置自己的代理参数")
    print("4. MCP 增强助手 - 支持文件保存和 AI 对话的高级助手")
    print("\n输入 'q' 或 'exit' 退出")
    print("=" * 60)

async def run_simple_assistant(provider, model, thinking):
    """运行简单助手模式"""
    print(f"\n启动简单助手模式 (提供商: {provider}, 模型: {model or '默认'})")
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建助手
        assistant = await create_assistant(
            assistant_type="simple", 
            provider_name=provider, 
            model=model
        )
        
        # 创建并启动CLI界面
        cli = AgentCLI(assistant, show_thinking=thinking, language="zh-CN")
        await cli.start()
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_multi_agent(provider, model, thinking):
    """运行多代理系统模式"""
    print(f"\n启动多代理系统模式 (提供商: {provider}, 模型: {model or '默认'})")
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建多代理系统
        mas = await create_assistant(
            assistant_type="multi_agent", 
            provider_name=provider, 
            model=model
        )
        
        # 创建并启动CLI界面
        cli = AgentCLI(mas, show_thinking=thinking, language="zh-CN")
        await cli.start()
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_custom_mode(provider, model, thinking, config_path):
    """运行自定义助手模式 - 使用MCP增强助手"""
    print(f"\n启动MCP增强助手模式 (提供商: {provider}, 模型: {model or '默认'})")
    
    if not config_path:
        config_path = input("请输入配置文件路径 (留空使用默认配置): ").strip()
    
    try:
        from ui.cli import AgentCLI
        from providers.assistant_factory import create_assistant
        
        # 使用助手工厂异步创建MCP增强助手
        assistant = await create_assistant(
            assistant_type="mcp", 
            provider_name=provider, 
            model=model,
            config_path=config_path
        )
        
        # 创建CLI界面进行交互
        cli = AgentCLI(assistant, show_thinking=thinking, language="zh-CN", config_path=config_path)
        await cli.start()
        
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

async def run_mcp_assistant(provider, model, thinking):
    """运行 MCP 增强助手模式"""
    print(f"\n启动 MCP 增强助手 (提供商: {provider}, 模型: {model or '默认'})")
    
    try:
        import asyncio
        from examples.mcp_enhanced_assistant import MCPEnhancedAssistant
        
        # 创建 MCP 助手实例
        assistant = await MCPEnhancedAssistant.create(
            name="MiniLuma",
            provider_name=provider,
            model=model
        )
        
        # 欢迎信息
        print(f"\n{assistant.name} 已准备就绪。输入'exit'或'quit'退出。")
        print("特殊命令:")
        print("- '-chat': 进入聊天模式（默认保存所有生成的文件）")
        print("- '-m <对话ID>': 恢复指定记忆/历史记录")
        print("- '-ai <内容>': 向特定AI模型请求回答")
        #print("- '-save': 保存当前对话生成的文件")
        print("-" * 50)
        
        # 默认模式标识
        chat_mode = False
        
        # 交互循环
        while True:
            # 获取用户输入
            prompt = "聊天模式" if chat_mode else "用户"
            user_input = input(f"{prompt}: ").strip()
            
            # 检查退出命令
            if user_input.lower() in ['exit', 'quit', 'q']:
                # 结束会话并保存状态
                await assistant.end_session()
                print("再见！")
                break
                
            # 检查模式切换命令
            if user_input.lower() == '-chat':
                chat_mode = not chat_mode
                mode_status = "已进入聊天模式" if chat_mode else "已退出聊天模式"
                print(f"\n{mode_status}（{'默认保存所有生成的文件' if chat_mode else '仅手动保存生成的文件'}）\n")
                continue
                
            # 在聊天模式下，自动添加-save前缀
            if chat_mode and not user_input.startswith('-'):
                # 处理用户输入
                response = await assistant.process(user_input)
                print(f"\n{assistant.name}: {response}\n")
                
                # 自动保存生成的文件
                save_result = await assistant._save_generated_files(None)
                if "成功保存" in save_result:
                    print(f"[系统] {save_result}\n")
            else:
                # 正常处理用户输入
                response = await assistant.process(user_input)
                print(f"\n{assistant.name}: {response}\n")
            
    except KeyboardInterrupt:
        print("\n程序已终止")
        # 保存状态
        await assistant.end_session()
    except Exception as e:
        print(f"错误: {str(e)}")
        import traceback
        traceback.print_exc()

def check_api_keys():
    """检查API密钥是否设置"""
    missing_providers = []
    
    # 检查默认提供商是否设置了API密钥
    default_provider = config.get_default_provider()
    if not config.is_api_key_set(default_provider):
        missing_providers.append(default_provider)
    
    if missing_providers:
        print("\n警告: 以下提供商的API密钥未设置:")
        for provider in missing_providers:
            print(f"- {provider.upper()}_API_KEY")
        
        print("\n请在config目录下的配置文件中设置API密钥。")
        print(f"您可以编辑 {os.path.join('config', 'config_global.toml')} 文件添加您的API密钥。")
        
        response = input("\n是否继续? (y/n): ").strip().lower()
        return response in ['y', 'yes']
    
    return True

async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="MiniLuma 中文界面")
    parser.add_argument(
        "--mode", "-m",
        type=int,
        choices=[1, 2, 3, 4],
        help="运行模式: 1=简单助手, 2=多代理系统, 3=自定义, 4=MCP增强助手"
    )
    parser.add_argument(
        "--provider", "-p",
        default=config.get_default_provider(),
        choices=["openai", "deepseek", "silicon_flow"],
        help="LLM提供商"
    )
    parser.add_argument(
        "--model",
        help="具体模型名称"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="显示代理思考过程"
    )
    parser.add_argument(
        "--config", "-c",
        help="配置文件路径 (仅适用于自定义模式)"
    )
    
    args = parser.parse_args()
    
    # 如果未指定模型，使用配置文件中的默认模型
    if not args.model:
        args.model = config.get_default_model(args.provider)
    
    # 检查API密钥
    if not check_api_keys():
        print("退出程序。")
        return 1
    
    # 如果未指定模式，显示欢迎界面并请求输入
    mode = args.mode
    if not mode:
        show_welcome()
        
        while True:
            choice = input("\n请选择一个模式 (1-4) 或输入 'q' 退出: ").strip().lower()
            
            if choice in ['q', 'exit']:
                print("退出程序。")
                return 0
            
            try:
                mode = int(choice)
                if 1 <= mode <= 4:
                    break
                else:
                    print("请输入有效的模式编号 (1-4)。")
            except ValueError:
                print("请输入有效的模式编号。")
    
    # 如果未指定思考模式，使用配置文件中的设置
    thinking = args.thinking
    if not thinking:
        thinking = config.get("global", "show_thinking", False)
    
    # 运行选定的模式
    if mode == 1:
        await run_simple_assistant(args.provider, args.model, thinking)
    elif mode == 2:
        await run_multi_agent(args.provider, args.model, thinking)
    elif mode == 3:
        await run_custom_mode(args.provider, args.model, thinking, args.config)
    elif mode == 4:
        await run_mcp_assistant(args.provider, args.model, thinking)
    
    return 0

if __name__ == "__main__":
    import asyncio
    sys.exit(asyncio.run(main()))
