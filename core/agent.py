"""
Base Agent implementation for the MiniLuma.
Provides core functionality for building intelligent agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Callable

from .context import Context
from .memory import Memory

class BaseAgent(ABC):
    """Base class for all agents in the framework.
    
    All agent implementations should inherit from this class
    and implement the think() and act() methods.
    """
    
    def __init__(self, name: str, memory: Optional[Memory] = None):
        """Initialize the base agent.
        
        Args:
            name: A unique identifier for the agent
            memory: Optional memory object for the agent, will create a new one if None
        """
        self.name = name
        self.memory = memory or Memory()
        self.context = Context()
    
    @abstractmethod
    def think(self, input_data: Any) -> Dict:
        """Process input data and decide on the next action.
        
        This method should implement the agent's reasoning process.
        
        Args:
            input_data: The input data to process (e.g. user query, system state)
            
        Returns:
            A dictionary containing the agent's thought process and decision
        """
        pass
    
    @abstractmethod
    def act(self, thought: Dict) -> Any:
        """Execute the action based on the thinking process.
        
        Args:
            thought: The output from the think() method
            
        Returns:
            The result of the action (can be any type)
        """
        pass
    
    def run(self, input_data: Any) -> Any:
        """Run a complete thinking and acting cycle.
        
        Args:
            input_data: The input data to process
            
        Returns:
            The result of the action
        """
        thought = self.think(input_data)
        result = self.act(thought)
        self.memory.update(thought, result)
        return result


class ReactorAgent(BaseAgent):
    """Agent implementation based on the Reactor pattern.
    
    Uses an LLM to determine which tools to use based on input,
    then executes the selected tool and returns the result.
    """
    
    def __init__(self, name: str, tools: List, llm_service, system_prompt: str = ""):
        """Initialize a ReactorAgent.
        
        Args:
            name: A unique identifier for the agent
            tools: A list of Tool objects that the agent can use
            llm_service: A language model service for agent reasoning
            system_prompt: Optional system prompt to guide agent behavior
        """
        super().__init__(name)
        self.tools = {tool.name: tool for tool in tools}
        self.llm = llm_service
        
        if system_prompt:
            self.context.set_system_prompt(system_prompt)
    
    def think(self, user_input: str) -> Dict:
        """Process the user input using an LLM and determine which tool to use.
        
        Args:
            user_input: The user query or input
            
        Returns:
            A dictionary containing the tool to use and its parameters
        """
        context = self.context.get_prompt_context()
        
        # Convert tools to the format expected by the LLM
        tool_schemas = [tool.get_schema() for tool in self.tools.values()]
        
        # Generate a response with tool choices
        response = self.llm.generate_with_tools(
            system_prompt=context["system"],
            user_input=user_input,
            tools=tool_schemas,
            context=context["history"]
        )
        
        # Save the user input and LLM response to history
        self.context.add_message("user", user_input)
        
        # If there's a content response, save it
        if response.get("content"):
            self.context.add_message("assistant", response["content"])
        
        # Parse the LLM response to extract tool call information
        return self._parse_tool_calls(response)
    
    def _parse_tool_calls(self, response: Dict) -> Dict:
        """Extract tool call information from the LLM response.
        
        Args:
            response: The LLM response containing tool call information
            
        Returns:
            A dictionary with tool name and arguments
        """
        tool_calls = response.get("tool_calls", [])
        
        if not tool_calls:
            return {"type": "response", "content": response.get("content", "")}
        
        # Get the first tool call (we'll handle only one at a time for simplicity)
        tool_call = tool_calls[0]
        
        return {
            "type": "tool_call",
            "tool": tool_call.get("name"),
            "args": tool_call.get("arguments", {})
        }
    
    def act(self, thought: Dict) -> Any:
        """Execute the tool call or return the response.
        
        Args:
            thought: The output from think() method containing tool and parameters
            
        Returns:
            The result of the tool execution or the response content
        """
        if thought.get("type") == "response":
            return thought.get("content", "")
        
        tool_name = thought.get("tool")
        tool_args = thought.get("args", {})
        
        if not tool_name or tool_name not in self.tools:
            error_msg = f"Tool '{tool_name}' not found"
            self.context.add_message("system", error_msg)
            return {"error": error_msg}
        
        tool = self.tools[tool_name]
        
        try:
            result = tool.execute(**tool_args)
            # Record the tool call and result
            self.context.add_message(
                "system", 
                f"Tool '{tool_name}' executed with args {tool_args}. Result: {result}"
            )
            return result
        except Exception as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            self.context.add_message("system", error_msg)
            return {"error": error_msg}


class MultiAgentCoordinator:
    """Coordinates multiple agents for complex tasks.
    
    Uses a planning agent to break down tasks and delegates to specialized
    executor agents.
    """
    
    def __init__(self, planning_agent: BaseAgent, executor_agents: Dict[str, BaseAgent]):
        """Initialize the multi-agent coordinator.
        
        Args:
            planning_agent: The agent responsible for task planning
            executor_agents: A dictionary of agent names to agent instances
        """
        self.planning_agent = planning_agent
        self.executor_agents = executor_agents
    
    def execute_task(self, task_description: str) -> Any:
        """Execute a complex task using multiple agents.
        
        Args:
            task_description: The description of the task to execute
            
        Returns:
            The summarized results from all agents
        """
        # 1. Generate a plan using the planning agent
        plan = self.planning_agent.run({
            "type": "planning",
            "task": task_description
        })
        
        # 2. Execute each step in the plan
        results = []
        for step in plan.get("steps", []):
            agent_name = step.get("agent")
            subtask = step.get("task")
            
            # Skip if missing information
            if not agent_name or not subtask:
                results.append({"error": "Missing agent name or subtask in plan"})
                continue
            
            # Get the agent and execute the subtask
            agent = self.executor_agents.get(agent_name)
            if not agent:
                results.append({"error": f"Agent '{agent_name}' not found"})
                continue
            
            # Execute the subtask and collect the result
            result = agent.run(subtask)
            results.append({
                "agent": agent_name,
                "task": subtask,
                "result": result
            })
        
        # 3. Summarize the results using the planning agent
        return self.planning_agent.run({
            "type": "summarize",
            "original_task": task_description,
            "steps_results": results
        })
