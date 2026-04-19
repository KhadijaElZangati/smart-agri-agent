import os
import json
import subprocess
import requests
from datetime import datetime

# --- PATH CONFIGURATION (Linux Standard) ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OFFLINE_AGENT = os.path.join(BASE_DIR, "..", "agents", "Offline_soil_agent.py")
ONLINE_AGENT = os.path.join(BASE_DIR, "..", "agents", "online_soil_agent.py")

def check_internet(timeout=3):
    """Heartbeat check to determine connectivity status."""
    try:
        # Pinging Google DNS to check if we are online in Souss-Massa
        requests.get("https://8.8.8.8", timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def run_soil_intelligence():
    print(f"---  Soil Intelligence Coordinator Booting ---")
    is_online = check_internet()
    
    if is_online:
        print(" [STATUS] Online: Triggering SoilGrids + FAO Context...")
        # Run Online Agent (REST API Focus)
        subprocess.run(["python3", ONLINE_AGENT])
        active_json = os.path.join(BASE_DIR, "..", "config", "online_soil_state.json")
    else:
        print(" [STATUS] Offline: Falling back to NASA-Simulated IoT Pulse...")
        # Run Offline Agent (Local Sensor Focus)
        subprocess.run(["python3", OFFLINE_AGENT])
        active_json = os.path.join(BASE_DIR, "..", "config", "soil_state.json")

    # Final Verification: Bulletproof File Reading
    if os.path.exists(active_json):
        try:
            with open(active_json, 'r') as f:
                content = f.read().strip()
                if content:
                    state = json.loads(content)
                    print(f"  Process Complete. Mode: {'Cloud' if is_online else 'Edge'}")
                    print(f"  Current Status: {state.get('status', state.get('health_status', 'DATA_READY'))}")
                else:
                    print(" ⏳ State file created but still empty. Waiting for next cycle...")
        except json.JSONDecodeError:
            print(" ⚠️ State file is currently locked or corrupt. Retrying on next cycle...")
    else:
        print(" ⚠️ State file not found. Ensure agents are generating reports correctly.")

if __name__ == "__main__":
    run_soil_intelligence()
