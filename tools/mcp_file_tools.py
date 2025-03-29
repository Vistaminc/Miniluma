"""
MCP 文件管理工具
提供更强大的文件操作能力，支持文件保存、读取、列表等功能
"""
import os
import json
import yaml
import csv
import shutil
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

from core.mcp import mcp_tool

class FileManager:
    """文件管理器类，提供高级文件操作功能"""
    
    def __init__(self, base_dir: Optional[str] = None):
        """初始化文件管理器
        
        Args:
            base_dir: 基础目录，如果提供，所有相对路径将相对于此目录
        """
        self.base_dir = base_dir
    
    def resolve_path(self, file_path: str) -> str:
        """解析文件路径
        
        Args:
            file_path: 文件路径
            
        Returns:
            解析后的绝对路径
        """
        if self.base_dir and not os.path.isabs(file_path):
            return os.path.abspath(os.path.join(self.base_dir, file_path))
        return os.path.abspath(file_path)
    
    def read_file(self, file_path: str, encoding: str = 'utf-8') -> str:
        """读取文件内容
        
        Args:
            file_path: 文件路径
            encoding: 文件编码
            
        Returns:
            文件内容
        """
        resolved_path = self.resolve_path(file_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        with open(resolved_path, 'r', encoding=encoding) as f:
            return f.read()
    
    def write_file(self, file_path: str, content: str, append: bool = False, encoding: str = 'utf-8') -> str:
        """写入内容到文件
        
        Args:
            file_path: 文件路径
            content: 要写入的内容
            append: 是否追加模式
            encoding: 文件编码
            
        Returns:
            操作结果信息
        """
        resolved_path = self.resolve_path(file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        
        mode = 'a' if append else 'w'
        with open(resolved_path, mode, encoding=encoding) as f:
            f.write(content)
        
        return f"成功{'追加' if append else '写入'}内容到文件 '{file_path}'"
    
    def list_files(self, directory: str, pattern: str = "*", recursive: bool = False) -> List[str]:
        """列出目录中的文件
        
        Args:
            directory: 目录路径
            pattern: 文件匹配模式
            recursive: 是否递归搜索
            
        Returns:
            文件路径列表
        """
        resolved_dir = self.resolve_path(directory)
        if not os.path.exists(resolved_dir):
            raise FileNotFoundError(f"目录不存在: {resolved_dir}")
        
        result = []
        if recursive:
            for root, _, files in os.walk(resolved_dir):
                for file in files:
                    if Path(file).match(pattern):
                        rel_path = os.path.relpath(os.path.join(root, file), resolved_dir)
                        result.append(rel_path)
        else:
            for file in os.listdir(resolved_dir):
                file_path = os.path.join(resolved_dir, file)
                if os.path.isfile(file_path) and Path(file).match(pattern):
                    result.append(file)
        
        return result
    
    def save_json(self, file_path: str, data: Any, indent: int = 2, ensure_ascii: bool = False) -> str:
        """保存数据为JSON文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
            indent: 缩进空格数
            ensure_ascii: 是否确保ASCII编码
            
        Returns:
            操作结果信息
        """
        resolved_path = self.resolve_path(file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        
        with open(resolved_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, ensure_ascii=ensure_ascii)
        
        return f"成功保存JSON数据到文件 '{file_path}'"
    
    def load_json(self, file_path: str) -> Any:
        """从JSON文件加载数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        resolved_path = self.resolve_path(file_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def save_yaml(self, file_path: str, data: Any) -> str:
        """保存数据为YAML文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据
            
        Returns:
            操作结果信息
        """
        resolved_path = self.resolve_path(file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        
        with open(resolved_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
        
        return f"成功保存YAML数据到文件 '{file_path}'"
    
    def load_yaml(self, file_path: str) -> Any:
        """从YAML文件加载数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据
        """
        resolved_path = self.resolve_path(file_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        with open(resolved_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def save_csv(self, file_path: str, data: List[Dict], fieldnames: Optional[List[str]] = None) -> str:
        """保存数据为CSV文件
        
        Args:
            file_path: 文件路径
            data: 要保存的数据（字典列表）
            fieldnames: 字段名列表，如果为None则使用第一个字典的键
            
        Returns:
            操作结果信息
        """
        resolved_path = self.resolve_path(file_path)
        
        # 确保目录存在
        os.makedirs(os.path.dirname(resolved_path), exist_ok=True)
        
        if not data:
            return f"错误: 没有数据可保存到 '{file_path}'"
        
        if not fieldnames:
            fieldnames = list(data[0].keys())
        
        with open(resolved_path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(data)
        
        return f"成功保存CSV数据到文件 '{file_path}'"
    
    def load_csv(self, file_path: str) -> List[Dict]:
        """从CSV文件加载数据
        
        Args:
            file_path: 文件路径
            
        Returns:
            加载的数据（字典列表）
        """
        resolved_path = self.resolve_path(file_path)
        if not os.path.exists(resolved_path):
            raise FileNotFoundError(f"文件不存在: {resolved_path}")
        
        result = []
        with open(resolved_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                result.append(dict(row))
        
        return result
    
    def copy_file(self, source: str, destination: str) -> str:
        """复制文件
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
            
        Returns:
            操作结果信息
        """
        resolved_source = self.resolve_path(source)
        resolved_dest = self.resolve_path(destination)
        
        if not os.path.exists(resolved_source):
            raise FileNotFoundError(f"源文件不存在: {resolved_source}")
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(resolved_dest), exist_ok=True)
        
        shutil.copy2(resolved_source, resolved_dest)
        
        return f"成功复制文件 '{source}' 到 '{destination}'"
    
    def move_file(self, source: str, destination: str) -> str:
        """移动文件
        
        Args:
            source: 源文件路径
            destination: 目标文件路径
            
        Returns:
            操作结果信息
        """
        resolved_source = self.resolve_path(source)
        resolved_dest = self.resolve_path(destination)
        
        if not os.path.exists(resolved_source):
            raise FileNotFoundError(f"源文件不存在: {resolved_source}")
        
        # 确保目标目录存在
        os.makedirs(os.path.dirname(resolved_dest), exist_ok=True)
        
        shutil.move(resolved_source, resolved_dest)
        
        return f"成功移动文件 '{source}' 到 '{destination}'"
    
    def delete_file(self, file_path: str) -> str:
        """删除文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            操作结果信息
        """
        resolved_path = self.resolve_path(file_path)
        
        if not os.path.exists(resolved_path):
            return f"文件不存在: {resolved_path}"
        
        if os.path.isdir(resolved_path):
            shutil.rmtree(resolved_path)
            return f"成功删除目录 '{file_path}'"
        else:
            os.remove(resolved_path)
            return f"成功删除文件 '{file_path}'"

# ==================== MCP文件工具 ====================

# 全局文件管理器实例
_file_manager = FileManager()

@mcp_tool(name="list_files", description="列出目录中的文件")
def list_files_tool(directory: str, pattern: str = "*", recursive: bool = False) -> List[str]:
    """
    列出目录中的文件
    
    Args:
        directory: 目录路径
        pattern: 文件匹配模式
        recursive: 是否递归搜索
        
    Returns:
        文件路径列表
    """
    try:
        return _file_manager.list_files(directory, pattern, recursive)
    except Exception as e:
        return [f"错误: {str(e)}"]

@mcp_tool(name="save_file", description="保存内容到文件")
def save_file_tool(file_path: str, content: str, append: bool = False) -> str:
    """
    保存内容到文件
    
    Args:
        file_path: 文件路径
        content: 要保存的内容
        append: 是否追加模式
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.write_file(file_path, content, append)
    except Exception as e:
        return f"保存文件时出错: {str(e)}"

@mcp_tool(name="read_file", description="读取文件内容")
def read_file_tool(file_path: str) -> str:
    """
    读取文件内容
    
    Args:
        file_path: 文件路径
        
    Returns:
        文件内容
    """
    try:
        return _file_manager.read_file(file_path)
    except FileNotFoundError:
        return f"错误: 文件 '{file_path}' 不存在"
    except Exception as e:
        return f"读取文件时出错: {str(e)}"

@mcp_tool(name="save_json", description="保存数据为JSON文件")
def save_json_tool(file_path: str, data: Any) -> str:
    """
    保存数据为JSON文件
    
    Args:
        file_path: 文件路径
        data: 要保存的数据
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.save_json(file_path, data)
    except Exception as e:
        return f"保存JSON文件时出错: {str(e)}"

@mcp_tool(name="load_json", description="从JSON文件加载数据")
def load_json_tool(file_path: str) -> Any:
    """
    从JSON文件加载数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        加载的数据
    """
    try:
        return _file_manager.load_json(file_path)
    except FileNotFoundError:
        return {"error": f"文件不存在: {file_path}"}
    except Exception as e:
        return {"error": f"加载JSON文件时出错: {str(e)}"}

@mcp_tool(name="save_csv", description="保存数据为CSV文件")
def save_csv_tool(file_path: str, data: List[Dict], fieldnames: Optional[List[str]] = None) -> str:
    """
    保存数据为CSV文件
    
    Args:
        file_path: 文件路径
        data: 要保存的数据（字典列表）
        fieldnames: 字段名列表，如果为None则使用第一个字典的键
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.save_csv(file_path, data, fieldnames)
    except Exception as e:
        return f"保存CSV文件时出错: {str(e)}"

@mcp_tool(name="load_csv", description="从CSV文件加载数据")
def load_csv_tool(file_path: str) -> List[Dict]:
    """
    从CSV文件加载数据
    
    Args:
        file_path: 文件路径
        
    Returns:
        加载的数据（字典列表）
    """
    try:
        return _file_manager.load_csv(file_path)
    except FileNotFoundError:
        return [{"error": f"文件不存在: {file_path}"}]
    except Exception as e:
        return [{"error": f"加载CSV文件时出错: {str(e)}"}]

@mcp_tool(name="copy_file", description="复制文件")
def copy_file_tool(source: str, destination: str) -> str:
    """
    复制文件
    
    Args:
        source: 源文件路径
        destination: 目标文件路径
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.copy_file(source, destination)
    except Exception as e:
        return f"复制文件时出错: {str(e)}"

@mcp_tool(name="move_file", description="移动文件")
def move_file_tool(source: str, destination: str) -> str:
    """
    移动文件
    
    Args:
        source: 源文件路径
        destination: 目标文件路径
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.move_file(source, destination)
    except Exception as e:
        return f"移动文件时出错: {str(e)}"

@mcp_tool(name="delete_file", description="删除文件")
def delete_file_tool(file_path: str) -> str:
    """
    删除文件
    
    Args:
        file_path: 文件路径
        
    Returns:
        操作结果信息
    """
    try:
        return _file_manager.delete_file(file_path)
    except Exception as e:
        return f"删除文件时出错: {str(e)}"

def get_all_file_tools() -> List:
    """获取所有文件工具"""
    return [
        list_files_tool,
        save_file_tool,
        read_file_tool,
        save_json_tool,
        load_json_tool,
        save_csv_tool,
        load_csv_tool,
        copy_file_tool,
        move_file_tool,
        delete_file_tool
    ]
