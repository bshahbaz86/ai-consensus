"""
Serializers for user authentication and account management.
"""
from rest_framework import serializers
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
from .models import User, APIKey


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializer for user registration.
    """
    password = serializers.CharField(write_only=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('email', 'username', 'display_name', 'password', 'password_confirm')
    
    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            email=validated_data['email'],
            username=validated_data['username'],
            display_name=validated_data.get('display_name', ''),
            password=validated_data['password']
        )
        return user


class UserLoginSerializer(serializers.Serializer):
    """
    Serializer for user login.
    """
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        email = attrs.get('email')
        password = attrs.get('password')
        
        if email and password:
            user = authenticate(username=email, password=password)
            if user:
                if not user.is_active:
                    raise serializers.ValidationError('User account is disabled.')
                attrs['user'] = user
                return attrs
            else:
                raise serializers.ValidationError('Invalid email or password.')
        else:
            raise serializers.ValidationError('Email and password are required.')


class UserProfileSerializer(serializers.ModelSerializer):
    """
    Serializer for user profile information.
    """
    class Meta:
        model = User
        fields = ('id', 'email', 'username', 'display_name', 'avatar', 
                 'preferred_ai_service', 'date_joined', 'last_login')
        read_only_fields = ('id', 'email', 'date_joined', 'last_login')


class APIKeySerializer(serializers.ModelSerializer):
    """
    Serializer for API key management.
    """
    key = serializers.CharField(write_only=True, help_text="The actual API key (will be encrypted)")
    decrypted_key = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = ('id', 'service_name', 'key', 'decrypted_key', 'is_active', 'created_at', 'updated_at')
        read_only_fields = ('id', 'created_at', 'updated_at')
    
    def get_decrypted_key(self, obj):
        # Only show last 4 characters for security
        key = obj.get_key()
        if key and len(key) > 4:
            return f"****{key[-4:]}"
        return "****"
    
    def create(self, validated_data):
        key = validated_data.pop('key')
        api_key = APIKey(**validated_data)
        api_key.set_key(key)
        api_key.save()
        return api_key
    
    def update(self, instance, validated_data):
        if 'key' in validated_data:
            key = validated_data.pop('key')
            instance.set_key(key)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        instance.save()
        return instance