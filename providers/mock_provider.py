"""
模拟LLM服务提供商
用于测试和开发，不需要真实API密钥
"""
import asyncio
from typing import Dict, List, Any, Optional
from .base import BaseLLMProvider

class MockLLMProvider(BaseLLMProvider):
    """模拟LLM服务提供商
    
    返回预设响应，用于测试系统功能，无需实际API调用
    """
    
    def __init__(self, model: str = "mock-model", **kwargs):
        """初始化模拟LLM提供商
        
        Args:
            model: 模型名称，默认为"mock-model"
            **kwargs: 其他参数
        """
        super().__init__(model, **kwargs)
        self.response_delay = kwargs.get("response_delay", 1.0)  # 模拟响应延迟（秒）
    
    async def generate(self, system_prompt: str = None, user_input: str = None, 
                     context: List[Dict[str, str]] = None, messages: List[Dict[str, str]] = None,
                     tools: List[Dict] = None, max_tokens: int = None, **kwargs) -> Dict[str, Any]:
        """生成模拟AI响应
        
        Args:
            system_prompt: 系统提示词
            user_input: 用户输入
            context: 上下文消息列表
            messages: 消息列表（新的统一接口参数）
            tools: 可用工具列表
            max_tokens: 最大生成令牌数
            **kwargs: 其他参数
            
        Returns:
            包含响应的字典
        """
        # 模拟思考延迟
        await asyncio.sleep(self.response_delay)
        
        # 处理新的messages格式
        if messages is not None:
            # 从messages中提取system_prompt和user_input
            for msg in messages:
                if msg.get("role") == "system":
                    system_prompt = msg.get("content", system_prompt)
                elif msg.get("role") == "user" and user_input is None:
                    user_input = msg.get("content", "")
        
        # 如果仍然没有user_input，使用默认值
        if user_input is None:
            user_input = "未提供用户输入"
        
        # 创建模拟响应
        thinking = f"思考过程：\n分析用户输入: '{user_input}'\n系统提示: '{system_prompt[:30] if system_prompt else 'None'}...'\n"
        thinking += "1. 理解用户问题\n2. 生成适当的回答\n3. 返回结果"
        
        # 如果提供了工具，添加到思考过程
        if tools:
            thinking += f"\n\n可用工具: {len(tools)}个"
            for tool in tools:
                thinking += f"\n- {tool.get('name', 'unknown')}: {tool.get('description', 'no description')}"
        
        # 基本固定回答（中文）
        response = f"这是来自模拟AI的回答。\n\n您的输入是: '{user_input}'\n\n"
        response += "由于目前使用的是模拟模式，无法提供真实的AI回答。"
        response += "这只是用于测试系统功能的示例响应。"
        
        # 如果输入中包含特定关键词，则生成特殊响应
        if "文件" in user_input or "代码" in user_input:
            response += "\n\n这是一个示例Python代码:\n\n```python\ndef hello_world():\n    print('你好，世界！')\n```"
        
        if "帮助" in user_input or "功能" in user_input:
            response += "\n\n## 系统功能\n\n- 支持对话\n- 代码生成和保存\n- 多代理协作\n- 工具调用"
            
        if "保存" in user_input and ("对话" in user_input or "聊天" in user_input):
            response += "\n\n我已经将对话保存到文件中。"
        
        # 考虑max_tokens限制
        if max_tokens is not None:
            # 简单模拟令牌数量限制
            char_per_token = 2  # 假设平均每个token约2个字符
            max_chars = max_tokens * char_per_token
            if len(response) > max_chars:
                response = response[:max_chars] + "...(已达到最大令牌数限制)"
        
        return {
            "response": response,
            "thinking": thinking,
            "tools": [],  # 模拟工具使用响应
            "terminal_output": "这是模拟的终端输出内容\n命令执行成功。"  # 模拟终端输出(中文)
        }
    
    def get_provider_name(self) -> str:
        """获取提供商名称
        
        Returns:
            提供商名称 "mock"
        """
        return "mock"
