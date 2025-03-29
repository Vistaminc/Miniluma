"""
Context management module for the MiniLuma.
Provides functionality for managing conversation history and context.
"""
from typing import Dict, List, Any, Optional

class Context:
    """Manages the conversation context and history for agents.
    
    Handles history tracking, system prompts, and contextual metadata
    to provide complete context for LLM prompting.
    """
    
    def __init__(self, max_history: int = 10):
        """Initialize the context manager.
        
        Args:
            max_history: Maximum number of messages to keep in history
        """
        self.history: List[Dict[str, str]] = []
        self.max_history = max_history
        self.system_prompt = ""
        self.metadata: Dict[str, Any] = {}
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to the conversation history.
        
        Args:
            role: The role of the message sender (e.g., "user", "assistant", "system")
            content: The message content
        """
        self.history.append({"role": role, "content": content})
        
        # Trim history if it exceeds the maximum length
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def set_system_prompt(self, prompt: str) -> None:
        """Set the system prompt for the agent.
        
        Args:
            prompt: The system prompt that defines agent behavior
        """
        self.system_prompt = prompt
    
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to the context.
        
        Args:
            key: The metadata key
            value: The metadata value
        """
        self.metadata[key] = value
    
    def get_metadata(self, key: str, default: Any = None) -> Any:
        """Get metadata from the context.
        
        Args:
            key: The metadata key
            default: Default value to return if key is not found
            
        Returns:
            The metadata value or default if not found
        """
        return self.metadata.get(key, default)
    
    def get_prompt_context(self) -> Dict:
        """Get the complete prompt context.
        
        Returns:
            A dictionary containing system prompt, history, and metadata
        """
        return {
            "system": self.system_prompt,
            "history": self.history,
            "metadata": self.metadata
        }
    
    def clear_history(self) -> None:
        """Clear the conversation history."""
        self.history = []
    
    def get_last_messages(self, n: int = 1) -> List[Dict[str, str]]:
        """Get the n most recent messages.
        
        Args:
            n: Number of messages to retrieve
            
        Returns:
            A list of the n most recent messages
        """
        return self.history[-n:] if self.history else []
    
    def get_history(self) -> List[Dict[str, str]]:
        """Get the complete conversation history.
        
        Returns:
            A list of all messages in the conversation history
        """
        return self.history

    def get_system_prompt(self) -> str:
        """获取系统提示词。
        
        Returns:
            系统提示词
        """
        return self.system_prompt
