from typing import Dict, List, Any, Optional
from django.contrib.auth import get_user_model
from django.db import transaction
import uuid
import logging

from .models import AIService, AIQuery, AIServiceTask
from .tasks import process_ai_query
from apps.conversations.models import Conversation, Message

User = get_user_model()
logger = logging.getLogger(__name__)


class MultiAgentOrchestrator:
    def __init__(self):
        self.active_services = AIService.objects.filter(is_active=True)
    
    async def process_user_query(
        self,
        user: User,
        prompt: str,
        conversation_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
        selected_services: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        
        try:
            with transaction.atomic():
                conversation = await self._get_or_create_conversation(user, conversation_id)
                
                user_message = Message.objects.create(
                    conversation=conversation,
                    sender=user,
                    content=prompt,
                    message_type='user'
                )
                
                query_context = self._prepare_query_context(conversation, context)
                
                ai_query = AIQuery.objects.create(
                    user=user,
                    conversation=conversation,
                    prompt=prompt,
                    context=query_context,
                    status='pending'
                )
                
                services_to_use = self._select_services(selected_services)
                
                service_tasks = []
                for service in services_to_use:
                    task = AIServiceTask.objects.create(
                        ai_query=ai_query,
                        ai_service=service,
                        status='pending'
                    )
                    service_tasks.append(task)
                
                process_ai_query.delay(str(ai_query.id))
                
                return {
                    'success': True,
                    'query_id': str(ai_query.id),
                    'conversation_id': str(conversation.id),
                    'message_id': str(user_message.id),
                    'services_count': len(service_tasks),
                    'status': 'processing'
                }
                
        except Exception as e:
            logger.error(f"Error in multi-agent orchestrator: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query_id': None,
                'conversation_id': conversation_id,
                'services_count': 0,
                'status': 'failed'
            }
    
    async def _get_or_create_conversation(self, user: User, conversation_id: Optional[str]) -> Conversation:
        if conversation_id:
            try:
                conversation = Conversation.objects.get(id=conversation_id, user=user)
                return conversation
            except Conversation.DoesNotExist:
                pass
        
        conversation = Conversation.objects.create(
            user=user,
            title=f"Chat {uuid.uuid4().hex[:8]}"
        )
        return conversation
    
    def _prepare_query_context(self, conversation: Conversation, context: Optional[Dict[str, Any]]) -> Dict[str, Any]:
        conversation_history = []
        
        recent_messages = conversation.messages.order_by('-created_at')[:10]
        for message in reversed(recent_messages):
            conversation_history.append({
                'role': 'assistant' if message.message_type == 'ai' else 'user',
                'content': message.content
            })
        
        query_context = {
            'conversation_history': conversation_history,
            'system_prompt': context.get('system_prompt', '') if context else '',
            'user_preferences': self._get_user_preferences(conversation.user),
            'conversation_metadata': {
                'id': str(conversation.id),
                'title': conversation.title,
                'message_count': conversation.messages.count()
            }
        }
        
        if context:
            query_context.update(context)
        
        return query_context
    
    def _get_user_preferences(self, user: User) -> Dict[str, Any]:
        return {
            'preferred_temperature': getattr(user, 'preferred_temperature', 0.7),
            'preferred_max_tokens': getattr(user, 'preferred_max_tokens', 2048),
            'ai_service_preferences': getattr(user, 'ai_service_preferences', {})
        }
    
    def _select_services(self, selected_services: Optional[List[str]]) -> List[AIService]:
        available_services = list(self.active_services)
        
        if not selected_services:
            return available_services
        
        filtered_services = []
        for service in available_services:
            if service.service_type.lower() in [s.lower() for s in selected_services]:
                filtered_services.append(service)
        
        return filtered_services if filtered_services else available_services
    
    def get_query_status(self, query_id: str, user: User) -> Dict[str, Any]:
        try:
            query = AIQuery.objects.get(id=query_id, user=user)
            
            service_tasks = query.aiservicetask_set.all()
            responses = query.airesponse_set.all()
            
            task_statuses = {}
            for task in service_tasks:
                task_statuses[task.ai_service.service_type] = {
                    'status': task.status,
                    'error': task.error_message
                }
            
            response_data = []
            for response in responses:
                response_data.append({
                    'id': str(response.id),
                    'service': response.ai_service.service_type,
                    'content': response.content,
                    'summary': response.summary,
                    'reasoning': response.reasoning,
                    'metadata': response.metadata,
                    'status': response.status
                })
            
            return {
                'success': True,
                'query_id': str(query.id),
                'status': query.status,
                'prompt': query.prompt,
                'created_at': query.created_at.isoformat(),
                'task_statuses': task_statuses,
                'responses': response_data,
                'total_services': service_tasks.count(),
                'completed_services': service_tasks.filter(status='completed').count(),
                'failed_services': service_tasks.filter(status='failed').count()
            }
            
        except AIQuery.DoesNotExist:
            return {
                'success': False,
                'error': 'Query not found',
                'query_id': query_id
            }
        except Exception as e:
            logger.error(f"Error getting query status: {str(e)}")
            return {
                'success': False,
                'error': str(e),
                'query_id': query_id
            }