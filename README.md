# ZeroMailPanthom

# Email Campaign System

A comprehensive email campaign system with tracking capabilities, security features, and anonymous routing options.

## Table of Contents
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Project Structure](#project-structure)
- [Configuration](#configuration)
- [Usage](#usage)
- [Security Features](#security-features)
- [Templates](#templates)
- [Tracking System](#tracking-system)
- [Anonymous Routing](#anonymous-routing)
- [Troubleshooting](#troubleshooting)
- [Security Considerations](#security-considerations)

## Features

### Core Features
- Batch email sending with customizable delays
- HTML and plain text email support
- Email open and click tracking
- Anonymous routing through Tor
- Sandbox detection and evasion
- Attachment support
- Template personalization
- Campaign analytics

### Security Features
- Tor network integration
- HTTPS tracking endpoints
- Sandbox detection
- Rate limiting
- IP rotation
- SSL/TLS encryption

### Tracking Capabilities
- Email opens
- Link clicks
- Device and client detection
- Geographic tracking
- Engagement analytics

## Prerequisites

### System Requirements
- Python 3.8 or higher
- Tor service (optional, for anonymous routing)
- SMTP server or API credentials
- Ngrok account (for tracking)

### Required Python Packages
```bash
pip install -r requirements.txt
```

Core dependencies:
```
requests>=2.31.0
pyngrok>=7.0.0
stem>=1.8.2
PySocks>=1.7.1
Flask>=3.0.2
SQLite-Utils>=3.35.1
cryptography>=42.0.2
```

## Installation

1. Clone the repository:
```bash
git clone https://github.com/DcodeZero/ZeroMailPanthom.git
cd ZeroMailPanthom
```

2. Create virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up directory structure:
```bash
mkdir templates attachments logs data
```

## Project Structure

```plaintext
ZeroMailPanthom_project/
├── ZeroMailPanthom/
│   ├── __init__.py
│   ├── main.py              # Main campaign orchestration
│   ├── email_sender.py      # Email sending functionality
│   ├── email_tracking.py    # Tracking implementation
│   ├── tor_handler.py       # Tor network integration
│   ├── ngrok_handler.py     # Tracking URL management
│   └── sandbox_evasion.py   # Security features
├── config.json              # Configuration file
├── requirements.txt         # Dependencies
├── templates/              # Email templates
├── attachments/           # Email attachments
├── logs/                 # Log files
└── data/                # SQLite database and tracking data
```

## Configuration

### Basic Configuration (config.json)
```json
{
    "smtp": {
        "host": "smtp.example.com",
        "port": 587,
        "username": "user@example.com",
        "password": "your_password",
        "from_address": {
            "email": "sender@example.com",
            "name": "Sender Name"
        }
    },
    "email_settings": {
        "batch_size": 50,
        "delay_between_batches": 5,
        "delay_between_emails": 1,
        "max_retries": 3,
        "retry_delay": 5
    },
    "tracking": {
        "enabled": true,
        "database_path": "data/tracking.db"
    },
    "ngrok": {
        "enabled": true,
        "auth_token": "your_ngrok_auth_token",
        "tunnel_config": {
            "port": 8080
        }
    },
    "tor": {
        "enabled": false,
        "socks_port": 9050,
        "control_port": 9051,
        "circuit_refresh_interval": 600
    }
}
```

### Recipients Configuration (recipients.json)
```json
{
    "targets": [
        {
            "email": "recipient@example.com",
            "first_name": "John",
            "last_name": "Doe",
            "custom_field": "value"
        }
    ]
}
```

## Usage

### Basic Usage

```python
from email_campaign.main import EmailCampaign

# Initialize campaign
campaign = EmailCampaign(
    config_path='config.json',
    campaign_id='test_campaign'
)

# Send campaign
campaign.send_campaign(
    recipients_path='recipients.json',
    template_names=['template1.html'],
    test_mode=True
)
```

### Command Line Usage
```bash
python -m email_campaign.cli --config config.json --recipients recipients.json --test-mode
```

### CLI Options
- `--config`: Path to configuration file
- `--recipients`: Path to recipients file
- `--templates`: Specific template names (optional)
- `--campaign-id`: Custom campaign ID (optional)
- `--test-mode`: Send to first recipient only
- `--validate-only`: Validate configuration without sending
- `--debug`: Enable debug logging
- `--skip-environment-check`: Skip sandbox detection

## Templates

### Template Format
```html
Subject: Welcome {{.FirstName}}!
Content-Type: text/html
Attachments: document.pdf,brochure.pdf

<html>
<body>
    <h1>Hello {{.FirstName}} {{.LastName}},</h1>
    <p>Welcome to our platform!</p>
    <a href="{{.URL}}">Click here</a>
</body>
</html>
```

### Available Template Variables
- `{{.FirstName}}`: Recipient's first name
- `{{.LastName}}`: Recipient's last name
- `{{.Email}}`: Recipient's email
- `{{.URL}}`: Landing page URL

## Tracking System

### Tracking Features
- Email opens via pixel tracking
- Link click tracking
- Device and browser detection
- Geographic location tracking
- Engagement analytics

### Tracking Setup
1. Enable tracking in config.json:
```json
{
    "tracking": {
        "enabled": true,
        "database_path": "data/tracking.db"
    },
    "ngrok": {
        "enabled": true,
        "auth_token": "your_token"
    }
}
```

2. Tracking data is stored in SQLite database with tables:
- emails: Sent email records
- opens: Email open events
- clicks: Link click events
- bounces: Email bounce records

## Anonymous Routing

### Tor Setup
1. Install Tor service
2. Enable in config.json:
```json
{
    "tor": {
        "enabled": true,
        "socks_port": 9050,
        "control_port": 9051,
        "circuit_refresh_interval": 600
    }
}
```

### IP Rotation
- Automatic circuit refresh
- Configurable refresh interval
- IP verification
- Connection testing

## Security Considerations

### Best Practices
1. Always use HTTPS for tracking URLs
2. Implement rate limiting
3. Enable Tor for anonymity
4. Use sandbox detection
5. Rotate IPs regularly
6. Monitor for bounces
7. Handle unsubscribes properly

### Sandbox Detection
The system checks for:
- System resources
- VM artifacts
- Hardware characteristics
- User interaction patterns
- Uptime and processes

## Troubleshooting

### Common Issues
1. SMTP Connection Errors
   - Check credentials
   - Verify port numbers
   - Test server connection

2. Tracking Issues
   - Verify Ngrok setup
   - Check database permissions
   - Ensure proper URL configuration

3. Tor Connection Problems
   - Verify Tor service is running
   - Check port configurations
   - Test circuit refresh

### Logging
- Logs are stored in `logs/` directory
- Debug mode: `--debug` flag
- Rotating log files with timestamp

## Security Notice
This tool is for legitimate email campaigns only. Ensure compliance with:
- CAN-SPAM Act
- GDPR regulations
- Email service provider terms
- Local privacy laws
