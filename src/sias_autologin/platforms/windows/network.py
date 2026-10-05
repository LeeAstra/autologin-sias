"""Windows Wi-Fi observation."""
import ctypes
import os
import re
import subprocess

def target_wifi(ssid):
    try:
        result = subprocess.run(['netsh', 'wlan', 'show', 'interfaces'], capture_output=True,
                                timeout=5, creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
        # SSIDs are Unicode on Windows; netsh console encoding follows the OEM code page.
        encoding = f'cp{ctypes.windll.kernel32.GetOEMCP()}' if os.name == 'nt' else 'utf-8'
        text = result.stdout.decode(encoding, errors='replace')
        if result.returncode != 0:
            return 'network_unverified'
        names = re.findall(r'^\s*SSID\s*:\s*(.*?)\s*$', text, re.M)
        return 'target_network' if ssid in names else 'wrong_network'
    except Exception:
        return 'network_unverified'
