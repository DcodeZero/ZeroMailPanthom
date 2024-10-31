#!/usr/bin/env python3
import os
import platform
import time
import socket
import uuid
import psutil
import ctypes
import random
from typing import Dict, Optional
import logging

class SandboxDetector:
    def __init__(self, config: Dict = None):
        """Initialize Sandbox Detector with configuration."""
        self.config = config or {}
        self.setup_logging()
        self._init_thresholds()
        self.is_windows = platform.system() == 'Windows'

    def setup_logging(self):
        """Configure logging."""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)

    def _init_thresholds(self):
        """Initialize default detection thresholds."""
        self.thresholds = {
            'min_ram': 4096,  # MB
            'min_disk': 100,  # GB
            'min_cpu_cores': 2,
            'min_running_processes': 50,
            'min_uptime': 3600  # seconds
        }

    def check_system_resources(self) -> bool:
        """Check system resources for sandbox indicators."""
        try:
            # RAM Check
            total_ram = psutil.virtual_memory().total / (1024 * 1024)  # Convert to MB
            if total_ram < self.thresholds['min_ram']:
                return False

            # Disk Check
            disk_size = psutil.disk_usage('/').total / (1024 * 1024 * 1024)  # Convert to GB
            if disk_size < self.thresholds['min_disk']:
                return False

            # CPU Cores Check
            cpu_cores = psutil.cpu_count()
            if cpu_cores < self.thresholds['min_cpu_cores']:
                return False

            # Running Processes Check
            running_processes = len(psutil.pids())
            if running_processes < self.thresholds['min_running_processes']:
                return False

            return True
            
        except Exception as e:
            self.logger.error(f"Error checking system resources: {e}")
            return True

    def check_system_uptime(self) -> bool:
        """Check system uptime."""
        try:
            if self.is_windows:
                kernel32 = ctypes.windll.kernel32
                uptime = kernel32.GetTickCount64() / 1000  # Convert to seconds
            else:
                uptime = time.time() - psutil.boot_time()
            
            return uptime >= self.thresholds['min_uptime']
        except Exception as e:
            self.logger.error(f"Error checking uptime: {e}")
            return True

    def check_vm_artifacts(self) -> bool:
        """Check for VM/Sandbox artifacts."""
        suspicious_processes = [
            'vboxservice.exe', 'vmtoolsd.exe', 'vmwaretray.exe',
            'sandboxiedcomlaunch.exe', 'procmon.exe', 'wireshark.exe'
        ]
        
        try:
            for proc in psutil.process_iter(['name']):
                try:
                    if proc.info['name'].lower() in suspicious_processes:
                        return False
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking VM artifacts: {e}")
            return True

    def check_hardware_artifacts(self) -> bool:
        """Check hardware characteristics."""
        try:
            vm_macs = ['00:05:69', '00:0C:29', '00:1C:14', '00:50:56', '08:00:27']
            
            mac = uuid.getnode()
            mac_str = ':'.join([f'{(mac >> i) & 0xFF:02x}' for i in range(0, 48, 8)])
            
            for vm_mac in vm_macs:
                if mac_str.startswith(vm_mac):
                    return False
            return True
            
        except Exception as e:
            self.logger.error(f"Error checking hardware artifacts: {e}")
            return True

    def apply_timing_evasion(self) -> bool:
        """Apply timing-based evasion techniques."""
        try:
            sleep_time = random.uniform(1, 3)
            time.sleep(sleep_time)
            
            start_time = time.time()
            _ = [i * i for i in range(1000)]  # Simple computation
            execution_time = time.time() - start_time
            
            return execution_time > 0.001
            
        except Exception as e:
            self.logger.error(f"Error in timing evasion: {e}")
            return True

    def check_user_interaction(self) -> bool:
        """Check for signs of user interaction."""
        try:
            if self.is_windows:
                try:
                    import win32api #type: ignore
                    last_input = win32api.GetLastInputInfo()
                    return last_input > 0
                except ImportError:
                    self.logger.warning("win32api not available, skipping Windows-specific checks")
                    return True
            else:
                # For Linux/Unix systems
                try:
                    with open('/proc/uptime', 'r') as f:
                        uptime = float(f.readline().split()[0])
                    return uptime > 3600  # More than 1 hour uptime
                except:
                    return True
                    
        except Exception as e:
            self.logger.error(f"Error checking user interaction: {e}")
            return True

