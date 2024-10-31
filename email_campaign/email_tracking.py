#!/usr/bin/env python3
import os
import json
import sqlite3
from datetime import datetime, timedelta
import uuid
import logging
import base64
from typing import Dict, List, Optional, Union
from urllib.parse import urlencode
import hashlib
import traceback

class EmailTracker:
    def __init__(self, db_path: str = 'data/tracking.db'):
        """Initialize email tracker with database."""
        self.db_path = db_path
        self._init_database()

    def _init_database(self):
        """Initialize SQLite database for tracking."""
        try:
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Drop existing tables if they exist
                cursor.execute('DROP TABLE IF EXISTS clicks')
                cursor.execute('DROP TABLE IF EXISTS opens')
                cursor.execute('DROP TABLE IF EXISTS bounces')
                cursor.execute('DROP TABLE IF EXISTS emails')
                
                # Create emails table
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
                
                # Create opens table
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
                
                # Create clicks table
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
                
                # Create bounces table
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
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_campaign_id ON emails(campaign_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_recipient_email ON emails(recipient_email)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_email_id ON opens(email_id)')
                cursor.execute('CREATE INDEX IF NOT EXISTS idx_click_email_id ON clicks(email_id)')
                
                conn.commit()
                logging.info("Tracking database initialized successfully")
                
        except Exception as e:
            error_msg = f"Failed to initialize tracking database: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def track_email_send(self, recipient_email: str, template_name: str, 
                        campaign_id: str, metadata: Dict = None) -> str:
        """Record an email being sent."""
        try:
            email_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT INTO emails (
                        email_id, campaign_id, recipient_email, template_name,
                        sent_time, status, metadata
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    email_id,
                    campaign_id,
                    recipient_email,
                    template_name,
                    datetime.now().isoformat(),
                    'sent',
                    json.dumps(metadata) if metadata else None
                ))
                
                conn.commit()
                logging.debug(f"Tracked email send to {recipient_email}")
                return email_id
                
        except Exception as e:
            error_msg = f"Failed to track email send: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def create_tracking_pixel(self, email_id: str) -> str:
        """Create a unique tracking pixel ID for an email."""
        try:
            pixel_id = str(uuid.uuid4())
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    UPDATE emails 
                    SET tracking_pixel_id = ? 
                    WHERE email_id = ?
                ''', (pixel_id, email_id))
                
                conn.commit()
                logging.debug(f"Created tracking pixel for email {email_id}")
                return pixel_id
                
        except Exception as e:
            error_msg = f"Failed to create tracking pixel: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def track_open(self, pixel_id: str, user_agent: str = None, 
                  ip_address: str = None, country: str = None) -> None:
        """Record an email being opened."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Get email_id from pixel_id
                cursor.execute('''
                    SELECT email_id FROM emails 
                    WHERE tracking_pixel_id = ?
                ''', (pixel_id,))
                
                result = cursor.fetchone()
                if result:
                    email_id = result[0]
                    open_id = str(uuid.uuid4())
                    
                    # Record the open
                    cursor.execute('''
                        INSERT INTO opens (
                            open_id, email_id, open_time, user_agent,
                            ip_address, country, device_type, client_info
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        open_id,
                        email_id,
                        datetime.now().isoformat(),
                        user_agent,
                        self._hash_ip(ip_address) if ip_address else None,
                        country,
                        self._detect_device_type(user_agent),
                        self._parse_client_info(user_agent)
                    ))
                    
                    conn.commit()
                    logging.debug(f"Tracked email open for {email_id}")
                
        except Exception as e:
            error_msg = f"Failed to track email open: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def _hash_ip(self, ip_address: str) -> Optional[str]:
        """Hash IP address for privacy."""
        if not ip_address:
            return None
        return hashlib.sha256(ip_address.encode()).hexdigest()

    def _detect_device_type(self, user_agent: str) -> str:
        """Detect device type from user agent string."""
        if not user_agent:
            return 'unknown'
            
        user_agent = user_agent.lower()
        if 'mobile' in user_agent or 'android' in user_agent or 'iphone' in user_agent:
            return 'mobile'
        elif 'tablet' in user_agent or 'ipad' in user_agent:
            return 'tablet'
        else:
            return 'desktop'

    def _parse_client_info(self, user_agent: str) -> str:
        """Parse detailed client information from user agent."""
        if not user_agent:
            return json.dumps({'type': 'unknown'})
            
        info = {
            'type': self._detect_device_type(user_agent),
            'browser': self._detect_browser(user_agent),
            'os': self._detect_os(user_agent)
        }
        
        return json.dumps(info)
    def _detect_browser(self, user_agent: str) -> str:
        """Detect browser from user agent string."""
        if not user_agent:
            return 'unknown'
            
        user_agent = user_agent.lower()
        if 'chrome' in user_agent and 'chromium' not in user_agent:
            return 'chrome'
        elif 'firefox' in user_agent:
            return 'firefox'
        elif 'safari' in user_agent and 'chrome' not in user_agent:
            return 'safari'
        elif 'edge' in user_agent:
            return 'edge'
        elif 'opera' in user_agent:
            return 'opera'
        else:
            return 'unknown'

    def _detect_os(self, user_agent: str) -> str:
        """Detect operating system from user agent string."""
        if not user_agent:
            return 'unknown'
            
        user_agent = user_agent.lower()
        if 'windows' in user_agent:
            return 'windows'
        elif 'mac os' in user_agent or 'macos' in user_agent:
            return 'macos'
        elif 'linux' in user_agent:
            return 'linux'
        elif 'android' in user_agent:
            return 'android'
        elif 'ios' in user_agent or 'iphone' in user_agent or 'ipad' in user_agent:
            return 'ios'
        else:
            return 'unknown'

    def track_click(self, email_id: str, link_url: str, user_agent: str = None,
                   ip_address: str = None, country: str = None) -> None:
        """Record a link being clicked."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                click_id = str(uuid.uuid4())
                
                cursor.execute('''
                    INSERT INTO clicks (
                        click_id, email_id, link_url, click_time,
                        user_agent, ip_address, country, device_type
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    click_id,
                    email_id,
                    link_url,
                    datetime.now().isoformat(),
                    user_agent,
                    self._hash_ip(ip_address) if ip_address else None,
                    country,
                    self._detect_device_type(user_agent)
                ))
                
                conn.commit()
                logging.debug(f"Tracked link click for email {email_id}")
                
        except Exception as e:
            error_msg = f"Failed to track link click: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def track_bounce(self, email_id: str, bounce_type: str,
                    bounce_reason: str, description: str = None) -> None:
        """Record an email bounce."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                bounce_id = str(uuid.uuid4())
                
                cursor.execute('''
                    INSERT INTO bounces (
                        bounce_id, email_id, bounce_time,
                        bounce_type, bounce_reason, description
                    ) VALUES (?, ?, ?, ?, ?, ?)
                ''', (
                    bounce_id,
                    email_id,
                    datetime.now().isoformat(),
                    bounce_type,
                    bounce_reason,
                    description
                ))
                
                # Update email status
                cursor.execute('''
                    UPDATE emails 
                    SET status = ?, bounce_info = ?
                    WHERE email_id = ?
                ''', ('bounced', bounce_reason, email_id))
                
                conn.commit()
                logging.info(f"Tracked bounce for email {email_id}")
                
        except Exception as e:
            error_msg = f"Failed to track bounce: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def generate_tracking_links(self, content: str, email_id: str,
                              tracking_domain: str) -> str:
        """Replace links in content with tracking links."""
        try:
            import re
            
            def replace_link(match):
                original_url = match.group(1)
                tracking_params = {
                    'eid': email_id,
                    'url': original_url,
                    'tid': hashlib.sha256(f"{email_id}:{original_url}".encode()).hexdigest()[:12]
                }
                
                tracking_url = f"https://{tracking_domain}/click?" + urlencode(tracking_params)
                return f'href="{tracking_url}"'
                
            tracked_content = re.sub(r'href="([^"]+)"', replace_link, content)
            logging.debug(f"Generated tracking links for email {email_id}")
            return tracked_content
            
        except Exception as e:
            error_msg = f"Failed to generate tracking links: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def generate_tracking_pixel(self, email_id: str, tracking_domain: str) -> str:
        """Generate HTML for a tracking pixel."""
        try:
            pixel_id = self.create_tracking_pixel(email_id)
            return f'''
                <img src="https://{tracking_domain}/pixel/{pixel_id}"
                     width="1" height="1" alt="" style="display:none;" />
            '''
        except Exception as e:
            error_msg = f"Failed to generate tracking pixel: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def get_campaign_stats(self, campaign_id: str, 
                          start_date: datetime = None,
                          end_date: datetime = None) -> Dict:
        """Get comprehensive statistics for a campaign."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Add date range to query if specified
                date_filter = ""
                params = [campaign_id]
                if start_date and end_date:
                    date_filter = "AND sent_time BETWEEN ? AND ?"
                    params.extend([start_date.isoformat(), end_date.isoformat()])
                
                # Get total emails sent
                cursor.execute(f'''
                    SELECT COUNT(*) as total_sent,
                           COUNT(DISTINCT recipient_email) as unique_recipients
                    FROM emails 
                    WHERE campaign_id = ? {date_filter}
                ''', params)
                
                total_sent, unique_recipients = cursor.fetchone()
                
                # Get unique opens
                cursor.execute(f'''
                    SELECT COUNT(DISTINCT e.email_id) as unique_opens,
                           COUNT(o.open_id) as total_opens
                    FROM emails e
                    LEFT JOIN opens o ON e.email_id = o.email_id
                    WHERE e.campaign_id = ? {date_filter}
                ''', params)
                
                unique_opens, total_opens = cursor.fetchone()
                
                # Get unique clicks
                cursor.execute(f'''
                    SELECT COUNT(DISTINCT e.email_id) as unique_clicks,
                           COUNT(c.click_id) as total_clicks
                    FROM emails e
                    LEFT JOIN clicks c ON e.email_id = c.email_id
                    WHERE e.campaign_id = ? {date_filter}
                ''', params)
                
                unique_clicks, total_clicks = cursor.fetchone()
                
                # Get device breakdown
                cursor.execute(f'''
                    SELECT o.device_type, COUNT(DISTINCT e.email_id) as count
                    FROM emails e
                    JOIN opens o ON e.email_id = o.email_id
                    WHERE e.campaign_id = ? {date_filter}
                    GROUP BY o.device_type
                ''', params)
                
                device_breakdown = dict(cursor.fetchall())
                
                # Get bounces
                cursor.execute(f'''
                    SELECT COUNT(*) as bounces,
                           bounce_type,
                           COUNT(*) as type_count
                    FROM emails e
                    JOIN bounces b ON e.email_id = b.email_id
                    WHERE e.campaign_id = ? {date_filter}
                    GROUP BY bounce_type
                ''', params)
                
                bounce_details = {}
                total_bounces = 0
                for _, bounce_type, count in cursor.fetchall():
                    bounce_details[bounce_type] = count
                    total_bounces += count
                
                # Calculate rates
                stats = {
                    'campaign_id': campaign_id,
                    'period': {
                        'start': start_date.isoformat() if start_date else None,
                        'end': end_date.isoformat() if end_date else None
                    },
                    'delivery': {
                        'total_sent': total_sent,
                        'unique_recipients': unique_recipients,
                        'bounces': total_bounces,
                        'bounce_details': bounce_details,
                        'bounce_rate': (total_bounces / total_sent * 100) if total_sent > 0 else 0
                    },
                    'engagement': {
                        'unique_opens': unique_opens,
                        'total_opens': total_opens,
                        'unique_clicks': unique_clicks,
                        'total_clicks': total_clicks,
                        'open_rate': (unique_opens / total_sent * 100) if total_sent > 0 else 0,
                        'click_rate': (unique_clicks / total_sent * 100) if total_sent > 0 else 0,
                        'click_to_open_rate': (unique_clicks / unique_opens * 100) if unique_opens > 0 else 0
                    },
                    'devices': device_breakdown,
                    'timestamp': datetime.now().isoformat()
                }
                
                logging.info(f"Retrieved campaign stats for {campaign_id}")
                return stats
                
        except Exception as e:
            error_msg = f"Failed to get campaign stats: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def get_recipient_activity(self, email: str, days: int = 30) -> List[Dict]:
        """Get activity history for a specific recipient."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                since_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                cursor.execute('''
                    SELECT e.email_id,
                           e.campaign_id,
                           e.template_name,
                           e.sent_time,
                           COUNT(DISTINCT o.open_id) as opens,
                           COUNT(DISTINCT c.click_id) as clicks,
                           e.status,
                           e.bounce_info
                    FROM emails e
                    LEFT JOIN opens o ON e.email_id = o.email_id
                    LEFT JOIN clicks c ON e.email_id = c.email_id
                    WHERE e.recipient_email = ?
                    AND e.sent_time >= ?
                    GROUP BY e.email_id
                    ORDER BY e.sent_time DESC
                ''', (email, since_date))
                
                activity = []
                for row in cursor.fetchall():
                    activity.append({
                        'email_id': row[0],
                        'campaign_id': row[1],
                        'template': row[2],
                        'sent_time': row[3],
                        'opens': row[4],
                        'clicks': row[5],
                        'status': row[6],
                        'bounce_info': row[7]
                    })
                
                return activity
                
        except Exception as e:
            error_msg = f"Failed to get recipient activity: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)

    def cleanup_old_data(self, days: int = 90) -> None:
        """Clean up tracking data older than specified days."""
        try:
            cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Delete old data from all tables
                for table in ['opens', 'clicks', 'bounces', 'emails']:
                    if table == 'emails':
                        cursor.execute(
                            f'DELETE FROM {table} WHERE sent_time < ?',
                            (cutoff_date,)
                        )
                    else:
                        cursor.execute(f'''
                            DELETE FROM {table}
                            WHERE email_id IN (
                                SELECT email_id FROM emails
                                WHERE sent_time < ?
                            )
                        ''', (cutoff_date,))
                
                conn.commit()
                logging.info(f"Cleaned up tracking data older than {days} days")
                
        except Exception as e:
            error_msg = f"Failed to clean up old data: {e}\n{traceback.format_exc()}"
            logging.error(error_msg)
            raise RuntimeError(error_msg)