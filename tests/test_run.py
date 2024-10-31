#!/usr/bin/env python3
import os
import sys
import json

# Add the project root to the Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from email_campaign.main import EmailCampaign

def test_campaign():
    """Run a test campaign with minimal configuration."""
    try:
        # Initialize campaign
        campaign = EmailCampaign(
            config_path='config.json',
        )
        
        # Run campaign in test mode
        campaign.send_campaign(
            recipients_path='recipients.json',
            test_mode=True  # Only sends to first recipient
        )
        
        print("Test campaign completed successfully!")
        
    except Exception as e:
        print(f"Test campaign failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_run()