"""
DeepSeek LLM集成模块
支持DeepSeek R1和V3模型的文本生成和工具调用
"""
import json
import os
import requests
from typing import Dict, List, Any, Optional, Union
from .base import BaseLLM
from core.config import config

class DeepSeekLLM(BaseLLM):
    """DeepSeek LLM实现类"""
    
    def __init__(self, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None):
        """
        初始化DeepSeek LLM
        
        Args:
            model: 模型名称，默认为配置中的默认模型
            api_key: API密钥，默认从配置或环境变量中获取
            base_url: API基础URL，用于中转或自定义服务
        """
        # 获取配置
        deepseek_config = config.get_llm_config("deepseek")
        
        self.model = model or deepseek_config.get("model", "deepseek-chat")
        self.api_key = api_key or deepseek_config.get("api_key")
        self.base_url = base_url or deepseek_config.get("base_url", "https://api.deepseek.com/v1/")
        
        # 获取其他模型参数
        self.max_tokens = deepseek_config.get("max_tokens", 4096)
        self.temperature = deepseek_config.get("temperature", 0.0)
        self.top_p = deepseek_config.get("top_p", 0.95)
        
        # 确保API路径末尾有斜杠
        if self.base_url and not self.base_url.endswith("/"):
            self.base_url += "/"
            
        # 确保API密钥被设置
        if not self.api_key:
            raise ValueError("DeepSeek API密钥未设置。请在配置文件或环境变量中设置DEEPSEEK_API_KEY。")
    
    @classmethod
    async def async_init(cls, model: Optional[str] = None, api_key: Optional[str] = None, base_url: Optional[str] = None, **kwargs):
        """异步初始化DeepSeek LLM
        
        Args:
            model: 模型名称，默认为配置中的默认模型
            api_key: API密钥，默认从配置或环境变量中获取
            base_url: API基础URL，用于中转或自定义服务
            **kwargs: 其他参数
            
        Returns:
            DeepSeekLLM实例
        """
        instance = cls(model=model, api_key=api_key, base_url=base_url)
        # 在这里可以添加需要异步执行的初始化代码
        return instance
    
    async def generate(self, messages=None, tools=None, max_tokens=None, **kwargs) -> Dict[str, Any]:
        """
        生成AI响应
        
        Args:
            messages: 消息历史，包含system、user、assistant等角色的消息
            tools: 工具列表
            max_tokens: 最大生成长度
            **kwargs: 其他参数
            
        Returns:
            包含响应的字典
        """
        try:
            # 调试输出
            print(f"DeepSeek LLM 接收到请求，消息数量: {len(messages) if messages else 0}")
            
            # 检查参数
            if not messages:
                # 如果没有提供messages，尝试从kwargs中获取system_prompt和user_input
                system_prompt = kwargs.get("system_prompt", "你是一个有帮助的AI助手。")
                user_input = kwargs.get("user_input", "")
                
                if user_input:
                    messages = self.format_messages(system_prompt, user_input)
                else:
                    # 返回错误
                    error_message = "错误：没有提供消息或用户输入"
                    print(error_message)
                    return {
                        "content": error_message,
                        "error": error_message
                    }
            
            # 1. 确保消息格式正确
            # DeepSeek只接受system/user/assistant角色，其他角色会导致403错误
            formatted_messages = []
            for i, msg in enumerate(messages):
                if not isinstance(msg, dict):
                    print(f"警告: 消息 {i} 不是字典: {msg}")
                    if hasattr(msg, 'to_dict'):
                        msg = msg.to_dict()
                    else:
                        msg = {"role": "user", "content": str(msg)}
                
                # 1.1 确保必要的键存在且内容符合要求
                role = msg.get("role", "user")
                content = msg.get("content", "")
                
                # 1.2 角色标准化 - DeepSeek只接受system/user/assistant
                if role not in ["system", "user", "assistant"]:
                    if role == "tool":
                        # 如果是工具消息，将其转换为assistant或user
                        if "name" in msg and msg.get("name", "").startswith("tool_"):
                            # 作为assistant消息添加
                            print(f"将工具消息 '{msg.get('name', '')}' 转换为assistant消息")
                            role = "assistant"
                        else:
                            # 作为user消息添加
                            print(f"将工具消息转换为user消息")
                            role = "user"
                    else:
                        print(f"警告: 角色 '{role}' 不被DeepSeek支持，转换为'user'")
                        role = "user"
                
                # 1.3 确保内容是字符串
                if not isinstance(content, str):
                    content = str(content)
                
                # 1.4 添加格式化的消息
                formatted_messages.append({
                    "role": role,
                    "content": content
                })
            
            # 2. 准备请求参数
            request_data = {
                "model": self.model,
                "messages": formatted_messages,
                "temperature": kwargs.get("temperature", self.temperature),
                "top_p": kwargs.get("top_p", self.top_p),
                "max_tokens": max_tokens or self.max_tokens
            }
            
            # 3. 处理工具
            if tools:
                print(f"准备 {len(tools)} 个工具定义")
                
                # 3.1 确保工具格式正确 - DeepSeek期望的格式
                formatted_tools = []
                for tool in tools:
                    # 3.1.1 如果工具有get_schema方法，调用它获取schema
                    if hasattr(tool, 'get_schema'):
                        tool_schema = tool.get_schema()
                    else:
                        tool_schema = tool
                    
                    # 3.1.2 确保工具有必要的字段
                    if not isinstance(tool_schema, dict):
                        print(f"警告: 工具 {tool} 不是字典")
                        continue
                    
                    if "name" not in tool_schema:
                        print(f"警告: 工具缺少name字段: {tool_schema}")
                        continue
                    
                    # 检查并修复函数定义
                    if "function" in tool_schema:
                        # 已经是DeepSeek格式
                        formatted_tool = tool_schema
                    else:
                        # 需要转换为DeepSeek格式
                        formatted_tool = {
                            "type": "function",
                            "function": {
                                "name": tool_schema["name"],
                                "description": tool_schema.get("description", ""),
                                "parameters": tool_schema.get("parameters", {})
                            }
                        }
                    
                    formatted_tools.append(formatted_tool)
                
                # 3.2 如果有工具，添加到请求
                if formatted_tools:
                    request_data["tools"] = formatted_tools
                    request_data["tool_choice"] = "auto"
            
            # 4. 发送请求
            api_url = f"{self.base_url}chat/completions"
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            # 打印完整请求数据用于调试（注意移除敏感信息）
            print(f"向DeepSeek发送请求, API URL: {api_url}")
            print(f"消息数: {len(formatted_messages)}")
            debug_request = request_data.copy()
            debug_request["messages"] = f"[{len(formatted_messages)}条消息]"  # 不打印完整消息内容
            if "tools" in debug_request:
                debug_request["tools"] = f"[{len(debug_request['tools'])}个工具]"  # 不打印完整工具内容
            print(f"请求数据: {json.dumps(debug_request, ensure_ascii=False, indent=2)}")
            
            # 使用aiohttp进行异步HTTP请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(api_url, json=request_data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_message = f"DeepSeek API请求失败: {response.status} {response.reason} for url: {api_url}"
                        print(f"错误: {error_message}")
                        print(f"响应内容: {error_text}")
                        
                        # 尝试解析错误响应
                        try:
                            error_json = json.loads(error_text)
                            if "error" in error_json:
                                error_detail = error_json["error"]
                                print(f"错误详情: {error_detail}")
                                error_message += f"\n错误详情: {error_detail}"
                        except:
                            pass
                            
                        # 添加请求细节到错误消息
                        error_message += "\n请检查API密钥和请求格式"
                        
                        return {
                            "content": f"抱歉，无法生成回复。错误: {error_message}",
                            "error": error_message
                        }
                    
                    response_data = await response.json()
            
            # 5. 处理响应
            print(f"收到响应: {json.dumps(response_data, ensure_ascii=False)[:200]}...")
            
            # 5.1 检查是否有错误
            if "error" in response_data:
                error_message = f"DeepSeek API错误: {response_data['error']}"
                print(f"错误: {error_message}")
                return {
                    "content": f"抱歉，生成回复时出错: {error_message}",
                    "error": error_message
                }
            
            # 5.2 提取响应内容
            try:
                choices = response_data.get("choices", [])
                if not choices:
                    error_message = "DeepSeek API响应中没有选择"
                    print(f"错误: {error_message}")
                    return {
                        "content": "抱歉，生成回复失败。",
                        "error": error_message
                    }
                
                choice = choices[0]
                message = choice.get("message", {})
                content = message.get("content", "")
                
                # 5.3 检查是否有工具调用
                if "tool_calls" in message and message["tool_calls"]:
                    tool_calls = message["tool_calls"]
                    print(f"检测到 {len(tool_calls)} 个工具调用")
                    
                    return {
                        "content": content,
                        "tool_calls": tool_calls,
                        "response": content  # 兼容旧代码
                    }
                
                # 5.4 返回普通响应
                return {
                    "content": content,
                    "response": content  # 兼容旧代码
                }
            
            except Exception as e:
                error_message = f"处理DeepSeek响应时出错: {str(e)}"
                print(f"错误: {error_message}")
                import traceback
                traceback.print_exc()
                return {
                    "content": "抱歉，处理回复时出现错误。",
                    "error": error_message
                }
                
        except Exception as e:
            error_message = f"DeepSeek生成过程出错: {str(e)}"
            print(f"错误: {error_message}")
            import traceback
            traceback.print_exc()
            return {
                "content": f"抱歉，处理您的请求时出现错误: {str(e)}",
                "error": error_message
            }
    
    def format_messages(self, system_prompt: str, user_input: str) -> List[Dict[str, str]]:
        """
        将系统提示词和用户输入格式化为messages格式
        
        Args:
            system_prompt: 系统提示词
            user_input: 用户输入
            
        Returns:
            格式化后的消息列表
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    async def generate_with_tools(self, messages: List[Dict[str, str]], tools: List[Dict[str, Any]], 
                           stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        生成带有工具调用的文本响应
        
        Args:
            messages: 对话历史消息
            tools: 工具定义列表
            stream: 是否流式返回
            **kwargs: 其他参数
        
        Returns:
            生成的文本响应，可能包含工具调用
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
            # 使用aiohttp进行异步HTTP请求
            import aiohttp
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=data, headers=headers) as response:
                    if response.status != 200:
                        error_text = await response.text()
                        error_message = f"DeepSeek API请求失败: {response.status} {response.reason} for url: {url}"
                        print(f"错误: {error_message}")
                        print(f"响应内容: {error_text}")
                        
                        # 尝试解析错误响应
                        try:
                            error_json = json.loads(error_text)
                            if "error" in error_json:
                                error_detail = error_json["error"]
                                print(f"错误详情: {error_detail}")
                                error_message += f"\n错误详情: {error_detail}"
                        except:
                            pass
                        
                        return {
                            "response": f"API请求错误: {error_message}",
                            "error": error_message
                        }
                    
                    if stream:
                        # 流式响应处理待实现
                        raise NotImplementedError("Stream mode not implemented yet for DeepSeek")
                    else:
                        result = await response.json()
                        
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
        
        except Exception as e:
            error_message = f"DeepSeek API请求失败: {str(e)}"
            print(f"错误: {error_message}")
            import traceback
            traceback.print_exc()
            
            return {
                "response": f"生成响应时出错: {error_message}",
                "error": error_message
            }
