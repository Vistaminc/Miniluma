"""
MCP智能体实现，基于OWL和OpenManus的MCP技术
提供标准化的AI模型交互和工具调用能力
"""
import json
import os
import asyncio
from typing import Dict, List, Any, Optional, Callable, Union

from .agent import BaseAgent
from .mcp import MCPProtocol, MCPToolKit, MCPTool, mcp_tool

class MCPAgent(BaseAgent):
    """
    基于MCP协议的智能体实现
    
    整合了OWL框架的MCP技术，实现标准化的AI模型交互，
    支持多模态处理、工具调用和各种外部API集成
    """
    
    def __init__(self, 
                name: str, 
                llm_service,
                tools: Optional[List[Union[MCPTool, Callable]]] = None,
                system_prompt: str = "",
                **kwargs):
        """初始化MCP智能体
        
        Args:
            name: 智能体名称
            llm_service: 语言模型服务
            tools: 工具列表
            system_prompt: 系统提示词
            **kwargs: 额外参数
        """
        super().__init__(name)
        
        # 创建工具包
        self.toolkit = MCPToolKit()
        
        # 注册工具
        if tools:
            for tool in tools:
                if callable(tool) and hasattr(tool, '_mcp_tool'):
                    self.toolkit.register_tool(
                        tool, 
                        name=getattr(tool, '_tool_name', None), 
                        description=getattr(tool, '_tool_description', None)
                    )
                elif isinstance(tool, MCPTool):
                    self.toolkit.register_tool(tool)
                elif callable(tool):
                    self.toolkit.register_tool(tool)
        
        # 创建MCP协议处理器
        self.mcp = MCPProtocol(llm_service, self.toolkit)
        if system_prompt:
            self.mcp.set_system_prompt(system_prompt)
        
        # 用于存储当前思考和行动
        self.current_thought = None
        self.current_action = None
        
        # 存储调用历史
        self.call_history = []
    
    def think(self, input_data: Any) -> Dict:
        """处理输入数据并决定下一步行动
        
        Args:
            input_data: 输入数据 (用户查询、系统状态等)
            
        Returns:
            包含智能体思考过程和决策的字典
        """
        # 对于MCP智能体，思考过程是异步的，这里我们仅设置输入
        self.current_thought = {
            "input": input_data,
            "tools_available": len(self.toolkit.get_all_tools()),
            "processing_status": "pending"
        }
        return self.current_thought
    
    async def think_async(self, input_data: str) -> Dict[str, Any]:
        """异步思考过程
        
        Args:
            input_data: 需要处理的输入
            
        Returns:
            思考结果
        """
        # 调用MCP生成响应
        result = await self.mcp.generate_response(input_data)
        
        # 兼容性处理：确保result有response字段
        if "response" not in result:
            if "content" in result:
                result["response"] = result["content"]
            else:
                print(f"警告: MCP响应格式异常: {result}")
                result["response"] = "处理请求时出现错误，响应格式不正确"
        
        # 更新思考状态
        self.current_thought = {
            "input": input_data,
            "output": result["response"],
            "processing_status": "complete",
            "history": result.get("history", [])
        }
        
        # 记录调用历史
        self.call_history.append({
            "input": input_data,
            "output": result["response"],
            "timestamp": self._get_timestamp()
        })
        
        return self.current_thought
    
    def act(self, thought: Dict) -> Any:
        """基于思考过程执行行动
        
        Args:
            thought: think()方法的输出
            
        Returns:
            行动结果
        """
        # 由于MCP的异步特性，这个方法主要返回最近的处理结果
        if thought.get("processing_status") == "complete":
            self.current_action = {
                "action_type": "response",
                "content": thought.get("output", ""),
                "status": "complete"
            }
        else:
            self.current_action = {
                "action_type": "thinking",
                "status": "pending"
            }
        
        return self.current_action
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """处理用户输入并返回响应
        
        一个便捷方法，组合了think_async和act
        
        Args:
            user_input: 用户输入
            
        Returns:
            包含响应内容的字典或响应文本
        """
        thought = await self.think_async(user_input)
        action = self.act(thought)
        
        # 返回包含响应内容的字典，便于调用者提取更多信息
        if isinstance(action, dict) and "content" in action:
            return {
                "response": action["content"],
                "action": action,
                "thought": thought
            }
        
        # 兼容性返回，如果无法提取内容，返回空字符串
        return {"response": action.get("content", "")}
    
    def register_tool(self, tool: Union[MCPTool, Callable], 
                     name: Optional[str] = None, 
                     description: Optional[str] = None) -> MCPTool:
        """注册工具到智能体
        
        Args:
            tool: 要注册的工具或函数
            name: 可选工具名称
            description: 可选工具描述
            
        Returns:
            注册的MCPTool实例
        """
        return self.toolkit.register_tool(tool, name, description)
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表
        
        Returns:
            工具Schema列表
        """
        return self.toolkit.get_all_schemas()
    
    def clear_history(self):
        """清除对话历史"""
        self.mcp.clear_history()
        
    def _get_timestamp(self):
        """获取当前时间戳"""
        import datetime
        return datetime.datetime.now().isoformat()
