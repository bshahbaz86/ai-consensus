#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys
from pathlib import Path


def _bootstrap_local_site_packages():
    """
    Ensure the project's checked-in virtualenv is available on PYTHONPATH.

    This allows developers to run `python manage.py ...` with the system
    interpreter while still resolving dependencies installed in ./venv.
    """
    base_dir = Path(__file__).resolve().parent
    venv_dir = base_dir / 'venv'
    if not venv_dir.exists():
        return

    candidate_paths = [
        venv_dir / 'Lib' / 'site-packages',  # Windows virtualenv layout
    ]
    candidate_paths.extend(venv_dir.glob('lib/python*/site-packages'))  # Unix layout

    for path in candidate_paths:
        if path.exists():
            resolved = str(path)
            if resolved not in sys.path:
                sys.path.insert(0, resolved)



def main():
    """Run administrative tasks."""
    _bootstrap_local_site_packages()
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
