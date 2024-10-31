#!/usr/bin/env python3
import os
import json
import logging
import time
import requests
from pyngrok import ngrok
from typing import Dict, Optional, List
import signal
import atexit

class NgrokHandler:
    def __init__(self, config: Dict):
        """Initialize Ngrok handler with configuration."""
        self.config = config.get('ngrok', {})
        self.enabled = self.config.get('enabled', False)
        self.tunnel_config = self.config.get('tunnel_config', {})
        self.tunnels = {}
        self.setup_logging()
        
        if self.enabled:
            self._setup_ngrok()
            atexit.register(self.cleanup)
            signal.signal(signal.SIGTERM, self._signal_handler)

    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def _setup_ngrok(self):
        """Setup Ngrok configuration."""
        try:
            auth_token = self.config.get('auth_token')
            if auth_token:
                ngrok.set_auth_token(auth_token)
                self.logger.info("Ngrok configuration initialized successfully")
            else:
                self.logger.warning("No Ngrok auth token provided")
            
        except Exception as e:
            self.logger.error(f"Failed to setup Ngrok: {e}")
            raise

    def start_tunnel(self, port: int = 8080, protocol: str = 'http', name: str = None) -> Optional[str]:
        """Start an Ngrok tunnel."""
        try:
            # Close existing tunnel with same name if exists
            if name and name in self.tunnels:
                self.stop_tunnel(name)
            
            # Basic tunnel configuration
            tunnel_config = {
                "addr": f"http://localhost:{port}",
                "proto": protocol,
            }
            
            # Add optional configurations
            if self.tunnel_config.get('subdomain'):
                tunnel_config["subdomain"] = self.tunnel_config['subdomain']
            if self.tunnel_config.get('hostname'):
                tunnel_config["hostname"] = self.tunnel_config['hostname']
            
            # Start tunnel with simplified configuration
            tunnel = ngrok.connect(**tunnel_config)
            public_url = tunnel.public_url
            
            # Store tunnel
            if name:
                self.tunnels[name] = tunnel
            else:
                self.tunnels[public_url] = tunnel
            
            self.logger.info(f"Started tunnel: {public_url}")
            return public_url
            
        except Exception as e:
            self.logger.error(f"Failed to start tunnel: {e}")
            return None

    def stop_tunnel(self, name: str = None):
        """Stop specific Ngrok tunnel or all tunnels."""
        try:
            if name:
                if name in self.tunnels:
                    ngrok.disconnect(self.tunnels[name].public_url)
                    del self.tunnels[name]
                    self.logger.info(f"Stopped tunnel: {name}")
            else:
                for tunnel in list(self.tunnels.values()):
                    ngrok.disconnect(tunnel.public_url)
                self.tunnels.clear()
                self.logger.info("Stopped all tunnels")
                
        except Exception as e:
            self.logger.error(f"Error stopping tunnel: {e}")

    def get_tunnel_info(self) -> Dict:
        """Get information about current tunnels."""
        try:
            tunnels_info = []
            for name, tunnel in self.tunnels.items():
                tunnels_info.append({
                    "name": name,
                    "public_url": tunnel.public_url,
                    "proto": tunnel.proto
                })
            
            return {
                "status": "running" if self.tunnels else "no_tunnels",
                "tunnels": tunnels_info
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get tunnel info: {e}")
            return {"status": "error", "error": str(e)}

    def _signal_handler(self, signum, frame):
        """Handle termination signals."""
        self.logger.info(f"Received signal {signum}")
        self.cleanup()

    def cleanup(self):
        """Cleanup Ngrok resources."""
        try:
            self.stop_tunnel()  # Stop all tunnels
            ngrok.kill()
            self.logger.info("Ngrok cleanup completed")
        except Exception as e:
            self.logger.error(f"Failed to cleanup Ngrok: {e}")

class TrackingServer:
    def __init__(self, config: Dict, ngrok_handler: NgrokHandler = None):
        """Initialize tracking server with Ngrok integration."""
        self.config = config
        self.ngrok_handler = ngrok_handler or NgrokHandler(config)
        self.public_url = None
        self.setup_logging()

    def setup_logging(self):
        """Configure logging."""
        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(logging.INFO)

    def start(self, port: int = 8080) -> Optional[str]:
        """Start tracking server with Ngrok tunnel."""
        try:
            self.public_url = self.ngrok_handler.start_tunnel(
                port=port,
                protocol='http',
                name='tracking_server'
            )
            
            if self.public_url:
                # Convert http to https if needed
                if self.public_url.startswith('http:'):
                    self.public_url = 'https:' + self.public_url[5:]
                    
                self.logger.info(f"Tracking server started: {self.public_url}")
                return self.public_url
            
            return None
            
        except Exception as e:
            self.logger.error(f"Failed to start tracking server: {e}")
            return None

    def stop(self):
        """Stop tracking server and tunnel."""
        try:
            if self.ngrok_handler:
                self.ngrok_handler.stop_tunnel('tracking_server')
            self.public_url = None
            self.logger.info("Tracking server stopped")
        except Exception as e:
            self.logger.error(f"Failed to stop tracking server: {e}")