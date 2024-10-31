#!/usr/bin/env python3
import os
import json
import base64
import mimetypes
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.base import MIMEBase
from email import encoders
import smtplib
import ssl
from typing import Dict, List, Optional, Union
import requests
from datetime import datetime
import logging
import time
import socket
import socks
from stem import Signal
from stem.control import Controller

try:
    from .email_tracking import EmailTracker
    TRACKING_AVAILABLE = True
except ImportError:
    TRACKING_AVAILABLE = False
    logging.warning("Email tracking module not available. Tracking features will be disabled.")

class EmailConfig:
    def __init__(self, config_path: str):
        """Initialize email configuration from a JSON file."""
        with open(config_path) as f:
            config = json.load(f)
            
        self.smtp_config = config.get('smtp', {})
        self.api_config = config.get('api', {})
        self.template_dir = config.get('template_directory', 'templates')
        self.attachment_dir = config.get('attachment_directory', 'attachments')
        self.use_api = config.get('use_api', False)
        self.urls = config.get('urls', {})
        
        # Sender configurations
        self.default_sender = config.get('default_sender', {
            'email': self.smtp_config.get('username', ''),
            'name': 'Default Sender',
            'reply_to': None
        })
        
        # Get appropriate from_address based on sending method
        if self.use_api:
            self.from_address = self.api_config.get('from_address', self.default_sender)
        else:
            self.from_address = self.smtp_config.get('from_address', self.default_sender)
        
        # Tor configuration
        self.tor_config = config.get('tor', {})
        self.use_tor = self.tor_config.get('enabled', False)
        
        # Tracking configuration
        tracking_config = config.get('tracking', {})
        self.tracking_enabled = tracking_config.get('enabled', False) and TRACKING_AVAILABLE
        self.tracking_domain = tracking_config.get('domain', '')
        self.tracking_db_path = tracking_config.get('database_path', 'data/tracking.db')
        
        self.email_settings = config.get('email_settings', {
            'batch_size': 50,
            'delay_between_batches': 5,
            'delay_between_emails': 1,
            'max_retries': 3,
            'retry_delay': 5,
            'max_attachment_size': 10485760
        })

    def get_formatted_from_address(self) -> str:
        """Get properly formatted from address."""
        if self.from_address.get('name'):
            return f"{self.from_address['name']} <{self.from_address['email']}>"
        return self.from_address['email']

    def validate(self):
        """Validate the configuration."""
        if self.use_api:
            required_fields = ['api_key', 'api_url']
            config_section = self.api_config
            section_name = 'API'
        else:
            required_fields = ['host', 'port', 'username', 'password']
            config_section = self.smtp_config
            section_name = 'SMTP'

        missing_fields = [field for field in required_fields 
                         if field not in config_section]
        
        if missing_fields:
            raise ValueError(
                f"Missing required {section_name} configuration fields: {missing_fields}"
            )

