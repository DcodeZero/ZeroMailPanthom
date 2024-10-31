#!/usr/bin/env python3
import socket
import socks
import requests
import time
import logging
from typing import Dict, Optional
import json
import stem
from stem import Signal
from stem.control import Controller
import traceback
import os

class TorHandler:
    def __init__(self, config: Dict):
        """Initialize Tor handler with configuration.
        
        Args:
            config (Dict): Configuration dictionary containing Tor settings
                {
                    'tor': {
                        'enabled': bool,
                        'socks_port': int,
                        'control_port': int,
                        'control_password': str,
                        'circuit_refresh_interval': int,
                        'circuit_build_timeout': int,
                        'retry_attempts': int,
                        'retry_delay': int,
                        'force_tor': bool
                    }
                }
        """
        self.config = config.get('tor', {})
        self.enabled = self.config.get('enabled', False)
        self.socks_port = self.config.get('socks_port', 9050)
        self.control_port = self.config.get('control_port', 9051)
        self.control_password = self.config.get('control_password', None)
        self.refresh_interval = self.config.get('circuit_refresh_interval', 600)
        self.circuit_timeout = self.config.get('circuit_build_timeout', 10)
        self.max_retries = self.config.get('retry_attempts', 3)
        self.retry_delay = self.config.get('retry_delay', 5)
        self.force_tor = self.config.get('force_tor', False)
        
        # Initialize tracking variables
        self.last_refresh = 0
        self.current_ip = None
        
        # Set up logging
        self.setup_logging()
        
        if self.enabled:
            self._setup_tor()

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _setup_tor(self):
        """Set up Tor connection and SOCKS proxy."""
        try:
            # Configure SOCKS proxy
            socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", self.socks_port)
            socket.socket = socks.socksocket
            
            # Test Tor connection
            self._test_tor_connection()
            self.current_ip = self._get_current_ip()
            self.logger.info(f"Tor connection established. Current IP: {self.current_ip}")
            
        except Exception as e:
            error_msg = f"Failed to set up Tor connection: {e}\n{traceback.format_exc()}"
            self.logger.error(error_msg)
            if self.force_tor:
                raise RuntimeError(error_msg)

    def _test_tor_connection(self) -> bool:
        """Test Tor connection and verify it's working.
        
        Returns:
            bool: True if connection is successful
            
        Raises:
            RuntimeError: If connection fails after max retries
        """
        retry_count = 0
        while retry_count < self.max_retries:
            try:
                response = requests.get(
                    'https://check.torproject.org/api/ip',
                    timeout=10,
                    proxies=self.get_proxy_settings()
                )
                data = response.json()
                
                if data.get('IsTor', False):
                    self.logger.info("Successfully connected to Tor network")
                    return True
                else:
                    raise Exception("Connected, but not through Tor network")
                
            except Exception as e:
                retry_count += 1
                if retry_count < self.max_retries:
                    self.logger.warning(f"Tor connection attempt {retry_count} failed: {e}")
                    time.sleep(self.retry_delay)
                else:
                    raise RuntimeError(f"Failed to verify Tor connection after {self.max_retries} attempts")

    def _get_current_ip(self) -> Optional[str]:
        """Get current IP address through Tor.
        
        Returns:
            Optional[str]: Current IP address or None if request fails
        """
        try:
            response = requests.get(
                'https://api.ipify.org?format=json',
                proxies=self.get_proxy_settings()
            )
            return response.json()['ip']
        except Exception as e:
            self.logger.error(f"Failed to get current IP: {e}")
            return None

    def refresh_circuit(self) -> bool:
        """Refresh Tor circuit and verify IP change.
        
        Returns:
            bool: True if circuit was refreshed successfully
        """
        if not self.enabled:
            return False
            
        current_time = time.time()
        if current_time - self.last_refresh < self.refresh_interval:
            return False
            
        try:
            # Store old IP for verification
            old_ip = self._get_current_ip()
            
            # Send signal to refresh circuit
            with Controller.from_port(port=self.control_port) as controller:
                if self.control_password:
                    controller.authenticate(password=self.control_password)
                else:
                    controller.authenticate()
                
                controller.signal(Signal.NEWNYM)
                self.last_refresh = current_time
                self.logger.info("Sent signal to refresh Tor circuit")
                
                # Wait for circuit to be built
                time.sleep(self.circuit_timeout)
                
                # Verify IP changed
                new_ip = self._get_current_ip()
                if new_ip and new_ip != old_ip:
                    self.current_ip = new_ip
                    self.logger.info(f"Tor circuit refreshed successfully. New IP: {new_ip}")
                    return True
                else:
                    self.logger.warning("Tor circuit refresh may have failed: IP did not change")
                    return False
                
        except Exception as e:
            error_msg = f"Failed to refresh Tor circuit: {e}"
            self.logger.error(error_msg)
            if self.force_tor:
                raise RuntimeError(error_msg)
            return False

    def get_proxy_settings(self) -> Dict:
        """Get SOCKS proxy settings for requests.
        
        Returns:
            Dict: Proxy configuration dictionary
        """
        if not self.enabled:
            return {}
            
        return {
            'http': f'socks5h://127.0.0.1:{self.socks_port}',
            'https': f'socks5h://127.0.0.1:{self.socks_port}'
        }

    def check_tor_status(self) -> Dict:
        """Check Tor connection status and details.
        
        Returns:
            Dict: Status information including circuits and IP
        """
        if not self.enabled:
            return {'enabled': False, 'status': 'disabled'}
            
        try:
            current_ip = self._get_current_ip()
            
            # Get circuit information
            circuits = []
            with Controller.from_port(port=self.control_port) as controller:
                if self.control_password:
                    controller.authenticate(password=self.control_password)
                else:
                    controller.authenticate()
                
                for circ in controller.get_circuits():
                    circuits.append({
                        'id': circ.id,
                        'status': circ.status,
                        'purpose': circ.purpose,
                        'path': [node[0] for node in circ.path],
                        'build_flags': circ.build_flags,
                    })
                
            return {
                'enabled': True,
                'status': 'connected',
                'current_ip': current_ip,
                'last_refresh': time.strftime(
                    '%Y-%m-%d %H:%M:%S',
                    time.localtime(self.last_refresh)
                ),
                'circuits': circuits,
                'proxy_settings': self.get_proxy_settings()
            }
                
        except Exception as e:
            error_msg = f"Error checking Tor status: {e}"
            self.logger.error(error_msg)
            return {
                'enabled': True,
                'status': 'error',
                'error': str(e)
            }

    def verify_connection(self) -> bool:
        """Verify Tor connection is working properly.
        
        Returns:
            bool: True if connection is verified
        """
        try:
            # Check basic connection
            self._test_tor_connection()
            
            # Verify IP masking
            original_ip = requests.get('https://api.ipify.org?format=json').json()['ip']
            tor_ip = self._get_current_ip()
            
            if original_ip == tor_ip:
                raise Exception("Tor is not masking IP address")
            
            # Test circuit refresh
            if not self.refresh_circuit():
                raise Exception("Failed to refresh Tor circuit")
            
            return True
            
        except Exception as e:
            error_msg = f"Tor connection verification failed: {e}"
            self.logger.error(error_msg)
            if self.force_tor:
                raise RuntimeError(error_msg)
            return False

    def cleanup(self):
        """Clean up Tor connection and reset socket."""
        try:
            # Reset socket to default
            socket.socket = socket._socketobject
            self.logger.info("Tor connection cleaned up")
        except Exception as e:
            self.logger.error(f"Error during Tor cleanup: {e}")

def test_tor_handler():
    """Test Tor handler functionality."""
    # Example configuration
    config = {
        'tor': {
            'enabled': True,
            'socks_port': 9050,
            'control_port': 9051,
            'control_password': None,
            'circuit_refresh_interval': 1000,
            'circuit_build_timeout': 10,
            'retry_attempts': 5,
            'retry_delay': 8,
            'force_tor': False
        }
    }
    
    try:
        # Initialize handler
        handler = TorHandler(config)
        
        # Check initial status
        print("\nInitial Tor Status:")
        print(json.dumps(handler.check_tor_status(), indent=2))
        
        # Test circuit refresh
        print("\nRefreshing Circuit:")
        if handler.refresh_circuit():
            print("Circuit refresh successful")
        else:
            print("Circuit refresh failed")
        
        # Check final status
        print("\nFinal Tor Status:")
        print(json.dumps(handler.check_tor_status(), indent=2))
        
    except Exception as e:
        print(f"Test failed: {e}")
        print(traceback.format_exc())
    finally:
        handler.cleanup()

if __name__ == "__main__":
    test_tor_handler()