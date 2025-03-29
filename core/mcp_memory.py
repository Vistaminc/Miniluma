"""
MCP增强型记忆系统
为MCP智能体提供长短期记忆管理功能
"""
import os
import json
import time
import datetime
from typing import Dict, List, Any, Optional, Union
import sqlite3
from pathlib import Path

class MCPMemory:
    """
    MCP记忆系统基类
    提供记忆存储和检索的基本接口
    """
    def __init__(self, name: str = "default"):
        """初始化记忆系统
        
        Args:
            name: 记忆系统名称
        """
        self.name = name
    
    async def add(self, content: Any, metadata: Dict = None) -> str:
        """添加记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            
        Returns:
            记忆ID
        """
        raise NotImplementedError
    
    async def get(self, memory_id: str) -> Dict:
        """获取记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆内容和元数据
        """
        raise NotImplementedError
    
    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索记忆
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            匹配的记忆列表
        """
        raise NotImplementedError
    
    async def update(self, memory_id: str, content: Any = None, metadata: Dict = None) -> bool:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新的记忆内容
            metadata: 新的记忆元数据
            
        Returns:
            成功更新返回True，否则False
        """
        raise NotImplementedError
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            成功删除返回True，否则False
        """
        raise NotImplementedError


class SqliteMemory(MCPMemory):
    """
    基于SQLite的记忆系统实现
    
    提供持久化的记忆存储，支持按时间和关键词检索
    """
    
    def __init__(self, name: str = "default", db_path: Optional[str] = None):
        """初始化SQLite记忆系统
        
        Args:
            name: 记忆系统名称
            db_path: 数据库文件路径
        """
        super().__init__(name)
        
        # 设置默认数据库路径
        if not db_path:
            # 在用户主目录的.config目录下创建数据库
            home_dir = os.path.expanduser("~")
            config_dir = os.path.join(home_dir, ".config", "mcp_memory")
            os.makedirs(config_dir, exist_ok=True)
            db_path = os.path.join(config_dir, f"{name}_memory.db")
        
        # 存储数据库路径
        self.db_path = db_path
        
        # 初始化数据库
        self._init_db()
    
    def _init_db(self):
        """初始化数据库表结构"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # 创建记忆表
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memories (
            id TEXT PRIMARY KEY,
            content TEXT,
            metadata TEXT,
            created_at REAL,
            updated_at REAL,
            importance REAL,
            tags TEXT
        )
        ''')
        
        # 创建搜索索引
        cursor.execute('''
        CREATE VIRTUAL TABLE IF NOT EXISTS memory_index 
        USING fts5(id, content, tags)
        ''')
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def generate_memory_id(content: Any) -> str:
        """生成记忆ID
        
        Args:
            content: 记忆内容
            
        Returns:
            生成的记忆ID
        """
        # 生成记忆ID格式: mem_timestamp_contenthash
        memory_id = f"mem_{int(time.time())}_{hash(str(content))}"
        return memory_id
    
    async def add(self, content: Any, metadata: Dict = None) -> str:
        """添加新记忆
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            
        Returns:
            记忆ID
        """
        # 生成记忆ID
        memory_id = self.generate_memory_id(content)
        
        # 处理元数据
        if not metadata:
            metadata = {}
        
        # 添加默认元数据字段
        metadata["created_at"] = time.time()
        metadata["updated_at"] = time.time()
        
        # 提取标签
        tags = metadata.get("tags", [])
        if isinstance(tags, list):
            tags = " ".join(tags)
        
        # 存储内容
        if not isinstance(content, str):
            content = json.dumps(content)
        
        # 将同步数据库操作包装在异步函数中执行
        def _db_operation():
            # 连接数据库
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 插入记忆
                cursor.execute(
                    '''
                    INSERT INTO memories 
                    (id, content, metadata, created_at, updated_at, importance, tags) 
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''',
                    (
                        memory_id, 
                        content, 
                        json.dumps(metadata),
                        metadata["created_at"],
                        metadata["updated_at"],
                        metadata.get("importance", 0.5),
                        tags
                    )
                )
                
                # 更新搜索索引
                cursor.execute(
                    '''
                    INSERT INTO memory_index
                    (id, content, tags)
                    VALUES (?, ?, ?)
                    ''',
                    (memory_id, content, tags)
                )
                
                # 提交事务
                conn.commit()
                
                return memory_id
            except Exception as e:
                conn.rollback()
                raise e
            finally:
                conn.close()
        
        # 使用异步运行器执行数据库操作
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)
    
    async def get(self, memory_id: str) -> Dict:
        """获取记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆内容和元数据
        """
        def _db_operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 查询记忆
                cursor.execute(
                    '''
                    SELECT content, metadata, created_at, updated_at, importance, tags
                    FROM memories
                    WHERE id = ?
                    ''',
                    (memory_id,)
                )
                
                result = cursor.fetchone()
                
                if not result:
                    return None
                    
                content, metadata_str, created_at, updated_at, importance, tags = result
                metadata = json.loads(metadata_str)
                
                return {
                    "id": memory_id,
                    "content": content,
                    "metadata": metadata,
                    "created_at": created_at,
                    "updated_at": updated_at,
                    "importance": importance,
                    "tags": tags.split(" ") if tags else []
                }
                
            finally:
                conn.close()
                
        # 使用异步运行器执行数据库操作
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)
        
    async def search(self, query: str, limit: int = 5) -> List[Dict]:
        """搜索记忆
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            匹配的记忆列表
        """
        def _db_operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 搜索记忆
                cursor.execute(
                    '''
                    SELECT m.id, m.content, m.metadata, m.created_at, m.updated_at, m.importance, m.tags
                    FROM memory_index i
                    JOIN memories m ON i.id = m.id
                    WHERE i.content MATCH ?
                    ORDER BY m.importance DESC, m.updated_at DESC
                    LIMIT ?
                    ''',
                    (query, limit)
                )
                
                results = cursor.fetchall()
                memories = []
                
                for row in results:
                    memory_id, content, metadata_str, created_at, updated_at, importance, tags = row
                    metadata = json.loads(metadata_str)
                    
                    memories.append({
                        "id": memory_id,
                        "content": content,
                        "metadata": metadata,
                        "created_at": created_at,
                        "updated_at": updated_at,
                        "importance": importance,
                        "tags": tags.split(" ") if tags else []
                    })
                    
                return memories
                
            finally:
                conn.close()
                
        # 使用异步运行器执行数据库操作
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)
        
    async def update(self, memory_id: str, content: Any = None, metadata: Dict = None) -> bool:
        """更新记忆
        
        Args:
            memory_id: 记忆ID
            content: 新内容
            metadata: 新元数据
            
        Returns:
            更新是否成功
        """
        def _db_operation():
            # 获取现有记忆
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 查询现有记忆
                cursor.execute(
                    '''
                    SELECT content, metadata
                    FROM memories
                    WHERE id = ?
                    ''',
                    (memory_id,)
                )
                
                result = cursor.fetchone()
                
                if not result:
                    return False
                    
                old_content, old_metadata_str = result
                old_metadata = json.loads(old_metadata_str)
                
                # 准备更新数据
                new_content = content if content is not None else old_content
                
                if not isinstance(new_content, str):
                    new_content = json.dumps(new_content)
                    
                new_metadata = old_metadata.copy()
                if metadata:
                    new_metadata.update(metadata)
                    
                # 更新时间戳
                new_metadata["updated_at"] = time.time()
                
                # 提取标签
                tags = new_metadata.get("tags", [])
                if isinstance(tags, list):
                    tags = " ".join(tags)
                
                # 执行更新
                cursor.execute(
                    '''
                    UPDATE memories
                    SET content = ?, metadata = ?, updated_at = ?, tags = ?
                    WHERE id = ?
                    ''',
                    (
                        new_content,
                        json.dumps(new_metadata),
                        new_metadata["updated_at"],
                        tags,
                        memory_id
                    )
                )
                
                # 更新搜索索引
                cursor.execute(
                    '''
                    DELETE FROM memory_index
                    WHERE id = ?
                    ''',
                    (memory_id,)
                )
                
                cursor.execute(
                    '''
                    INSERT INTO memory_index
                    (id, content, tags)
                    VALUES (?, ?, ?)
                    ''',
                    (memory_id, new_content, tags)
                )
                
                conn.commit()
                return True
                
            except Exception as e:
                conn.rollback()
                raise e
                
            finally:
                conn.close()
                
        # 使用异步运行器执行数据库操作
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)
    
    async def delete(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            是否成功删除
        """
        def _db_operation():
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            try:
                # 删除记忆
                cursor.execute(
                    "DELETE FROM memories WHERE id = ?",
                    (memory_id,)
                )
                
                # 删除索引
                cursor.execute(
                    "DELETE FROM memory_index WHERE id = ?",
                    (memory_id,)
                )
                
                conn.commit()
                return cursor.rowcount > 0
                
            except Exception as e:
                conn.rollback()
                raise e
                
            finally:
                conn.close()
                
        # 使用异步运行器执行数据库操作
        import asyncio
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, _db_operation)


class MCPMemoryManager:
    """
    MCP记忆管理器
    
    集中管理短期和长期记忆，提供智能检索和记忆重要性评估
    """
    
    def __init__(self, 
                agent_name: str = "default",
                db_path: Optional[str] = None,
                llm_service = None):
        """初始化记忆管理器
        
        Args:
            agent_name: 智能体名称
            db_path: 数据库路径
            llm_service: 语言模型服务，用于记忆重要性评估
        """
        self.agent_name = agent_name
        
        # 创建长期记忆存储
        self.long_term_memory = SqliteMemory(
            name=f"{agent_name}_long_term",
            db_path=db_path
        )
        
        # 短期记忆（工作记忆）
        self.working_memory = []
        self.working_memory_capacity = 10
        
        # LLM服务
        self.llm_service = llm_service
    
    async def remember(self, 
                    content: Any, 
                    metadata: Dict = None, 
                    long_term: bool = False,
                    importance: Optional[float] = None) -> str:
        """记忆新信息
        
        Args:
            content: 记忆内容
            metadata: 记忆元数据
            long_term: 是否存入长期记忆
            importance: 记忆重要性 (0.0-1.0)
            
        Returns:
            记忆ID
        """
        if not metadata:
            metadata = {}
        
        # 添加时间戳
        metadata["timestamp"] = time.time()
        
        # 评估记忆重要性
        if importance is None and self.llm_service:
            importance = await self._evaluate_importance(content)
        
        if importance is not None:
            metadata["importance"] = importance
        
        # 存入长期记忆
        if long_term or (importance is not None and importance > 0.7):
            return await self.long_term_memory.add(content, metadata)
        
        # 存入工作记忆
        memory_id = f"wm_{int(time.time())}_{hash(str(content))}"
        self.working_memory.append({
            "id": memory_id,
            "content": content,
            "metadata": metadata
        })
        
        # 限制工作记忆容量
        if len(self.working_memory) > self.working_memory_capacity:
            # 移除最旧或最不重要的记忆
            self.working_memory.sort(
                key=lambda x: x["metadata"].get("importance", 0) * 10 + 
                              x["metadata"].get("timestamp", 0)
            )
            self.working_memory.pop(0)
        
        return memory_id
    
    async def retrieve(self, query: str, limit: int = 5) -> List[Dict]:
        """检索相关记忆
        
        Args:
            query: 搜索查询
            limit: 返回结果数量限制
            
        Returns:
            相关记忆列表
        """
        # 从长期记忆中搜索
        long_term_results = await self.long_term_memory.search(query, limit)
        
        # 从工作记忆中查找匹配项
        working_memory_results = []
        for memory in self.working_memory:
            # 简单文本匹配
            content_str = str(memory["content"])
            if query.lower() in content_str.lower():
                working_memory_results.append(memory)
        
        # 合并结果并去重
        all_results = []
        seen_ids = set()
        
        # 先添加工作记忆结果
        for memory in working_memory_results:
            if memory["id"] not in seen_ids:
                all_results.append(memory)
                seen_ids.add(memory["id"])
        
        # 再添加长期记忆结果
        for memory in long_term_results:
            if memory["id"] not in seen_ids:
                all_results.append(memory)
                seen_ids.add(memory["id"])
        
        # 按重要性和时间排序
        all_results.sort(
            key=lambda x: (
                x["metadata"].get("importance", 0.5) * 10 +
                x["metadata"].get("timestamp", 0) / 1e10
            ),
            reverse=True
        )
        
        # 限制返回数量
        return all_results[:limit]
    
    async def get_memory(self, memory_id: str) -> Dict:
        """获取指定记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            记忆内容
        """
        # 检查工作记忆
        for memory in self.working_memory:
            if memory["id"] == memory_id:
                return memory
        
        # 检查长期记忆
        return await self.long_term_memory.get(memory_id)
    
    async def forget(self, memory_id: str) -> bool:
        """删除记忆
        
        Args:
            memory_id: 记忆ID
            
        Returns:
            成功删除返回True，否则False
        """
        # 检查工作记忆
        for i, memory in enumerate(self.working_memory):
            if memory["id"] == memory_id:
                self.working_memory.pop(i)
                return True
        
        # 检查长期记忆
        return await self.long_term_memory.delete(memory_id)
    
    async def consolidate(self):
        """
        将工作记忆中的重要信息整合到长期记忆中
        """
        for memory in self.working_memory[:]:
            importance = memory["metadata"].get("importance", 0)
            
            # 重要记忆移入长期存储
            if importance > 0.5:
                await self.long_term_memory.add(
                    memory["content"],
                    memory["metadata"]
                )
                self.working_memory.remove(memory)
    
    async def _evaluate_importance(self, content: Any) -> float:
        """评估记忆重要性
        
        使用LLM评估记忆的重要性
        
        Args:
            content: 记忆内容
            
        Returns:
            重要性评分 (0.0-1.0)
        """
        if not self.llm_service:
            return 0.5
        
        # 准备评估提示
        content_str = str(content)
        prompt = f"""评估以下信息对AI智能体的重要性。
考虑以下因素：
1. 信息的独特性和新颖性
2. 信息的持久价值
3. 信息中的关键指令或偏好
4. 与用户目标的相关性

评估对象：
"{content_str}"

请仅返回一个0到1之间的小数，表示重要性评分。
0表示完全不重要，1表示极其重要。不要提供其他解释。
"""
        
        try:
            response = await self.llm_service.generate(
                messages=[
                    {"role": "system", "content": "你是一个专业的记忆评估系统，专门评估信息的重要性。"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=10
            )
            
            # 提取重要性评分
            importance_text = response.get("content", "0.5").strip()
            
            # 提取数字
            import re
            match = re.search(r'([0-9]*[.])?[0-9]+', importance_text)
            if match:
                importance = float(match.group())
                # 确保在0-1范围内
                return max(0.0, min(1.0, importance))
            
            return 0.5
        
        except Exception:
            # 出错时返回默认值
            return 0.5
