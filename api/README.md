# MiniLuma API 文档

## 简介

MiniLuma API 是一个基于FastAPI的RESTful API服务，允许开发者通过HTTP请求访问MiniLuma的核心功能。通过这个API，您可以：

- 创建和管理MiniLuma助手实例
- 发送消息并获取回复
- 管理和获取生成的文件
- 使用记忆系统恢复对话上下文
- 结束会话并保存状态

API遵循RESTful设计原则，使用JSON作为数据交换格式，并提供详细的错误信息。

## 目录

- [开始使用](#开始使用)
- [API参考](#api参考)
  - [助手管理](#助手管理)
  - [消息处理](#消息处理)
  - [文件操作](#文件操作)
  - [记忆管理](#记忆管理)
- [请求/响应模型](#请求响应模型)
- [错误处理](#错误处理)
- [示例](#示例)

## 开始使用

### 安装依赖

在使用MiniLuma API之前，确保已安装所需的依赖：

```bash
pip install fastapi uvicorn pydantic
```

### 启动API服务器

您可以通过以下方式启动API服务器：

```bash
# 方法1：直接运行api_server.py
python -m api.api_server

# 方法2：通过Python代码启动
from api.api_server import start_api_server
start_api_server(host="0.0.0.0", port=8000)
```

服务器默认运行在`http://localhost:8000`，API文档可通过`http://localhost:8000/docs`访问。

## API参考

### 助手管理

#### 创建助手

```
POST /assistants
```

创建一个新的MiniLuma助手实例。

**请求参数**：
```json
{
  "name": "MiniLuma",
  "provider_name": "openai",
  "model": "gpt-4",
  "system_prompt": "你是一个智能助手，帮助用户解决问题",
  "conversation_id": null
}
```

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "MiniLuma",
  "conversation_id": "2618ad48-279a-4e1a-ad93-692f057e45eb",
  "provider": "openai",
  "model": "gpt-4"
}
```

#### 获取助手信息

```
GET /assistants/{assistant_id}
```

根据ID获取助手实例的详细信息。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "MiniLuma",
  "conversation_id": "2618ad48-279a-4e1a-ad93-692f057e45eb",
  "provider": "openai",
  "model": "gpt-4"
}
```

### 消息处理

#### 处理用户消息

```
POST /assistants/{assistant_id}/messages
```

向指定助手发送消息并获取回复。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)
- 请求体:
```json
{
  "message": "请帮我写一个Python函数，计算斐波那契数列",
  "add_to_memory": true,
  "memory_metadata": {
    "category": "programming",
    "topic": "算法"
  }
}
```

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "conversation_id": "2618ad48-279a-4e1a-ad93-692f057e45eb",
  "message": "以下是计算斐波那契数列的Python函数：\n\n```python\ndef fibonacci(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    else:\n        return fibonacci(n-1) + fibonacci(n-2)\n```\n\n这是一个递归实现，对于较大的n值可能会导致性能问题。你可以使用动态规划来优化：\n\n```python\ndef fibonacci_optimized(n):\n    if n <= 0:\n        return 0\n    elif n == 1:\n        return 1\n    \n    fib = [0] * (n+1)\n    fib[1] = 1\n    \n    for i in range(2, n+1):\n        fib[i] = fib[i-1] + fib[i-2]\n    \n    return fib[n]\n```",
  "saved_files": [
    "/results/20250329/202520250329+154345_45eb/code_snippet.py"
  ]
}
```

### 文件操作

#### 保存生成的文件

```
POST /assistants/{assistant_id}/save-files
```

触发助手保存生成的文件到结果目录。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)
- 请求体:
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "file_path": null
}
```

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "成功保存了 3 个文件到 /results/20250329/202520250329+154345_45eb/",
  "timestamp": "2025-03-29T15:43:45.123456"
}
```

#### 列出生成的文件

```
GET /assistants/{assistant_id}/files
```

获取助手生成并保存的文件列表。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "files": {
    "/tmp/code_snippet.py": "/results/20250329/202520250329+154345_45eb/code_snippet.py",
    "/tmp/requirements.txt": "/results/20250329/202520250329+154345_45eb/requirements.txt"
  },
  "count": 2,
  "timestamp": "2025-03-29T15:43:45.123456"
}
```

#### 下载生成的文件

```
GET /assistants/{assistant_id}/download/{file_name}
```

下载助手生成的特定文件。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)
- `file_name`: 文件名 (路径参数)

**响应**：
文件内容二进制流，带有适当的Content-Type和Content-Disposition头部。

### 记忆管理

#### 恢复记忆

```
POST /assistants/{assistant_id}/restore-memory
```

根据记忆ID恢复助手对话记忆。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)
- 请求体:
```json
{
  "memory_id": "mem_1743233474_-2051924784478605061",
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6"
}
```

**响应**：
```json
{
  "assistant_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "message": "已恢复记忆ID: mem_1743233474_-2051924784478605061，找到相关上下文",
  "memory_id": "mem_1743233474_-2051924784478605061",
  "timestamp": "2025-03-29T15:43:45.123456"
}
```

#### 结束会话

```
POST /assistants/{assistant_id}/end-session
```

结束并保存指定助手的会话状态。

**请求参数**：
- `assistant_id`: 助手ID (路径参数)

**响应**：
```json
{
  "success": true,
  "message": "会话已结束",
  "details": "会话已结束，所有状态已保存",
  "timestamp": "2025-03-29T15:43:45.123456"
}
```

## 请求/响应模型

### 消息请求模型 (MessageRequest)

| 字段 | 类型 | 描述 | 必填 |
|------|------|------|------|
| message | string | 用户消息内容 | 是 |
| add_to_memory | boolean | 是否添加到记忆系统 | 否 (默认: true) |
| memory_metadata | object | 记忆元数据 | 否 |

### 消息响应模型 (MessageResponse)

| 字段 | 类型 | 描述 |
|------|------|------|
| assistant_id | string | 助手ID |
| conversation_id | string | 对话ID |
| message | string | 助手回复内容 |
| saved_files | array | 保存的文件列表 |

### 助手创建请求模型 (AssistantCreateRequest)

| 字段 | 类型 | 描述 | 必填 |
|------|------|------|------|
| name | string | 助手名称 | 否 (默认: "MiniLuma") |
| provider_name | string | LLM提供商名称 | 否 |
| model | string | LLM模型名称 | 否 |
| system_prompt | string | 系统提示词 | 否 |
| conversation_id | string | 指定对话ID，用于恢复对话 | 否 |

### 助手响应模型 (AssistantResponse)

| 字段 | 类型 | 描述 |
|------|------|------|
| assistant_id | string | 助手ID |
| name | string | 助手名称 |
| conversation_id | string | 对话ID |
| provider | string | LLM提供商 |
| model | string | LLM模型 |

## 错误处理

API使用标准HTTP状态码表示请求结果：

- `200 OK`: 请求成功
- `400 Bad Request`: 请求参数错误
- `404 Not Found`: 资源未找到，如指定的助手或文件不存在
- `500 Internal Server Error`: 服务器内部错误

错误响应格式：

```json
{
  "detail": "错误信息描述"
}
```

## 示例

### 完整交互示例 (使用Python requests库)

```python
import requests
import json

# API基础URL
BASE_URL = "http://localhost:8000"

# 1. 创建助手
response = requests.post(
    f"{BASE_URL}/assistants",
    json={
        "name": "MiniLuma助手",
        "provider_name": "openai",
        "model": "gpt-4"
    }
)
assistant_data = response.json()
assistant_id = assistant_data["assistant_id"]
print(f"创建的助手ID: {assistant_id}")
print(f"对话ID: {assistant_data['conversation_id']}")

# 2. 发送消息
response = requests.post(
    f"{BASE_URL}/assistants/{assistant_id}/messages",
    json={
        "message": "请用Python写一个简单的Web服务器",
        "add_to_memory": True
    }
)
message_data = response.json()
print(f"助手回复: {message_data['message']}")
print(f"生成的文件: {message_data['saved_files']}")

# 3. 保存生成的文件
response = requests.post(
    f"{BASE_URL}/assistants/{assistant_id}/save-files",
    json={
        "assistant_id": assistant_id
    }
)
save_data = response.json()
print(f"保存结果: {save_data['message']}")

# 4. 列出生成的文件
response = requests.get(f"{BASE_URL}/assistants/{assistant_id}/files")
files_data = response.json()
print(f"生成的文件列表: {files_data['files']}")

# 5. 结束会话
response = requests.post(f"{BASE_URL}/assistants/{assistant_id}/end-session")
end_data = response.json()
print(f"会话结束结果: {end_data['message']}")
```

### cURL示例

#### 创建助手
```bash
curl -X 'POST' \
  'http://localhost:8000/assistants' \
  -H 'Content-Type: application/json' \
  -d '{
  "name": "MiniLuma助手",
  "provider_name": "openai",
  "model": "gpt-4"
}'
```

#### 发送消息
```bash
curl -X 'POST' \
  'http://localhost:8000/assistants/3fa85f64-5717-4562-b3fc-2c963f66afa6/messages' \
  -H 'Content-Type: application/json' \
  -d '{
  "message": "请帮我写一个Python函数，计算斐波那契数列",
  "add_to_memory": true
}'
```

## 注意事项

1. **对话ID持久性**：MiniLuma API会保持对话ID的持久性，即使在不同请求之间也能保持上下文连续性。对话ID只有在显式调用`end-session`接口时才会重置。

2. **文件存储结构**：所有通过API生成的文件会按照`/results/日期/对话ID/`的结构存储，确保了文件的组织性和可追溯性。

3. **安全性考虑**：
   - API默认没有身份认证机制，如果需要在生产环境使用，请添加适当的身份验证和授权机制。
   - 敏感配置和API密钥不应直接在API请求中传递。

4. **性能注意事项**：
   - 处理大型文件时可能会占用大量内存，请考虑分块处理。
   - 对话生成可能需要一定时间，取决于LLM模型和查询复杂度。

## 版本历史

- v1.0.0 (2025-03-29): 初始版本，提供基本的助手管理、消息处理、文件操作和记忆管理功能。
