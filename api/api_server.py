"""
MiniLuma API Server
提供基于FastAPI的HTTP API，允许通过REST接口访问MiniLuma的功能
"""
import os
import sys
import json
import asyncio
import glob
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

# 项目根目录路径
def get_project_root():
    """获取项目根目录"""
    # 获取当前模块路径
    current_file = os.path.abspath(__file__)
    # 获取api目录
    api_dir = os.path.dirname(current_file)
    # 获取项目根目录
    root_dir = os.path.dirname(api_dir)
    return root_dir

PROJECT_ROOT = get_project_root()
ASSISTANTS_DIR = os.path.join(PROJECT_ROOT, "assistants")

# 创建助手保存目录
os.makedirs(ASSISTANTS_DIR, exist_ok=True)

# 助手会话信息模型
class AssistantSession(BaseModel):
    """助手会话信息模型"""
    assistant_id: str
    name: str
    conversation_id: str
    provider_name: Optional[str]
    model: Optional[str]
    system_prompt: Optional[str]
    assistant_mode: str = "mcp"
    created_at: str
    last_used: str

# 持久化助手会话信息
async def save_assistant_session(assistant_id: str, assistant: Any, assistant_mode: str = "mcp"):
    """持久化保存助手会话信息"""
    try:
        # 仅保存需要的信息，不保存完整对象
        session_data = AssistantSession(
            assistant_id=assistant_id,
            name=assistant.name,
            conversation_id=assistant.conversation_id,
            provider_name=assistant.provider.provider_name if hasattr(assistant, 'provider') and assistant.provider else None,
            model=assistant.provider.model if hasattr(assistant, 'provider') and assistant.provider else None,
            system_prompt=assistant.system_prompt if hasattr(assistant, 'system_prompt') else None,
            assistant_mode=assistant_mode,
            created_at=datetime.datetime.now().isoformat(),
            last_used=datetime.datetime.now().isoformat()
        )
        
        # 保存到文件
        filepath = os.path.join(ASSISTANTS_DIR, f"{assistant_id}.json")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(session_data.json(ensure_ascii=False, indent=2))
            
        print(f"助手会话信息已保存: {assistant_id}")
    except Exception as e:
        print(f"保存助手会话信息失败: {str(e)}")

# 加载助手会话信息
async def load_assistant_sessions():
    """加载所有助手会话信息"""
    sessions = []
    
    # 查找助手会话文件
    session_files = glob.glob(os.path.join(ASSISTANTS_DIR, "*.json"))
    for file_path in session_files:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                sessions.append(AssistantSession(**data))
        except Exception as e:
            print(f"加载助手会话文件失败 {file_path}: {str(e)}")
    
    print(f"找到 {len(sessions)} 个助手会话记录")
    return sessions

# 尝试恢复助手会话
async def restore_assistant_sessions():
    """尝试恢复之前的助手会话"""
    sessions = await load_assistant_sessions()
    restored_count = 0
    
    for session in sessions:
        try:
            # 检查results目录中是否存在对应的对话ID记录
            conversation_path = find_conversation_directory(session.conversation_id)
            if not conversation_path:
                print(f"找不到对话目录，无法恢复助手: {session.assistant_id}, 对话ID: {session.conversation_id}")
                continue
                
            # 基于助手模式创建新实例
            if session.assistant_mode == "mcp" or not session.assistant_mode:
                assistant = await MCPEnhancedAssistant.create(
                    name=session.name,
                    provider_name=session.provider_name,
                    model=session.model,
                    system_prompt=session.system_prompt
                )
            else:
                # 对于其他模式，目前暂时使用MCPEnhancedAssistant
                assistant = await MCPEnhancedAssistant.create(
                    name=session.name,
                    provider_name=session.provider_name,
                    model=session.model,
                    system_prompt=session.system_prompt
                )
            
            # 尝试恢复对话记录
            try:
                await assistant._restore_from_memory(session.conversation_id)
                # 更新助手ID保持一致
                active_assistants[session.assistant_id] = assistant
                
                # 添加状态信息
                assistant_status[session.assistant_id] = AssistantStatus(
                    assistant_id=session.assistant_id,
                    status="idle",
                    current_operation=None,
                    operation_details=f"模式: {session.assistant_mode}, 已自动恢复"
                )
                
                restored_count += 1
                print(f"成功恢复助手: {session.assistant_id}, 名称: {session.name}")
            except Exception as e:
                print(f"恢复助手对话失败: {session.assistant_id}, 错误: {str(e)}")
                
        except Exception as e:
            print(f"恢复助手会话失败: {session.assistant_id}, 错误: {str(e)}")
    
    print(f"成功恢复 {restored_count}/{len(sessions)} 个助手会话")
    return restored_count

