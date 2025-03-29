"""
Task planning module for the MiniLuma.
Provides functionality for breaking down complex tasks and planning execution.
Inspired by both OWL and OpenMinus planning approaches.
"""
from typing import Dict, List, Any, Optional
import json
import inspect

class TaskPlanner:
    """Handles task decomposition and planning for complex operations.
    
    Creates structured plans for breaking down complex user requests
    into smaller, manageable subtasks for agent execution.
    """
    
    def __init__(self, llm_service, system_prompt: str = ""):
        """Initialize the task planner.
        
        Args:
            llm_service: The language model service to use for planning
            system_prompt: Optional system prompt to guide planning behavior
        """
        self.llm = llm_service
        self.system_prompt = system_prompt or self._get_default_system_prompt()
    
    def create_plan(self, task_description: str, agent_capabilities: List[Dict] = None) -> Dict[str, Any]:
        """Create an execution plan for a complex task.
        
        Args:
            task_description: The description of the task to plan
            agent_capabilities: Optional list of available agent capabilities
            
        Returns:
            A structured plan with steps for execution
        """
        capabilities_str = self._format_capabilities(agent_capabilities) if agent_capabilities else ""
        
        # 获取有效的代理名列表
        valid_agents = []
        if agent_capabilities:
            valid_agents = [agent.get("name") for agent in agent_capabilities if "name" in agent]
        
        valid_agents_str = ", ".join(valid_agents) if valid_agents else "none"
        
        prompt = f"""
# Task Planning Request

## Task Description
{task_description}

{capabilities_str}

## Available Agents
IMPORTANT: You MUST ONLY use the following agents in your plan: {valid_agents_str}
Do NOT specify any other agent names that are not in this list.

## Planning Instructions
1. Analyze the task to understand the requirements and constraints
2. Break down the task into sequential, logical steps
3. For each step, specify:
   - The specific subtask to accomplish
   - Which agent should handle it (ONLY use agents from the Available Agents list: {valid_agents_str})
   - The expected output of the step
4. Ensure the steps are ordered correctly with dependencies resolved
5. Consider error handling and alternative paths where appropriate

## Output Format
Provide your plan as a structured JSON object with the following format:

```json
{{
  "task": "original task description",
  "analysis": "your analysis of the task",
  "steps": [
    {{
      "id": 1,
      "agent": "agent_name",  # MUST be one of: {valid_agents_str}
      "task": "specific subtask description",
      "expected_output": "what this step should produce",
      "dependencies": [list of step IDs this step depends on]
    }},
    ...more steps...
  ],
  "success_criteria": "how to determine if the task is complete"
}}
```

Please ensure your plan is comprehensive, logical, and follows the required JSON structure.
CRITICAL: All agent names MUST be from this list: {valid_agents_str}
"""
        
        # Generate the plan using the LLM
        response_obj = self.llm.generate(
            system_prompt=self.system_prompt,
            user_input=prompt
        )
        
        # 确保响应是字符串类型
        plan_text = response_obj.get("response", "")
        if isinstance(plan_text, dict) and "response" in plan_text:
            plan_text = plan_text["response"]
        
        # Extract and parse JSON from the response
        try:
            # Try to extract JSON using a regex pattern in case LLM adds extra text
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', plan_text, re.DOTALL)
            
            if json_match:
                plan = json.loads(json_match.group(1))
            else:
                # If no JSON code block, try parsing the whole response
                plan = json.loads(plan_text)
                
            return plan
            
        except (json.JSONDecodeError, AttributeError):
            # Fallback to a simple plan structure if JSON parsing fails
            return {
                "task": task_description,
                "analysis": "Failed to generate structured plan",
                "steps": [
                    {
                        "id": 1,
                        "agent": "default",
                        "task": task_description,
                        "expected_output": "Task result",
                        "dependencies": []
                    }
                ],
                "success_criteria": "Task is completed successfully"
            }
    
    async def generate_plan(self, task_description: str, agent_capabilities: List[Dict] = None) -> Dict[str, Any]:
        """异步版本：Create an execution plan for a complex task.
        
        Args:
            task_description: The description of the task to plan
            agent_capabilities: Optional list of available agent capabilities
            
        Returns:
            A structured plan with steps for execution
        """
        import inspect
        
        capabilities_str = self._format_capabilities(agent_capabilities) if agent_capabilities else ""
        
        # 获取有效的代理名列表
        valid_agents = []
        if agent_capabilities:
            valid_agents = [agent.get("name") for agent in agent_capabilities if "name" in agent]
        
        valid_agents_str = ", ".join(valid_agents) if valid_agents else "none"
        
        prompt = f"""
# Task Planning Request

## Task Description
{task_description}

{capabilities_str}

## Available Agents
IMPORTANT: You MUST ONLY use the following agents in your plan: {valid_agents_str}
Do NOT specify any other agent names that are not in this list.

## Planning Instructions
1. Analyze the task to understand the requirements and constraints
2. Break down the task into sequential, logical steps
3. For each step, specify:
   - The specific subtask to accomplish
   - Which agent should handle it (ONLY use agents from the Available Agents list: {valid_agents_str})
   - The expected output of the step
4. Ensure the steps are ordered correctly with dependencies resolved
5. Consider error handling and alternative paths where appropriate

## Output Format
Provide your plan as a structured JSON object with the following format:

```json
{{
  "task": "original task description",
  "analysis": "your analysis of the task",
  "steps": [
    {{
      "id": 1,
      "agent": "agent_name",  # MUST be one of: {valid_agents_str}
      "task": "specific subtask description",
      "expected_output": "what this step should produce",
      "dependencies": [list of step IDs this step depends on]
    }},
    ...more steps...
  ],
  "success_criteria": "how to determine if the task is complete"
}}
```

Please ensure your plan is comprehensive, logical, and follows the required JSON structure.
CRITICAL: All agent names MUST be from this list: {valid_agents_str}
"""
        
        # 检查LLM的generate方法是否是异步的
        if inspect.iscoroutinefunction(self.llm.generate):
            response_obj = await self.llm.generate(
                system_prompt=self.system_prompt,
                user_input=prompt
            )
        else:
            # 同步调用LLM
            response_obj = self.llm.generate(
                system_prompt=self.system_prompt,
                user_input=prompt
            )
            
        # 检查结果是否是协程
        if inspect.iscoroutine(response_obj):
            response_obj = await response_obj
        
        # 确保响应是字符串类型
        plan_text = response_obj.get("response", "")
        if isinstance(plan_text, dict) and "response" in plan_text:
            plan_text = plan_text["response"]
            
        # 尝试提取subtasks结构
        try:
            # 先尝试解析完整的JSON计划
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', plan_text, re.DOTALL)
            
            if json_match:
                plan = json.loads(json_match.group(1))
            else:
                # 如果没有JSON代码块，尝试解析整个响应
                plan = json.loads(plan_text)
            
            # 检查是否有完整的步骤结构    
            if "steps" in plan:
                # 为了兼容旧结构，将steps转换为subtasks
                subtasks = []
                for step in plan["steps"]:
                    subtask = {
                        "id": step.get("id", 0),
                        "agent": step.get("agent", "default"),
                        "description": step.get("task", ""),
                        "expected_output": step.get("expected_output", ""),
                        "dependencies": step.get("dependencies", [])
                    }
                    subtasks.append(subtask)
                
                plan["subtasks"] = subtasks
            
            return plan
            
        except (json.JSONDecodeError, AttributeError) as e:
            # 如果JSON解析失败，返回一个简单的计划结构
            print(f"计划解析错误: {str(e)}")
            return {
                "task": task_description,
                "analysis": "Failed to generate structured plan",
                "subtasks": [
                    {
                        "id": 1,
                        "agent": "default",
                        "description": task_description,
                        "expected_output": "Task result",
                        "dependencies": []
                    }
                ],
                "success_criteria": "Task is completed successfully"
            }
    
    def revise_plan(self, original_plan: Dict[str, Any], execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Revise a plan based on execution results and failures.
        
        Args:
            original_plan: The original execution plan
            execution_results: Results from executed steps, including any failures
            
        Returns:
            A revised plan with adjusted steps
        """
        # Format the execution results
        results_str = self._format_execution_results(execution_results)
        
        prompt = f"""
# Plan Revision Request

## Original Plan
```json
{json.dumps(original_plan, indent=2)}
```

## Execution Results
{results_str}

## Revision Instructions
1. Analyze the execution results, especially any failures or unexpected outcomes
2. Identify steps that need to be modified, replaced, or added
3. Create a revised plan that addresses the issues encountered
4. Ensure the revised plan maintains the original task goals

## Output Format
Provide your revised plan as a structured JSON object with the following format:

```json
{{
  "task": "original task description",
  "analysis": "your analysis of the execution results and needed changes",
  "steps": [
    {{
      "id": 1,
      "agent": "agent_name",
      "task": "specific subtask description",
      "expected_output": "what this step should produce",
      "dependencies": [list of step IDs this step depends on]
    }},
    ...more steps...
  ],
  "success_criteria": "how to determine if the task is complete"
}}
```
"""
        
        # Generate the revised plan using the LLM
        response_obj = self.llm.generate(
            system_prompt=self.system_prompt,
            user_input=prompt
        )
        
        # 确保响应是字符串类型
        revised_plan_text = response_obj.get("response", "")
        if isinstance(revised_plan_text, dict) and "response" in revised_plan_text:
            revised_plan_text = revised_plan_text["response"]
        
        # Extract and parse JSON from the response
        try:
            # Try to extract JSON using a regex pattern
            import re
            json_match = re.search(r'```json\s*(.*?)\s*```', revised_plan_text, re.DOTALL)
            
            if json_match:
                revised_plan = json.loads(json_match.group(1))
            else:
                # If no JSON code block, try parsing the whole response
                revised_plan = json.loads(revised_plan_text)
                
            return revised_plan
            
        except (json.JSONDecodeError, AttributeError):
            # If parsing fails, make minimal adjustments to the original plan
            return self._create_fallback_revision(original_plan, execution_results)
    
    def _format_capabilities(self, capabilities: List[Dict]) -> str:
        """Format agent capabilities for inclusion in the prompt.
        
        Args:
            capabilities: List of agent capability dictionaries
            
        Returns:
            Formatted string of agent capabilities
        """
        if not capabilities:
            return ""
        
        formatted = "## Available Agents and Capabilities\n"
        for cap in capabilities:
            formatted += f"- **{cap['name']}**: {cap['description']}\n"
            if 'tools' in cap and cap['tools']:
                formatted += "  - Tools:\n"
                for tool in cap['tools']:
                    formatted += f"    - {tool['name']}: {tool['description']}\n"
            formatted += "\n"
        
        return formatted
    
    def _format_execution_results(self, results: List[Dict[str, Any]]) -> str:
        """Format execution results for inclusion in the prompt.
        
        Args:
            results: List of execution result dictionaries
            
        Returns:
            Formatted string of execution results
        """
        if not results:
            return "No execution results available."
        
        formatted = "### Step Execution Results\n"
        for result in results:
            step_id = result.get("step_id", "unknown")
            status = result.get("status", "unknown")
            output = result.get("output", "No output")
            error = result.get("error", "")
            
            formatted += f"**Step {step_id}**\n"
            formatted += f"- Status: {status}\n"
            if error:
                formatted += f"- Error: {error}\n"
            formatted += f"- Output: {output}\n\n"
        
        return formatted
    
    def _create_fallback_revision(self, original_plan: Dict[str, Any], execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Create a simple fallback revision when JSON parsing fails.
        
        Args:
            original_plan: The original execution plan
            execution_results: Results from executed steps
            
        Returns:
            A minimally revised plan
        """
        # Copy the original plan
        revised_plan = original_plan.copy()
        
        # Add failed step indicators
        failed_steps = []
        for result in execution_results:
            if result.get("status") == "failed":
                failed_steps.append(result.get("step_id"))
        
        # Add analysis of failures
        revised_plan["analysis"] = f"Revised plan due to failures in steps: {', '.join(map(str, failed_steps))}"
        
        return revised_plan
    
    def _get_default_system_prompt(self) -> str:
        """Get the default system prompt for the planner.
        
        Returns:
            Default system prompt
        """
        return """You are an AI Task Planner specialized in breaking down complex tasks into manageable steps.
Your role is to analyze user tasks, create logical execution plans, and assign steps to the most appropriate agents.
Your plans should be comprehensive, well-structured, and follow the JSON format exactly as specified."""
