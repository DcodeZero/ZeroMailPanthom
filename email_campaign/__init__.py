"""Email Campaign Package

This package provides functionality for sending and tracking email campaigns.
"""
from .email_sender import EmailConfig, EmailTemplate, EmailSender
from .email_tracking import EmailTracker
from .tor_handler import TorHandler

__version__ = '0.1.0'
__all__ = [
    'EmailConfig',
    'EmailTemplate',
    'EmailSender',
    'EmailTracker',
    'TorHandler',
    'TrackingServer'
]