# 查找对话目录
def find_conversation_directory(conversation_id: str):
    """在results目录中查找对话目录"""
    results_dir = os.path.join(PROJECT_ROOT, "results")
    
    # 如果results目录不存在，返回None
    if not os.path.exists(results_dir):
        return None
    
    # 按日期目录搜索
    date_dirs = [d for d in os.listdir(results_dir) if os.path.isdir(os.path.join(results_dir, d))]
    
    for date_dir in date_dirs:
        date_path = os.path.join(results_dir, date_dir)
        # 查找对话ID目录
        conv_path = os.path.join(date_path, conversation_id)
        if os.path.exists(conv_path) and os.path.isdir(conv_path):
            return conv_path
    
    return None

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
    use_memory_id: bool = Field(True, description="是否使用记忆系统ID格式作为助手ID")
    assistant_id: Optional[str] = Field(None, description="指定助手ID，仅当use_memory_id为False时使用")

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
        
        # 确定是否使用记忆系统ID格式
        # 默认使用记忆系统ID格式，除非明确指定了use_memory_id为False
        use_memory_id = request.use_memory_id
        
        # 如果不使用记忆系统ID格式，则使用标准UUID或用户指定的ID
        assistant_id = None
        if not use_memory_id:
            # 如果提供了assistant_id，使用它；否则生成一个新的UUID
            assistant_id = request.assistant_id if request.assistant_id else str(uuid.uuid4())
            print(f"使用标准UUID作为助手ID: {assistant_id}")
        
        # 创建助手实例 - 如果use_memory_id为True，assistant_id为None，
        # MCPEnhancedAssistant的create方法会自动生成记忆系统格式的ID
        if assistant_mode == "mcp":
            # 创建MCP增强助手实例
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt,
                assistant_id=assistant_id
            )
        elif assistant_mode == "simple":
            # 简单助手模式 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt,
                assistant_id=assistant_id
            )
        elif assistant_mode == "multi_agent":
            # 多代理系统 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt,
                assistant_id=assistant_id
            )
        elif assistant_mode == "custom":
            # 自定义模式 - 目前暂时使用MCPEnhancedAssistant作为后备
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt,
                assistant_id=assistant_id
            )
        else:
            # 未知模式，使用默认的MCP增强助手
            assistant = await MCPEnhancedAssistant.create(
                name=request.name,
                provider_name=request.provider_name,
                model=request.model,
                system_prompt=request.system_prompt,
                assistant_id=assistant_id
            )
        
        # 获取助手实例的ID，如果使用的是记忆系统格式的ID，这里会得到记忆系统格式的ID
        assistant_id = assistant.assistant_id
        
        # 输出创建的助手ID格式
        if assistant_id.startswith("mem_"):
            print(f"创建了带有记忆系统ID格式的助手: {assistant_id}")
        else:
            print(f"创建了带有标准UUID格式的助手: {assistant_id}")
        
        # 如果提供了对话ID，尝试恢复对话
        if request.conversation_id:
            try:
                # 恢复对话记录
                await assistant._restore_from_memory(request.conversation_id)
                # 对话恢复成功后，记录一下日志
                print(f"从记忆ID {request.conversation_id} 恢复对话成功")
            except Exception as e:
                # 恢复失败时记录错误但继续创建新会话
                print(f"恢复对话失败: {str(e)}")
        
        # 保存助手实例 - 使用记忆系统格式的ID
        active_assistants[assistant_id] = assistant
        
        # 存储助手模式信息
        assistant_status[assistant_id] = AssistantStatus(
            assistant_id=assistant_id,
            status="idle",
            current_operation=None,
            operation_details=f"模式: {assistant_mode}"
        )
        
        # 持久化保存会话信息
        await save_assistant_session(assistant_id, assistant, assistant_mode)
        
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
    # 检查助手是否存在
    if assistant_id not in active_assistants:
        # 检查是否是ID映射更新 - 新ID可能是记忆ID
        if status.assistant_id != assistant_id and status.assistant_id in active_assistants:
            # 这是一个ID映射更新，状态中的assistant_id是新ID
            print(f"检测到ID映射更新: {assistant_id} -> {status.assistant_id}")
            
            # 获取旧ID对应的助手
            assistant = active_assistants[status.assistant_id]
            
            # 将助手对象复制到新ID，保持旧ID可访问
            active_assistants[assistant_id] = assistant
            
            # 更新状态信息
            assistant_status[assistant_id] = status
            return status
        else:
            # 如果不是ID映射更新且助手不存在，返回404
            raise HTTPException(status_code=404, detail="未找到指定助手")
    
    # 更新状态信息
    assistant_status[assistant_id] = status
    
    # 返回更新后的状态
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
        
        # 更新会话最后使用时间
        session_file = os.path.join(ASSISTANTS_DIR, f"{assistant_id}.json")
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    session_data = json.load(f)
                
                session_data['last_used'] = datetime.datetime.now().isoformat()
                with open(session_file, 'w', encoding='utf-8') as f:
                    json.dump(session_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"更新会话最后使用时间失败: {str(e)}")
        
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

