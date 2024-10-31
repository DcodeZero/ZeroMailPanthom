"""Email Campaign Project."""

from email_campaign.email_sender import EmailConfig, EmailTemplate, EmailSender
from email_campaign.email_tracking import EmailTracker
from email_campaign.tor_handler import TorHandler
from email_campaign.main import main

__version__ = '0.1.0'
__all__ = [
    'EmailConfig',
    'EmailTemplate',
    'EmailSender',
    'EmailTracker',
    'TorHandler',
    'main'
]