import os
import json
from datetime import datetime

# --- PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SOIL_STATE = os.path.join(BASE_DIR, "..", "config", "soil_state.json")
IRRIGATION_STATE = os.path.join(BASE_DIR, "..", "config", "local_irrigation_state.json")

# Souss-Massa Target (FAO standards for Tomato in Sandy-Loam)
FIELD_CAPACITY_TARGET = 35.0  # % Moisture target for Agadir region
CRITICAL_WILTING_POINT = 15.0 # % Moisture where plants die

def calculate_emergency_water(current_moisture):
    """
    Calculates water needed based purely on local soil deficit.
    Simplified formula for the Edge: (Target % - Current %) * Root Depth factor
    """
    if current_moisture >= FIELD_CAPACITY_TARGET:
        return 0.0, "SOIL_SATURATED"
    
    # Calculate deficit (simulating mm of water needed to reach capacity)
    deficit_mm = (FIELD_CAPACITY_TARGET - current_moisture) * 0.5 
    
    status = "EMERGENCY_WATERING" if current_moisture < 20.0 else "MAINTENANCE_WATERING"
    return round(deficit_mm, 2), status

def run_agent():
    print(f"[{datetime.now().strftime('%H:%M:%S')}] Offline Irrigation Agent: Edge-Vision Active...")
    
    # 1. Read Local Soil Pulse
    current_moisture = 25.0 # Fallback
    if os.path.exists(SOIL_STATE):
        try:
            with open(SOIL_STATE, 'r') as f:
                soil_data = json.load(f)
                current_moisture = soil_data.get("readings", {}).get("moisture", 25.0)
        except:
            pass

    # 2. Compute immediate need
    water_mm, status = calculate_emergency_water(current_moisture)

    # 3. Create JSON Contract
    output = {
        "agent": "irrigation_agent_offline",
        "timestamp": datetime.now().isoformat(),
        "local_readings": {"current_moisture": current_moisture},
        "irrigation_plan": {
            "required_irrigation_mm": water_mm,
            "action_status": status
        },
        "is_offline_mode": True,
        "coordinator_note": "Direct sensor-to-pump logic triggered."
    }

    with open(IRRIGATION_STATE, 'w') as f:
        json.dump(output, f, indent=2)
    
    print(f"  Offline Irrigation Plan Saved: {water_mm}mm needed.")

if __name__ == "__main__":
    run_agent()
