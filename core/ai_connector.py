"""
AI连接器模块，基于Reactor模式实现AI请求和响应处理。
结合了OWL和OpenManus的设计思想，提供更智能的AI交互体验。
"""
import os
import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple, Callable
import traceback

from utils.ai_response_processor import AIResponseProcessor
from utils.file_manager import FileManager
from utils.logger import ConversationLogger

class AIConnector:
    """AI连接器，负责处理AI请求和响应，基于Reactor模式实现。
    
    提供统一的接口连接各种LLM服务，处理请求和响应，并自动化文件保存流程。
    实现了思考-行动循环，优化AI与系统交互。
    """
    
    def __init__(self, llm_service, system_prompt: str = "", max_retries: int = 3):
        """初始化AI连接器。
        
        Args:
            llm_service: LLM服务实例
            system_prompt: 系统提示词
            max_retries: 最大重试次数
        """
        self.llm = llm_service
        self.system_prompt = system_prompt
        self.max_retries = max_retries
        
        # 创建辅助组件
        self.file_manager = FileManager()
        self.response_processor = AIResponseProcessor(self.file_manager)
        self.logger = ConversationLogger()
        
        # 记录开始时间和请求信息
        self.start_time = None
        self.request_count = 0
        self.last_request_time = None
        
    async def request(self, prompt: str, task_name: str = None, 
                     include_thinking: bool = False, 
                     extra_context: List[Dict] = None) -> Dict[str, Any]:
        """发送请求到AI并处理响应。
        
        Args:
            prompt: 用户提示词
            task_name: 任务名称，用于保存文件时创建子目录
            include_thinking: 是否在结果中包含思考过程
            extra_context: 额外的上下文信息
            
        Returns:
            包含处理后响应的字典
        """
        self.start_time = time.time()
        self.request_count += 1
        self.last_request_time = self.start_time
        
        # 记录用户请求
        self.logger.log("user", prompt)
        self.logger.log_system_event("AI请求开始", f"任务: {task_name or '未命名任务'}")
        
        try:
            # 准备上下文
            context = []
            if extra_context:
                context.extend(extra_context)
            
            # 实现Reactor模式的思考-行动循环
            response_obj = await self.llm.generate(
                system_prompt=self.system_prompt,
                user_input=prompt,
                context=context
            )
            
            # 提取响应文本
            response_text = response_obj.get("response", "")
            thinking = response_obj.get("thinking", "")
            
            # 使用响应处理器处理响应
            processed_response, saved_files = self.response_processor.process_response(
                response_text, task_name
            )
            
            # 记录AI响应
            self.logger.log("assistant", processed_response)
            
            # 如果有思考过程，记录下来
            if thinking:
                self.logger.log_system_event(
                    "AI思考过程", 
                    f"思考内容长度: {len(thinking)}字符"
                )
                self.logger.log("thinking", thinking)
            
            # 如果保存了文件，记录信息
            if saved_files:
                files_info = "\n".join([f"- {os.path.basename(f)}" for f in saved_files])
                self.logger.log_system_event(
                    "文件保存", 
                    f"共保存了{len(saved_files)}个文件:\n{files_info}"
                )
            
            # 准备返回结果
            result = {
                "response": self.response_processor.format_for_display(
                    processed_response, include_thinking
                ),
                "thinking": thinking,
                "saved_files": saved_files,
                "execution_time": time.time() - self.start_time,
                "status": "success"
            }
            
            # 记录请求完成
            self.logger.log_system_event(
                "AI请求完成", 
                f"耗时: {result['execution_time']:.2f}秒"
            )
            
            return result
            
        except Exception as e:
            # 记录异常
            error_msg = str(e)
            stack_trace = traceback.format_exc()
            
            self.logger.log_system_event(
                "AI请求错误", 
                f"错误: {error_msg}\n堆栈跟踪:\n{stack_trace}"
            )
            
            # 准备错误返回结果
            return {
                "response": f"🚫 请求处理过程中发生错误: {error_msg}",
                "thinking": "",
                "saved_files": [],
                "execution_time": time.time() - self.start_time,
                "error": error_msg,
                "stack_trace": stack_trace,
                "status": "error"
            }
    
    async def request_with_retry(self, prompt: str, task_name: str = None,
                               include_thinking: bool = False,
                               extra_context: List[Dict] = None) -> Dict[str, Any]:
        """发送请求到AI并在失败时自动重试。
        
        Args:
            prompt: 用户提示词
            task_name: 任务名称，用于保存文件时创建子目录
            include_thinking: 是否在结果中包含思考过程
            extra_context: 额外的上下文信息
            
        Returns:
            包含处理后响应的字典
        """
        retries = 0
        last_error = None
        
        while retries < self.max_retries:
            result = await self.request(
                prompt, task_name, include_thinking, extra_context
            )
            
            if result.get("status") == "success":
                return result
            
            retries += 1
            last_error = result.get("error", "未知错误")
            
            # 记录重试信息
            self.logger.log_system_event(
                "AI请求重试", 
                f"第{retries}次重试，上次错误: {last_error}"
            )
            
            # 等待一会再重试（随重试次数增加等待时间）
            await asyncio.sleep(1 * retries)
        
        # 所有重试都失败后
        self.logger.log_system_event(
            "AI请求失败", 
            f"在{self.max_retries}次尝试后仍失败，最后错误: {last_error}"
        )
        
        return {
            "response": f"🚫 AI请求在{self.max_retries}次尝试后仍然失败: {last_error}",
            "thinking": "",
            "saved_files": [],
            "execution_time": time.time() - self.start_time,
            "error": last_error,
            "status": "error_with_retries"
        }
    
    def create_task_context(self, task_description: str, 
                           tools: List[Dict] = None,
                           constraints: List[str] = None) -> Dict[str, Any]:
        """创建任务上下文，用于多代理系统任务分配。
        
        Args:
            task_description: 任务描述
            tools: 可用工具列表
            constraints: 约束条件列表
            
        Returns:
            任务上下文字典
        """
        # 基本任务上下文
        context = {
            "task": task_description,
            "timestamp": time.time(),
            "session_dir": self.file_manager.get_session_dir()
        }
        
        # 添加可用工具
        if tools:
            context["tools"] = tools
            
        # 添加约束
        if constraints:
            context["constraints"] = constraints
            
        return context
