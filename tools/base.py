"""
Base tools module for the MiniLuma.
Provides base classes and decorators for defining and using tools.
"""
import inspect
from abc import ABC, abstractmethod
from functools import wraps
from typing import Callable, Dict, List, Any, Optional, Union, Type

class Tool(ABC):
    """Base class for all tools in the framework.
    
    All tool implementations should inherit from this class
    and implement the execute method.
    """
    
    def __init__(self, name: str, description: str):
        """Initialize a tool.
        
        Args:
            name: A unique identifier for the tool
            description: A description of what the tool does
        """
        self.name = name
        self.description = description
    
    @abstractmethod
    def execute(self, **kwargs) -> Any:
        """Execute the tool functionality.
        
        Args:
            **kwargs: Tool-specific parameters
            
        Returns:
            The result of the tool execution (can be any type)
        """
        pass
    
    def get_schema(self) -> Dict:
        """Get the JSON Schema describing the tool.
        
        This is used for LLM function calling and documentation.
        
        Returns:
            A dictionary containing the tool's JSON Schema
        """
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }


class FunctionTool(Tool):
    """Tool implementation that wraps a function.
    
    Automatically generates schemas and documentation from
    the function signature and docstring.
    """
    
    def __init__(self, func: Callable, name: Optional[str] = None, description: Optional[str] = None):
        """Initialize a function tool.
        
        Args:
            func: The function to wrap
            name: Optional name for the tool (defaults to function name)
            description: Optional description (defaults to function docstring)
        """
        self.func = func
        name = name or func.__name__
        description = description or func.__doc__ or f"Tool {name}"
        super().__init__(name, description)
        
        # Analyze the function signature for schema generation
        self.signature = inspect.signature(func)
    
    def execute(self, **kwargs) -> Any:
        """Execute the wrapped function.
        
        Args:
            **kwargs: Parameters to pass to the function
            
        Returns:
            The result of the function call
        """
        return self.func(**kwargs)
    
    def get_schema(self) -> Dict:
        """Generate JSON Schema from function signature.
        
        Returns:
            A dictionary containing the tool's JSON Schema
        """
        parameters = {}
        required = []
        
        for param_name, param in self.signature.parameters.items():
            # Determine parameter type from annotation or default to string
            param_type = "string"
            param_description = f"Parameter {param_name}"
            
            if param.annotation != inspect.Parameter.empty:
                if param.annotation == int:
                    param_type = "integer"
                elif param.annotation == float:
                    param_type = "number"
                elif param.annotation == bool:
                    param_type = "boolean"
                elif param.annotation == list or param.annotation == List:
                    param_type = "array"
                elif param.annotation == dict or param.annotation == Dict:
                    param_type = "object"
            
            parameters[param_name] = {
                "type": param_type,
                "description": param_description
            }
            
            # If parameter has no default, it's required
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
        
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": parameters,
                "required": required
            }
        }


def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator for creating tools from functions.
    
    Similar to the @tool decorator in OpenMinus, this simplifies
    tool creation and registration.
    
    Args:
        name: Optional name for the tool (defaults to function name)
        description: Optional description (defaults to function docstring)
        
    Returns:
        A decorator function
    """
    def decorator(func: Callable) -> Callable:
        """Create a tool from the decorated function.
        
        Args:
            func: The function to convert to a tool
            
        Returns:
            The original function with a .tool attribute
        """
        func.tool = FunctionTool(func, name, description)
        
        @wraps(func)
        def wrapper(*args, **kwargs):
            return func(*args, **kwargs)
        
        wrapper.tool = func.tool
        return wrapper
    
    return decorator


class ToolRegistry:
    """Registry for managing and accessing tools.
    
    Provides centralized tool registration and discovery.
    """
    
    def __init__(self):
        """Initialize the tool registry."""
        self.tools: Dict[str, Tool] = {}
    
    def register(self, tool: Union[Tool, Callable]) -> None:
        """Register a tool with the registry.
        
        Args:
            tool: A Tool instance or a function decorated with @tool
        
        Raises:
            ValueError: If a tool with the same name is already registered
            TypeError: If the tool is not a valid Tool instance or decorated function
        """
        # Handle both Tool instances and decorated functions
        if isinstance(tool, Tool):
            tool_instance = tool
        elif hasattr(tool, 'tool') and isinstance(tool.tool, Tool):
            tool_instance = tool.tool
        else:
            raise TypeError("Tool must be a Tool instance or a function decorated with @tool")
        
        # Check for name conflicts
        if tool_instance.name in self.tools:
            raise ValueError(f"Tool with name '{tool_instance.name}' is already registered")
        
        # Register the tool
        self.tools[tool_instance.name] = tool_instance
    
    def get_tool(self, name: str) -> Optional[Tool]:
        """Get a tool by name.
        
        Args:
            name: The name of the tool to retrieve
            
        Returns:
            The tool if found, None otherwise
        """
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[Tool]:
        """Get all registered tools.
        
        Returns:
            A list of all registered tools
        """
        return list(self.tools.values())
    
    def get_all_schemas(self) -> List[Dict]:
        """Get JSON Schemas for all registered tools.
        
        Returns:
            A list of tool schemas
        """
        return [tool.get_schema() for tool in self.tools.values()]


# Global tool registry instance
registry = ToolRegistry()


def register_tool(tool: Union[Tool, Callable]) -> Union[Tool, Callable]:
    """Register a tool with the global registry.
    
    Can be used as a decorator or a function.
    
    Args:
        tool: A Tool instance or a function decorated with @tool
        
    Returns:
        The original tool for chaining
    """
    registry.register(tool)
    return tool
