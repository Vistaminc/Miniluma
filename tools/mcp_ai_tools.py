"""
MCP AI对话工具
提供与各种AI模型交互的能力，支持对话请求和多模态处理
"""
import os
import sys
import json
import base64
import requests
from typing import Dict, List, Any, Optional, Union

from core.mcp import mcp_tool
from core.config import Config

# 获取配置
config = Config()

class AIProviderManager:
    """AI提供商管理器，用于与不同AI服务进行交互"""
    
    def __init__(self):
        """初始化AI提供商管理器"""
        self.providers = {
            "openai": self._call_openai,
            "azure": self._call_azure_openai,
            "anthropic": self._call_anthropic,
            "gemini": self._call_gemini,
            "baidu": self._call_baidu,
            "zhipu": self._call_zhipu
        }
    
    async def call_ai(self, 
                     provider: str, 
                     prompt: str, 
                     model: Optional[str] = None,
                     system_prompt: Optional[str] = None,
                     temperature: float = 0.7,
                     max_tokens: Optional[int] = None) -> Dict:
        """调用AI服务
        
        Args:
            provider: AI提供商名称
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        # 获取默认值
        if not model:
            model = config.get_default_model(provider)
        
        # 查找提供商处理函数
        provider_func = self.providers.get(provider.lower())
        if not provider_func:
            return {
                "error": f"不支持的AI提供商: {provider}",
                "content": f"错误: 不支持的AI提供商 '{provider}'。支持的提供商有: {', '.join(self.providers.keys())}"
            }
        
        # 调用提供商特定处理
        try:
            return await provider_func(prompt, model, system_prompt, temperature, max_tokens)
        except Exception as e:
            return {
                "error": str(e),
                "content": f"调用AI服务时出错: {str(e)}"
            }
    
    async def _call_openai(self, 
                          prompt: str, 
                          model: str = "gpt-4o",
                          system_prompt: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None) -> Dict:
        """调用OpenAI API
        
        Args:
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥
            api_key = os.environ.get("OPENAI_API_KEY") or config.get("openai.api_key")
            if not api_key:
                return {"error": "缺少OpenAI API密钥", "content": "错误: 请设置OPENAI_API_KEY环境变量或在配置中指定openai.api_key"}
            
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            # 发送请求
            url = os.environ.get("OPENAI_API_BASE", "https://api.openai.com") + "/v1/chat/completions"
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"OpenAI API错误: {response.status_code}",
                    "content": f"OpenAI API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            return {
                "provider": "openai",
                "model": model,
                "content": content,
                "usage": result.get("usage", {})
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用OpenAI API时出错: {str(e)}"}
    
    async def _call_azure_openai(self, 
                                prompt: str, 
                                model: str = "gpt-4",
                                system_prompt: Optional[str] = None,
                                temperature: float = 0.7,
                                max_tokens: Optional[int] = None) -> Dict:
        """调用Azure OpenAI API
        
        Args:
            prompt: 用户提示
            model: 部署名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥和端点
            api_key = os.environ.get("AZURE_OPENAI_API_KEY") or config.get("azure.api_key")
            endpoint = os.environ.get("AZURE_OPENAI_ENDPOINT") or config.get("azure.endpoint")
            
            if not api_key:
                return {"error": "缺少Azure OpenAI API密钥", "content": "错误: 请设置AZURE_OPENAI_API_KEY环境变量或在配置中指定azure.api_key"}
            if not endpoint:
                return {"error": "缺少Azure OpenAI端点", "content": "错误: 请设置AZURE_OPENAI_ENDPOINT环境变量或在配置中指定azure.endpoint"}
            
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "api-key": api_key
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            # 发送请求
            deployment_name = model
            url = f"{endpoint}/openai/deployments/{deployment_name}/chat/completions?api-version=2023-05-15"
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"Azure OpenAI API错误: {response.status_code}",
                    "content": f"Azure OpenAI API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            return {
                "provider": "azure",
                "model": model,
                "content": content,
                "usage": result.get("usage", {})
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用Azure OpenAI API时出错: {str(e)}"}
    
    async def _call_anthropic(self, 
                             prompt: str, 
                             model: str = "claude-3-opus-20240229",
                             system_prompt: Optional[str] = None,
                             temperature: float = 0.7,
                             max_tokens: Optional[int] = None) -> Dict:
        """调用Anthropic API
        
        Args:
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥
            api_key = os.environ.get("ANTHROPIC_API_KEY") or config.get("anthropic.api_key")
            if not api_key:
                return {"error": "缺少Anthropic API密钥", "content": "错误: 请设置ANTHROPIC_API_KEY环境变量或在配置中指定anthropic.api_key"}
            
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01"
            }
            
            data = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": temperature
            }
            
            if system_prompt:
                data["system"] = system_prompt
                
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            # 发送请求
            url = "https://api.anthropic.com/v1/messages"
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"Anthropic API错误: {response.status_code}",
                    "content": f"Anthropic API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["content"][0]["text"]
            
            return {
                "provider": "anthropic",
                "model": model,
                "content": content
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用Anthropic API时出错: {str(e)}"}
    
    async def _call_gemini(self, 
                          prompt: str, 
                          model: str = "gemini-pro",
                          system_prompt: Optional[str] = None,
                          temperature: float = 0.7,
                          max_tokens: Optional[int] = None) -> Dict:
        """调用Google Gemini API
        
        Args:
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥
            api_key = os.environ.get("GEMINI_API_KEY") or config.get("gemini.api_key")
            if not api_key:
                return {"error": "缺少Gemini API密钥", "content": "错误: 请设置GEMINI_API_KEY环境变量或在配置中指定gemini.api_key"}
            
            # 构建请求
            contents = []
            if system_prompt:
                contents.append({"role": "system", "parts": [{"text": system_prompt}]})
            contents.append({"role": "user", "parts": [{"text": prompt}]})
            
            data = {
                "contents": contents,
                "generationConfig": {
                    "temperature": temperature,
                }
            }
            
            if max_tokens:
                data["generationConfig"]["maxOutputTokens"] = max_tokens
            
            # 发送请求
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
            response = requests.post(url, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"Gemini API错误: {response.status_code}",
                    "content": f"Gemini API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["candidates"][0]["content"]["parts"][0]["text"]
            
            return {
                "provider": "gemini",
                "model": model,
                "content": content
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用Gemini API时出错: {str(e)}"}
    
    async def _call_baidu(self, 
                         prompt: str, 
                         model: str = "ernie-4.0",
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None) -> Dict:
        """调用百度文心API
        
        Args:
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥和密钥
            api_key = os.environ.get("BAIDU_API_KEY") or config.get("baidu.api_key")
            secret_key = os.environ.get("BAIDU_SECRET_KEY") or config.get("baidu.secret_key")
            
            if not api_key:
                return {"error": "缺少百度API密钥", "content": "错误: 请设置BAIDU_API_KEY环境变量或在配置中指定baidu.api_key"}
            if not secret_key:
                return {"error": "缺少百度密钥", "content": "错误: 请设置BAIDU_SECRET_KEY环境变量或在配置中指定baidu.secret_key"}
            
            # 获取访问令牌
            token_url = f"https://aip.baidubce.com/oauth/2.0/token?grant_type=client_credentials&client_id={api_key}&client_secret={secret_key}"
            token_response = requests.post(token_url)
            
            if token_response.status_code != 200:
                return {
                    "error": f"百度API获取令牌错误: {token_response.status_code}",
                    "content": f"百度API获取令牌错误: {token_response.text}"
                }
            
            access_token = token_response.json()["access_token"]
            
            # 构建请求
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                data["max_output_tokens"] = max_tokens
            
            # 发送请求
            url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/{model}?access_token={access_token}"
            response = requests.post(url, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"百度API错误: {response.status_code}",
                    "content": f"百度API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["result"]
            
            return {
                "provider": "baidu",
                "model": model,
                "content": content,
                "usage": result.get("usage", {})
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用百度API时出错: {str(e)}"}
    
    async def _call_zhipu(self, 
                         prompt: str, 
                         model: str = "glm-4",
                         system_prompt: Optional[str] = None,
                         temperature: float = 0.7,
                         max_tokens: Optional[int] = None) -> Dict:
        """调用智谱AI API
        
        Args:
            prompt: 用户提示
            model: 模型名称
            system_prompt: 系统提示
            temperature: 温度参数
            max_tokens: 最大生成令牌数
            
        Returns:
            AI响应结果
        """
        try:
            # 获取API密钥
            api_key = os.environ.get("ZHIPU_API_KEY") or config.get("zhipu.api_key")
            if not api_key:
                return {"error": "缺少智谱API密钥", "content": "错误: 请设置ZHIPU_API_KEY环境变量或在配置中指定zhipu.api_key"}
            
            # 构建请求
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
            
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            data = {
                "model": model,
                "messages": messages,
                "temperature": temperature
            }
            
            if max_tokens:
                data["max_tokens"] = max_tokens
            
            # 发送请求
            url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
            response = requests.post(url, headers=headers, json=data, timeout=60)
            
            if response.status_code != 200:
                return {
                    "error": f"智谱API错误: {response.status_code}",
                    "content": f"智谱API返回错误: {response.text}"
                }
            
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            return {
                "provider": "zhipu",
                "model": model,
                "content": content,
                "usage": result.get("usage", {})
            }
            
        except Exception as e:
            return {"error": str(e), "content": f"调用智谱API时出错: {str(e)}"}

# AI提供商管理器实例
ai_provider_manager = AIProviderManager()

# ==================== MCP AI工具 ====================

@mcp_tool(name="ask_ai", description="向AI模型提问并获取回答")
async def ask_ai_tool(prompt: str, 
                    provider: str = "openai", 
                    model: Optional[str] = None,
                    system_prompt: Optional[str] = None) -> str:
    """
    向AI模型提问并获取回答
    
    Args:
        prompt: 用户提示
        provider: AI提供商名称（openai, azure, anthropic, gemini, baidu, zhipu）
        model: 模型名称（可选，如果未指定则使用默认模型）
        system_prompt: 系统提示（可选）
        
    Returns:
        AI响应内容
    """
    result = await ai_provider_manager.call_ai(
        provider=provider,
        prompt=prompt,
        model=model,
        system_prompt=system_prompt
    )
    
    # 检查是否有错误
    if "error" in result:
        return f"错误: {result['error']}"
    
    return result["content"]

@mcp_tool(name="compare_ai_responses", description="向多个AI模型提问并比较回答")
async def compare_ai_responses_tool(prompt: str, 
                                  providers: List[str] = ["openai", "anthropic"],
                                  system_prompt: Optional[str] = None) -> Dict:
    """
    向多个AI模型提问并比较回答
    
    Args:
        prompt: 用户提示
        providers: AI提供商名称列表
        system_prompt: 系统提示（可选）
        
    Returns:
        各AI模型的响应比较
    """
    results = {}
    
    for provider in providers:
        result = await ai_provider_manager.call_ai(
            provider=provider,
            prompt=prompt,
            system_prompt=system_prompt
        )
        
        # 提取响应内容
        if "error" in result:
            content = f"错误: {result['error']}"
        else:
            content = result["content"]
        
        results[provider] = {
            "model": result.get("model", "未知模型"),
            "content": content
        }
    
    return results

@mcp_tool(name="ai_translate", description="使用AI模型进行文本翻译")
async def ai_translate_tool(text: str, 
                          target_language: str = "中文",
                          provider: str = "openai") -> str:
    """
    使用AI模型进行文本翻译
    
    Args:
        text: 要翻译的文本
        target_language: 目标语言
        provider: AI提供商名称
        
    Returns:
        翻译后的文本
    """
    prompt = f"请将以下文本翻译成{target_language}，只返回翻译结果，不要添加任何解释：\n\n{text}"
    system_prompt = f"你是一个专业翻译，能够准确地将文本翻译成{target_language}。请只返回翻译结果，不要添加任何解释或额外文字。"
    
    result = await ai_provider_manager.call_ai(
        provider=provider,
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    # 检查是否有错误
    if "error" in result:
        return f"翻译错误: {result['error']}"
    
    return result["content"]

@mcp_tool(name="summarize_text", description="使用AI模型对文本进行摘要")
async def summarize_text_tool(text: str, 
                            max_length: int = 200,
                            provider: str = "openai") -> str:
    """
    使用AI模型对文本进行摘要
    
    Args:
        text: 要摘要的文本
        max_length: 摘要最大长度
        provider: AI提供商名称
        
    Returns:
        文本摘要
    """
    prompt = f"请对以下文本进行摘要，摘要长度不超过{max_length}个字符：\n\n{text}"
    system_prompt = "你是一个专业文本摘要工具，能够提取文本的关键信息并生成简明扼要的摘要。"
    
    result = await ai_provider_manager.call_ai(
        provider=provider,
        prompt=prompt,
        system_prompt=system_prompt
    )
    
    # 检查是否有错误
    if "error" in result:
        return f"摘要错误: {result['error']}"
    
    return result["content"]

def get_all_ai_tools() -> List:
    """获取所有AI工具"""
    return [
        ask_ai_tool,
        compare_ai_responses_tool,
        ai_translate_tool,
        summarize_text_tool
    ]
