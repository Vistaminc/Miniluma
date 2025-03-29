"""
MCP插件系统
提供可扩展的插件架构，支持动态加载和集成外部功能
"""
import os
import sys
import json
import importlib
import inspect
import pkgutil
from typing import Dict, List, Any, Optional, Union, Callable, Type
from pathlib import Path

from core.mcp import MCPTool, mcp_tool
from core.mcp_agent import MCPAgent

class MCPPlugin:
    """
    MCP插件基类
    所有插件必须继承此类并实现必要的方法
    """
    
    def __init__(self, name: str, description: str = ""):
        """初始化插件
        
        Args:
            name: 插件名称
            description: 插件描述
        """
        self.name = name
        self.description = description
        self.enabled = False
        self.agent = None
        self.config = {}
    
    def initialize(self, agent: MCPAgent, config: Dict = None) -> bool:
        """初始化插件
        
        Args:
            agent: 要集成的MCPAgent
            config: 插件配置
            
        Returns:
            初始化是否成功
        """
        self.agent = agent
        self.config = config or {}
        self.enabled = True
        return True
    
    def get_tools(self) -> List[Callable]:
        """获取插件提供的工具
        
        Returns:
            工具函数列表
        """
        return []
    
    def register_tools(self) -> List[str]:
        """注册插件工具到智能体
        
        Returns:
            注册的工具名称列表
        """
        if not self.agent or not self.enabled:
            return []
        
        registered_tools = []
        for tool in self.get_tools():
            if callable(tool) and hasattr(tool, '_mcp_tool'):
                self.agent.register_tool(tool)
                registered_tools.append(getattr(tool, '_tool_name', tool.__name__))
        
        return registered_tools
    
    def on_message(self, message: Dict) -> Optional[Dict]:
        """消息拦截处理
        
        当智能体收到新消息时调用
        
        Args:
            message: 消息内容
            
        Returns:
            处理后的消息，如果返回None则不修改原消息
        """
        return None
    
    def on_response(self, response: Dict) -> Optional[Dict]:
        """响应拦截处理
        
        当智能体生成响应时调用
        
        Args:
            response: 响应内容
            
        Returns:
            处理后的响应，如果返回None则不修改原响应
        """
        return None
    
    def shutdown(self) -> bool:
        """关闭插件
        
        Returns:
            关闭是否成功
        """
        self.enabled = False
        return True


class TranslationPlugin(MCPPlugin):
    """
    翻译插件
    提供多语言翻译功能
    """
    
    def __init__(self):
        super().__init__(
            name="translation_plugin",
            description="提供多语言翻译功能"
        )
        self.default_target_lang = "zh-CN"
    
    def initialize(self, agent: MCPAgent, config: Dict = None) -> bool:
        """初始化翻译插件
        
        Args:
            agent: 要集成的MCPAgent
            config: 插件配置
            
        Returns:
            初始化是否成功
        """
        result = super().initialize(agent, config)
        
        # 设置默认目标语言
        if config and "default_target_lang" in config:
            self.default_target_lang = config["default_target_lang"]
        
        return result
    
    @staticmethod
    @mcp_tool(name="translate_text", description="将文本翻译为目标语言")
    def translate_text(text: str, target_lang: str = "zh-CN", source_lang: str = "auto") -> str:
        """将文本翻译为目标语言
        
        Args:
            text: 要翻译的文本
            target_lang: 目标语言代码
            source_lang: 源语言代码
            
        Returns:
            翻译后的文本
        """
        # 实际应用中应集成真实翻译API
        # 这里使用模拟实现
        
        if target_lang == "zh-CN":
            if "hello" in text.lower():
                return "你好"
            elif "thank" in text.lower():
                return "谢谢"
            else:
                return f"[翻译成中文] {text}"
        elif target_lang == "en":
            if "你好" in text:
                return "Hello"
            elif "谢谢" in text:
                return "Thank you"
            else:
                return f"[Translated to English] {text}"
        else:
            return f"[翻译到 {target_lang}] {text}"
    
    def get_tools(self) -> List[Callable]:
        """获取翻译工具
        
        Returns:
            工具函数列表
        """
        return [self.translate_text]
    
    def on_response(self, response: Dict) -> Optional[Dict]:
        """响应拦截处理
        
        自动将响应翻译为目标语言（如果配置了auto_translate）
        
        Args:
            response: 响应内容
            
        Returns:
            处理后的响应
        """
        if not self.enabled:
            return None
        
        # 检查是否启用自动翻译
        if self.config.get("auto_translate", False):
            if isinstance(response.get("content"), str):
                # 检查是否已经是目标语言
                # 这里简化处理，实际应使用语言检测
                if self.default_target_lang == "zh-CN" and not any(c in response["content"] for c in "你我他的是在"):
                    translated = self.translate_text(response["content"], self.default_target_lang)
                    return {**response, "content": translated}
        
        return None


