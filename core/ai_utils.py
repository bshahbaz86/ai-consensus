import json
from typing import Dict, Any, Type
from pydantic import BaseModel


def convert_pydantic_to_openai_function(model: Type[BaseModel]) -> Dict[str, Any]:
    """
    Convert a Pydantic model to OpenAI function calling schema.
    NOTE: This is a legacy utility - structured outputs now use unified pydantic_ai_service
    for consistent JSON schema across all providers (OpenAI, Claude, Gemini).
    """
    schema = model.model_json_schema()
    
    function_schema = {
        "name": model.__name__,
        "description": model.__doc__ or f"Call this function to create a {model.__name__}",
        "parameters": {
            "type": "object",
            "properties": schema.get("properties", {}),
            "required": schema.get("required", [])
        }
    }
    
    return function_schema


def parse_function_call_response(response_content: str, function_name: str) -> Dict[str, Any]:
    """
    Parse OpenAI function call response and extract the function arguments.
    """
    try:
        if isinstance(response_content, str):
            return json.loads(response_content)
        return response_content
    except json.JSONDecodeError:
        return {"error": f"Failed to parse {function_name} response"}


class JsonOutputFunctionsParser:
    """
    Parser for OpenAI function calling responses.
    Similar to JsonOutputFunctionsParser from langchain.
    """
    
    def parse(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """Parse the function call response from OpenAI."""
        try:
            choices = response.get('choices', [])
            if not choices:
                return {"error": "No choices in response"}
            
            message = choices[0].get('message', {})
            function_call = message.get('function_call')
            
            if function_call:
                function_name = function_call.get('name')
                arguments = function_call.get('arguments', '{}')
                
                if isinstance(arguments, str):
                    return json.loads(arguments)
                return arguments
            
            return {"error": "No function call in response"}
            
        except Exception as e:
            return {"error": f"Failed to parse function response: {str(e)}"}