"""
User account models for ChatAI.
"""
from django.contrib.auth.models import AbstractUser
from django.db import models
from cryptography.fernet import Fernet
from django.conf import settings
import base64


class User(AbstractUser):
    """
    Extended user model with ChatAI-specific fields.
    """
    email = models.EmailField(unique=True)
    display_name = models.CharField(max_length=100, blank=True)
    avatar = models.URLField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    # User preferences
    preferred_ai_service = models.CharField(
        max_length=50,
        default='claude',
        choices=[
            ('claude', 'Claude'),
            ('openai', 'OpenAI'),
            ('auto', 'Auto-select'),
        ]
    )

    # Model preferences per provider
    openai_model = models.CharField(
        max_length=100,
        default='gpt-4o',
        blank=True
    )
    claude_model = models.CharField(
        max_length=100,
        default='claude-sonnet-4-5-20250929',
        blank=True
    )
    gemini_model = models.CharField(
        max_length=100,
        default='models/gemini-flash-latest',
        blank=True
    )
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']
    
    class Meta:
        db_table = 'users'
        verbose_name = 'User'
        verbose_name_plural = 'Users'
    
    def __str__(self):
        return self.display_name or self.username


class APIKey(models.Model):
    """
    Encrypted storage for user's AI service API keys.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='api_keys')
    service_name = models.CharField(
        max_length=50,
        choices=[
            ('claude', 'Claude'),
            ('openai', 'OpenAI'),
            ('gemini', 'Google Gemini'),
            ('cohere', 'Cohere'),
        ]
    )
    encrypted_key = models.TextField()
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'api_keys'
        unique_together = ['user', 'service_name']
        verbose_name = 'API Key'
        verbose_name_plural = 'API Keys'
    
    def set_key(self, raw_key):
        """Encrypt and store the API key."""
        if not raw_key:
            return
        
        # Create cipher
        key = base64.urlsafe_b64encode(settings.ENCRYPTION_KEY.encode()[:32])
        cipher = Fernet(key)
        
        # Encrypt the key
        encrypted_key = cipher.encrypt(raw_key.encode())
        self.encrypted_key = base64.urlsafe_b64encode(encrypted_key).decode()
    
    def get_key(self):
        """Decrypt and return the API key."""
        if not self.encrypted_key:
            return None
        
        try:
            # Create cipher
            key = base64.urlsafe_b64encode(settings.ENCRYPTION_KEY.encode()[:32])
            cipher = Fernet(key)
            
            # Decrypt the key
            encrypted_key = base64.urlsafe_b64decode(self.encrypted_key.encode())
            decrypted_key = cipher.decrypt(encrypted_key)
            return decrypted_key.decode()
        except Exception:
            return None
    
    def __str__(self):
        return f"{self.user.username} - {self.service_name}"


class UserSession(models.Model):
    """
    Extended user session information.
    """
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='chat_sessions')
    session_key = models.CharField(max_length=40, unique=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    
    class Meta:
        db_table = 'user_sessions'
        verbose_name = 'User Session'
        verbose_name_plural = 'User Sessions'
    
    def __str__(self):
        return f"{self.user.username} - {self.session_key[:10]}..."
