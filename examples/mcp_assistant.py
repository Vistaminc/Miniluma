"""
基于MCP技术
"""
import os
import sys
import asyncio
from dotenv import load_dotenv

# 添加项目根目录到路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入MCP相关模块
from core.mcp import MCPMessage, MCPProtocol, mcp_tool
from core.mcp_agent import MCPAgent
from core.mcp_system import MCPSystem, TaskPlanner
from tools.mcp_tools import get_all_mcp_tools
from core.config import Config

# 导入LLM服务
from providers.factory import create_provider

# 加载环境变量
load_dotenv()

# 获取配置
config = Config()

class MCPAssistant:
    """
    基于MCP技术的智能助手
    """
    def __init__(self, 
                provider_name: str = None, 
                model: str = None,
                multi_agent: bool = False):
        """初始化MCP助手
        
        Args:
            provider_name: LLM提供商名称
            model: 模型名称
            multi_agent: 是否启用多智能体模式
        """
        # 获取默认提供商和模型
        if not provider_name:
            provider_name = config.get_default_provider()
        if not model:
            model = config.get_default_model(provider_name)
            
        # 创建LLM服务
        self.llm_provider = create_provider(provider_name, model)
        
        # 获取所有MCP工具
        self.tools = get_all_mcp_tools()
        
        # 设置系统提示
        self.system_prompt = """你是一个功能强大的AI助手，集成了多种工具和能力。
你可以帮助用户解决各种复杂问题，从信息搜索到代码编写，从数据分析到文档处理。
当回答问题时，请尽可能提供全面、准确、有用的信息。
如果你不确定某个答案，不要编造信息，而是坦率地说明你不知道。
如果需要额外信息或工具来帮助用户，请灵活使用你可用的工具。
"""
        
        # 多智能体模式
        self.multi_agent = multi_agent
        
        if multi_agent:
            # 初始化多智能体系统
            self.agent_system = MCPSystem(
                llm_service=self.llm_provider,
                tools=self.tools
            )
            
            # 设置角色特定的系统提示
            self.agent_roles = {
                "coordinator": """你是一个协调者，负责整合各个专家的工作成果，确保任务顺利完成。
你需要理解用户的整体目标，并确保所有子任务共同推进这一目标。
以清晰、专业的语言总结各专家的工作成果，提供全面的回应。""",

                "researcher": """你是一个研究专家，擅长收集和分析信息。
你善于使用搜索工具，快速找到相关资料，并对信息进行评估和组织。
提供详尽、准确的研究结果，确保信息的可靠性和相关性。""",

                "coder": """你是一个编程专家，擅长编写和调试代码。
你精通多种编程语言和框架，能够快速实现各种功能和解决技术问题。
编写清晰、高效、可维护的代码，并提供详细的注释和说明。""",

                "writer": """你是一个写作专家，擅长撰写各类文档和内容。
你能将复杂的概念转化为易于理解的文字，并根据需要调整写作风格和格式。
创作流畅、准确、引人入胜的内容，注重文档的结构和可读性。""",

                "general": """你是一个多领域专家，可以处理各种通用任务。
你拥有广泛的知识基础，能够灵活应对各种需求。
提供综合性的解决方案，并根据需要调用合适的工具。"""
            }
        else:
            # 单智能体模式
            self.agent = MCPAgent(
                name="mcp_assistant",
                llm_service=self.llm_provider,
                tools=self.tools,
                system_prompt=self.system_prompt
            )
    
    async def process(self, user_input: str) -> str:
        """处理用户输入
        
        Args:
            user_input: 用户输入文本
            
        Returns:
            助手响应
        """
        if self.multi_agent:
            # 多智能体处理
            result = await self.agent_system.process(user_input)
            return result.get("summary", "处理过程中发生错误，请重试。")
        else:
            # 单智能体处理
            return await self.agent.process(user_input)
    
    def get_tools_info(self) -> str:
        """获取所有可用工具的信息
        
        Returns:
            工具信息文本
        """
        if self.multi_agent:
            tools = []
            for tool_func in self.tools:
                if hasattr(tool_func, '_tool_name'):
                    tools.append({
                        "name": tool_func._tool_name,
                        "description": tool_func._tool_description
                    })
        else:
            tools = self.agent.get_tools()
            
        # 格式化工具信息
        tools_info = "可用工具列表:\n\n"
        for tool in tools:
            tools_info += f"- {tool['name']}: {tool.get('description', '无描述')}\n"
            
        return tools_info
    
    def clear_history(self):
        """清除对话历史"""
        if not self.multi_agent:
            self.agent.clear_history()

class MCPAssistantCLI:
    """MCP助手的命令行界面"""
    
    def __init__(self, assistant: MCPAssistant, show_thinking: bool = False):
        """初始化命令行界面
        
        Args:
            assistant: MCP助手实例
            show_thinking: 是否显示思考过程
        """
        self.assistant = assistant
        self.show_thinking = show_thinking
        
    async def start(self):
        """启动交互式CLI会话"""
        print("\n" + "=" * 60)
        print(" 欢迎使用MCP智能助手 ".center(60, "="))
        print("=" * 60)
        
        # 显示可用工具
        print("\n" + self.assistant.get_tools_info())
        
        print("\n输入 'exit' 或 'quit' 结束会话")
        print("输入 'tools' 查看可用工具")
        print("输入 'clear' 清除对话历史")
        print("=" * 60 + "\n")
        
        while True:
            try:
                # 获取用户输入
                user_input = input("\n> 用户: ")
                
                # 处理特殊命令
                if user_input.lower() in ['exit', 'quit', '退出']:
                    print("\n感谢使用MCP智能助手！再见！")
                    break
                elif user_input.lower() in ['tools', '工具']:
                    print("\n" + self.assistant.get_tools_info())
                    continue
                elif user_input.lower() in ['clear', '清除']:
                    self.assistant.clear_history()
                    print("\n已清除对话历史")
                    continue
                
                # 处理常规输入
                print("\n处理中...")
                response = await self.assistant.process(user_input)
                
                # 打印响应
                print(f"\n> 助手: {response}\n")
                
            except KeyboardInterrupt:
                print("\n\n操作被中断。感谢使用MCP智能助手！再见！")
                break
            except Exception as e:
                print(f"\n处理请求时发生错误: {str(e)}")
                import traceback
                traceback.print_exc()
                print("\n请重试或检查配置。")

async def main_async():
    """异步主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description="MCP智能助手示例")
    parser.add_argument(
        "--provider", "-p",
        default=config.get_default_provider(),
        help="LLM提供商名称"
    )
    parser.add_argument(
        "--model", "-m",
        help="模型名称"
    )
    parser.add_argument(
        "--multi-agent",
        action="store_true",
        help="启用多智能体模式"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="显示思考过程"
    )
    
    args = parser.parse_args()
    
    # 创建MCP助手
    assistant = MCPAssistant(
        provider_name=args.provider,
        model=args.model,
        multi_agent=args.multi_agent
    )
    
    # 创建CLI界面
    cli = MCPAssistantCLI(
        assistant=assistant,
        show_thinking=args.thinking
    )
    
    # 启动会话
    await cli.start()

def main():
    """主函数"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
