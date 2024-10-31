#!/usr/bin/env python3
from email_campaign import EmailTracker, EmailConfig, EmailSender, TRACKING_AVAILABLE
import logging

def test_tracking():
    """Test tracking functionality."""
    print("\nTesting Email Tracking:")
    print(f"Tracking Available: {TRACKING_AVAILABLE}")
    
    try:
        # Initialize tracker
        tracker = EmailTracker(db_path='data/tracking.db')
        print("✓ Successfully initialized EmailTracker")
        
        # Test tracking functionality
        email_id = tracker.track_email_send(
            recipient_email='test@example.com',
            template_name='test_template.txt',
            campaign_id='TEST_001'
        )
        print(f"✓ Successfully tracked email send with ID: {email_id}")
        
        # Test pixel tracking
        pixel_id = tracker.create_tracking_pixel(email_id)
        print(f"✓ Successfully created tracking pixel with ID: {pixel_id}")
        
        return True
        
    except Exception as e:
        print(f"× Error testing tracking: {e}")
        return False

def main():
    # Set up logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    if test_tracking():
        print("\nAll tracking tests passed successfully!")
    else:
        print("\nTracking tests failed!")

if __name__ == "__main__":
    main()