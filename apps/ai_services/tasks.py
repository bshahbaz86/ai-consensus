from celery import shared_task
from django.core.exceptions import ObjectDoesNotExist
from typing import Dict, Any, Optional
import asyncio
import logging

from .models import AIService, AIQuery, AIServiceTask
from .services.factory import AIServiceFactory
from apps.accounts.models import APIKey
from apps.responses.models import AIResponse

logger = logging.getLogger(__name__)


@shared_task
def process_ai_query(query_id: str):
    try:
        query = AIQuery.objects.get(id=query_id)
        query.status = 'processing'
        query.save()
        
        results = []
        for service_task in query.aiservicetask_set.all():
            result = process_single_ai_service.delay(service_task.id)
            results.append(result)
        
        for result in results:
            result.get()
        
        query.status = 'completed'
        query.save()
        
        return f"Query {query_id} processed successfully"
        
    except Exception as e:
        logger.error(f"Error processing AI query {query_id}: {str(e)}")
        try:
            query = AIQuery.objects.get(id=query_id)
            query.status = 'failed'
            query.error_message = str(e)
            query.save()
        except ObjectDoesNotExist:
            pass
        raise


@shared_task
def process_single_ai_service(service_task_id: str):
    try:
        service_task = AIServiceTask.objects.get(id=service_task_id)
        service_task.status = 'processing'
        service_task.save()
        
        ai_service = service_task.ai_service
        query = service_task.ai_query
        
        api_key_obj = APIKey.objects.filter(
            user=query.user,
            service_type=ai_service.service_type
        ).first()
        
        if not api_key_obj:
            raise Exception(f"No API key found for {ai_service.service_type}")
        
        decrypted_key = api_key_obj.get_decrypted_key()
        
        context = {
            'conversation_history': query.context.get('conversation_history', []),
            'system_prompt': query.context.get('system_prompt', ''),
            'temperature': ai_service.default_temperature,
            'max_tokens': ai_service.max_tokens
        }
        
        service_config = {
            'model': ai_service.model_name,
            'max_tokens': ai_service.max_tokens
        }
        
        ai_service_instance = AIServiceFactory.create_service(
            service_type=ai_service.service_type,
            api_key=decrypted_key,
            **service_config
        )
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            response = loop.run_until_complete(
                ai_service_instance.generate_response(query.prompt, context)
            )
        finally:
            loop.close()
        
        if response['success']:
            ai_response = AIResponse.objects.create(
                query=query,
                ai_service=ai_service,
                content=response['content'],
                metadata=response['metadata'],
                status='completed'
            )
            
            generate_response_summary.delay(ai_response.id)
            
            service_task.status = 'completed'
            service_task.response = ai_response
        else:
            service_task.status = 'failed'
            service_task.error_message = response['error']
            
        service_task.save()
        
        return f"Service task {service_task_id} completed"
        
    except Exception as e:
        logger.error(f"Error processing service task {service_task_id}: {str(e)}")
        try:
            service_task = AIServiceTask.objects.get(id=service_task_id)
            service_task.status = 'failed'
            service_task.error_message = str(e)
            service_task.save()
        except ObjectDoesNotExist:
            pass
        raise


@shared_task
def generate_response_summary(response_id: str):
    try:
        from apps.responses.services.summarization import ResponseSummarizer
        
        response = AIResponse.objects.get(id=response_id)
        summarizer = ResponseSummarizer()
        
        summary_data = summarizer.generate_summary(response.content)
        
        response.summary = summary_data.get('summary', '')
        response.reasoning = summary_data.get('reasoning', '')
        response.key_points = summary_data.get('key_points', [])
        response.save()
        
        return f"Summary generated for response {response_id}"
        
    except Exception as e:
        logger.error(f"Error generating summary for response {response_id}: {str(e)}")
        raise