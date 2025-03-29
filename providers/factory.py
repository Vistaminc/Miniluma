"""
LLM服务提供商工厂模块
根据配置创建不同的LLM服务提供商实例
"""
import os
from typing import Optional, Dict, Any
from .base import BaseLLMProvider
from .mock_provider import MockLLMProvider

async def create_provider(provider_name: str = None, model: str = None, **kwargs) -> BaseLLMProvider:
    """创建LLM服务提供商实例
    
    Args:
        provider_name: 提供商名称，如 "openai", "deepseek" 等，如果为None则使用mock
        model: 模型名称，如果为None则使用提供商默认模型
        **kwargs: 其他参数
        
    Returns:
        LLM服务提供商实例
    """
    # 导入所需模块
    import os
    import sys
    from core.config import Config
    
    # 如果未指定提供商，使用模拟提供商
    if not provider_name:
        return MockLLMProvider(model="mock-model", **kwargs)
    
    # 规范化提供商名称
    provider_name = provider_name.lower().strip()
    
    # 检查环境变量中是否有API密钥
    api_key_env = f"{provider_name.upper()}_API_KEY"
    api_key = os.environ.get(api_key_env)
    
    # 如果环境变量中没有API密钥，尝试从配置文件中获取
    if not api_key:
        # 获取配置
        config = Config()
        api_key = config.get(provider_name, "api_key")
        if api_key:
            print(f"从配置文件加载了 {provider_name} 的API密钥")
        else:
            print(f"配置文件中未找到 {provider_name} 的API密钥")
    else:
        print(f"从环境变量加载了 {provider_name} 的API密钥")
    
    # 如果还是没有API密钥，使用模拟提供商
    if not api_key:
        print(f"警告: 未找到{provider_name}的API密钥，使用模拟提供商替代")
        return MockLLMProvider(model="mock-model", **kwargs)
    else:
        print(f"成功获取 {provider_name} 的API密钥: {api_key[:4]}...{api_key[-4:]}")
    
    # 确保项目根目录在路径中
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    
    # 根据提供商名称创建对应的提供商实例
    if provider_name == "openai":
        try:
            print(f"尝试导入 OpenAI LLM...")
            from llm.openai import OpenAILLM
            print(f"成功导入 OpenAI LLM，正在初始化...")
            return OpenAILLM(model=model, api_key=api_key, **kwargs)
        except ImportError as e:
            print(f"警告: OpenAI提供商模块导入失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-gpt", **kwargs)
        except Exception as e:
            print(f"警告: OpenAI提供商初始化失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-gpt", **kwargs)
    
    elif provider_name == "deepseek":
        try:
            print(f"尝试导入 DeepSeek LLM...")
            from llm.deepseek import DeepSeekLLM
            print(f"成功导入 DeepSeek LLM，正在初始化，模型: {model}，API密钥: {api_key[:4]}...{api_key[-4:]}...")
            provider = await DeepSeekLLM.async_init(model=model, api_key=api_key, **kwargs)
            print(f"成功创建 DeepSeek LLM 提供商实例")
            return provider
        except ImportError as e:
            print(f"警告: DeepSeek提供商模块导入失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-deepseek", **kwargs)
        except Exception as e:
            print(f"警告: DeepSeek提供商初始化失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-deepseek", **kwargs)
    
    elif provider_name == "silicon_flow":
        try:
            print(f"尝试导入 Silicon Flow LLM...")
            from llm.silicon_flow import SiliconFlowLLM
            print(f"成功导入 Silicon Flow LLM，正在初始化...")
            return SiliconFlowLLM(model=model, api_key=api_key, **kwargs)
        except ImportError as e:
            print(f"警告: Silicon Flow提供商模块导入失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-silicon-flow", **kwargs)
        except Exception as e:
            print(f"警告: Silicon Flow提供商初始化失败，错误: {str(e)}，使用模拟提供商替代")
            return MockLLMProvider(model="mock-silicon-flow", **kwargs)
    
    # 默认使用模拟提供商
    print(f"未找到提供商 '{provider_name}'，使用模拟提供商替代")
    return MockLLMProvider(model=f"mock-{provider_name}", **kwargs)
