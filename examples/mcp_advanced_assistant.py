"""
MCP高级助手示例
展示如何使用MCP的高级功能，包括记忆系统、多模态处理、反馈和插件
"""
import os
import sys
import json
import asyncio
import argparse
from typing import Dict, List, Any, Optional, Union
from pathlib import Path

# 添加项目根目录到路径
ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(ROOT_DIR)

from core.mcp import MCPMessage, MCPProtocol, MCPTool, mcp_tool
from core.mcp_agent import MCPAgent
from core.mcp_system import MCPSystem
from core.mcp_memory import MCPMemoryManager
from core.mcp_multimodal import MCPMultimodalProcessor
from core.mcp_feedback import MCPFeedback, SelfEvaluator
from core.mcp_plugins import PluginManager, TranslationPlugin

class MCPAdvancedAssistant:
    """
    MCP高级助手
    展示MCP集成的高级功能
    """
    
    def __init__(
        self, 
        llm_provider: str = "openai", 
        model: str = None,
        memory_db: str = None,
        plugins_enabled: bool = True,
        multimodal_enabled: bool = True,
        feedback_enabled: bool = True,
        agent_name: str = "MCP高级助手"
    ):
        """初始化高级助手
        
        Args:
            llm_provider: LLM服务提供商
            model: 使用的模型
            memory_db: 记忆数据库路径
            plugins_enabled: 是否启用插件
            multimodal_enabled: 是否启用多模态
            feedback_enabled: 是否启用反馈
            agent_name: 智能体名称
        """
        self.agent_name = agent_name
        self.plugins_enabled = plugins_enabled
        self.multimodal_enabled = multimodal_enabled
        self.feedback_enabled = feedback_enabled
        
        # 初始化LLM服务
        self.llm_service = self._init_llm_service(llm_provider, model)
        
        # 设置基本工具
        self.tools = [
            self.echo_tool,
            self.get_time_tool,
            self.calculate_tool
        ]
        
        # 初始化记忆系统
        self.memory_db = memory_db or os.path.join(ROOT_DIR, "data", "memory", f"{agent_name.lower().replace(' ', '_')}.db")
        os.makedirs(os.path.dirname(self.memory_db), exist_ok=True)
        self.memory_manager = MCPMemoryManager(agent_name=agent_name, db_path=self.memory_db)
        
        # 初始化多模态处理器
        if self.multimodal_enabled:
            self.multimodal = MCPMultimodalProcessor()
            self.tools.append(self.process_image_tool)
        
        # 初始化反馈系统
        if self.feedback_enabled:
            feedback_db = os.path.join(os.path.dirname(self.memory_db), f"{agent_name.lower().replace(' ', '_')}_feedback.db")
            self.feedback_system = MCPFeedback(db_path=feedback_db)
            self.self_evaluator = SelfEvaluator(self.llm_service)
            self.tools.append(self.collect_feedback_tool)
        
        # 初始化智能体
        self.agent = MCPAgent(
            name=agent_name,
            llm_service=self.llm_service,
            tools=self.tools,
            system_prompt=self._get_system_prompt()
        )
        
        # 初始化插件系统
        if self.plugins_enabled:
            self.plugin_manager = PluginManager()
            # 添加插件目录
            plugin_dir = os.path.join(ROOT_DIR, "plugins")
            if os.path.exists(plugin_dir):
                self.plugin_manager.plugin_dirs.append(plugin_dir)
                self.plugin_manager.discover_plugins()
            
            # 配置插件
            plugin_config = {
                "translation_plugin": {
                    "default_target_lang": "zh-CN",
                    "auto_translate": False
                }
            }
            
            # 初始化插件
            initialized_plugins = self.plugin_manager.initialize_plugins(self.agent, plugin_config)
            print(f"已初始化插件: {', '.join(initialized_plugins)}")
    
    def _init_llm_service(self, provider: str, model: str = None):
        """初始化LLM服务
        
        Args:
            provider: 服务提供商
            model: 模型名称
            
        Returns:
            LLM服务对象
        """
        if provider.lower() == "openai":
            from llm.openai_llm import OpenAILLM
            model = model or "gpt-4o"
            return OpenAILLM(model=model)
        elif provider.lower() == "mock":
            # 使用模拟LLM进行测试
            from testing.mock_llm import MockLLM
            return MockLLM()
        else:
            raise ValueError(f"不支持的LLM提供商: {provider}")
    
    def _get_system_prompt(self) -> str:
        """获取系统提示
        
        Returns:
            系统提示文本
        """
        return f"""你是{self.agent_name}，一个功能强大的AI助手。
你拥有以下高级功能:
1. 记忆系统: 可以记住用户信息和过去的交互
2. 插件系统: 提供多语言翻译、网络搜索和数据分析能力
3. 反馈系统: 能够学习和改进

请尽可能提供有用、准确和安全的回答。
如果你不确定答案，可以坦诚承认，不要编造信息。
请使用中文回复用户的查询。
"""
    
    @staticmethod
    @mcp_tool(name="echo", description="回显输入内容")
    def echo_tool(text: str) -> str:
        """回显输入的文本
        
        Args:
            text: 输入文本
            
        Returns:
            相同的文本
        """
        return f"Echo: {text}"
    
    @staticmethod
    @mcp_tool(name="get_time", description="获取当前时间")
    def get_time_tool() -> str:
        """获取当前时间
        
        Returns:
            当前时间字符串
        """
        import datetime
        return f"当前时间: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    
    @staticmethod
    @mcp_tool(name="calculate", description="执行数学计算")
    def calculate_tool(expression: str) -> str:
        """执行简单的数学计算
        
        Args:
            expression: 数学表达式
            
        Returns:
            计算结果
        """
        try:
            # 注意：在实际生产环境中应使用更安全的计算方法
            # 这里只用于演示
            result = eval(expression)
            return f"计算结果: {expression} = {result}"
        except Exception as e:
            return f"计算错误: {str(e)}"
    
    @staticmethod
    @mcp_tool(name="process_image", description="处理和分析图像")
    def process_image_tool(image_path: str) -> str:
        """处理和分析图像
        
        Args:
            image_path: 图像文件路径
            
        Returns:
            图像分析结果
        """
        if not os.path.exists(image_path):
            return f"错误：文件 {image_path} 不存在"
        
        try:
            from PIL import Image
            
            # 打开并分析图像
            image = Image.open(image_path)
            width, height = image.size
            format_name = image.format
            mode = image.mode
            
            return (
                f"图像分析结果:\n"
                f"- 文件: {os.path.basename(image_path)}\n"
                f"- 格式: {format_name}\n"
                f"- 尺寸: {width}x{height}\n"
                f"- 模式: {mode}\n"
                f"在实际部署中，这里可以集成更高级的图像分析功能。"
            )
        except Exception as e:
            return f"图像处理错误: {str(e)}"
    
    @staticmethod
    @mcp_tool(name="collect_feedback", description="收集用户反馈")
    def collect_feedback_tool(rating: int, comment: str = "") -> str:
        """收集用户反馈
        
        Args:
            rating: 评分（1-5）
            comment: 评论
            
        Returns:
            确认消息
        """
        if not 1 <= rating <= 5:
            return "错误：评分必须在1到5之间"
        
        return f"感谢您的反馈！您的评分（{rating}/5）和评论已记录。"
    
    async def remember(self, content: str, metadata: Dict = None, long_term: bool = True) -> str:
        """记忆信息
        
        Args:
            content: 记忆内容
            metadata: 元数据
            long_term: 是否为长期记忆
            
        Returns:
            记忆ID
        """
        metadata = metadata or {}
        return await self.memory_manager.remember(content, metadata, long_term)
    
    async def retrieve_memory(self, query: str) -> List[Dict]:
        """检索记忆
        
        Args:
            query: 搜索查询
            
        Returns:
            记忆列表
        """
        return await self.memory_manager.retrieve(query)
    
    async def process_message(self, message: str, message_type: str = "text") -> str:
        """处理用户消息
        
        Args:
            message: 消息内容
            message_type: 消息类型（text/image_path）
            
        Returns:
            处理结果
        """
        # 创建合适的消息格式
        if message_type == "text":
            user_message = MCPMessage.user(message)
        elif message_type == "image_path" and self.multimodal_enabled:
            # 处理图像消息
            if not os.path.exists(message):
                return f"错误：文件 {message} 不存在"
            
            try:
                # 编码图像
                image_data = self.multimodal.encode_image(message)
                
                # 创建多模态消息
                user_message = MCPMessage.multimodal(
                    text="请分析这张图片",
                    image_data=[{"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}]
                )
            except Exception as e:
                return f"图像处理错误: {str(e)}"
        else:
            return f"不支持的消息类型: {message_type}"
        
        # 应用插件拦截器
        if self.plugins_enabled:
            user_message = self.plugin_manager.intercept_message(user_message)
        
        # 处理消息
        try:
            # 检索相关记忆
            memories = await self.memory_manager.retrieve(message)
            if memories:
                # 格式化记忆以添加到上下文
                memory_text = "以下是相关的记忆:\n" + "\n".join(
                    f"- {mem['content']}" for mem in memories[:3]
                )
                # 添加记忆上下文
                self.agent.add_message(MCPMessage.system(memory_text))
            
            # 处理消息
            response = await self.agent.process(user_message)
            
            # 应用插件拦截器
            if self.plugins_enabled:
                response = self.plugin_manager.intercept_response(response)
            
            # 自我评估
            if self.feedback_enabled:
                # 异步执行自我评估，不阻塞响应
                asyncio.create_task(self._evaluate_response(message, response))
            
            # 可能的记忆整合
            if self.memory_manager.should_consolidate():
                asyncio.create_task(self.memory_manager.consolidate())
            
            return response
            
        except Exception as e:
            import traceback
            print(f"处理消息时出错: {str(e)}")
            print(traceback.format_exc())
            return f"抱歉，处理您的消息时出现错误: {str(e)}"
    
    async def _evaluate_response(self, query: str, response: str):
        """评估响应质量
        
        Args:
            query: 用户查询
            response: 助手响应
        """
        try:
            # 执行自我评估
            evaluation = await self.self_evaluator.evaluate_response(query, response)
            
            # 记录评估结果
            await self.feedback_system.record_self_assessment(
                query=query,
                response=response,
                evaluation=evaluation
            )
            
            # 存储重要的评估作为记忆
            if evaluation["overall_score"] < 3:
                memory_content = f"对查询'{query}'的响应质量较低（{evaluation['overall_score']}/5）。改进建议：{evaluation['improvement_suggestions']}"
                await self.memory_manager.remember(
                    content=memory_content,
                    metadata={"type": "self_evaluation", "score": evaluation["overall_score"]},
                    long_term=True
                )
            
        except Exception as e:
            print(f"自我评估时出错: {str(e)}")
    
    async def shutdown(self):
        """关闭助手
        
        清理资源和关闭插件
        """
        # 关闭插件
        if self.plugins_enabled:
            self.plugin_manager.shutdown_all()
        
        # 记忆整合
        await self.memory_manager.consolidate()


async def chat_terminal(assistant: MCPAdvancedAssistant):
    """
    启动终端聊天界面
    
    Args:
        assistant: MCP高级助手实例
    """
    print(f"\n欢迎使用 {assistant.agent_name}!")
    print("输入 'exit' 或 'quit' 结束对话")
    print("输入 'image:路径' 发送图片")
    print("输入 'memory:内容' 创建记忆")
    print("输入 'retrieve:查询' 检索记忆")
    print("输入 'feedback:评分:评论' 提供反馈\n")
    
    while True:
        try:
            user_input = input("\n用户: ")
            
            if user_input.lower() in ["exit", "quit", "再见", "退出"]:
                print("助手: 再见！")
                break
            
            # 处理特殊命令
            if user_input.startswith("image:"):
                image_path = user_input[6:].strip()
                print("\n[处理图像中...]")
                response = await assistant.process_message(image_path, "image_path")
                print(f"\n助手: {response}")
                
            elif user_input.startswith("memory:"):
                memory_content = user_input[7:].strip()
                memory_id = await assistant.remember(memory_content)
                print(f"\n[记忆已创建，ID: {memory_id}]")
                
            elif user_input.startswith("retrieve:"):
                query = user_input[9:].strip()
                memories = await assistant.retrieve_memory(query)
                print("\n[检索到的记忆]:")
                for i, mem in enumerate(memories, 1):
                    print(f"{i}. {mem['content']}")
                
            elif user_input.startswith("feedback:"):
                parts = user_input[9:].strip().split(":", 1)
                try:
                    rating = int(parts[0])
                    comment = parts[1] if len(parts) > 1 else ""
                    
                    if 1 <= rating <= 5:
                        await assistant.feedback_system.record_user_feedback(
                            rating=rating,
                            comment=comment
                        )
                        print(f"\n[反馈已记录，评分: {rating}/5]")
                    else:
                        print("\n[错误: 评分必须在1到5之间]")
                except Exception as e:
                    print(f"\n[反馈格式错误: {str(e)}]")
                
            else:
                print("\n[思考中...]")
                response = await assistant.process_message(user_input)
                print(f"\n助手: {response}")
            
        except KeyboardInterrupt:
            print("\n\n助手: 再见！")
            break
        
        except Exception as e:
            import traceback
            print(f"\n处理输入时出错: {str(e)}")
            print(traceback.format_exc())
    
    # 关闭助手
    await assistant.shutdown()


async def main_async():
    """主函数"""
    parser = argparse.ArgumentParser(description="MCP高级助手")
    parser.add_argument("--llm", type=str, default="mock", help="LLM提供商 (openai, mock)")
    parser.add_argument("--model", type=str, help="模型名称")
    parser.add_argument("--no-plugins", action="store_true", help="禁用插件")
    parser.add_argument("--no-multimodal", action="store_true", help="禁用多模态")
    parser.add_argument("--no-feedback", action="store_true", help="禁用反馈")
    parser.add_argument("--memory-db", type=str, help="记忆数据库路径")
    parser.add_argument("--name", type=str, default="MCP高级助手", help="智能体名称")
    
    args = parser.parse_args()
    
    # 创建MCP高级助手
    assistant = MCPAdvancedAssistant(
        llm_provider=args.llm,
        model=args.model,
        memory_db=args.memory_db,
        plugins_enabled=not args.no_plugins,
        multimodal_enabled=not args.no_multimodal,
        feedback_enabled=not args.no_feedback,
        agent_name=args.name
    )
    
    # 启动聊天
    await chat_terminal(assistant)

def main():
    """主入口"""
    asyncio.run(main_async())

if __name__ == "__main__":
    main()
