"""
AI响应处理模块，用于处理和格式化AI响应内容。
自动提取文件和代码，并处理不同格式的AI输出。
"""
import os
import re
from typing import Dict, List, Any, Optional, Tuple
from utils.file_manager import FileManager

class AIResponseProcessor:
    """AI响应处理器，用于提取和处理AI生成的内容。
    
    具备自动代码提取、文件保存、响应格式化等功能，使AI与文件系统的交互更加智能化。
    """
    
    def __init__(self, file_manager: Optional[FileManager] = None):
        """初始化AI响应处理器。
        
        Args:
            file_manager: 文件管理器实例，如果为None则创建新实例
        """
        self.file_manager = file_manager or FileManager()
        
    def process_response(self, response: str, task_name: str = None) -> Tuple[str, List[str]]:
        """处理AI完整响应文本。
        
        Args:
            response: AI生成的原始响应文本
            task_name: 任务名称，用于命名子目录
            
        Returns:
            处理后的响应文本和保存的文件路径列表
        """
        # 创建任务子目录（如果提供了任务名）
        subdir = task_name if task_name else None
        
        # 查找并提取文件创建意图
        processed_response, saved_files = self._process_and_extract_files(response, subdir)
        
        return processed_response, saved_files
    
    def _process_and_extract_files(self, response: str, subdir: str = None) -> Tuple[str, List[str]]:
        """从响应中提取并保存文件，同时返回处理后的响应。
        
        Args:
            response: AI生成的原始响应文本
            subdir: 可选的子目录名
            
        Returns:
            处理后的响应文本和保存的文件路径列表
        """
        saved_files = []
        
        # 从Markdown代码块提取并保存文件
        code_files = self.file_manager.extract_code_from_markdown(response)
        
        for filename, code in code_files.items():
            file_path = self.file_manager.save_file(code, filename, subdir)
            saved_files.append(file_path)
            
            # 获取相对路径用于在消息中显示
            session_dir = self.file_manager.get_session_dir()
            rel_path = os.path.relpath(file_path, start=session_dir)
            
            # 在响应中添加文件保存通知
            if len(saved_files) == 1:  # 第一个文件时添加分隔符
                response += "\n\n---\n\n📁 **文件已保存：**\n"
            
            response += f"- `{rel_path}` ({len(code)} 字节)\n"
            
        return response, saved_files
    
    def extract_thought_process(self, response: str) -> Tuple[str, str]:
        """从响应中提取思考过程和最终回答。
        
        用于分离AI的思考过程和给用户的最终回答。
        
        Args:
            response: AI生成的原始响应文本
            
        Returns:
            思考过程和最终回答的元组
        """
        # 查找思考过程分隔符
        thought_markers = [
            "思考过程：", "思考过程:", "Thinking:", "Thinking process:", 
            "思路分析：", "思路分析:", "Analysis:", 
            "让我思考一下", "Let me think"
        ]
        
        response_markers = [
            "最终回答：", "最终回答:", "Final answer:", 
            "回答：", "回答:", "Answer:", 
            "总结：", "总结:", "Summary:"
        ]
        
        # 默认整个内容为回答
        thought = ""
        answer = response
        
        # 尝试寻找思考过程和回答的分隔点
        for marker in response_markers:
            if marker in response:
                parts = response.split(marker, 1)
                thought = parts[0].strip()
                answer = parts[1].strip()
                break
                
        # 如果没有找到回答标记，但有思考标记
        if thought == "" and answer == response:
            for marker in thought_markers:
                if marker in response:
                    # 不分割，但标记整个文本包含思考过程
                    thought = response
                    answer = "请参考上述分析。"
                    break
        
        return thought, answer
    
    def format_for_display(self, response: str, include_thought_process: bool = False) -> str:
        """格式化响应用于显示。
        
        Args:
            response: AI生成的原始响应文本
            include_thought_process: 是否包含思考过程
            
        Returns:
            格式化后用于显示的响应文本
        """
        thought, answer = self.extract_thought_process(response)
        
        if include_thought_process and thought:
            return f"🤔 **思考过程**：\n\n{thought}\n\n---\n\n💡 **回答**：\n\n{answer}"
        else:
            return answer
        
    def detect_completions(self, response: str) -> List[Dict[str, Any]]:
        """检测响应中的不完整部分，如未完成的代码或指示。
        
        Args:
            response: AI生成的原始响应文本
            
        Returns:
            未完成元素的列表，每个元素包含类型和细节
        """
        incomplete_elements = []
        
        # 检测未关闭的代码块
        open_code_blocks = len(re.findall(r'```\w*\n', response))
        close_code_blocks = len(re.findall(r'\n```', response))
        
        if open_code_blocks > close_code_blocks:
            incomplete_elements.append({
                "type": "code_block",
                "details": f"有 {open_code_blocks - close_code_blocks} 个未关闭的代码块"
            })
            
        # 检测省略号结尾（可能表示未完成）
        if response.rstrip().endswith(("...", "…")):
            incomplete_elements.append({
                "type": "ellipsis",
                "details": "响应以省略号结束，可能未完成"
            })
            
        # 检测未完成的指示词
        instruction_markers = ["接下来", "next", "继续", "continue", "然后", "then"]
        last_lines = response.split('\n')[-3:]  # 检查最后几行
        
        for line in last_lines:
            for marker in instruction_markers:
                if marker in line.lower():
                    incomplete_elements.append({
                        "type": "instruction",
                        "details": f"响应中含有可能的未完成指示：'{line.strip()}'"
                    })
                    break
        
        return incomplete_elements
