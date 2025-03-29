"""
Memory management module for the MiniLuma.
Provides functionality for storing and retrieving agent state and conversation history.
"""
from typing import Dict, List, Any, Optional
import time
import json
from datetime import datetime

class Memory:
    """Manages the agent's memory and state.
    
    Stores thoughts, observations, and execution results for
    reference during future reasoning.
    """
    
    def __init__(self, max_items: int = 100):
        """Initialize the memory manager.
        
        Args:
            max_items: Maximum number of memory items to store
        """
        self.memories: List[Dict[str, Any]] = []
        self.max_items = max_items
        self.short_term: Dict[str, Any] = {}  # For temporary storage between cycles
    
    def update(self, thought: Dict, result: Any) -> None:
        """Update the memory with a new thought-result pair.
        
        Args:
            thought: The agent's thought/reasoning
            result: The result of the action taken
        """
        memory_item = {
            "timestamp": datetime.now().isoformat(),
            "thought": thought,
            "result": result,
        }
        
        self.memories.append(memory_item)
        
        # Trim memory if it exceeds the maximum size
        if len(self.memories) > self.max_items:
            self.memories = self.memories[-self.max_items:]
    
    def get_recent_memories(self, n: int = 5) -> List[Dict[str, Any]]:
        """Get the n most recent memories.
        
        Args:
            n: Number of memories to retrieve
            
        Returns:
            A list of the n most recent memories
        """
        return self.memories[-n:] if self.memories else []
    
    def search_memories(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Search for memories containing the query string.
        
        This is a simple string matching function. In a more advanced implementation,
        this could use semantic search with embeddings.
        
        Args:
            query: The search query
            limit: Maximum number of results to return
            
        Returns:
            A list of memories matching the query
        """
        matching_memories = []
        
        # Convert query to lowercase for case-insensitive matching
        query = query.lower()
        
        for memory in reversed(self.memories):  # Start with most recent
            # Check if query exists in thought or result (converted to string)
            thought_str = json.dumps(memory["thought"]).lower()
            result_str = str(memory["result"]).lower()
            
            if query in thought_str or query in result_str:
                matching_memories.append(memory)
                
                if len(matching_memories) >= limit:
                    break
        
        return matching_memories
    
    def store_short_term(self, key: str, value: Any) -> None:
        """Store a value in short-term memory.
        
        Short-term memory is useful for passing information between
        sequential operations.
        
        Args:
            key: The key to store the value under
            value: The value to store
        """
        self.short_term[key] = value
    
    def get_short_term(self, key: str, default: Any = None) -> Any:
        """Get a value from short-term memory.
        
        Args:
            key: The key to retrieve
            default: Default value to return if key is not found
            
        Returns:
            The value stored under the key, or default if not found
        """
        return self.short_term.get(key, default)
    
    def clear_short_term(self) -> None:
        """Clear all short-term memory."""
        self.short_term = {}
    
    def clear_all(self) -> None:
        """Clear all memory (both long-term and short-term)."""
        self.memories = []
        self.clear_short_term()
    
    def summarize_memories(self, n: int = 10) -> str:
        """Generate a summary of recent memories.
        
        Args:
            n: Number of recent memories to summarize
            
        Returns:
            A string summary of recent memories
        """
        recent = self.get_recent_memories(n)
        if not recent:
            return "No memories available."
        
        summary = "Recent actions and observations:\n"
        for i, memory in enumerate(recent, 1):
            # Extract the key information from the thought
            if isinstance(memory["thought"], dict):
                if "tool" in memory["thought"]:
                    thought_summary = f"Used tool: {memory['thought']['tool']}"
                else:
                    thought_summary = str(memory["thought"])[:100] + "..." if len(str(memory["thought"])) > 100 else str(memory["thought"])
            else:
                thought_summary = str(memory["thought"])[:100] + "..." if len(str(memory["thought"])) > 100 else str(memory["thought"])
            
            # Format the result for display
            if isinstance(memory["result"], dict) and "error" in memory["result"]:
                result_summary = f"Error: {memory['result']['error']}"
            else:
                result_summary = str(memory["result"])[:100] + "..." if len(str(memory["result"])) > 100 else str(memory["result"])
            
            summary += f"{i}. {thought_summary} -> {result_summary}\n"
        
        return summary
