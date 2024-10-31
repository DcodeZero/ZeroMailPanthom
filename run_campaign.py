#!/usr/bin/env python3
import os
import sys
import argparse

def setup_environment():
    """Set up environment variables and paths."""
    # Add project root to Python path
    project_root = os.path.dirname(os.path.abspath(__file__))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    # Create necessary directories
    directories = ['templates', 'attachments', 'logs', 'data']
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

if __name__ == "__main__":
    # Set up environment
    setup_environment()
    
    # Import after environment setup
    try:
        from email_campaign.main import main
    except ImportError as e:
        print(f"Import error: {e}")
        print("Make sure all required files are in the correct locations.")
        sys.exit(1)
    
    # Run the campaign
    sys.exit(main())