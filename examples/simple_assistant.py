"""
Simple Assistant example for the MiniLuma.
Demonstrates basic usage of the framework to create a chatbot assistant.
"""
import os
import sys
import argparse
from dotenv import load_dotenv

# Add parent directory to path to allow importing from the project
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.agent import ReactorAgent
from core.reactor import Reactor
from core.context import Context
from core.memory import Memory
from llm.openai import OpenAILLM
from llm.deepseek import DeepSeekLLM
from llm.silicon_flow import SiliconFlowLLM
from tools.base import tool, register_tool
from ui.cli import AgentCLI


# Load environment variables from .env file if present
load_dotenv()


@tool(name="calculator", description="Perform basic arithmetic calculations")
def calculator(expression: str) -> str:
    """
    Evaluate a mathematical expression.
    
    Args:
        expression: A mathematical expression as a string
        
    Returns:
        The result of the calculation
    """
    try:
        # Use a safer eval with limited scope
        allowed_names = {"abs": abs, "max": max, "min": min, "round": round, "sum": sum}
        
        # Replace unsafe operations
        expression = expression.replace("^", "**")
        
        # Calculate and return the result
        result = eval(expression, {"__builtins__": {}}, allowed_names)
        return f"Result: {result}"
    except Exception as e:
        return f"Error: {str(e)}"


@tool(name="get_weather", description="Get current weather for a location")
def get_weather(location: str) -> str:
    """
    Get current weather information for a location.
    
    Args:
        location: The city or location to get weather for
        
    Returns:
        Weather information
    """
    # This is a mock implementation
    import random
    weather_types = ["Sunny", "Cloudy", "Rainy", "Snowy", "Partly Cloudy", "Windy"]
    temp = random.randint(0, 35)
    weather = random.choice(weather_types)
    humidity = random.randint(30, 95)
    
    return f"Weather for {location}:\nTemperature: {temp}°C\nConditions: {weather}\nHumidity: {humidity}%"


class SimpleAssistant:
    """A simple assistant using the MiniLuma.
    
    Demonstrates how to use the framework components to create
    a functional AI assistant with tool usage capabilities.
    """
    
    async def __init__(self, llm_provider: str = "openai", model: str = None):
        """Initialize the simple assistant.
        
        Args:
            llm_provider: LLM provider to use ("openai", "deepseek", or "silicon_flow")
            model: Specific model to use (provider-dependent)
        """
        # Create LLM based on provider
        self.llm = await self._create_llm(llm_provider, model)
        
        # Set up context and memory
        self.context = Context(max_history=10)
        self.memory = Memory(max_items=50)
        
        # Set system prompt
        system_prompt = """You are a helpful AI assistant that can answer questions and use tools.
When you don't know the answer or need more information, use the appropriate tool to help.
Always be respectful, honest, and helpful. If you're unsure, say so rather than making up information."""
        self.context.set_system_prompt(system_prompt)
        
        # Register tools
        self.tools = {
            "calculator": calculator,
            "get_weather": get_weather
        }
        
        # Create reactor for handling the conversation
        self.reactor = Reactor(
            llm_service=self.llm,
            tools=self.tools,
            system_prompt=system_prompt,
            max_iterations=5
        )
    
    async def _create_llm(self, provider: str, model: str = None):
        """Create an LLM instance based on the provider.
        
        Args:
            provider: LLM provider to use
            model: Specific model to use (provider-dependent)
            
        Returns:
            LLM instance
        """
        if provider == "openai":
            api_key = os.environ.get("OPENAI_API_KEY")
            model = model or "gpt-4"
            return OpenAILLM(model=model, api_key=api_key)
        
        elif provider == "deepseek":
            api_key = os.environ.get("DEEPSEEK_API_KEY")
            model = model or "deepseek-v3"
            # 使用异步初始化
            return await DeepSeekLLM.async_init(model=model, api_key=api_key)
        
        elif provider == "silicon_flow":
            api_key = os.environ.get("SILICONFLOW_API_KEY")
            model = model or "default"
            return SiliconFlowLLM(model=model, api_key=api_key)
        
        else:
            raise ValueError(f"Unsupported LLM provider: {provider}")
    
    async def process(self, user_input: str) -> dict:
        """Process a user input and return the response.
        
        Args:
            user_input: User query or instruction
            
        Returns:
            A dictionary containing the response and iteration history
        """
        # Update conversation context
        self.context.add_message("user", user_input)
        
        # Process with the reactor
        # 检查reactor.process是否是异步方法
        import inspect
        if inspect.iscoroutinefunction(self.reactor.process):
            result = await self.reactor.process(user_input)
        else:
            result = self.reactor.process(user_input)
            
        # 如果结果是协程对象，等待它完成
        if inspect.iscoroutine(result):
            result = await result
        
        # 确保结果的回复是字符串类型
        response = result["response"]
        if isinstance(response, dict) and "response" in response:
            response = response["response"]
        
        # Update conversation context with assistant response
        self.context.add_message("assistant", response)
        
        # Update memory with the latest interaction
        self.memory.update(
            thought={"query": user_input},
            result=response
        )
        
        # 更新结果中的响应以确保一致性
        result["response"] = response
        
        return result
    
    async def respond(self, user_input: str) -> str:
        """Simple response method for non-React usage.
        
        Args:
            user_input: User query or instruction
            
        Returns:
            Assistant response as a string
        """
        result = await self.process(user_input)
        return result["response"]
    
    def get_tools(self) -> list:
        """Get the list of available tools.
        
        Returns:
            List of tool schemas
        """
        tool_schemas = []
        for name, tool_func in self.tools.items():
            if hasattr(tool_func, "tool"):
                tool_schemas.append(tool_func.tool.get_schema())
        
        return tool_schemas
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.context.clear_history()


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Simple Assistant Example")
    parser.add_argument(
        "--provider", "-p",
        default="openai",
        choices=["openai", "deepseek", "silicon_flow"],
        help="LLM provider to use"
    )
    parser.add_argument(
        "--model", "-m",
        help="Model to use (provider-dependent)"
    )
    parser.add_argument(
        "--thinking", "-t",
        action="store_true",
        help="Show thinking process"
    )
    
    return parser.parse_args()


async def main():
    """Main function to run the simple assistant example."""
    args = parse_args()
    
    # Create and run the assistant
    provider = args.provider
    model = args.model
    
    # 使用工厂函数异步创建助手
    from providers.factory import create_assistant
    assistant = await create_assistant(assistant_type="simple", provider_name=provider, model=model)
    
    # 使用CLI进行交互
    from ui.cli import AgentCLI
    cli = AgentCLI(assistant, show_thinking=args.thinking)
    await cli.start()
    
    return 0


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
