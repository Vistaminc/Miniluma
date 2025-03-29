"""
基于MCP的多智能体系统
整合OWL和OpenManus的先进特性，实现智能体间的协作
"""
import os
import json
import asyncio
from typing import Dict, List, Any, Optional, Union, Callable

from .mcp import MCPMessage, MCPTool, MCPToolKit
from .mcp_agent import MCPAgent

class TaskPlanner:
    """
    任务规划器
    负责分解复杂任务并生成执行计划
    """
    def __init__(self, llm_service, system_prompt: Optional[str] = None):
        """初始化任务规划器
        
        Args:
            llm_service: 语言模型服务
            system_prompt: 规划器的系统提示
        """
        self.llm = llm_service
        
        # 设置默认系统提示
        if not system_prompt:
            system_prompt = """你是一个专业的任务规划专家。你的任务是：
1. 分析用户的复杂请求
2. 将其分解为可管理的子任务
3. 确定每个子任务的最佳执行顺序
4. 指定处理每个子任务的智能体角色
5. 考虑任务间的依赖关系

请输出JSON格式的计划，包含task_id、description、agent_role和dependencies字段。
确保计划是完整的、逻辑清晰的，并能有效解决用户的请求。"""
        
        self.system_prompt = system_prompt
    
    async def create_plan(self, task_description: str) -> Dict[str, Any]:
        """创建任务执行计划
        
        Args:
            task_description: 任务描述
            
        Returns:
            任务计划
        """
        # 构建提示
        prompt = f"""请为以下任务创建一个执行计划：

任务: {task_description}

请分析此任务，将其分解为多个子任务，并为每个子任务指定合适的智能体角色。
输出格式应为JSON，包含以下结构:
{{
  "plan_name": "计划名称",
  "overall_goal": "总体目标描述",
  "tasks": [
    {{
      "task_id": "task_1",
      "description": "子任务描述",
      "agent_role": "执行此任务的智能体角色",
      "dependencies": ["依赖的任务ID列表，可为空"]
    }},
    ...更多子任务
  ]
}}

确保你的计划是完整的、逻辑清晰的，并能有效解决用户的请求。
"""
        
        # 调用LLM生成计划
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": prompt}
        ]
        
        response = await self.llm.generate(
            messages=messages,
            max_tokens=2048
        )
        
        # 解析JSON计划
        plan_text = response.get("content", "")
        try:
            # 提取JSON部分
            import re
            json_match = re.search(r'```json\n([\s\S]*?)\n```', plan_text)
            if json_match:
                plan_json = json_match.group(1)
            else:
                # 尝试直接解析
                plan_json = plan_text
                
            plan = json.loads(plan_json)
            return plan
        except json.JSONDecodeError:
            # 如果解析失败，返回原始文本
            return {
                "plan_name": "解析错误的计划",
                "overall_goal": task_description,
                "error": "无法解析计划JSON",
                "raw_response": plan_text,
                "tasks": [
                    {
                        "task_id": "task_1",
                        "description": task_description,
                        "agent_role": "general",
                        "dependencies": []
                    }
                ]
            }

