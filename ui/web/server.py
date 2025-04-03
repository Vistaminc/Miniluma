"""
MiniLuma Web界面服务器
提供基于Flask的Web界面，允许通过浏览器访问MiniLuma功能
"""
import os
import sys
import json
import asyncio
import traceback
import zipfile
import io
from typing import Dict, List, Any, Optional
from flask import Flask, render_template, request, jsonify, redirect, url_for, session, send_from_directory, send_file
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
API_BASE_URL = "http://localhost:9788"  # MiniLuma API地址

# 添加全局错误处理
@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常处理"""
    # 记录详细的错误信息
    error_message = f"服务器错误: {str(e)}\n"
    error_message += traceback.format_exc()
    print("=" * 50)
    print("服务器发生错误:")
    print(error_message)
    print("=" * 50)
    
    # 返回错误页面或JSON
    if request.path.startswith('/api/'):
        return jsonify({"error": str(e), "details": traceback.format_exc()}), 500
    else:
        return f"""
        <html>
            <head><title>服务器错误</title></head>
            <body>
                <h1>服务器错误</h1>
                <p>非常抱歉，服务器遇到了一个问题：</p>
                <pre>{str(e)}</pre>
                <h2>详细信息：</h2>
                <pre>{traceback.format_exc()}</pre>
            </body>
        </html>
        """, 500

# 主页
@app.route('/')
def index():
    """渲染主页"""
    return render_template('index.html')

# 测试页面
@app.route('/test')
def test_page():
    """渲染测试页面"""
    return render_template('test.html')

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

# 聊天界面 - 路径参数版本
@app.route('/chat/<assistant_id>')
def chat_with_id(assistant_id):
    """使用路径参数渲染聊天界面"""
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

# 下载所有文件为zip压缩包
@app.route('/api/assistants/<assistant_id>/download-all', methods=['GET'])
def download_all_files_as_zip(assistant_id):
    """将助手生成的所有文件打包为zip格式下载"""
    try:
        # 获取文件列表
        response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files")
        response.raise_for_status()
        files_data = response.json()
        
        if not files_data.get('files') or len(files_data['files']) == 0:
            return jsonify({"error": "没有可下载的文件"}), 404
        
        # 创建内存中的zip文件
        memory_file = io.BytesIO()
        with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zipf:
            # 获取每个文件并添加到zip中
            for original_path, saved_path in files_data['files'].items():
                clean_filename = os.path.basename(saved_path)
                
                try:
                    # 尝试下载文件内容
                    try:
                        file_response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/download/{clean_filename}", stream=True)
                        file_response.raise_for_status()
                        file_content = file_response.content
                    except Exception as e:
                        # 尝试备用API
                        file_response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files/content", 
                                              params={"file_name": clean_filename})
                        file_response.raise_for_status()
                        
                        # 如果是JSON响应，提取内容
                        if 'application/json' in file_response.headers.get('Content-Type', ''):
                            content_data = file_response.json()
                            file_content = content_data.get("content", "").encode('utf-8')
                        else:
                            file_content = file_response.content
                    
                    # 使用原始路径作为zip内的路径（如果有）
                    zip_path = original_path if original_path else clean_filename
                    zipf.writestr(zip_path, file_content)
                except Exception as e:
                    print(f"添加文件 {clean_filename} 到zip时出错: {e}")
                    # 继续处理其他文件
        
        # 将文件指针移到开头
        memory_file.seek(0)
        
        # 生成下载文件名
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        download_filename = f"MiniLuma_files_{assistant_id}_{timestamp}.zip"
        
        return send_file(
            memory_file,
            mimetype='application/zip',
            as_attachment=True,
            download_name=download_filename
        )
    except Exception as e:
        error_msg = f"打包文件失败: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

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

# 查看代码文件
@app.route('/view-code/<assistant_id>/<path:filename>')
def view_code(assistant_id, filename):
    """使用代码高亮查看生成的代码文件"""
    try:
        # 获取纯文件名（移除任何路径信息）
        clean_filename = os.path.basename(filename)
        
        # 调用MiniLuma API获取文件内容
        try:
            # 先尝试使用文件内容API
            content_response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files/content", 
                                          params={"file_name": clean_filename})
            content_response.raise_for_status()
            file_content = content_response.json().get("content", "")
        except Exception as e:
            print(f"无法获取文件内容: {e}")
            # 尝试备用方法
            try:
                # 备用：从文件下载API获取
                download_response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/download/{clean_filename}")
                download_response.raise_for_status()
                file_content = download_response.content.decode('utf-8', errors='replace')
            except Exception as download_error:
                print(f"备用方法也失败: {download_error}")
                file_content = f"// 无法加载文件内容: {str(e)}\n// 然后: {str(download_error)}"
        
        # 获取文件内容
        # file_content = response.content.decode('utf-8')
        
        # 根据文件扩展名确定语言
        file_extension = clean_filename.split('.')[-1].lower() if '.' in clean_filename else ''
        code_language = file_extension
        
        # 映射扩展名到highlight.js支持的语言
        language_mapping = {
            'js': 'javascript',
            'ts': 'typescript',
            'py': 'python',
            'html': 'html',
            'htm': 'html',
            'css': 'css',
            'scss': 'scss',
            'json': 'json',
            'md': 'markdown',
            'java': 'java',
            'cpp': 'cpp',
            'c': 'c',
            'cs': 'csharp',
            'rb': 'ruby',
            'php': 'php',
            'go': 'go',
            'sh': 'bash',
            'bat': 'batch',
            'ps1': 'powershell',
            'sql': 'sql',
            'xml': 'xml',
            'yaml': 'yaml',
            'yml': 'yaml',
            'txt': 'plaintext'
        }
        
        code_language = language_mapping.get(file_extension, file_extension)
        
        # 从会话中获取助手名称
        assistant_name = session.get(f'assistant_name_{assistant_id}', 'MiniLuma')
        
        # 尝试获取文件路径(可能不存在)
        try:
            files_response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files")
            files_response.raise_for_status()
            files_data = files_response.json()
            file_path = next((path for path in files_data.get("files", {}).values() if os.path.basename(path) == clean_filename), "")
        except:
            file_path = ""
        
        return render_template('view_code.html',
                               assistant_id=assistant_id,
                               assistant_name=assistant_name,
                               file_name=clean_filename,
                               file_path=file_path,
                               file_extension=file_extension,
                               file_content=file_content,
                               code_language=code_language)
    except Exception as e:
        return f"<h1>错误</h1><p>无法加载文件: {str(e)}</p><a href='/chat?assistant_id={assistant_id}'>返回对话</a>", 500

# 文件下载代理
@app.route('/api/download/<assistant_id>/<path:filename>')
def download_file(assistant_id, filename):
    """下载助手生成的文件"""
    try:
        # 获取纯文件名（移除任何路径信息）
        clean_filename = os.path.basename(filename)
        
        # 调用MiniLuma API下载文件
        try:
            # 尝试使用download API端点
            response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/download/{clean_filename}", stream=True)
            response.raise_for_status()
        except Exception as e:
            print(f"使用download API失败: {e}")
            # 尝试备用API
            response = requests.get(f"{API_BASE_URL}/assistants/{assistant_id}/files/content", 
                                  params={"file_name": clean_filename})
            response.raise_for_status()
            
            # 如果是JSON响应，提取内容并转为二进制
            if 'application/json' in response.headers.get('Content-Type', ''):
                content_data = response.json()
                response._content = content_data.get("content", "").encode('utf-8')
        
        # 创建临时目录用于保存文件
        temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'temp')
        os.makedirs(temp_dir, exist_ok=True)
        
        # 保存文件到临时目录
        file_path = os.path.join(temp_dir, clean_filename)
        with open(file_path, 'wb') as f:
            if hasattr(response, 'iter_content'):
                for chunk in response.iter_content(chunk_size=8192): 
                    f.write(chunk)
            else:
                f.write(response.content)
        
        # 从临时目录提供文件下载
        return send_from_directory(temp_dir, clean_filename, as_attachment=True)
    except Exception as e:
        error_msg = f"下载文件失败: {str(e)}"
        print(error_msg)
        return jsonify({"error": error_msg}), 500

# 启动服务器
def run_web_server(host="0.0.0.0", port=9787, debug=True):
    """启动Web服务器"""
    app.debug = True  # 启用调试模式以获取详细错误信息
    print("Web服务器调试模式已开启...")
    app.run(host=host, port=port)

if __name__ == "__main__":
    run_web_server()
