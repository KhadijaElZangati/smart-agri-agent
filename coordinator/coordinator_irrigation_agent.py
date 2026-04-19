import os
import json
import requests
import subprocess
from datetime import datetime

# --- DYNAMIC PATH MANAGEMENT ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_DIR = os.path.join(BASE_DIR, "..", "config")

# Input Dependencies (Data from other agents)
SOIL_STATE = os.path.join(CONFIG_DIR, "soil_state.json")
WEATHER_STATE = os.path.join(CONFIG_DIR, "online_weather_state.json")

# Outputs
ONLINE_IRR_STATE = os.path.join(CONFIG_DIR, "online_irrigation_state.json")
OFFLINE_IRR_STATE = os.path.join(CONFIG_DIR, "local_irrigation_state.json")

# Scripts
AGENTS_DIR = os.path.join(BASE_DIR, "..", "agents")
ONLINE_SCRIPT = os.path.join(AGENTS_DIR, "online_irrigation_agent.py")
OFFLINE_SCRIPT = os.path.join(AGENTS_DIR, "Offline_irrigation_agent.py")

def check_internet(timeout=5):
    """Heartbeat check for Souss-Massa connectivity."""
    try:
        requests.get("https://8.8.8.8", timeout=timeout)
        return True
    except (requests.ConnectionError, requests.Timeout):
        return False

def run_agent(script_path):
    """Executes the chosen irrigation logic."""
    try:
        print(f" Running: {os.path.basename(script_path)}...")
        subprocess.run(["python3", script_path], check=True)
        return True
    except subprocess.CalledProcessError as e:
        print(f"  Error running {script_path}: {e}")
        return False

def get_unified_irrigation():
    print(f"--- Irrigation Coordinator Heartbeat [{datetime.now().strftime('%H:%M:%S')}] ---")
    
    # 1. Check Connectivity
    is_online = check_internet()
    
    if is_online:
        print(" [STATUS] Online: Optimizing water via FAO + Forecast...")
        if run_agent(ONLINE_SCRIPT) and os.path.exists(ONLINE_IRR_STATE):
            with open(ONLINE_IRR_STATE, 'r') as f:
                return json.load(f)
    
    # 2. Fallback: Immediate Soil Deficit Logic
    print(" [STATUS] Offline: Fallback to Emergency Edge Watering...")
    if run_agent(OFFLINE_SCRIPT) and os.path.exists(OFFLINE_IRR_STATE):
        with open(OFFLINE_IRR_STATE, 'r') as f:
            data = json.load(f)
            return data

    return {"error": "Critical Failure: Irrigation calculation unavailable."}

if __name__ == "__main__":
    # Final check: Ensure the dependencies exist
    if not os.path.exists(SOIL_STATE):
        print(" Warning: No Soil Data found. Run Soil Coordinator first.")
        
    final_plan = get_unified_irrigation()
    
    print("\n FINAL IRRIGATION DECISION:")
    print(json.dumps(final_plan, indent=2))
