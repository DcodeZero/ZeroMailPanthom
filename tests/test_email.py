#!/usr/bin/env python3
import os
import sys

def check_structure():
    """Check project structure."""
    required_files = [
        'setup.py',
        'email_campaign/__init__.py',
        'email_campaign/email_tracking.py',
        'email_campaign/email_sender.py',
        'email_campaign/main.py',
        'email_campaign/utils/__init__.py'
    ]
    
    required_dirs = [
        'email_campaign',
        'email_campaign/utils',
        'templates',
        'attachments',
        'logs',
        'data'
    ]
    
    print("Checking project structure...")
    
    # Check directories
    for directory in required_dirs:
        if os.path.isdir(directory):
            print(f"✓ Directory found: {directory}")
        else:
            print(f"× Missing directory: {directory}")
    
    # Check files
    for file in required_files:
        if os.path.isfile(file):
            print(f"✓ File found: {file}")
        else:
            print(f"× Missing file: {file}")

def test_imports():
    """Test imports."""
    print("\nTesting imports...")
    
    try:
        from email_campaign.email_tracking import EmailTracker
        print("✓ Successfully imported EmailTracker")
    except ImportError as e:
        print(f"× Failed to import EmailTracker: {e}")
    
    try:
        from email_campaign.email_sender import EmailConfig, EmailTemplate, EmailSender
        print("✓ Successfully imported EmailSender components")
    except ImportError as e:
        print(f"× Failed to import EmailSender components: {e}")

def print_python_path():
    """Print Python path information."""
    print("\nPython environment information:")
    print(f"Python version: {sys.version}")
    print(f"Python executable: {sys.executable}")
    print("\nPYTHONPATH:")
    for path in sys.path:
        print(f"  {path}")

if __name__ == "__main__":
    check_structure()
    test_imports()
    print_python_path()