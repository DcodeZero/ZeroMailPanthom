from flask import Flask, request, send_file, redirect
import logging
from email_tracking import EmailTracker
from datetime import datetime
import os

app = Flask(__name__)
tracker = EmailTracker(db_path='data/tracking.db')

# Create a 1x1 transparent pixel
PIXEL_DATA = b'GIF89a\x01\x00\x01\x00\x80\x00\x00\x00\x00\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,\x00\x00\x00\x00\x01\x00\x01\x00\x00\x02\x02D\x01\x00;'

def save_pixel():
    """Save the tracking pixel if it doesn't exist."""
    pixel_path = 'static/pixel.gif'
    os.makedirs('static', exist_ok=True)
    
    if not os.path.exists(pixel_path):
        with open(pixel_path, 'wb') as f:
            f.write(PIXEL_DATA)

@app.route('/pixel/<pixel_id>')
def track_open(pixel_id):
    """Handle tracking pixel requests."""
    try:
        tracker.track_open(
            pixel_id=pixel_id,
            user_agent=request.headers.get('User-Agent'),
            ip_address=request.remote_addr
        )
        return send_file('static/pixel.gif', mimetype='image/gif')
    except Exception as e:
        logging.error(f"Error tracking open: {e}")
        return send_file('static/pixel.gif', mimetype='image/gif')

@app.route('/click')
def track_click():
    """Handle link click tracking."""
    try:
        email_id = request.args.get('eid')
        original_url = request.args.get('url')
        
        if email_id and original_url:
            tracker.track_click(
                email_id=email_id,
                link_url=original_url,
                user_agent=request.headers.get('User-Agent'),
                ip_address=request.remote_addr
            )
        
        return redirect(original_url)
    except Exception as e:
        logging.error(f"Error tracking click: {e}")
        return redirect(original_url)

@app.route('/status')
def status():
    """Check if tracking server is running."""
    return {
        'status': 'ok',
        'timestamp': datetime.now().isoformat(),
        'tracking_enabled': True
    }

if __name__ == '__main__':
    # Ensure the pixel exists
    save_pixel()
    
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    # Run the server
    app.run(host='0.0.0.0', port=8080, debug=True)