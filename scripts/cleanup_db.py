#!/usr/bin/env python3
import os
import sqlite3
import logging

def cleanup_database(db_path: str):
    """Clean up and reinitialize the tracking database."""
    try:
        # Backup existing database if it exists
        if os.path.exists(db_path):
            backup_path = f"{db_path}.backup"
            os.rename(db_path, backup_path)
            print(f"Backed up existing database to {backup_path}")
        
        # Initialize new database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
            CREATE TABLE emails (
                email_id TEXT PRIMARY KEY,
                campaign_id TEXT,
                recipient_email TEXT,
                template_name TEXT,
                sent_time TIMESTAMP,
                status TEXT,
                tracking_pixel_id TEXT UNIQUE,
                bounce_info TEXT,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE opens (
                open_id TEXT PRIMARY KEY,
                email_id TEXT,
                open_time TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT,
                country TEXT,
                device_type TEXT,
                client_info TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (email_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE clicks (
                click_id TEXT PRIMARY KEY,
                email_id TEXT,
                link_url TEXT,
                click_time TIMESTAMP,
                user_agent TEXT,
                ip_address TEXT,
                country TEXT,
                device_type TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (email_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE bounces (
                bounce_id TEXT PRIMARY KEY,
                email_id TEXT,
                bounce_time TIMESTAMP,
                bounce_type TEXT,
                bounce_reason TEXT,
                description TEXT,
                FOREIGN KEY (email_id) REFERENCES emails (email_id)
            )
        ''')
        
        # Create indexes
        cursor.execute('CREATE INDEX idx_campaign_id ON emails(campaign_id)')
        cursor.execute('CREATE INDEX idx_recipient_email ON emails(recipient_email)')
        cursor.execute('CREATE INDEX idx_email_id ON opens(email_id)')
        cursor.execute('CREATE INDEX idx_click_email_id ON clicks(email_id)')
        
        conn.commit()
        conn.close()
        
        print("Database cleaned up and reinitialized successfully")
        
    except Exception as e:
        print(f"Error cleaning up database: {e}")
        raise

if __name__ == "__main__":
    db_path = 'data/tracking.db'
    cleanup_database(db_path)