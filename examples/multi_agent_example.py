"""
Multi-Agent example for the MiniLuma.
Demonstrates how to use multiple specialized agents to solve complex tasks.
"""
import os
import sys
import argparse
import re
from dotenv import load_dotenv

# Add parent directory to path to allow importing from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import ReactorAgent
from core.planner import TaskPlanner
from core.context import Context
from core.memory import Memory
from llm.openai import OpenAILLM
from llm.deepseek import DeepSeekLLM
from tools.base import tool, register_tool
from tools.file_tools import save_text, save_code, save_image, list_saved_files, get_session_dir
from utils.file_manager import FileManager
from ui.cli import AgentCLI
from utils.logger import ConversationLogger

# Load environment variables from .env file if present
load_dotenv()


@tool(name="web_search", description="Search the web for information")
def web_search(query: str) -> str:
    """
    Simulates searching the web for information.
    
    Args:
        query: The search query
        
    Returns:
        Search results
    """
    # This is a mock implementation
    return f"Found results for: {query}\n1. Wikipedia article on {query}\n2. Recent news about {query}\n3. Expert analysis of {query}"


@tool(name="code_executor", description="Execute Python code")
def code_executor(code: str) -> str:
    """
    Executes Python code and returns the result.
    
    Args:
        code: Python code to execute
        
    Returns:
        Execution result or error message
    """
    try:
        # Create a restricted local environment
        local_env = {}
        
        # Execute the code in a restricted environment
        exec(code, {"__builtins__": {}}, local_env)
        
        # If there's an output variable, return it
        if "output" in local_env:
            return str(local_env["output"])
        else:
            return "Code executed successfully, but no output variable was defined."
    except Exception as e:
        return f"Error executing code: {str(e)}"


# 创建全局文件管理器实例
file_manager = FileManager()


class ResearchAgent:
    """Research Agent, specialized in gathering and analyzing information.
    
    """
    
    def __init__(self, llm):
        """Initialize the Research Agent.
        
        Args:
            llm: Language model
        """
        self.llm = llm
        self.context = Context(max_history=10)
        self.memory = Memory(max_items=30)
        
        # Set system prompt
        system_prompt = """You are a Research Agent, specialized in gathering and analyzing information.
Your goal is to find relevant information and summarize it into a concise and accurate summary.
Use the web_search tool to search the web for relevant information."""
        self.context.set_system_prompt(system_prompt)
        
        # Register tools
        self.tools = {
            "web_search": web_search
        }
        
        # Create logger
        from utils.logger import ConversationLogger
        self.logger = ConversationLogger()
    
    async def process(self, task: str) -> str:
        """Process a research task.
        
        Args:
            task: Research task description
            
        Returns:
            Research results
        """
        # Log the task
        self.logger.log_system_event("研究任务", task)
        
        # Add task to context
        self.context.add_message("user", task)
        
        # Initialize reasoning cycles
        from core.reactor import Reactor
        reactor = Reactor(
            llm_service=self.llm,
            tools=self.tools,
            system_prompt=self.context.get_system_prompt()
        )
        
        # Process task with reactor pattern
        result = await reactor.process(task)
        
        # Format the response
        response = result.get("response", "")
        
        # Log the response
        self.logger.log("assistant", response, "研究助手")
        
        # Update context with response
        self.context.add_message("assistant", response)
        
        return response


