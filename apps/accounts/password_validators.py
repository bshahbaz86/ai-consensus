"""
Custom password validators for enhanced security.
"""
import re
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _


class ComplexityValidator:
    """
    Validates that the password meets one of these requirements:
    - At least 15 letters long (can be all letters)
    - At least 8 characters long with both letters and numbers
    """

    def validate(self, password, user=None):
        # Check if password is at least 15 letters (only alphabetic characters)
        if len(password) >= 15 and password.isalpha():
            return  # Valid: 15+ letters

        # Check if password is at least 8 characters with both letters and numbers
        if len(password) >= 8:
            has_letter = re.search(r'[a-zA-Z]', password) is not None
            has_number = re.search(r'\d', password) is not None

            if has_letter and has_number:
                return  # Valid: 8+ chars with letters and numbers

        # If neither condition is met, raise validation error
        raise ValidationError(
            _("Use a password at least 15 letters long, or at least 8 characters long with both letters and numbers."),
            code='password_complexity',
        )

    def get_help_text(self):
        return _(
            "Your password must be at least 15 letters long, or at least 8 characters long with both letters and numbers."
        )