class MCPSystem:
    """
    基于MCP的多智能体系统
    实现OWL框架的多智能体协作能力
    """
    def __init__(self, 
                llm_service,
                tools: Optional[List[Union[MCPTool, Callable]]] = None,
                agent_roles: Optional[Dict[str, str]] = None,
                max_iterations: int = 10):
        """初始化MCP系统
        
        Args:
            llm_service: 语言模型服务
            tools: 可用工具列表
            agent_roles: 智能体角色定义 {角色名: 系统提示}
            max_iterations: 最大迭代次数
        """
        self.llm = llm_service
        self.tools = tools or []
        self.task_planner = TaskPlanner(llm_service)
        self.max_iterations = max_iterations
        
        # 设置默认角色
        if not agent_roles:
            agent_roles = {
                "coordinator": "你是一个协调者，负责整合各个专家的工作成果，确保任务顺利完成。",
                "researcher": "你是一个研究专家，擅长收集和分析信息。",
                "coder": "你是一个编程专家，擅长编写和调试代码。",
                "writer": "你是一个写作专家，擅长撰写各类文档和内容。",
                "general": "你是一个多领域专家，可以处理各种通用任务。"
            }
        self.agent_roles = agent_roles
        
        # 智能体实例池
        self.agents: Dict[str, MCPAgent] = {}
        
        # 创建基础智能体
        self._create_base_agents()
        
        # 任务执行状态
        self.execution_state = {
            "current_plan": None,
            "completed_tasks": [],
            "pending_tasks": [],
            "results": {},
            "status": "idle"
        }
    
    def _create_base_agents(self):
        """创建基础智能体"""
        for role, prompt in self.agent_roles.items():
            agent = MCPAgent(
                name=role,
                llm_service=self.llm,
                tools=self.tools,
                system_prompt=prompt
            )
            self.agents[role] = agent
    
    def _can_execute_task(self, task: Dict[str, Any]) -> bool:
        """检查任务是否可以执行"""
        # 检查依赖
        dependencies = task.get("dependencies", [])
        return all(dep in self.execution_state["completed_tasks"] for dep in dependencies)
    
    def _get_next_tasks(self) -> List[Dict[str, Any]]:
        """获取下一批可执行的任务"""
        plan = self.execution_state["current_plan"]
        if not plan:
            return []
            
        tasks = plan.get("tasks", [])
        next_tasks = []
        
        for task in tasks:
            task_id = task.get("task_id")
            if (task_id not in self.execution_state["completed_tasks"] and 
                task_id not in self.execution_state["pending_tasks"] and
                self._can_execute_task(task)):
                next_tasks.append(task)
                
        return next_tasks
    
    async def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """执行单个任务
        
        Args:
            task: 任务描述
            
        Returns:
            任务执行结果
        """
        task_id = task.get("task_id")
        description = task.get("description")
        role = task.get("agent_role")
        
        # 获取合适的智能体
        agent = self.agents.get(role)
        if not agent:
            # 如果没有找到对应角色的智能体，使用通用智能体
            agent = self.agents.get("general")
        
        # 构建任务上下文
        context = {}
        dependencies = task.get("dependencies", [])
        if dependencies:
            context["previous_results"] = {}
            for dep in dependencies:
                if dep in self.execution_state["results"]:
                    context["previous_results"][dep] = self.execution_state["results"][dep]
        
        # 构建提示
        prompt = f"""任务ID: {task_id}
任务描述: {description}

"""
        if context.get("previous_results"):
            prompt += "以下是依赖任务的结果：\n"
            for dep, result in context["previous_results"].items():
                prompt += f"任务 {dep} 结果:\n{result}\n\n"
        
        prompt += "请执行此任务并提供结果。"
        
        # 标记为正在执行
        self.execution_state["pending_tasks"].append(task_id)
        
        # 执行任务
        result = await agent.process(prompt)
        
        # 更新执行状态
        self.execution_state["pending_tasks"].remove(task_id)
        self.execution_state["completed_tasks"].append(task_id)
        self.execution_state["results"][task_id] = result
        
        return {
            "task_id": task_id,
            "result": result
        }
    
    async def process(self, task_description: str) -> Dict[str, Any]:
        """处理复杂任务
        
        Args:
            task_description: 任务描述
            
        Returns:
            处理结果
        """
        # 创建执行计划
        plan = await self.task_planner.create_plan(task_description)
        
        # 初始化执行状态
        self.execution_state = {
            "current_plan": plan,
            "completed_tasks": [],
            "pending_tasks": [],
            "results": {},
            "status": "in_progress"
        }
        
        # 执行循环
        iteration = 0
        while iteration < self.max_iterations:
            # 获取下一批任务
            next_tasks = self._get_next_tasks()
            
            # 如果没有更多任务，说明已完成或陷入死锁
            if not next_tasks:
                # 检查是否所有任务都已完成
                all_task_ids = [task.get("task_id") for task in plan.get("tasks", [])]
                if all(task_id in self.execution_state["completed_tasks"] for task_id in all_task_ids):
                    self.execution_state["status"] = "completed"
                    break
                else:
                    # 可能存在死锁或依赖错误
                    self.execution_state["status"] = "blocked"
                    break
            
            # 并行执行任务
            tasks_futures = [self.execute_task(task) for task in next_tasks]
            await asyncio.gather(*tasks_futures)
            
            iteration += 1
        
        # 生成最终结果
        if self.execution_state["status"] == "completed":
            # 让协调者生成总结
            coordinator = self.agents.get("coordinator")
            if coordinator:
                summary_prompt = f"""以下是完成的任务及其结果:

{json.dumps(self.execution_state["results"], indent=2, ensure_ascii=False)}

请根据以上结果，为用户提供一个清晰、全面的总结，解答他们的原始请求：
{task_description}
"""
                final_summary = await coordinator.process(summary_prompt)
                return {
                    "status": "success",
                    "summary": final_summary,
                    "plan": plan,
                    "results": self.execution_state["results"]
                }
            
        # 如果没有完成或没有协调者
        return {
            "status": self.execution_state["status"],
            "plan": plan,
            "completed_tasks": self.execution_state["completed_tasks"],
            "results": self.execution_state["results"]
        }