class CodeAgent:
    """Code Agent, specialized in writing and debugging code.
    
    """
    
    def __init__(self, llm):
        """Initialize the Code Agent.
        
        Args:
            llm: Language model
        """
        self.llm = llm
        self.context = Context(max_history=10)
        self.memory = Memory(max_items=30)
        
        # Set system prompt
        system_prompt = """You are a Code Agent, specialized in writing and debugging code.
Your goal is to create efficient, readable, and bug-free code to solve a specified task.
Use the code_executor tool to test your code.
Ensure to save any important code, HTML, or other files to the file system."""
        self.context.set_system_prompt(system_prompt)
        
        # Register tools
        self.tools = {
            "code_executor": code_executor,
            "save_code": save_code,
            "save_text": save_text,
            "save_image": save_image,
            "list_saved_files": list_saved_files
        }
        
        # Create logger
        from utils.logger import ConversationLogger
        self.logger = ConversationLogger()
    
    async def process(self, task: str) -> str:
        """Process a coding task.
        
        Args:
            task: Coding task description
            
        Returns:
            Coding results and processing history
        """
        # Log the task
        self.logger.log_system_event("编码任务", task)
        
        # Add task to context
        self.context.add_message("user", task)
        
        # Initialize reasoning cycles
        from core.reactor import Reactor
        reactor = Reactor(
            llm_service=self.llm,
            tools=self.tools,
            system_prompt=self.context.get_system_prompt()
        )
        
        # Process task with reactor pattern
        result = await reactor.process(task)
        
        # Get the original response
        response = result.get("response", "")
        
        # Process code in response and save files
        processed_response = await self._process_and_save_code(response, task)
        
        # Log the processed response
        self.logger.log("assistant", processed_response, "代码助手")
        
        # Update context with processed response
        self.context.add_message("assistant", processed_response)
        
        return processed_response
    
    async def _process_and_save_code(self, response: str, task: str) -> str:
        """Automatically process response code, saving files with original AI-specified names.
        
        Args:
            response: Original response text
            task: Task description
            
        Returns:
            Processed response text
        """
        # Find all code blocks in markdown format
        code_blocks = re.finditer(r"```(\w*)\n(.*?)```", response, re.DOTALL)
        
        saved_files = []
        processed_response = response
        
        for match in code_blocks:
            lang = match.group(1).strip().lower()
            code = match.group(2)
            
            # Try to find filename in the text before the code block
            filename = None
            lines_before = response[:match.start()].split('\n')
            
            # Check the last 5 lines before the code block for a filename
            for line in lines_before[-5:]:
                filename_match = re.search(r'[`"]([^`"]+\.\w+)[`"]', line)
                if filename_match:
                    filename = filename_match.group(1)
                    break
                
                # Try alternative pattern for "filename: xxx.py" or "file: xxx.py"
                alt_match = re.search(r'(?:filename|file):\s*[\'"]*([^\s\'"]+)[\'"]*', line, re.IGNORECASE)
                if alt_match:
                    filename = alt_match.group(1)
                    break
            
            # If we found a filename and the code is not empty
            if filename and code.strip():
                # Determine file type
                if lang in ['python', 'py']:
                    save_func = save_code
                    if not filename.endswith('.py'):
                        filename += '.py'
                elif lang in ['html', 'htm']:
                    save_func = save_text
                    if not filename.endswith('.html'):
                        filename += '.html'
                elif lang in ['css']:
                    save_func = save_text
                    if not filename.endswith('.css'):
                        filename += '.css'
                elif lang in ['javascript', 'js']:
                    save_func = save_text
                    if not filename.endswith('.js'):
                        filename += '.js'
                else:
                    save_func = save_text
                
                # Save the file
                try:
                    save_result = save_func(filename, code)
                    saved_files.append(f"{filename}")
                    
                    # Add a note about the saved file
                    processed_response = processed_response.replace(
                        match.group(0),
                        f"{match.group(0)}\n\n> 已自动保存到文件: `{filename}`"
                    )
                except Exception as e:
                    # Add error information if saving failed
                    processed_response = processed_response.replace(
                        match.group(0),
                        f"{match.group(0)}\n\n> ❌ 保存失败: {str(e)}"
                    )
        
        # Add summary of saved files if any
        if saved_files:
            saved_files_text = "\n".join([f"- `{file}`" for file in saved_files])
            processed_response += f"\n\n### 已保存文件\n\n{saved_files_text}\n\n文件已保存到: {get_session_dir()}"
        
        return processed_response


