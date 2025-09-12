from typing import Dict, Any, Optional
from .base import BaseAIService
from .claude_service import ClaudeService
from .openai_service import OpenAIService
from .gemini_service import GeminiService


class AIServiceFactory:
    _services = {
        'claude': ClaudeService,
        'openai': OpenAIService,
        'gemini': GeminiService,
    }
    
    @classmethod
    def create_service(cls, service_type: str, api_key: str, **kwargs) -> BaseAIService:
        service_class = cls._services.get(service_type.lower())
        if not service_class:
            raise ValueError(f"Unsupported AI service type: {service_type}")
        
        return service_class(api_key=api_key, **kwargs)
    
    @classmethod
    def get_available_services(cls) -> list:
        return list(cls._services.keys())
    
    @classmethod
    def register_service(cls, service_type: str, service_class: type):
        if not issubclass(service_class, BaseAIService):
            raise ValueError("Service class must inherit from BaseAIService")
        cls._services[service_type.lower()] = service_class