"""
Django-allauth adapters for custom OAuth and account handling.
"""
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from django.conf import settings
from django.utils import timezone


class SocialAccountAdapter(DefaultSocialAccountAdapter):
    """Custom adapter to handle Google OAuth flows."""

    def pre_social_login(self, request, sociallogin):
        """
        Link social account to existing user with same email.
        This prevents duplicate accounts when users sign up via email then add Google.
        """
        if sociallogin.is_existing:
            return

        try:
            email = sociallogin.account.extra_data.get('email')
            if not email:
                return

            # Check if user with this email already exists
            from apps.accounts.models import User
            user = User.objects.get(email=email)

            # Link social account to existing user
            sociallogin.connect(request, user)

        except User.DoesNotExist:
            pass  # New user, will be created by allauth

    def save_user(self, request, sociallogin, form=None):
        """
        Save Google OAuth user data to our custom User model.
        """
        user = super().save_user(request, sociallogin, form)

        # Extract Google data
        extra_data = sociallogin.account.extra_data

        # Save Google-specific fields
        user.google_id = extra_data.get('sub') or extra_data.get('id')
        user.google_email = extra_data.get('email')
        user.google_profile_picture = extra_data.get('picture')
        user.auth_method = 'google_oauth'
        user.last_auth_at = timezone.now()

        # Set avatar if not already set
        if not user.avatar and extra_data.get('picture'):
            user.avatar = extra_data.get('picture')

        # Set display name if not already set
        if not user.display_name and extra_data.get('name'):
            user.display_name = extra_data.get('name')

        # Encrypt and save OAuth tokens if available
        access_token = sociallogin.token.token
        refresh_token = getattr(sociallogin.token, 'token_secret', None)
        if access_token:
            user.encrypt_google_tokens(access_token, refresh_token or '')

        user.save()

        return user

    def get_callback_url(self, request, app):
        """Return the OAuth callback URL."""
        return f"{settings.FRONTEND_URL}/auth/google/callback"


class AccountAdapter(DefaultAccountAdapter):
    """Custom account adapter for email-based flows."""

    def is_open_for_signup(self, request):
        """Allow new signups."""
        return True

    def save_user(self, request, user, form, commit=True):
        """Save user from email signup."""
        user = super().save_user(request, user, form, commit=False)

        # Set default auth method
        if not user.auth_method:
            user.auth_method = 'permanent_password'
            user.has_permanent_password = True

        if commit:
            user.save()

        return user
