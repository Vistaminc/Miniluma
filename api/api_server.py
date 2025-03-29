"""
MiniLuma API Server
提供基于FastAPI的HTTP API，允许通过REST接口访问MiniLuma的功能
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from fastapi import FastAPI, HTTPException, BackgroundTasks, File, UploadFile, Form, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
from pydantic import BaseModel, Field
import uvicorn
import uuid
import datetime

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入MiniLuma相关模块
from examples.mcp_enhanced_assistant import MCPEnhancedAssistant
from core.config import Config
from utils.logger import ConversationLogger

# 创建FastAPI应用
app = FastAPI(
    title="MiniLuma API",
    description="MiniLuma的API接口，提供对话、文件处理和记忆管理功能",
    version="1.0.0"
)

# 配置CORS中间件，允许跨域请求
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源，可根据需要限制
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加健康检查端点
@app.get("/health", status_code=200)
async def health_check():
    """健康检查端点，用于检测API服务器是否正常运行"""
    return {"status": "healthy", "timestamp": datetime.datetime.now().isoformat()}

# 保存活跃的助手实例
active_assistants = {}

# 保存每个助手的实时状态信息
assistant_status = {}

# 请求/响应模型
class MessageRequest(BaseModel):
    """用户消息请求模型"""
    message: str = Field(..., description="用户消息内容")
    add_to_memory: bool = Field(True, description="是否添加到记忆系统")
    memory_metadata: Optional[Dict[str, Any]] = Field(None, description="记忆元数据")

class MessageResponse(BaseModel):
    """助手响应模型"""
    assistant_id: str = Field(..., description="助手ID")
    conversation_id: str = Field(..., description="对话ID")
    message: str = Field(..., description="助手回复内容")
    saved_files: List[str] = Field([], description="保存的文件列表")

class AssistantCreateRequest(BaseModel):
    """创建助手请求模型"""
    name: str = Field("MiniLuma", description="助手名称")
    assistant_mode: Optional[str] = Field("mcp", description="助手模式：simple/multi_agent/custom/mcp")
    provider_name: Optional[str] = Field(None, description="LLM提供商名称")
    model: Optional[str] = Field(None, description="LLM模型名称")
    system_prompt: Optional[str] = Field(None, description="系统提示词")
    conversation_id: Optional[str] = Field(None, description="指定对话ID，用于恢复对话")

class AssistantResponse(BaseModel):
    """助手响应模型"""
    assistant_id: str = Field(..., description="助手ID")
    name: str = Field(..., description="助手名称")
    conversation_id: str = Field(..., description="对话ID")
    provider: str = Field(..., description="LLM提供商")
    model: str = Field(..., description="LLM模型")

class FileRequest(BaseModel):
    """文件操作请求模型"""
    assistant_id: str = Field(..., description="助手ID")
    file_path: Optional[str] = Field(None, description="文件路径")

class MemoryRequest(BaseModel):
    """记忆操作请求模型"""
    memory_id: str = Field(..., description="记忆ID")
    assistant_id: str = Field(..., description="助手ID")

class AssistantStatus(BaseModel):
    """助手状态模型"""
    assistant_id: str
    current_operation: Optional[str] = None
    operation_details: Optional[str] = None
    progress: Optional[float] = None  # 0-100之间的值
    status: str = "idle"  # idle, thinking, processing, error
    timestamp: str = datetime.datetime.now().isoformat()

# API路由
@app.get("/")
async def root():
    """API根路径，返回API状态信息"""
    return {
        "status": "online", 
        "name": "MiniLuma API", 
        "version": "1.0.0",
        "timestamp": datetime.datetime.now().isoformat()
    }

@app.post("/assistants", response_model=AssistantResponse)
async def create_assistant(request: AssistantCreateRequest):
    """创建一个新的助手实例
    
    创建并初始化MiniLuma助手实例，支持指定提供商、模型和系统提示词
    
    Args:
        request: 创建助手请求对象
        
    Returns:
        新创建的助手信息
    """
    try:
        # 根据选择的模式创建不同类型的助手
        assistant_mode = request.assistant_mode or "mcp"
        
        if assistant_mode == "mcp":
            # 创建MCP增强助手实例
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt
            )
        elif assistant_mode == "simple":
            # 简单助手模式 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt
            )
        elif assistant_mode == "multi_agent":
            # 多代理系统 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt
            )
        elif assistant_mode == "custom":
            # 自定义模式 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt
            )
        else:
            # 未知模式，使用默认的MCP增强助手
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt
            )
        
        # 生成唯一的助手ID
        assistant_id = str(uuid.uuid4())
        
        # 如果提供了对话ID，尝试恢复对话
        if request.conversation_id:
            try:
                await assistant._restore_from_memory(request.conversation_id)
            except Exception as e:
                # 恢复失败时记录错误但继续创建新会话
                print(f"恢复对话失败: {str(e)}")
        
        # 保存助手实例
        active_assistants[assistant_id] = assistant
        
        # 存储助手模式信息
        assistant_status[assistant_id] = AssistantStatus(
            assistant_id=assistant_id,
            status="idle",
            current_operation=None,
            operation_details=f"模式: {assistant_mode}"
        )
        
        # 返回助手信息
        return {
            "assistant_id": assistant_id,
            "name": assistant.name,
            "conversation_id": assistant.conversation_id,
            "provider": assistant.provider.provider_name if hasattr(assistant, 'provider') and assistant.provider else "unknown",
            "model": assistant.provider.model if hasattr(assistant, 'provider') and assistant.provider else "unknown"
        }
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"创建助手失败: {str(e)}")

@app.get("/assistants/{assistant_id}", response_model=AssistantResponse)
async def get_assistant(assistant_id: str):
    """获取助手信息
    
    根据助手ID获取助手实例的详细信息
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        助手详细信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    return {
        "assistant_id": assistant_id,
        "name": assistant.name,
        "conversation_id": assistant.conversation_id,
        "provider": assistant.provider_name,
        "model": assistant.model
    }

