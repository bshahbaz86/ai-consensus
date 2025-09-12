from typing import Dict, Any, List, Optional
import logging
from django.conf import settings

from langchain_openai import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.runnables import RunnablePassthrough
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_functions
from langchain.agents.output_parsers import OpenAIFunctionsAgentOutputParser
from langchain_core.tools import tool

from apps.ai_services.services.factory import AIServiceFactory

logger = logging.getLogger(__name__)


class LangChainService:
    """
    Django-integrated LangChain service for AI orchestration and tool calling.
    Based on the user's cbfs pattern but integrated with Django architecture.
    """
    
    def __init__(self, tools: List = None, ai_service_name: str = "openai"):
        self.ai_service_name = ai_service_name
        self.tools = tools or []
        self.memory = ConversationBufferMemory(
            return_messages=True,
            memory_key="chat_history"
        )
        
        # Setup model based on AI service
        self.model = self._setup_model()
        
        # Create prompt template similar to user's pattern
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful but intelligent assistant with access to tools. Use tools when needed to provide accurate and comprehensive responses."),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", "{input}"),
            MessagesPlaceholder(variable_name="agent_scratchpad")
        ])
        
        # Setup chain and agent executor
        self._setup_agent()
    
    def _setup_model(self):
        """Setup the language model based on AI service configuration."""
        try:
            ai_service = AIServiceFactory.get_service(self.ai_service_name)
            
            if self.ai_service_name == "openai":
                # Use LangChain's ChatOpenAI with our service's API key
                return ChatOpenAI(
                    openai_api_key=ai_service.api_key,
                    model=getattr(ai_service, 'model', 'gpt-4'),
                    temperature=0.7
                )
            else:
                # For other services, we'll create a custom wrapper
                return self._create_custom_model_wrapper(ai_service)
                
        except Exception as e:
            logger.error(f"Error setting up LangChain model: {str(e)}")
            # Fallback to OpenAI if available
            try:
                openai_service = AIServiceFactory.get_service("openai")
                return ChatOpenAI(
                    openai_api_key=openai_service.api_key,
                    model='gpt-4',
                    temperature=0.7
                )
            except:
                raise Exception("Failed to setup any AI model for LangChain")
    
    def _create_custom_model_wrapper(self, ai_service):
        """Create a custom wrapper for non-OpenAI services."""
        # This would need to be implemented based on specific service requirements
        # For now, fallback to OpenAI
        logger.warning(f"Custom wrapper not implemented for {self.ai_service_name}, using OpenAI fallback")
        openai_service = AIServiceFactory.get_service("openai")
        return ChatOpenAI(
            openai_api_key=openai_service.api_key,
            model='gpt-4',
            temperature=0.7
        )
    
    def _setup_agent(self):
        """Setup the agent executor similar to user's pattern."""
        try:
            # Convert tools to OpenAI function format
            if self.tools:
                from langchain_core.tools.utils import format_tool_to_openai_function
                functions = [format_tool_to_openai_function(tool) for tool in self.tools]
                model_with_functions = self.model.bind(functions=functions)
            else:
                model_with_functions = self.model
            
            # Create the chain similar to user's pattern
            self.chain = RunnablePassthrough.assign(
                agent_scratchpad=lambda x: format_to_openai_functions(x["intermediate_steps"])
            ) | self.prompt | model_with_functions | OpenAIFunctionsAgentOutputParser()
            
            # Create agent executor
            self.agent_executor = AgentExecutor(
                agent=self.chain,
                tools=self.tools,
                verbose=False,
                memory=self.memory,
                return_intermediate_steps=True
            )
            
        except Exception as e:
            logger.error(f"Error setting up agent: {str(e)}")
            # Fallback to basic chain without tools
            self.chain = self.prompt | self.model
            self.agent_executor = None
    
    async def invoke(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Invoke the agent with a query, similar to user's convchain method.
        """
        try:
            if not query:
                return {
                    'success': False,
                    'error': 'Empty query provided',
                    'output': '',
                    'intermediate_steps': []
                }
            
            # Prepare input
            input_data = {"input": query}
            if context:
                input_data.update(context)
            
            # Run the agent
            if self.agent_executor:
                result = await self.agent_executor.ainvoke(input_data)
            else:
                # Fallback to basic chain
                result = await self.chain.ainvoke(input_data)
                result = {'output': result.content if hasattr(result, 'content') else str(result)}
            
            return {
                'success': True,
                'output': result.get('output', ''),
                'intermediate_steps': result.get('intermediate_steps', []),
                'metadata': {
                    'model': self.ai_service_name,
                    'tools_used': len(result.get('intermediate_steps', [])),
                    'memory_length': len(self.memory.chat_memory.messages)
                }
            }
            
        except Exception as e:
            logger.error(f"Error invoking LangChain agent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'output': '',
                'intermediate_steps': []
            }
    
    def add_tool(self, tool):
        """Add a tool to the agent."""
        if tool not in self.tools:
            self.tools.append(tool)
            self._setup_agent()  # Recreate agent with new tools
    
    def remove_tool(self, tool_name: str):
        """Remove a tool by name."""
        self.tools = [tool for tool in self.tools if tool.name != tool_name]
        self._setup_agent()  # Recreate agent without the tool
    
    def clear_memory(self):
        """Clear conversation history, similar to user's clr_history method."""
        self.memory.clear()
    
    def get_memory_summary(self) -> Dict[str, Any]:
        """Get summary of current conversation memory."""
        messages = self.memory.chat_memory.messages
        return {
            'message_count': len(messages),
            'last_messages': [
                {
                    'type': type(msg).__name__,
                    'content': msg.content[:100] + '...' if len(msg.content) > 100 else msg.content
                }
                for msg in messages[-5:]  # Last 5 messages
            ]
        }


class ConversationAgentExecutor:
    """
    Django-specific agent executor for conversation management.
    Integrates with Django models and follows Django patterns.
    """
    
    def __init__(self, conversation_id: Optional[int] = None):
        self.conversation_id = conversation_id
        self.langchain_service = None
        self.panels = []  # Similar to user's pattern for UI tracking
    
    def setup_service(self, tools: List = None, ai_service_name: str = "openai"):
        """Setup the LangChain service with specified tools."""
        self.langchain_service = LangChainService(tools=tools, ai_service_name=ai_service_name)
    
    async def process_query(self, query: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Process a query and return formatted response.
        Similar to user's convchain method but Django-integrated.
        """
        if not self.langchain_service:
            return {
                'success': False,
                'error': 'LangChain service not initialized',
                'response': ''
            }
        
        try:
            # Invoke the agent
            result = await self.langchain_service.invoke(query, context)
            
            if result.get('success'):
                response_text = result.get('output', '')
                
                # Store in panels for UI tracking (similar to user's pattern)
                self.panels.extend([
                    {'type': 'user', 'content': query},
                    {'type': 'assistant', 'content': response_text}
                ])
                
                # Save to Django model if conversation_id is provided
                if self.conversation_id:
                    await self._save_to_conversation(query, response_text, result.get('metadata', {}))
                
                return {
                    'success': True,
                    'response': response_text,
                    'metadata': result.get('metadata', {}),
                    'intermediate_steps': result.get('intermediate_steps', []),
                    'panels': self.panels[-2:]  # Return last user-assistant pair
                }
            else:
                return {
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'response': ''
                }
                
        except Exception as e:
            logger.error(f"Error processing query with agent: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'response': ''
            }
    
    async def _save_to_conversation(self, query: str, response: str, metadata: Dict[str, Any]):
        """Save query and response to Django conversation model."""
        try:
            # Import here to avoid circular imports
            from apps.conversations.models import Conversation, Message
            
            if self.conversation_id:
                conversation = await Conversation.objects.aget(id=self.conversation_id)
                
                # Save user message
                await Message.objects.acreate(
                    conversation=conversation,
                    content=query,
                    role='user',
                    metadata={'agent_processed': True}
                )
                
                # Save assistant response
                await Message.objects.acreate(
                    conversation=conversation,
                    content=response,
                    role='assistant',
                    metadata={
                        'agent_processed': True,
                        'langchain_metadata': metadata,
                        'tools_used': metadata.get('tools_used', 0)
                    }
                )
                
        except Exception as e:
            logger.error(f"Error saving to conversation: {str(e)}")
    
    def clear_history(self):
        """Clear conversation history, similar to user's clr_history method."""
        if self.langchain_service:
            self.langchain_service.clear_memory()
        self.panels = []
    
    def get_conversation_panels(self) -> List[Dict[str, str]]:
        """Get conversation panels for UI display."""
        return self.panels