class WebSearchPlugin(MCPPlugin):
    """
    网络搜索插件
    提供网络搜索和信息获取功能
    """
    
    def __init__(self):
        super().__init__(
            name="web_search_plugin",
            description="提供网络搜索和信息获取功能"
        )
    
    @staticmethod
    @mcp_tool(name="search_web", description="执行网络搜索并返回结果")
    def search_web(query: str, num_results: int = 5) -> str:
        """执行网络搜索
        
        Args:
            query: 搜索查询
            num_results: 结果数量
            
        Returns:
            搜索结果
        """
        # 实际应用中应集成真实搜索API
        # 这里使用模拟实现
        return f"为查询'{query}'找到 {num_results} 条模拟搜索结果。实际部署时请集成搜索API。"
    
    @staticmethod
    @mcp_tool(name="get_webpage", description="获取网页内容")
    def get_webpage(url: str) -> str:
        """获取网页内容
        
        Args:
            url: 网页URL
            
        Returns:
            网页内容
        """
        # 实际应用中应获取真实网页
        # 这里使用模拟实现
        return f"这是来自 {url} 的模拟网页内容。实际部署时请集成网页获取功能。"
    
    def get_tools(self) -> List[Callable]:
        """获取搜索工具
        
        Returns:
            工具函数列表
        """
        return [self.search_web, self.get_webpage]


