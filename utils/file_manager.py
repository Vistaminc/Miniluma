"""
文件管理模块，用于处理MiniLuma框架生成的文件。
提供文件的存储、组织和管理功能。
"""
import os
import time
import datetime
import shutil
from typing import Optional, List, Dict, Any

class FileManager:
    """文件管理器类，用于管理AI代理生成的文件。
    
    此类处理文件的保存和查询，确保所有生成的文件都存储在正确的目录结构中。
    """
    
    def __init__(self, base_dir: str = None):
        """初始化文件管理器。
        
        Args:
            base_dir: 基础目录，默认为项目根目录下的results文件夹
        """
        # 如果没有指定基础目录，使用默认目录
        if not base_dir:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.base_dir = os.path.join(project_root, "results")
        else:
            self.base_dir = base_dir
        
        # 确保基础目录存在
        self._ensure_dir_exists(self.base_dir)
        
        # 创建本次会话的结果目录
        self._session_dir = self._create_session_dir()
    
    def _ensure_dir_exists(self, directory):
        """确保目录存在，如果不存在则创建。
        
        Args:
            directory: 需要确保存在的目录路径
        """
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    def _create_session_dir(self):
        """创建新的会话目录。
        
        Returns:
            新创建的会话目录路径
        """
        # 使用当前日期和时间为会话目录生成唯一名称
        now = datetime.datetime.now()
        
        # 创建日期目录
        date_str = now.strftime("%Y%m%d")
        date_dir = os.path.join(self.base_dir, date_str)
        self._ensure_dir_exists(date_dir)
        
        # 用时间前两位作为前缀
        time_prefix = now.strftime("%H%M")[0:2]
        timestamp = str(int(time.time()))
        dir_name = f"{time_prefix}_{now.strftime('%H%M%S')}{timestamp[:2]}"
        
        session_dir = os.path.join(date_dir, dir_name)
        self._ensure_dir_exists(session_dir)
        return session_dir
    
    def save_file(self, content: str, filename: str, subdir: str = None) -> str:
        """保存文本内容到文件。
        
        Args:
            content: 要保存的文本内容
            filename: 文件名
            subdir: 可选的子目录名
            
        Returns:
            保存的文件的完整路径
        """
        # 确保会话目录存在
        self._ensure_dir_exists(self.session_dir)
        
        # 如果提供了子目录，创建该子目录
        if subdir:
            target_dir = os.path.join(self.session_dir, subdir)
            self._ensure_dir_exists(target_dir)
        else:
            target_dir = self.session_dir
        
        # 自动检测和纠正文件扩展名
        if '.' not in filename:
            # 尝试从内容推断文件类型
            if "<html" in content or "<!DOCTYPE html" in content:
                if not filename.endswith('.html'):
                    filename += '.html'
            elif "def " in content or "import " in content or "class " in content:
                if not filename.endswith('.py'):
                    filename += '.py'
            elif "{" in content and "}" in content and ("function" in content or ":" in content):
                if not filename.endswith('.js'):
                    filename += '.js'
            elif "body" in content and "{" in content and "}" in content:
                if not filename.endswith('.css'):
                    filename += '.css'
            else:
                # 默认文本文件
                if not filename.endswith('.txt'):
                    filename += '.txt'
        
        # 创建文件路径，使用原始文件名
        file_path = os.path.join(target_dir, filename)
        
        # 写入内容
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        return file_path
    
    def save_binary_file(self, content: bytes, filename: str, subdir: str = None) -> str:
        """保存二进制内容到文件。
        
        Args:
            content: 要保存的二进制内容
            filename: 文件名
            subdir: 可选的子目录名
            
        Returns:
            保存的文件的完整路径
        """
        # 确保会话目录存在
        self._ensure_dir_exists(self.session_dir)
        
        # 如果提供了子目录，创建该子目录
        if subdir:
            target_dir = os.path.join(self.session_dir, subdir)
            self._ensure_dir_exists(target_dir)
        else:
            target_dir = self.session_dir
        
        # 创建文件路径，使用原始文件名
        file_path = os.path.join(target_dir, filename)
        
        # 写入内容
        with open(file_path, 'wb') as f:
            f.write(content)
        
        return file_path
    
    def copy_file(self, source_path: str, target_filename: str = None, subdir: str = None) -> str:
        """将外部文件复制到会话目录。
        
        Args:
            source_path: 源文件路径
            target_filename: 目标文件名，如果不提供则使用源文件名
            subdir: 可选的子目录名
            
        Returns:
            复制后的文件的完整路径
        """
        # 确保会话目录存在
        self._ensure_dir_exists(self.session_dir)
        
        # 如果没有提供目标文件名，使用源文件名
        if not target_filename:
            target_filename = os.path.basename(source_path)
        
        # 如果提供了子目录，创建该子目录
        if subdir:
            target_dir = os.path.join(self.session_dir, subdir)
            self._ensure_dir_exists(target_dir)
        else:
            target_dir = self.session_dir
        
        # 完整目标文件路径
        target_path = os.path.join(target_dir, target_filename)
        
        # 复制文件
        shutil.copy2(source_path, target_path)
        
        return target_path
    
    def list_files(self, subdir: str = None) -> List[str]:
        """列出会话目录中的所有文件。
        
        Args:
            subdir: 可选的子目录名
            
        Returns:
            文件路径列表
        """
        # 确定要搜索的目录
        if subdir:
            search_dir = os.path.join(self.session_dir, subdir)
            self._ensure_dir_exists(search_dir)
        else:
            search_dir = self.session_dir
        
        # 获取所有文件
        files = []
        for root, _, filenames in os.walk(search_dir):
            for filename in filenames:
                files.append(os.path.join(root, filename))
        
        return files
    
    def get_session_dir(self) -> str:
        """获取当前会话目录路径。
        
        Returns:
            当前会话目录的完整路径
        """
        return self._session_dir
    
    def extract_code_from_markdown(self, markdown_text: str) -> Dict[str, str]:
        """从Markdown文本中提取代码块。
        
        Args:
            markdown_text: 包含代码块的Markdown文本
            
        Returns:
            字典，键为推断的文件名，值为代码内容
        """
        import re
        
        # 定义代码块正则表达式模式
        # 匹配```语言\n代码内容\n```格式
        pattern = r'```(\w*)\n([\s\S]*?)\n```'
        
        # 查找所有代码块
        code_blocks = re.findall(pattern, markdown_text)
        
        # 提取文件名提示
        filename_pattern = r'(?:filename|文件名)[:：]\s*([^\s\n]+)'
        filename_matches = re.findall(filename_pattern, markdown_text, re.IGNORECASE)
        
        result = {}
        
        # 处理每个代码块
        for i, (lang, code) in enumerate(code_blocks):
            # 如果有明确指定的文件名，使用它
            if i < len(filename_matches):
                filename = filename_matches[i]
            else:
                # 根据语言确定默认文件名
                lang = lang.lower().strip()
                if lang == 'html' or ('<html' in code):
                    filename = f"index_{i+1}.html"
                elif lang in ['python', 'py']:
                    filename = f"script_{i+1}.py"
                elif lang in ['javascript', 'js']:
                    filename = f"script_{i+1}.js"
                elif lang == 'css':
                    filename = f"style_{i+1}.css"
                elif lang == 'json':
                    filename = f"data_{i+1}.json"
                else:
                    filename = f"file_{i+1}.txt"
            
            result[filename] = code
        
        return result
    
    def save_files_from_markdown(self, markdown_text: str, subdir: str = None) -> List[str]:
        """从Markdown响应中提取并保存所有代码块为文件。
        
        Args:
            markdown_text: 包含代码块的Markdown文本
            subdir: 可选的子目录名
            
        Returns:
            保存的所有文件路径列表
        """
        code_files = self.extract_code_from_markdown(markdown_text)
        saved_files = []
        
        for filename, code in code_files.items():
            file_path = self.save_file(code, filename, subdir)
            saved_files.append(file_path)
        
        return saved_files
    
    @property
    def session_dir(self) -> str:
        """会话目录属性。
        
        Returns:
            当前会话目录的完整路径
        """
        return self._session_dir