class EmailTemplate:
    def __init__(self, template_path: str, attachment_dir: str):
        """Initialize email template."""
        self.template_path = template_path
        self.attachment_dir = attachment_dir
        self.subject = ""
        self.content = ""
        self.is_html = False
        self.is_base64 = False
        self.attachments = []
        self._load_template()
    
    def _load_template(self):
        """Load and parse template file."""
        try:
            with open(self.template_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            # Parse template headers
            content_lines = []
            in_headers = True
            
            for line in lines:
                line = line.strip()
                if in_headers:
                    if line.startswith('Subject:'):
                        self.subject = line.replace('Subject:', '').strip()
                    elif line.startswith('Content-Type:'):
                        self.is_html = 'html' in line.lower()
                    elif line.startswith('Encoding:'):
                        self.is_base64 = 'base64' in line.lower()
                    elif line.startswith('Attachments:'):
                        attachments = line.replace('Attachments:', '').strip()
                        if attachments:
                            self.attachments = [a.strip() for a in attachments.split(',')]
                    elif not line:
                        in_headers = False
                else:
                    if line:
                        content_lines.append(line)
            
            # Join content lines
            self.content = '\n'.join(content_lines)
            
            # Decode base64 if needed
            if self.is_base64:
                try:
                    self.content = base64.b64decode(self.content).decode('utf-8')
                except Exception as e:
                    logging.error(f"Failed to decode base64 content: {e}")
                    raise
                
            # Validate attachments exist
            self._validate_attachments()
                
        except Exception as e:
            logging.error(f"Error loading template {self.template_path}: {e}")
            raise

    def _validate_attachments(self):
        """Validate that specified attachments exist."""
        if not self.attachments:
            return

        missing_attachments = []
        for attachment in self.attachments:
            attachment_path = os.path.join(self.attachment_dir, attachment)
            if not os.path.exists(attachment_path):
                missing_attachments.append(attachment)

        if missing_attachments:
            raise FileNotFoundError(
                f"Missing attachments: {', '.join(missing_attachments)} "
                f"in directory {self.attachment_dir}"
            )

    def get_attachment_paths(self) -> List[str]:
        """Get full paths for all attachments."""
        return [os.path.join(self.attachment_dir, attachment) 
                for attachment in self.attachments]

    def replace_placeholders(self, replacements: Dict[str, str]) -> tuple[str, str]:
        """Replace placeholders in subject and content."""
        subject = self.subject
        content = self.content
        
        for key, value in replacements.items():
            placeholder = f"{{{{.{key}}}}}"
            subject = subject.replace(placeholder, str(value))
            content = content.replace(placeholder, str(value))
            
        return subject, content
class EmailSender:
    def __init__(self, config: EmailConfig):
        """Initialize email sender."""
        self.config = config
        self.config.validate()
        
        # Initialize tracker if enabled
        self.tracker = None
        if self.config.tracking_enabled:
            self.tracker = EmailTracker(db_path=self.config.tracking_db_path)
            logging.info("Email tracking initialized")
        
        # Initialize Tor if enabled
        if self.config.use_tor:
            self._setup_tor()
            logging.info("Tor handler initialized")

    def _setup_tor(self):
        """Set up Tor connection."""
        if not self.config.use_tor:
            return

        try:
            # Configure SOCKS proxy
            socks.set_default_proxy(
                socks.SOCKS5, 
                "127.0.0.1", 
                self.config.tor_config.get('socks_port', 9050)
            )
            socket.socket = socks.socksocket
            
            # Test Tor connection
            self._test_tor_connection()
            logging.info("Tor connection established successfully")
            
        except Exception as e:
            error_msg = f"Failed to set up Tor connection: {e}"
            logging.error(error_msg)
            if self.config.tor_config.get('force_tor', False):
                raise RuntimeError(error_msg)
            else:
                logging.warning("Continuing without Tor")
                # Reset socket to default if Tor fails
                socket.socket = socket._socketobject
                self.config.use_tor = False

    def _test_tor_connection(self):
        """Test Tor connection by checking IP."""
        try:
            response = requests.get('https://check.torproject.org/api/ip', timeout=10)
            data = response.json()
            if data.get('IsTor', False):
                logging.info(f"Connected through Tor. IP: {data.get('IP')}")
                return True
            else:
                raise Exception("Connected, but not through Tor network")
        except Exception as e:
            error_msg = f"Failed to verify Tor connection: {e}"
            logging.error(error_msg)
            raise

    def refresh_tor_circuit(self):
        """Refresh Tor circuit if needed."""
        if not self.config.use_tor:
            return

        try:
            with Controller.from_port(
                port=self.config.tor_config.get('control_port', 9051)
            ) as controller:
                try:
                    controller.authenticate()
                    controller.signal(Signal.NEWNYM)
                    time.sleep(self.config.tor_config.get('circuit_build_timeout', 10))
                    logging.info("Tor circuit refreshed successfully")
                except Exception as e:
                    error_msg = f"Failed to authenticate with Tor controller: {e}"
                    logging.error(error_msg)
                    raise
        except Exception as e:
            error_msg = f"Failed to refresh Tor circuit: {e}"
            logging.error(error_msg)
            if self.config.tor_config.get('force_tor', False):
                raise RuntimeError(error_msg)
            else:
                logging.warning("Continuing without Tor circuit refresh")

    def _add_attachments(self, msg: MIMEMultipart, template: EmailTemplate):
        """Add attachments to email message."""
        max_size = self.config.email_settings.get('max_attachment_size', 10485760)
        
        for attachment_path in template.get_attachment_paths():
            try:
                if os.path.getsize(attachment_path) > max_size:
                    raise ValueError(
                        f"Attachment {os.path.basename(attachment_path)} exceeds "
                        f"maximum size of {max_size/1048576:.1f}MB"
                    )
                
                with open(attachment_path, 'rb') as f:
                    file_data = f.read()
                    
                # Detect MIME type
                content_type, encoding = mimetypes.guess_type(attachment_path)
                if content_type is None:
                    content_type = 'application/octet-stream'
                
                maintype, subtype = content_type.split('/', 1)
                
                if maintype == 'text':
                    attachment = MIMEText(file_data.decode(), _subtype=subtype)
                elif maintype == 'application':
                    attachment = MIMEApplication(file_data, _subtype=subtype)
                else:
                    attachment = MIMEBase(maintype, subtype)
                    attachment.set_payload(file_data)
                    encoders.encode_base64(attachment)
                
                filename = os.path.basename(attachment_path)
                attachment.add_header(
                    'Content-Disposition', 'attachment', 
                    filename=filename
                )
                
                msg.attach(attachment)
                logging.info(f"Added attachment: {filename}")
                
            except Exception as e:
                logging.error(f"Error adding attachment {attachment_path}: {e}")
                raise

    def send_email(self, template: EmailTemplate, recipient: Dict[str, str], 
                  sender: str = None, url: str = None, tracking_url: str = None, 
                  campaign_id: str = None):
        """Send email with tracking and attachments.
        
        Args:
            template (EmailTemplate): Email template to use
            recipient (Dict[str, str]): Recipient information
            sender (str, optional): Sender email address. Defaults to None.
            url (str, optional): Landing page URL. Defaults to None.
            tracking_url (str, optional): URL for tracking. Defaults to None.
            campaign_id (str, optional): Campaign identifier. Defaults to None.
        """
        try:
            email_id = None
            if self.tracker and campaign_id:
                email_id = self.tracker.track_email_send(
                    recipient_email=recipient['email'],
                    template_name=template.template_path,
                    campaign_id=campaign_id
                )

            # Get sender information
            if sender is None:
                sender = self.config.get_formatted_from_address()

            # Prepare replacements
            replacements = {
                "FirstName": recipient.get('first_name', ''),
                "LastName": recipient.get('last_name', ''),
                "Email": recipient.get('email', ''),
                "URL": url or self.config.urls.get('landing_page', ''),
                "TrackingURL": tracking_url or ''
            }
            
            # Replace placeholders
            subject, content = template.replace_placeholders(replacements)
            
            # Add tracking if enabled
            if self.tracker and email_id and tracking_url:
                content = self.tracker.generate_tracking_links(
                    content=content,
                    email_id=email_id,
                    tracking_domain=tracking_url
                )
                
                tracking_pixel = self.tracker.generate_tracking_pixel(
                    email_id=email_id,
                    tracking_domain=tracking_url
                )
                if template.is_html:
                    content = content.replace('</body>', f'{tracking_pixel}</body>')
            
            # Create message
            msg = MIMEMultipart()
            msg['Subject'] = subject
            msg['From'] = sender
            msg['To'] = recipient['email']
            
            # Add Reply-To if configured
            reply_to = self.config.from_address.get('reply_to')
            if reply_to:
                msg['Reply-To'] = reply_to
            
            if campaign_id:
                msg['X-Campaign-ID'] = campaign_id
            if email_id:
                msg['X-Email-ID'] = email_id
            
            # Attach content
            content_type = 'html' if template.is_html else 'plain'
            msg.attach(MIMEText(content, content_type))
            
            # Add attachments
            if template.attachments:
                self._add_attachments(msg, template)

            # Send email
            if self.config.use_api:
                self._send_via_api(msg, recipient['email'])
            else:
                self._send_via_smtp(msg, recipient['email'])
                
        except Exception as e:
            logging.error(f"Error sending email to {recipient['email']}: {e}")
            raise

    def _send_via_smtp(self, msg: MIMEMultipart, recipient: str):
        """Send email using SMTP through Tor if enabled."""
        retry_count = 0
        max_retries = self.config.email_settings.get('max_retries', 3)
        retry_delay = self.config.email_settings.get('retry_delay', 5)

        while retry_count < max_retries:
            try:
                # Only try to refresh Tor circuit if Tor is enabled and working
                if self.config.use_tor:
                    try:
                        self.refresh_tor_circuit()
                    except Exception as e:
                        logging.warning(f"Tor circuit refresh failed: {e}")
                        # Continue without Tor if it fails and not forced
                        if not self.config.tor_config.get('force_tor', False):
                            self.config.use_tor = False
                
                context = ssl.create_default_context()
                
                with smtplib.SMTP(self.config.smtp_config['host'], 
                                self.config.smtp_config['port']) as server:
                    server.starttls(context=context)
                    server.login(self.config.smtp_config['username'],
                            self.config.smtp_config['password'])
                    server.send_message(msg)
                    logging.info(f"Email sent successfully via SMTP to {recipient}")
                    return
                    
            except smtplib.SMTPServerDisconnected as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"SMTP connection lost, retry {retry_count} for {recipient}: {str(e)}")
                    time.sleep(retry_delay)
                    # Reset socket to default if using Tor
                    if self.config.use_tor:
                        socket.socket = socket._socketobject
                        self.config.use_tor = False
                        logging.info("Disabled Tor due to connection issues")
                else:
                    logging.error(f"Failed to send email via SMTP to {recipient} after {max_retries} retries: {e}")
                    raise
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Retry {retry_count} for {recipient}: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Failed to send email via SMTP to {recipient} after {max_retries} retries: {e}")
                    raise

    def _send_via_api(self, msg: MIMEMultipart, recipient: str):
        """Send email using API through Tor if enabled."""
        retry_count = 0
        max_retries = self.config.email_settings.get('max_retries', 3)
        retry_delay = self.config.email_settings.get('retry_delay', 5)

        while retry_count < max_retries:
            try:
                # Refresh Tor circuit if enabled
                if self.config.use_tor:
                    self.refresh_tor_circuit()
                
                payload = {
                    'to': recipient,
                    'subject': msg['Subject'],
                    'html' if 'html' in msg.get_content_type().lower() else 'text': 
                        msg.get_payload(0).get_payload(),
                    'from': msg['From'],
                    'attachments': []
                }
                
                # Add attachments to payload
                for part in msg.get_payload()[1:]:
                    if part.get_content_type() not in ['text/plain', 'text/html']:
                        attachment_data = {
                            'filename': part.get_filename(),
                            'content': base64.b64encode(
                                part.get_payload(decode=True)
                            ).decode(),
                            'content_type': part.get_content_type()
                        }
                        payload['attachments'].append(attachment_data)
                
                headers = {
                    'Authorization': f"Bearer {self.config.api_config['api_key']}",
                    'Content-Type': 'application/json'
                }
                
                response = requests.post(
                    self.config.api_config['api_url'],
                    json=payload,
                    headers=headers,
                    proxies={
                        'http': 'socks5h://127.0.0.1:9050',
                        'https': 'socks5h://127.0.0.1:9050'
                    } if self.config.use_tor else None
                )
                response.raise_for_status()
                logging.info(f"Email sent successfully via API to {recipient}")
                return
                
            except Exception as e:
                retry_count += 1
                if retry_count < max_retries:
                    logging.warning(f"Retry {retry_count} for {recipient}: {str(e)}")
                    time.sleep(retry_delay)
                else:
                    logging.error(f"Failed to send email via API to {recipient} after {max_retries} retries: {e}")
                    raise