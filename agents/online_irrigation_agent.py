import os
import json
import requests
from datetime import datetime
from dotenv import load_dotenv
from supabase import create_client, Client

# --- 1. DYNAMIC PATH CONFIGURATION ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")
IRRIGATION_STATE = os.path.join(BASE_DIR, "..", "config", "online_irrigation_state.json")
WEATHER_STATE = os.path.join(BASE_DIR, "..", "config", "online_weather_state.json")

# Explicitly load environment variables
load_dotenv(dotenv_path=ENV_PATH)

# --- 2. CREDENTIALS & DEFAULTS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
FARM_NAME = os.getenv("FARM_NAME", "Default Farm - Souss-Massa")

# Default Souss-Massa Crop Parameters (Based on FAO AquaCrop standards)
CROP_TYPE = "Tomato" 
CROP_KC = 1.15  # Crop Coefficient for mid-season tomatoes
BASE_ET0 = 4.5  # mm/day average for the Agadir region

def calculate_irrigation_need(forecast_data):
    """
    Calculates the water deficit based on FAO Kc and NASA/Open-Meteo rain forecast.
    Formula: Irrigation = (ET0 * Kc) - Rain
    """
    print(f"  Calculating water requirements for {CROP_TYPE}...")
    
    # Calculate base daily need (ETc)
    daily_crop_need = BASE_ET0 * CROP_KC
    
    # Check precipitation forecast from the Weather Agent's local JSON contract
    expected_rain_mm = 0.0
    if forecast_data and "forecast" in forecast_data:
        # Pulls the sum of precipitation for the current day
        try:
            expected_rain_mm = forecast_data["forecast"].get("precipitation_sum", [0.0])[0]
        except (IndexError, TypeError):
            expected_rain_mm = 0.0
    
    # Calculate final deficit to avoid waste (addresses high cost of inputs)
    irrigation_deficit = daily_crop_need - expected_rain_mm
    
    # Ensure no negative watering values
    final_need = max(0.0, irrigation_deficit)
    
    status = "WATERING_REQUIRED" if final_need > 0 else "NO_WATERING_NEEDED"
    
    return {
        "crop": CROP_TYPE,
        "daily_need_mm": round(daily_crop_need, 2),
        "expected_rain_mm": expected_rain_mm,
        "required_irrigation_mm": round(final_need, 2),
        "action_status": status
    }

def run_agent():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f"  Error: Supabase credentials missing at {ENV_PATH}!")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Irrigation Agent: Computing water schedules for {FARM_NAME}...")
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f"  Connection Error: {e}")
        return

    # 1. Read Weather Forecast (The 'Chained' decision dependency)
    forecast_data = None
    if os.path.exists(WEATHER_STATE):
        try:
            with open(WEATHER_STATE, 'r') as f:
                forecast_data = json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            print("  ️ Weather state unavailable, defaulting to full demand.")

    # 2. Compute the decision based on Cloud APIs + FAO Context
    irrigation_decision = calculate_irrigation_need(forecast_data)
    
    # 3. Build the Structured JSON Output
    agent_output = {
        "agent": "irrigation_agent_online",
        "timestamp": datetime.now().isoformat(),
        "farm_name": FARM_NAME,
        "irrigation_plan": irrigation_decision,
        "status": "SCHEDULING_COMPLETE",
        "is_offline_mode": False
    }

    # 4. Save local JSON contract for the Coordinator (Survival/Logic Gate)
    os.makedirs(os.path.dirname(IRRIGATION_STATE), exist_ok=True)
    with open(IRRIGATION_STATE, 'w') as f:
        json.dump(agent_output, f, indent=2)
    
    # 5. Push to Supabase (Cloud Historical Archive)
    print("  Syncing irrigation schedule to Supabase...")
    try:
        supabase.table("irrigation_logs").insert({
            "farm_name": FARM_NAME,
            "crop_type": CROP_TYPE,
            "required_mm": irrigation_decision["required_irrigation_mm"],
            "irrigation_data": agent_output 
        }).execute()
        print("  Success! Cloud Data Synced and Local State Saved.")
    except Exception as e:
        print(f"  Data saved locally, but Supabase sync failed: {e}")

if __name__ == "__main__":
    run_agent()
