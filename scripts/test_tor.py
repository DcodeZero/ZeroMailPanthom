#!/usr/bin/env python3
import requests
import stem
import stem.control
import socks
import socket
import json
import time

def test_tor_connection():
    """Test Tor connection and circuit creation."""
    try:
        # Configure SOCKS proxy
        socks.set_default_proxy(socks.SOCKS5, "127.0.0.1", 9050)
        socket.socket = socks.socksocket
        
        # Test connection
        print("Testing Tor connection...")
        response = requests.get('https://check.torproject.org/api/ip')
        data = response.json()
        
        if data.get('IsTor', False):
            print("✓ Successfully connected to Tor")
            print(f"Current IP: {data.get('IP')}")
        else:
            print("× Not connected through Tor")
            
        # Test circuit refresh
        print("\nTesting circuit refresh...")
        with stem.control.Controller.from_port(port=9051) as controller:
            controller.authenticate()
            controller.signal(stem.Signal.NEWNYM)
            time.sleep(5)  # Wait for new circuit
            
            response = requests.get('https://api.ipify.org?format=json')
            new_ip = response.json()['ip']
            print(f"New IP after circuit refresh: {new_ip}")
            
        print("\nTor connection test completed successfully")
        return True
        
    except Exception as e:
        print(f"Error testing Tor connection: {e}")
        return False

if __name__ == "__main__":
    test_tor_connection()