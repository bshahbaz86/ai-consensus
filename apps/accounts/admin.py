from django.contrib import admin
from .models import User, APIKey, UserSession, EmailPasscode


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('email', 'display_name', 'auth_method', 'has_permanent_password', 'is_active', 'date_joined')
    list_filter = ('auth_method', 'has_permanent_password', 'is_active')
    search_fields = ('email', 'username', 'display_name')
    readonly_fields = ('date_joined', 'last_login', 'last_auth_at')


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ('user', 'service_name', 'is_active', 'created_at')
    list_filter = ('service_name', 'is_active')
    search_fields = ('user__email', 'user__username')


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'ip_address', 'is_active', 'created_at', 'last_activity')
    list_filter = ('is_active',)
    search_fields = ('user__email', 'session_key', 'ip_address')
    readonly_fields = ('created_at', 'last_activity')


@admin.register(EmailPasscode)
class EmailPasscodeAdmin(admin.ModelAdmin):
    list_display = ('email', 'passcode', 'is_used', 'attempts', 'created_at', 'expires_at')
    list_filter = ('is_used', 'created_at')
    search_fields = ('email',)
    readonly_fields = ('created_at',)
