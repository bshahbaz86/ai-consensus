import json
import logging
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from django.core.exceptions import ObjectDoesNotExist

from .models import Conversation, Message
from apps.ai_services.models import AIQuery
from apps.ai_services.orchestrator import MultiAgentOrchestrator

User = get_user_model()
logger = logging.getLogger(__name__)


class ChatConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.conversation_id = self.scope['url_route']['kwargs']['conversation_id']
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        try:
            conversation = await self.get_conversation()
            if not conversation or conversation.user != self.user:
                await self.close()
                return
        except Exception as e:
            logger.error(f"Error validating conversation: {str(e)}")
            await self.close()
            return
        
        self.room_group_name = f'chat_{self.conversation_id}'
        
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'conversation_id': self.conversation_id,
            'message': 'Connected to chat'
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(
                self.room_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'chat_message':
                await self.handle_chat_message(data)
            elif message_type == 'query_status_request':
                await self.handle_query_status_request(data)
            else:
                await self.send_error('Unknown message type')
                
        except json.JSONDecodeError:
            await self.send_error('Invalid JSON format')
        except Exception as e:
            logger.error(f"Error in WebSocket receive: {str(e)}")
            await self.send_error('Internal server error')
    
    async def handle_chat_message(self, data):
        message_content = data.get('message', '').strip()
        if not message_content:
            await self.send_error('Empty message content')
            return
        
        try:
            orchestrator = MultiAgentOrchestrator()
            
            context = data.get('context', {})
            selected_services = data.get('services', None)
            
            result = await orchestrator.process_user_query(
                user=self.user,
                prompt=message_content,
                conversation_id=self.conversation_id,
                context=context,
                selected_services=selected_services
            )
            
            if result['success']:
                await self.channel_layer.group_send(
                    self.room_group_name,
                    {
                        'type': 'chat_message_created',
                        'message': {
                            'id': result['message_id'],
                            'content': message_content,
                            'sender': 'user',
                            'timestamp': None
                        },
                        'query': {
                            'id': result['query_id'],
                            'status': result['status'],
                            'services_count': result['services_count']
                        }
                    }
                )
            else:
                await self.send_error(f"Failed to process message: {result.get('error', 'Unknown error')}")
                
        except Exception as e:
            logger.error(f"Error handling chat message: {str(e)}")
            await self.send_error('Failed to process message')
    
    async def handle_query_status_request(self, data):
        query_id = data.get('query_id')
        if not query_id:
            await self.send_error('Missing query_id')
            return
        
        try:
            orchestrator = MultiAgentOrchestrator()
            status = orchestrator.get_query_status(query_id, self.user)
            
            await self.send(text_data=json.dumps({
                'type': 'query_status_update',
                'query_status': status
            }))
            
        except Exception as e:
            logger.error(f"Error getting query status: {str(e)}")
            await self.send_error('Failed to get query status')
    
    async def chat_message_created(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message_created',
            'message': event['message'],
            'query': event['query']
        }))
    
    async def ai_response_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ai_response_update',
            'response': event['response'],
            'query_id': event['query_id']
        }))
    
    async def query_completed(self, event):
        await self.send(text_data=json.dumps({
            'type': 'query_completed',
            'query_id': event['query_id'],
            'responses': event['responses']
        }))
    
    async def send_error(self, error_message):
        await self.send(text_data=json.dumps({
            'type': 'error',
            'error': error_message
        }))
    
    @database_sync_to_async
    def get_conversation(self):
        try:
            return Conversation.objects.get(id=self.conversation_id)
        except Conversation.DoesNotExist:
            return None


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        
        if not self.user or not self.user.is_authenticated:
            await self.close()
            return
        
        self.user_group_name = f'user_{self.user.id}'
        
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        
        await self.accept()
        
        await self.send(text_data=json.dumps({
            'type': 'connection_established',
            'message': 'Connected to notifications'
        }))
    
    async def disconnect(self, close_code):
        if hasattr(self, 'user_group_name'):
            await self.channel_layer.group_discard(
                self.user_group_name,
                self.channel_name
            )
    
    async def receive(self, text_data):
        try:
            data = json.loads(text_data)
            message_type = data.get('type')
            
            if message_type == 'ping':
                await self.send(text_data=json.dumps({
                    'type': 'pong',
                    'timestamp': data.get('timestamp')
                }))
                
        except json.JSONDecodeError:
            pass
    
    async def notification_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'notification': event['notification']
        }))
    
    async def ai_task_update(self, event):
        await self.send(text_data=json.dumps({
            'type': 'ai_task_update',
            'task_update': event['task_update']
        }))