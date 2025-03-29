"""
OpenAI LLM implementation for the MiniLuma.
Provides integration with OpenAI's API for text generation and tool calling.
"""
from typing import Dict, List, Any, Optional
import json
import openai
from .base import BaseLLM

class OpenAILLM(BaseLLM):
    """OpenAI language model implementation.
    
    Supports text generation and function calling with OpenAI models.
    """
    
    def __init__(self, 
                model: str = "gpt-4", 
                api_key: Optional[str] = None,
                temperature: float = 0.7,
                max_tokens: Optional[int] = None):
        """Initialize the OpenAI LLM.
        
        Args:
            model: The OpenAI model to use
            api_key: Optional API key (will use environment variable if not provided)
            temperature: Model temperature setting (0.0 to 1.0)
            max_tokens: Maximum tokens to generate (None for model default)
        """
        self.model = model
        if api_key:
            openai.api_key = api_key
        self.temperature = temperature
        self.max_tokens = max_tokens
    
    def generate(self, 
                system_prompt: str, 
                user_input: str, 
                context: Optional[List[Dict]] = None, 
                **kwargs) -> str:
        """Generate text using OpenAI's API.
        
        Args:
            system_prompt: The system prompt to guide model behavior
            user_input: The user query or instruction
            context: Optional list of conversation history messages
            **kwargs: Additional parameters to pass to the OpenAI API
            
        Returns:
            The generated text response
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history context
        if context:
            messages.extend(context)
        
        # Add the current user input
        messages.append({"role": "user", "content": user_input})
        
        # Set default parameters but allow overrides
        params = {
            "model": self.model,
            "temperature": self.temperature,
        }
        
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
            
        # Add any additional parameters
        params.update(kwargs)
        
        # Make the API call
        try:
            response = openai.chat.completions.create(
                messages=messages,
                **params
            )
            
            return response.choices[0].message.content
        except Exception as e:
            return f"Error generating response: {str(e)}"
    
    def generate_with_tools(self,
                           system_prompt: str,
                           user_input: str,
                           tools: List[Dict],
                           context: Optional[List[Dict]] = None,
                           **kwargs) -> Dict:
        """Generate text with tool calling capabilities.
        
        Args:
            system_prompt: The system prompt to guide model behavior
            user_input: The user query or instruction
            tools: List of tool schemas for the model to use
            context: Optional list of conversation history messages
            **kwargs: Additional parameters to pass to the OpenAI API
            
        Returns:
            A dictionary containing the response content and tool calls
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history context
        if context:
            messages.extend(context)
        
        # Add the current user input
        messages.append({"role": "user", "content": user_input})
        
        # Set default parameters but allow overrides
        params = {
            "model": self.model,
            "temperature": self.temperature,
            "tools": tools
        }
        
        if self.max_tokens:
            params["max_tokens"] = self.max_tokens
            
        # Add any additional parameters
        params.update(kwargs)
        
        # Make the API call
        try:
            response = openai.chat.completions.create(
                messages=messages,
                **params
            )
            
            # Extract content and tool calls
            message = response.choices[0].message
            result = {"content": message.content}
            
            # Check if there are tool calls
            if hasattr(message, 'tool_calls') and message.tool_calls:
                # Format the tool calls
                tool_calls = []
                for tool_call in message.tool_calls:
                    # Parse the arguments if they're in JSON format
                    args = {}
                    try:
                        if hasattr(tool_call, 'function'):
                            args = json.loads(tool_call.function.arguments)
                    except json.JSONDecodeError:
                        args = tool_call.function.arguments
                    
                    tool_calls.append({
                        "id": tool_call.id,
                        "name": tool_call.function.name,
                        "arguments": args
                    })
                
                result["tool_calls"] = tool_calls
            
            return result
        except Exception as e:
            return {
                "content": f"Error generating response: {str(e)}",
                "tool_calls": []
            }
    
    def extract_tool_calls(self, response: Dict) -> List[Dict]:
        """Extract tool calls from an OpenAI response.
        
        Args:
            response: The response from generate_with_tools
            
        Returns:
            A list of extracted tool calls
        """
        return response.get("tool_calls", [])