@app.get("/assistants/{assistant_id}/files/{file_name}")
async def get_file_content(assistant_id: str, file_name: str):
    """获取指定文件的内容
    
    根据文件名获取助手生成的文件内容
    
    Args:
        assistant_id: 助手ID
        file_name: 文件名（仅文件名，不含路径）
        
    Returns:
        文件内容
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    assistant = active_assistants[assistant_id]
    
    try:
        # 提取纯文件名（如果包含路径）
        clean_file_name = os.path.basename(file_name)
        
        # 检查文件是否存在
        file_path = None
        if hasattr(assistant, "auto_saved_files") and assistant.auto_saved_files:
            # 查找匹配的文件
            for orig_path, saved_path in assistant.auto_saved_files.items():
                if os.path.basename(saved_path) == clean_file_name:
                    file_path = saved_path
                    break
        
        if not file_path or not os.path.exists(file_path):
            # 查找临时文件
            if hasattr(assistant, "pending_files_to_save") and assistant.pending_files_to_save:
                for temp_path in assistant.pending_files_to_save:
                    if os.path.basename(temp_path) == clean_file_name:
                        file_path = temp_path
                        break
        
        if not file_path or not os.path.exists(file_path):
            raise HTTPException(status_code=404, detail=f"未找到指定文件: {clean_file_name}")
        
        # 判断文件类型
        _, file_ext = os.path.splitext(file_path)
        
        # 设置适当的媒体类型
        media_type = "application/octet-stream"  # 默认
        if file_ext.lower() in ['.txt', '.md', '.py', '.js', '.html', '.css', '.json', '.xml', '.yml', '.yaml']:
            media_type = "text/plain"
        elif file_ext.lower() in ['.jpg', '.jpeg']:
            media_type = "image/jpeg"
        elif file_ext.lower() == '.png':
            media_type = "image/png"
        elif file_ext.lower() == '.gif':
            media_type = "image/gif"
        elif file_ext.lower() == '.svg':
            media_type = "image/svg+xml"
        
        # 返回文件内容
        return FileResponse(
            path=file_path,
            filename=os.path.basename(file_path),
            media_type=media_type
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"获取文件内容失败: {str(e)}")

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

@app.delete("/assistants/{assistant_id}")
async def delete_assistant(assistant_id: str):
    """删除助手实例
    
    删除指定的助手实例和相关资源
    
    Args:
        assistant_id: 助手ID
        
    Returns:
        删除结果信息
    """
    if assistant_id not in active_assistants:
        raise HTTPException(status_code=404, detail="未找到指定助手")
    
    try:
        # 结束会话
        assistant = active_assistants[assistant_id]
        
        # 从内存中移除
        del active_assistants[assistant_id]
        if assistant_id in assistant_status:
            del assistant_status[assistant_id]
        
        # 删除持久化文件
        session_file = os.path.join(ASSISTANTS_DIR, f"{assistant_id}.json")
        if os.path.exists(session_file):
            os.remove(session_file)
        
        return {"status": "success", "message": f"已删除助手 {assistant_id}"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除助手失败: {str(e)}")

# 主函数，启动API服务器
async def start_api_server(host="0.0.0.0", port=9788, workers=1, use_signals=True):
    """启动API服务器
    
    Args:
        host: 服务器主机地址
        port: 服务器端口
        workers: 工作进程数量
        use_signals: 是否使用信号处理器，在子线程中应设为False
    """
    import uvicorn
    
    # 尝试恢复之前的助手会话
    print("正在尝试恢复之前的助手会话...")
    restored_count = await restore_assistant_sessions()
    if restored_count > 0:
        print(f"成功恢复了 {restored_count} 个助手会话")
    
    # 使用正确的Logger参数启动Uvicorn
    if workers == 1:
        config = uvicorn.Config(app, host=host, port=port, log_level="info")
        server = uvicorn.Server(config)
        
        # 在所有版本中都存在的方法
        await server.serve()
    else:
        # 多工作进程模式
        print(f"启动 {workers} 个工作进程")
        uvicorn.run(app, host=host, port=port, workers=workers)

# 当作为脚本运行时，启动服务器
if __name__ == "__main__":
    import asyncio
    asyncio.run(start_api_server(workers=1, use_signals=True))