class MultiAgentSystem:
    """Multi-Agent System, coordinating specialized agents to solve complex tasks.
    
    """
    
    async def __init__(self, provider: str = "openai", model: str = None):
        """Initialize the Multi-Agent System.
        
        Args:
            provider: Language model provider
            model: Specific model
        """
        # 从工厂函数获取LLM
        from providers.factory import create_provider
        self.llm = await create_provider(provider_name=provider, model=model)
        
        # Create file manager and ensure result directory exists
        self.file_manager = FileManager()
        self.session_dir = self.file_manager.get_session_dir()
        
        # Create specialized agents
        self.research_agent = ResearchAgent(self.llm)
        self.code_agent = CodeAgent(self.llm)
        
        # Create task planner
        self.planner = TaskPlanner(self.llm)
        
        # Map agent names to agent instances
        self.agents = {
            "research": self.research_agent,
            "code": self.code_agent
        }
        
        # Set up context and memory
        self.context = Context(max_history=10)
        self.memory = Memory(max_items=50)
        
        # Track execution history
        self.history = []
        
        # Create logger for conversation logging
        self.logger = ConversationLogger()
        
        # Add system prompt, including file save information
        system_prompt = f"""You are a Multi-Agent System that coordinates specialized agents to solve complex tasks.
You have access to the following agents:
1. Research Agent - for gathering and analyzing information
2. Code Agent - for writing and debugging code

All code and other generated artifacts will be saved in the following directory:
{self.session_dir}"""
        self.context.set_system_prompt(system_prompt)
    
    async def get_agent_capabilities(self) -> list:
        """Get the capabilities of available agents.
        
        Returns:
            Agent capabilities list
        """
        return [
            {
                "name": "research",
                "description": "Research Agent, specialized in gathering and analyzing information",
                "tools": [
                    {
                        "name": "web_search",
                        "description": "Search the web for information"
                    }
                ]
            },
            {
                "name": "code",
                "description": "Code Agent, specialized in writing and debugging code",
                "tools": [
                    {
                        "name": "code_executor",
                        "description": "Execute Python code and return the result"
                    },
                    {
                        "name": "save_code",
                        "description": "Save Python code file"
                    },
                    {
                        "name": "save_text",
                        "description": "Save text file"
                    },
                    {
                        "name": "save_image",
                        "description": "Save image file"
                    },
                    {
                        "name": "list_saved_files",
                        "description": "List saved files"
                    }
                ]
            }
        ]
    
    async def process(self, task: str) -> dict:
        """Process a complex task.
        
        Args:
            task: Complex task description
            
        Returns:
            Processing results and history
        """
        # 添加用户输入到上下文
        self.context.add_message("user", task)
        
        # 记录事件
        self.logger.log("user", task)
        
        # 记录起始任务
        self.history.append({"role": "user", "content": task})
        
        # 解析任务
        # 使用任务计划器分解任务
        self.logger.log_system_event("规划", "分解任务为子任务")
        plan_result = await self.planner.generate_plan(task)
        subtasks = plan_result["subtasks"]
        
        # 记录计划
        self.logger.log_system_event("计划", f"任务计划: {subtasks}")
        self.history.append({"role": "system", "content": f"任务计划: {subtasks}"})
        
        # 执行子任务
        results = []
        
        for i, subtask in enumerate(subtasks):
            self.logger.log_system_event("执行", f"正在执行子任务 {i+1}/{len(subtasks)}: {subtask['description']}")
            
            # 确定最适合的代理
            agent_name = subtask.get("agent", "")
            if not agent_name or agent_name not in self.agents:
                # 如果没有指定代理或代理不存在，尝试分配
                if "research" in subtask["description"].lower() or "information" in subtask["description"].lower():
                    agent_name = "research"
                elif "code" in subtask["description"].lower() or "programming" in subtask["description"].lower():
                    agent_name = "code"
                else:
                    agent_name = "research"  # 默认使用研究代理
            
            # 获取代理
            agent = self.agents[agent_name]
            
            # 执行子任务
            self.logger.log_system_event("代理", f"使用{agent_name}代理处理: {subtask['description']}")
            
            # 调用代理处理子任务
            result = await agent.process(subtask["description"])
            
            # 记录结果
            results.append({
                "task": subtask["description"],
                "agent": agent_name,
                "result": result
            })
            
            # 更新历史
            self.history.append({
                "role": "agent",
                "agent": agent_name,
                "content": f"子任务结果: {result}"
            })
            
            self.logger.log_system_event("完成", f"子任务 {i+1} 完成")
        
        # 格式化输出结果
        formatted_results = self._format_execution_results(results)
        
        # 添加结果到上下文
        self.context.add_message("assistant", formatted_results)
        
        # 记录助手响应
        self.logger.log("assistant", formatted_results)
        
        # 返回结果
        return {
            "response": formatted_results,
            "history": self.history,
            "results": results
        }

    async def respond(self, user_input: str) -> dict:
        """Simple response method for CLI interface.
        
        Args:
            user_input: User query or instruction
            
        Returns:
            AI assistant response
        """
        result = await self.process(user_input)
        return result["response"]
    
    def _format_execution_results(self, results: list) -> str:
        """Format execution results.
        
        Args:
            results: Execution results list
            
        Returns:
            Formatted execution results string
        """
        if not results:
            return "No execution results available."
        
        formatted_output = "# 🤖 Multi-Agent Execution Results\n\n"
        
        for result in results:
            task = result["task"]
            agent = result["agent"]
            output = result["result"]
            
            formatted_output += f"## Task: {task} (Agent: {agent})\n\n"
            formatted_output += f"Output: {output}\n\n"
            
            # Check if there are any saved files to mention
            if "File saved as:" in output:
                # The file information is already in the output
                pass
            elif "files saved" in output.lower():
                # The file information is already in the output
                pass
        
        formatted_output += "\n## 📋 Summary\n\n"
        formatted_output += f"✅ Successfully completed {len(results)} task(s) using our specialized agents.\n"
        formatted_output += f"💾 Results and generated files are saved in: {self.session_dir}\n"
        
        return formatted_output


def parse_args():
    """Parse command line arguments.
    
    Returns:
        Parsed arguments
    """
    parser = argparse.ArgumentParser(description="Multi-Agent System example")
    parser.add_argument(
        "--provider", "-p",
        default="openai",
        choices=["openai", "deepseek"],
        help="Language model provider"
    )
    parser.add_argument(
        "--model", "-m",
        help="Specific model"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="Show agent thinking process"
    )
    
    return parser.parse_args()


def main():
    """Main function, running the Multi-Agent System example."""
    args = parse_args()
    
    try:
        # Create the Multi-Agent System
        mas = MultiAgentSystem(args.provider, args.model)
        
        # Create and start the CLI
        cli = AgentCLI(mas, show_thinking=args.thinking)
        cli.start()
        
        return 0
    
    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
