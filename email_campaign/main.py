#!/usr/bin/env python3
import os
import json
import argparse
from datetime import datetime
import logging
from logging.handlers import RotatingFileHandler
import time
import sys
import uuid
import traceback
from typing import Dict, List, Optional
from .sandbox_evasion import integrate_sandbox_evasion
from .ngrok_handler import NgrokHandler, TrackingServer

# Add the parent directory to path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

try:
    from email_campaign.email_sender import EmailConfig, EmailTemplate, EmailSender
    from email_campaign.email_tracking import EmailTracker
    from email_campaign.tor_handler import TorHandler
    MODULES_AVAILABLE = True
except ImportError as e:
    logging.warning(f"Import error: {e}")
    MODULES_AVAILABLE = False

@integrate_sandbox_evasion
class EmailCampaign:
    def __init__(self, config_path: str, campaign_id: str = None, skip_environment_check: bool = False):
        """Initialize email campaign."""
        self.config_path = config_path
        self.campaign_id = campaign_id or str(uuid.uuid4())
        self.config = self._load_config()
        self.skip_environment_check = skip_environment_check
        self.setup_logging()
        
        # Initialize configurations
        self.email_config = EmailConfig(config_path)
        self.email_sender = EmailSender(self.email_config)
        
        # Initialize Tor if enabled
        self.tor_handler = None
        if self.config.get('tor', {}).get('enabled', False):
            try:
                self.tor_handler = TorHandler(self.config)
                logging.info("Tor routing enabled and initialized")
            except Exception as e:
                logging.error(f"Failed to initialize Tor: {e}")
                if self.config['tor'].get('force_tor', False):
                    raise

        self.ngrok_handler = None
        self.tracking_server = None
        if self.config.get('ngrok', {}).get('enabled', False):
            try:
                self.ngrok_handler = NgrokHandler(self.config)
                self.tracking_server = TrackingServer(
                    config=self.config,
                    ngrok_handler=self.ngrok_handler
                )
                logging.info("Ngrok initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize Ngrok: {e}")
        
        # Initialize tracker if enabled
        self.tracker = None
        if self.config.get('tracking', {}).get('enabled', False) and MODULES_AVAILABLE:
            try:
                self.tracker = EmailTracker(
                    db_path=self.config.get('tracking', {}).get('database_path', 'data/tracking.db')
                )
                logging.info("Email tracking initialized successfully")
            except Exception as e:
                logging.error(f"Failed to initialize tracking: {e}")

    def _load_config(self) -> Dict:
        """Load configuration from file."""
        try:
            if not os.path.exists(self.config_path):
                raise FileNotFoundError(f"Configuration file not found: {self.config_path}")
                
            with open(self.config_path, 'r') as f:
                config = json.load(f)
                
            # Validate essential configuration sections
            required_sections = ['smtp', 'template_directory', 'email_settings']
            missing_sections = [section for section in required_sections 
                              if section not in config]
            
            if missing_sections:
                raise ValueError(f"Missing required configuration sections: {missing_sections}")
                
            return config
            
        except Exception as e:
            error_msg = f"Error loading configuration from {self.config_path}: {e}"
            print(error_msg)  # Print error before logging is set up
            raise ValueError(error_msg)


    def setup_logging(self) -> None:
        """Set up logging configuration."""
        log_config = self.config.get('logging', {})
        log_file = log_config.get('log_file', 'email_sender.log')
        log_level = getattr(logging, log_config.get('log_level', 'INFO'))
        
        # Create logs directory if it doesn't exist
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        log_file = os.path.join('logs', log_file)
        
        if log_config.get('rotate_logs', False):
            handler = RotatingFileHandler(
                log_file,
                maxBytes=log_config.get('max_log_size', 5242880),
                backupCount=log_config.get('backup_count', 3)
            )
        else:
            handler = logging.FileHandler(log_file)
        
        # Configure logging format with timestamp
        formatter = logging.Formatter(
            '%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        
        # Also log to console with same format
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        
        # Set up root logger
        logging.basicConfig(
            level=log_level,
            handlers=[handler, console_handler]
        )
    def load_recipients(self, recipients_path: str) -> List[Dict]:
        """Load recipients from JSON file."""
        try:
            if not os.path.exists(recipients_path):
                raise FileNotFoundError(f"Recipients file not found: {recipients_path}")
                
            with open(recipients_path, 'r') as f:
                recipients_config = json.load(f)
                
            if 'targets' not in recipients_config:
                raise ValueError("Recipients configuration must contain 'targets' key")
                
            required_fields = ['email', 'first_name', 'last_name']
            for recipient in recipients_config['targets']:
                missing_fields = [field for field in required_fields 
                                if field not in recipient]
                if missing_fields:
                    raise ValueError(
                        f"Recipient {recipient.get('email', 'unknown')} missing "
                        f"required fields: {missing_fields}"
                    )
                    
            return recipients_config['targets']
            
        except Exception as e:
            logging.error(f"Error loading recipients from {recipients_path}: {e}")
            raise

    def get_template_files(self) -> List[str]:
        """Get list of template files from directory."""
        template_dir = self.config.get('template_directory', 'templates')
        try:
            if not os.path.exists(template_dir):
                raise FileNotFoundError(f"Template directory not found: {template_dir}")
            
            templates = [f for f in os.listdir(template_dir)
                        if f.endswith(('.txt', '.html'))]
            
            if not templates:
                raise FileNotFoundError("No template files found")
                
            return templates
            
        except Exception as e:
            logging.error(f"Error accessing template directory: {e}")
            raise

    def setup_tracking_url(self) -> Optional[str]:
        """Setup tracking URL using Ngrok if enabled."""
        if not self.ngrok_handler:
            return None
            
        try:
            # Start Ngrok tunnel for tracking
            tracking_port = self.config.get('tracking', {}).get('port', 8080)
            public_url = self.ngrok_handler.start_tunnel(
                port=tracking_port,
                protocol='http'
            )
            
            if public_url:
                logging.info(f"Tracking URL established: {public_url}")
                return public_url
            return None
            
        except Exception as e:
            logging.error(f"Failed to setup tracking URL: {e}")
            return None

    def get_ngrok_status(self) -> Dict:
        """Get Ngrok status and metrics."""
        if not self.ngrok_handler:
            return {"enabled": False}
            
        return {
            "enabled": True,
            "tunnel_info": self.ngrok_handler.get_tunnel_info()
        }

    def check_sandbox_status(self) -> Dict:
        """Check and return detailed sandbox detection status."""
        if not hasattr(self, 'sandbox_evasion'):
            return {
                'enabled': False,
                'message': 'Sandbox detection not initialized'
            }
            
        try:
            results = self.sandbox_evasion.run_checks()
            status = {
                'enabled': self.config.get('sandbox_evasion', {}).get('enabled', False),
                'confidence_threshold': self.config.get('sandbox_evasion', {}).get('confidence_threshold', 70),
                'results': results,
                'is_sandbox': results['confidence'] < self.config.get('sandbox_evasion', {}).get('confidence_threshold', 70)
            }
            
            status['checks'] = {
                'system_resources': results.get('system_resources', False),
                'uptime': results.get('uptime', False),
                'vm_artifacts': results.get('vm_artifacts', False),
                'hardware': results.get('hardware', False),
                'timing': results.get('timing', False),
                'user_interaction': results.get('user_interaction', False)
            }
            
            return status
            
        except Exception as e:
            return {
                'enabled': False,
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    def validate_directories(self):
        """Ensure required directories exist."""
        directories = [
            self.config.get('template_directory', 'templates'),
            self.config.get('attachment_directory', 'attachments'),
            'logs',
            'data'
        ]
        
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logging.info(f"Created directory: {directory}")

    def validate_campaign(self, recipients_path: str, template_names: List[str] = None) -> bool:
        """Validate campaign configuration before sending."""
        try:
            # Check for sandbox environment if not skipped
            if not self.skip_environment_check:
                try:
                    self.check_environment()
                except EnvironmentError as e:
                    logging.error(f"Environment validation failed: {e}")
                    return False
            else:
                logging.warning("Sandbox environment check skipped")

            # Check recipients file
            if not os.path.exists(recipients_path):
                logging.error(f"Recipients file not found: {recipients_path}")
                return False
            
            # Validate templates
            template_dir = self.config.get('template_directory', 'templates')
            if template_names:
                for template in template_names:
                    template_path = os.path.join(template_dir, template)
                    if not os.path.exists(template_path):
                        logging.error(f"Template not found: {template_path}")
                        return False
            
            # Validate email configuration
            if self.config.get('use_api', False):
                required_fields = ['api_key', 'api_url']
                config_section = self.config.get('api', {})
                section_name = "API"
            else:
                required_fields = ['host', 'port', 'username', 'password']
                config_section = self.config.get('smtp', {})
                section_name = "SMTP"
            
            missing_fields = [field for field in required_fields 
                            if field not in config_section]
            if missing_fields:
                logging.error(
                    f"Missing required {section_name} configuration fields: "
                    f"{missing_fields}"
                )
                return False
            
            # Validate Tor if enabled
            if self.config.get('tor', {}).get('enabled', False):
                try:
                    import socks
                    if self.tor_handler:
                        self.tor_handler._test_tor_connection()
                except ImportError:
                    logging.error("Tor support requires 'socks' package")
                    return False
                except Exception as e:
                    logging.error(f"Tor connection test failed: {e}")
                    return False
                    
            # Validate Ngrok if enabled
            if self.config.get('ngrok', {}).get('enabled', False):
                if not self.ngrok_handler:
                    logging.error("Ngrok enabled but handler not initialized")
                    return False
            
            return True
            
        except Exception as e:
            logging.error(f"Validation failed: {e}")
            return False

    def send_campaign(self, recipients_path: str, template_names: List[str] = None, 
                     test_mode: bool = False) -> None:
        """Send email campaign to recipients."""
        try:
            # Validate campaign
            if not self.validate_campaign(recipients_path, template_names):
                raise ValueError("Campaign validation failed")

            # Start tracking server if enabled
            tracking_url = None
            if self.tracking_server:
                tracking_url = self.tracking_server.start(
                    port=self.config['ngrok']['tunnel_config'].get('port', 8080)
                )
                if tracking_url:
                    self.config['urls']['tracking_url'] = tracking_url
                    logging.info(f"Tracking URL established: {tracking_url}")
            
            # Load recipients
            recipients = self.load_recipients(recipients_path)
            
            # Apply test mode limitations
            if test_mode:
                recipients = recipients[:1]
                logging.info("Running in test mode - sending to first recipient only")
            
            # Get templates
            if template_names:
                templates = template_names
            else:
                templates = self.get_template_files()
            
            logging.info(
                f"Starting email campaign {self.campaign_id} with "
                f"{len(recipients)} recipients and {len(templates)} templates"
            )
            
            # Process each template
            for template_name in templates:
                template_path = os.path.join(
                    self.config['template_directory'], 
                    template_name
                )
                
                template = EmailTemplate(
                    template_path=template_path,
                    attachment_dir=self.config.get('attachment_directory', 'attachments')
                )
                
                logging.info(f"Processing template: {template_name}")
                
                # Send to recipients in batches
                batch_size = self.config['email_settings']['batch_size']
                for i in range(0, len(recipients), batch_size):
                    batch = recipients[i:i + batch_size]
                    logging.info(f"Processing batch of {len(batch)} recipients")
                    
                    for recipient in batch:
                        try:
                            # Get URLs
                            landing_url = self.config.get('urls', {}).get('landing_page', '')
                            tracking_url = self.config.get('urls', {}).get('tracking_url', '')
                            
                            self.email_sender.send_email(
                                template=template,
                                recipient=recipient,
                                url=landing_url,
                                tracking_url=tracking_url,
                                campaign_id=self.campaign_id
                            )
                            
                            logging.info(f"Successfully sent email to {recipient['email']}")
                            
                            # Delay between individual emails
                            time.sleep(
                                self.config['email_settings'].get('delay_between_emails', 1)
                            )
                            
                        except Exception as e:
                            logging.error(
                                f"Failed to send email to {recipient['email']}: {e}\n"
                                f"Traceback: {traceback.format_exc()}"
                            )
                            continue
                    
                    # Delay between batches
                    if i + batch_size < len(recipients):
                        delay = self.config['email_settings'].get('delay_between_batches', 5)
                        logging.info(f"Waiting {delay} seconds before next batch")
                        time.sleep(delay)
            
            logging.info(f"Email campaign {self.campaign_id} completed")
            
            # Print campaign statistics
            if self.tracker:
                stats = self.tracker.get_campaign_stats(self.campaign_id)
                logging.info(f"Campaign Statistics:\n{json.dumps(stats, indent=2)}")
            
        except Exception as e:
            logging.error(
                f"Campaign failed: {e}\n"
                f"Traceback: {traceback.format_exc()}"
            )
            raise
        finally:
            # Cleanup
            if self.tracking_server:
                self.tracking_server.stop()
            if self.ngrok_handler:
                self.ngrok_handler.cleanup()

def main():
    """Main function to handle command line arguments and run the campaign."""
    parser = argparse.ArgumentParser(description='Send email campaign')
    parser.add_argument('--config', required=True, help='Path to configuration file')
    parser.add_argument('--recipients', required=True, help='Path to recipients JSON file')
    parser.add_argument('--templates', nargs='*', help='Specific template names to use')
    parser.add_argument('--campaign-id', help='Optional campaign ID for tracking')
    parser.add_argument('--test-mode', action='store_true', 
                       help='Run in test mode (sends to first recipient only)')
    parser.add_argument('--validate-only', action='store_true',
                       help='Validate configuration without sending')
    parser.add_argument('--debug', action='store_true',
                       help='Enable debug logging')
    parser.add_argument('--skip-environment-check', action='store_true',
                       help='Skip sandbox environment checking')
    
    args = parser.parse_args()
    
    try:
        # Initialize campaign
        campaign = EmailCampaign(
            config_path=args.config,
            campaign_id=args.campaign_id,
            skip_environment_check=args.skip_environment_check
        )
        
        # Set debug logging if requested
        if args.debug:
            logging.getLogger().setLevel(logging.DEBUG)
            
            # Show sandbox and Ngrok status in debug mode
            sandbox_status = campaign.check_sandbox_status()
            ngrok_status = campaign.get_ngrok_status()
            
            logging.debug("Environment Status:")
            logging.debug("Sandbox Detection Status:")
            logging.debug(json.dumps(sandbox_status, indent=2))
            logging.debug("Ngrok Status:")
            logging.debug(json.dumps(ngrok_status, indent=2))
        
        # Validate campaign
        if not campaign.validate_campaign(args.recipients, args.templates):
            logging.error("Campaign validation failed")
            return 1
            
        if args.validate_only:
            logging.info("Campaign validation successful")
            return 0
        
        # Run campaign
        campaign.send_campaign(
            recipients_path=args.recipients,
            template_names=args.templates,
            test_mode=args.test_mode
        )
        
        return 0
        
    except Exception as e:
        logging.error(
            f"Error running campaign: {e}\n"
            f"Traceback: {traceback.format_exc()}"
        )
        return 1

if __name__ == "__main__":
    sys.exit(main())