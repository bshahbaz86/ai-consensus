"""
Utility for extracting token usage from AI service responses.

Each AI service returns token usage in different formats:
- Claude: usage.input_tokens, usage.output_tokens
- OpenAI: usage.prompt_tokens, usage.completion_tokens
- Gemini: usageMetadata.promptTokenCount, usageMetadata.candidatesTokenCount
"""

from typing import Dict, Any, Tuple


def extract_tokens(metadata: Dict[str, Any], service_name: str) -> Tuple[int, int]:
    """
    Extract input and output token counts from service-specific metadata.

    Args:
        metadata: The metadata dict from the AI service response
        service_name: Name of the service ('claude', 'openai', 'gemini')

    Returns:
        Tuple of (input_tokens, output_tokens)

    Example:
        >>> metadata = {'usage': {'input_tokens': 100, 'output_tokens': 50}}
        >>> extract_tokens(metadata, 'claude')
        (100, 50)
    """
    service_name = service_name.lower()

    if service_name == 'claude':
        usage = metadata.get('usage', {})
        input_tokens = usage.get('input_tokens', 0)
        output_tokens = usage.get('output_tokens', 0)
        return (input_tokens, output_tokens)

    elif service_name == 'openai':
        usage = metadata.get('usage', {})
        input_tokens = usage.get('prompt_tokens', 0)
        output_tokens = usage.get('completion_tokens', 0)
        return (input_tokens, output_tokens)

    elif service_name == 'gemini':
        # Gemini returns usageMetadata at top level
        usage = metadata.get('usage', {})
        # Try both naming conventions
        input_tokens = usage.get('promptTokenCount', usage.get('prompt_token_count', 0))
        output_tokens = usage.get('candidatesTokenCount', usage.get('candidates_token_count', 0))
        return (input_tokens, output_tokens)

    # Unknown service - return zeros
    return (0, 0)


def calculate_total_tokens(input_tokens: int, output_tokens: int) -> int:
    """
    Calculate total tokens for backwards compatibility.

    Args:
        input_tokens: Number of input/prompt tokens
        output_tokens: Number of output/completion tokens

    Returns:
        Total tokens used
    """
    return input_tokens + output_tokens
