"""
Reactor pattern implementation for the MiniLuma.
Inspired by the Reactor pattern used in OpenMinus and similar frameworks.
"""
from typing import Dict, List, Any, Optional, Callable
import json
import inspect

class Reactor:
    """
    Implementation of the Reactor pattern for agent reasoning and action cycles.
    
    The Reactor pattern follows a Reason-Action-Observe cycle where:
    1. The agent receives input and reasons about what to do (think)
    2. The agent selects and executes a tool/action (act)
    3. The agent observes the result and updates its understanding (observe)
    4. The cycle repeats until a final response is ready
    """
    
    def __init__(self, 
                 llm_service,
                 tools: Dict[str, Callable],
                 system_prompt: str = "",
                 max_iterations: int = 10):
        """Initialize the Reactor.
        
        Args:
            llm_service: The language model service to use for reasoning
            tools: A dictionary of tool name to function mapping
            system_prompt: The system prompt to guide agent behavior
            max_iterations: Maximum number of reasoning iterations
        """
        self.llm = llm_service
        self.tools = tools
        self.system_prompt = system_prompt
        self.max_iterations = max_iterations
        self.iteration_history = []
        
        # 添加 logger 属性
        from utils.logger import ConversationLogger
        self.logger = ConversationLogger()
    
    async def process(self, user_input: str) -> Dict[str, Any]:
        """Process a user input through the Reactor cycle.
        
        Args:
            user_input: The user query or instruction
            
        Returns:
            The final result after completing the Reactor cycle
        """
        context = {
            "user_input": user_input,
            "iterations": 0,
            "observations": [],
            "complete": False,
            "final_response": ""
        }
        
        # Reset history for a new session
        self.iteration_history = []
        
        # Begin the Reactor cycle
        while not context["complete"] and context["iterations"] < self.max_iterations:
            # Step 1: Reason about what to do next
            thought = await self._reason(context)
            
            # Step 2: Determine if we need to perform an action or provide a final response
            if thought.get("action_type") == "tool_use":
                # Execute the tool and observe the result
                observation = await self._execute_tool(thought)
                
                # Step 3: Record the observation
                context["observations"].append({
                    "thought": thought,
                    "observation": observation
                })
                
                # Add to history
                self.iteration_history.append({
                    "iteration": context["iterations"],
                    "thought": thought,
                    "observation": observation
                })
            
            elif thought.get("action_type") == "final_response":
                # We have a final response - end the cycle
                context["complete"] = True
                context["final_response"] = thought.get("response", "")
            
            # Increment iteration counter
            context["iterations"] += 1
        
        # If we hit the max iterations without a final response, generate one
        if not context["complete"]:
            context["final_response"] = await self._generate_timeout_response(context)
            context["complete"] = True
        
        return {
            "response": context["final_response"],
            "iterations": context["iterations"],
            "history": self.iteration_history
        }
    
    async def _reason(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """推理阶段，决定下一步的行动。
        
        Args:
            context: 当前处理的上下文
            
        Returns:
            包含推理结果的字典
        """
        # 构建提示语
        prompt = self._build_reasoning_prompt(context)
        
        # 执行LLM调用前的日志记录
        self.logger.debug(f"向LLM发送推理提示: {prompt}")
        
        # 使用系统提示词和用户输入格式调用LLM
        system_prompt = """
你是一个智能助手，帮助用户回答问题并执行任务。你可以使用工具来获取信息和完成任务。
分析用户的需求，并决定是直接回答还是使用工具。

请仔细按照以下流程进行思考:
1. 理解用户的问题或请求
2. 决定是否需要使用工具
3. 如果需要工具，选择最合适的工具并提供准确的参数
4. 如果不需要工具，直接提供最终回答

Your response must be valid JSON with one of these formats:

1. To use a tool:
{
  "action_type": "tool_use",
  "tool_name": "tool_name",
  "tool_params": { parameters for the tool },
  "reasoning": "Your reasoning for using this tool"
}

2. To provide a final answer:
{
  "action_type": "final_response",
  "response": "Your response to the user",
  "reasoning": "Your reasoning for this response"
}
"""
        
        # 确认LLM是否支持异步操作
        if inspect.iscoroutinefunction(self.llm.generate):
            # 异步调用LLM
            llm_response = await self.llm.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
        else:
            # 同步调用LLM
            llm_response = self.llm.generate(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
            
        # 如果响应是协程，等待它完成
        if inspect.iscoroutine(llm_response):
            llm_response = await llm_response
        
        # 提取响应内容
        content = ""
        if isinstance(llm_response, dict):
            choices = llm_response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                content = message.get("content", "")
        
        # 尝试将内容解析为JSON
        try:
            result = json.loads(content)
            self.logger.debug(f"LLM推理结果: {json.dumps(result, ensure_ascii=False)}")
            return result
        except json.JSONDecodeError:
            # 如果不是有效的JSON，构建一个最终回复
            self.logger.debug(f"无法解析LLM响应为JSON，使用原始内容作为最终回复")
            return {
                "action_type": "final_response",
                "response": content,
                "reasoning": "直接返回LLM的响应"
            }
    
    def _build_reasoning_prompt(self, context: Dict[str, Any]) -> str:
        """
        构建用于推理的提示词
        
        Args:
            context: 包含用户输入和观察历史的上下文
            
        Returns:
            格式化的提示词字符串
        """
        # 格式化工具描述
        tool_descriptions = self._format_tool_descriptions()
        # 格式化观察历史
        observation_history = self._format_observation_history(context["observations"])
        
        # 构建提示词
        prompt = f"""
你是一个AI助手，通过Reactor模式处理用户请求。
每次迭代请遵循以下步骤:

1. 分析用户请求和观察历史
2. 决定是:
   a. 使用工具获取更多信息
   b. 提供最终回答
3. 将你的响应格式化为有效的JSON

{tool_descriptions}

用户请求: {context["user_input"]}

迭代历史:
{observation_history}

当前迭代: {context["iterations"] + 1}
"""
        return prompt
    
    async def _execute_tool(self, thought: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool based on the thought.
        
        Args:
            thought: The thought containing tool name and parameters
            
        Returns:
            The result of the tool execution
        """
        # 检查思考中的工具名字段
        # 适配不同的工具字段命名
        if "tool_name" in thought:
            tool_name = thought.get("tool_name", "")
        else:
            tool_name = thought.get("tool", "")
            
        # 适配不同的参数字段命名
        if "tool_params" in thought:
            parameters = thought.get("tool_params", {})
        else:
            parameters = thought.get("parameters", {})
        
        # Check if the tool exists
        if tool_name not in self.tools:
            return {
                "error": f"Tool '{tool_name}' not found",
                "available_tools": list(self.tools.keys())
            }
        
        # Execute the tool
        try:
            tool_function = self.tools[tool_name]
            
            # 检查工具函数是否是异步函数
            import inspect
            if inspect.iscoroutinefunction(tool_function):
                # 异步执行工具函数
                tool_result = await tool_function(**parameters)
            else:
                # 同步执行工具函数
                tool_result = tool_function(**parameters)
                
            # 检查结果是否是协程对象
            if inspect.iscoroutine(tool_result):
                tool_result = await tool_result
            
            return {
                "result": tool_result,
                "success": True
            }
        except Exception as e:
            import traceback
            error_traceback = traceback.format_exc()
            self.logger.debug(f"工具执行错误: {error_traceback}")
            return {
                "error": f"Error executing tool {tool_name}: {str(e)}",
                "success": False
            }
    
    def _format_tool_descriptions(self) -> str:
        """Format tool descriptions for the prompt.
        
        Returns:
            A formatted string describing available tools
        """
        if not self.tools:
            return "No tools available."
        
        tool_info = "Available tools:\n\n"
        
        for name, tool_function in self.tools.items():
            # Get tool description from function docstring
            description = tool_function.__doc__ or "No description available."
            description = description.strip().split('\n')[0]
            
            # Get tool parameters from function signature
            import inspect
            signature = inspect.signature(tool_function)
            params = []
            
            for param_name, param in signature.parameters.items():
                if param.default is param.empty:
                    params.append(f"{param_name} (required)")
                else:
                    params.append(f"{param_name} (optional)")
            
            parameters_str = ", ".join(params)
            
            tool_info += f"- {name}: {description}\n"
            tool_info += f"  Parameters: {parameters_str}\n\n"
        
        return tool_info
    
    def _format_observation_history(self, observations: List[Dict[str, Any]]) -> str:
        """Format observation history for the prompt.
        
        Args:
            observations: List of observations from previous iterations
            
        Returns:
            A formatted string containing the observation history
        """
        if not observations:
            return "No previous observations."
        
        history = ""
        
        for i, obs in enumerate(observations):
            thought = obs["thought"]
            observation = obs["observation"]
            
            # Format thought
            reasoning = thought.get("reasoning", "No reasoning provided")
            
            if thought.get("action_type") == "tool_use":
                tool = thought.get("tool", "unknown_tool")
                parameters = thought.get("parameters", {})
                parameters_str = ", ".join([f"{k}={v}" for k, v in parameters.items()])
                
                history += f"Iteration {i+1}:\n"
                history += f"Reasoning: {reasoning}\n"
                history += f"Action: Use tool '{tool}' with parameters {parameters_str}\n"
            else:
                history += f"Iteration {i+1}:\n"
                history += f"Reasoning: {reasoning}\n"
            
            # Format observation
            if "error" in observation:
                history += f"Result: Error - {observation['error']}\n"
            elif "result" in observation:
                result = observation["result"]
                if isinstance(result, str) and len(result) > 100:
                    result = result[:100] + "..."
                history += f"Result: {result}\n"
            
            history += "\n"
        
        return history
    
    async def _generate_timeout_response(self, context: Dict[str, Any]) -> str:
        """在达到最大迭代次数时生成超时响应。
        
        Args:
            context: 当前处理的上下文
            
        Returns:
            超时响应文本
        """
        prompt = f"""
达到最大迭代次数 ({self.max_iterations})，但仍未生成最终回复。
用户原始输入: {context['user_input']}

已有的观察结果:
{json.dumps(context['observations'], indent=2, ensure_ascii=False)}

基于以上信息，请为用户提供一个有帮助的最终回复。
"""
        
        # 确认LLM是否支持异步操作
        if inspect.iscoroutinefunction(self.llm.generate):
            # 异步调用LLM
            response = await self.llm.generate(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
        else:
            # 同步调用LLM
            response = self.llm.generate(
                messages=[
                    {"role": "system", "content": self.system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1024
            )
            
        # 如果响应是协程，等待它完成
        if inspect.iscoroutine(response):
            response = await response
        
        # 提取响应内容
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices and len(choices) > 0:
                message = choices[0].get("message", {})
                return message.get("content", "很抱歉，我无法完成这个请求。请尝试提供更明确的指令。")
        
        return "很抱歉，我无法完成这个请求。请尝试提供更明确的指令。"
    
    def _summarize_observations(self, observations: List[Dict[str, Any]]) -> str:
        """Summarize observations for a timeout response.
        
        Args:
            observations: List of observations from previous iterations
            
        Returns:
            A summary of what we learned from observations
        """
        if not observations:
            return "I don't have enough information to answer your question yet."
        
        summary = ""
        
        for obs in observations:
            if "observation" in obs and "result" in obs["observation"]:
                result = obs["observation"]["result"]
                if isinstance(result, str):
                    summary += result + " "
        
        if not summary:
            return "I wasn't able to gather the information needed to answer your question."
        
        return summary
