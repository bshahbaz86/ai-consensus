from typing import Any, Dict, List
import logging
import asyncio
from datetime import datetime

from langchain_core.tools import tool
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


class WebSearchInput(BaseModel):
    """Input for web search tool."""
    query: str = Field(description="Search query to look up on the web")
    max_results: int = Field(default=5, description="Maximum number of search results to return")


class CalculatorInput(BaseModel):
    """Input for calculator tool."""
    expression: str = Field(description="Mathematical expression to evaluate")


class SummaryInput(BaseModel):
    """Input for content summarization tool."""
    content: str = Field(description="Content to summarize")
    max_words: int = Field(default=100, description="Maximum words in summary")


@tool("web_search", args_schema=WebSearchInput)
def web_search_tool(query: str, max_results: int = 5) -> str:
    """
    Search the web for information. Useful for getting current information,
    news, or facts that might not be in the AI's training data.
    """
    try:
        # Placeholder implementation - would integrate with actual search API
        logger.info(f"Web search requested for: {query}")
        
        # Simulated search results
        results = [
            f"Search result {i+1} for '{query}': Information about {query} from source {i+1}"
            for i in range(min(max_results, 3))
        ]
        
        return "\n".join(results)
        
    except Exception as e:
        logger.error(f"Error in web search: {str(e)}")
        return f"Error performing web search: {str(e)}"


@tool("calculator", args_schema=CalculatorInput)
def calculator_tool(expression: str) -> str:
    """
    Perform mathematical calculations. Can handle basic arithmetic,
    percentages, and simple mathematical expressions.
    """
    try:
        # Safe evaluation of mathematical expressions
        import ast
        import operator
        
        # Supported operations
        ops = {
            ast.Add: operator.add,
            ast.Sub: operator.sub,
            ast.Mult: operator.mul,
            ast.Div: operator.truediv,
            ast.Pow: operator.pow,
            ast.USub: operator.neg,
        }
        
        def eval_expr(node):
            if isinstance(node, ast.Num):
                return node.n
            elif isinstance(node, ast.BinOp):
                return ops[type(node.op)](eval_expr(node.left), eval_expr(node.right))
            elif isinstance(node, ast.UnaryOp):
                return ops[type(node.op)](eval_expr(node.operand))
            else:
                raise TypeError(node)
        
        # Parse and evaluate
        node = ast.parse(expression, mode='eval')
        result = eval_expr(node.body)
        
        return f"The result of {expression} is: {result}"
        
    except Exception as e:
        logger.error(f"Error in calculation: {str(e)}")
        return f"Error performing calculation: {str(e)}"


@tool("content_summarizer", args_schema=SummaryInput)
def content_summarizer_tool(content: str, max_words: int = 100) -> str:
    """
    Summarize long content into key points. Useful for processing
    lengthy documents or responses.
    """
    try:
        # Use the existing Django summarization service
        from apps.responses.services.summarization import ResponseSummarizer
        
        summarizer = ResponseSummarizer()
        # Temporarily adjust max words
        original_max = summarizer.max_summary_words
        summarizer.max_summary_words = max_words
        
        result = summarizer.generate_summary(content)
        
        # Restore original setting
        summarizer.max_summary_words = original_max
        
        summary = result.get('summary', 'Unable to generate summary')
        key_points = result.get('key_points', [])
        
        response = f"Summary: {summary}"
        if key_points:
            response += "\n\nKey Points:\n" + "\n".join([f"- {point}" for point in key_points])
        
        return response
        
    except Exception as e:
        logger.error(f"Error in content summarization: {str(e)}")
        return f"Error summarizing content: {str(e)}"


@tool
def django_model_query_tool(model_name: str, query_params: str) -> str:
    """
    Query Django models for data. Useful for getting information
    from the database about conversations, users, or responses.
    """
    try:
        logger.info(f"Django model query requested: {model_name} with params: {query_params}")
        
        # This would need proper implementation based on specific models
        # For security, we'd want to whitelist allowed models and operations
        
        # Placeholder response
        return f"Query result for {model_name}: Data retrieved successfully (placeholder)"
        
    except Exception as e:
        logger.error(f"Error in Django model query: {str(e)}")
        return f"Error querying Django model: {str(e)}"


@tool
def datetime_tool(format_type: str = "iso") -> str:
    """
    Get current date and time in various formats.
    Useful for timestamping or date-related queries.
    """
    try:
        now = datetime.now()
        
        if format_type == "iso":
            return now.isoformat()
        elif format_type == "human":
            return now.strftime("%Y-%m-%d %H:%M:%S")
        elif format_type == "date":
            return now.strftime("%Y-%m-%d")
        elif format_type == "time":
            return now.strftime("%H:%M:%S")
        else:
            return now.strftime("%Y-%m-%d %H:%M:%S")
            
    except Exception as e:
        logger.error(f"Error getting datetime: {str(e)}")
        return f"Error getting current time: {str(e)}"


class ToolRegistry:
    """
    Registry for managing available tools in the LangChain integration.
    """
    
    def __init__(self):
        self._tools = {
            'web_search': web_search_tool,
            'calculator': calculator_tool,
            'content_summarizer': content_summarizer_tool,
            'django_query': django_model_query_tool,
            'datetime': datetime_tool,
        }
    
    def get_tool(self, tool_name: str):
        """Get a specific tool by name."""
        return self._tools.get(tool_name)
    
    def get_tools(self, tool_names: List[str] = None) -> List:
        """Get multiple tools by name, or all tools if no names provided."""
        if tool_names is None:
            return list(self._tools.values())
        
        return [self._tools[name] for name in tool_names if name in self._tools]
    
    def register_tool(self, name: str, tool):
        """Register a new tool."""
        self._tools[name] = tool
    
    def list_available_tools(self) -> Dict[str, str]:
        """List all available tools with descriptions."""
        return {
            name: tool.description if hasattr(tool, 'description') else str(tool)
            for name, tool in self._tools.items()
        }


# Global tool registry instance
tool_registry = ToolRegistry()


def get_default_tools() -> List:
    """Get the default set of tools for LangChain agents."""
    return tool_registry.get_tools([
        'web_search',
        'calculator', 
        'content_summarizer',
        'datetime'
    ])


def get_all_tools() -> List:
    """Get all available tools."""
    return tool_registry.get_tools()


def create_custom_tool(name: str, description: str, func):
    """
    Create a custom tool from a function.
    
    Args:
        name: Tool name
        description: Tool description
        func: Function to wrap as a tool
    
    Returns:
        LangChain tool
    """
    from langchain_core.tools import Tool
    
    return Tool(
        name=name,
        description=description,
        func=func
    )