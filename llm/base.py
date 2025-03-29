"""
Base LLM interface for the MiniLuma.
Defines the common interface that all LLM implementations must follow.
"""
from typing import Dict, List, Any, Optional, Union

class BaseLLM:
    """Base class for all LLM implementations"""
    
    async def generate(self, system_prompt: str = "", user_input: str = "", messages: Optional[List[Dict[str, str]]] = None, stream: bool = False, **kwargs) -> Dict[str, Any]:
        """
        Generate a response from the LLM
        
        Args:
            system_prompt: System instructions for the LLM
            user_input: User query or input text
            messages: Full conversation history in messages format (overrides system_prompt+user_input)
            stream: Whether to stream the response
            **kwargs: Additional model parameters
        
        Returns:
            The LLM response
        """
        raise NotImplementedError("Subclasses must implement the generate method")
    
    def format_messages(self, system_prompt: str, user_input: str) -> List[Dict[str, str]]:
        """
        Format system prompt and user input into messages format
        
        Args:
            system_prompt: System instructions
            user_input: User input text
        
        Returns:
            Formatted messages
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": user_input})
        
        return messages
