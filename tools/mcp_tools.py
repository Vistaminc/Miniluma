"""
MCP工具集实现
基于OWL框架的多模态工具，支持网络搜索、浏览器自动化等功能
"""
import os
import json
import base64
import datetime
import requests
from typing import Dict, List, Any, Optional, Union

from core.mcp import mcp_tool

# ==================== 网络工具 ====================

@mcp_tool(name="web_search", description="执行网络搜索并返回搜索结果")
def web_search(query: str, num_results: int = 5) -> str:
    """
    执行网络搜索并返回搜索结果
    
    Args:
        query: 搜索查询
        num_results: 返回结果数量
        
    Returns:
        搜索结果文本
    """
    try:
        # 这里使用模拟数据，实际应用中应集成真实搜索API
        # 例如使用Serper.dev, SerpAPI, Google Custom Search API等
        return f"为查询 '{query}' 返回了 {num_results} 条搜索结果。在实际部署中，请替换为真实搜索API。"
    except Exception as e:
        return f"搜索时发生错误: {str(e)}"

@mcp_tool(name="fetch_webpage", description="获取网页内容")
def fetch_webpage(url: str) -> str:
    """
    获取并返回网页内容
    
    Args:
        url: 网页URL
        
    Returns:
        网页内容文本
    """
    try:
        # 在实际应用中，应该使用更健壮的网页抓取方式
        # 例如使用Playwright或Puppeteer处理JavaScript渲染的页面
        return f"成功获取URL '{url}' 的内容。在实际部署中，请使用Playwright等工具处理。"
    except Exception as e:
        return f"获取网页时发生错误: {str(e)}"

# ==================== 文件工具 ====================

@mcp_tool(name="read_file", description="读取文件内容")
def read_file(file_path: str) -> str:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容
    """
    try:
        if not os.path.exists(file_path):
            return f"错误: 文件 '{file_path}' 不存在"
            
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        return content
    except Exception as e:
        return f"读取文件时发生错误: {str(e)}"

@mcp_tool(name="write_file", description="写入内容到文件")
def write_file(file_path: str, content: str, append: bool = False) -> str:
    """
    写入内容到文件
    
    Args:
        file_path: 文件路径
        content: 要写入的内容
        append: 是否追加模式
        
    Returns:
        操作结果
    """
    try:
        # 确保目录存在
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
            
        return f"成功{'追加' if append else '写入'}内容到文件 '{file_path}'"
    except Exception as e:
        return f"写入文件时发生错误: {str(e)}"

# ==================== 代码执行工具 ====================

@mcp_tool(name="execute_python", description="执行Python代码")
def execute_python(code: str) -> str:
    """
    在安全的环境中执行Python代码
    
    Args:
        code: 要执行的Python代码
        
    Returns:
        执行结果
    """
    try:
        # 注意：实际部署时应使用沙箱或隔离环境
        # 这里使用简单的locals隔离
        locals_dict = {}
        
        # 捕获打印输出
        import io
        import sys
        from contextlib import redirect_stdout
        
        buffer = io.StringIO()
        with redirect_stdout(buffer):
            exec(code, {"__builtins__": __builtins__}, locals_dict)
            
        # 获取标准输出
        stdout = buffer.getvalue()
        
        # 构建结果
        result = "执行结果:\n"
        if stdout:
            result += f"输出:\n{stdout}\n"
            
        # 添加局部变量
        if locals_dict:
            result += "局部变量:\n"
            for k, v in locals_dict.items():
                if not k.startswith('_'):
                    result += f"{k} = {repr(v)}\n"
                    
        return result
    except Exception as e:
        return f"执行代码时发生错误: {str(e)}"

# ==================== 时间日期工具 ====================

@mcp_tool(name="get_current_datetime", description="获取当前日期和时间")
def get_current_datetime() -> str:
    """
    获取当前日期和时间
    
    Returns:
        当前日期时间信息
    """
    now = datetime.datetime.now()
    return {
        "iso_format": now.isoformat(),
        "date": now.strftime("%Y-%m-%d"),
        "time": now.strftime("%H:%M:%S"),
        "weekday": now.strftime("%A"),
        "timestamp": now.timestamp()
    }

# ==================== 数据处理工具 ====================

@mcp_tool(name="json_parser", description="解析JSON文本")
def json_parser(json_text: str) -> Dict:
    """
    解析JSON文本为结构化数据
    
    Args:
        json_text: JSON格式的文本
        
    Returns:
        解析后的数据结构
    """
    try:
        data = json.loads(json_text)
        return data
    except json.JSONDecodeError as e:
        return {"error": f"JSON解析错误: {str(e)}"}

@mcp_tool(name="format_data", description="格式化数据为可读格式")
def format_data(data: Any, format_type: str = "json") -> str:
    """
    将数据格式化为可读格式
    
    Args:
        data: 要格式化的数据
        format_type: 格式类型("json", "text", "table")
        
    Returns:
        格式化后的文本
    """
    try:
        if format_type.lower() == "json":
            return json.dumps(data, indent=2, ensure_ascii=False)
        elif format_type.lower() == "text":
            if isinstance(data, (dict, list)):
                return str(data)
            return data
        elif format_type.lower() == "table":
            # 简单表格格式化
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                if not data:
                    return "空表格"
                    
                # 获取所有可能的键
                all_keys = set()
                for item in data:
                    all_keys.update(item.keys())
                    
                # 按字母排序键名
                keys = sorted(all_keys)
                
                # 构建表头
                table = " | ".join(keys) + "\n"
                table += "-|-".join(["-" * len(k) for k in keys]) + "\n"
                
                # 添加行
                for item in data:
                    row = []
                    for k in keys:
                        row.append(str(item.get(k, "")))
                    table += " | ".join(row) + "\n"
                    
                return table
            return "数据不适合表格格式化"
        else:
            return f"不支持的格式类型: {format_type}"
    except Exception as e:
        return f"格式化数据时发生错误: {str(e)}"

# ==================== 统合工具包 ====================

def get_all_mcp_tools() -> List:
    """获取所有MCP工具"""
    from tools.mcp_file_tools import get_all_file_tools
    from tools.mcp_ai_tools import get_all_ai_tools
    
    # 基础工具
    base_tools = [
        web_search,
        fetch_webpage,
        read_file,
        write_file,
        execute_python,
        get_current_datetime,
        json_parser,
        format_data
    ]
    
    # 添加文件工具
    file_tools = get_all_file_tools()
    
    # 添加AI对话工具
    ai_tools = get_all_ai_tools()
    
    # 返回所有工具
    return base_tools + file_tools + ai_tools
