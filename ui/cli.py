"""
Command Line Interface for the MiniLuma.
Provides a simple CLI for interacting with agents.
"""
import argparse
import sys
import os
import json
from typing import Dict, List, Any, Optional
from colorama import init, Fore, Style
import asyncio

# 尝试导入readline (Unix系统) 或使用Windows替代方案
try:
    import readline  # For command history on Unix systems
except ImportError:
    # Windows系统不支持readline
    pass

import yaml

# 导入日志记录器和文件管理器
from utils.logger import ConversationLogger
from utils.file_manager import FileManager

# Initialize colorama for cross-platform colored terminal output
init()

class AgentCLI:
    """Command Line Interface for interacting with MiniLumas.
    
    Provides a user-friendly terminal interface with command history,
    colored output, and interactive prompting.
    """
    
    def __init__(self, 
                agent, 
                config_path: Optional[str] = None,
                show_thinking: bool = False,
                language: str = "en"):
        """Initialize the CLI.
        
        Args:
            agent: The agent instance to interact with
            config_path: Optional path to a configuration file
            show_thinking: Whether to display agent thinking process
            language: Interface language (en = English, zh = Chinese)
        """
        self.agent = agent
        self.config = self._load_config(config_path) if config_path else {}
        self.show_thinking = show_thinking
        self.language = language
        self.running = False
        self.history = []
        
        # 初始化日志记录器
        self.logger = ConversationLogger()
        
        # 初始化文件管理器
        self.file_manager = FileManager()
        
        # 获取会话目录，而不是创建
        self.session_dir = self.file_manager.get_session_dir()
        
        # Set prompt style
        self.user_prompt = f"{Fore.GREEN}You>{Style.RESET_ALL} "
        self.agent_prompt = f"{Fore.BLUE}Agent>{Style.RESET_ALL} "
        self.system_prompt = f"{Fore.YELLOW}System>{Style.RESET_ALL} "
        self.thinking_prompt = f"{Fore.CYAN}Thinking>{Style.RESET_ALL} "
    
    def _load_config(self, config_path: str) -> Dict:
        """Load configuration from file.
        
        Args:
            config_path: Path to the configuration file
            
        Returns:
            Dictionary containing the configuration
        """
        try:
            if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                with open(config_path, 'r', encoding='utf-8') as file:
                    return yaml.safe_load(file)
            elif config_path.endswith('.json'):
                with open(config_path, 'r', encoding='utf-8') as file:
                    return json.load(file)
            else:
                print(f"{self.system_prompt}Unsupported config file format. Using defaults.")
                return {}
        except Exception as e:
            print(f"{self.system_prompt}Error loading config: {str(e)}")
            return {}
    
    def _print_welcome(self):
        """Print welcome message and instructions."""
        if self.language == "zh":
            print(f"\n{Fore.CYAN}======================================")
            print(f"       MiniLuma CLI 界面       ")
            print(f"======================================{Style.RESET_ALL}")
            print(f"输入您的消息与代理交互。")
            print(f"特殊命令:")
            print(f"  {Fore.YELLOW}/exit{Style.RESET_ALL} - 退出程序")
            print(f"  {Fore.YELLOW}/help{Style.RESET_ALL} - 显示帮助信息")
            print(f"  {Fore.YELLOW}/clear{Style.RESET_ALL} - 清除对话历史")
            print(f"  {Fore.YELLOW}/thinking{Style.RESET_ALL} - 切换显示代理思考过程")
            print(f"  {Fore.YELLOW}/save <filename>{Style.RESET_ALL} - 保存对话到文件")
            print(f"  {Fore.YELLOW}/tools{Style.RESET_ALL} - 列出可用工具\n")
            
            # 显示会话目录信息
            session_dir = self.file_manager.get_session_dir()
            print(f"{self.system_prompt}会话结果将保存在: {session_dir}")
        else:
            print(f"\n{Fore.CYAN}======================================")
            print(f"       MiniLuma CLI Interface       ")
            print(f"======================================{Style.RESET_ALL}")
            print(f"Type your messages to interact with the agent.")
            print(f"Special commands:")
            print(f"  {Fore.YELLOW}/exit{Style.RESET_ALL} - Exit the program")
            print(f"  {Fore.YELLOW}/help{Style.RESET_ALL} - Show this help message")
            print(f"  {Fore.YELLOW}/clear{Style.RESET_ALL} - Clear the conversation history")
            print(f"  {Fore.YELLOW}/thinking{Style.RESET_ALL} - Toggle display of agent thinking")
            print(f"  {Fore.YELLOW}/save <filename>{Style.RESET_ALL} - Save conversation to file")
            print(f"  {Fore.YELLOW}/tools{Style.RESET_ALL} - List available tools\n")
            
            # 显示会话目录信息
            session_dir = self.file_manager.get_session_dir()
            print(f"{self.system_prompt}Session results will be saved in: {session_dir}")
    
    def _process_command(self, command: str) -> bool:
        """Process special commands.
        
        Args:
            command: The command to process
            
        Returns:
            True if the session should continue, False if it should end
        """
        parts = command.split()
        cmd = parts[0].lower()
        
        if cmd == "/exit":
            # 保存日志记录
            self.logger.save_complete_log()
            if self.language == "zh":
                print(f"{self.system_prompt}再见！")
            else:
                print(f"{self.system_prompt}Goodbye!")
            return False
        
        elif cmd == "/help":
            if self.language == "zh":
                print(f"{self.system_prompt}特殊命令:")
                print(f"  {Fore.YELLOW}/exit{Style.RESET_ALL} - 退出程序")
                print(f"  {Fore.YELLOW}/help{Style.RESET_ALL} - 显示帮助信息")
                print(f"  {Fore.YELLOW}/clear{Style.RESET_ALL} - 清除对话历史")
                print(f"  {Fore.YELLOW}/thinking{Style.RESET_ALL} - 切换显示代理思考过程")
                print(f"  {Fore.YELLOW}/save <filename>{Style.RESET_ALL} - 保存对话到文件")
                print(f"  {Fore.YELLOW}/tools{Style.RESET_ALL} - 列出可用工具")
                print(f"  {Fore.YELLOW}/results{Style.RESET_ALL} - 显示当前会话结果目录")
            else:
                print(f"{self.system_prompt}Special commands:")
                print(f"  {Fore.YELLOW}/exit{Style.RESET_ALL} - Exit the program")
                print(f"  {Fore.YELLOW}/help{Style.RESET_ALL} - Show this help message")
                print(f"  {Fore.YELLOW}/clear{Style.RESET_ALL} - Clear the conversation history")
                print(f"  {Fore.YELLOW}/thinking{Style.RESET_ALL} - Toggle display of agent thinking")
                print(f"  {Fore.YELLOW}/save <filename>{Style.RESET_ALL} - Save conversation to file")
                print(f"  {Fore.YELLOW}/tools{Style.RESET_ALL} - List available tools")
                print(f"  {Fore.YELLOW}/results{Style.RESET_ALL} - Show the current session results directory")
            # 记录日志
            self.logger.log_system_event("帮助", "用户查看了帮助信息")
        
        elif cmd == "/clear":
            # Clear conversation history if the agent supports it
            if hasattr(self.agent, 'clear_history'):
                self.agent.clear_history()
            self.history = []
            if self.language == "zh":
                print(f"{self.system_prompt}对话历史已清除。")
            else:
                print(f"{self.system_prompt}Conversation history cleared.")
            # 记录日志
            self.logger.log_system_event("清除历史", "用户清除了对话历史")
        
        elif cmd == "/thinking":
            self.show_thinking = not self.show_thinking
            if self.language == "zh":
                print(f"{self.system_prompt}代理思考过程显示: {'开启' if self.show_thinking else '关闭'}")
            else:
                print(f"{self.system_prompt}Agent thinking display: {'ON' if self.show_thinking else 'OFF'}")
            # 记录日志
            self.logger.log_system_event("思考显示", f"用户{'开启' if self.show_thinking else '关闭'}了代理思考过程显示")
        
        elif cmd == "/save":
            if len(parts) < 2:
                if self.language == "zh":
                    print(f"{self.system_prompt}请指定文件名: /save <filename>")
                else:
                    print(f"{self.system_prompt}Please specify a filename: /save <filename>")
            else:
                filename = parts[1]
                if not filename.endswith(('.txt', '.json')):
                    filename += '.txt'
                self._save_conversation(filename)
                # 记录日志
                self.logger.log_system_event("保存对话", f"用户将对话保存到文件: {filename}")
        
        elif cmd == "/tools":
            self._list_tools()
            # 记录日志
            self.logger.log_system_event("工具列表", "用户查看了可用工具列表")
        
        elif cmd == "/results":
            # 显示当前会话结果目录
            session_dir = self.file_manager.get_session_dir()
            if self.language == "zh":
                print(f"{self.system_prompt}当前会话结果目录: {session_dir}")
            else:
                print(f"{self.system_prompt}Current session results directory: {session_dir}")
            
            # 列出已保存的文件
            files = os.listdir(session_dir)
            if files:
                if self.language == "zh":
                    print(f"{self.system_prompt}当前已保存的文件:")
                else:
                    print(f"{self.system_prompt}Files saved in this session:")
                for i, file in enumerate(files, 1):
                    file_path = os.path.join(session_dir, file)
                    if os.path.isfile(file_path):
                        size = os.path.getsize(file_path)
                        if self.language == "zh":
                            print(f"  {i}. {file} ({size} bytes)")
                        else:
                            print(f"  {i}. {file} ({size} bytes)")
            else:
                if self.language == "zh":
                    print(f"{self.system_prompt}当前会话尚未保存任何文件。")
                else:
                    print(f"{self.system_prompt}No files saved in this session.")
            
            # 记录日志
            self.logger.log_system_event("结果目录", "用户查看了当前会话结果目录")
        
        else:
            if self.language == "zh":
                print(f"{self.system_prompt}未知命令: {cmd}")
            else:
                print(f"{self.system_prompt}Unknown command: {cmd}")
            # 记录日志
            self.logger.log_system_event("未知命令", f"用户输入了未知命令: {cmd}")
        
        return True
    
    async def _save_conversation(self, filename: str):
        """Save the conversation history to a file.
        
        Args:
            filename: The name of the file to save to
        """
        try:
            with open(filename, 'w', encoding='utf-8') as file:
                for entry in self.history:
                    role = "User" if entry["role"] == "user" else "Agent"
                    file.write(f"{role}: {entry['content']}\n\n")
            if self.language == "zh":
                print(f"{self.system_prompt}对话已保存到 {filename}")
            else:
                print(f"{self.system_prompt}Conversation saved to {filename}")
        except Exception as e:
            if self.language == "zh":
                print(f"{self.system_prompt}保存对话失败: {str(e)}")
            else:
                print(f"{self.system_prompt}Error saving conversation: {str(e)}")
            # 记录日志
            self.logger.log_system_event("保存错误", f"保存对话到文件 {filename} 时出错: {str(e)}")
    
    def _list_tools(self):
        """List the tools available to the agent."""
        if hasattr(self.agent, 'get_tools'):
            tools = self.agent.get_tools()
            if tools:
                if self.language == "zh":
                    print(f"{self.system_prompt}可用工具:")
                else:
                    print(f"{self.system_prompt}Available tools:")
                for i, tool in enumerate(tools, 1):
                    name = tool.get("name", f"Tool {i}")
                    desc = tool.get("description", "No description available")
                    if self.language == "zh":
                        print(f"  {Fore.YELLOW}{name}{Style.RESET_ALL}: {desc}")
                    else:
                        print(f"  {Fore.YELLOW}{name}{Style.RESET_ALL}: {desc}")
            else:
                if self.language == "zh":
                    print(f"{self.system_prompt}无可用工具。")
                else:
                    print(f"{self.system_prompt}No tools available.")
        else:
            if self.language == "zh":
                print(f"{self.system_prompt}该代理不提供工具信息。")
            else:
                print(f"{self.system_prompt}This agent doesn't provide tool information.")
    
    async def start(self):
        """Start the CLI interactive session."""
        self._print_welcome()
        self.running = True
        
        # 创建新的日志文件
        log_file = self.logger.create_log_file()
        self.logger.log_system_event("会话开始", f"日志文件: {log_file}")
        
        # 记录会话目录
        session_dir = self.file_manager.get_session_dir()
        self.logger.log_system_event("会话目录", f"结果将保存在: {session_dir}")
        
        while self.running:
            try:
                # Get user input
                user_input = input(self.user_prompt).strip()
                
                # Check if it's a special command
                if user_input.startswith("/"):
                    self.running = self._process_command(user_input)
                    continue
                
                # Skip empty inputs
                if not user_input:
                    continue
                
                # Add to history
                self.history.append({"role": "user", "content": user_input})
                
                # 记录用户输入到日志
                self.logger.log("user", user_input)
                
                # Process the input with the agent
                if hasattr(self.agent, 'process'):
                    # 检查process方法是否为异步方法
                    import inspect
                    is_async = inspect.iscoroutinefunction(self.agent.process)
                    
                    if is_async:
                        # 处理异步方法
                        result = await self.agent.process(user_input)
                    else:
                        # 处理同步方法
                        result = self.agent.process(user_input)
                    
                    # 检查result的类型，防止协程对象没有被await
                    if inspect.iscoroutine(result):
                        # 如果返回了一个协程但是没有await
                        self.logger.log_system_event("警告", "agent.process返回了一个协程但没有被正确await")
                        result = await result
                    
                    # Display thinking if available and enabled
                    if self.show_thinking and isinstance(result, dict) and 'thinking' in result and result['thinking']:
                        print(f"\n{self.thinking_prompt} {result['thinking']}\n")
                        # 记录思考过程到日志
                        self.logger.log_system_event("思考过程", result['thinking'])
                    
                    # Display the agent's response
                    if isinstance(result, dict) and 'response' in result:
                        print(f"{self.agent_prompt} {result['response']}")
                        # Add to history
                        self.history.append({"role": "assistant", "content": result['response']})
                        # 记录代理回复到日志
                        self.logger.log("assistant", result['response'])
                    elif isinstance(result, str):
                        # 如果返回了字符串而不是字典
                        print(f"{self.agent_prompt} {result}")
                        # Add to history
                        self.history.append({"role": "assistant", "content": result})
                        # 记录代理回复到日志
                        self.logger.log("assistant", result)
                    else:
                        # 处理其他返回类型
                        response_text = str(result)
                        print(f"{self.agent_prompt} {response_text}")
                        self.history.append({"role": "assistant", "content": response_text})
                        self.logger.log("assistant", response_text)
                else:
                    # For simpler agents that just return a response string
                    # 检查respond方法是否为异步方法
                    import inspect
                    is_async = hasattr(self.agent, 'respond') and inspect.iscoroutinefunction(self.agent.respond)
                    
                    if is_async:
                        response = await self.agent.respond(user_input)
                    else:
                        response = self.agent.respond(user_input)
                    
                    # 检查response的类型，防止协程对象没有被await
                    if inspect.iscoroutine(response):
                        response = await response
                        
                    print(f"{self.agent_prompt} {response}")
                    # Add to history
                    self.history.append({"role": "assistant", "content": response})
                    # 记录代理回复到日志
                    self.logger.log("assistant", response)
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully
                print("\n")
                if self.language == "zh":
                    print(f"{self.system_prompt}用户中断了对话。输入 /exit 退出。")
                else:
                    print(f"{self.system_prompt}Interrupted by user. Type /exit to quit.")
                # 记录日志
                self.logger.log_system_event("中断", "用户中断了对话")
            
            except Exception as e:
                if self.language == "zh":
                    print(f"{self.system_prompt}错误: {str(e)}")
                else:
                    print(f"{self.system_prompt}Error: {str(e)}")
                # 记录日志
                self.logger.log_system_event("错误", f"处理用户输入时出错: {str(e)}")
        
        # 会话结束时保存完整日志
        self.logger.save_complete_log()


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="MiniLuma CLI")
    parser.add_argument(
        "--model", "-m",
        default="gpt-4",
        help="Model to use (default: gpt-4)"
    )
    parser.add_argument(
        "--config", "-c",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="Show agent thinking process"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    parser.add_argument(
        "--language", "-l",
        default="en",
        help="Interface language (en = English, zh = Chinese)"
    )
    
    return parser.parse_args()


async def main():
    """Main function to run the CLI."""
    args = parse_args()
    
    # Import here to avoid circular imports
    from ..core.agent import ReactorAgent
    from ..llm.openai import OpenAILLM
    
    try:
        # Check for API key
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print(f"{Fore.RED}Error: OPENAI_API_KEY environment variable not set.{Style.RESET_ALL}")
            print("Please set your OpenAI API key with:")
            print("  export OPENAI_API_KEY=your-key  # for Linux/MacOS")
            print("  set OPENAI_API_KEY=your-key     # for Windows CMD")
            print("  $env:OPENAI_API_KEY='your-key'  # for Windows PowerShell")
            return 1
        
        # Create LLM service
        llm = OpenAILLM(model=args.model)
        
        # Create the agent
        agent = ReactorAgent(llm)
        
        # Create and start the CLI
        cli = AgentCLI(agent, args.config, args.thinking, args.language)
        await cli.start()
        
        return 0
    
    except Exception as e:
        print(f"{Fore.RED}Error: {str(e)}{Style.RESET_ALL}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
