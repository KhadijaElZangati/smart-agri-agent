import os
import json
from datetime import datetime

# --- CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOIL_STATE_JSON = os.path.join(BASE_DIR, "..", "config", "soil_state.json")

def read_physical_sensors():
    """
    In a real setup, this would use 'serial' to read from 
    your ESP32/Arduino via USB. For now, we simulate.
    """
    # Simulate a dry Agadir soil reading
    return {
        "moisture": 28.5,  # Percentage (%)
        "ph_level": 6.8,   # Neutral-to-slightly acidic
        "temperature_c": 24.2
    }

def run_agent():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Offline Soil Agent: Accessing hardware sensors...")
    
    data = read_physical_sensors()
    
    # Hard-coded threshold (Protects against Prompt Injection)
    # The AI cannot 'persuade' the system to ignore these numbers.
    status = "OPTIMAL"
    if data["moisture"] < 30.0:
        status = "CRITICAL_DRY"
    elif data["ph_level"] > 7.5:
        status = "ALKALINE_WARNING"

    soil_report = {
        "agent": "soil_agent_offline",
        "timestamp": datetime.now().isoformat(),
        "readings": data,
        "health_status": status,
        "is_offline_mode": True,
        "source": "Local T450 Hardware Interface"
    }

    with open(SOIL_STATE_JSON, 'w') as f:
        json.dump(soil_report, f, indent=2)
    
    print(f"  Soil Status: {status} (Moisture: {data['moisture']}%)")

if __name__ == "__main__":
    run_agent()
