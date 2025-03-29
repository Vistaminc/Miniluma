"""
MiniLuma Web界面服务器
提供基于Flask的Web界面，允许通过浏览器访问MiniLuma功能
"""
import os
import sys
import json
import asyncio
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory
import requests
import uuid
import datetime

# 添加项目根目录到sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

# 创建Flask应用
app = Flask(__name__, 
            static_folder='static',
            template_folder='templates')

# 配置
app.secret_key = str(uuid.uuid4())  # 用于session
API_BASE_URL = "http://localhost:8000"  # MiniLuma API地址

# 主页
@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

# 聊天界面
@app.route('/chat')
def chat():
    """渲染聊天界面"""
    assistant_id = request.args.get('assistant_id')
    if not assistant_id:
        # 如果没有指定助手ID，重定向到创建助手页面
        return redirect(url_for('new_assistant'))
    
    # 从会话中获取助手名称
    assistant_name = session.get(f'assistant_name_{assistant_id}', 'MiniLuma')
    
    return render_template('chat.html', 
                          assistant_id=assistant_id,
                          assistant_name=assistant_name)

# 创建新助手页面
@app.route('/new-assistant')
def new_assistant():
    """渲染创建新助手的页面"""
    return render_template('new_assistant.html')

# 创建助手API端点
@app.route('/api/assistants', methods=['POST'])
def create_assistant():
    """创建一个新的助手实例"""
    data = request.json
    
    # 调用MiniLuma API创建助手
    try:
        response = requests.post(f"{API_BASE_URL}/assistants", json=data)
        response.raise_for_status()
        assistant_data = response.json()
        
        # 保存助手名称到会话
        session[f"assistant_name_{assistant_data['assistant_id']}"] = assistant_data['name']
        
        return jsonify(assistant_data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 发送消息API端点
@app.route('/api/assistants/<assistant_id>/messages', methods=['POST'])
def send_message(assistant_id):
    """向助手发送消息并获取回复"""
    data = request.json
    
    # 调用MiniLuma API发送消息
    try:
        response = requests.post(f"{API_BASE_URL}/assistants/{assistant_id}/messages", json=data)
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 获取文件列表API端点
@app.route('/api/assistants/<assistant_id>/files', methods=['GET'])
def get_files(assistant_id):
    """获取助手生成的文件列表"""
    try:
        response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files")
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 保存文件API端点
@app.route('/api/assistants/<assistant_id>/save-files', methods=['POST'])
def save_files(assistant_id):
    """触发助手保存生成的文件"""
    try:
        response = requests.post(
            f"{API_BASE_URL}/assistants/{assistant_id}/save-files",
            json={"assistant_id": assistant_id}
        )
        response.raise_for_status()
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 结束会话API端点
@app.route('/api/assistants/<assistant_id>/end-session', methods=['POST'])
def end_session(assistant_id):
    """结束助手会话"""
    try:
        api_url = f"{API_BASE_URL}/assistants/{assistant_id}/end"
        response = requests.post(api_url)
        
        if response.status_code == 200:
            # 从会话中移除助手信息
            session.pop(f'assistant_name_{assistant_id}', None)
            return jsonify(response.json())
        else:
            return jsonify({"error": f"结束会话失败，API返回状态码: {response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 添加助手状态路由
@app.route('/api/assistants/<assistant_id>/status', methods=['GET'])
def get_assistant_status(assistant_id):
    """
    获取助手的当前状态
    
    Args:
        assistant_id: 助手ID
    """
    try:
        api_url = f"{API_BASE_URL}/assistants/{assistant_id}/status"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({
                "status": "error",
                "current_operation": "获取状态失败",
                "operation_details": f"API返回状态码: {response.status_code}",
                "assistant_id": assistant_id
            }), 500
    except Exception as e:
        return jsonify({
            "status": "error",
            "current_operation": "获取状态失败",
            "operation_details": str(e),
            "assistant_id": assistant_id
        }), 500

# 获取对话历史记录
@app.route('/api/assistants/<assistant_id>/conversation-history', methods=['GET'])
def get_conversation_history(assistant_id):
    """获取助手的对话历史记录"""
    try:
        api_url = f"{API_BASE_URL}/assistants/{assistant_id}/conversation-history"
        response = requests.get(api_url)
        
        if response.status_code == 200:
            return jsonify(response.json())
        else:
            return jsonify({"error": f"获取对话历史失败，API返回状态码: {response.status_code}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 文件下载代理
@app.route('/api/download/<assistant_id>/<path:filename>')
def download_file(assistant_id, filename):
    """下载助手生成的文件"""
    try:
        # 从MiniLuma API获取文件
        response = requests.get(
            f"{API_BASE_URL}/assistants/{assistant_id}/download/{filename}",
            stream=True
        )
        response.raise_for_status()
        
        # 设置响应头
        headers = {}
        if 'Content-Type' in response.headers:
            headers['Content-Type'] = response.headers['Content-Type']
        if 'Content-Disposition' in response.headers:
            headers['Content-Disposition'] = response.headers['Content-Disposition']
            
        # 返回文件内容
        return response.content, 200, headers
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# 启动服务器
def run_web_server(host="0.0.0.0", port=8080, debug=True):
    """启动Web服务器"""
    app.run(host=host, port=port, debug=debug)

if __name__ == "__main__":
    run_web_server()