class DataAnalysisPlugin(MCPPlugin):
    """
    数据分析插件
    提供数据处理和可视化功能
    """
    
    def __init__(self):
        super().__init__(
            name="data_analysis_plugin",
            description="提供数据处理和可视化功能"
        )
    
    @staticmethod
    @mcp_tool(name="analyze_data", description="分析数据并返回统计摘要")
    def analyze_data(data: List[Union[int, float]]) -> Dict:
        """分析数值数据
        
        Args:
            data: 数值列表
            
        Returns:
            统计摘要
        """
        if not data:
            return {"error": "提供的数据为空"}
        
        try:
            # 计算基本统计量
            count = len(data)
            mean = sum(data) / count
            sorted_data = sorted(data)
            median = sorted_data[count // 2] if count % 2 != 0 else (sorted_data[count // 2 - 1] + sorted_data[count // 2]) / 2
            minimum = min(data)
            maximum = max(data)
            data_range = maximum - minimum
            
            # 计算标准差
            variance = sum((x - mean) ** 2 for x in data) / count
            std_dev = variance ** 0.5
            
            return {
                "count": count,
                "mean": mean,
                "median": median,
                "min": minimum,
                "max": maximum,
                "range": data_range,
                "std_dev": std_dev,
                "variance": variance
            }
        except Exception as e:
            return {"error": f"分析数据时出错: {str(e)}"}
    
    @staticmethod
    @mcp_tool(name="format_table", description="将数据格式化为表格")
    def format_table(data: List[Dict], columns: Optional[List[str]] = None) -> str:
        """将数据格式化为表格
        
        Args:
            data: 数据列表
            columns: 要显示的列
            
        Returns:
            格式化的表格
        """
        if not data:
            return "空表格"
        
        try:
            # 确定列
            if not columns:
                columns = list(data[0].keys())
            
            # 计算每列的最大宽度
            widths = {col: len(col) for col in columns}
            for row in data:
                for col in columns:
                    if col in row:
                        widths[col] = max(widths[col], len(str(row[col])))
            
            # 构建表头
            header = " | ".join(col.ljust(widths[col]) for col in columns)
            separator = "-+-".join("-" * widths[col] for col in columns)
            
            # 构建表格行
            rows = []
            for row in data:
                formatted_row = " | ".join(
                    str(row.get(col, "")).ljust(widths[col]) for col in columns
                )
                rows.append(formatted_row)
            
            # 合并表格
            table = f"{header}\n{separator}\n" + "\n".join(rows)
            return table
            
        except Exception as e:
            return f"格式化表格时出错: {str(e)}"
    
    def get_tools(self) -> List[Callable]:
        """获取数据分析工具
        
        Returns:
            工具函数列表
        """
        return [self.analyze_data, self.format_table]


class PluginManager:
    """
    插件管理器
    管理MCP插件的加载、配置和集成
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None):
        """初始化插件管理器
        
        Args:
            plugin_dirs: 插件目录列表
        """
        self.plugins: Dict[str, MCPPlugin] = {}
        self.plugin_dirs = plugin_dirs or []
        
        # 添加默认插件
        self._register_default_plugins()
    
    def _register_default_plugins(self):
        """注册默认插件"""
        self.register_plugin(TranslationPlugin())
        self.register_plugin(WebSearchPlugin())
        self.register_plugin(DataAnalysisPlugin())
    
    def register_plugin(self, plugin: MCPPlugin) -> bool:
        """注册插件
        
        Args:
            plugin: 插件实例
            
        Returns:
            注册是否成功
        """
        if plugin.name in self.plugins:
            return False
        
        self.plugins[plugin.name] = plugin
        return True
    
    def get_plugin(self, name: str) -> Optional[MCPPlugin]:
        """获取插件
        
        Args:
            name: 插件名称
            
        Returns:
            插件实例
        """
        return self.plugins.get(name)
    
    def discover_plugins(self) -> List[str]:
        """从插件目录发现插件
        
        Returns:
            发现的插件名称列表
        """
        discovered = []
        
        for plugin_dir in self.plugin_dirs:
            if not os.path.exists(plugin_dir) or not os.path.isdir(plugin_dir):
                continue
            
            # 将插件目录添加到路径
            sys.path.insert(0, plugin_dir)
            
            # 遍历目录中的模块
            for finder, name, is_pkg in pkgutil.iter_modules([plugin_dir]):
                try:
                    # 导入模块
                    module = importlib.import_module(name)
                    
                    # 查找MCPPlugin子类
                    for item_name, item in inspect.getmembers(module, inspect.isclass):
                        if issubclass(item, MCPPlugin) and item != MCPPlugin:
                            # 创建插件实例
                            plugin = item()
                            if self.register_plugin(plugin):
                                discovered.append(plugin.name)
                
                except Exception as e:
                    print(f"加载插件 {name} 时出错: {str(e)}")
            
            # 恢复路径
            if plugin_dir in sys.path:
                sys.path.remove(plugin_dir)
        
        return discovered
    
    def initialize_plugins(self, agent: MCPAgent, config: Dict = None) -> List[str]:
        """初始化所有插件
        
        Args:
            agent: 要集成的智能体
            config: 插件配置 {plugin_name: plugin_config}
            
        Returns:
            成功初始化的插件名称列表
        """
        initialized = []
        
        for name, plugin in self.plugins.items():
            plugin_config = None
            if config and name in config:
                plugin_config = config[name]
            
            if plugin.initialize(agent, plugin_config):
                plugin.register_tools()
                initialized.append(name)
        
        return initialized
    
    def shutdown_all(self) -> List[str]:
        """关闭所有插件
        
        Returns:
            成功关闭的插件名称列表
        """
        shutdown = []
        
        for name, plugin in self.plugins.items():
            if plugin.shutdown():
                shutdown.append(name)
        
        return shutdown
    
    def intercept_message(self, message: Dict) -> Dict:
        """处理传入消息
        
        让所有启用的插件有机会修改消息
        
        Args:
            message: 原始消息
            
        Returns:
            处理后的消息
        """
        current_message = message
        
        for plugin in self.plugins.values():
            if plugin.enabled:
                result = plugin.on_message(current_message)
                if result is not None:
                    current_message = result
        
        return current_message
    
    def intercept_response(self, response: Dict) -> Dict:
        """处理输出响应
        
        让所有启用的插件有机会修改响应
        
        Args:
            response: 原始响应
            
        Returns:
            处理后的响应
        """
        current_response = response
        
        for plugin in self.plugins.values():
            if plugin.enabled:
                result = plugin.on_response(current_response)
                if result is not None:
                    current_response = result
        
        return current_response
