"""
配置加载和管理模块
支持从config目录下的TOML配置文件加载配置
"""
import os
import tomli
from typing import Any, Dict, Optional, Union

# 配置文件默认路径
CONFIG_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config")
GLOBAL_CONFIG_PATH = os.path.join(CONFIG_DIR, "config_global.toml")

# 默认配置
DEFAULT_CONFIG = {
    "global": {
        "show_thinking": False,
        "language": "zh-CN"
    },
    "openai": {
        "model": "gpt-4",
        "max_tokens": 4096,
        "temperature": 0.7,
        "base_url": None,
    },
    "deepseek": {
        "model": "deepseek-chat",
        "max_tokens": 4096,
        "temperature": 0.0,
        "base_url": "https://api.deepseek.com/v1/",
    },
    "silicon_flow": {
        "model": "sf-plus",
        "max_tokens": 4096,
        "temperature": 0.7,
        "base_url": "https://api.siliconflow.cn/v1/",
    },
    "agent": {
        "default_provider": "openai",
        "system_prompt": "你是一个智能助手，帮助用户解决各种问题。",
        "memory_limit": 10
    },
    "tools": {
        "enabled": ["search", "calculator", "weather"]
    },
    "ui": {
        "theme": "blue",
        "use_colors": True
    }
}

class Config:
    """配置管理类"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化配置
        
        Args:
            config_path: 配置文件路径，默认查找config目录下的配置文件
        """
        self.config = DEFAULT_CONFIG.copy()
        
        # 如果提供了配置文件路径，尝试加载
        if config_path:
            self._load_from_toml(config_path)
        else:
            # 尝试从全局配置文件加载
            if os.path.exists(GLOBAL_CONFIG_PATH):
                self._load_from_toml(GLOBAL_CONFIG_PATH)
    
    def _load_from_toml(self, config_path: str) -> None:
        """
        从TOML文件加载配置
        
        Args:
            config_path: TOML配置文件路径
        """
        try:
            with open(config_path, "rb") as f:
                toml_config = tomli.load(f)
            
            # 递归合并配置
            self._merge_configs(self.config, toml_config)
            
            print(f"加载配置文件: {config_path}")
                
        except Exception as e:
            print(f"加载配置文件 {config_path} 失败: {str(e)}")
    
    def _merge_configs(self, target: Dict[str, Any], source: Dict[str, Any]) -> None:
        """
        递归合并配置
        
        Args:
            target: 目标配置
            source: 源配置
        """
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                self._merge_configs(target[key], value)
            else:
                target[key] = value
    
    def get(self, section: str, key: str, default: Any = None) -> Any:
        """
        获取配置项
        
        Args:
            section: 配置区块
            key: 配置键
            default: 默认值
        
        Returns:
            配置值
        """
        return self.config.get(section, {}).get(key, default)
    
    def get_llm_config(self, provider: str) -> Dict[str, Any]:
        """
        获取指定提供商的LLM配置
        
        Args:
            provider: LLM提供商名称
        
        Returns:
            LLM配置字典
        """
        if provider not in self.config:
            raise ValueError(f"未知的LLM提供商: {provider}")
        
        return self.config[provider]
    
    def get_default_provider(self) -> str:
        """获取默认LLM提供商"""
        return self.config["agent"].get("default_provider", "openai")
    
    def get_default_model(self, provider: Optional[str] = None) -> str:
        """
        获取默认模型
        
        Args:
            provider: LLM提供商，如果为None则使用默认提供商
        
        Returns:
            默认模型名称
        """
        if provider is None:
            provider = self.get_default_provider()
        
        return self.config[provider].get("model")
    
    def is_api_key_set(self, provider: str) -> bool:
        """
        检查指定提供商的API密钥是否已设置
        
        Args:
            provider: LLM提供商名称
        
        Returns:
            API密钥是否已设置
        """
        return bool(self.config.get(provider, {}).get("api_key"))
    
    def get_all_sections(self) -> Dict[str, Dict[str, Any]]:
        """获取所有配置区块"""
        return self.config.copy()

# 创建全局配置实例
config = Config()
