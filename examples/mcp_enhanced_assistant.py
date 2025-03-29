"""
增强版 MCP 助手示例
集成了文件管理、AI 对话请求和多模态处理能力
"""
import os
import sys
import json
import asyncio
import datetime
from typing import Dict, List, Any, Optional, Union
import logging
import inspect
import time
import re
import shutil

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.mcp import MCPMessage
from core.mcp_agent import MCPAgent
from core.mcp_memory import MCPMemory, SqliteMemory
from core.mcp_feedback import MCPFeedback
from core.mcp_multimodal import MCPMultimodal
from core.mcp_plugins import PluginManager
from core.config import Config
from tools.mcp_tools import get_all_mcp_tools
from providers.factory import create_provider

class MCPEnhancedAssistant:
    """增强版 MCP 助手，提供文件保存和 AI 对话请求等功能"""
    
    def __init__(self, name: str):
        """初始化基本属性，真正的初始化通过_initialize方法完成"""
        self.name = name
        self.agent = None
        self.memory = None
        self.feedback = None
        self.multimodal = None
        self.plugin_manager = None
        self.conversation_history = []
        self.last_response = None
        self.last_saved_file = None
        self.provider_name = None
        self.model = None
        
        # 初始化自动保存相关属性
        self.auto_save_enabled = True  # 默认启用自动保存
        self.pending_files_to_save = []  # 待保存的文件列表
        self.last_auto_save_time = time.time()  # 上次自动保存时间
        self.auto_save_interval = 300  # 默认自动保存间隔(秒)
        self.auto_saved_files = {}  # 已自动保存的文件映射 {原始路径: 保存路径}
        
        # 项目根目录 (用于文件保存)
        # 获取脚本所在目录的上一级目录，即项目根目录
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        
        # 对话ID持久性
        self.conversation_id_file = os.path.join(self.project_root, "data", "last_conversation_id.txt")
        
        # 初始化日志记录器
        from utils.logger import ConversationLogger
        self.logger = ConversationLogger()
        # 获取日志文件路径
        self.log_file = self.logger.create_log_file()
        # 获取对话记忆ID
        self.conversation_id = self.logger.get_conversation_id()
        
        # 配置模块级日志
        global logger
        logger = logging.getLogger("MCP助手")
        logger.setLevel(logging.INFO)
        
        # 添加文件处理器
        file_handler = logging.FileHandler(self.log_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)
        
        # 添加控制台处理器
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.INFO)
        
        # 设置日志格式
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        # 添加处理器到日志记录器
        logger.addHandler(file_handler)
        logger.addHandler(console_handler)
        
        # 记录初始化信息
        logger.info(f"对话记忆ID: {self.conversation_id}")
    
    @classmethod
    async def create(cls, 
                    name: str = "增强版助手",
                    provider_name: str = None,
                    model: str = None,
                    system_prompt: Optional[str] = None,
                    memory_path: Optional[str] = None,
                    enable_multimodal: bool = True,
                    enable_auto_save: bool = True):
        """异步工厂方法，创建并初始化增强版助手实例
        
        Args:
            name: 助手名称
            provider_name: LLM提供商名称
            model: 模型名称
            system_prompt: 系统提示
            memory_path: 记忆数据库路径
            enable_multimodal: 是否启用多模态处理
            enable_auto_save: 是否启用自动保存功能
            
        Returns:
            初始化好的助手实例
        """
        instance = cls(name)
        
        # 记录模型信息
        instance.provider_name = provider_name
        instance.model = model
        
        # 设置自动保存状态
        instance.auto_save_enabled = enable_auto_save
        
        # 获取配置
        config = Config()
        
        # 获取默认提供商和模型
        if not provider_name:
            provider_name = config.get_default_provider()
        if not model:
            model = config.get_default_model(provider_name)
            
        # 异步创建LLM服务
        logger.info(f"正在创建LLM服务，提供商: {provider_name}，模型: {model}")
        llm_service = await create_provider(provider_name, model)
        
        # 初始化 MCP 代理
        instance.agent = MCPAgent(
            name=name,
            llm_service=llm_service,
            system_prompt=system_prompt
        )
        
        # 注册所有工具
        for tool in get_all_mcp_tools():
            instance.agent.toolkit.register_tool(tool)
        
        # 初始化记忆系统
        if memory_path:
            instance.memory = SqliteMemory(name=name, db_path=memory_path)
        else:
            instance.memory = SqliteMemory(name=name)
        
        # 初始化反馈系统
        instance.feedback = MCPFeedback()
        
        # 初始化多模态处理（如果启用）
        if enable_multimodal:
            instance.multimodal = MCPMultimodal()
        else:
            instance.multimodal = None
        
        # 初始化插件管理器
        instance.plugin_manager = PluginManager()
        
        # 注册默认插件并初始化
        instance.plugin_manager.initialize_plugins(instance.agent)
        
        # 会话历史
        instance.conversation_history = []
        
        # 最后一条消息的响应
        instance.last_response = None
        
        logger.info(f"MCP助手 '{name}' 初始化完成")
        return instance
    
    async def process(self, 
                     user_input: str, 
                     add_to_memory: bool = True,
                     memory_metadata: Optional[Dict[str, Any]] = None) -> str:
        """处理用户输入并生成回复
        
        Args:
            user_input: 用户输入
            add_to_memory: 是否添加到记忆系统
            memory_metadata: 记忆元数据
            
        Returns:
            助手回复
        """
        if not user_input:
            return "请输入内容"
        
        # 记录用户消息
        logger.info(f"用户输入: {user_input}")
        
        # 同时记录到标准会话日志
        self.logger.log("user", user_input)
        
        # 添加用户消息到历史
        user_message = MCPMessage("user", user_input)
        self.conversation_history.append(user_message)
        
        # 检查是否是恢复记忆请求 (-m<记忆ID>)
        memory_pattern = re.compile(r'^-m([a-zA-Z0-9_-]+)$')
        memory_match = memory_pattern.match(user_input.strip())
        if memory_match:
            logger.info("检测到恢复记忆请求")
            memory_id = memory_match.group(1)
            return await self._restore_from_memory(memory_id)
        
        # 检查是否是保存生成文件请求 (-save)
        save_pattern = re.compile(r'^-save(\s+.+)?$')
        save_match = save_pattern.match(user_input.strip())
        if save_match:
            logger.info("检测到保存生成文件请求")
            file_path = save_match.group(1).strip() if save_match.group(1) else None
            return await self._save_generated_files(file_path)
            
        # 检查是否是自动保存设置请求
        auto_save_pattern = re.compile(r'^-autosave\s+(on|off|interval\s+\d+)$')
        auto_save_match = auto_save_pattern.match(user_input.strip())
        if auto_save_match:
            logger.info("检测到自动保存设置请求")
            setting = auto_save_match.group(1)
            return self._configure_auto_save(setting)
        
        # 检查是否是对话保存请求
        if self._is_save_request(user_input):
            logger.info("检测到对话保存请求")
            file_path = self._save_conversation()
            self.last_response = f"已将对话保存到文件：{file_path}"
            
            # 添加助手消息到历史
            assistant_message = MCPMessage("assistant", self.last_response)
            self.conversation_history.append(assistant_message)
            
            # 添加到日志
            self.logger.log("assistant", self.last_response, agent=self.name)
            logger.info(f"系统响应: {self.last_response}")
            
            # 添加到记忆系统
            if add_to_memory:
                try:
                    memory_id = await self.memory.add(
                        content=user_input + " -> " + self.last_response,
                        metadata=memory_metadata or {"type": "file_save"}
                    )
                    logger.info(f"会话已添加到记忆系统，ID: {memory_id}")
                except Exception as e:
                    logger.error(f"记忆保存失败: {str(e)}")
            
            return self.last_response
        
        # 检查是否是 AI 对话请求
        if self._is_ai_request(user_input):
            logger.info("检测到AI对话请求")
            try:
                # 提取 AI 对话内容
                ai_content = self._extract_ai_content(user_input)
                logger.info(f"提取的AI对话内容: {ai_content}")
                
                # 使用提供商生成回复
                provider_response = await self.provider.generate(
                    system_prompt="你是一个有用的AI助手。",
                    user_input=ai_content
                )
                
                # 记录原始响应
                logger.info(f"AI提供商原始响应: {provider_response}")
                
                # 提取回复内容
                if isinstance(provider_response, dict):
                    if "response" in provider_response:
                        self.last_response = provider_response["response"]
                    elif "content" in provider_response:
                        self.last_response = provider_response["content"]
                    else:
                        logger.warning(f"agent.process返回格式异常: {provider_response}")
                        self.last_response = "处理请求时出错，响应格式不正确"
                else:
                    self.last_response = str(provider_response)
            except Exception as e:
                self.last_response = f"向 AI 模型请求时出错: {str(e)}"
                logger.error(f"向 AI 模型请求时出错: {str(e)}")
            
            # 添加助手消息到历史
            assistant_message = MCPMessage("assistant", self.last_response)
            self.conversation_history.append(assistant_message)
            
            # 添加到日志
            self.logger.log("assistant", self.last_response, agent=self.name)
            logger.info(f"系统响应: {self.last_response}")
            
            # 添加到记忆系统
            if add_to_memory:
                try:
                    memory_id = await self.memory.add(
                        content=user_input + " -> " + self.last_response,
                        metadata=memory_metadata or {"type": "ai_dialog"}
                    )
                    logger.info(f"会话已添加到记忆系统，ID: {memory_id}")
                except Exception as e:
                    logger.error(f"记忆保存失败: {str(e)}")
            
            return self.last_response
        
        # 正常处理用户输入
        try:
            logger.info("使用MCP Agent处理请求")
            
            # 记录处理开始
            start_time = time.time()
            
            # 使用MCPAgent处理用户输入
            result = await self.agent.process(user_input)
            
            # 记录处理时间
            processing_time = time.time() - start_time
            logger.info(f"MCP处理耗时: {processing_time:.2f}秒")
            
            # 存储可能生成的文件路径
            generated_files = []
            
            # 记录处理前的文件列表和修改时间
            files_before = {}
            current_dir = os.getcwd()
            for file in os.listdir(current_dir):
                file_path = os.path.join(current_dir, file)
                if os.path.isfile(file_path):
                    files_before[file_path] = os.path.getmtime(file_path)
            
            # 记录工具使用情况
            if isinstance(result, dict) and "tools" in result:
                tool_info = result["tools"]
                logger.info(f"使用的工具: {tool_info}")
                
                # 添加工具使用记录到对话历史
                for tool in tool_info:
                    tool_name = tool.get('name', '未知工具')
                    tool_args = tool.get('args', {})
                    tool_result = tool.get('result', '无结果')
                    
                    # 添加到对话历史
                    tool_message = MCPMessage(
                        "tool", 
                        f"工具名称: {tool_name}\n参数: {tool_args}\n结果: {tool_result}", 
                        name=tool_name
                    )
                    self.conversation_history.append(tool_message)
                    
                    # 添加到日志
                    self.logger.log_system_event(
                        f"工具使用: {tool_name}",
                        f"参数: {tool_args}\n结果: {tool_result}"
                    )
                    
                    # 自动检测并保存生成的代码文件 - 支持多种可能的工具名称格式
                    # 在实际API中，不同的LLM可能会使用不同的工具名称格式
                    write_file_tools = ['write_to_file', 'write_file', 'writeToFile', 'WriteFile', 'writeFile', 'write-file', 'write-to-file']
                    if any(name.lower() in tool_name.lower() for name in write_file_tools):
                        logger.info(f"检测到文件写入工具: {tool_name}")
                        # 尝试不同的参数名称格式
                        file_path = None
                        for param_name in ['path', 'file_path', 'filepath', 'file', 'filename', 'target_file', 'targetFile', 'TargetFile']:
                            if isinstance(tool_args, dict) and param_name in tool_args:
                                file_path = tool_args[param_name]
                                break
                        
                        if file_path:
                            logger.info(f"从工具参数中提取的文件路径: {file_path}")
                            # 保存文件路径用于稍后处理
                            generated_files.append(file_path)
                            # 添加到待保存文件列表
                            if file_path not in self.pending_files_to_save:
                                self.pending_files_to_save.append(file_path)
                            
                            # 立即保存文件到正确的目录结构
                            await self._auto_save_generated_file(file_path)
            
            # 记录终端输出
            if isinstance(result, dict) and "terminal_output" in result:
                terminal_output = result["terminal_output"]
                logger.info(f"终端输出: {terminal_output}")
                
                # 添加终端输出到对话历史
                terminal_message = MCPMessage(
                    "system", 
                    f"终端输出:\n```\n{terminal_output}\n```"
                )
                self.conversation_history.append(terminal_message)
                
                # 添加到日志
                self.logger.log_system_event(
                    "终端输出",
                    f"```\n{terminal_output}\n```"
                )
            
            # 如果返回值是字典，提取response字段
            if isinstance(result, dict):
                if "response" in result:
                    response = result["response"]
                elif "content" in result:
                    response = result["content"]
                else:
                    logger.warning(f"agent.process返回格式异常: {result}")
                    response = "处理请求时出错，响应格式不正确"
            else:
                response = str(result)
                
            logger.info(f"处理结果: {response}")
            
            # 记录响应
            self.last_response = response
            
            # 检测生成或修改的文件并保存
            files_after = {}
            for file in os.listdir(current_dir):
                file_path = os.path.join(current_dir, file)
                if os.path.isfile(file_path):
                    files_after[file_path] = os.path.getmtime(file_path)
            
            # 查找新增或修改的文件
            new_or_modified_files = []
            for file_path, mod_time in files_after.items():
                if file_path not in files_before or mod_time > files_before.get(file_path, 0):
                    new_or_modified_files.append(file_path)
                    logger.info(f"检测到新增或修改的文件: {file_path}")
            
            # 保存新增或修改的文件
            saved_files = []
            for file_path in new_or_modified_files:
                saved_path = await self._auto_save_generated_file(file_path)
                if saved_path:
                    saved_files.append(saved_path)
            
            # 从响应中提取代码块并保存
            extracted_files = await self._auto_detect_and_save_files_from_response(response)
            saved_files.extend([f for f in extracted_files if f])
            
            # 如果有保存的文件，将保存信息添加到响应
            if saved_files:
                file_info = "\n\n已自动保存以下文件："
                for file_path in saved_files:
                    rel_path = os.path.relpath(file_path, self.project_root)
                    file_info += f"\n- {rel_path}"
                
                # 修改响应，添加文件保存信息
                self.last_response += file_info
                
                # 记录到日志
                logger.info(f"已自动保存 {len(saved_files)} 个文件")
            
            # 移动项目目录下的文件到结果目录
            moved_files = await self._move_files_to_results_directory()
            if moved_files:
                moved_info = "\n\n已将项目目录下的文件移动到结果目录："
                for file_path in moved_files:
                    rel_path = os.path.relpath(file_path, self.project_root)
                    moved_info += f"\n- {rel_path}"
                
                # 修改响应，添加文件移动信息
                self.last_response += moved_info
                
                # 更新最后一个助手消息内容
                if len(self.conversation_history) > 0 and self.conversation_history[-1].type == "assistant":
                    self.conversation_history[-1].content = self.last_response
                
                # 记录到日志
                logger.info(f"已移动 {len(moved_files)} 个文件")
            
            # 添加助手消息到历史
            assistant_message = MCPMessage("assistant", self.last_response)
            self.conversation_history.append(assistant_message)
            
            # 添加到日志
            self.logger.log("assistant", self.last_response, agent=self.name)
            logger.info(f"系统响应: {self.last_response}")
            
            # 添加到记忆系统
            if add_to_memory:
                try:
                    # 保存对话历史到元数据
                    if not memory_metadata:
                        memory_metadata = {}
                    
                    # 将对话历史序列化为可保存的格式
                    conversation_data = []
                    for msg in self.conversation_history:
                        msg_data = {
                            'role': msg.role,  # 使用role字段
                            'content': msg.content
                        }
                        if msg.name:
                            msg_data['name'] = msg.name
                        conversation_data.append(msg_data)
                    
                    # 添加对话历史到元数据
                    memory_metadata['conversation_history'] = conversation_data
                    
                    # 保存到记忆系统
                    memory_id = await self.memory.add(
                        content=user_input + " -> " + response,
                        metadata=memory_metadata
                    )
                    logger.info(f"会话已添加到记忆系统，ID: {memory_id}")
                except Exception as e:
                    logger.error(f"记忆保存失败: {str(e)}")
            
            # 自动保存检测到的文件，立即执行，不等待时间间隔
            if self.auto_save_enabled and self.pending_files_to_save:
                await self._perform_auto_save()
        
            return response
            
        except Exception as e:
            error_msg = f"处理请求时出错: {str(e)}"
            logger.error(error_msg)
            import traceback
            traceback_str = traceback.format_exc()
            logger.error(f"异常堆栈: {traceback_str}")
            
            # 添加错误信息到对话历史
            error_message = MCPMessage(
                "system", 
                f"错误信息:\n```\n{traceback_str}\n```"
            )
            self.conversation_history.append(error_message)
            
            # 记录到日志
            self.logger.log_system_event(
                "错误",
                f"错误信息:\n```\n{traceback_str}\n```"
            )
            
            self.last_response = error_msg
            return error_msg
    
    def _is_save_request(self, user_input: str) -> bool:
        """检查是否是保存对话请求
        
        Args:
            user_input: 用户输入
            
        Returns:
            是否是保存请求
        """
        # 检查是否包含保存关键词，但不匹配-save命令
        if "-save" in user_input:
            return False
        
        return "保存" in user_input and ("对话" in user_input or "聊天" in user_input or "内容" in user_input)
    
    def _save_conversation(self) -> str:
        """保存当前对话到文件
        
        Returns:
            文件保存路径
        """
        try:
            # 获取格式化后的对话历史
            content = self._format_conversation_history()
            
            # 准备文件保存路径
            # 按照新要求的目录结构: /results/时间/对话ID/
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            
            # 使用会话ID作为目录名
            conversation_id_short = self.conversation_id[:8]
            
            # 创建时间目录
            results_dir = os.path.join(self.project_root, "results")
            os.makedirs(results_dir, exist_ok=True)
            logger.info(f"创建结果目录: {results_dir}")
            
            time_dir = os.path.join(results_dir, date_str)
            os.makedirs(time_dir, exist_ok=True)
            logger.info(f"创建日期目录: {time_dir}")
            
            # 创建对话ID目录
            conversation_dir = os.path.join(time_dir, conversation_id_short)
            os.makedirs(conversation_dir, exist_ok=True)
            logger.info(f"创建对话ID目录: {conversation_dir}")
            
            # 创建文件名 
            file_name = f"对话记录_{time_str}.md"
            
            # 完整文件路径
            file_path = os.path.join(conversation_dir, file_name)
            
            # 使用文件管理器保存
            from utils.file_manager import FileManager
            file_manager = FileManager()
            result = file_manager.save_file_to_path(content, file_path)
            
            # 添加系统消息到对话历史
            system_message = MCPMessage(
                "system", 
                f"已保存对话记录到: {os.path.relpath(result, self.project_root)}"
            )
            self.conversation_history.append(system_message)
            
            # 记录到日志
            self.logger.log_system_event("对话保存", f"已保存对话记录到: {result}")
            
            return result
            
        except Exception as e:
            error_msg = f"保存对话时出错: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            
            # 添加错误信息到对话历史
            error_message = MCPMessage("system", error_msg)
            self.conversation_history.append(error_message)
            
            return error_msg
    
    def _is_ai_request(self, user_input: str) -> bool:
        """检查是否是 AI 对话请求
        
        Args:
            user_input: 用户输入
            
        Returns:
            是否是 AI 对话请求
        """
        ai_providers = ["openai", "gpt", "azure", "anthropic", "claude", "gemini", "baidu", "文心", "智谱", "glm"]
        return any(provider in user_input.lower() for provider in ai_providers) and ("问" in user_input or "询问" in user_input or "请教" in user_input)
    
    def _extract_ai_content(self, user_input: str) -> str:
        """提取 AI 对话内容
        
        Args:
            user_input: 用户输入
            
        Returns:
            AI 对话内容
        """
        import re
        match = re.search(r'问\s*([^：]+)', user_input)
        if match:
            return match.group(1)
        else:
            return user_input
    
    def _format_conversation_history(self) -> str:
        """格式化对话历史为易读的文本
        
        Returns:
            格式化后的对话历史文本
        """
        # 添加对话ID和时间戳作为标题
        now = datetime.datetime.now()
        time_str = now.strftime("%Y-%m-%d %H:%M:%S")
        
        # 获取模型名称（保护缺失的情况）
        model_name = getattr(self, 'model', '未知模型')
        
        # 添加会话头部信息
        lines = [
            f"# 对话记录 - {time_str}",
            f"会话ID: {self.conversation_id}",
            f"助手名称: {self.name}",
            f"模型: {model_name}",
            "",
            "## 对话内容",
            ""
        ]
        
        # 添加每条消息
        for msg in self.conversation_history:
            # 根据消息类型格式化
            if msg.role == "user":  # 使用role字段
                lines.append(f"### 用户")
                lines.append(f"{msg.content}")
                lines.append("")
            elif msg.role == "assistant":  # 使用role字段
                lines.append(f"### 助手")
                lines.append(f"{msg.content}")
                lines.append("")
            elif msg.role == "system":  # 使用role字段
                lines.append(f"### 系统信息")
                lines.append(f"{msg.content}")
                lines.append("")
            elif msg.role == "tool":  # 使用role字段
                lines.append(f"### 工具使用: {msg.name}")
                lines.append(f"{msg.content}")
                lines.append("")
        
        # 连接所有行
        return "\n".join(lines)
    
    async def save_conversation(self, file_path: str) -> str:
        """保存当前对话到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            操作结果
        """
        content = self._format_conversation_history()
        
        try:
            # 尝试直接调用工具函数
            from tools.mcp_file_tools import FileManager
            file_manager = FileManager()
            result = await file_manager.save_file(file_path=file_path, content=content)
            return result
        except ImportError:
            return "错误：无法加载文件管理工具"
        except Exception as e:
            return f"保存对话时出错: {str(e)}"
    
    async def save_last_response(self, file_path: str) -> str:
        """保存最后一条回复到文件
        
        Args:
            file_path: 文件路径
            
        Returns:
            操作结果
        """
        if not self.last_response:
            return "没有可保存的回复"
        
        try:
            # 尝试直接调用工具函数
            from tools.mcp_file_tools import FileManager
            file_manager = FileManager()
            result = await file_manager.save_file(file_path=file_path, content=self.last_response)
            return result
        except ImportError:
            return "错误：无法加载文件管理工具"
        except Exception as e:
            return f"保存回复时出错: {str(e)}"
    
    async def get_ai_response(self, prompt: str, provider: str = "openai") -> str:
        """获取其他 AI 模型的回答
        
        Args:
            prompt: 提示
            provider: AI 提供商
            
        Returns:
            AI 回答
        """
        try:
            # 尝试直接调用 AI 工具
            from tools.mcp_ai_tools import AIProviderManager
            ai_manager = AIProviderManager()
            result = await ai_manager.ask_ai(prompt=prompt, provider=provider)
            return result
        except Exception as e:
            return f"获取 AI 回答时出错: {str(e)}"
    
    async def compare_ai_responses(self, prompt: str, providers: List[str] = ["openai", "anthropic"]) -> Dict:
        """比较多个 AI 模型的回答
        
        Args:
            prompt: 提示
            providers: AI 提供商列表
            
        Returns:
            各 AI 模型的回答比较
        """
        try:
            # 使用 AI 比较工具
            result = await self.agent.execute_tool(
                "compare_ai_responses",
                {"prompt": prompt, "providers": providers}
            )
            return result
        except Exception as e:
            return {"error": f"比较 AI 回答时出错: {str(e)}"}
    
    async def clear_conversation(self) -> None:
        """清空当前对话历史"""
        self.conversation_history = []
        self.last_response = None
    
    def get_conversation_history(self) -> List[Dict]:
        """获取当前对话历史
        
        Returns:
            对话历史
        """
        return self.conversation_history
    
    async def _restore_from_memory(self, memory_id: str) -> str:
        """从记忆ID恢复对话记录
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            恢复结果信息
        """
        try:
            logger.info(f"正在从记忆ID恢复对话: {memory_id}")
            
            # 验证记忆ID格式
            if not memory_id or not isinstance(memory_id, str):
                error_msg = "无效的记忆ID格式"
                logger.error(error_msg)
                return f"恢复对话失败: {error_msg}"
            
            # 尝试获取记忆内容
            memory_item = await self.memory.get(memory_id)
            
            if not memory_item:
                error_msg = f"找不到记忆ID: {memory_id}"
                logger.error(error_msg)
                return f"恢复对话失败: {error_msg}"
            
            # 从记忆中提取对话内容
            memory_content = memory_item.get('content', '')
            memory_metadata = memory_item.get('metadata', {})
            
            # 记录到日志
            logger.info(f"已找到记忆: {memory_id}")
            logger.info(f"记忆元数据: {memory_metadata}")
            
            # 如果记忆中包含完整对话历史
            if 'conversation_history' in memory_metadata:
                conversation_data = memory_metadata['conversation_history']
                try:
                    # 恢复对话历史
                    if isinstance(conversation_data, str):
                        # 如果是JSON字符串，解析它
                        import json
                        conversation_data = json.loads(conversation_data)
                    
                    # 转换为MCPMessage对象
                    self.conversation_history = []
                    for msg_data in conversation_data:
                        msg_type = msg_data.get('role', 'system')  # 使用role字段
                        msg_content = msg_data.get('content', '')
                        msg_name = msg_data.get('name', None)
                        msg = MCPMessage(msg_type, msg_content, name=msg_name)
                        self.conversation_history.append(msg)
                    
                    logger.info(f"已恢复{len(self.conversation_history)}条对话消息")
                    
                    # 构建恢复摘要
                    summary = f"已从记忆 {memory_id} 恢复对话，共{len(self.conversation_history)}条消息。"
                    
                    # 添加恢复信息到对话历史
                    restore_msg = MCPMessage("system", f"已恢复记忆ID: {memory_id}的对话")
                    self.conversation_history.append(restore_msg)
                    
                    # 记录到日志
                    self.logger.log_system_event("对话恢复", f"已从记忆ID {memory_id} 恢复对话历史")
                    
                    return summary
                except Exception as e:
                    logger.error(f"解析对话历史数据时出错: {str(e)}")
                    import traceback
                    logger.error(traceback.format_exc())
                    return f"恢复对话历史时出错: {str(e)}"
            
            # 如果记忆中没有完整对话历史，只有简单内容
            # 添加系统消息说明
            system_msg = MCPMessage("system", f"已尝试从记忆ID {memory_id} 恢复，但记忆中没有完整对话历史。\n记忆内容: {memory_content}")
            self.conversation_history.append(system_msg)
            
            # 记录到日志
            self.logger.log_system_event("对话恢复部分成功", f"记忆ID {memory_id} 中没有完整对话历史")
            
            return f"已尝试从记忆ID {memory_id} 恢复，但只找到部分内容。\n记忆内容: {memory_content[:100]}..."
            
        except Exception as e:
            error_msg = f"从记忆恢复对话时出错: {str(e)}"
            logger.error(error_msg)
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            
            # 添加错误信息到对话历史
            error_message = MCPMessage("system", f"恢复记忆出错: {str(e)}")
            self.conversation_history.append(error_message)
            
            # 记录到日志
            self.logger.log_system_event("恢复记忆错误", error_msg)
            
            return f"恢复对话失败: {str(e)}"

    async def _move_files_to_results_directory(self) -> List[str]:
        """将项目目录下的文件移动到结果目录中
        
        将项目目录中的文件移动到 /results/日期/年份日期+时间_对话id后4位/ 结构下
        仅移动项目根目录下的文件，不处理子目录
        
        Returns:
            移动的文件路径列表
        """
        try:
            logger.info("开始移动项目目录下的文件到结果目录")
            
            # 准备保存目录结构: /results/日期/年份日期+时间_对话ID后4位/
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            year_str = now.strftime("%Y")
            
            # 使用对话ID的后4位作为目录名的一部分
            conversation_id_suffix = self.conversation_id[-4:] if len(self.conversation_id) >= 4 else self.conversation_id
            dir_name = f"{year_str}{date_str}+{time_str}_{conversation_id_suffix}"
            
            # 创建结果目录 (在项目根目录下)
            results_dir = os.path.join(self.project_root, "results")
            os.makedirs(results_dir, exist_ok=True)
            logger.info(f"创建结果目录: {results_dir}")
            
            time_dir = os.path.join(results_dir, date_str)
            os.makedirs(time_dir, exist_ok=True)
            logger.info(f"创建日期目录: {time_dir}")
            
            # 创建对话ID目录
            conversation_dir = os.path.join(time_dir, dir_name)
            os.makedirs(conversation_dir, exist_ok=True)
            logger.info(f"创建时间及对话ID目录: {conversation_dir}")
            
            # 读取忽略文件列表
            ignore_files = []
            ignored_files_path = os.path.join(self.project_root, "data", "ignored_files.txt")
            if os.path.exists(ignored_files_path):
                try:
                    with open(ignored_files_path, 'r', encoding='utf-8') as f:
                        for line in f:
                            line = line.strip()
                            # 跳过空行和注释
                            if not line or line.startswith('#'):
                                continue
                            ignore_files.append(line)
                    logger.info(f"从配置文件加载了 {len(ignore_files)} 个忽略文件模式")
                except Exception as e:
                    logger.error(f"读取忽略文件列表时出错: {str(e)}")
                    # 使用默认值
                    ignore_files = ['LICENSE', 'README', 'requirements.txt', 'setup.py', 'config.json', '.env']
            else:
                # 如果配置文件不存在，使用默认值
                ignore_files = ['LICENSE', 'README', 'requirements.txt', 'setup.py', 'config.json', '.env']
                logger.warning(f"忽略文件配置不存在: {ignored_files_path}，使用默认值")
            
            # 获取项目根目录中的文件列表，并筛选出非系统文件
            moved_files = []
            ignore_dirs = ['.git', '__pycache__', 'logs', 'results', 'utils', 'examples', 'data']
            ignore_extensions = ['.py', '.md', '.gitignore', '.txt']
            
            for item in os.listdir(self.project_root):
                item_path = os.path.join(self.project_root, item)
                
                # 只处理文件，忽略目录
                if os.path.isdir(item_path):
                    continue
                    
                # 忽略指定的目录中的文件
                if any(item.startswith(prefix) for prefix in ignore_dirs):
                    continue
                    
                # 忽略指定扩展名的文件
                if any(item.endswith(ext) for ext in ignore_extensions):
                    continue
                
                # 检查是否应该忽略此文件
                should_ignore = False
                for pattern in ignore_files:
                    # 简单的通配符匹配
                    if pattern.endswith('*'):
                        if item.startswith(pattern[:-1]):
                            should_ignore = True
                            break
                    elif pattern.startswith('*'):
                        if item.endswith(pattern[1:]):
                            should_ignore = True
                            break
                    elif pattern == item:
                        should_ignore = True
                        break
                
                if should_ignore:
                    logger.info(f"忽略文件: {item} (匹配忽略模式)")
                    continue
                    
                # 移动文件到结果目录
                dest_path = os.path.join(conversation_dir, item)
                
                try:
                    # 复制文件到目标位置
                    shutil.copy2(item_path, dest_path)
                    logger.info(f"已复制文件: {item_path} -> {dest_path}")
                    
                    # 删除原文件
                    os.remove(item_path)
                    logger.info(f"已删除原文件: {item_path}")
                    
                    moved_files.append(dest_path)
                except Exception as e:
                    logger.error(f"移动文件时出错: {item_path} -> {dest_path}, 错误: {str(e)}")
            
            # 生成移动结果消息
            if moved_files:
                moved_files_rel = [os.path.relpath(f, self.project_root) for f in moved_files]
                message = f"已移动 {len(moved_files)} 个文件到 {os.path.relpath(conversation_dir, self.project_root)}:\n"
                for idx, file_path in enumerate(moved_files_rel):
                    message += f"{idx+1}. {file_path}\n"
                
                # 添加系统消息到对话历史
                system_message = MCPMessage("system", message)
                self.conversation_history.append(system_message)
                
                # 记录到日志
                self.logger.log_system_event("文件移动", message)
                
                return moved_files
            else:
                logger.info("没有找到需要移动的文件")
                return []
                
        except Exception as e:
            logger.error(f"移动文件到结果目录时出错: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return []
            
    async def _auto_save_generated_file(self, file_path: str) -> Optional[str]:
        """自动保存生成的文件到存档目录
        
        Args:
            file_path: 文件路径
            
        Returns:
            保存的文件路径，如果失败则返回None
        """
        if not file_path or not os.path.exists(file_path):
            logger.warning(f"文件不存在，无法保存: {file_path}")
            return None
            
        try:
            # 准备保存目录结构: /results/日期/年份日期+时间_对话ID后4位/
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            year_str = now.strftime("%Y")
            
            # 使用对话ID的后4位作为目录名的一部分
            conversation_id_suffix = self.conversation_id[-4:] if len(self.conversation_id) >= 4 else self.conversation_id
            dir_name = f"{year_str}{date_str}+{time_str}_{conversation_id_suffix}"
            
            # 创建结果目录 (在项目根目录下)
            results_dir = os.path.join(self.project_root, "results")
            os.makedirs(results_dir, exist_ok=True)
            logger.info(f"创建结果目录: {results_dir}")
            
            time_dir = os.path.join(results_dir, date_str)
            os.makedirs(time_dir, exist_ok=True)
            logger.info(f"创建日期目录: {time_dir}")
            
            # 创建对话ID目录
            conversation_dir = os.path.join(time_dir, dir_name)
            os.makedirs(conversation_dir, exist_ok=True)
            logger.info(f"创建年份日期时间对话ID目录: {conversation_dir}")
            
            # 创建文件管理器
            from utils.file_manager import FileManager
            file_manager = FileManager()
            
            # 获取文件名
            file_name = os.path.basename(file_path)
            dest_file = os.path.join(conversation_dir, file_name)
            
            # 复制文件到目标位置
            dest_file = file_manager.copy_file_to_path(file_path, dest_file)
            logger.info(f"已自动保存文件: {file_path} -> {dest_file}")
            
            # 记录已保存的文件
            self.auto_saved_files[file_path] = dest_file
            
            # 记录到日志
            self.logger.log_system_event("文件保存", f"已自动保存文件: {file_path} -> {dest_file}")
            
            return dest_file
            
        except Exception as e:
            logger.error(f"自动保存文件时出错: {file_path}, {str(e)}")
            return None
            
    async def _auto_detect_and_save_files_from_response(self, response: str) -> List[str]:
        """自动检测和保存从响应中提取的代码文件
        
        Args:
            response: AI响应内容
            
        Returns:
            保存的文件路径列表
        """
        try:
            # 从响应中提取代码块和文件名
            code_blocks = []
            in_code_block = False
            current_block = []
            current_lang = ""
            
            # 提取可能的文件名(引号中包含点和字母的内容)
            file_names = re.findall(r'[\'"`]([a-zA-Z0-9_\-]+\.[a-zA-Z0-9]+)[\'"`]', response)
            logger.info(f"从引号中提取的文件名: {file_names}")
            
            # 提取代码块
            lines = response.split('\n')
            for line in lines:
                if line.strip().startswith('```'):
                    if in_code_block:
                        # 结束代码块
                        in_code_block = False
                        code_blocks.append({
                            'lang': current_lang,
                            'code': '\n'.join(current_block)
                        })
                        current_block = []
                        current_lang = ""
                    else:
                        # 开始代码块
                        in_code_block = True
                        # 尝试提取语言
                        lang_match = re.match(r'```(\w+)', line)
                        if lang_match:
                            current_lang = lang_match.group(1)
                elif in_code_block:
                    current_block.append(line)
            
            # 如果有未关闭的代码块，添加到列表
            if in_code_block and current_block:
                code_blocks.append({
                    'lang': current_lang,
                    'code': '\n'.join(current_block)
                })
            
            # 保存提取的代码块
            saved_files = []
            
            # 准备保存目录结构: /results/日期/年份日期+时间_对话ID后4位/
            now = datetime.datetime.now()
            date_str = now.strftime("%Y%m%d")
            time_str = now.strftime("%H%M%S")
            year_str = now.strftime("%Y")
            
            # 使用对话ID的后4位作为目录名的一部分
            conversation_id_suffix = self.conversation_id[-4:] if len(self.conversation_id) >= 4 else self.conversation_id
            dir_name = f"{year_str}{date_str}+{time_str}_{conversation_id_suffix}"
            
            # 创建结果目录 (在项目根目录下)
            results_dir = os.path.join(self.project_root, "results")
            os.makedirs(results_dir, exist_ok=True)
            logger.info(f"创建结果目录: {results_dir}")
            
            time_dir = os.path.join(results_dir, date_str)
            os.makedirs(time_dir, exist_ok=True)
            logger.info(f"创建日期目录: {time_dir}")
            
            # 创建对话ID目录
            conversation_dir = os.path.join(time_dir, dir_name)
            os.makedirs(conversation_dir, exist_ok=True)
            logger.info(f"创建年份日期时间对话ID目录: {conversation_dir}")
            
            # 创建文件管理器
            from utils.file_manager import FileManager
            file_manager = FileManager()
            
            # 保存代码块
            for i, block in enumerate(code_blocks):
                lang = block['lang'].lower()
                code = block['code']
                
                # 根据语言确定文件扩展名
                ext = '.txt'  # 默认
                if lang in ['python', 'py']:
                    ext = '.py'
                elif lang in ['javascript', 'js']:
                    ext = '.js'
                elif lang in ['html']:
                    ext = '.html'
                elif lang in ['css']:
                    ext = '.css'
                elif lang in ['json']:
                    ext = '.json'
                elif lang in ['markdown', 'md']:
                    ext = '.md'
                
                # 尝试从文件名列表匹配扩展名
                matched_name = None
                for name in file_names:
                    if name.endswith(ext):
                        matched_name = name
                        # 从列表中移除已使用的文件名
                        file_names.remove(name)
                        break
                
                # 如果没有匹配到，生成一个默认名
                if not matched_name:
                    matched_name = f"代码块_{i+1}{ext}"
                
                # 保存文件
                file_path = os.path.join(conversation_dir, matched_name)
                saved_file = file_manager.save_file_to_path(code, file_path)
                saved_files.append(saved_file)
                logger.info(f"已保存代码块到: {saved_file}")
            
            # 系统消息
            if saved_files:
                saved_files_rel = [os.path.relpath(f, self.project_root) for f in saved_files]
                message = f"已自动保存 {len(saved_files)} 个代码文件到 {os.path.relpath(conversation_dir, self.project_root)}:\n"
                for idx, file_path in enumerate(saved_files_rel):
                    message += f"{idx+1}. {file_path}\n"
                
                # 添加系统消息到对话历史
                system_message = MCPMessage("system", message)
                self.conversation_history.append(system_message)
                
                # 记录到日志
                self.logger.log_system_event("代码文件保存", message)
            
            return saved_files
            
        except Exception as e:
            logger.error(f"自动检测和保存文件时出错: {str(e)}")
            import traceback
            logger.error(f"异常堆栈: {traceback.format_exc()}")
            return []
            
    async def _initialize(self):
        """异步初始化方法，完成各种组件的初始化"""
        # 设置日志文件
        os.makedirs("logs", exist_ok=True)
        self.log_file = os.path.join("logs", f"mcp_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        
        # 初始化日志记录器
        self._setup_logger()
        
        # 保存当前的对话ID到文件中
        self._save_conversation_id()
        
        global logger
        logger = logging.getLogger("MCP助手")
        logger.setLevel(logging.INFO)
    
    def _save_conversation_id(self):
        """保存当前对话ID到文件，用于持久化"""
        try:
            # 确保目录存在
            os.makedirs(os.path.dirname(self.conversation_id_file), exist_ok=True)
            
            # 写入对话ID
            with open(self.conversation_id_file, 'w', encoding='utf-8') as f:
                f.write(self.conversation_id)
                
            logger.info(f"已保存对话ID: {self.conversation_id}")
        except Exception as e:
            logger.error(f"保存对话ID时出错: {str(e)}")
            
    def _load_last_conversation_id(self) -> Optional[str]:
        """尝试加载上次的对话ID，用于对话连续性"""
        try:
            if os.path.exists(self.conversation_id_file):
                with open(self.conversation_id_file, 'r', encoding='utf-8') as f:
                    conversation_id = f.read().strip()
                    if conversation_id:
                        logger.info(f"已加载上次的对话ID: {conversation_id}")
                        return conversation_id
        except Exception as e:
            if logger:
                logger.error(f"加载对话ID时出错: {str(e)}")
            else:
                print(f"加载对话ID时出错: {str(e)}")
        
        return None
    
    async def _perform_auto_save(self) -> None:
        """执行自动保存操作，保存所有待保存的文件"""
        if not self.auto_save_enabled or not self.pending_files_to_save:
            return
            
        logger.info(f"执行自动保存，待保存文件数: {len(self.pending_files_to_save)}")
        
        # 复制一份列表防止迭代过程中修改
        files_to_save = self.pending_files_to_save.copy()
        saved_count = 0
        
        for file_path in files_to_save:
            if await self._auto_save_generated_file(file_path):
                saved_count += 1
        
        # 记录保存结果
        if saved_count > 0:
            logger.info(f"自动保存完成，成功保存了 {saved_count} 个文件")
            # 添加系统消息到对话历史
            system_message = MCPMessage(
                "system", 
                f"自动保存已完成，成功保存了 {saved_count} 个文件"
            )
            self.conversation_history.append(system_message)
            
            # 添加到日志
            self.logger.log_system_event("文件自动保存完成", f"成功保存了 {saved_count} 个文件")
            
    def _configure_auto_save(self, setting: str) -> str:
        """配置自动保存设置
        
        Args:
            setting: 自动保存设置，可以是"on"、"off"或"interval 300"等
            
        Returns:
            设置结果信息
        """
        if setting == "on":
            self.auto_save_enabled = True
            logger.info("自动保存功能已启用")
            return "自动保存功能已启用"
        elif setting == "off":
            self.auto_save_enabled = False
            logger.info("自动保存功能已禁用")
            return "自动保存功能已禁用"
        elif setting.startswith("interval"):
            try:
                interval = int(setting.split()[1])
                if interval < 10:
                    return "自动保存间隔不能小于10秒"
                self.auto_save_interval = interval
                logger.info(f"自动保存间隔已设置为: {interval}秒")
                return f"自动保存间隔已设置为: {interval}秒"
            except (IndexError, ValueError):
                return "自动保存间隔设置错误，格式应为: -autosave interval 秒数"
        else:
            return "自动保存设置错误，可用命令: -autosave on/off/interval 秒数"


class MCPMessage:
    """MCP通信消息类"""
    
    def __init__(self, type_or_role: str, content: str, name: Optional[str] = None):
        """初始化消息
        
        Args:
            type_or_role: 消息类型或角色 (user/assistant/system/tool)
            content: 消息内容
            name: 可选的名称，当type为tool时表示工具名称
        """
        self.type = type_or_role
        self.role = type_or_role  # 为了兼容性，同时保存为role字段
        self.content = content
        self.name = name
