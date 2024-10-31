#!/usr/bin/env python3
import os
import sys

def test_imports():
    """Test all required imports."""
    try:
        print("Testing imports...")
        
        print("1. Testing email_sender imports...")
        from email_campaign.email_sender import EmailConfig, EmailTemplate, EmailSender
        print("✓ email_sender imports successful")
        
        print("\n2. Testing email_tracking imports...")
        from email_campaign.email_tracking import EmailTracker
        print("✓ email_tracking imports successful")
        
        print("\n3. Testing tor_handler imports...")
        from email_campaign.tor_handler import TorHandler
        print("✓ tor_handler imports successful")
        
        print("\n4. Testing main imports...")
        from email_campaign.main import main
        print("✓ main imports successful")
        
        print("\nAll imports successful!")
        return True
        
    except Exception as e:
        print(f"\nError during import testing: {e}")
        print("\nDebug information:")
        print(f"Current directory: {os.getcwd()}")
        print(f"Python path: {sys.path}")
        print(f"Directory contents: {os.listdir('.')}")
        if os.path.exists('email_campaign'):
            print(f"email_campaign contents: {os.listdir('email_campaign')}")
        return False

if __name__ == "__main__":
    success = test_imports()
    sys.exit(0 if success else 1)