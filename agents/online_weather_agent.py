import os
import json
import requests
from datetime import datetime, timedelta
from dotenv import load_dotenv
from supabase import create_client, Client

# --- 1. DYNAMIC PATH CONFIGURATION ---
# This finds the 'agents/' folder where this script lives
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# Find the .env file in the root directory
ENV_PATH = os.path.join(BASE_DIR, "..", ".env")
# Path to save the output for the Coordinator to read
STATE_FILE = os.path.join(BASE_DIR, "..", "config", "online_weather_state.json")

# Explicitly load environment variables from the root .env
load_dotenv(dotenv_path=ENV_PATH)

# --- 2. CREDENTIALS & DEFAULTS ---
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

FARM_LAT = float(os.getenv("FARM_LAT", 30.42)) 
FARM_LON = float(os.getenv("FARM_LON", -9.60))
FARM_NAME = os.getenv("FARM_NAME", "Default Farm - Souss-Massa")

def run_agent():
    if not SUPABASE_URL or not SUPABASE_KEY:
        print(f" ❌ Error: Supabase credentials missing at {ENV_PATH}!")
        return

    print(f"[{datetime.now().strftime('%H:%M:%S')}] Online Agent starting for {FARM_NAME}...")
    
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
    except Exception as e:
        print(f" ❌ Connection Error: {e}")
        return

    # 3. Fetch NASA Data (Historical context)
    today = datetime.now()
    start = (today - timedelta(days=3)).strftime("%Y%m%d")
    end = today.strftime("%Y%m%d")
    
    nasa_url = f"https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR,RH2M&community=AG&longitude={FARM_LON}&latitude={FARM_LAT}&start={start}&end={end}&format=JSON"
    nasa_res = requests.get(nasa_url).json()
    
    # Clean -999.0 values
    params = nasa_res['properties']['parameter']
    for p in params:
        for d in params[p]:
            if params[p][d] == -999.0: params[p][d] = None

    # 4. Fetch Open-Meteo Forecast
    forecast_url = f"https://api.open-meteo.com/v1/forecast?latitude={FARM_LAT}&longitude={FARM_LON}&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Africa/Casablanca"
    forecast_res = requests.get(forecast_url).json()

    # 5. Build Unified Output
    agent_output = {
        "agent": "weather_agent_online",
        "timestamp": datetime.now().isoformat(),
        "farm_name": FARM_NAME,
        "perceived_condition": "Fetched from Cloud API",
        "historical": params,
        "forecast": forecast_res.get('daily', {}),
        "alerts": [],
        "is_offline_mode": False
    }

    # Souss-Massa specific water scarcity alert
    precip_sum = sum(forecast_res['daily'].get('precipitation_sum', [0]))
    if precip_sum < 0.2:
        agent_output["alerts"].append("Critical: No rain forecast. Adjust irrigation.")

    # 6. SAVE LOCAL STATE FOR COORDINATOR
    # Ensure config folder exists
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        json.dump(agent_output, f, indent=2)

    # 7. Sync to Supabase for your dashboard
    try:
        supabase.table("weather_logs").insert({
            "farm_name": FARM_NAME,
            "latitude": FARM_LAT,
            "longitude": FARM_LON,
            "weather_data": agent_output 
        }).execute()
        print("  Success! Cloud Data Synced and Local State Saved.")
    except Exception as e:
        print(f"  Data saved locally, but Supabase sync failed: {e}")

if __name__ == "__main__":
    run_agent()
