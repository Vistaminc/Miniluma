"""
助手工厂模块
根据类型创建不同的助手实例
"""
from typing import Optional, Dict, Any

async def create_assistant(assistant_type: str, provider_name: str = None, model: str = None, **kwargs):
    """创建助手实例
    
    Args:
        assistant_type: 助手类型，如 "simple", "multi_agent" 等
        provider_name: LLM提供商名称
        model: 模型名称
        **kwargs: 其他参数
        
    Returns:
        助手实例
    """
    # 根据类型创建不同的助手
    if assistant_type == "simple":
        from examples.simple_assistant import SimpleAssistant
        
        # SimpleAssistant现在需要异步初始化
        assistant = SimpleAssistant.__new__(SimpleAssistant)
        await assistant.__init__(llm_provider=provider_name, model=model)
        return assistant
        
    elif assistant_type == "multi_agent":
        from examples.multi_agent_example import MultiAgentSystem
        
        # 创建多代理系统
        mas = MultiAgentSystem.__new__(MultiAgentSystem)
        await mas.__init__(provider=provider_name, model=model)
        return mas
        
    elif assistant_type == "mcp":
        from examples.mcp_enhanced_assistant import MCPEnhancedAssistant
        
        # 创建MCP助手
        return await MCPEnhancedAssistant.create(
            name="MiniLuma",
            provider_name=provider_name,
            model=model,
            **kwargs
        )
    
    else:
        raise ValueError(f"不支持的助手类型: {assistant_type}")
