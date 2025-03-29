"""
模型上下文协议(MCP)实现
基于OWL框架的MCP技术，用于标准化AI模型与工具和数据源的交互
"""
import json
import os
import uuid
from typing import Dict, List, Any, Optional, Callable, Union
import inspect

class MCPMessage:
    """
    MCP消息类，用于标准化AI模型与工具之间的通信
    """
    def __init__(self, role: str, content: str, metadata: Optional[Dict[str, Any]] = None):
        self.id = str(uuid.uuid4())
        self.role = role  # 'system', 'user', 'assistant', 'tool'
        self.content = content
        self.metadata = metadata or {}
        self.timestamp = self._get_timestamp()
    
    def _get_timestamp(self):
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典表示"""
        return {
            "id": self.id,
            "role": self.role,
            "content": self.content,
            "metadata": self.metadata,
            "timestamp": self.timestamp
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MCPMessage':
        """从字典创建消息实例"""
        msg = cls(data["role"], data["content"], data.get("metadata", {}))
        msg.id = data.get("id", msg.id)
        msg.timestamp = data.get("timestamp", msg.timestamp)
        return msg

class MCPTool:
    """
    MCP工具包装器，用于标准化工具的定义和调用过程
    支持同步和异步函数
    """
    def __init__(self, 
                name: str, 
                description: str, 
                func: Callable, 
                parameters: Dict[str, Any] = None):
        self.name = name
        self.description = description
        self.func = func
        self.parameters = parameters or self._infer_parameters(func)
        self.is_async = inspect.iscoroutinefunction(func)
    
    def _infer_parameters(self, func: Callable) -> Dict[str, Any]:
        """从函数签名推断参数模式"""
        import inspect
        sig = inspect.signature(func)
        parameters = {}
        
        for name, param in sig.parameters.items():
            # 跳过self参数
            if name == 'self':
                continue
                
            param_info = {"type": "string"}  # 默认类型
            
            # 尝试从类型注解获取更多信息
            if param.annotation != inspect.Parameter.empty:
                # 处理基本类型
                if param.annotation == str:
                    param_info["type"] = "string"
                elif param.annotation == int:
                    param_info["type"] = "integer"
                elif param.annotation == bool:
                    param_info["type"] = "boolean"
                elif param.annotation == float:
                    param_info["type"] = "number"
                elif param.annotation == list or param.annotation == List:
                    param_info["type"] = "array"
                    param_info["items"] = {"type": "string"}
                elif param.annotation == dict or param.annotation == Dict:
                    param_info["type"] = "object"
            
            # 检查默认值以推断参数是否必需
            if param.default == inspect.Parameter.empty:
                param_info["required"] = True
                
            parameters[name] = param_info
            
        return parameters
    
    def get_schema(self) -> Dict[str, Any]:
        """获取工具的Schema定义"""
        # 创建required字段列表，收集所有标记为required:true的参数名称
        required_params = []
        for name, info in self.parameters.items():
            # 如果参数标记为必需，添加到required列表
            if info.get("required", False):
                required_params.append(name)
                # 从参数信息中移除required字段，避免DeepSeek API的格式冲突
                if "required" in info:
                    del info["required"]
                    
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": required_params  # 确保这是一个数组
            }
        }
    
    async def execute(self, **kwargs) -> Any:
        """执行工具功能，支持同步和异步"""
        try:
            if self.is_async:
                # 如果是异步函数，使用await调用
                return await self.func(**kwargs)
            else:
                # 如果是同步函数，直接调用
                return self.func(**kwargs)
        except Exception as e:
            error_msg = f"调用工具 {self.name} 时出错: {str(e)}"
            print(error_msg)
            import traceback
            traceback.print_exc()
            return {"error": error_msg}

class MCPToolKit:
    """
    MCP工具包，管理多个MCP工具
    """
    def __init__(self):
        self.tools: Dict[str, MCPTool] = {}
    
    def register_tool(self, tool: Union[MCPTool, Callable], 
                     name: Optional[str] = None, 
                     description: Optional[str] = None) -> MCPTool:
        """注册工具到工具包"""
        # 如果是函数，将其包装为MCPTool
        if callable(tool) and not isinstance(tool, MCPTool):
            func_name = name or tool.__name__
            func_desc = description or tool.__doc__ or f"Tool {func_name}"
            tool = MCPTool(func_name, func_desc, tool)
        
        # 如果已存在同名工具，抛出异常
        if tool.name in self.tools:
            raise ValueError(f"Tool with name '{tool.name}' already registered")
        
        # 添加到工具集
        self.tools[tool.name] = tool
        return tool
    
    def get_tool(self, name: str) -> Optional[MCPTool]:
        """通过名称获取工具"""
        return self.tools.get(name)
    
    def get_all_tools(self) -> List[MCPTool]:
        """获取所有工具"""
        return list(self.tools.values())
    
    def get_all_schemas(self) -> List[Dict[str, Any]]:
        """获取所有工具的Schema"""
        return [tool.get_schema() for tool in self.tools.values()]

class MCPProtocol:
    """
    模型上下文协议(MCP)的核心实现
    整合了消息、工具和模型的交互
    """
    def __init__(self, llm_service, toolkit: Optional[MCPToolKit] = None):
        self.llm = llm_service
        self.toolkit = toolkit or MCPToolKit()
        self.conversation_history: List[MCPMessage] = []
        self.system_prompt = None
    
    def set_system_prompt(self, prompt: str):
        """设置系统提示"""
        self.system_prompt = prompt
        if self.conversation_history and self.conversation_history[0].role == "system":
            self.conversation_history[0].content = prompt
        else:
            system_msg = MCPMessage("system", prompt)
            self.conversation_history.insert(0, system_msg)
    
    def add_user_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """添加用户消息"""
        message = MCPMessage("user", content, metadata)
        self.conversation_history.append(message)
        return message
    
    def add_assistant_message(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """添加助手消息"""
        message = MCPMessage("assistant", content, metadata)
        self.conversation_history.append(message)
        return message
    
    def add_tool_message(self, content: str, tool_name: str, metadata: Optional[Dict[str, Any]] = None) -> MCPMessage:
        """添加工具消息"""
        metadata = metadata or {}
        metadata["tool_name"] = tool_name
        message = MCPMessage("tool", content, metadata)
        self.conversation_history.append(message)
        return message
    
    def format_messages_for_llm(self) -> List[Dict[str, Any]]:
        """将历史消息格式化为适合LLM的格式"""
        formatted_messages = []
        
        for msg in self.conversation_history:
            formatted_msg = {"role": msg.role, "content": msg.content}
            
            # 如果是工具消息，可能需要特殊处理
            if msg.role == "tool" and "tool_name" in msg.metadata:
                formatted_msg["name"] = msg.metadata["tool_name"]
                
            formatted_messages.append(formatted_msg)
            
        return formatted_messages
    
    async def generate_response(self, user_input: str) -> Dict[str, Any]:
        """使用MCP生成响应"""
        # 添加用户消息
        self.add_user_message(user_input)
        
        # 准备工具列表
        tools = self.toolkit.get_all_schemas()
        
        # 格式化消息历史
        messages = self.format_messages_for_llm()
        
        try:
            # 生成响应
            response = await self.llm.generate(
                messages=messages,
                tools=tools,
                max_tokens=2048
            )
            
            # 兼容性处理：确保response包含content字段
            if "content" not in response and "response" in response:
                response["content"] = response["response"]
            
            # 确保响应不是空值
            if not response or ("content" not in response and "tool_calls" not in response):
                print(f"警告: AI响应格式无效: {response}")
                return {
                    "response": "抱歉，AI模型没有返回有效响应。",
                    "content": "抱歉，AI模型没有返回有效响应。",
                    "error": "无效的响应格式"
                }
                
            # 处理响应
            if "tool_calls" in response and response["tool_calls"]:
                # 处理工具调用
                tool_messages = await self._process_tool_calls_async(response["tool_calls"])
                
                # 递归调用以获取最终响应
                return await self.generate_response("请根据工具执行结果继续回答")
            else:
                # 确保有content字段
                if "content" not in response:
                    if "response" in response:
                        response["content"] = response["response"]
                    else:
                        print(f"警告: AI响应缺少content字段，完整响应: {response}")
                        response["content"] = "抱歉，AI模型没有返回有效响应。"
                
                # 检查响应是否有效
                if not isinstance(response["content"], str):
                    print(f"警告: AI响应content不是字符串: {response['content']}")
                    response["content"] = str(response["content"])
                
                # 添加助手消息到对话历史
                self.add_assistant_message(response["content"])
                
                # 确保response也有response字段，以兼容旧代码
                if "response" not in response:
                    response["response"] = response["content"]
                
                return response
                
        except Exception as e:
            error_message = f"生成响应时出错: {str(e)}"
            print(f"错误: {error_message}")
            import traceback
            traceback.print_exc()
            
            # 返回错误信息
            return {
                "content": f"抱歉，处理您的请求时出现错误: {str(e)}",
                "response": f"抱歉，处理您的请求时出现错误: {str(e)}",
                "error": error_message
            }

    async def _process_tool_calls_async(self, tool_calls: List[Dict[str, Any]]) -> List[MCPMessage]:
        """异步处理工具调用"""
        tool_messages = []
        
        for call in tool_calls:
            # 从工具调用中提取工具名称和参数
            function_call = call.get("function", {})
            tool_name = function_call.get("name")
            
            if not tool_name:
                error_msg = f"工具调用中缺少工具名称: {call}"
                tool_msg = self.add_tool_message(
                    error_msg,
                    "unknown_tool",
                    {"error": True}
                )
                tool_messages.append(tool_msg)
                continue
                
            tool = self.toolkit.get_tool(tool_name)
            
            if not tool:
                error_msg = f"工具 '{tool_name}' 未找到"
                tool_msg = self.add_tool_message(
                    error_msg,
                    tool_name,
                    {"error": True}
                )
                tool_messages.append(tool_msg)
                continue
                
            # 解析工具参数
            arguments_str = function_call.get("arguments", "{}")
            try:
                if isinstance(arguments_str, dict):
                    arguments = arguments_str
                else:
                    arguments = json.loads(arguments_str)
            except json.JSONDecodeError:
                error_msg = f"无法解析工具参数: {arguments_str}"
                tool_msg = self.add_tool_message(
                    error_msg,
                    tool_name,
                    {"error": True}
                )
                tool_messages.append(tool_msg)
                continue
                
            # 执行工具
            try:
                # 检查工具的execute方法是否是异步的
                import inspect
                if inspect.iscoroutinefunction(tool.execute):
                    result = await tool.execute(**arguments)
                else:
                    result = tool.execute(**arguments)
                    
                # 将结果转换为字符串
                if not isinstance(result, str):
                    result = json.dumps(result, ensure_ascii=False)
                    
                tool_msg = self.add_tool_message(
                    result,
                    tool_name
                )
                tool_messages.append(tool_msg)
            except Exception as e:
                error_msg = f"工具执行错误: {str(e)}"
                tool_msg = self.add_tool_message(
                    error_msg,
                    tool_name,
                    {"error": True}
                )
                tool_messages.append(tool_msg)
                
        return tool_messages
    
    def clear_history(self):
        """清除历史记录，保留系统提示"""
        system_prompt = None
        if self.conversation_history and self.conversation_history[0].role == "system":
            system_prompt = self.conversation_history[0].content
            
        self.conversation_history = []
        
        if system_prompt:
            self.set_system_prompt(system_prompt)

# 创建MCP实用工具装饰器
def mcp_tool(name: Optional[str] = None, description: Optional[str] = None):
    """
    工具装饰器，类似于OpenMinus的@tool装饰器
    用于简化工具创建和注册
    """
    def decorator(func: Callable) -> Callable:
        func._mcp_tool = True
        func._tool_name = name or func.__name__
        func._tool_description = description or func.__doc__ or f"Tool {func._tool_name}"
        
        return func
    
    return decorator