class SandboxEvasion:
    def __init__(self, config: Dict = None):
        """Initialize Sandbox Evasion with configuration."""
        self.config = config or {}
        self.detector = SandboxDetector(config)

    def run_checks(self) -> Dict:
        """Run configured sandbox detection checks."""
        checks_config = self.config.get('sandbox_evasion', {}).get('checks', {})
        results = {
            'system_resources': False,
            'uptime': False,
            'vm_artifacts': False,
            'hardware': False,
            'timing': False,
            'user_interaction': False,
            'score': 0
        }
        
        enabled_checks = len([check for check, enabled in checks_config.items() if enabled])
        if enabled_checks == 0:
            return {'score': 0, 'confidence': 0, **results}

        if checks_config.get('system_resources', True):
            results['system_resources'] = self.detector.check_system_resources()
            if results['system_resources']:
                results['score'] += 1

        if checks_config.get('uptime', True):
            results['uptime'] = self.detector.check_system_uptime()
            if results['uptime']:
                results['score'] += 1

        if checks_config.get('vm_artifacts', True):
            results['vm_artifacts'] = self.detector.check_vm_artifacts()
            if results['vm_artifacts']:
                results['score'] += 1

        if checks_config.get('hardware', True):
            results['hardware'] = self.detector.check_hardware_artifacts()
            if results['hardware']:
                results['score'] += 1

        if checks_config.get('timing', True):
            results['timing'] = self.detector.apply_timing_evasion()
            if results['timing']:
                results['score'] += 1

        if checks_config.get('user_interaction', True):
            results['user_interaction'] = self.detector.check_user_interaction()
            if results['user_interaction']:
                results['score'] += 1

        results['confidence'] = (results['score'] / enabled_checks) * 100
        return results

    def evade(self) -> Optional[str]:
        """Run sandbox evasion checks and return result."""
        if not self.config.get('sandbox_evasion', {}).get('enabled', False):
            return None
            
        checks = self.run_checks()
        threshold = self.config.get('sandbox_evasion', {}).get('confidence_threshold', 70)
        
        if checks['confidence'] < threshold:
            self.detector.logger.warning(
                f"Sandbox detected with {checks['confidence']}% confidence"
            )
            return "sandbox_detected"
        
        return None

def integrate_sandbox_evasion(email_campaign_class):
    """Decorator to integrate sandbox evasion with email campaign."""
    original_init = email_campaign_class.__init__

    def new_init(self, *args, **kwargs):
        original_init(self, *args, **kwargs)
        self.sandbox_evasion = SandboxEvasion(self.config)

    def check_environment(self):
        """Check environment before sending emails."""
        evasion_result = self.sandbox_evasion.evade()
        if evasion_result == "sandbox_detected":
            raise EnvironmentError("Unsafe environment detected")

    email_campaign_class.__init__ = new_init
    email_campaign_class.check_environment = check_environment
    return email_campaign_class

def test_sandbox_evasion():
    """Test sandbox evasion functionality."""
    # Example configuration matching your format
    config = {
        "sandbox_evasion": {
            "enabled": False,
            "confidence_threshold": 70,
            "checks": {
                "system_resources": True,
                "uptime": True,
                "vm_artifacts": True,
                "hardware": True,
                "timing": True,
                "user_interaction": True
            }
        }
    }
    
    # Initialize sandbox evasion
    sandbox = SandboxEvasion(config)
    
    # Run checks and print results
    print("\nRunning Sandbox Detection Checks...")
    results = sandbox.run_checks()
    
    print("\nCheck Results:")
    for check, result in results.items():
        if check not in ['score', 'confidence']:
            print(f"{check}: {'✓' if result else '×'}")
    
    print(f"\nConfidence Score: {results['confidence']:.1f}%")
    print(f"Sandbox Detection: {'Yes' if results['confidence'] < config['sandbox_evasion']['confidence_threshold'] else 'No'}")

if __name__ == "__main__":
    test_sandbox_evasion()