@app.get("/assistants/{assistant_id}/status", response_model=AssistantStatus)
async def get_assistant_status(assistant_id: str):
    """获取助手的当前状态
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        AssistantStatus: 助手当前状态信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail=f"助手 {assistant_id} 不存在")
    
    # 获取助手的状态信息，如果没有则返回默认状态
    status = assistant_status.get(assistant_id, AssistantStatus(
        assistant_id=assistant_id,
        status="idle",
        timestamp=datetime.datetime.now().isoformat()
    ))
    
    return status

@app.post("/assistants/{assistant_id}/status", response_model=AssistantStatus)
async def update_assistant_status(assistant_id: str, status: AssistantStatus):
    """更新助手的当前状态
    
    Args:
        assistant_id: 助手ID
        status: 新的状态信息
        
    Returns:
        AssistantStatus: 更新后的状态信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail=f"助手 {assistant_id} 不存在")
    
    # 更新时间戳
    status.timestamp = datetime.datetime.now().isoformat()
    assistant_status[assistant_id] = status
    
    return status

@app.post("/assistants/{assistant_id}/messages", response_model=MessageResponse)
async def process_message(assistant_id: str, request: MessageRequest, background_tasks: BackgroundTasks):
    """处理用户消息
    
    发送消息给指定助手并获取回复
    
    Args:
        assistant_id: 助手ID
        request: 用户消息请求
        background_tasks: FastAPI后台任务
        
    Returns:
        助手回复消息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 更新助手状态为"思考中"
        status = AssistantStatus(
            assistant_id=assistant_id,
            status="thinking",
            current_operation="正在处理您的请求",
            operation_details="分析问题并准备回应",
            progress=10.0
        )
        assistant_status[assistant_id] = status
        
        # 处理用户消息
        response = await assistant.process(
            user_input=request.message,
            add_to_memory=request.add_to_memory,
            memory_metadata=request.memory_metadata
        )
        
        # 获取生成的文件列表
        saved_files = []
        if hasattr(assistant, "auto_saved_files") and assistant.auto_saved_files:
            saved_files = list(assistant.auto_saved_files.values())
        
        # 更新助手状态为"空闲"
        status = AssistantStatus(
            assistant_id=assistant_id,
            status="idle",
            timestamp=datetime.datetime.now().isoformat()
        )
        assistant_status[assistant_id] = status
        
        return {
            "assistant_id": assistant_id,
            "conversation_id": assistant.conversation_id,
            "message": response,
            "saved_files": saved_files
        }
    except Exception as e:
        # 更新助手状态为"错误"
        status = AssistantStatus(
            assistant_id=assistant_id,
            status="error",
            current_operation="处理请求时出错",
            operation_details=str(e),
            timestamp=datetime.datetime.now().isoformat()
        )
        assistant_status[assistant_id] = status
        
        raise HTTPException(status_code=500, detail=f"处理消息失败: {str(e)}")

@app.post("/assistants/{assistant_id}/save-files")
async def save_files(assistant_id: str, request: FileRequest):
    """保存助手生成的文件
    
    触发助手保存生成的文件到结果目录
    
    Args:
        assistant_id: 助手ID
        request: 文件保存请求
        
    Returns:
        保存结果信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 调用助手的文件保存方法
        result = await assistant._save_generated_files(request.file_path)
        
        # 返回保存结果
        return {
            "assistant_id": assistant_id,
            "message": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"保存文件失败: {str(e)}")

