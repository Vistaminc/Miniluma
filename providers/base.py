"""
LLM服务提供商基类
定义了与不同LLM服务交互的标准接口
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional

class BaseLLMProvider(ABC):
    """LLM服务提供商的抽象基类
    
    所有LLM服务提供商都应继承此类并实现其方法
    """
    
    def __init__(self, model: str = None, **kwargs):
        """初始化LLM提供商
        
        Args:
            model: 模型名称
            **kwargs: 其他参数
        """
        self.model = model
        self.kwargs = kwargs
    
    @abstractmethod
    async def generate(self, system_prompt: str, user_input: str, 
                     context: List[Dict[str, str]] = None) -> Dict[str, Any]:
        """生成AI响应
        
        Args:
            system_prompt: 系统提示词
            user_input: 用户输入
            context: 上下文消息列表
            
        Returns:
            包含响应的字典，如 {"response": "...", "thinking": "..."}
        """
        pass
        
    @abstractmethod
    def get_provider_name(self) -> str:
        """获取提供商名称
        
        Returns:
            提供商名称，如 "openai", "deepseek" 等
        """
        pass
