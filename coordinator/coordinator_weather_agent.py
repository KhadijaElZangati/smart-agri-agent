import os
import json
import requests
import subprocess
from datetime import datetime

# --- DYNAMIC PATH MANAGEMENT ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Points to the config folder in the root
CONFIG_DIR = os.path.join(BASE_DIR, "..", "config")
ONLINE_STATE = os.path.join(CONFIG_DIR, "online_weather_state.json")
LOCAL_STATE = os.path.join(CONFIG_DIR, "local_weather_state.json")

# Points to the agents folder in the root
AGENTS_DIR = os.path.join(BASE_DIR, "..", "agents")
ONLINE_SCRIPT = os.path.join(AGENTS_DIR, "online_weather_agent.py")
OFFLINE_SCRIPT = os.path.join(AGENTS_DIR, "Offline_weather_agent.py")

def check_internet(timeout=8):
    """Pings a reliable server to check for a 4G/LTE heartbeat."""
    try:
        # Pinging Google's DNS
        requests.get("https://8.8.8.8", timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def run_agent(script_path):
    """Helper to execute an agent script and wait for its JSON output."""
    try:
        print(f" Executing: {os.path.basename(script_path)}...")
        subprocess.run(["python3", script_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f" Execution failed for {script_path}: {e}")
        return False

def get_unified_weather():
    """
    The main logic for the Weather Department Head.
    Decides between Cloud data and Edge-Vision.
    """
    print(f"--- Weather Coordinator Heartbeat [{datetime.now().strftime('%H:%M:%S')}] ---")
    
    # 1. Check Connectivity
    is_online = check_internet()
    
    if is_online:
        print(" Status: ONLINE. Triggering Cloud Intelligence...")
        if run_agent(ONLINE_SCRIPT) and os.path.exists(ONLINE_STATE):
            with open(ONLINE_STATE, 'r') as f:
                return json.load(f)
    
    # 2. Fallback to Survival Mode (Offline Vision)
    print("status: OFFLINE (or API Error). Activating MiT-B0 Vision...")
    if run_agent(OFFLINE_SCRIPT) and os.path.exists(LOCAL_STATE):
        with open(LOCAL_STATE, 'r') as f:
            data = json.load(f)
            data["coordinator_note"] = "Data sourced from local Edge-AI vision due to connection loss."
            return data

    return {"error": "Critical Failure: Both Online and Offline sources unavailable."}

if __name__ == "__main__":
    # Ensure the config directory exists
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    final_weather = get_unified_weather()
    
    print("\n FINAL WEATHER REPORT FOR THE CENTRAL COORDINATOR:")
    print(json.dumps(final_weather, indent=2))