@app.get("/assistants/{assistant_id}/files")
async def get_files(assistant_id: str):
    """获取助手生成的文件
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        生成的文件列表
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        saved_files = {}
        
        # 获取自动保存的文件
        if hasattr(assistant, "auto_saved_files") and assistant.auto_saved_files:
            saved_files = assistant.auto_saved_files
        
        # 获取临时生成的文件（尚未自动保存的）
        if hasattr(assistant, "pending_files_to_save") and assistant.pending_files_to_save:
            for file_path in assistant.pending_files_to_save:
                # 使用文件名作为键
                file_name = os.path.basename(file_path)
                saved_files[file_path] = file_path
        
        return {
            "assistant_id": assistant_id,
            "files": saved_files
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件列表失败: {str(e)}")

@app.get("/assistants/{assistant_id}/download/{file_name}")
async def download_file(assistant_id: str, file_name: str):
    """下载生成的文件
    
    根据文件名下载助手生成的文件
    
    Args:
        assistant_id: 助手ID
        file_name: 文件名
        
    Returns:
        文件内容
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 检查文件是否存在
        file_path = None
        if hasattr(assistant, "auto_saved_files") and assistant.auto_saved_files:
            # 查找匹配的文件
            for orig_path, saved_path in assistant.auto_saved_files.items():
                if os.path.basename(saved_path) == file_name:
                    file_path = saved_path
                    break
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail="未找到指定文件")
        
        # 返回文件内容
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type="application/octet-stream"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"下载文件失败: {str(e)}")

@app.get("/assistants/{assistant_id}/conversation-history")
async def get_conversation_history(assistant_id: str):
    """获取助手的对话历史记录
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        对话历史记录列表
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 获取对话历史
        history = []
        if hasattr(assistant, "conversation_history") and assistant.conversation_history:
            history = assistant.conversation_history
        
        return {
            "assistant_id": assistant_id,
            "conversation_id": assistant.conversation_id,
            "history": history
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取对话历史失败: {str(e)}")

@app.post("/assistants/{assistant_id}/restore-memory")
async def restore_memory(assistant_id: str, request: MemoryRequest):
    """恢复特定记忆
    
    根据记忆ID恢复助手对话记忆
    
    Args:
        assistant_id: 助手ID
        request: 记忆恢复请求
        
    Returns:
        恢复结果信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 调用助手的记忆恢复方法
        result = await assistant._restore_from_memory(request.memory_id)
        
        # 返回恢复结果
        return {
            "assistant_id": assistant_id,
            "message": result,
            "memory_id": request.memory_id,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"恢复记忆失败: {str(e)}")

@app.post("/assistants/{assistant_id}/end-session")
async def end_session(assistant_id: str):
    """结束助手会话
    
    结束并保存指定助手的会话状态
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        结束会话结果信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 调用助手的会话结束方法
        result = await assistant.end_session()
        
        # 从活跃助手中移除
        del active_assistants[assistant_id]
        
        # 返回结束结果
        return {
            "success": True,
            "message": "会话已结束",
            "details": result,
            "timestamp": datetime.datetime.now().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"结束会话失败: {str(e)}")

# 主函数，启动API服务器
def start_api_server(host="0.0.0.0", port=8000, workers=1, use_signals=True):
    """启动API服务器
    
    Args:
        host: 服务器主机地址
        port: 服务器端口
        workers: 工作进程数量
        use_signals: 是否使用信号处理器，在子线程中应设为False
    """
    # 在子线程中启动时禁用信号处理器
    config = uvicorn.Config(
        "api.api_server:app",
        host=host,
        port=port,
        reload=False,  # 在子线程中不能使用reload
        workers=workers,
        use_colors=True,
        log_level="info"
    )
    server = uvicorn.Server(config)
    if not use_signals:
        server.config.use_colors = True
        server.config.signal_handlers = []  # 禁用信号处理器
    server.run()

# 当作为脚本运行时，启动服务器
if __name__ == "__main__":
    start_api_server(workers=1, use_signals=True)
