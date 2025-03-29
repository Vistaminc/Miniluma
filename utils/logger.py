"""
日志记录模块，用于记录MiniLuma框架的对话内容。
提供简单的日志记录功能，将对话内容保存到文件中。
"""
import os
import time
import datetime
import uuid
from typing import Optional, List, Dict, Any

class ConversationLogger:
    """对话日志记录器，记录用户与AI代理的对话内容。
    
    将对话记录到指定的日志文件中，支持按照指定格式命名日志文件。
    """
    
    def __init__(self, log_dir: str = None):
        """初始化日志记录器。
        
        Args:
            log_dir: 日志文件存储的目录，默认为项目根目录下的logs文件夹
        """
        # 如果没有指定日志目录，使用默认目录
        if not log_dir:
            # 获取项目根目录
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            self.log_dir = os.path.join(project_root, "logs")
        else:
            self.log_dir = log_dir
        
        # 确保日志目录存在
        os.makedirs(self.log_dir, exist_ok=True)
        
        self.log_file = None
        self.conversation_history = []
        
        # 生成对话记忆ID
        self.conversation_id = str(uuid.uuid4())
    
    def create_log_file(self) -> str:
        """创建新的日志文件。
        
        按照格式：/logs/年月日/时间前两位_时间+时间戳前两位.log
        
        Returns:
            日志文件的完整路径
        """
        # 获取当前时间
        now = datetime.datetime.now()
        timestamp = str(int(time.time()))
        
        # 创建日期目录
        date_str = now.strftime("%Y%m%d")
        date_dir = os.path.join(self.log_dir, date_str)
        os.makedirs(date_dir, exist_ok=True)
        
        # 用时间前两位作为前缀
        time_prefix = now.strftime("%H%M")[0:2]
        
        # 创建文件名：时间前两位_时分秒+时间戳前两位.log
        filename = f"{time_prefix}_{now.strftime('%H%M%S')}{timestamp[:2]}.log"
        
        # 完整文件路径
        file_path = os.path.join(date_dir, filename)
        
        # 打开文件准备写入
        self.log_file = file_path
        
        # 写入日志文件头部信息
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"对话记忆ID: {self.conversation_id}\n")
            f.write(f"=== MiniLuma对话日志 ===\n")
            f.write(f"开始时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"===================\n\n")
        
        return file_path
    
    def log(self, role: str, content: str, agent: str = None) -> None:
        """记录一条对话信息。
        
        Args:
            role: 发言角色，如"user"、"assistant"或"system"
            content: 对话内容
            agent: 代理名称（可选）
        """
        if not self.log_file:
            self.create_log_file()
        
        # 添加到内存中的历史记录
        log_entry = {
            "role": role,
            "content": content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        if agent:
            log_entry["agent"] = agent
        self.conversation_history.append(log_entry)
        
        # 写入到日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            # 使用表情符号区分不同角色
            if role == "user":
                display_role = "👤 用户"
            elif role == "assistant":
                display_role = "🤖 AI" + (f" ({agent})" if agent else "")
            else:
                display_role = "🔧 系统"
            f.write(f"[{timestamp}] {display_role}: {content}\n\n")
    
    def log_system_event(self, event_type: str, details: str = "") -> None:
        """记录系统事件。
        
        Args:
            event_type: 事件类型
            details: 事件详情
        """
        if not self.log_file:
            self.create_log_file()
        
        # 写入到日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] 系统事件 - {event_type}: {details}\n\n")
    
    def debug(self, message: str) -> None:
        """记录调试信息。
        
        Args:
            message: 调试信息内容
        """
        if not self.log_file:
            self.create_log_file()
        
        # 写入到日志文件
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] 🔍 调试: {message}\n\n")
    
    def log_execution_step(self, step_number: int, step_description: str, agent: str) -> None:
        """记录任务执行步骤。
        
        Args:
            step_number: 步骤编号
            step_description: 步骤描述
            agent: 执行步骤的代理名称
        """
        if not self.log_file:
            self.create_log_file()
        
        # 添加到内存中的历史记录
        self.conversation_history.append({
            "role": "system",
            "step": step_number,
            "description": step_description,
            "agent": agent,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 写入到日志文件，使用🔄表情标识执行步骤
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] 🔄 执行步骤 {step_number}: {step_description} (Agent: {agent})\n\n")
    
    def log_thinking(self, agent: str, thinking_content: str) -> None:
        """记录AI的思考过程。
        
        Args:
            agent: 思考的代理名称
            thinking_content: 思考内容
        """
        if not self.log_file:
            self.create_log_file()
        
        # 添加到内存中的历史记录
        self.conversation_history.append({
            "role": "thinking",
            "agent": agent,
            "content": thinking_content,
            "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        # 写入到日志文件，使用🤔表情标识思考过程
        with open(self.log_file, "a", encoding="utf-8") as f:
            timestamp = datetime.datetime.now().strftime("%H:%M:%S")
            f.write(f"[{timestamp}] 🤔 思考过程 ({agent}):\n<think>\n{thinking_content}\n</think>\n\n")
    
    def get_conversation_history(self) -> List[Dict[str, Any]]:
        """获取对话历史记录。
        
        Returns:
            对话历史记录列表
        """
        return self.conversation_history
    
    def get_conversation_id(self) -> str:
        """获取对话记忆ID。
        
        Returns:
            对话记忆ID
        """
        return self.conversation_id
    
    def save_complete_log(self) -> None:
        """在会话结束时保存完整日志。"""
        if not self.log_file:
            return
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            now = datetime.datetime.now()
            f.write(f"\n===================\n")
            f.write(f"结束时间: {now.strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"=== 日志记录结束 ===\n")
