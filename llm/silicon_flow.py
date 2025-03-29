"""
Silicon Flow (硅基流动) LLM implementation for the MiniLuma.
Provides integration with Silicon Flow's API for language models.
"""
from typing import Dict, List, Any, Optional, Union
import json
import os
import requests
from .base import BaseLLM
from core.config import config

class SiliconFlowLLM(BaseLLM):
    """Silicon Flow (硅基流动) language model implementation.
    
    Supports text generation and function calling with Silicon Flow's API.
    """
    
    def __init__(self, 
                model: Optional[str] = None, 
                api_key: Optional[str] = None,
                base_url: Optional[str] = None):
        """Initialize the Silicon Flow LLM.
        
        Args:
            model: The model identifier to use
            api_key: API key for authentication
            base_url: Base URL for API calls
        """
        # 获取配置
        sf_config = config.get_llm_config("silicon_flow")
        
        self.model = model or sf_config.get("model", "sf-plus")
        self.api_key = api_key or sf_config.get("api_key")
        self.base_url = base_url or sf_config.get("base_url", "https://api.siliconflow.cn/v1/")
        
        # 获取其他模型参数
        self.max_tokens = sf_config.get("max_tokens", 4096)
        self.temperature = sf_config.get("temperature", 0.7)
        self.top_p = sf_config.get("top_p", 0.95)
        
        # 确保API路径末尾有斜杠
        if self.base_url and not self.base_url.endswith("/"):
            self.base_url += "/"
            
        # 确保API密钥被设置
        if not self.api_key:
            raise ValueError("Silicon Flow API key not set. Please set SILICONFLOW_API_KEY in your configuration file or environment variables.")
    
    def generate(self, 
                system_prompt: str = "", 
                user_input: str = "", 
                messages: Optional[List[Dict[str, str]]] = None, 
                stream: bool = False, 
                **kwargs) -> Dict[str, Any]:
        """Generate text using Silicon Flow's API.
        
        Args:
            system_prompt: System instructions
            user_input: User input text
            messages: Conversation history messages (overrides system_prompt+user_input)
            stream: Whether to return the response in streaming mode
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            The generated text response
        """
        # 如果没有提供messages，则从system_prompt和user_input构建
        if not messages:
            messages = self.format_messages(system_prompt, user_input)
            
        # 构建请求URL
        url = f"{self.base_url}chat/completions"
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建请求体
        data = {
            "model": self.model,
            "messages": messages,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": stream
        }
        
        try:
            # 发送请求
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            if stream:
                # 流式响应处理待实现
                raise NotImplementedError("Stream mode not implemented yet for Silicon Flow")
            else:
                result = response.json()
                
                # 提取生成的文本
                return {
                    "response": result["choices"][0]["message"]["content"],
                    "raw_response": result
                }
        
        except requests.exceptions.RequestException as e:
            error_message = f"Silicon Flow API request failed: {str(e)}"
            
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_message += f" - {error_data['error']['message']}"
            except:
                pass
            
            return {
                "response": f"Sorry, I encountered an error: {error_message}",
                "error": error_message
            }
    
    def format_messages(self, system_prompt: str, user_input: str) -> List[Dict[str, str]]:
        """
        Format system prompt and user input into messages format
        
        Args:
            system_prompt: System instructions
            user_input: User input text
        
        Returns:
            Formatted messages
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def generate_with_tools(self, 
                           messages: List[Dict[str, str]], 
                           tools: List[Dict[str, Any]], 
                           stream: bool = False, 
                           **kwargs) -> Dict[str, Any]:
        """Generate text with tool calling capabilities.
        
        Args:
            messages: Conversation history messages
            tools: List of tool schemas for the model to use
            stream: Whether to return the response in streaming mode
            **kwargs: Additional parameters to pass to the API
            
        Returns:
            A dictionary containing the response content and tool calls
        """
        # 构建请求URL
        url = f"{self.base_url}chat/completions"
        
        # 构建请求头
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}"
        }
        
        # 构建请求体
        data = {
            "model": self.model,
            "messages": messages,
            "tools": tools,
            "max_tokens": kwargs.get("max_tokens", self.max_tokens),
            "temperature": kwargs.get("temperature", self.temperature),
            "top_p": kwargs.get("top_p", self.top_p),
            "stream": stream
        }
        
        try:
            # 发送请求
            response = requests.post(url, headers=headers, json=data)
            response.raise_for_status()
            
            if stream:
                # 流式响应处理待实现
                raise NotImplementedError("Stream mode not implemented yet for Silicon Flow")
            else:
                result = response.json()
                
                # 提取生成的文本和工具调用
                message = result["choices"][0]["message"]
                content = message.get("content", "")
                
                # 检查是否有工具调用
                tool_calls = message.get("tool_calls", [])
                
                return {
                    "response": content,
                    "tool_calls": tool_calls,
                    "raw_response": result
                }
        
        except requests.exceptions.RequestException as e:
            error_message = f"Silicon Flow API request failed: {str(e)}"
            
            try:
                error_data = e.response.json()
                if "error" in error_data:
                    error_message += f" - {error_data['error']['message']}"
            except:
                pass
            
            return {
                "response": f"Sorry, I encountered an error: {error_message}",
                "error": error_message
            }
